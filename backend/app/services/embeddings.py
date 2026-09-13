import asyncio
import logging

import httpx

from ..config import get_settings

logger = logging.getLogger(__name__)

# Sending the whole book's chunks to Ollama in a single request routinely times out on
# CPU-bound embedding (thousands of chunks per book). Batching keeps each request small,
# so progress can be logged incrementally.
BATCH_SIZE = 8

# Ollama's /api/embed has exactly one processing slot on this box (confirmed via its own
# logs: it serializes every request). If our client times out and retries, the retry just
# queues up behind the still-running "abandoned" request (Ollama only notices we left once
# it tries — and fails — to write the response back), making retries actively harmful here.
# Since nothing synchronously waits on book indexing, there's no reason to time this out at
# all: we only bound the initial connection, and then wait as long as it takes for a reply.
REQUEST_TIMEOUT = httpx.Timeout(connect=10.0, read=None, write=None, pool=None)

# Keeps book indexing (and RAG query embedding) strictly sequential against Ollama's single
# processing slot, so concurrent uploads/queries queue safely instead of racing.
_embed_lock = asyncio.Lock()


async def embed(texts: list[str], context: str | None = None) -> list[list[float]]:
    settings = get_settings()
    vectors: list[list[float]] = []
    total = len(texts)
    async with _embed_lock, httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        for start in range(0, total, BATCH_SIZE):
            batch = texts[start : start + BATCH_SIZE]
            # This box's GPU (an old Kepler-era Quadro K600) crashes Ollama's Vulkan backend
            # ("device lost") partway through sustained embedding workloads. num_gpu=0 forces
            # CPU-only inference for this request, which is barely slower for an embedding
            # model this small and avoids the crash entirely.
            response = await client.post(
                f"{settings.ollama_host}/api/embed",
                json={"model": "nomic-embed-text", "input": batch, "options": {"num_gpu": 0}},
            )
            response.raise_for_status()
            vectors.extend(response.json()["embeddings"])
            # Only log progress for multi-batch calls (book indexing); a single-chunk RAG
            # query embed would otherwise add a noisy log line to every tutor message.
            if total > BATCH_SIZE:
                logger.info("Embedding progress%s: %d/%d chunks", f" for {context}" if context else "", len(vectors), total)
    return vectors
