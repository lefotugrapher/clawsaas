#!/usr/bin/env bash
set -euo pipefail
SECRETS="${HOME}/.openclaw/secrets/telegram.json"

BOT_TOKEN=$(python3 -c "import json; d=json.load(open('${SECRETS}')); print(d['bot_token'])")
CHAT_ID=$(python3 -c "import json; d=json.load(open('${SECRETS}')); print(d['chat_id'])")

MESSAGE="${1:-}"
if [[ -z "$MESSAGE" ]]; then
  echo "No message supplied"
  exit 1
fi

curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
  -d chat_id="${CHAT_ID}" \
  -d text="${MESSAGE}" > /dev/null
