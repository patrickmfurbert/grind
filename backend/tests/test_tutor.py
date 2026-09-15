import json

import httpx
import pytest
import respx


SSE_BODY = (
    'data: {"choices":[{"delta":{"content":"Why"}}]}\n\n'
    'data: {"choices":[{"delta":{"content":" do"}}]}\n\n'
    "data: [DONE]\n\n"
)

SUBSTANTIVE_RESPONSE = " ".join(["word"] * 50)


def _stub_mastery_eval(monkeypatch, score):
    import backend.app.routers.tutor as tutor_module

    async def fake_complete_json(messages, model_key="evaluation"):
        return {"score": score, "explanation": "stub"}

    monkeypatch.setattr(tutor_module, "complete_json", fake_complete_json)


def _stub_mastery_eval_raises(monkeypatch):
    import backend.app.routers.tutor as tutor_module

    async def fake_complete_json(messages, model_key="evaluation"):
        raise RuntimeError("evaluation model unreachable")

    monkeypatch.setattr(tutor_module, "complete_json", fake_complete_json)


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
    # A fresh session (no prior tutor turn) never qualifies for mastery evaluation, so
    # the trailing mastery event reports no update.
    assert response.text == (
        'data: {"token": "Why"}\n\n'
        'data: {"token": " do"}\n\n'
        'data: {"mastery_updated": false, "mastery_level": 0}\n\n'
        "data: [DONE]\n\n"
    )


@respx.mock
def test_chat_uses_teach_back_prompt_when_mode_is_teach_back(client):
    route = respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, content=SSE_BODY, headers={"content-type": "text/event-stream"})
    )

    response = client.post(
        "/tutor/chat",
        json={
            "concept_id": "why-distributed-systems-exist",
            "message": "Let me explain CAP theorem.",
            "conversation_history": [],
            "mode": "teach_back",
        },
    )
    assert response.status_code == 200
    sent_body = json.loads(route.calls.last.request.content)
    system_prompt = sent_body["messages"][0]["content"]
    assert "teach-back" in system_prompt.lower()
    assert "do not explain the concept yourself" in system_prompt.lower()


@respx.mock
def test_chat_uses_algo_pattern_prompt_for_phase_6_concept(client):
    """Phase 6 ("Algorithm Patterns") gets the explain-then-problem-then-walkthrough
    Socratic flow instead of the general open-ended tutor prompt."""
    route = respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, content=SSE_BODY, headers={"content-type": "text/event-stream"})
    )

    response = client.post(
        "/tutor/chat",
        json={"concept_id": "two-pointers-pattern", "message": "Explain this pattern.", "conversation_history": []},
    )
    assert response.status_code == 200
    sent_body = json.loads(route.calls.last.request.content)
    system_prompt = sent_body["messages"][0]["content"]
    assert "5 minutes" in system_prompt
    assert "walk through the solution together" in system_prompt.lower()


@respx.mock
def test_chat_uses_junior_engineer_teach_back_prompt_for_phase_6_concept(client):
    route = respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, content=SSE_BODY, headers={"content-type": "text/event-stream"})
    )

    response = client.post(
        "/tutor/chat",
        json={
            "concept_id": "two-pointers-pattern",
            "message": "Let me explain two pointers.",
            "conversation_history": [],
            "mode": "teach_back",
        },
    )
    assert response.status_code == 200
    sent_body = json.loads(route.calls.last.request.content)
    system_prompt = sent_body["messages"][0]["content"]
    assert "junior" in system_prompt.lower()


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


def _mastery_event(response_text):
    line = next(line for line in response_text.splitlines() if '"mastery_updated"' in line)
    return json.loads(line[len("data: "):])


@respx.mock
def test_mastery_never_updates_on_a_fresh_session_with_no_prior_tutor_turn(client, monkeypatch):
    """Even a long, substantive first message can't have been a response to a tutor
    challenge that never happened — mastery must never move on the opening turn."""
    _stub_mastery_eval(monkeypatch, score=5)
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, content=SSE_BODY, headers={"content-type": "text/event-stream"})
    )

    response = client.post(
        "/tutor/chat",
        json={"concept_id": "why-distributed-systems-exist", "message": SUBSTANTIVE_RESPONSE, "conversation_history": []},
    )
    assert response.status_code == 200
    assert _mastery_event(response.text) == {"mastery_updated": False, "mastery_level": 0}


@respx.mock
def test_mastery_never_updates_when_the_last_message_is_a_question(client, monkeypatch):
    _stub_mastery_eval(monkeypatch, score=5)
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, content=SSE_BODY, headers={"content-type": "text/event-stream"})
    )

    response = client.post(
        "/tutor/chat",
        json={
            "concept_id": "why-distributed-systems-exist",
            "message": "Can you explain that again in a different way?",
            "conversation_history": [{"role": "assistant", "content": "Why do you think distributed systems exist?"}],
        },
    )
    assert response.status_code == 200
    assert _mastery_event(response.text) == {"mastery_updated": False, "mastery_level": 0}


