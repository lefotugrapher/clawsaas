"""
Autonomous shoot-booking flow.

When a client emails about a shoot, Clawsassy handles
the conversation autonomously — asking purpose, location, date/time, duration,
special requests — without bothering Kayzee.

Once all details are collected, sends a summary to Kayzee on Telegram for
yes/no approval before calendar event + final confirmation email.
"""
import json, os, re, urllib.parse, urllib.request, logging
from openai import OpenAI
import config
from gmail_send import send_reply

log = logging.getLogger(__name__)


# ─── State persistence ─────────────────────────────────────────────

def load_conversations():
    if os.path.exists(config.SHOOT_CONVERSATIONS):
        with open(config.SHOOT_CONVERSATIONS) as f:
            return json.load(f)
    return {}


def save_conversations(data):
    with open(config.SHOOT_CONVERSATIONS, "w") as f:
        json.dump(data, f, indent=2)


# ─── Detection ─────────────────────────────────────────────────────

def is_shoot_inquiry(subject, body):
    text = f"{subject} {body}".lower()
    return any(kw in text for kw in config.SHOOT_KEYWORDS)


def find_active_conversation(thread_id, conversations):
    return conversations.get(thread_id)


# ─── LLM helpers ───────────────────────────────────────────────────

def _call_llm(api_key, prompt, max_tokens=400):
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    for model in config.OPENROUTER_FALLBACKS:
        try:
            r = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                timeout=30,
            )
            return r.choices[0].message.content.strip()
        except Exception as e:
            log.warning(f"shoot_flow: model {model} failed: {str(e)[:100]}")
    raise RuntimeError("All models failed in shoot_flow")


def extract_all_answers(client_reply, api_key):
    """Use LLM to extract ALL 5 answers from a single client reply."""
    prompt = f"""A client is booking a photo/video shoot. They replied to an email asking 5 questions:
1. What is the shoot for? (purpose)
2. Location (full address)
3. Date and time
4. Duration (hours)
5. Special requests

Client's reply:
\"\"\"
{client_reply}
\"\"\"

Extract their answers as JSON in this exact format:
{{
  "purpose": "...",
  "location": "...",
  "datetime": "...",
  "duration": "...",
  "special_requests": "..."
}}

Rules:
- If an answer is missing or unclear, use "MISSING"
- Keep each value short and clean (a phrase, not a sentence)
- Return ONLY the JSON, no other text"""

    text = _call_llm(api_key, prompt, max_tokens=400)
    # Strip code fences and extract JSON
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    return json.loads(text)


def craft_opening_message(client_message, api_key):
    """Initial reply asking ALL 5 questions in one go."""
    prompt = f"""Your name is Clawsassy (exact spelling — never Clawsawesome or any variation). You are Kayzee's personal AI assistant. A client just emailed about a shoot:

"{client_message}"

Write a warm email reply that:
1. Briefly introduces yourself as Clawsassy, Kayzee's AI assistant who handles bookings
2. Says you're excited to help and need a few details to lock it in
3. Asks ALL of these questions in a clean numbered list:
   1. What is the shoot for? (e.g. marketing, event, portrait, product)
   2. Where would you like it? (full address)
   3. Preferred date and time?
   4. How long do you need? (in hours)
   5. Any special requests? (props, permits, specific shots, etc.)
4. Mention that the shoot is €300 for 1 hour
5. Says they can answer all in one reply

Sign off as "Clawsassy". Keep tone friendly and clean. No subject line."""
    return _call_llm(api_key, prompt, max_tokens=400)


def craft_followup_for_missing(missing_keys, api_key):
    """Follow-up email asking for just the missing answers."""
    questions = {
        "purpose":          "What is the shoot for? (marketing, event, portrait, product?)",
        "location":         "Where would you like the shoot? (full address)",
        "datetime":         "Preferred date and time?",
        "duration":         "How long do you need? (in hours)",
        "special_requests": "Any special requests? (props, permits, specific shots, etc.)",
    }
    missing_qs = "\n".join(f"- {questions[k]}" for k in missing_keys)
    prompt = f"""You are Clawsassy. The client missed some details in their last reply. Write a brief, friendly follow-up email asking ONLY for these missing items:

{missing_qs}

Keep it under 4 sentences. Sign off as "Clawsassy". No subject line."""
    return _call_llm(api_key, prompt, max_tokens=250)


