import httpx

from ..config import get_settings


async def embed(texts: list[str]) -> list[list[float]]:
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(f"{get_settings().ollama_host}/api/embed", json={"model": "nomic-embed-text", "input": texts})
        response.raise_for_status()
    return response.json()["embeddings"]
