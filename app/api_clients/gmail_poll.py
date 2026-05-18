#!/usr/bin/env python3
import os, json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

CREDENTIALS_PATH = "/Users/kshitizmittal/.openclaw/secrets/gmail_credentials.json"
TOKEN_PATH = "/Users/kshitizmittal/.openclaw/secrets/gmail_token.json"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify"
]

def get_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)

def fetch_unread(service, max_results=10):
    result = service.users().messages().list(
        userId="me", q="is:unread", maxResults=max_results
    ).execute()
    messages = result.get("messages", [])
    for msg in messages:
        detail = service.users().messages().get(
            userId="me", id=msg["id"], format="metadata",
            metadataHeaders=["From", "Subject", "Date"]
        ).execute()
        headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
        print(f"From: {headers.get('From')}")
        print(f"Subject: {headers.get('Subject')}")
        print(f"Date: {headers.get('Date')}")
        print("---")

if __name__ == "__main__":
    service = get_service()
    fetch_unread(service)
