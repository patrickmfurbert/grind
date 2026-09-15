def test_summary_defaults_to_zero_pct_and_no_streak(client):
    response = client.get("/progress/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["overall_pct"] == 0
    assert body["streak"] == 0
    assert isinstance(body["by_phase"], list) and body["by_phase"]


def test_update_mastery_is_reflected_in_summary(client):
    concept_id = "why-distributed-systems-exist"
    response = client.post("/progress/mastery", json={"concept_id": concept_id, "mastery_level": 5})
    assert response.status_code == 200
    assert response.json() == {"updated": True}

    summary = client.get("/progress/summary").json()
    assert summary["overall_pct"] > 0


def test_update_mastery_rejects_out_of_range_level(client):
    response = client.post(
        "/progress/mastery", json={"concept_id": "why-distributed-systems-exist", "mastery_level": 7}
    )
    assert response.status_code == 422


def test_weak_spots_excludes_unstudied_and_fully_mastered_concepts(client):
    client.post("/progress/mastery", json={"concept_id": "why-distributed-systems-exist", "mastery_level": 1})
    client.post("/progress/mastery", json={"concept_id": "why-distributed-systems-fail", "mastery_level": 5})

    response = client.get("/progress/weak-spots")
    assert response.status_code == 200
    ids = [concept["id"] for concept in response.json()["concepts"]]
    assert "why-distributed-systems-exist" in ids
    # Fully mastered and never-studied concepts shouldn't show up as weak spots.
    assert "why-distributed-systems-fail" not in ids


def test_weak_spots_sorts_weakest_first(client):
    client.post("/progress/mastery", json={"concept_id": "why-distributed-systems-exist", "mastery_level": 3})
    client.post("/progress/mastery", json={"concept_id": "why-distributed-systems-fail", "mastery_level": 1})

    ids = [concept["id"] for concept in client.get("/progress/weak-spots").json()["concepts"]]
    assert ids.index("why-distributed-systems-fail") < ids.index("why-distributed-systems-exist")


def test_weak_spots_ranks_by_wrong_count_before_mastery(client, monkeypatch):
    """A concept missed twice on quizzes should outrank a lower-mastery concept that has
    never been answered wrong, since wrong_count is the primary sort key."""
    import backend.app.routers.quiz as quiz_module

    frequently_missed = "why-distributed-systems-exist"
    merely_low_mastery = "why-distributed-systems-fail"

    async def fake_complete_json(messages, model_key="quiz_gen"):
        return {
            "questions": [
                {
                    "type": "multiple_choice",
                    "prompt": "Q",
                    "options": ["right", "wrong"],
                    "correct_answer": "right",
                }
            ]
        }

    monkeypatch.setattr(quiz_module, "complete_json", fake_complete_json)

    for _ in range(2):
        questions = client.post(
            "/quiz/generate",
            json={"concept_id": frequently_missed, "quiz_type": "comprehension", "use_book_rag": False, "include_interleaved": False},
        ).json()["questions"]
        client.post("/quiz/submit", json={"question_id": questions[0]["id"], "answer": "wrong"})

    client.post("/progress/mastery", json={"concept_id": merely_low_mastery, "mastery_level": 0})

    ids = [concept["id"] for concept in client.get("/progress/weak-spots").json()["concepts"]]
    assert ids.index(frequently_missed) < ids.index(merely_low_mastery)
