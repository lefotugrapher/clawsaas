#!/usr/bin/env python3
"""
Confirm or decline a shoot booking.
Usage:
  shoot_confirm.py confirm <thread_id_prefix>
  shoot_confirm.py decline <thread_id_prefix>

On confirm: adds 1-hour event to Google Calendar, sends final email to client.
On decline: sends polite decline email to client.
"""
import sys, json, subprocess, re, logging
from datetime import datetime, timedelta
import config
import shoot_flow
from gmail_send import send_reply
from openai import OpenAI

log = logging.getLogger("shoot_confirm")
log.setLevel(logging.INFO)
log.propagate = False
if not log.handlers:
    _h = logging.FileHandler(f"{config.LOGS}/shoot_confirm.log")
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(_h)


def find_conv(thread_prefix, conversations):
    for tid, conv in conversations.items():
        if tid.startswith(thread_prefix):
            return tid, conv
    return None, None


def parse_datetime_with_llm(datetime_str, api_key):
    """Use LLM to parse 'next Tuesday 3pm' into ISO format."""
    today = datetime.now().strftime("%Y-%m-%d (%A)")
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    prompt = f"""Today is {today}. Convert this datetime to ISO format: "{datetime_str}"

Return ONLY a string in format "YYYY-MM-DD HH:MM" (24h). If ambiguous, pick the next reasonable upcoming time. If you cannot parse it at all, return "UNCLEAR"."""
    for model in config.OPENROUTER_FALLBACKS:
        try:
            r = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                timeout=20,
            )
            text = r.choices[0].message.content.strip().strip('"').strip("'")
            m = re.search(r"\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2}", text)
            if m:
                return m.group(0)
            return None
        except Exception:
            continue
    return None


def craft_confirmation_email(conv, api_key):
    a = conv["answers"]
    prompt = f"""You are Clawsassy, Kayzee's AI assistant. Write a warm final confirmation email to the client confirming their shoot booking.

Details:
- Purpose: {a.get('purpose')}
- Location: {a.get('location')}
- Date/Time: {a.get('datetime')}
- Duration: {a.get('duration')}
- Special requests: {a.get('special_requests')}
- Price: €{config.SHOOT_PRICE_EUR}

Confirm everything, say Kayzee will be there, and mention you've added it to the calendar. 4-5 sentences. Sign off as "Clawsassy (Kayzee's AI assistant)". No subject line."""

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    for model in config.OPENROUTER_FALLBACKS:
        try:
            r = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                timeout=30,
            )
            return r.choices[0].message.content.strip()
        except Exception:
            continue
    raise RuntimeError("All models failed")


def craft_decline_email(conv, api_key):
    prompt = f"""You are Clawsassy, Kayzee's AI assistant. Write a polite, brief email declining a shoot booking.

The client asked for a shoot for: {conv['answers'].get('purpose', 'something')}.

Apologise, say Kayzee isn't available for this one, wish them well. 2-3 sentences. Sign off as "Clawsassy (Kayzee's AI assistant)". No subject line."""

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    for model in config.OPENROUTER_FALLBACKS:
        try:
            r = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                timeout=20,
            )
            return r.choices[0].message.content.strip()
        except Exception:
            continue
    raise RuntimeError("All models failed")


def get_api_key():
    with open(config.AUTH_PROFILES) as f:
        return json.load(f)["profiles"]["openrouter:default"]["key"]


def confirm(thread_prefix):
    conversations = shoot_flow.load_conversations()
    tid, conv = find_conv(thread_prefix, conversations)
    if not conv:
        log.error(f"No conversation found for prefix {thread_prefix}")
        print(f"No shoot booking found for: {thread_prefix}")
        return

    api_key = get_api_key()
    a = conv["answers"]

    # Parse datetime
    iso = parse_datetime_with_llm(a.get("datetime", ""), api_key)
    if not iso:
        print(f"Could not parse date/time '{a.get('datetime')}'. Calendar event skipped.")
        log.warning(f"Datetime parse failed for {tid}")
    else:
        dt = datetime.strptime(iso, "%Y-%m-%d %H:%M")
        end = dt + timedelta(hours=config.SHOOT_DURATION_HOURS)
        title = f"Shoot — {a.get('purpose', 'booking')}"
        try:
            subprocess.run([
                config.VENV_PYTHON,
                f"{config.WORKSPACE}/calendar_api.py",
                "add", title,
                dt.strftime("%Y-%m-%d %H:%M"),
                end.strftime("%Y-%m-%d %H:%M"),
            ], check=True)
            log.info(f"Calendar event added: {title} at {iso}")
            print(f"Calendar event added: {title} at {iso}")
        except Exception as e:
            log.error(f"Calendar add failed: {e}")
            print(f"Calendar add failed: {e}")

    # Send confirmation email
    try:
        body = craft_confirmation_email(conv, api_key)
        send_reply(conv["to"], conv["subject"], body, tid)
        log.info(f"Confirmation email sent to {conv['to']}")
        print(f"Confirmation email sent to {conv['to']}")
    except Exception as e:
        log.error(f"Confirmation email failed: {e}")
        print(f"Confirmation email failed: {e}")
        return

    conv["status"] = "confirmed"
    shoot_flow.save_conversations(conversations)
    shoot_flow.send_telegram(
        f"✅ Shoot booked!\nClient: {shoot_flow._escape(conv['from'])}\nWhen: {shoot_flow._escape(a.get('datetime', '-'))}\nAdded to calendar."
    )


def decline(thread_prefix):
    conversations = shoot_flow.load_conversations()
    tid, conv = find_conv(thread_prefix, conversations)
    if not conv:
        print(f"No shoot booking found for: {thread_prefix}")
        return

    api_key = get_api_key()
    try:
        body = craft_decline_email(conv, api_key)
        send_reply(conv["to"], conv["subject"], body, tid)
        log.info(f"Decline email sent to {conv['to']}")
        print(f"Decline email sent to {conv['to']}")
    except Exception as e:
        log.error(f"Decline failed: {e}")
        print(f"Decline failed: {e}")
        return

    conv["status"] = "declined"
    shoot_flow.save_conversations(conversations)
    shoot_flow.send_telegram(f"❌ Shoot declined.\nClient: {shoot_flow._escape(conv['from'])}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    action, prefix = sys.argv[1], sys.argv[2]
    if action == "confirm":
        confirm(prefix)
    elif action == "decline":
        decline(prefix)
    else:
        print("Unknown action. Use 'confirm' or 'decline'.")
        sys.exit(1)