# ─── Flow orchestration ───────────────────────────────────────────

def start_conversation(mail, api_key):
    """Create a new shoot conversation — send ONE email with all 5 questions."""
    opening = craft_opening_message(mail["body"][:500], api_key)
    to_address = _extract_email(mail["from"])
    subject = mail["subject"]

    send_reply(to_address, subject, opening, mail.get("thread_id"))
    log.info(f"shoot_flow: started conversation with {to_address} (all questions in one email)")

    return {
        "to":        to_address,
        "from":      mail["from"],
        "subject":   subject,
        "thread_id": mail["thread_id"],
        "status":    "in_progress",
        "answers":   {},
        "history":   [
            {"role": "client", "text": mail["body"][:1000]},
            {"role": "us",     "text": opening},
        ],
    }


def continue_conversation(conv, client_reply, api_key):
    """Parse client reply for all 5 answers. Send summary if complete, otherwise ask for missing only."""
    all_keys = ["purpose", "location", "datetime", "duration", "special_requests"]

    try:
        extracted = extract_all_answers(client_reply, api_key)
    except Exception as e:
        log.error(f"shoot_flow: extraction failed: {e}")
        raise

    # Merge new answers, keeping any prior ones we already have
    for k in all_keys:
        val = extracted.get(k, "MISSING")
        if val and val.upper() != "MISSING":
            conv["answers"][k] = val

    conv["history"].append({"role": "client", "text": client_reply[:1000]})

    missing = [k for k in all_keys if k not in conv["answers"] or not conv["answers"][k]]

    # All answers in → ready for Kayzee
    if not missing:
        conv["status"] = "awaiting_approval"
        log.info(f"shoot_flow: all answers collected for {conv['to']}")
        return conv, "complete"

    # Some missing → send a brief follow-up asking only for those
    followup = craft_followup_for_missing(missing, api_key)
    send_reply(conv["to"], conv["subject"], followup, conv["thread_id"])
    conv["history"].append({"role": "us", "text": followup})
    log.info(f"shoot_flow: asked for missing {missing} from {conv['to']}")
    return conv, "in_progress"


def build_summary_for_kayzee(conv):
    """Telegram summary asking Kayzee to confirm booking."""
    answers = conv["answers"]
    return (
        f"📸 <b>SHOOT BOOKING — READY FOR APPROVAL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Client:</b> {_escape(conv['from'])}\n"
        f"<b>Subject:</b> {_escape(conv['subject'])}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Purpose:</b> {_escape(answers.get('purpose', '-'))}\n"
        f"<b>Location:</b> {_escape(answers.get('location', '-'))}\n"
        f"<b>Date/Time:</b> {_escape(answers.get('datetime', '-'))}\n"
        f"<b>Duration:</b> {_escape(answers.get('duration', '-'))}\n"
        f"<b>Special:</b> {_escape(answers.get('special_requests', '-'))}\n"
        f"<b>Price:</b> €{config.SHOOT_PRICE_EUR}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Reply <b>confirm shoot {conv['thread_id'][:8]}</b> to book + add to calendar\n"
        f"❌ Reply <b>decline shoot {conv['thread_id'][:8]}</b> to cancel\n\n"
        f"<i>thread: {conv['thread_id'][:8]}</i>"
    )


# ─── Utilities ─────────────────────────────────────────────────────

def _extract_email(from_field):
    m = re.search(r"<(.+?)>", from_field)
    return m.group(1) if m else from_field.strip()


def _escape(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def send_telegram(text):
    with open(config.TELEGRAM_SECRET) as f:
        tg = json.load(f)
    data = urllib.parse.urlencode({
        "chat_id":    tg["chat_id"],
        "text":       text,
        "parse_mode": "HTML",
    }).encode()
    url = f"https://api.telegram.org/bot{tg['bot_token']}/sendMessage"
    urllib.request.urlopen(url, data, timeout=10)
