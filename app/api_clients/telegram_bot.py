#!/usr/bin/env python3
"""
Poll Telegram for replies about pending Gmail drafts.
Handles: YES <id>, NO <id>, <id> <feedback> (redraft with feedback)
"""
import os, json, time, sys, re, urllib.request, urllib.parse, base64, email.mime.text
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from openai import OpenAI

TELEGRAM_SECRET = "/Users/kshitizmittal/.openclaw/secrets/telegram.json"
PENDING_PATH    = "/Users/kshitizmittal/.openclaw/workspace/api_clients/.pending_replies.json"
OFFSET_PATH     = "/Users/kshitizmittal/.openclaw/workspace/api_clients/.telegram_offset.json"
TOKEN_PATH      = "/Users/kshitizmittal/.openclaw/secrets/gmail_token.json"
AUTH_PROFILES   = "/Users/kshitizmittal/.openclaw/agents/main/agent/auth-profiles.json"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]

def get_openrouter_key():
    with open(AUTH_PROFILES) as f:
        return json.load(f)["profiles"]["openrouter:default"]["key"]

def get_tg_creds():
    with open(TELEGRAM_SECRET) as f:
        return json.load(f)

def get_gmail_service():
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)

def load_offset():
    if os.path.exists(OFFSET_PATH):
        with open(OFFSET_PATH) as f:
            return json.load(f).get("offset", 0)
    return 0

def save_offset(offset):
    with open(OFFSET_PATH, "w") as f:
        json.dump({"offset": offset}, f)

def load_pending():
    if os.path.exists(PENDING_PATH):
        with open(PENDING_PATH) as f:
            return json.load(f)
    return {}

def save_pending(pending):
    with open(PENDING_PATH, "w") as f:
        json.dump(pending, f, indent=2)

def get_updates(token, offset):
    url = f"https://api.telegram.org/bot{token}/getUpdates?offset={offset}&timeout=30"
    with urllib.request.urlopen(url, timeout=35) as r:
        return json.loads(r.read())

def send_msg(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
    }).encode()
    urllib.request.urlopen(url, data, timeout=10)

def send_email(data):
    svc = get_gmail_service()
    msg = email.mime.text.MIMEText(data["draft"])
    msg["To"] = data["to"]
    subj = data["subject"]
    msg["Subject"] = subj if subj.startswith("Re:") else f"Re: {subj}"
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    payload = {"raw": raw}
    if data.get("thread_id"):
        payload["threadId"] = data["thread_id"]
    result = svc.users().messages().send(userId="me", body=payload).execute()
    return result["id"]

def redraft(current_draft, feedback, api_key):
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    prompt = f"""Here is a draft email reply:

{current_draft}

The user wants changes: {feedback}

Rewrite the reply incorporating their feedback. Return only the new reply body, nothing else."""
    response = client.chat.completions.create(
        model="anthropic/claude-3.5-haiku",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
    )
    return response.choices[0].message.content.strip()

def find_pending(pending, short_id):
    for full_id, data in pending.items():
        if full_id.startswith(short_id) and data.get("status") == "pending":
            return full_id, data
    return None, None

