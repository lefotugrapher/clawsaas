# clawSaas — App Code

This folder contains the Python engine that powers clawSaas. It runs as a set of self-hosted scripts on your own Mac, scheduled by `launchd`, and uses Telegram as the user interface.

```
app/
├── api_clients/         — all the runtime scripts
│   ├── config.py
│   ├── gmail_important_watch.py
│   ├── gmail_send.py
│   ├── gmail_poll.py
│   ├── shoot_flow.py
│   ├── shoot_confirm.py
│   ├── calendar_api.py
│   ├── instagram_watch.py
│   ├── instagram_send.py
│   ├── daily_briefing.py
│   ├── health_check.py
│   ├── telegram_send.sh
│   └── start_bot.sh
├── skills/              — agent skill descriptions
└── *.md                 — persona files (IDENTITY, SOUL, USER, TOOLS, MEMORY, AGENTS)
```

## What it does

| File | Job |
|------|-----|
| `gmail_important_watch.py` | Polls Gmail every 60 s. LLM judges importance, drafts a reply, sends to Telegram for approval. Triggers `shoot_flow` for shoot inquiries. |
| `shoot_flow.py` | Autonomous email back-and-forth for shoot bookings. Asks all 5 questions in one go, extracts answers, surfaces a Telegram summary when complete. |
| `shoot_confirm.py` | When user confirms a shoot on Telegram, adds a 1-hour calendar event and sends a final confirmation email to the client. |
| `calendar_api.py` | List / search / add Google Calendar events. |
| `instagram_watch.py` | Same flow as Gmail, polling Instagram Graph API. |
| `instagram_send.py` | Send approved IG DM replies. |
| `daily_briefing.py` | 7 AM Telegram summary. |
| `health_check.py` | Every 10 minutes — checks tokens, launchd services, pending counts. Pages Telegram if anything is broken. |
| `gmail_send.py` | Send a Gmail reply. |
| `gmail_poll.py` | Simple inbox poll utility. |

## Prerequisites

- macOS with Python 3.12+
- A Python virtualenv with `google-auth`, `google-auth-oauthlib`, `google-api-python-client`, `openai`, `markdown`
- Google Cloud project with Gmail + Calendar APIs enabled and an OAuth Desktop client downloaded as `gmail_credentials.json`
- Meta Developer App with Instagram Business permissions, a long-lived IG access token
- Telegram bot token + chat ID
- An OpenRouter API key (free tier is enough)

## Secrets layout

All secrets live OUTSIDE the repo at `~/.openclaw/secrets/`:

```
~/.openclaw/secrets/
├── gmail_credentials.json  # OAuth client (Gmail + Calendar)
├── gmail_token.json        # Auto-generated on first run
├── calendar_token.json     # Auto-generated on first run
├── telegram.json           # {"bot_token": "…", "chat_id": "…"}
└── instagram.json          # {"access_token": "…", "ig_user_id": "…"}
```

The OpenRouter key is read from `~/.openclaw/agents/main/agent/auth-profiles.json` (configured by the agent runtime).

These paths are all defined in `api_clients/config.py` — adjust to match your install.

## Running it

```bash
# 1. Create the venv and install deps
python3 -m venv ~/.openclaw/venv
~/.openclaw/venv/bin/pip install google-auth google-auth-oauthlib google-api-python-client openai markdown markdown-pdf

# 2. Drop your gmail_credentials.json into ~/.openclaw/secrets/
mkdir -p ~/.openclaw/secrets
mv ~/Downloads/client_secret_*.json ~/.openclaw/secrets/gmail_credentials.json
chmod 600 ~/.openclaw/secrets/gmail_credentials.json

# 3. First-time OAuth (opens browser)
~/.openclaw/venv/bin/python3 api_clients/gmail_important_watch.py

# 4. Add launchd jobs — see ~/Library/LaunchAgents/com.openclaw.*.plist
```

## Status

| Component | State |
|-----------|-------|
| Gmail watcher + AI triage | live |
| Shoot booking flow | live |
| Calendar integration | live |
| Daily 7 AM briefing | live |
| Health monitoring | live |
| Instagram DM watcher | live in dev mode, awaiting Meta App Review |

## License

MIT (planned). Open-core — the engine is free and self-hostable.
