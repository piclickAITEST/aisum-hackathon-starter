# Claude Code setup

The MCP key is optional: it lets Claude Code call the AISUM product tools while you
build. Your app does not need it — the app only uses the keys in `.env`.

Open this folder in Claude Code (the CLI, or the VS Code extension) and it is already
pointed at the AISUM gateway and the AISUM product tools. You add two keys: the
**LLM key for Claude Code** and your **MCP key**.

| File | Committed? | What it does |
|---|---|---|
| `.claude/settings.json` | yes | Gateway address and model. Not secret — leave it as is |
| `.claude/settings.local.json` | **no** (ignored) | Your keys. Read on top of `settings.json`; the same name here wins. You create it |
| `.mcp.json` | yes | Connects the AISUM MCP tools. Reads `AISUM_TEAM_KEY` from `settings.local.json`. **Don't put the key in `.mcp.json` — it is committed.** |

Create the local settings file and put **both keys** in it (same on every OS). The
Claude Code key is not the app key from `.env`:

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

If `/mcp` shows `aisum` as not connected, set the key in the shell instead and start
`claude` again from that same terminal:

**macOS / Linux**

```bash
export AISUM_TEAM_KEY="<your MCP key>"
claude
```

**Windows (PowerShell)**

```powershell
$env:AISUM_TEAM_KEY = "<your MCP key>"
claude
```

Tool calls from Claude Code share your team's limits with your app — go easy before a
live demo.

Settings apply to the folder you start `claude` in. Started anywhere else, Claude Code
uses your own account instead of the gateway.

Cursor and Windsurf use different configuration formats; add those separately if
your team needs them.
