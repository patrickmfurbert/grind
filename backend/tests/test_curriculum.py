def test_phases_groups_all_concepts_by_phase(client):
    response = client.get("/curriculum/phases")
    assert response.status_code == 200
    phases = response.json()["phases"]
    assert {phase["name"] for phase in phases} == {
        "Phase 1", "Phase 1.5", "Phase 2", "Phase 2.5", "Phase 3", "Phase 4", "Phase 5", "Phase 6",
    }
    assert sum(len(phase["concepts"]) for phase in phases) == 74


def test_concept_detail_returns_prerequisites_as_list(client):
    response = client.get("/curriculum/concept/why-distributed-systems-exist")
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Why distributed systems exist"
    assert body["prerequisites"] == []


def test_concept_detail_missing_returns_404(client):
    response = client.get("/curriculum/concept/does-not-exist")
    assert response.status_code == 404


def test_phase_6_first_concept_connects_to_last_phase_5_concept(client):
    response = client.get("/curriculum/concept/arrays-and-hashing-fundamentals")
    assert response.status_code == 200
    assert response.json()["prerequisites"] == ["how-to-whiteboard-under-pressure"]


def test_code_demos_returns_the_concepts_starter_exercises(client):
    response = client.get("/curriculum/code-demos/two-pointers-pattern")
    assert response.status_code == 200
    demos = response.json()["code_demos"]
    assert len(demos) == 2
    assert demos[0]["language"] == "python"
    assert "starter" in demos[0]


def test_code_demos_missing_concept_returns_404(client):
    response = client.get("/curriculum/code-demos/does-not-exist")
    assert response.status_code == 404


def test_code_demos_empty_for_concept_without_demos(client):
    response = client.get("/curriculum/code-demos/why-distributed-systems-exist")
    assert response.status_code == 200
    assert response.json()["code_demos"] == []
