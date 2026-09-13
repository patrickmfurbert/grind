from .embeddings import embed
from .qdrant import COLLECTION, client


async def retrieve(query: str, limit: int = 4) -> str:
    vectors = await embed([query])
    results = client().query_points(COLLECTION, query=vectors[0], limit=limit).points
    return "\n\n".join(f"[{point.payload['title']}, p. {point.payload['page']}]\n{point.payload['text']}" for point in results)
