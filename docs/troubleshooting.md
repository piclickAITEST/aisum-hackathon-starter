# Troubleshooting

Search this page for the exact text you see.

## `Missing settings: …` when starting the app

The app checks every setting at start-up and names the ones that are empty or absent.
Copy `.env.example` to `.env` if you have not, and fill in the names listed. A fresh
`.env.example` has the six `FIREBASE_*` values empty — that is the usual cause.

## gcloud not found

The terminal says `command not found: gcloud` (macOS / Linux) or
`gcloud : The term 'gcloud' is not recognized` (Windows). Either the Google Cloud CLI is
not installed — [install it](https://cloud.google.com/sdk/docs/install), or use Cloud
Shell — or it is installed but not on your `PATH`. **Open a new terminal first**: the
installer updates `PATH` only for terminals opened after it ran.

Still not found:

**macOS / Linux** — add the SDK's `bin` folder to your shell profile.

```bash
echo 'export PATH="<where you unpacked it>/google-cloud-sdk/bin:$PATH"' >> ~/.zshrc   # or ~/.bashrc
```

**Windows (PowerShell)** — re-run the installer and leave *Add to PATH* checked, or for
the current terminal only:

```powershell
$env:PATH += ";$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin"
```

## A `401` — which one?

| Message | Cause |
|---|---|
| `Sign in first — no Firebase ID token` | You are not signed in on this page |
| `Firebase ID token rejected: Audience doesn't match` | The token is from a different Firebase project than `FIREBASE_PROJECT_ID` — after switching projects, sign out and in again |
| `MCP server answered HTTP 401 — check MCP_API_KEY` | The MCP key |
| `LLM gateway answered HTTP 401 …` on **Check LLM connection** | The LLM key |

Putting one key in the other's place is the most common cause.

## `400` from the model after a tool call

The second model call (the one carrying the tool result) is rejected. Two rules are
usually the cause, whether you wrote the loop or a framework did:

- send the model's own reply back **unchanged** — it may carry fields you did not read,
  such as its reasoning
- answer each tool call with a `tool` message carrying the **same** `tool_call_id`

The **One tool call, end to end** card shows a working set of messages to compare with.

## Sign-in shows `auth/unauthorized-domain`

The page's address is not on the Firebase project's list of allowed sign-in domains.
Locally, open `http://localhost:8000` instead of `http://127.0.0.1:8000`. On Cloud
Run, see [checkpoint 6](deploy.md#checkpoint-6--the-deployed-copy).

## The LLM returned `200 OK` but the text is empty

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

## Image search fails with `INTERNAL_ERROR: task failed before producing a result`

Most often the image is too large. The same photo failed as a 2.4 MB original and
worked as a 325 KB resize. Send a web-sized image (around 1000 px wide); many image
hosts resize through the URL, for example `?w=1080` on Unsplash. The error text does
not mention size, so check this first.
