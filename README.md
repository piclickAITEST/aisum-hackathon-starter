# AISUM Hackathon Starter Kit

A small wiring example for AISUM Hackathon 2026. It shows four connections and
nothing that decides what your product should be:

- Google sign-in with Firebase
- Three MCP call patterns (text, image, and a two-step scene job)
- One OpenAI-compatible LLM gateway call
- Cloud Run deployment

There is no shopping UI, product recommendation flow, agent loop, session store,
or memory system here. Build those parts yourself.

## Before you start

The organizers give your team two keys and one Firebase project:

- **MCP key** — for the AISUM product tools at `https://acts.aedi.ai/mcp`
- **LLM key** — for the LLM gateway at `https://acts.aedi.ai/llm`. The same key is
  used by this app and by Claude Code.
- the Firebase web configuration for your team's Firebase project

Copy the template and fill in the two keys and the six `FIREBASE_*` values. The URLs
and model name are already correct:

```bash
cp .env.example .env
```

| `.env` variable | What goes there |
|---|---|
| `MCP_API_KEY` | MCP key |
| `OPENAI_API_KEY` | LLM key |
| `FIREBASE_*` | Firebase console → Project settings → General → Your apps → SDK setup and configuration → Config |

Both keys are secrets. Keep `.env` local. Never put either key in source code,
`.env.example`, GitHub, or a browser request.

Install and run locally:

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m uvicorn src.main:app --reload
```

Open <http://127.0.0.1:8000>.

## Checkpoint 0 — did you receive the MCP key?

Load `.env` into your shell first (the commands below and in checkpoint 3 read from
it), then run:

```bash
set -a; . ./.env; set +a
curl -s https://acts.aedi.ai/status \
  -H "Authorization: Bearer $MCP_API_KEY"
```

**It is working when:** the JSON contains your team name and the configured tool
limits. This checks the ordinary `/status` endpoint only. It does **not** prove that
the MCP JSON-RPC session works; checkpoint 1 does that.

If this returns `401`, check `MCP_API_KEY`. Do not put the LLM key in this header.

## Checkpoint 1 — can the app call MCP?

Start the app and sign in. Click the three MCP buttons in order:

1. **Text search** calls `search_products_by_text` once and displays JSON.
2. **Image search** calls `search_products_by_image` once and displays grouped JSON.
3. **Scene match** calls `start_scene_match` once, receives a `task_id`, and then
   calls `get_scene_match_result` repeatedly with that **same** `task_id`.

**It is working when:** text returns promptly, image returns after a short wait,
and scene visibly moves from `task_id received / polling` to a completed JSON result.
A scene job must never be started again just because its result is still pending.
That same start-then-poll pattern is used by the video tools; video is described here
rather than included as a fourth app button.

### Why `src/mcp_client.py` is longer than a normal HTTP request

MCP Streamable HTTP requires a small handshake:

1. POST JSON-RPC `initialize`.
2. Read the returned `mcp-session-id`.
3. POST `notifications/initialized`.
4. Include that session ID on later JSON-RPC requests.
5. Parse the response body as Server-Sent Events, even when there is one result.

The client uses `httpx` directly so you can see every part of the wire protocol. The
team key stays server-side and is sent as `Authorization: Bearer ...` only from the
Python app.

## Checkpoint 1-1 — can the app call the LLM gateway?

Click **Check LLM connection**. This makes exactly one request to:

```text
{OPENAI_BASE_URL}/chat/completions
```

and prints the returned text. There is deliberately no agent loop here: a model
choosing tools and building a product experience is your team's design.

**It is working when:** a model response appears in the result box. If it fails, read
the error: it tells you to check `OPENAI_BASE_URL` and `OPENAI_API_KEY`. Those are the
LLM settings; they are separate from the MCP URL and MCP key.

## Checkpoint 2 — does Firebase sign-in work?

Click **Sign in with Google**, choose an account, and return to the page.

**It is working when:** the email address appears in the header and the example
panels become available.

The browser obtains its Firebase configuration from `/api/firebase-config`. The values
are public Firebase web configuration, not service-account credentials. To switch from
the pilot project to a company project or your team's project, change the six
`FIREBASE_*` values in `.env`; do not edit `static/auth.js`.

The page includes this user notice intentionally:

> Signing in creates an account in a Google Cloud project operated by AISUM for AISUM
> Hackathon 2026.

Do not remove it without understanding the participant notice requirements.

## Checkpoint 3 — can Cloud Run deploy it?

The project must listen on the port Cloud Run gives it and bind to `0.0.0.0`. The
included `Procfile` does both through Uvicorn.

You need the Google Cloud CLI (`gcloud`), or use Cloud Shell in the browser where it
is already installed. Sign in once and select your team's project:

```bash
gcloud auth login
gcloud config set project <your-team-project-id>
```

Cloud Run does not read `.env`. Turn it into `env.yaml` (ignored by git, and not
uploaded with the source), then deploy with that file. This keeps the keys out of
your shell history:

```bash
grep -E '^[A-Z_]+=' .env | sed -E 's/^([A-Z_]+)=(.*)$/\1: "\2"/' > env.yaml

