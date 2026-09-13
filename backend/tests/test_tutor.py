import httpx
import respx


SSE_BODY = (
    'data: {"choices":[{"delta":{"content":"Why"}}]}\n\n'
    'data: {"choices":[{"delta":{"content":" do"}}]}\n\n'
    "data: [DONE]\n\n"
)


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
