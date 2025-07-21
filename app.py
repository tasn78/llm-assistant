import os
import io
import logging
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
import base64

import docx
import fitz  # PyMuPDF
import pytz
from dateparser.search import search_dates
from dotenv import load_dotenv
from email.mime.text import MIMEText
from flask import (Flask, Response, flash, redirect, render_template, request,
                   session, url_for)
from flask_session import Session
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from transformers import pipeline, AutoTokenizer

# --- Application Setup ---
load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY')

# --- Server-Side Session Config ---
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = "/data/flask_session"
Session(app)

# --- Global Constants & Config ---
DATABASE = '/data/app_logs.db'
SCOPES = ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/gmail.send']
TOKEN_FILE = 'token.json'
CREDENTIALS_FILE = 'credentials.json'
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "password")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL")

# --- Logging & Model Loading ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
try:
    MODEL_NAME = "sshleifer/distilbart-cnn-12-6"
    summarizer = pipeline("summarization", model=MODEL_NAME)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    logging.info("Summarization model and tokenizer loaded.")
except Exception as e:
    logging.error(f"Failed to load model/tokenizer: {e}")
    summarizer, tokenizer = None, None

# --- Database & Auth Functions (No Changes) ---
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not os.path.exists(os.path.dirname(DATABASE)):
        os.makedirs(os.path.dirname(DATABASE))
    conn = get_db_connection()
    with conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL
            )
        ''')
    conn.close()

def log_action(level, message):
    timestamp = datetime.now(pytz.utc).isoformat()
    try:
        conn = get_db_connection()
        with conn:
            conn.execute('INSERT INTO logs (timestamp, level, message) VALUES (?, ?, ?)',
                         (timestamp, level, message))
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")

def get_google_creds():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
        else:
            log_action('ERROR', 'Could not obtain valid Google credentials.')
            return None
    return creds

def require_admin_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not (auth.username == ADMIN_USERNAME and auth.password == ADMIN_PASSWORD):
            return Response('Login Required', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})
        return f(*args, **kwargs)
    return decorated

# --- Helper Functions ---
def chunk_by_tokens(text, tokenizer, max_length=1000):
    tokens = tokenizer.encode(text)
    chunks = []
    for i in range(0, len(tokens), max_length):
        chunk_tokens = tokens[i:i + max_length]
        chunks.append(tokenizer.decode(chunk_tokens, skip_special_tokens=True))
    return chunks

# --- NEW FUNCTION TO FIND ACTION ITEMS ---
def find_action_items(text):
    """Finds sentences containing dates and returns them."""
    action_items = []
    # Use dateparser to find any text fragments that look like dates
    found_dates = search_dates(text, settings={'PREFER_DATES_FROM': 'future'})
    if found_dates:
        # For each found date, find the full sentence it belongs to
        for date_text, date_obj in found_dates:
            # Find the sentence containing the date text
            for sentence in text.split('.'):
                if date_text in sentence:
                    action_items.append(sentence.strip() + ".")
                    break # Move to the next found date
    return action_items

# --- Main Routes ---
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        text_to_process = request.form.get("input_text", "")
        document_file = request.files.get('document_file')
        if document_file and document_file.filename:
            try:
                if document_file.filename.lower().endswith('.pdf'):
                    pdf_doc = fitz.open(stream=document_file.read(), filetype="pdf")
                    uploaded_text = "".join(page.get_text() for page in pdf_doc)
                    pdf_doc.close()
                else:
                    uploaded_text = document_file.read().decode('utf-8', 'ignore')
                text_to_process = f"{text_to_process}\n\n{uploaded_text}".strip()
            except Exception as e:
                flash(f"Error reading file: {e}", "danger")
                return redirect(url_for('home'))
        if not text_to_process.strip():
            flash("No text was provided or extracted from the document.", "warning")
            return redirect(url_for('home'))
        if not summarizer or not tokenizer:
            flash("Summarization service is unavailable.", "danger")
            return redirect(url_for('home'))
        try:
            min_len = int(request.form.get("min_length", 30))
            max_len = int(request.form.get("max_length", 150))
            token_count = len(tokenizer.encode(text_to_process))
            if token_count > 1000:
                chunks = chunk_by_tokens(text_to_process, tokenizer)
                summaries = summarizer(chunks, max_length=max_len, min_length=min_len, do_sample=False)
                summary_text = "\n\n".join([summ['summary_text'] for summ in summaries])
            else:
                summary_result = summarizer(text_to_process, max_length=max_len, min_length=min_len, do_sample=False)
                if not summary_result:
                    flash("Summarization failed. The text may be too short.", "warning")
                    return redirect(url_for('home'))
                summary_text = summary_result[0]['summary_text']
            
            # --- APPEND ACTION ITEMS TO THE SUMMARY ---
            action_items = find_action_items(text_to_process)
            if action_items:
                summary_text += "\n\n**Action Items:**\n- " + "\n- ".join(action_items)
            
            session['summary'] = summary_text
            session['original_text'] = text_to_process
            return redirect(url_for('automate'))
        except Exception as e:
            flash(f"Summarization error: {e}", "danger")
            log_action("ERROR", f"Summarization Error: {e}")
            return redirect(url_for('home'))
    return render_template("index.html")

@app.route("/automate", methods=["GET", "POST"])
def automate():
    summary = session.get('summary')
    original_text = session.get('original_text')
    if not summary:
        return redirect(url_for('home'))
    if request.method == "POST":
        creds = get_google_creds()
        if not creds:
            flash("Could not connect to Google Services. Check credentials.", "danger")
            return render_template("automate.html", summary=summary, original_text=original_text)
        if 'create_event' in request.form:
            try:
                calendar_service = build('calendar', 'v3', credentials=creds)
                dates = search_dates(original_text, settings={'PREFER_DATES_FROM': 'future'})
                future_event_time = None
                now_aware = datetime.now(pytz.utc)
                if dates:
                    for text_fragment, parsed_time in dates:
                        if parsed_time.tzinfo is None:
                            parsed_time = pytz.timezone('America/Chicago').localize(parsed_time)
                        if parsed_time > now_aware:
                            future_event_time = parsed_time
                            break
                if not future_event_time:
                    flash("Could not find a future date in the text for the event.", "warning")
                else:
                    start_time = future_event_time
                    end_time = start_time + timedelta(hours=1)
                    event = {
                        'summary': request.form.get('event_title') or "Meeting from AI Assistant",
                        'description': f"Generated Summary:\n{summary}",
                        'start': {'dateTime': start_time.isoformat(), 'timeZone': 'America/Chicago'},
                        'end': {'dateTime': end_time.isoformat(), 'timeZone': 'America/Chicago'},
                    }
                    calendar_service.events().insert(calendarId='primary', body=event).execute()
                    flash(f"Calendar event created for {start_time.strftime('%Y-%m-%d %I:%M %p')}!", "success")
            except Exception as e:
                flash(f"Failed to create calendar event: {e}", "danger")
    return render_template("automate.html", summary=summary, original_text=original_text)

@app.route('/admin')
@require_admin_auth
def admin_dashboard():
    conn = get_db_connection()
    logs = conn.execute('SELECT * FROM logs ORDER BY id DESC LIMIT 50').fetchall()
    conn.close()
    return render_template("admin.html", logs=logs)

with app.app_context():
    init_db()

if __name__ == '__main__':
    if os.path.exists('cert.pem') and os.path.exists('key.pem'):
        app.run(host='0.0.0.0', port=443, ssl_context=('cert.pem', 'key.pem'), debug=True)
    else:
        app.run(host='0.0.0.0', port=5001, debug=True)
