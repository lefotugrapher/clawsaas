#!/usr/bin/env python3
"""Daily 7 AM briefing — email summary sent to Telegram."""
import json, urllib.request, urllib.parse, logging
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from openai import OpenAI
import config

log = logging.getLogger("daily_briefing")
log.setLevel(logging.INFO)
log.propagate = False
if not log.handlers:
    _h = logging.FileHandler(f"{config.LOGS}/daily_briefing.log")
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(_h)

def get_gmail():
    creds = Credentials.from_authorized_user_file(config.GMAIL_TOKEN, config.GMAIL_SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)

def get_tg():
    with open(config.TELEGRAM_SECRET) as f:
        return json.load(f)

def get_api_key():
    with open(config.AUTH_PROFILES) as f:
        return json.load(f)["profiles"]["openrouter:default"]["key"]

def count_unread_24h(svc):
    result = svc.users().messages().list(
        userId="me", q="is:unread newer_than:1d", maxResults=100
    ).execute()
    return len(result.get("messages", []))

def load_pending():
    import os
    if os.path.exists(config.PENDING_REPLIES):
        with open(config.PENDING_REPLIES) as f:
            return json.load(f)
    return {}

def send_tg(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    urllib.request.urlopen(url, data, timeout=10)

def main():
    try:
        gmail   = get_gmail()
        tg      = get_tg()
        api_key = get_api_key()
        pending = load_pending()

        unread   = count_unread_24h(gmail)
        waiting  = [p for p in pending.values() if p.get("status") == "pending"]
        sent     = sum(1 for p in pending.values() if p.get("status") == "sent")

        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
        waiting_summary = "\n".join(
            f"- {w['to']} re: {w['subject']}" for w in waiting[:5]
        ) or "(none)"

        prompt = (
            f"Write a short warm morning briefing (3-4 sentences) for a busy person.\n"
            f"Time: {datetime.now().strftime('%A %b %d, %I:%M %p')}\n"
            f"Unread emails (24h): {unread}\n"
            f"Drafts waiting approval: {len(waiting)}\n"
            f"Replies sent: {sent}\n"
            f"Pending: {waiting_summary}\n"
            f"Tone: friendly, brief, like a personal assistant texting at 7 AM. Plain text, no markdown."
        )
        response = client.chat.completions.create(
            model=config.OPENROUTER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250,
        )
        body = response.choices[0].message.content.strip()
        send_tg(tg["bot_token"], tg["chat_id"], f"Good morning! ({datetime.now().strftime('%A, %b %d')})\n\n{body}")
        log.info("Briefing sent.")
    except Exception as e:
        log.error(f"Briefing failed: {e}")

if __name__ == "__main__":
    main()
