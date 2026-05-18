#!/usr/bin/env python3
"""
Watch ALL new emails. Claude judges importance and drafts a reply.
Sends to Telegram for approval. Handles feedback/edits before sending.
"""
import json, sys, re, base64, urllib.request, urllib.parse, logging, os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from openai import OpenAI
import config
import shoot_flow

log = logging.getLogger("gmail_watch")
log.setLevel(logging.INFO)
log.propagate = False
if not log.handlers:
    _h = logging.FileHandler(f"{config.LOGS}/gmail_watch.log")
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(_h)

def get_openrouter_key():
    with open(config.AUTH_PROFILES) as f:
        return json.load(f)["profiles"]["openrouter:default"]["key"]

def get_tg_creds():
    with open(config.TELEGRAM_SECRET) as f:
        return json.load(f)

def get_gmail_service():
    creds = Credentials.from_authorized_user_file(config.GMAIL_TOKEN, config.GMAIL_SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(config.GMAIL_TOKEN, "w") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)

def decode_body(data):
    try:
        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
    except Exception:
        return ""

def extract_body(payload):
    mime = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data", "")
    if mime == "text/plain" and body_data:
        return decode_body(body_data)
    for part in payload.get("parts", []):
        result = extract_body(part)
        if result:
            return result
    return ""

def fetch_new_emails(service, max_results=10):
    results = service.users().messages().list(
        userId="me", q="is:unread -from:me", maxResults=max_results
    ).execute()
    msgs = results.get("messages", [])
    detailed = []
    for m in msgs:
        msg = service.users().messages().get(
            userId="me", id=m["id"], format="full"
        ).execute()
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        body = extract_body(msg["payload"])[:2000]
        detailed.append({
            "id":        m["id"],
            "thread_id": msg.get("threadId"),
            "subject":   headers.get("Subject", "(no subject)"),
            "from":      headers.get("From", "(unknown)"),
            "date":      headers.get("Date", ""),
            "body":      body,
        })
    return detailed

def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def judge_and_draft(mail, api_key):
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    prompt = f"""You are an email assistant for Kayzee. Read this email and decide if it needs a reply.

From: {mail['from']}
Subject: {mail['subject']}
Date: {mail['date']}
Body: {mail['body'] or '(no body)'}

Respond in this exact JSON format:
{{
  "important": true or false,
  "reason": "one sentence",
  "draft": "reply body if important, else empty string"
}}

Rules for the draft:
- Always sign off as "Kayzee" — never use [Your Name] or any placeholder
- Keep it short, warm, and natural
- No corporate stiffness

Only return the JSON."""

    response = None
    last_err = None
    for model in config.OPENROUTER_FALLBACKS:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                timeout=30,
            )
            log.info(f"  Used model: {model}")
            break
        except Exception as e:
            last_err = e
            log.warning(f"  Model {model} failed: {str(e)[:100]}")
            continue
    if response is None:
        raise RuntimeError(f"All models failed. Last error: {last_err}")
    text = response.choices[0].message.content.strip()
    # Strip markdown fences
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    # Extract JSON object if wrapped in extra text
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    return json.loads(text)

def escape_html(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def send_tg(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }).encode()
    urllib.request.urlopen(url, data, timeout=10)

def extract_email_address(from_field):
    match = re.search(r"<(.+?)>", from_field)
    return match.group(1) if match else from_field.strip()

def main():
    try:
        gmail   = get_gmail_service()
        api_key = get_openrouter_key()
        tg      = get_tg_creds()
    except Exception as e:
        log.error(f"Startup failed: {e}")
        sys.exit(1)

    processed = set(load_json(config.PROCESSED_EMAILS, []))
    pending   = load_json(config.PENDING_REPLIES, {})
    new_ids   = set()

    try:
        emails = fetch_new_emails(gmail)
    except Exception as e:
        log.error(f"Failed to fetch emails: {e}")
        sys.exit(1)

    conversations = shoot_flow.load_conversations()

    for mail in emails:
        if mail["id"] in processed:
            continue
        log.info(f"Processing: {mail['subject']} from {mail['from']}")
        thread_id = mail["thread_id"]

        # ─── Path 1: continuation of an active shoot conversation ────────
        active = shoot_flow.find_active_conversation(thread_id, conversations)
        if active and active.get("status") == "in_progress":
            try:
                conv, state = shoot_flow.continue_conversation(active, mail["body"], api_key)
                conversations[thread_id] = conv
                shoot_flow.save_conversations(conversations)
                new_ids.add(mail["id"])
                if state == "complete":
                    log.info(f"  Shoot details complete — sending summary to Kayzee")
                    shoot_flow.send_telegram(shoot_flow.build_summary_for_kayzee(conv))
                else:
                    log.info(f"  Asked next question, awaiting client reply")
            except Exception as e:
                log.error(f"  Shoot continuation failed: {str(e)[:200]} — will retry")
            continue

        # ─── Judge importance and decide flow ────────────────────────────
        try:
            result = judge_and_draft(mail, api_key)
        except Exception as e:
            log.error(f"Claude failed for {mail['id']}: {str(e)[:200]} — will retry next run")
            continue
        new_ids.add(mail["id"])

        short_id = mail["id"][:8]

        # ─── Path 2: new shoot inquiry → start autonomous flow ───────────
        if shoot_flow.is_shoot_inquiry(mail["subject"], mail["body"]):
            try:
                conv = shoot_flow.start_conversation(mail, api_key)
                conversations[thread_id] = conv
                shoot_flow.save_conversations(conversations)
                log.info(f"  Started shoot flow — replied to client autonomously")
                # Light heads-up to Kayzee
                shoot_flow.send_telegram(
                    f"📸 New shoot inquiry from {shoot_flow._escape(mail['from'])}\n"
                    f"Subject: {shoot_flow._escape(mail['subject'])}\n\n"
                    f"I'm handling the back-and-forth. Will send the full summary when ready."
                )
            except Exception as e:
                log.error(f"  Shoot start failed: {str(e)[:200]}")
            continue

        # ─── Path 3: not important → silently skip ───────────────────────
        if not result.get("important"):
            log.info(f"  Skipped: {result.get('reason')}")
            continue

        # ─── Path 4: regular important email → draft for Kayzee's approval ─
        draft = result.get("draft", "")
        to_address = extract_email_address(mail["from"])

        pending[mail["id"]] = {
            "to":        to_address,
            "subject":   mail["subject"],
            "thread_id": thread_id,
            "draft":     draft,
            "status":    "pending",
        }
        save_json(config.PENDING_REPLIES, pending)

        msg = (
            f"📧 <b>NEW EMAIL</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>From:</b> {escape_html(mail['from'])}\n"
            f"<b>Subject:</b> {escape_html(mail['subject'])}\n"
            f"<b>Why it matters:</b> {escape_html(result.get('reason', ''))}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"✍️ <b>SUGGESTED REPLY</b>\n"
            f"{escape_html(draft)}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ Reply <b>send</b> to send this\n"
            f"❌ Reply <b>skip</b> to ignore\n"
            f"✏️ Or just tell me what to change\n\n"
            f"<i>ref: {short_id}</i>"
        )
        try:
            send_tg(tg["bot_token"], tg["chat_id"], msg)
            log.info(f"  Notified on Telegram")
        except Exception as e:
            log.error(f"  Telegram failed: {e}")

    if new_ids:
        processed.update(new_ids)
        save_json(config.PROCESSED_EMAILS, list(processed))

    if not new_ids:
        log.info("No new emails.")

if __name__ == "__main__":
    main()
