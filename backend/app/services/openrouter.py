import json
from collections.abc import AsyncIterator

import httpx

from ..config import get_settings

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODELS = {
    "tutor_fast": "meta-llama/llama-3.3-70b-instruct",
    "tutor_quality": "anthropic/claude-haiku-4.5",
    "content_gen": "deepseek/deepseek-v4-flash",
    "evaluation": "anthropic/claude-sonnet-5",
    "quiz_gen": "deepseek/deepseek-v4-flash",
}


async def stream_chat(messages: list[dict[str, str]], model_key: str = "tutor_fast") -> AsyncIterator[str]:
    key = get_settings().openrouter_api_key
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")
    payload = {"model": MODELS[model_key], "messages": messages, "stream": True}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream("POST", f"{OPENROUTER_BASE_URL}/chat/completions", headers=headers, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: ") or line == "data: [DONE]":
                    continue
                data = json.loads(line[6:])
                content = data["choices"][0].get("delta", {}).get("content")
                if content:
                    yield content
