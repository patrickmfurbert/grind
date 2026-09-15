import pytest

CONCEPT_ID = "why-distributed-systems-exist"
OTHER_CONCEPT_ID = "why-distributed-systems-fail"

MCQ_GENERATE_RESPONSE = {
    "questions": [
        {
            "type": "multiple_choice",
            "prompt": "Why do distributed systems exist?",
            "options": ["To scale beyond one machine", "To make debugging easier", "To avoid using a database", "To reduce code size"],
            "correct_answer": "To scale beyond one machine",
        }
    ]
}

FREE_RESPONSE_GENERATE_RESPONSE = {
    "questions": [
        {
            "type": "free_response",
            "prompt": "Explain why this concept exists and name a trade-off it creates.",
            "correct_answer": "Distributed systems trade simplicity for scale/availability.",
        }
    ]
}


def _stub_generate(monkeypatch, response):
    import backend.app.routers.quiz as quiz_module

    async def fake_complete_json(messages, model_key="quiz_gen"):
        return response

    monkeypatch.setattr(quiz_module, "complete_json", fake_complete_json)


def test_generate_returns_multiple_choice_questions_for_comprehension(client, monkeypatch):
    _stub_generate(monkeypatch, MCQ_GENERATE_RESPONSE)

    response = client.post(
        "/quiz/generate", json={"concept_id": CONCEPT_ID, "quiz_type": "comprehension", "use_book_rag": False, "include_interleaved": False}
    )
    assert response.status_code == 200
    questions = response.json()["questions"]
    assert questions[0]["type"] == "multiple_choice"
    assert questions[0]["options"] == MCQ_GENERATE_RESPONSE["questions"][0]["options"]
    assert questions[0]["concept_id"] == CONCEPT_ID
    # correct_answer must never be sent to the client
    assert "correct_answer" not in questions[0]


def test_generate_unknown_concept_returns_404(client, monkeypatch):
    _stub_generate(monkeypatch, MCQ_GENERATE_RESPONSE)

    response = client.post(
        "/quiz/generate", json={"concept_id": "not-a-real-concept", "quiz_type": "comprehension", "use_book_rag": False}
    )
    assert response.status_code == 404


def test_generate_asks_the_llm_to_avoid_repeating_recently_seen_prompts(client, monkeypatch):
    import backend.app.routers.quiz as quiz_module

    seen_prompts = []

    async def fake_complete_json(messages, model_key="quiz_gen"):
        seen_prompts.append(messages[0]["content"])
        return MCQ_GENERATE_RESPONSE

    monkeypatch.setattr(quiz_module, "complete_json", fake_complete_json)

    # First generation: no history yet, so no "already seen" section.
    client.post("/quiz/generate", json={"concept_id": CONCEPT_ID, "quiz_type": "comprehension", "use_book_rag": False, "include_interleaved": False})
    assert "already seen these questions" not in seen_prompts[0]

    # Second generation: the previously generated prompt should be fed back so the
    # model rotates to something new instead of repeating itself.
    client.post("/quiz/generate", json={"concept_id": CONCEPT_ID, "quiz_type": "comprehension", "use_book_rag": False, "include_interleaved": False})
    assert "already seen these questions" in seen_prompts[1]
    assert MCQ_GENERATE_RESPONSE["questions"][0]["prompt"] in seen_prompts[1]


def test_generate_surfaces_502_when_llm_fails(client, monkeypatch):
    import backend.app.routers.quiz as quiz_module

    async def failing_complete_json(messages, model_key="quiz_gen"):
        raise RuntimeError("openrouter down")

    monkeypatch.setattr(quiz_module, "complete_json", failing_complete_json)

    response = client.post(
        "/quiz/generate", json={"concept_id": CONCEPT_ID, "quiz_type": "comprehension", "use_book_rag": False}
    )
    assert response.status_code == 502


def test_generate_mixes_in_one_interleaved_question_from_the_weakest_studied_concept(client, monkeypatch):
    """Interleaving mixes a quick recall question from a different, already-studied
    concept into the current quiz, so practice isn't purely blocked on one topic."""
    _stub_generate(monkeypatch, MCQ_GENERATE_RESPONSE)
    # Mark a different concept as previously studied (and weak) so it's eligible to be
    # picked as the interleaved concept.
    client.post("/progress/mastery", json={"concept_id": OTHER_CONCEPT_ID, "mastery_level": 1})

    response = client.post(
        "/quiz/generate", json={"concept_id": CONCEPT_ID, "quiz_type": "comprehension", "use_book_rag": False, "include_interleaved": True}
    )
    questions = response.json()["questions"]
    assert len(questions) == 2
    concept_ids = {question["concept_id"] for question in questions}
    assert concept_ids == {CONCEPT_ID, OTHER_CONCEPT_ID}


def test_generate_skips_interleaving_when_no_other_concept_has_been_studied(client, monkeypatch):
    _stub_generate(monkeypatch, MCQ_GENERATE_RESPONSE)

    response = client.post(
        "/quiz/generate", json={"concept_id": CONCEPT_ID, "quiz_type": "comprehension", "use_book_rag": False, "include_interleaved": True}
    )
    questions = response.json()["questions"]
    assert len(questions) == 1


