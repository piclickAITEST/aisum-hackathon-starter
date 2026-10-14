"""Environment configuration. Every secret comes from .env — never from code.

This is the one place a project switches: MCP, LLM gateway and Firebase project
values all come from here, whether that's a local .env file or Cloud Run
--env-vars-file. Nothing below this module ever hardcodes a project value.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_REQUIRED = [
    "MCP_URL", "MCP_API_KEY", "OPENAI_BASE_URL", "OPENAI_API_KEY", "MODEL",
    # Firebase web config. Not secret: it identifies the project, it grants nothing.
    "FIREBASE_API_KEY", "FIREBASE_AUTH_DOMAIN", "FIREBASE_PROJECT_ID",
    "FIREBASE_STORAGE_BUCKET", "FIREBASE_MESSAGING_SENDER_ID", "FIREBASE_APP_ID",
]


def _read_env(path):
    """The text of .env, however a Windows tool saved it.

    `Path.read_text()` with no encoding decodes with the machine's locale — cp949 on a
    Korean Windows — so a UTF-8 .env containing any non-ASCII character failed to load.
    Decode the bytes explicitly. Two things Windows tools do to a .env are handled too:
    Notepad can add a UTF-8 byte-order mark, and `echo KEY=value > .env` in Windows
    PowerShell 5 writes UTF-16.

    Keys and values are ASCII, so only they have to survive: a comment saved in some other
    encoding is read as best it can be and ignored, and a line that sets a value is the
    only thing that stops the app, with the line number.
    """
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    text = raw.decode("utf-8-sig", errors="replace")
    for number, line in enumerate(text.splitlines(), 1):
        if "\ufffd" in line and not line.lstrip().startswith("#"):
            raise SystemExit(
                f"{path}, line {number}: a setting contains a character that is not UTF-8. "
                "Keys and values are plain ASCII: retype that line, and save the file as "
                "UTF-8 (in Notepad: File > Save As > Encoding: UTF-8).")
    return text


_env = ROOT / ".env"
if _env.exists():
    for line in _read_env(_env).splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

_missing = [k for k in _REQUIRED if not os.environ.get(k)]
if _missing:
    raise SystemExit(
        f"Missing settings: {', '.join(_missing)}. Set them in {_env}"
        + ("" if _env.exists() else " (not found — copy .env.example to .env)")
        + ", or as environment variables on Cloud Run.")

MCP_URL = os.environ["MCP_URL"]
MCP_API_KEY = os.environ["MCP_API_KEY"]

OPENAI_BASE_URL = os.environ["OPENAI_BASE_URL"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
MODEL = os.environ["MODEL"]

FIREBASE_API_KEY = os.environ["FIREBASE_API_KEY"]
FIREBASE_AUTH_DOMAIN = os.environ["FIREBASE_AUTH_DOMAIN"]
FIREBASE_PROJECT_ID = os.environ["FIREBASE_PROJECT_ID"]
FIREBASE_STORAGE_BUCKET = os.environ["FIREBASE_STORAGE_BUCKET"]
FIREBASE_MESSAGING_SENDER_ID = os.environ["FIREBASE_MESSAGING_SENDER_ID"]
FIREBASE_APP_ID = os.environ["FIREBASE_APP_ID"]
