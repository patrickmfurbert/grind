CONCEPT_ID = "why-distributed-systems-exist"


def test_generate_returns_at_least_one_question(client):
    response = client.post(
        "/quiz/generate", json={"concept_id": CONCEPT_ID, "quiz_type": "comprehension", "use_book_rag": False}
    )
    assert response.status_code == 200
    questions = response.json()["questions"]
    assert questions and questions[0]["type"] == "comprehension"


def test_submit_high_score_marks_correct_and_schedules_future_review(client):
    response = client.post(
        "/quiz/submit",
        json={"concept_id": CONCEPT_ID, "question_id": "q1", "answer": "scale", "quiz_type": "comprehension", "score": 5},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is True
    assert "next_review_date" in body


def test_submit_low_score_marks_incorrect(client):
    response = client.post(
        "/quiz/submit",
        json={"concept_id": CONCEPT_ID, "question_id": "q1", "answer": "guess", "quiz_type": "comprehension", "score": 1},
    )
    assert response.status_code == 200
    assert response.json()["correct"] is False


def test_due_today_lists_only_concepts_with_a_past_next_review(client):
    # A future-scheduled review (score >= 3 -> interval_days=1) should not show up as due today.
    client.post(
        "/quiz/submit",
        json={"concept_id": CONCEPT_ID, "question_id": "q1", "answer": "scale", "quiz_type": "comprehension", "score": 4},
    )
    due = client.get("/quiz/due-today").json()["concepts"]
    assert not any(concept["id"] == CONCEPT_ID for concept in due)


def test_submit_rejects_score_outside_zero_to_five(client):
    response = client.post(
        "/quiz/submit",
        json={"concept_id": CONCEPT_ID, "question_id": "q1", "answer": "x", "quiz_type": "comprehension", "score": 9},
    )
    assert response.status_code == 422
