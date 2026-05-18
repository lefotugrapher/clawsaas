#!/usr/bin/env python3
import os, json, datetime, pathlib, sys
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# Paths (same as used in gmail_poll.py)
CREDENTIALS_PATH = "/Users/kshitizmittal/.openclaw/secrets/gmail_credentials.json"
TOKEN_PATH = "/Users/kshitizmittal/.openclaw/secrets/gmail_token.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]

def get_service():
    if not os.path.exists(TOKEN_PATH):
        sys.stderr.write("Token file not found. Run the oauth flow first.\n")
        sys.exit(1)
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    service = build("gmail", "v1", credentials=creds)
    return service

def list_important_last_month(service, max_results=50):
    # Gmail query: is:important newer_than:30d
    query = "is:important newer_than:30d"
    results = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    msgs = results.get("messages", [])
    detailed = []
    for m in msgs:
        msg = service.users().messages().get(userId="me", id=m["id"], format="metadata", metadataHeaders=["Subject", "From", "Date"]).execute()
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        detailed.append({
            "id": m["id"],
            "subject": headers.get("Subject", "(no subject)"),
            "from": headers.get("From", ""),
            "date": headers.get("Date", ""),
        })
    return detailed

def main():
    svc = get_service()
    important = list_important_last_month(svc)
    if not important:
        print("No important emails in the past 30 days.")
        return
    print(f"Found {len(important)} important emails in the last 30 days:\n")
    for i, e in enumerate(important, 1):
        print(f"{i}. From: {e['from']}")
        print(f"   Subject: {e['subject']}")
        print(f"   Date: {e['date']}")
        print(f"   ID: {e['id']}\n")

if __name__ == "__main__":
    main()
