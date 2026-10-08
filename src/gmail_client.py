import os
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CREDENTIALS_PATH = os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")
TOKEN_PATH = os.getenv("GMAIL_TOKEN_PATH", "token.json")


def get_gmail_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                creds = None
        if not creds or not creds.valid:
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(f"Missing {CREDENTIALS_PATH}")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


if __name__ == "__main__":
    try:
        service = get_gmail_service()
        profile = service.users().getProfile(userId="me").execute()
        print("Connected as:", profile["emailAddress"])
    except FileNotFoundError as e:
        print("Error:", e)
    except HttpError as e:
        print("Gmail API error:", e)