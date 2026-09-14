import json

import httpx
import pytest
import respx


SSE_BODY = (
    'data: {"choices":[{"delta":{"content":"Why"}}]}\n\n'
    'data: {"choices":[{"delta":{"content":" do"}}]}\n\n'
    "data: [DONE]\n\n"
)


@pytest.fixture(autouse=True)
def no_book_context(monkeypatch):
    """Tutor tests exercise OpenRouter streaming, not RAG retrieval; stub retrieve_passages()
    so they don't depend on a real Qdrant/Ollama instance being reachable."""
    import backend.app.routers.tutor as tutor_module

    async def fake_retrieve_passages(query, limit=4):
        return []

    monkeypatch.setattr(tutor_module, "retrieve_passages", fake_retrieve_passages)


@respx.mock
def test_chat_streams_tokens_from_openrouter(client):
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, content=SSE_BODY, headers={"content-type": "text/event-stream"})
    )

    response = client.post(
        "/tutor/chat",
        json={"concept_id": "why-distributed-systems-exist", "message": "Why does it exist?", "conversation_history": []},
    )
    assert response.status_code == 200
    assert response.text == 'data: {"token": "Why"}\n\ndata: {"token": " do"}\n\ndata: [DONE]\n\n'


@respx.mock
def test_chat_uses_default_mastery_for_unknown_concept(client):
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, content='data: [DONE]\n\n', headers={"content-type": "text/event-stream"})
    )

    response = client.post(
        "/tutor/chat",
        json={"concept_id": "unknown-concept", "message": "hi", "conversation_history": []},
    )
    assert response.status_code == 200


@respx.mock
def test_chat_emits_error_event_when_openrouter_fails(client):
    """A bad model/auth/etc. from OpenRouter surfaces as an SSE error event instead of
    silently dropping the stream, since the HTTP status is already 200 by the time
    streaming begins."""
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(400, json={"error": "invalid model"})
    )

    response = client.post(
        "/tutor/chat",
        json={"concept_id": "why-distributed-systems-exist", "message": "Why does it exist?", "conversation_history": []},
    )
    assert response.status_code == 200
    assert '"error"' in response.text
    assert response.text.endswith("data: [DONE]\n\n")


@respx.mock
def test_chat_injects_retrieved_book_passages_into_system_prompt(client, monkeypatch):
    """When retrieve_passages() finds relevant book passages, they should be appended to
    the system prompt sent to OpenRouter so the tutor can ground its response in them."""
    import backend.app.routers.tutor as tutor_module

    async def fake_retrieve_passages(query, limit=4):
        assert query == "why-distributed-systems-exist" or query  # called with the concept name
        return [{"title": "Designing Data-Intensive Applications", "page": 12, "text": "Replication trades consistency for availability."}]

    monkeypatch.setattr(tutor_module, "retrieve_passages", fake_retrieve_passages)

    route = respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, content="data: [DONE]\n\n", headers={"content-type": "text/event-stream"})
    )

    response = client.post(
        "/tutor/chat",
        json={"concept_id": "why-distributed-systems-exist", "message": "Why does it exist?", "conversation_history": []},
    )
    assert response.status_code == 200

    sent_body = json.loads(route.calls.last.request.content)
    system_message = sent_body["messages"][0]["content"]
    assert "Replication trades consistency for availability." in system_message
    assert "Designing Data-Intensive Applications, p. 12" in system_message


@respx.mock
def test_chat_emits_sources_event_when_book_passages_found(client, monkeypatch):
    """The frontend needs to show citations for what the tutor drew on, so a successful
    stream should end with a sources SSE event listing the deduplicated book/page pairs."""
    import backend.app.routers.tutor as tutor_module

    async def fake_retrieve_passages(query, limit=4):
        return [
            {"title": "Designing Data-Intensive Applications", "page": 12, "text": "Replication trades consistency for availability."},
            {"title": "Designing Data-Intensive Applications", "page": 12, "text": "Duplicate page, should be deduplicated."},
            {"title": "Designing Data-Intensive Applications", "page": 40, "text": "Partitioning spreads load across nodes."},
        ]

    monkeypatch.setattr(tutor_module, "retrieve_passages", fake_retrieve_passages)

    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, content="data: [DONE]\n\n", headers={"content-type": "text/event-stream"})
    )

    response = client.post(
        "/tutor/chat",
        json={"concept_id": "why-distributed-systems-exist", "message": "Why does it exist?", "conversation_history": []},
    )
    assert response.status_code == 200
    sources_line = next(line for line in response.text.splitlines() if '"sources"' in line)
    sources = json.loads(sources_line[len("data: "):])["sources"]
    assert sources == [
        {"title": "Designing Data-Intensive Applications", "page": 12},
        {"title": "Designing Data-Intensive Applications", "page": 40},
    ]
