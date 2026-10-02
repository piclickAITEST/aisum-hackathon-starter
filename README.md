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

You need the values in `.env` from the hackathon organizers:

- `MCP_API_KEY`: the team key for AISUM MCP
- `OPENAI_API_KEY`: the team key for the LLM gateway
- the Firebase web configuration for your team's Firebase project

Copy the template and fill it in:

```bash
cp .env.example .env
```

`MCP_API_KEY` and `OPENAI_API_KEY` are secrets. Keep `.env` local. Never put either
key in source code, `.env.example`, GitHub, or a browser request.

Install and run locally:

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m uvicorn src.main:app --reload
```

Open <http://127.0.0.1:8000>.

## Checkpoint 0 — did you receive the MCP key?

Run:

```bash
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

The verified billing-enabled test project is `molten-amulet-471104-r0`, using the
`personal` gcloud configuration. Do not activate that configuration globally: another
terminal may be using the company `default` configuration.

First make sure your deployment environment has the values from `.env` available. Then
run the deploy command with the configuration on **this command only**:

```bash
export PATH="$HOME/tools/google-cloud-sdk/bin:$PATH"
CLOUDSDK_ACTIVE_CONFIG_NAME=personal gcloud run deploy aisum-hackathon-starter \
  --source . \
  --project molten-amulet-471104-r0 \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "MCP_URL=$MCP_URL,MCP_API_KEY=$MCP_API_KEY,OPENAI_BASE_URL=$OPENAI_BASE_URL,OPENAI_API_KEY=$OPENAI_API_KEY,MODEL=$MODEL,FIREBASE_API_KEY=$FIREBASE_API_KEY,FIREBASE_AUTH_DOMAIN=$FIREBASE_AUTH_DOMAIN,FIREBASE_PROJECT_ID=$FIREBASE_PROJECT_ID,FIREBASE_STORAGE_BUCKET=$FIREBASE_STORAGE_BUCKET,FIREBASE_MESSAGING_SENDER_ID=$FIREBASE_MESSAGING_SENDER_ID,FIREBASE_APP_ID=$FIREBASE_APP_ID"
```

**It is working when:** `gcloud` prints a Cloud Run URL and opening that URL shows the
starter page. `--allow-unauthenticated` is required so Firebase can handle sign-in and
the page can load before a user has authenticated with Cloud Run.

For a real team deployment, use the project and billing setup provided by the
organizers. Do not deploy hackathon apps into a company project that has not been
prepared for it.

## Checkpoint 4 — does the deployed copy work?

On the Cloud Run URL, repeat checkpoint 1, checkpoint 1-1, and checkpoint 2.

**It is working when:** the deployed copy can sign in, call text/image/scene MCP, and
return one LLM response just like localhost.

If sign-in fails only after deployment with `auth/unauthorized-domain`, add the Cloud
Run domain to the Firebase project's authorized domains. Localhost is normally already
allowed; a new deployed domain is not.

## Claude Code setup

The app runtime and your coding agent are two separate connections. The repository
includes `.mcp.json` for the MCP tools and `.claude/settings.example.json` plus
`.claude/settings.local.json.example` for the coding-agent settings.

Copy the two Claude Code templates after the organizers give you the real coding
Gateway host, model name, and coding key:

```bash
cp .claude/settings.example.json .claude/settings.json
cp .claude/settings.local.json.example .claude/settings.local.json
# edit the three placeholders in settings.json and the key in settings.local.json
```

Do not commit either copied live file. `.gitignore` excludes them because they may
contain internal URLs and credentials. The settings template deliberately uses
placeholders: Claude Code reads `settings.json` as a live configuration, so an
unusable placeholder URL or model would make the session fail rather than merely
explain what to do.

### Claude Code MCP connection


```bash
export AISUM_TEAM_KEY="$MCP_API_KEY"
claude
```

The committed `.mcp.json` uses `${AISUM_TEAM_KEY}` expansion. The key itself is never
in that file. A custom variable name is intentional: do not rename it to a provider
credential variable such as `ANTHROPIC_API_KEY`.

The configuration is for Claude Code. Cursor and Windsurf use different configuration
formats; add those separately if your team needs them.

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

- `.env` is ignored and not staged.
- No MCP or LLM key appears in a file, URL, log, screenshot, or commit.
- Only the public MCP hostname `acts.aedi.ai` appears; do not publish internal hosts or
  IP addresses.
- Do not publish internal tool names or server implementation details.
- The Firebase web config may be visible; Firebase service-account credentials must not.
