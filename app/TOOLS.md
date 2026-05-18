# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

## Available Local Scripts

These scripts give you direct access to my Gmail, Telegram, and Google Calendar. Run them via Bash. Always use the venv python: `/Users/kshitizmittal/.openclaw/venv/bin/python3`.

### Google Calendar
Script: `/Users/kshitizmittal/.openclaw/workspace/api_clients/calendar_api.py`

```bash
# List next 10 upcoming events
/Users/kshitizmittal/.openclaw/venv/bin/python3 /Users/kshitizmittal/.openclaw/workspace/api_clients/calendar_api.py list

# Today's events
/Users/kshitizmittal/.openclaw/venv/bin/python3 /Users/kshitizmittal/.openclaw/workspace/api_clients/calendar_api.py today

# Next 7 days
/Users/kshitizmittal/.openclaw/venv/bin/python3 /Users/kshitizmittal/.openclaw/workspace/api_clients/calendar_api.py week

# Search ALL events by keyword (past + future) — use for questions like "when was my first date with aups"
/Users/kshitizmittal/.openclaw/venv/bin/python3 /Users/kshitizmittal/.openclaw/workspace/api_clients/calendar_api.py search "aups"

# Add an event
/Users/kshitizmittal/.openclaw/venv/bin/python3 /Users/kshitizmittal/.openclaw/workspace/api_clients/calendar_api.py add "Title" "2026-05-17 14:00" "2026-05-17 15:00"
```

### Gmail
- Read unread: `/Users/kshitizmittal/.openclaw/workspace/api_clients/gmail_poll.py`
- Watch important emails + auto-draft + Telegram notify: `/Users/kshitizmittal/.openclaw/workspace/api_clients/gmail_important_watch.py` (runs every minute via cron)
- Send reply: `/Users/kshitizmittal/.openclaw/workspace/api_clients/gmail_send.py <to> <subject> <body>`

### Telegram
- Send a message: `bash /Users/kshitizmittal/.openclaw/workspace/api_clients/telegram_send.sh "your message"`
- Daily briefing (runs at 7 AM via cron): `/Users/kshitizmittal/.openclaw/workspace/api_clients/daily_briefing.py`

### Scheduled jobs (launchd — macOS native scheduler)

Why launchd instead of OpenClaw cron: OpenClaw cron requires going through an AI agent (agentTurn), which is too slow/unreliable for 1-minute intervals on the free model tier. Launchd is Apple's system scheduler — rock solid, runs in background, no LLM involved.

Active jobs:
- `com.openclaw.gmailwatch` — runs gmail_important_watch.py every 60 seconds
- `com.openclaw.dailybriefing` — runs daily_briefing.py at 7:00 AM

Manage via launchctl:
```bash
# Check status of all openclaw jobs
launchctl list | grep openclaw

# Stop a job
launchctl unload /Users/kshitizmittal/Library/LaunchAgents/com.openclaw.gmailwatch.plist

# Start a job
launchctl load /Users/kshitizmittal/Library/LaunchAgents/com.openclaw.gmailwatch.plist

# Force run a job now (without waiting for next interval)
launchctl start com.openclaw.gmailwatch

# View logs
tail -20 /Users/kshitizmittal/.openclaw/logs/gmail_watch.log
tail -20 /Users/kshitizmittal/.openclaw/logs/launchd_gmail.err
```

OpenClaw still monitors health via the `health_check` cron job (every 10 min) which alerts on Telegram if anything stops working.

### Instagram DMs (@lefotugrapher)

Watcher: `/Users/kshitizmittal/.openclaw/workspace/api_clients/instagram_watch.py` — runs every 60s via launchd (`com.openclaw.instagramwatch`).

Same flow as Gmail:
1. Polls Instagram Graph API for new DMs
2. AI judges importance + drafts a casual IG-style reply (no email sign-offs)
3. Sends notification + draft to Telegram
4. Kayzee approves with `send dm <ref>` / `skip dm <ref>`

To send an approved DM:
```bash
/Users/kshitizmittal/.openclaw/venv/bin/python3 /Users/kshitizmittal/.openclaw/workspace/api_clients/instagram_send.py <recipient_id> "<text>"
```

Pending DMs live in `.pending_dms.json` (keyed by message_id). Each entry has `from`, `from_id` (use as recipient_id when sending), `conv_id`, `message`, `draft`, `status`.

Secrets: `~/.openclaw/secrets/instagram.json` (access_token, ig_user_id).

### Shoot Booking Flow (autonomous)

When a client emails about a shoot (keywords: shoot, photo, video, film, session, photoshoot, filming), Clawsassy AUTOMATICALLY handles the back-and-forth — asks purpose, location, date/time, duration, special requests. Kayzee is NOT bothered until all details are collected.

When Kayzee receives the summary on Telegram and replies `confirm shoot <thread_id>`:
```bash
/Users/kshitizmittal/.openclaw/venv/bin/python3 /Users/kshitizmittal/.openclaw/workspace/api_clients/shoot_confirm.py confirm <thread_id>
```

Or `decline shoot <thread_id>`:
```bash
/Users/kshitizmittal/.openclaw/venv/bin/python3 /Users/kshitizmittal/.openclaw/workspace/api_clients/shoot_confirm.py decline <thread_id>
```

Active conversations are tracked in `/Users/kshitizmittal/.openclaw/workspace/api_clients/.shoot_conversations.json`.

Price per shoot: €300. Default duration: 1 hour.

### Pending email drafts
File: `/Users/kshitizmittal/.openclaw/workspace/api_clients/.pending_replies.json`

Each entry has: `to`, `subject`, `thread_id`, `draft`, `status` (pending/sent/skipped). You can read it directly to answer questions like "what drafts are waiting".

### Secrets
- Gmail OAuth creds: `~/.openclaw/secrets/gmail_credentials.json` (also used by Calendar)
- Gmail token: `~/.openclaw/secrets/gmail_token.json`
- Calendar token: `~/.openclaw/secrets/calendar_token.json`
- Telegram: `~/.openclaw/secrets/telegram.json`

---

Add whatever helps you do your job. This is your cheat sheet.

## Related

- [Agent workspace](/concepts/agent-workspace)
