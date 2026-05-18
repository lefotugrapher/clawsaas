#!/usr/bin/env python3
"""
Health check — runs every 10 min via cron.
Alerts on Telegram if anything is broken.
"""
import os, json, urllib.request, urllib.parse, logging
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import config

log = logging.getLogger("health_check")
log.setLevel(logging.INFO)
log.propagate = False
if not log.handlers:
    _h = logging.FileHandler(f"{config.LOGS}/health_check.log")
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(_h)

def send_tg(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    urllib.request.urlopen(url, data, timeout=10)

def check_gmail_token():
    try:
        creds = Credentials.from_authorized_user_file(config.GMAIL_TOKEN, config.GMAIL_SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        return True, None
    except Exception as e:
        return False, str(e)

def check_log_activity(log_path, max_age_minutes=5):
    """Check if a log file was written to recently."""
    if not os.path.exists(log_path):
        return False, "Log file missing"
    age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(log_path))
    if age > timedelta(minutes=max_age_minutes):
        return False, f"Last activity {int(age.total_seconds() / 60)} min ago"
    return True, None

def check_launchd_services():
    """Check that launchd services are loaded."""
    import subprocess
    services = ["com.openclaw.gmailwatch", "com.openclaw.dailybriefing"]
    missing = []
    try:
        result = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=5)
        for svc in services:
            if svc not in result.stdout:
                missing.append(svc)
    except Exception as e:
        return False, f"launchctl check failed: {e}"
    if missing:
        return False, f"Services not loaded: {', '.join(missing)}"
    return True, None

def check_pending_count():
    """Warn if too many drafts are stuck pending."""
    if not os.path.exists(config.PENDING_REPLIES):
        return True, None
    with open(config.PENDING_REPLIES) as f:
        pending = json.load(f)
    stuck = [p for p in pending.values() if p.get("status") == "pending"]
    if len(stuck) > 10:
        return False, f"{len(stuck)} drafts stuck pending — check your Telegram"
    return True, None

def main():
    with open(config.TELEGRAM_SECRET) as f:
        tg = json.load(f)

    issues = []

    ok, err = check_gmail_token()
    if not ok:
        issues.append(f"Gmail token broken: {err}")

    ok, err = check_log_activity(f"{config.LOGS}/gmail_watch.log", max_age_minutes=5)
    if not ok:
        issues.append(f"Gmail watcher stale: {err}")

    ok, err = check_pending_count()
    if not ok:
        issues.append(err)

    ok, err = check_launchd_services()
    if not ok:
        issues.append(f"Launchd: {err}")

    if issues:
        msg = "OpenClaw health alert:\n" + "\n".join(f"- {i}" for i in issues)
        try:
            send_tg(tg["bot_token"], tg["chat_id"], msg)
            log.warning(f"Alert sent: {issues}")
        except Exception as e:
            log.error(f"Failed to send alert: {e}")
    else:
        log.info("All systems healthy.")

if __name__ == "__main__":
    main()
