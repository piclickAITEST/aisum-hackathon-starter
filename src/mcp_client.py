"""Every call to the AISUM MCP server goes through this module.

Streamable-HTTP MCP: one POST per JSON-RPC message, replies arrive as a
text/event-stream body even for a single result, and the server hands out an
mcp-session-id on initialize that every later request must echo back. There is no
MCP client library in requirements.txt on purpose — this is what it looks like to
talk to it with nothing but httpx.

Two differences from a purely internal client:
  - every request carries the team key on Authorization: Bearer <key>. The public
    endpoint (acts.aedi.ai) rejects everything without it.
  - get_scene_match_result rewrites a NOT_FOUND for a task_id *we* started into
    `pending`. The job is queued, not missing — obeying the literal error would
    resubmit it forever. This is the one behavior worth copying exactly.
"""
import json
import logging
from typing import Any

import httpx

from .config import MCP_API_KEY, MCP_URL

log = logging.getLogger(__name__)

_ACCEPT = "application/json, text/event-stream"
_PROTOCOL_VERSION = "2025-06-18"
_TIMEOUT = 60.0


class McpError(RuntimeError):
    """A tool call that came back as a failure, in any of the server's three shapes."""

    def __init__(self, message: str, code: str = "TOOL_ERROR", raw: Any = None):
        super().__init__(message)
        self.code = code
        self.raw = raw


def _parse_body(text: str) -> dict:
    """Pull the JSON-RPC message out of an SSE body (`data: {...}`)."""
    for line in text.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    return json.loads(text)


class McpClient:
    """Async MCP client. One instance per process; the session is established lazily."""

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
        r.raise_for_status()
        self._session_id = r.headers["mcp-session-id"]
        # The server rejects tools/call until this notification has been sent.
        await self._client.post(
            self._url,
            headers=self._headers(),
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        )

    async def call(self, name: str, arguments: dict) -> dict:
        """Call one MCP tool and return its decoded payload. Raises McpError on failure."""
        await self._ensure_session()
        self._next_id += 1
        r = await self._client.post(
            self._url,
            headers=self._headers(),
            json={"jsonrpc": "2.0", "id": self._next_id, "method": "tools/call",
                  "params": {"name": name, "arguments": arguments}},
        )
        r.raise_for_status()
        msg = _parse_body(r.text)
        if "error" in msg:
            raise McpError(msg["error"].get("message", "MCP transport error"),
                           code="RPC_ERROR", raw=msg["error"])
        return _unwrap(name, msg["result"])


def _unwrap(name: str, result: dict) -> dict:
    """Normalise the server's three different failure envelopes into one exception.

    Failures arrive as (a) isError=true with a bare `CODE: message` string,
    (b) isError=false with a JSON body whose top level is `error`, and (c)
    isError=false with `status: "failed"` plus a nested `error`. Checking only
    `isError` lets (b) and (c) through as empty results.
    """
    text = "".join(c.get("text", "") for c in result.get("content", []))
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        raise McpError(text.strip() or "Empty response from MCP",
                       code="VALIDATION_ERROR", raw=text)

    if result.get("isError"):
        raise McpError(text.strip(), code="TOOL_ERROR", raw=payload)
    if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
        err = payload["error"]
        raise McpError(err.get("message", "unknown error"),
                       code=err.get("code", "TOOL_ERROR"), raw=payload)
    if isinstance(payload, dict) and payload.get("status") == "failed":
        err = payload.get("error") or {}
        raise McpError(err.get("message", "The task failed."),
                       code=err.get("code", "FAILED"), raw=payload)
    return payload
