import logging

from .embeddings import embed
from .qdrant import COLLECTION, client

logger = logging.getLogger(__name__)


async def retrieve_passages(query: str, limit: int = 4) -> list[dict]:
    """Returns the raw matched book passages (title/page/text) for a query. Used both to
    build the tutor's book-context prompt and to surface citations in the chat UI."""
    try:
        qdrant = client()
        if not qdrant.collection_exists(COLLECTION):
            return []
        vectors = await embed([query])
        results = qdrant.query_points(COLLECTION, query=vectors[0], limit=limit).points
    except Exception:
        # Retrieval augments the tutor prompt but isn't essential to it — if Qdrant/Ollama
        # is unreachable or errors, fall back to no book context rather than breaking chat.
        logger.exception("RAG retrieval failed for query: %s", query)
        return []
    return [{"title": point.payload["title"], "page": point.payload["page"], "text": point.payload["text"]} for point in results]


async def retrieve(query: str, limit: int = 4) -> str:
    passages = await retrieve_passages(query, limit)
    return "\n\n".join(f"[{passage['title']}, p. {passage['page']}]\n{passage['text']}" for passage in passages)

