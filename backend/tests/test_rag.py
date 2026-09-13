import httpx
import respx
from qdrant_client.http.models import ScoredPoint

from backend.app.services import rag


class FakeQdrant:
    def __init__(self, exists=True, points=None):
        self._exists = exists
        self._points = points or []

    def collection_exists(self, name):
        return self._exists

    def query_points(self, name, query, limit):
        class Result:
            points = self._points

        return Result()


def point(title, page, text):
    return ScoredPoint(id=1, version=0, score=0.9, payload={"title": title, "page": page, "text": text})


@respx.mock
async def test_retrieve_returns_empty_string_when_collection_missing(monkeypatch):
    monkeypatch.setattr(rag, "client", lambda: FakeQdrant(exists=False))

    result = await rag.retrieve("distributed systems")

    assert result == ""


@respx.mock
async def test_retrieve_formats_matches_with_title_and_page(monkeypatch):
    fake = FakeQdrant(points=[point("Kafka: The Definitive Guide", 42, "Partitions enable parallel consumption.")])
    monkeypatch.setattr(rag, "client", lambda: fake)
    respx.post("http://localhost:11434/api/embed").mock(
        return_value=httpx.Response(200, json={"embeddings": [[0.1, 0.2]]})
    )

    result = await rag.retrieve("how do partitions work")

    assert "[Kafka: The Definitive Guide, p. 42]" in result
    assert "Partitions enable parallel consumption." in result


async def test_retrieve_returns_empty_string_when_qdrant_unreachable(monkeypatch):
    def raise_connection_error():
        raise ConnectionError("qdrant unreachable")

    monkeypatch.setattr(rag, "client", raise_connection_error)

    result = await rag.retrieve("anything")

    assert result == ""
