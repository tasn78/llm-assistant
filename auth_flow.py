import os
from google_auth_oauthlib.flow import InstalledAppFlow

# The corrected list of permissions (scopes)
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.send'
]
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'

def main():
    """Runs the manual authorization flow to get a token."""
    
    # --- THIS IS THE MODIFIED LINE ---
    # We are explicitly setting the redirect_uri to use the "out-of-band" flow.
    flow = InstalledAppFlow.from_client_secrets_file(
        CREDENTIALS_FILE,
        SCOPES,
        redirect_uri='urn:ietf:wg:oauth:2.0:oob'
    )
    
    auth_url, _ = flow.authorization_url(prompt='consent')

    print('Please go to this URL and authorize access:')
    print(auth_url)

    code = input('Enter the authorization code you receive here: ')
    flow.fetch_token(code=code)

    with open(TOKEN_FILE, 'w') as token:
        token.write(flow.credentials.to_json())

    print(f'\nToken created successfully and saved to {TOKEN_FILE}!')

if __name__ == '__main__':
    main()
