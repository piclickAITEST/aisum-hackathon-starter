"""Environment configuration. Every secret comes from .env — never from code.

This is the one place a project switches: MCP, LLM gateway and Firebase project
values all come from here, whether that's a local .env file or Cloud Run
--set-env-vars. Nothing below this module ever hardcodes a project value.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.split("#")[0].strip())


_load_dotenv()

MCP_URL = os.environ["MCP_URL"]
MCP_API_KEY = os.environ["MCP_API_KEY"]

OPENAI_BASE_URL = os.environ["OPENAI_BASE_URL"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
MODEL = os.environ.get("MODEL", "gpt-5.6-luna")

# Firebase — public client config. Not a secret: it identifies the project, it does
# not grant anything. Served to the browser via /api/firebase-config so that
# switching projects is an env-var change, not a code change.
FIREBASE_API_KEY = os.environ["FIREBASE_API_KEY"]
FIREBASE_AUTH_DOMAIN = os.environ["FIREBASE_AUTH_DOMAIN"]
FIREBASE_PROJECT_ID = os.environ["FIREBASE_PROJECT_ID"]
FIREBASE_STORAGE_BUCKET = os.environ["FIREBASE_STORAGE_BUCKET"]
FIREBASE_MESSAGING_SENDER_ID = os.environ["FIREBASE_MESSAGING_SENDER_ID"]
FIREBASE_APP_ID = os.environ["FIREBASE_APP_ID"]
