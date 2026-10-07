"""Start here. Run:  .venv/bin/python -m uvicorn src.main:app --reload  → http://localhost:8000

HTTP routes. The browser talks only to this server — never to MCP or the gateway.
Two reasons: the team's API keys must not reach the browser, and the MCP server
sends no CORS headers, so a direct fetch from the page would be blocked anyway.

Every /api/* route except /api/firebase-config needs a signed-in user (src/auth.py).

  /api/search/text    search_products_by_text        — one call
  /api/search/image   search_products_by_image        — one call
  /api/scene/start +
  /api/scene/result   start_scene_match / get_scene_match_result — two steps,
                       the browser polls /api/scene/result itself (see static/app.js)
  /api/video/start +
  /api/video/result   start_video_match / get_video_match_result — the same two steps
  /api/llm/check      one LLM gateway call
  /api/tool-call      one tool call, end to end — the model asks, this app runs it on
                       MCP, the model answers
"""
import json
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import llm_client
from .auth import require_user
from .config import (FIREBASE_API_KEY, FIREBASE_APP_ID, FIREBASE_AUTH_DOMAIN,
                     FIREBASE_MESSAGING_SENDER_ID, FIREBASE_PROJECT_ID,
                     FIREBASE_STORAGE_BUCKET, ROOT)
from .llm_client import LlmError
from .mcp_client import McpClient, McpError

STATIC = ROOT / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.mcp = McpClient()
    yield
    await app.state.mcp.aclose()


app = FastAPI(title="AISUM Hackathon Starter Kit", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


def _mcp_error(e: McpError, **extra) -> JSONResponse:
    raw = e.raw if e.raw is None or isinstance(e.raw, str) else json.dumps(e.raw)
    return JSONResponse({"error": f"{e.code}: {e}", "raw": raw and raw[:500], **extra},
                        status_code=502)


# ── Page and Firebase config (no sign-in needed) ─────────────────────────

@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/firebase-config")
async def firebase_config():
    """The one place the browser learns which Firebase project it's talking to.

    static/auth.js fetches this before calling initializeApp — so switching project
    (personal account -> company project -> your team's project) is an env-var
    change on this server, never a code change in the browser bundle.
    """
    return {
        "apiKey": FIREBASE_API_KEY,
        "authDomain": FIREBASE_AUTH_DOMAIN,
        "projectId": FIREBASE_PROJECT_ID,
        "storageBucket": FIREBASE_STORAGE_BUCKET,
        "messagingSenderId": FIREBASE_MESSAGING_SENDER_ID,
        "appId": FIREBASE_APP_ID,
    }


# ── 1–2. One-call MCP tools ──────────────────────────────────────────────
# Field names match the tool's arguments, so the request body passes straight through.
# `uid` is the verified Firebase user — unused here, it's where per-user features hook in.

# The tool accepts more than this. Your team documentation lists the rest.
class TextSearch(BaseModel):
    query: str


@app.post("/api/search/text")
async def search_text(req: TextSearch, uid: str = Depends(require_user)):
    try:
        return await app.state.mcp.call("search_products_by_text",
                                         req.model_dump(exclude_none=True))
    except McpError as e:
        return _mcp_error(e)


# The tool accepts more than this. Your team documentation lists the rest.
class ImageSearch(BaseModel):
    image_url: str


@app.post("/api/search/image")
async def search_image(req: ImageSearch, uid: str = Depends(require_user)):
    try:
        return await app.state.mcp.call("search_products_by_image",
                                         req.model_dump(exclude_none=True))
    except McpError as e:
        return _mcp_error(e)


# ── 3–4. Two-step MCP tools: start once, then ask again with the same task_id ──

class SceneStart(BaseModel):
    title: str
    image_url: str


@app.post("/api/scene/start")
async def scene_start(req: SceneStart, uid: str = Depends(require_user)):
    try:
        return await app.state.mcp.call("start_scene_match", req.model_dump())
    except McpError as e:
        return _mcp_error(e)


@app.get("/api/scene/result/{task_id}")
async def scene_result(task_id: str, uid: str = Depends(require_user)):
    return await _poll("get_scene_match_result", task_id)


class VideoStart(BaseModel):
    video_url: str


@app.post("/api/video/start")
async def video_start(req: VideoStart, uid: str = Depends(require_user)):
    try:
        return await app.state.mcp.call("start_video_match", req.model_dump())
    except McpError as e:
        return _mcp_error(e)


@app.get("/api/video/result/{task_id}")
async def video_result(task_id: str, uid: str = Depends(require_user)):
    return await _poll("get_video_match_result", task_id)


async def _poll(tool: str, task_id: str):
    """One ask. The browser calls this repeatedly with the SAME task_id — see
    static/app.js's polling loop. Nothing here ever starts the job again.
    """
    try:
        return await app.state.mcp.call(tool, {"task_id": task_id})
    except McpError as e:
        # A job that has not started yet can answer NOT_FOUND instead of pending.
        # Treat it as pending: obeying the literal message would mean starting the
        # job again, forever. No record of "tasks we started" is kept — on Cloud Run
        # the next ask may reach another instance, which would not have it.
        if e.code == "NOT_FOUND":
            return {"status": "pending", "task_id": task_id}
        return _mcp_error(e)


# ── 5. One LLM call ──────────────────────────────────────────────────────

class LlmCheck(BaseModel):
    prompt: str = "Say hello in one short sentence."


@app.post("/api/llm/check")
async def llm_check(req: LlmCheck, uid: str = Depends(require_user)):
    try:
        choice = await llm_client.chat([{"role": "user", "content": req.prompt}])
    except (LlmError, httpx.HTTPError) as e:
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=502)
    return {"text": choice["message"].get("content"),
            "finish_reason": choice["finish_reason"]}


