import logging

from .embeddings import embed
from .qdrant import COLLECTION, client

logger = logging.getLogger(__name__)


async def retrieve(query: str, limit: int = 4) -> str:
    try:
        qdrant = client()
        if not qdrant.collection_exists(COLLECTION):
            return ""
        vectors = await embed([query])
        results = qdrant.query_points(COLLECTION, query=vectors[0], limit=limit).points
    except Exception:
        # Retrieval augments the tutor prompt but isn't essential to it — if Qdrant/Ollama
        # is unreachable or errors, fall back to no book context rather than breaking chat.
        logger.exception("RAG retrieval failed for query: %s", query)
        return ""
    return "\n\n".join(f"[{point.payload['title']}, p. {point.payload['page']}]\n{point.payload['text']}" for point in results)

