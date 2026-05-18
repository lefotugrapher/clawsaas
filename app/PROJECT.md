# clawSaas — Project Context

> Single source of truth for what this app is, what it does, how it works, and where it's going. Use this when pitching, writing app review submissions, onboarding collaborators, or briefing a new AI agent.

---

## What it is

**clawSaas** is the AI sidekick your inbox has been begging for — an operations engine for local service businesses and creators who don't have time to live at a laptop.

It watches every channel a real business actually uses (Gmail, Instagram DMs, Google Calendar, customer reviews), drafts the replies, books the appointments, fends off the spam, and only buzzes you when a human decision is actually needed. You approve the things that need you from your phone. The boring stuff handles itself.

- **Product name:** clawSaas
- **Operating entity:** Kshitiz Mittal, sole trader (Dublin, Ireland)
- **Persona:** Clawsassy — sharp, direct, slightly playful AI assistant
- **Operator nickname:** Kayzee (the user)
- **Built:** May 2026, active development
- **Funding status:** Applying for Student Inc 2026 at DKIT (Dundalk Institute of Technology)

---

## The problem

For local brick-and-mortar businesses and lean startups, **missed notifications equal lost revenue**. Business owners are on their feet serving clients — not sitting at laptops.

- **Fragmented communication.** Leads and inquiries scatter across Instagram DMs, Gmail, Google Business Profile, Yelp.
- **Leaking funnel.** Inquiries go unanswered for hours; potential customers book elsewhere.
- **Reputation neglect.** Replying to Google reviews is critical for local SEO but is consistently neglected.

Existing tools (HubSpot, Hootsuite) are too heavy, too expensive, and assume the owner has time to sit at a dashboard. clawSaas is the opposite — it lives in your pocket and only surfaces what truly needs you.

---

## What it does today (May 2026)

