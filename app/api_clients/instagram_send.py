#!/usr/bin/env python3
"""Send an Instagram DM via Graph API."""
import sys, json, urllib.request, urllib.parse, logging
import config

log = logging.getLogger("instagram_send")
log.setLevel(logging.INFO)
log.propagate = False
if not log.handlers:
    _h = logging.FileHandler(f"{config.LOGS}/instagram_send.log")
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(_h)

def send_dm(recipient_id, text):
    with open(config.INSTAGRAM_SECRET) as f:
        ig = json.load(f)
    url = f"https://graph.instagram.com/{config.IG_GRAPH_VERSION}/{ig['ig_user_id']}/messages"
    payload = json.dumps({
        "recipient": {"id": recipient_id},
        "message": {"text": text},
    }).encode()
    req = urllib.request.Request(
        url + "?access_token=" + urllib.parse.quote(ig["access_token"]),
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    r = urllib.request.urlopen(req, timeout=20)
    result = json.loads(r.read())
    log.info(f"DM sent to {recipient_id}: {result}")
    return result

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: instagram_send.py <recipient_id> <text>")
        sys.exit(1)
    print(send_dm(sys.argv[1], sys.argv[2]))
