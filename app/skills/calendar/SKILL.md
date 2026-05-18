# Calendar Skill

**Description**
Read and create Google Calendar events from chat.

**Commands**
- `list` — next 10 upcoming events
- `today` — today's events
- `week` — next 7 days
- `add "Title" "YYYY-MM-DD HH:MM" "YYYY-MM-DD HH:MM"` — create event

**Script path**
`/Users/kshitizmittal/.openclaw/workspace/api_clients/calendar_api.py`

**Run via**
```bash
/Users/kshitizmittal/.openclaw/venv/bin/python3 /Users/kshitizmittal/.openclaw/workspace/api_clients/calendar_api.py <command> [args]
```

**First run**
Will open a browser for Google OAuth (Calendar scope). Token saved to `~/.openclaw/secrets/calendar_token.json`.

**Requirements**
- Google Calendar API enabled in `sassy-claw` Cloud project
- `calendar` scope added to OAuth consent screen
- Reuses existing `gmail_credentials.json` (same OAuth client)
