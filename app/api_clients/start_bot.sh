#!/usr/bin/env bash
# Start the Telegram bot in the background
VENV="/Users/kshitizmittal/.openclaw/venv/bin/python3"
BOT="/Users/kshitizmittal/.openclaw/workspace/api_clients/telegram_bot.py"
LOG="/Users/kshitizmittal/.openclaw/logs/telegram_bot.log"
PID_FILE="/Users/kshitizmittal/.openclaw/tmp/telegram_bot.pid"

mkdir -p "$(dirname "$LOG")" "$(dirname "$PID_FILE")"

# Kill existing if running
if [[ -f "$PID_FILE" ]]; then
    OLD_PID=$(cat "$PID_FILE")
    kill "$OLD_PID" 2>/dev/null || true
fi

cd /Users/kshitizmittal/.openclaw/workspace/api_clients
nohup "$VENV" "$BOT" >> "$LOG" 2>&1 &
echo $! > "$PID_FILE"
echo "Bot started (PID: $!). Logs: $LOG"
