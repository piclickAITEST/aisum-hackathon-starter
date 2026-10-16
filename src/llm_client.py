"""Calls to the LLM gateway — no SDK, no agent loop.

The gateway (LiteLLM, OpenAI-compatible) is one of the four things a team is given
(MCP key, LLM key, Firebase, Cloud Run). This module shows the call shape and nothing
else: what you do with the model's answer is product design, not wiring.
"""
import httpx

from .config import MODEL, OPENAI_API_KEY, OPENAI_BASE_URL

# The model reasons before it answers, and a request that carries tool results is
# longer than a hello. 30s was enough for a one-liner and not much more.
_TIMEOUT = 60.0


class LlmError(RuntimeError):
    pass


async def chat(messages: list[dict], tools: list[dict] | None = None,
               model: str = MODEL) -> dict:
    """POST /chat/completions once and return choices[0]: {message, finish_reason}.

    No max_tokens on purpose. The model is a reasoning model and max_tokens caps
    reasoning and answer together — set it low and you get 200 OK with empty content
    and finish_reason "length" (docs/troubleshooting.md).
    """
    body = {"model": model, "messages": messages}
    if tools:
        body["tools"] = tools
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.post(
            f"{OPENAI_BASE_URL.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json=body,
        )
    if r.is_error:
        # The body says which: an unknown model, a key not allowed that model, a bad
        # key, or a team budget that is used up. The status code alone does not.
        hint = ("team budget used up — run python -m src.budget"
                if r.status_code == 429 and "budget_exceeded" in r.text
                else "check OPENAI_BASE_URL / OPENAI_API_KEY / MODEL")
        raise LlmError(f"LLM gateway answered HTTP {r.status_code}: {r.text[:300]} — {hint}")
    return r.json()["choices"][0]