def process_update(update, creds, pending, api_key):
    msg = update.get("message", {})
    text = msg.get("text", "").strip()
    chat_id = str(msg.get("chat", {}).get("id", ""))
    token = creds["bot_token"]

    if not text or chat_id != str(creds["chat_id"]):
        return

    parts = text.split(None, 2)
    command = parts[0].upper() if parts else ""

    # YES <id>
    if command == "YES" and len(parts) >= 2:
        short_id = parts[1]
        full_id, data = find_pending(pending, short_id)
        if not full_id:
            send_msg(token, chat_id, f"No pending email found for: {short_id}")
            return
        try:
            send_email(data)
            pending[full_id]["status"] = "sent"
            save_pending(pending)
            send_msg(token, chat_id, f"Sent reply to {data['to']}")
        except Exception as e:
            send_msg(token, chat_id, f"Failed to send: {e}")

    # NO <id>
    elif command == "NO" and len(parts) >= 2:
        short_id = parts[1]
        full_id, data = find_pending(pending, short_id)
        if not full_id:
            send_msg(token, chat_id, f"No pending email found for: {short_id}")
            return
        pending[full_id]["status"] = "skipped"
        save_pending(pending)
        send_msg(token, chat_id, f"Skipped.")

    # <id> <feedback> — redraft
    elif len(parts) >= 2 and len(parts[0]) == 8 and re.match(r"^[0-9a-f]+$", parts[0].lower()):
        short_id = parts[0]
        feedback = " ".join(parts[1:])
        full_id, data = find_pending(pending, short_id)
        if not full_id:
            send_msg(token, chat_id, f"No pending email found for: {short_id}")
            return
        try:
            send_msg(token, chat_id, "Redrafting...")
            new_draft = redraft(data["draft"], feedback, api_key)
            pending[full_id]["draft"] = new_draft
            save_pending(pending)
            send_msg(
                token, chat_id,
                f"Updated draft:\n{new_draft}\n\n"
                f"Reply YES {short_id} to send or give more feedback."
            )
        except Exception as e:
            send_msg(token, chat_id, f"Redraft failed: {e}")

    # Greetings → AI-generated friendly reply with menu
    elif text.lower() in ("hi", "hello", "hey", "yo", "sup", "menu", "/menu", "/start"):
        waiting = [(fid, d) for fid, d in pending.items() if d.get("status") == "pending"]
        sent_today = sum(1 for p in pending.values() if p.get("status") == "sent")
        try:
            client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
            from datetime import datetime
            ctx = (
                f"Time: {datetime.now().strftime('%A %I:%M %p')}\n"
                f"Pending drafts: {len(waiting)}\n"
                f"Replies sent today: {sent_today}\n"
                f"Latest pending subjects: {', '.join(d['subject'][:30] for _, d in waiting[:3]) or 'none'}\n"
                f"User just said: {text}"
            )
            prompt = (
                f"You are Sassyclaw, a witty personal email assistant on Telegram. "
                f"The user greeted you. Write a SHORT (1-2 sentences) fresh greeting that feels natural and references the current context (time, pending stuff, etc). "
                f"No corporate tone. Slightly playful. End with the menu below verbatim.\n\n"
                f"Context:\n{ctx}\n\n"
                f"After your greeting, on a new line, append exactly this menu:\n\n"
                f"1. Show pending drafts ({len(waiting)})\n"
                f"2. Check Gmail for new emails now\n"
                f"3. Send me the morning briefing\n"
                f"4. Show today's stats"
            )
            response = client.chat.completions.create(
                model="anthropic/claude-3.5-haiku",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
            )
            send_msg(token, chat_id, response.choices[0].message.content.strip())
        except Exception as e:
            # Fallback to static menu
            send_msg(token, chat_id,
                f"Hey! What do you need?\n\n"
                f"1. Show pending drafts ({len(waiting)})\n"
                f"2. Check Gmail for new emails now\n"
                f"3. Send me the morning briefing\n"
                f"4. Show today's stats")

    elif text.strip() == "1" or text.lower() in ("/status", "status", "drafts"):
        waiting = [(fid, d) for fid, d in pending.items() if d.get("status") == "pending"]
        if not waiting:
            send_msg(token, chat_id, "No pending drafts right now.")
        else:
            lines = [f"{len(waiting)} pending drafts:\n"]
            for fid, d in waiting[:10]:
                lines.append(f"ID: {fid[:8]}")
                lines.append(f"To: {d['to']}")
                lines.append(f"Subject: {d['subject'][:60]}")
                lines.append(f"Draft: {d['draft'][:120]}...")
                lines.append("")
            send_msg(token, chat_id, "\n".join(lines))

    elif text.strip() == "2" or text.lower() in ("check", "/check"):
        send_msg(token, chat_id, "Checking Gmail now...")
        import subprocess
        subprocess.Popen([
            "/Users/kshitizmittal/.openclaw/venv/bin/python3",
            "/Users/kshitizmittal/.openclaw/workspace/api_clients/gmail_important_watch.py"
        ])

    elif text.strip() == "3" or text.lower() in ("brief", "briefing", "/brief"):
        send_msg(token, chat_id, "Generating briefing...")
        import subprocess
        subprocess.Popen([
            "/Users/kshitizmittal/.openclaw/venv/bin/python3",
            "/Users/kshitizmittal/.openclaw/workspace/api_clients/daily_briefing.py"
        ])

    elif text.strip() == "4" or text.lower() in ("stats", "/stats"):
        sent = sum(1 for p in pending.values() if p.get("status") == "sent")
        skipped = sum(1 for p in pending.values() if p.get("status") == "skipped")
        waiting = sum(1 for p in pending.values() if p.get("status") == "pending")
        total = len(pending)
        send_msg(token, chat_id,
            f"Stats so far:\n"
            f"Total processed: {total}\n"
            f"Sent: {sent}\n"
            f"Skipped: {skipped}\n"
            f"Pending: {waiting}")

    else:
        send_msg(token, chat_id, f"Didn't catch that. Type 'hi' for a menu.")

def main():
    creds   = get_tg_creds()
    api_key = get_openrouter_key()
    offset  = load_offset()
    print("Telegram bot polling started...", flush=True)

    while True:
        try:
            updates = get_updates(creds["bot_token"], offset)
            pending = load_pending()
            for update in updates.get("result", []):
                process_update(update, creds, pending, api_key)
                offset = update["update_id"] + 1
                save_offset(offset)
        except KeyboardInterrupt:
            print("Bot stopped.")
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}", flush=True)
            time.sleep(5)

if __name__ == "__main__":
    main()