### 1. Gmail watcher with AI triage
- Polls Gmail every 60 seconds via macOS launchd (chosen for reliability over agent-based cron).
- An LLM (Claude, Llama, Gemma — whichever responds via OpenRouter's free tier first) reads each unread email and decides whether it deserves a reply.
- For important mails, it drafts a personalised response and posts a notification to Telegram:

```
📧 NEW EMAIL
━━━━━━━━━━━━━━━━━━━━
From: Jane Doe
Subject: Booking enquiry
Why it matters: customer requesting availability
━━━━━━━━━━━━━━━━━━━━
✍️ SUGGESTED REPLY
Hi Jane! Thanks for reaching out…
Kayzee
━━━━━━━━━━━━━━━━━━━━
✅ Reply send to send this
❌ Reply skip to ignore
✏️ Or just tell me what to change

ref: 19e35efb
```

### 2. Autonomous shoot-booking flow
When a client emails about a photo, video or film shoot, clawSaas auto-replies, asking all five details in a single email: purpose, location, date and time, duration, special requests. Once the client replies, the LLM extracts every answer and surfaces a summary on Telegram for one-tap approval. On confirm, a one-hour event is automatically added to Google Calendar (at €300) and a confirmation email is sent. The whole back-and-forth happens without bothering Kayzee until the summary is ready.

### 3. Instagram DM watcher
- Same architecture as Gmail. Polls the Instagram Graph API every 60 seconds.
- Same AI triage, same Telegram approval flow, casual IG-style tone in drafts.
- Currently restricted to tester accounts (Meta dev-mode limitation). App Review submission in progress to unlock real-world traffic.

### 4. Google Calendar tools
- List upcoming events, fetch today and this week, search across all events by keyword, add events.
- Powers the shoot-booking flow and is exposed to the AI assistant for natural-language requests like *"when was my first date with Aups?"*

### 5. Daily 7 AM briefing
A short, conversational morning summary on Telegram: how many unread emails landed overnight, how many drafts are waiting for approval, how many replies you sent yesterday.

### 6. Health monitoring
A self-check job runs every 10 minutes and pages Telegram if Gmail tokens have expired, launchd services have stopped, or pending drafts have piled up. The system tells you it's broken before your customers do.

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    clawSaas Workspace                       │
│        ~/.openclaw/workspace/   (lives on user's Mac)       │
├────────────────────────────────────────────────────────────┤
│  Persona files     IDENTITY · SOUL · USER · TOOLS · MEMORY  │
│  Skills            calendar · gmail-poll · …                │
│  API clients       gmail_important_watch · daily_briefing   │
│                    shoot_flow · shoot_confirm · calendar    │
│                    instagram_watch · instagram_send         │
│                    gmail_send · health_check                │
├────────────────────────────────────────────────────────────┤
│  Schedulers                                                 │
│   • launchd: gmail_watch (60s), instagram_watch (60s),      │
│              daily_briefing (07:00)                         │
│   • OpenClaw cron: health_check (10 min)                    │
├────────────────────────────────────────────────────────────┤
│  External services                                          │
│   • Google APIs:   Gmail readonly / modify / send,          │
│                    Calendar                                 │
│   • Meta APIs:     Instagram Graph (business_basic,         │
│                    manage_messages, manage_comments)        │
│   • Telegram:      Bot API (sends notifications,            │
│                    OpenClaw natively handles user replies)  │
│   • OpenRouter:    LLM gateway → Llama 3.3, Gemma 4,        │
│                    GPT-OSS, Qwen3, Hermes 3, DeepSeek       │
│                    (free tier, with fallback chain)         │
└────────────────────────────────────────────────────────────┘
```

### Why launchd instead of agent-based cron?
Agent-based cron must go through an AI turn — too slow, too rate-limited for 1-minute intervals on a free LLM tier. macOS launchd runs Python scripts directly: no LLM in the hot path, sub-second startup, rock-solid. The agent-based scheduler still monitors everything via a 10-minute health check.

### Why polling instead of webhooks?
Webhooks would require a public HTTPS endpoint, app publication, and webhook signing. For a self-hosted Mac install, polling is simpler and the 60-second latency penalty is invisible to users.

---

## Tech stack

| Layer        | Choice                                                      |
|--------------|-------------------------------------------------------------|
| Runtime      | Python 3.14 in a local venv                                 |
| HTTP         | `urllib` (stdlib) + `google-api-python-client`              |
| AI client    | `openai` SDK pointed at OpenRouter (`base_url` override)    |
| OAuth        | `google-auth-oauthlib` for Google; manual token for Meta    |
| Persistence  | Flat JSON files under `~/.openclaw/workspace/api_clients/`  |
| Scheduling   | macOS `launchd` (production); agent cron (monitoring)       |
| UI           | Telegram (notifications + approval), no web dashboard       |
| Hosting      | Self-hosted on user's own Mac (no clawSaas server exists)   |

---

## Data we touch (for App Review)

| Permission                        | What we read                                            | Why                                            |
|-----------------------------------|---------------------------------------------------------|------------------------------------------------|
| `instagram_business_basic`        | Username, profile, follower count                       | Identify the connected account                 |
| `instagram_business_manage_messages` | Direct messages in the IG Business inbox             | Read incoming DMs, draft + send replies after explicit user approval on Telegram |
| `instagram_business_manage_comments` | Comments on the IG Business account's posts          | (Roadmap: respond to DMs from story replies / comment-funnels) |
| Gmail `readonly` + `modify` + `send` | Email content & metadata for unread mails            | Same flow as IG — draft, approve, send         |
| Google Calendar `calendar`        | Events on primary calendar                              | List, search, add events tied to bookings      |

### Where the data goes
- **Stored:** locally only, on the user's own Mac. No clawSaas server exists.
- **Transmitted:** to the LLM provider (OpenRouter → underlying providers like Anthropic, Meta, Google) to generate the draft. No long-term retention at the LLM provider.
- **Shared with third parties:** never.
- **Retention:** message IDs are cached locally to avoid duplicate notifications. Drafts are kept until the user sends, skips, or edits them.

---

## Roadmap

### Tier 1 — Currently shipping
- Gmail watcher with Telegram approval
- Shoot-booking conversation flow
- Google Calendar (list, search, add)
- Daily 7 AM briefing
- Instagram DM watcher (dev mode, awaiting App Review)
- Health monitoring with Telegram alerts

### Tier 2 — Next
- Meta App Review approval (in progress)
- Google Business Profile reviews — apply for API access, then build review responder
- Instagram comment monitoring with auto-replies for posts
- Story-reply funnel (story replies → DM auto-conversation)

### Tier 3 — Later
- WhatsApp Business API integration
- Yelp review monitoring
- Competitor monitoring (rating drops, promo shifts)
- Multi-account support (manage several businesses from one inbox)
- Mobile-first onboarding wizard (under 2 minutes from install to first reply)

---

## Business model

**Open-core SaaS.**

- **Open-source engine (free).** The base data-grabbing framework and the local agent run on the user's own machine. Developer trust, organic distribution, crowd-sourced maintenance of connectors.
- **Managed service (paid subscription).** For users who don't want to self-host: hosted infrastructure, the unified dashboard, premium AI generation, SMS/WhatsApp delivery, SLAs.

Pricing target: €15–€30 / month per business for the managed tier.

---

## Differentiation (the moat)

| Versus | Why clawSaas wins |
|--------|-------------------|
| HubSpot / Zoho CRM | Priced and designed for sales teams sitting at desks. clawSaas is a phone-first OS for solo operators on their feet. |
| Hootsuite / Buffer | They schedule outbound. clawSaas handles inbound, outbound and reputation in one. |
| Generic AI chatbots | They reply mindlessly. clawSaas judges importance first, surfaces only what matters, never sends without explicit approval (except in clearly-defined autonomous flows like shoot booking). |
| Building it yourself | The open-source engine is the foundation. Hosted tier removes ops burden. |

---

## Key URLs

| Resource | URL |
|----------|-----|
| Landing site | https://lefotugrapher.github.io/clawsaas/ |
| Privacy policy | https://lefotugrapher.github.io/clawsaas/privacy.html |
| Terms of service | https://lefotugrapher.github.io/clawsaas/terms.html |
| Data deletion | https://lefotugrapher.github.io/clawsaas/data-deletion.html |
| Source (landing site) | https://github.com/lefotugrapher/clawsaas |
| Contact | mittalkshitiz13@gmail.com |

---

## Status snapshot (as of 18 May 2026)

- Gmail watcher: **live**, every 60s, processing real mail
- Shoot booking flow: **live**, end-to-end working
- Calendar integration: **live**
- Daily briefing: **live**, scheduled at 07:00
- Health monitor: **live**, every 10 min
- Instagram DM watcher: **live in dev mode** — visible only to Meta-tester accounts until App Review approval
- Meta App Review: **submission in preparation** (legal docs and landing page complete; screencast and writeups pending)
- Funding application: **Student Inc 2026 at DKIT** — deadline 18 May 2026