def test_submit_multiple_choice_correct_answer_is_graded_instantly_and_raises_mastery(client, monkeypatch):
    _stub_generate(monkeypatch, MCQ_GENERATE_RESPONSE)
    question_id = client.post(
        "/quiz/generate", json={"concept_id": CONCEPT_ID, "quiz_type": "comprehension", "use_book_rag": False, "include_interleaved": False}
    ).json()["questions"][0]["id"]

    response = client.post("/quiz/submit", json={"question_id": question_id, "answer": "To scale beyond one machine"})
    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is True
    assert body["mastery_level"] == 1
    assert body["concept_id"] == CONCEPT_ID
    assert "next_review_date" in body


def test_submit_multiple_choice_wrong_answer_lowers_mastery_and_explains_correct_answer(client, monkeypatch):
    _stub_generate(monkeypatch, MCQ_GENERATE_RESPONSE)
    question_id = client.post(
        "/quiz/generate", json={"concept_id": CONCEPT_ID, "quiz_type": "comprehension", "use_book_rag": False, "include_interleaved": False}
    ).json()["questions"][0]["id"]

    response = client.post("/quiz/submit", json={"question_id": question_id, "answer": "To reduce code size"})
    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is False
    assert body["mastery_level"] == 0
    assert "To scale beyond one machine" in body["explanation"]


def test_submit_unknown_question_returns_404(client):
    response = client.post("/quiz/submit", json={"question_id": "not-a-real-question", "answer": "anything"})
    assert response.status_code == 404


def test_submit_free_response_is_graded_by_the_evaluation_model_and_reports_the_gap(client, monkeypatch):
    import backend.app.routers.quiz as quiz_module

    _stub_generate(monkeypatch, FREE_RESPONSE_GENERATE_RESPONSE)
    question_id = client.post(
        "/quiz/generate", json={"concept_id": CONCEPT_ID, "quiz_type": "application", "use_book_rag": False, "include_interleaved": False}
    ).json()["questions"][0]["id"]

    async def fake_grade(messages, model_key="quiz_gen"):
        assert model_key == "evaluation"
        return {"score": 4, "explanation": "Good answer, minor gap on availability trade-off.", "gap": "Didn't mention availability during partitions."}

    monkeypatch.setattr(quiz_module, "complete_json", fake_grade)

    response = client.post("/quiz/submit", json={"question_id": question_id, "answer": "It lets you scale horizontally."})
    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is True
    assert body["score"] == 4
    assert "availability trade-off" in body["explanation"]
    assert body["gap"] == "Didn't mention availability during partitions."


def test_submit_free_response_grading_failure_falls_back_to_partial_pass(client, monkeypatch):
    import backend.app.routers.quiz as quiz_module

    _stub_generate(monkeypatch, FREE_RESPONSE_GENERATE_RESPONSE)
    question_id = client.post(
        "/quiz/generate", json={"concept_id": CONCEPT_ID, "quiz_type": "application", "use_book_rag": False, "include_interleaved": False}
    ).json()["questions"][0]["id"]

    async def failing_grade(messages, model_key="quiz_gen"):
        raise RuntimeError("evaluation model down")

    monkeypatch.setattr(quiz_module, "complete_json", failing_grade)

    response = client.post("/quiz/submit", json={"question_id": question_id, "answer": "some answer"})
    assert response.status_code == 200
    assert response.json()["score"] == 3


def test_hint_returns_a_scaffolded_hint_without_the_answer(client, monkeypatch):
    import backend.app.routers.quiz as quiz_module

    _stub_generate(monkeypatch, FREE_RESPONSE_GENERATE_RESPONSE)
    question_id = client.post(
        "/quiz/generate", json={"concept_id": CONCEPT_ID, "quiz_type": "application", "use_book_rag": False, "include_interleaved": False}
    ).json()["questions"][0]["id"]

    async def fake_hint(messages, model_key="quiz_gen"):
        return {"hint": "Think about what happens to a single machine under heavy load."}

    monkeypatch.setattr(quiz_module, "complete_json", fake_hint)

    response = client.post("/quiz/hint", json={"question_id": question_id})
    assert response.status_code == 200
    assert response.json()["hint"] == "Think about what happens to a single machine under heavy load."


def test_hint_surfaces_502_when_llm_fails(client, monkeypatch):
    import backend.app.routers.quiz as quiz_module

    _stub_generate(monkeypatch, FREE_RESPONSE_GENERATE_RESPONSE)
    question_id = client.post(
        "/quiz/generate", json={"concept_id": CONCEPT_ID, "quiz_type": "application", "use_book_rag": False, "include_interleaved": False}
    ).json()["questions"][0]["id"]

    async def failing_hint(messages, model_key="quiz_gen"):
        raise RuntimeError("openrouter down")

    monkeypatch.setattr(quiz_module, "complete_json", failing_hint)

    response = client.post("/quiz/hint", json={"question_id": question_id})
    assert response.status_code == 502


def test_hint_unknown_question_returns_404(client):
    response = client.post("/quiz/hint", json={"question_id": "not-a-real-question"})
    assert response.status_code == 404


def test_due_today_lists_only_concepts_with_a_past_next_review(client, monkeypatch):
    _stub_generate(monkeypatch, MCQ_GENERATE_RESPONSE)
    question_id = client.post(
        "/quiz/generate", json={"concept_id": CONCEPT_ID, "quiz_type": "comprehension", "use_book_rag": False, "include_interleaved": False}
    ).json()["questions"][0]["id"]

    # A correct answer schedules a future review, so it shouldn't show up as due today.
    client.post("/quiz/submit", json={"question_id": question_id, "answer": "To scale beyond one machine"})
    due = client.get("/quiz/due-today").json()["concepts"]
    assert not any(concept["id"] == CONCEPT_ID for concept in due)
