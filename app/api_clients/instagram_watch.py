#!/usr/bin/env python3
"""
Watch Instagram DMs for the @lefotugrapher account.
Same flow as Gmail: AI judges importance, drafts reply, Telegram approval.

Also detects shoot inquiries and routes to shoot_flow (just like Gmail does).
"""
import json, os, sys, re, urllib.request, urllib.parse, logging
from openai import OpenAI
import config

log = logging.getLogger("instagram_watch")
log.setLevel(logging.INFO)
log.propagate = False
if not log.handlers:
    _h = logging.FileHandler(f"{config.LOGS}/instagram_watch.log")
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(_h)


# ─── Helpers ───────────────────────────────────────────────────────

def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def get_ig_creds():
    with open(config.INSTAGRAM_SECRET) as f:
        return json.load(f)

def get_tg_creds():
    with open(config.TELEGRAM_SECRET) as f:
        return json.load(f)

def get_openrouter_key():
    with open(config.AUTH_PROFILES) as f:
        return json.load(f)["profiles"]["openrouter:default"]["key"]

def escape_html(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ─── Instagram Graph API ────────────────────────────────────────────

def graph_get(endpoint, params, token):
    params["access_token"] = token
    url = f"https://graph.instagram.com/{config.IG_GRAPH_VERSION}/{endpoint}?{urllib.parse.urlencode(params)}"
    r = urllib.request.urlopen(url, timeout=20)
    return json.loads(r.read())

def fetch_conversations(token, ig_user_id):
    """Fetch recent conversations (DM threads)."""
    return graph_get(
        f"{ig_user_id}/conversations",
        {"fields": "messages.limit(5){from,message,created_time,id}", "limit": 20},
        token,
    )

def fetch_username(user_id, token):
    """Resolve a sender's IG user ID to a username."""
    try:
        r = graph_get(user_id, {"fields": "username"}, token)
        return r.get("username", user_id)
    except Exception:
        return user_id


# ─── LLM ───────────────────────────────────────────────────────────

def judge_and_draft(sender, message, api_key):
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    prompt = f"""You are an Instagram assistant for Kayzee (@lefotugrapher — a photographer). Read this DM and decide if it needs a reply.

From: @{sender}
Message: {message}

Respond in this exact JSON format:
{{
  "important": true or false,
  "reason": "one sentence",
  "draft": "reply if important, else empty string"
}}

Rules for the draft:
- Casual, Instagram tone — short, no email-style sign-offs
- Never use [Your Name] or placeholders
- Don't sign with "Kayzee" — IG DMs aren't emails
- Max 2-3 sentences

Skip (not important): generic spam, follower-train requests, random emoji-only messages, automated bot DMs.

Only return the JSON."""

    last_err = None
    for model in config.OPENROUTER_FALLBACKS:
        try:
            r = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                timeout=30,
            )
            text = r.choices[0].message.content.strip()
            text = re.sub(r"^```json\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if m: text = m.group(0)
            return json.loads(text)
        except Exception as e:
            last_err = e
            log.warning(f"  Model {model} failed: {str(e)[:100]}")
    raise RuntimeError(f"All models failed: {last_err}")


# ─── Telegram ──────────────────────────────────────────────────────

def send_tg(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }).encode()
    urllib.request.urlopen(url, data, timeout=10)


# ─── Main loop ─────────────────────────────────────────────────────

def main():
    try:
        ig = get_ig_creds()
        tg = get_tg_creds()
        api_key = get_openrouter_key()
    except Exception as e:
        log.error(f"Startup failed: {e}")
        sys.exit(1)

    processed = set(load_json(config.IG_PROCESSED, []))
    pending = load_json(config.IG_PENDING, {})
    new_ids = set()

    try:
        convs = fetch_conversations(ig["access_token"], ig["ig_user_id"])
    except Exception as e:
        log.error(f"Failed to fetch conversations: {e}")
        sys.exit(1)

    my_id_short = ig["ig_user_id"]

    for conv in convs.get("data", []):
        messages = conv.get("messages", {}).get("data", [])
        # Find the latest message NOT from me
        for msg in messages:
            sender = msg.get("from", {})
            if str(sender.get("id")) == str(my_id_short):
                continue
            msg_id = msg["id"]
            if msg_id in processed:
                continue

            text = msg.get("message", "")
            if not text:
                processed.add(msg_id)  # nothing to process (likely media)
                continue

            sender_username = sender.get("username") or fetch_username(sender.get("id"), ig["access_token"])
            log.info(f"Processing DM from @{sender_username}: {text[:60]}")

            try:
                result = judge_and_draft(sender_username, text, api_key)
            except Exception as e:
                log.error(f"  Claude failed: {str(e)[:200]} — will retry next run")
                continue

            new_ids.add(msg_id)

            if not result.get("important"):
                log.info(f"  Skipped: {result.get('reason')}")
                continue

            short_id = msg_id[-8:]
            pending[msg_id] = {
                "from":     sender_username,
                "from_id":  sender.get("id"),
                "conv_id":  conv["id"],
                "message":  text,
                "draft":    result.get("draft", ""),
                "status":   "pending",
            }
            save_json(config.IG_PENDING, pending)

            tg_msg = (
                f"📸 <b>NEW INSTAGRAM DM</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"<b>From:</b> @{escape_html(sender_username)}\n"
                f"<b>Message:</b> {escape_html(text)}\n"
                f"<b>Why it matters:</b> {escape_html(result.get('reason', ''))}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"✍️ <b>SUGGESTED REPLY</b>\n"
                f"{escape_html(result.get('draft', ''))}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ Reply <b>send dm {short_id}</b> to send\n"
                f"❌ Reply <b>skip dm {short_id}</b> to ignore\n"
                f"✏️ Or tell me what to change\n\n"
                f"<i>ref: {short_id}</i>"
            )
            try:
                send_tg(tg["bot_token"], tg["chat_id"], tg_msg)
                log.info(f"  Notified on Telegram")
            except Exception as e:
                log.error(f"  Telegram failed: {e}")
            break  # only handle one new message per conversation per run

    if new_ids:
        processed.update(new_ids)
        save_json(config.IG_PROCESSED, list(processed))

    if not new_ids:
        log.info("No new DMs.")


if __name__ == "__main__":
    main()
