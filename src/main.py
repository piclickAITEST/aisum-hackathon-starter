"""HTTP routes. The browser talks only to this server — never to MCP or the gateway.

Two reasons: the team's API keys must not reach the browser, and the MCP server
sends no CORS headers, so a direct fetch from the page would be blocked anyway.

Three MCP call patterns, one route each:
  /api/search/text    search_products_by_text        — single call, fast
  /api/search/image   search_products_by_image        — single call, slower
  /api/scene/start +
  /api/scene/result   start_scene_match / get_scene_match_result — two steps,
                       the browser polls /api/scene/result itself (see static/app.js)
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import llm_client
from .config import (FIREBASE_API_KEY, FIREBASE_APP_ID, FIREBASE_AUTH_DOMAIN,
                     FIREBASE_MESSAGING_SENDER_ID, FIREBASE_PROJECT_ID,
                     FIREBASE_STORAGE_BUCKET, ROOT)
from .mcp_client import McpClient, McpError

STATIC = ROOT / "static"

# task_ids this process started — see mcp_client.py's module docstring and
# get_scene_match_result's NOT_FOUND handling below. In-memory on purpose: this is a
# teaching example for one person at a time, not a durable job store.
_started_scene_tasks: set[str] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.mcp = McpClient()
    yield
    await app.state.mcp.aclose()


app = FastAPI(title="AISUM Hackathon Starter Kit", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


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


class TextSearch(BaseModel):
    query: str
    domain: str | None = None
    max_price: float | None = None
    min_price: float | None = None
    gender: str | None = None


@app.post("/api/search/text")
async def search_text(req: TextSearch):
    args = {"query": req.query}
    for k in ("domain", "max_price", "min_price", "gender"):
        v = getattr(req, k)
        if v is not None:
            args[k] = v
    try:
        return await app.state.mcp.call("search_products_by_text", args)
    except McpError as e:
        return JSONResponse({"error": f"{e.code}: {e}"}, status_code=502)


class ImageSearch(BaseModel):
    image_url: str
    category: str | None = None
    max_price: float | None = None
    min_price: float | None = None
    gender: str | None = None


@app.post("/api/search/image")
async def search_image(req: ImageSearch):
    args = {"image_url": req.image_url}
    for k in ("category", "max_price", "min_price", "gender"):
        v = getattr(req, k)
        if v is not None:
            args[k] = v
    try:
        return await app.state.mcp.call("search_products_by_image", args)
    except McpError as e:
        return JSONResponse({"error": f"{e.code}: {e}"}, status_code=502)


class SceneStart(BaseModel):
    title: str
    image_url: str


@app.post("/api/scene/start")
async def scene_start(req: SceneStart):
    try:
        result = await app.state.mcp.call(
            "start_scene_match", {"title": req.title, "image_url": req.image_url})
    except McpError as e:
        return JSONResponse({"error": f"{e.code}: {e}"}, status_code=502)
    task_id = result.get("task_id")
    if task_id:
        _started_scene_tasks.add(task_id)
    return result


@app.get("/api/scene/result/{task_id}")
async def scene_result(task_id: str):
    """One poll attempt. The browser calls this repeatedly with the SAME task_id —
    see static/app.js's explicit polling loop. This route never resubmits the job.
    """
    try:
        return await app.state.mcp.call("get_scene_match_result", {"task_id": task_id})
    except McpError as e:
        # The job is queued, not missing — a NOT_FOUND for a task_id we started
        # ourselves gets reinterpreted as still-pending instead of surfaced as an
        # error. Obeying the literal message would mean resubmitting forever.
        if e.code == "NOT_FOUND" and task_id in _started_scene_tasks:
            return {"status": "pending", "task_id": task_id}
        return JSONResponse({"error": f"{e.code}: {e}"}, status_code=502)


class LlmCheck(BaseModel):
    prompt: str = "Say hello in one short sentence."


@app.post("/api/llm/check")
async def llm_check(req: LlmCheck):
    try:
        text = await llm_client.chat_once(req.prompt)
    except Exception as e:
        return JSONResponse(
            {"error": f"{type(e).__name__}: {e} — check OPENAI_BASE_URL / "
                      f"OPENAI_API_KEY (this is the LLM key, not the MCP key)"},
            status_code=502)
    return {"text": text}
