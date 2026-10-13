"""Every call to the AISUM MCP server goes through this module.

Streamable-HTTP MCP: one POST per JSON-RPC message, replies arrive as a
text/event-stream body even for a single result, and the server hands out an
mcp-session-id on initialize that every later request must echo back.

Written with plain httpx so every step of the protocol is visible — a connection check,
not a requirement. Your own app can talk MCP however it likes: this way, an MCP SDK,
or whatever your framework provides.

Every request carries the team key on Authorization: Bearer <key>. The public
endpoint (acts.aedi.ai) rejects everything without it.
"""
import json
import re
from typing import Any

import httpx

from .config import MCP_API_KEY, MCP_URL

_ACCEPT = "application/json, text/event-stream"
_PROTOCOL_VERSION = "2025-06-18"
_TIMEOUT = 60.0
_CODE = re.compile(r"[A-Z][A-Z_]+")


class McpError(RuntimeError):
    """A tool call that came back as a failure."""

    def __init__(self, message: str, code: str = "TOOL_ERROR", raw: Any = None):
        super().__init__(message)
        self.code = code
        self.raw = raw


def _check_http(r: httpx.Response) -> None:
    """Turn an HTTP-level failure into an McpError that names the setting to check.

    A wrong key fails here, on `initialize`, before any tool runs — and a bare
    `401 Unauthorized` does not say which of your two keys it was.
    """
    if r.is_success:
        return
    # Only 401 means the key. A 403 comes from in front of the server (network
    # access), and sending someone to re-check a correct key wastes their afternoon.
    hint = {401: " — check MCP_API_KEY (this is the MCP key, not the LLM key)",
            403: " — the server refused this network; tell the organizers"
            }.get(r.status_code, " — check MCP_URL")
    raise McpError(f"MCP server answered HTTP {r.status_code}{hint}",
                   code=f"HTTP_{r.status_code}", raw=r.text[:500])


def _parse_body(text: str) -> dict:
    for line in text.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    return json.loads(text)


class McpClient:
    def __init__(self, url: str = MCP_URL, api_key: str = MCP_API_KEY):
        self._url = url
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=_TIMEOUT)
        self._session_id: str | None = None
        self._next_id = 0

    async def aclose(self) -> None:
        await self._client.aclose()

    def _headers(self) -> dict:
        h = {
            "Content-Type": "application/json",
            "Accept": _ACCEPT,
            "Authorization": f"Bearer {self._api_key}",
        }
        if self._session_id:
            h["mcp-session-id"] = self._session_id
        return h

    async def _ensure_session(self) -> None:
        if self._session_id:
            return
        r = await self._client.post(
            self._url,
            headers=self._headers(),
            json={
                "jsonrpc": "2.0",
                "id": 0,
                "method": "initialize",
                "params": {
                    "protocolVersion": _PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "aisum-hackathon-starter", "version": "1.0"},
                },
            },
        )
        _check_http(r)
        self._session_id = r.headers["mcp-session-id"]
        # The server rejects tools/call until this notification has been sent.
        await self._client.post(
            self._url,
            headers=self._headers(),
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        )

    async def call(self, name: str, arguments: dict) -> dict:
        """Call one MCP tool.

        in:  the tool's name, and its arguments as a dict, e.g. {"query": "..."}.
        out: the tool's JSON result as a dict. Any failure raises McpError.
        """
        result = await self._rpc("tools/call", {"name": name, "arguments": arguments})
        return _unwrap(name, result)

    async def list_tools(self) -> list[dict]:
        """The tools the server offers, each with a JSON Schema for its arguments.

        That schema is exactly what an LLM needs in order to call the tool — see
        /api/tool-call in main.py, which hands it to the model unchanged.
        """
        return (await self._rpc("tools/list", {}))["tools"]

    async def _rpc(self, method: str, params: dict) -> dict:
        r = await self._post(method, params)
        if r.status_code == 404 and self._session_id:
            # The server forgot our session — it was restarted or redeployed. The MCP
            # spec answers 404 for an unknown session id; the fix is a new handshake.
            self._session_id = None
            r = await self._post(method, params)
        _check_http(r)
        msg = _parse_body(r.text)
        if "error" in msg:
            raise McpError(msg["error"].get("message", "MCP transport error"),
                           code="RPC_ERROR", raw=msg["error"])
        return msg["result"]

    async def _post(self, method: str, params: dict) -> httpx.Response:
        await self._ensure_session()
        self._next_id += 1
        return await self._client.post(
            self._url,
            headers=self._headers(),
            json={"jsonrpc": "2.0", "id": self._next_id, "method": method,
                  "params": params},
        )


def _unwrap(name: str, result: dict) -> dict:
    """Turn a failed tool call into one exception that carries `error.code`.

    A failure sets `isError` and its body is JSON: `{"error": {...}}`, or for a
    submitted job that failed, `{"status": "failed", "error": {...}}`. Read the
    body first and `isError` second: the flag says that the call failed, the body
    says why, and `error.code` is what tells you whether calling again can help.

    A body that is not JSON is still handled, as `CODE: message` or plain text.
    This server does not send one; another MCP server might.
    """
    text = "".join(c.get("text", "") for c in result.get("content", []))
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None
        if not result.get("isError"):
            raise McpError(f"MCP returned a result that is not JSON: {text[:200]!r}",
                           code="BAD_RESPONSE", raw=text)
    if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
        err = payload["error"]
        raise McpError(err.get("message", "unknown error"),
                       code=err.get("code", "TOOL_ERROR"), raw=payload)
    if isinstance(payload, dict) and payload.get("status") == "failed":
        err = payload.get("error") or {}
        raise McpError(err.get("message", "The task failed."),
                       code=err.get("code", "FAILED"), raw=payload)
    if result.get("isError"):
        # Not JSON. The code is the word before the first colon, when there is one.
        code, sep, message = text.strip().partition(": ")
        if sep and _CODE.fullmatch(code):
            raise McpError(message, code=code, raw=text)
        raise McpError(text.strip() or "The tool reported an error.",
                       code="TOOL_ERROR", raw=text)
    return payload
