#!/usr/bin/env python3
"""
Google Calendar integration for Sassyclaw.
Usage:
  calendar_api.py list                       # list upcoming 10 events
  calendar_api.py today                      # events today
  calendar_api.py week                       # next 7 days
  calendar_api.py search "keyword"           # search ALL events by keyword (past + future)
  calendar_api.py add "Title" "2026-05-17 14:00" "2026-05-17 15:00"
"""
import os, json, sys, datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

CREDENTIALS_PATH = "/Users/kshitizmittal/.openclaw/secrets/gmail_credentials.json"
TOKEN_PATH       = "/Users/kshitizmittal/.openclaw/secrets/calendar_token.json"
SCOPES = ["https://www.googleapis.com/auth/calendar"]

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
    return build("calendar", "v3", credentials=creds)

def fmt_event(e):
    start = e["start"].get("dateTime", e["start"].get("date"))
    summary = e.get("summary", "(no title)")
    location = e.get("location", "")
    loc_str = f" @ {location}" if location else ""
    return f"  {start[:16].replace('T', ' ')} — {summary}{loc_str}"

def list_events(time_min, time_max=None, max_results=10):
    svc = get_service()
    args = {
        "calendarId": "primary",
        "timeMin": time_min,
        "maxResults": max_results,
        "singleEvents": True,
        "orderBy": "startTime",
    }
    if time_max:
        args["timeMax"] = time_max
    result = svc.events().list(**args).execute()
    events = result.get("items", [])
    if not events:
        return "No events found."
    return "\n".join(fmt_event(e) for e in events)

def cmd_list():
    now = datetime.datetime.utcnow().isoformat() + "Z"
    print(list_events(now, max_results=10))

def cmd_today():
    today = datetime.date.today()
    start = datetime.datetime.combine(today, datetime.time.min).isoformat() + "Z"
    end = datetime.datetime.combine(today, datetime.time.max).isoformat() + "Z"
    print(list_events(start, end))

def cmd_week():
    now = datetime.datetime.utcnow()
    start = now.isoformat() + "Z"
    end = (now + datetime.timedelta(days=7)).isoformat() + "Z"
    print(list_events(start, end, max_results=50))

def cmd_search(query):
    svc = get_service()
    result = svc.events().list(
        calendarId="primary",
        q=query,
        maxResults=50,
        singleEvents=True,
        orderBy="startTime",
    ).execute()
    events = result.get("items", [])
    if not events:
        print(f"No events found matching '{query}'.")
        return
    print(f"Found {len(events)} events matching '{query}':")
    for e in events:
        print(fmt_event(e))

def cmd_add(title, start_str, end_str):
    svc = get_service()
    start_dt = datetime.datetime.fromisoformat(start_str.replace(" ", "T"))
    end_dt = datetime.datetime.fromisoformat(end_str.replace(" ", "T"))
    event = {
        "summary": title,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": "Europe/Dublin"},
        "end":   {"dateTime": end_dt.isoformat(), "timeZone": "Europe/Dublin"},
    }
    result = svc.events().insert(calendarId="primary", body=event).execute()
    print(f"Added: {result.get('summary')} — {result.get('htmlLink')}")

def main():
    if len(sys.argv) < 2:
        cmd_list()
        return
    cmd = sys.argv[1].lower()
    if cmd == "list":
        cmd_list()
    elif cmd == "today":
        cmd_today()
    elif cmd == "week":
        cmd_week()
    elif cmd == "search" and len(sys.argv) >= 3:
        cmd_search(sys.argv[2])
    elif cmd == "add" and len(sys.argv) >= 5:
        cmd_add(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
