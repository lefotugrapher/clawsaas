"""Central config for all OpenClaw scripts."""
import os

BASE       = os.path.expanduser("~/.openclaw")
SECRETS    = f"{BASE}/secrets"
WORKSPACE  = f"{BASE}/workspace/api_clients"
LOGS       = f"{BASE}/logs"

GMAIL_CREDENTIALS = f"{SECRETS}/gmail_credentials.json"
GMAIL_TOKEN       = f"{SECRETS}/gmail_token.json"
CALENDAR_TOKEN    = f"{SECRETS}/calendar_token.json"
TELEGRAM_SECRET   = f"{SECRETS}/telegram.json"
AUTH_PROFILES     = f"{BASE}/agents/main/agent/auth-profiles.json"

PROCESSED_EMAILS    = f"{WORKSPACE}/.processed_emails.json"
PENDING_REPLIES     = f"{WORKSPACE}/.pending_replies.json"
TELEGRAM_OFFSET     = f"{WORKSPACE}/.telegram_offset.json"
SHOOT_CONVERSATIONS = f"{WORKSPACE}/.shoot_conversations.json"

INSTAGRAM_SECRET     = f"{SECRETS}/instagram.json"
IG_PROCESSED         = f"{WORKSPACE}/.processed_dms.json"
IG_PENDING           = f"{WORKSPACE}/.pending_dms.json"
IG_GRAPH_VERSION     = "v23.0"

SHOOT_KEYWORDS = ["shoot", "photo", "photoshoot", "video", "film", "session", "filming"]
SHOOT_PRICE_EUR = 300
SHOOT_DURATION_HOURS = 1

SHOOT_QUESTIONS = [
    ("purpose",         "What is the shoot for? (e.g. marketing, event, portrait, product)"),
    ("location",        "Where would you like the shoot? Please include the full address."),
    ("datetime",        "What date and time works for you? (preferred start time)"),
    ("duration",        "Roughly how long do you need? (in hours)"),
    ("special_requests", "Any special requirements? (props, permits, specific shots, etc.) Reply 'none' if not."),
]

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]

TIMEZONE = "Europe/Dublin"
OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
OPENROUTER_FALLBACKS = [
    "openai/gpt-oss-120b:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "google/gemma-4-31b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "deepseek/deepseek-v4-flash:free",
    "z-ai/glm-4.5-air:free",
]
VENV_PYTHON = f"{BASE}/venv/bin/python3"