@respx.mock
def test_mastery_never_updates_for_a_response_under_the_word_minimum(client, monkeypatch):
    _stub_mastery_eval(monkeypatch, score=5)
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, content=SSE_BODY, headers={"content-type": "text/event-stream"})
    )

    response = client.post(
        "/tutor/chat",
        json={
            "concept_id": "why-distributed-systems-exist",
            "message": "Because one machine can't handle the load.",
            "conversation_history": [{"role": "assistant", "content": "Why do you think distributed systems exist?"}],
        },
    )
    assert response.status_code == 200
    assert _mastery_event(response.text) == {"mastery_updated": False, "mastery_level": 0}


@respx.mock
def test_mastery_updates_only_after_a_substantive_response_to_a_tutor_challenge(client, monkeypatch):
    _stub_mastery_eval(monkeypatch, score=5)
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, content=SSE_BODY, headers={"content-type": "text/event-stream"})
    )

    response = client.post(
        "/tutor/chat",
        json={
            "concept_id": "why-distributed-systems-exist",
            "message": SUBSTANTIVE_RESPONSE,
            "conversation_history": [{"role": "assistant", "content": "Why do you think distributed systems exist?"}],
        },
    )
    assert response.status_code == 200
    assert _mastery_event(response.text) == {"mastery_updated": True, "mastery_level": 1}


@respx.mock
def test_mastery_can_decrease_on_a_low_scoring_substantive_response(client, monkeypatch):
    _stub_mastery_eval(monkeypatch, score=1)
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, content=SSE_BODY, headers={"content-type": "text/event-stream"})
    )
    client.post("/progress/mastery", json={"concept_id": "why-distributed-systems-exist", "mastery_level": 3})

    response = client.post(
        "/tutor/chat",
        json={
            "concept_id": "why-distributed-systems-exist",
            "message": SUBSTANTIVE_RESPONSE,
            "conversation_history": [{"role": "assistant", "content": "Why do you think distributed systems exist?"}],
        },
    )
    assert response.status_code == 200
    event = _mastery_event(response.text)
    assert event["mastery_updated"] is True
    assert event["mastery_level"] == 2


@respx.mock
def test_mastery_eval_failure_reports_no_update_without_failing_the_chat(client, monkeypatch):
    """If the evaluation model errors, the tutor reply itself must still succeed — the
    conversation isn't held hostage by a best-effort mastery judgment."""
    _stub_mastery_eval_raises(monkeypatch)
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, content=SSE_BODY, headers={"content-type": "text/event-stream"})
    )

    response = client.post(
        "/tutor/chat",
        json={
            "concept_id": "why-distributed-systems-exist",
            "message": SUBSTANTIVE_RESPONSE,
            "conversation_history": [{"role": "assistant", "content": "Why do you think distributed systems exist?"}],
        },
    )
    assert response.status_code == 200
    assert '"token": "Why"' in response.text
    assert _mastery_event(response.text) == {"mastery_updated": False, "mastery_level": 0}


@respx.mock
def test_system_prompt_always_forbids_self_reported_mastery_and_requires_explain_back(client):
    """Guards against the tutor narrating its own fake mastery grade in the reply text
    (e.g. "Mastery level: 5/5 — well done!") and ensures every explanation is followed
    by asking Pat to explain the idea back, per the Socratic contract."""
    route = respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, content=SSE_BODY, headers={"content-type": "text/event-stream"})
    )

    response = client.post(
        "/tutor/chat",
        json={"concept_id": "why-distributed-systems-exist", "message": "Why does it exist?", "conversation_history": []},
    )
    assert response.status_code == 200
    system_prompt = json.loads(route.calls.last.request.content)["messages"][0]["content"]
    assert "never state a mastery level" in system_prompt.lower()
    assert "explain that idea back in their own words" in system_prompt.lower()


@respx.mock
def test_system_prompt_nudges_deeper_engagement_when_mastery_evaluation_is_skipped(client):
    route = respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, content=SSE_BODY, headers={"content-type": "text/event-stream"})
    )

    response = client.post(
        "/tutor/chat",
        json={
            "concept_id": "why-distributed-systems-exist",
            "message": "Can you say more about that?",
            "conversation_history": [{"role": "assistant", "content": "Why do you think distributed systems exist?"}],
        },
    )
    assert response.status_code == 200
    system_prompt = json.loads(route.calls.last.request.content)["messages"][0]["content"]
    assert "too brief to demonstrate real understanding" in system_prompt.lower()
