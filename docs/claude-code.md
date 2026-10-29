# Claude Code setup

Open this folder in Claude Code (the CLI, or the VS Code extension) and it already uses
the AISUM gateway for the model. You add one key: the **LLM key for Claude Code**.

Add your **MCP key** too if you want Claude Code to call the AISUM product tools while
you build. This is optional — your app does not need it; the app uses the keys in
`.env`. These calls count against the same team limits as your app. If Claude Code is
calling tools while you demo, your app's calls can come back `RATE_LIMITED`.

| File | Committed? | What it does |
|---|---|---|
| `.claude/settings.json` | yes | Gateway address and model. Not secret — leave it as is |
| `.claude/settings.local.json` | **no** (ignored) | Your keys. Read on top of `settings.json`; the same name here wins. You create it |
| `.mcp.json` | yes | Connects the AISUM MCP tools. Reads `AISUM_TEAM_KEY` from `settings.local.json`. **Don't put the key in `.mcp.json` — git tracks this file, so the key would be pushed with your code.** |

Create the local settings file and put your Claude Code key in it, and your MCP key if
you want the product tools (same on every OS). The Claude Code key is not the app key
from `.env`:

```bash
cp .claude/settings.local.json.example .claude/settings.local.json
# replace "replace-with-your-Claude-Code-key" with your Claude Code LLM key
# replace "replace-with-your-MCP-key" with your MCP key
```

Then start Claude Code from this folder.

The first time, Claude Code asks whether to use the MCP servers in this project's
`.mcp.json`. Approve `aisum`. Until you do, `claude mcp list` shows it as
`Pending approval`.

**It is working when:** running `/mcp` inside Claude Code lists the `aisum` server as
connected with its tools, and asking *"search for a warm camping jacket with the aisum
tools"* returns products.

`claude mcp list` may warn `Missing environment variables: AISUM_TEAM_KEY` — it does not
read `settings.local.json`, so the warning does not mean the connection is broken.
`/mcp` inside Claude Code is the real check.

If `/mcp` shows `aisum` as not connected, register it for yourself instead — once, for
this folder on your machine; the key stays in your Claude Code user settings, outside the repo. The same
line works in a macOS / Linux terminal and in PowerShell:

```bash
claude mcp add --transport http --scope local aisum https://acts.aedi.ai/mcp --header "Authorization: Bearer <your MCP key>"
```

Then start `claude` again. A server added this way takes precedence over the one in
`.mcp.json`.

Settings apply to the folder you start `claude` in. Started anywhere else, Claude Code
uses your own account instead of the gateway.

Cursor and Windsurf use different configuration formats; add those separately if
your team needs them.
