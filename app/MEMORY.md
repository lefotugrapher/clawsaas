# MEMORY.md - Long Term Memory

## What I Know

### The Product
OpenClaw OS is Kshitiz's project — an AI operations platform for local service businesses. Core idea: busy owners miss leads because they can't sit at laptops. OpenClaw monitors their digital channels, drafts responses, and lets them manage everything from their phone via Telegram.

### Current Stack (as of May 2026)
- **Email:** Gmail API → Claude judges importance → Telegram approval → send reply
- **Calendar:** Google Calendar API (list/search/add events)
- **Notifications:** Telegram bot (OpenClaw native channel)
- **AI:** OpenRouter (claude-3.5-haiku for fast tasks)
- **Automation:** OpenClaw cron (gmail_watch every 1 min, daily briefing 7 AM)
- **Scripts:** All in `~/.openclaw/workspace/api_clients/`

### Credentials
- Gmail + Calendar OAuth: shared `gmail_credentials.json`, separate token files
- Telegram: configured in OpenClaw natively (bot: @clawsassy_bot)
- OpenRouter: stored in `~/.openclaw/agents/main/agent/auth-profiles.json`

### Known Issues (resolved as of May 17)
- Gmail token was regenerated after invalid scope error
- Telegram bot.py removed — OpenClaw handles Telegram natively now
- All scripts updated to use `config.py` for centralised paths

### What's Next
- Instagram DMs integration
- Google Reviews responder
- Health monitoring / failure alerts

### Shoot Booking Workflow
**Goal:** When a client asks about a shoot (photo/video/film etc.), I will collect all necessary details before booking.

**Step‑by‑step Q&A:**
1. *What is the shoot about?* (purpose/brief)
2. *Where will it take place?* (full address)
3. *When will it happen?* (date & time)
4. *How long will it last?* (estimated hours)
5. *What’s the budget?* (will be charged €300)
6. *Any special requests or requirements?*
7. *Summarise* and ask for confirmation to add the event to the calendar.

After confirmation, I’ll add a 1‑hour event to Google Calendar and set the cost at €300. I can manage the communication thread, draft replies, and include the "Clawsassy" personal assistant introduction.

### Email Permissions
I have your permission to send emails on your behalf for shoot appointments only, until you revoke or modify this instruction.
