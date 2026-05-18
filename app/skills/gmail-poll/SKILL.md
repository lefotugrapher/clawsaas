# Gmail‑Poll Skill
**Description**
Runs the Gmail polling script inside the OpenClaw virtual‑environment and returns the list of unread messages directly in the chat.

**User invocation**
```
!gmail-poll
```
or simply type `gmail poll`.

**How it works**
1. Activates the virtual‑environment at `/Users/kshitizmittal/.openclaw/venv`.
2. Executes `../api_clients/gmail_poll.py`.
3. Captures stdout and sends it back to the chat.

**Requirements**
- The virtual‑environment must contain the Gmail Python dependencies (`google-auth`, `google-api-python-client`).
- Token and credentials files are stored in `/Users/kshitizmittal/.openclaw/secrets/`.

**Installation**
```bash
cd /Users/kshitizmittal/.openclaw/workspace/skills/gmail-poll
openclaw skill install .
```
After installing, you can invoke the skill in any chat session with `!gmail-poll`.