gcloud run deploy app \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --env-vars-file env.yaml
```

**It is working when:** `gcloud` prints a `Service URL: https://...run.app` line and
opening that URL shows the starter page with the sign-in button.

`--allow-unauthenticated` is required. Without it the URL answers `403 Forbidden` —
the deploy succeeded, but Cloud Run refuses anyone who is not signed in to your Google
Cloud project, which includes every user of your app.

## Checkpoint 4 — does the deployed copy work?

On the Cloud Run URL, repeat checkpoint 1, checkpoint 1-1, and checkpoint 2.

**It is working when:** the deployed copy can sign in, call text/image/scene MCP, and
return one LLM response just like localhost.

If sign-in works on localhost but the deployed page shows `auth/unauthorized-domain`,
the new `run.app` address is not yet on the Firebase project's list of allowed sign-in
domains. AISUM owns the Firebase projects and adds deployed addresses for you; if the
error is still there some time after your first deploy, tell the organizers the URL.

## Claude Code setup

Open this folder in Claude Code (the CLI, or the VS Code extension) and it is already
pointed at the AISUM gateway and the AISUM product tools. You add two keys.

| File | Committed? | What it does |
|---|---|---|
| `.claude/settings.json` | yes | Gateway address and model. Not secret — leave it as is |
| `.claude/settings.local.json` | **no** (ignored) | Your LLM key. You create it |
| `.mcp.json` | yes | Connects the AISUM MCP tools. Reads the MCP key from your shell |

Create the local settings file and put your **LLM key** in it:

```bash
cp .claude/settings.local.json.example .claude/settings.local.json
# replace "replace-with-your-LLM-key" with your LLM key
```

Export your **MCP key** under the name `.mcp.json` expects, then start Claude Code
from this folder:

```bash
export AISUM_TEAM_KEY="<your MCP key>"
claude
```

**It is working when:** running `/mcp` inside Claude Code lists the `aisum` server as
connected with its tools, and asking *"search for a warm camping jacket with the aisum
tools"* returns products. If `aisum` shows as failed with a 401, `AISUM_TEAM_KEY` is
not set in the shell you started `claude` from.

Settings apply to the folder you start `claude` in. Started anywhere else, Claude Code
uses your own account instead of the gateway.

Cursor and Windsurf use different configuration formats; add those separately if
your team needs them.

## FAQ

### The LLM returned `200 OK` but the text is empty

The model (`deepseek-v4.1-flash`) is a reasoning model: it thinks before it answers,
and `max_tokens` caps **thinking and answer together**. If `max_tokens` is small, the
thinking can use all of it and nothing is left for the answer:

```text
request   max_tokens: 20, a question that needs some reasoning
response  HTTP 200
          choices[0].message.content   ""        <- empty, but not an error
          choices[0].finish_reason     "length"
          usage.completion_tokens      20
```

How to recognise it: `content == ""` **and** `finish_reason == "length"`.

- **Do not retry.** The same request comes back empty again.
- Leave `max_tokens` out (as `src/llm_client.py` does), or set it to 1024 or more.
- It depends on the prompt: easy questions finish their thinking quickly and answer
  even with a small limit, so the bug looks random. It is not — it is the limit.

### `401` from MCP or the LLM gateway

Each service has its own key. `401` from `/status` or a search button means the MCP
key; an error from **Check LLM connection** means the LLM key or base URL. Putting one
key in the other's place is the most common cause.

## File map

```text
src/config.py       all environment settings, including Firebase's six public values
src/mcp_client.py   MCP handshake, session ID, SSE parsing, team-key header
src/llm_client.py   one httpx POST to /chat/completions
src/main.py         small FastAPI routes and explicit scene polling endpoint
static/auth.js      Firebase config fetch and Google sign-in
static/app.js       four buttons, including the visible scene polling loop
```

## Public-repository safety

Before committing, confirm that the following are true:

- `.env`, `env.yaml` and `.claude/settings.local.json` are ignored and not staged.
- No MCP or LLM key appears in a file, URL, log, screenshot, or commit.
- The Firebase web config may be visible; Firebase service-account credentials must not.
