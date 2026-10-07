# Claude Code setup

Open this folder in Claude Code (the CLI, or the VS Code extension) and it is already
pointed at the AISUM gateway and the AISUM product tools. You add two keys.

| File | Committed? | What it does |
|---|---|---|
| `.claude/settings.json` | yes | Gateway address and model. Not secret — leave it as is |
| `.claude/settings.local.json` | **no** (ignored) | Your LLM key. You create it |
| `.mcp.json` | yes | Connects the AISUM MCP tools. Reads the MCP key from your shell |

Create the local settings file and put your **LLM key** in it (same on every OS):

```bash
cp .claude/settings.local.json.example .claude/settings.local.json
# replace "replace-with-your-LLM-key" with your LLM key
```

Set your **MCP key** under the name `.mcp.json` expects, then start Claude Code from
this folder, in the same terminal:

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

The first time, Claude Code asks whether to use the MCP servers in this project's
`.mcp.json`. Approve `aisum`. Until you do, `claude mcp list` shows it as
`Pending approval`.

**It is working when:** running `/mcp` inside Claude Code lists the `aisum` server as
connected with its tools, and asking *"search for a warm camping jacket with the aisum
tools"* returns products.

If you see `Missing environment variables: AISUM_TEAM_KEY`, the key is not exported
in the shell you started `claude` from — set it as shown above and start `claude` again.

Settings apply to the folder you start `claude` in. Started anywhere else, Claude Code
uses your own account instead of the gateway.

Cursor and Windsurf use different configuration formats; add those separately if
your team needs them.
