from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from ..config import get_settings

COLLECTION = "grind_books"


def client() -> QdrantClient:
    settings = get_settings()
    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


def index_chunks(points: list[PointStruct], dimensions: int) -> None:
    qdrant = client()
    if not qdrant.collection_exists(COLLECTION):
        qdrant.create_collection(COLLECTION, vectors_config=VectorParams(size=dimensions, distance=Distance.COSINE))
    qdrant.upsert(COLLECTION, points)
