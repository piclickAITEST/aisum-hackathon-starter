# Local setup — checkpoints 0 to 4

Each checkpoint ends with **It is working when** — if you see that, move on. The order
matches the progress strip at the top of the page. Run the app first
([README](../README.md#run-it-locally)); checkpoint 1 signs you in, which every `/api/*`
route needs.

## Checkpoint 0 — MCP key

Load `.env` into your terminal, then ask the server who you are. Loading lasts until
you close that terminal.

**macOS / Linux**

```bash
set -a; . ./.env; set +a
curl -s https://acts.aedi.ai/status -H "Authorization: Bearer $MCP_API_KEY"
```

**Windows (PowerShell)** — use `curl.exe`; plain `curl` in Windows PowerShell is a
different command.

```powershell
Get-Content .env | Where-Object { $_ -match '^[A-Z_]+=' } | ForEach-Object {
  $k, $v = $_ -split '=', 2; Set-Item "env:$k" $v.Trim() }
curl.exe -s https://acts.aedi.ai/status -H "Authorization: Bearer $env:MCP_API_KEY"
```

**It is working when:** the JSON contains your team name and the configured tool
limits. This checks the ordinary `/status` endpoint only. It does **not** prove that
the MCP JSON-RPC session works; checkpoint 2 does that.

If this returns `401`, check `MCP_API_KEY`. Do not put the LLM key in this header.

## Checkpoint 1 — sign-in

Click **Sign in with Google**, choose an account, and return to the page.

**It is working when:** the email address appears in the header, the cards below
appear, and **Sign in** turns green in the progress strip.

### Why sign-in is required

Your deployed URL is public, and every button on it spends your team's MCP and LLM
quota. So the server answers `/api/*` only for a signed-in user: after Google sign-in,
`static/app.js` sends the Firebase ID token on every request, and `src/auth.py`
checks Google's signature on it with Google's public keys before anything runs. No
Firebase Admin credentials are involved, so it works the same locally and on Cloud
Run. The route gets the user's id as `uid` — the place to hang anything per-user.
Sign-ins are also what the judging counts, so your own app should require them too.

The browser obtains its Firebase configuration from `/api/firebase-config`. The values
are public Firebase web configuration, not service-account credentials. To switch from
the pilot project to a company project or your team's project, change the six
`FIREBASE_*` values in `.env`; do not edit `static/auth.js`.

The page includes this user notice intentionally:

> Signing in creates an account in a Google Cloud project operated by AISUM for AISUM
> Hackathon 2026. What you type into this app is sent to AISUM's services to produce
> results, and is recorded there.

Keep it next to your sign-in control, and keep it visible wherever users type. This
page does both: the full notice sits under the sign-in button, and once signed in, a
short line under the progress strip and the full text at the bottom.

Do not remove it without understanding the participant notice requirements.

## Checkpoint 2 — MCP tools from the app

Run the four product-tool cards in order:

1. **Text search** calls `search_products_by_text` once and displays JSON.
2. **Image search** calls `search_products_by_image` once and displays grouped JSON.
3. **Scene match** calls `start_scene_match` once, receives a `task_id`, and then
   calls `get_scene_match_result` repeatedly with that **same** `task_id`.
4. **Video match** does the same with `start_video_match` and
   `get_video_match_result`.

**It is working when:** each card shows a green ✓ line, and scene and video visibly
move from `Got task_id … Polling` to a completed result. A job must never be started
again just because its result is still pending. The example video has been run
before, so it returns in seconds; a video nobody has run before takes minutes.

### Why `src/mcp_client.py` is longer than a normal HTTP request

MCP Streamable HTTP requires a small handshake:

1. POST JSON-RPC `initialize`.
2. Read the returned `mcp-session-id`.
3. POST `notifications/initialized`.
4. Include that session ID on later JSON-RPC requests.
5. Parse the response body as Server-Sent Events, even when there is one result.

The kit uses `httpx` directly so every step is visible when you check the connection.
That is a choice for this example, not a requirement: your own app can use this
approach, an MCP SDK, or whatever your framework provides. The team key stays
server-side and is sent as `Authorization: Bearer ...` only from the Python app.

### The same calls with the official MCP SDK

Checked with `mcp` 2.3.0 on Python 3.11 (the SDK needs 3.10 or newer). Function and
field names have changed between SDK versions — check the version you install.

```python
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client, httpx2 as httpx

async with httpx.AsyncClient(headers={"Authorization": f"Bearer {KEY}"}, timeout=60) as http:
    async with streamable_http_client(MCP_URL, http_client=http) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = await s.list_tools()
            out = await s.call_tool("search_products_by_text", {"query": "..."})
            # out.is_error, and out.content[0].text holds the JSON payload
```

## Checkpoint 3 — the LLM gateway

Click **Check LLM connection**. This makes exactly one request to:

```text
{OPENAI_BASE_URL}/chat/completions
```

and prints the returned text. There is deliberately no agent loop here: a model
choosing tools and building a product experience is your team's design.

**It is working when:** a model response appears in the result box and the status
line says `finish_reason: stop`. If it fails, the error carries the gateway's own
message — an unknown model, a key not allowed that model, or a bad key — and points at
`OPENAI_BASE_URL`, `OPENAI_API_KEY` and `MODEL`. Those are the LLM settings; they are
separate from the MCP URL and MCP key.

## Checkpoint 4 — one tool call, end to end

The **One tool call, end to end** card gives the model your question and one product
tool, runs the call the model asks for, and sends the result back. Each of the four
steps is shown on the page.

**It is working when:** step 1 ends with `finish_reason: "tool_calls"` and step 4 with
`"stop"`. A question that needs no products (try "What is 2 + 2?") stops after step 1 —
that is normal.

This is a connection check, not a pattern to copy. If a tool call fails with a `400`,
see [troubleshooting](troubleshooting.md#400-from-the-model-after-a-tool-call).

Next: [deploy to Cloud Run](deploy.md).
