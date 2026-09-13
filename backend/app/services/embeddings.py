import asyncio
import logging

import httpx

from ..config import get_settings

logger = logging.getLogger(__name__)

# Sending the whole book's chunks to Ollama in a single request routinely times out on
# CPU-bound embedding (thousands of chunks per book). Batching keeps each request small
# and fast, so one slow book can't blow past any single timeout. The Z420 also runs
# several other CPU-hungry containers alongside Ollama, so batches are kept small and
# generously timed out, with retries on transient timeouts before giving up on a batch.
BATCH_SIZE = 8
REQUEST_TIMEOUT = 300
MAX_RETRIES = 3

# Ollama serializes requests to a single model instance. If two books are uploaded close
# together, their embed calls interleave and queue up behind each other on the Ollama
# side, which can blow past any per-request timeout even though no individual batch is
# slow. This lock keeps book indexing (and RAG query embedding) strictly sequential.
_embed_lock = asyncio.Lock()


async def _embed_batch(client: httpx.AsyncClient, settings, batch: list[str]) -> list[list[float]]:
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = await client.post(f"{settings.ollama_host}/api/embed", json={"model": "nomic-embed-text", "input": batch})
            response.raise_for_status()
            return response.json()["embeddings"]
        except (httpx.TimeoutException, httpx.HTTPStatusError) as error:
            last_error = error
            logger.warning("Embed batch attempt %d/%d failed: %s", attempt, MAX_RETRIES, error)
    raise last_error


async def embed(texts: list[str], context: str | None = None) -> list[list[float]]:
    settings = get_settings()
    vectors: list[list[float]] = []
    total = len(texts)
    async with _embed_lock, httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        for start in range(0, total, BATCH_SIZE):
            batch = texts[start : start + BATCH_SIZE]
            vectors.extend(await _embed_batch(client, settings, batch))
            # Only log progress for multi-batch calls (book indexing); a single-chunk RAG
            # query embed would otherwise add a noisy log line to every tutor message.
            if total > BATCH_SIZE:
                logger.info("Embedding progress%s: %d/%d chunks", f" for {context}" if context else "", len(vectors), total)
    return vectors
