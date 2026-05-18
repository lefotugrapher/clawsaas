#!/usr/bin/env python3
"""Send a reply email via Gmail API."""
import sys, base64, email.mime.text, logging
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import config

log = logging.getLogger("gmail_send")
log.setLevel(logging.INFO)
log.propagate = False
if not log.handlers:
    _h = logging.FileHandler(f"{config.LOGS}/gmail_send.log")
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(_h)

def get_service():
    creds = Credentials.from_authorized_user_file(config.GMAIL_TOKEN, config.GMAIL_SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)

def send_reply(to_address, subject, body, thread_id=None):
    svc = get_service()
    msg = email.mime.text.MIMEText(body)
    msg["To"] = to_address
    msg["Subject"] = subject if subject.startswith("Re:") else f"Re: {subject}"
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    payload = {"raw": raw}
    if thread_id:
        payload["threadId"] = thread_id
    result = svc.users().messages().send(userId="me", body=payload).execute()
    log.info(f"Sent to {to_address}: {result['id']}")
    return result["id"]

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: gmail_send.py <to> <subject> <body>")
        sys.exit(1)
    msg_id = send_reply(sys.argv[1], sys.argv[2], sys.argv[3])
    print(f"Sent: {msg_id}")
