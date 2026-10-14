# AISUM Hackathon Starter Kit

A small wiring example for AISUM Hackathon 2026. It shows four connections and
nothing that decides what your product should be:

- Google sign-in with Firebase
- Four product tools over MCP — text, image, scene and video — in two call patterns
- One OpenAI-compatible LLM gateway call
- Cloud Run deployment

This kit stops at the wiring. Anything that holds state between calls, decides
what to call next, or presents results to a person is deliberately absent —
that part is yours.

The tools search a product catalog. What you build on top of them is open:
the brief lists example directions, and they are examples, not requirements.

## The whole picture

```text
 Browser  (static/)                       holds no keys
    │
    │  sign in with Google; every /api/* call carries the Firebase ID token
    ▼
 This app  (src/main.py)                  your laptop now, Cloud Run later
    │
    │  1. check the token                 src/auth.py
    │  2. call AISUM with your team's keys
    │
    ├─ src/mcp_client.py ─ MCP key ─> acts.aedi.ai/mcp  product tools
    └─ src/llm_client.py ─ LLM key ─> acts.aedi.ai/llm  LLM gateway
```

| Tool | Give it | Get back | How long |
|---|---|---|---|
| `search_products_by_text` (AIMS) | a sentence or a whole article | matching products | instant |
| `search_products_by_image` (AIRS) | a photo URL | the items found in it, each with its own matches | a few seconds |
| `start_scene_match` → `get_scene_match_result` (AIMS) | a photo + a description | products that fit the situation | longer — it is a two-step job for a reason |
| `start_video_match` → `get_video_match_result` (AEDI-V) | a YouTube URL | products per moment, with timestamps | minutes, not seconds — a video you have not used before takes the longest |

What matters is the order of magnitude: a text search can sit inside any loop you
like; a video job cannot — something has to wait for it.

The tools accept more parameters than this example uses. The documentation you
receive with your API key lists them.

## Run it locally

The organizers give your team three keys — an **MCP key**, an **LLM key for your app**
and an **LLM key for Claude Code** — and a Firebase project. Copy the template and fill in
the MCP key, the app LLM key and the six `FIREBASE_*` values — the URLs and model name are
already correct. The Claude Code key goes elsewhere, see [docs/claude-code.md](docs/claude-code.md):

```bash
cp .env.example .env
```

| `.env` variable | What goes there |
|---|---|
| `MCP_API_KEY` | MCP key |
| `OPENAI_API_KEY` | LLM key for your app |
| `FIREBASE_*` | Firebase console → Project settings → General → Your apps → SDK setup and configuration → Config |

All three keys are secrets: keep them in `.env` and `.claude/settings.local.json` only.
The two LLM keys are not interchangeable — the app key does not work in Claude Code, and
the Claude Code key does not work in your app. Then install and run.

> **Two versions where commands differ.** macOS and Linux use the first block; Windows
> uses the **PowerShell** block (not `cmd`). Commands shown once work on both.

**macOS / Linux**

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m uvicorn src.main:app --reload
```

**Windows (PowerShell)**

```powershell
uv venv --python 3.11 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
.venv\Scripts\python.exe -m uvicorn src.main:app --reload
```

Open <http://localhost:8000> — `localhost`, not the `127.0.0.1` Uvicorn prints;
Google sign-in only works on `localhost` by default. Sign in first (checkpoint 1).

Type that address into your browser yourself. If you run the app from VS Code's terminal
and VS Code opens or offers a different address (the Ports tab, a `*.devtunnels.ms` link),
sign-in fails with `auth/unauthorized-domain` there — those addresses are not on the list.
Use `localhost`, or run the command from a plain PowerShell / Terminal window instead.

## Checkpoints — where are you?

| # | Check | It is working when | Details |
|---|---|---|---|
| 0 | MCP key | `curl …/status` returns your team name | [setup](docs/setup.md#checkpoint-0--mcp-key) |
| 1 | Sign-in | your email appears in the header | [setup](docs/setup.md#checkpoint-1--sign-in) |
| 2 | MCP tools | text, image, scene and video return JSON; scene and video poll one `task_id` | [setup](docs/setup.md#checkpoint-2--mcp-tools-from-the-app) |
| 3 | LLM gateway | **One model call** shows an answer and `finish_reason: stop` | [setup](docs/setup.md#checkpoint-3--the-llm-gateway) |
| 4 | One tool call | **One tool call, end to end**: step 1 `tool_calls`, step 4 `stop` | [setup](docs/setup.md#checkpoint-4--one-tool-call-end-to-end) |
| 5 | Deploy | `gcloud` prints a `run.app` URL that shows this page | [deploy](docs/deploy.md#checkpoint-5--deploy) |
| 6 | Deployed copy | checkpoints 1–4 work on that URL | [deploy](docs/deploy.md#checkpoint-6--the-deployed-copy) |

Coding with Claude Code against the same tools: [docs/claude-code.md](docs/claude-code.md).
Something failed: [docs/troubleshooting.md](docs/troubleshooting.md) — search it for the
exact error text.

## File map — read in this order

```text
src/main.py         start here: every route, in the order of the page
src/auth.py         checks the Firebase ID token on each /api/* request
src/mcp_client.py   MCP handshake, session ID, SSE parsing, team-key header, tools/list
src/llm_client.py   httpx POST to /chat/completions, optionally with tools
src/config.py       all settings from .env, including Firebase's six public values
static/app.js       the six cards, the scene and video polling loop
static/auth.js      Firebase config fetch and Google sign-in
```

## Public-repository safety

`.env`, `env.yaml` and `.claude/settings.local.json` are ignored by git — keep it that
way, and never put a key in a file, URL, log or screenshot. The Firebase web config may
be public; Firebase service-account credentials must not be. Share the kit by
`git clone` only: a zip of a working folder carries your `.env`.
