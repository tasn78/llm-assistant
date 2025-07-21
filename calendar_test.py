from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']

creds = Credentials.from_authorized_user_file('token.json', SCOPES)
service = build('calendar', 'v3', credentials=creds)
event = {
    'summary': "Test Event",
    'start': {
        'dateTime': "2025-07-31T15:00:00",
        'timeZone': 'America/Chicago',
    },
    'end': {
        'dateTime': "2025-07-31T16:00:00",
        'timeZone': 'America/Chicago',
    }
}
print("[DEBUG] Inserting minimal event:", event)
service.events().insert(calendarId='primary', body=event).execute()
print("[DEBUG] Minimal event created!")
