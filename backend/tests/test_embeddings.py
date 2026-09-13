import httpx
import pytest
import respx

from backend.app.services.embeddings import embed


@respx.mock
async def test_embed_batches_requests():
    """A total larger than BATCH_SIZE (8) should be split across multiple requests."""
    route = respx.post("http://localhost:11434/api/embed").mock(
        return_value=httpx.Response(200, json={"embeddings": [[0.1, 0.2]] * 8})
    )

    vectors = await embed([f"chunk {i}" for i in range(20)])

    assert len(vectors) == 24  # 3 batches of 8 mocked responses each
    assert route.call_count == 3


@respx.mock
async def test_embed_retries_on_timeout_then_succeeds():
    route = respx.post("http://localhost:11434/api/embed").mock(
        side_effect=[httpx.TimeoutException("slow"), httpx.Response(200, json={"embeddings": [[0.1]]})]
    )

    vectors = await embed(["one chunk"])

    assert vectors == [[0.1]]
    assert route.call_count == 2


@respx.mock
async def test_embed_gives_up_after_max_retries():
    respx.post("http://localhost:11434/api/embed").mock(side_effect=httpx.TimeoutException("always slow"))

    with pytest.raises(httpx.TimeoutException):
        await embed(["one chunk"])