# ── 6. One tool call, end to end ─────────────────────────────────────────

DEMO_TOOL = "search_products_by_text"


class ToolCallDemo(BaseModel):
    question: str


@app.post("/api/tool-call")
async def tool_call(req: ToolCallDemo, uid: str = Depends(require_user)):
    """One tool call, end to end — the four steps an agent repeats, done once.

    A connection check, not a pattern to copy: write your own loop or use any SDK or
    framework — the messages on the wire are the same, and this shows them. No loop,
    no memory, one tool. `report` is only for the page; the four numbered blocks are
    the wiring.
    """
    report: list[dict] = []
    try:
        tools = [await _tool_for_llm(DEMO_TOOL)]
        messages = [{"role": "user", "content": req.question}]

        # 1  model — in: the question + the tool's schema.
        #    out: an answer, or tool_calls = [{id, function: {name, arguments}}],
        #    where `arguments` is a JSON *string* the model wrote.
        t = time.perf_counter()
        reply = await llm_client.chat(messages, tools)
        calls = reply["message"].get("tool_calls") or []
        report.append(_step(1, t, finish_reason=reply["finish_reason"],
                            tool_calls=[{"id": c["id"], **c["function"]} for c in calls],
                            content=reply["message"].get("content")))
        if not calls:
            return {"steps": report, "note": "The model answered without calling the "
                    "tool, so there is nothing for steps 2-4 to do."}

        # 2  app — run the first requested call on MCP. A model may ask for several
        #    at once; running them all would already be a design decision.
        call = calls[0]
        name, args = call["function"]["name"], json.loads(call["function"]["arguments"])
        t = time.perf_counter()
        result = await app.state.mcp.call(name, args)
        report.append(_step(2, t, tool=name, arguments=args, result=result))

        # 3  app — send back the model's own message unchanged (it may carry
        #    reasoning fields), then the result as role "tool" with the SAME call id.
        messages += [reply["message"],
                     {"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result)}]
        report.append(_step(3, messages_sent=[m["role"] for m in messages],
                            tool_content_chars=len(messages[-1]["content"])))

        # 4  model — in: everything so far. out: an answer in words.
        t = time.perf_counter()
        final = await llm_client.chat(messages, tools)
        report.append(_step(4, t, finish_reason=final["finish_reason"],
                            content=final["message"].get("content"),
                            # A loop would run this next call; this demo stops here.
                            asked_for_another_call=bool(final["message"].get("tool_calls"))))
        return {"steps": report}
    except McpError as e:
        return _mcp_error(e, steps=report)
    except json.JSONDecodeError as e:
        # The model's `arguments` is a string it wrote; nothing guarantees it parses.
        return JSONResponse({"steps": report, "error": f"The model's tool arguments are "
                                                       f"not valid JSON: {e}"},
                            status_code=502)
    except (LlmError, httpx.HTTPError) as e:
        return JSONResponse({"steps": report, "error": f"{type(e).__name__}: {e}"},
                            status_code=502)


async def _tool_for_llm(name: str) -> dict:
    """An MCP tool, in the shape a chat call's `tools` list expects:
    {"type": "function", "function": {name, description, parameters}}.

    MCP's `inputSchema` and the chat API's `parameters` are both JSON Schema, so the
    schema passes through unchanged.
    """
    available = await app.state.mcp.list_tools()
    spec = next((t for t in available if t["name"] == name), None)
    if spec is None:
        raise McpError(f"No tool named {name!r} on the server. Available: "
                       f"{', '.join(t['name'] for t in available)}", code="UNKNOWN_TOOL")
    return {"type": "function", "function": {
        "name": spec["name"], "description": spec.get("description", ""),
        "parameters": spec["inputSchema"]}}


def _step(n: int, started: float | None = None, **fields) -> dict:
    """One entry of the page's report: the step number, seconds since `started`."""
    if started is not None:
        fields["seconds"] = round(time.perf_counter() - started, 2)
    return {"step": n, **fields}
