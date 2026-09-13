def test_phases_groups_all_concepts_by_phase(client):
    response = client.get("/curriculum/phases")
    assert response.status_code == 200
    phases = response.json()["phases"]
    assert {phase["name"] for phase in phases} == {
        "Phase 1", "Phase 1.5", "Phase 2", "Phase 2.5", "Phase 3", "Phase 4", "Phase 5",
    }
    assert sum(len(phase["concepts"]) for phase in phases) == 60


def test_concept_detail_returns_prerequisites_as_list(client):
    response = client.get("/curriculum/concept/why-distributed-systems-exist")
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Why distributed systems exist"
    assert body["prerequisites"] == []


def test_concept_detail_missing_returns_404(client):
    response = client.get("/curriculum/concept/does-not-exist")
    assert response.status_code == 404
