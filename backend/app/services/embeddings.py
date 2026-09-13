import httpx

from ..config import get_settings

# Sending the whole book's chunks to Ollama in a single request routinely times out on
# CPU-bound embedding (thousands of chunks per book). Batching keeps each request small
# and fast, so one slow book can't blow past any single timeout.
BATCH_SIZE = 16
REQUEST_TIMEOUT = 120


async def embed(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    vectors: list[list[float]] = []
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        for start in range(0, len(texts), BATCH_SIZE):
            batch = texts[start : start + BATCH_SIZE]
            response = await client.post(f"{settings.ollama_host}/api/embed", json={"model": "nomic-embed-text", "input": batch})
            response.raise_for_status()
            vectors.extend(response.json()["embeddings"])
    return vectors
