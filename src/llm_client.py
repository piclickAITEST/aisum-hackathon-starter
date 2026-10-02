"""One call to the LLM gateway — no SDK, no agent loop.

The gateway (LiteLLM, OpenAI-compatible) is one of the four things a team is given
(MCP key, LLM key, Firebase, Cloud Run). This module shows the call shape and nothing
else: what you do with the model's answer is product design, not wiring.
"""
import httpx

from .config import MODEL, OPENAI_API_KEY, OPENAI_BASE_URL

_TIMEOUT = 30.0


async def chat_once(prompt: str, model: str = MODEL) -> str:
    """POST /chat/completions once and return the reply text. Raises on HTTP failure."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.post(
            f"{OPENAI_BASE_URL.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}]},
        )
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]
