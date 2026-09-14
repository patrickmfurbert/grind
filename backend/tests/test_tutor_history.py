from backend.app.database import connection


def test_history_starts_a_new_session_when_none_exists(client):
    response = client.get("/tutor/history/why-distributed-systems-exist")

    assert response.status_code == 200
    body = response.json()
    assert body["messages"] == []
    assert body["session_id"]

    with connection() as conn:
        row = conn.execute("SELECT concept_id FROM sessions WHERE session_id=?", (body["session_id"],)).fetchone()
    assert row["concept_id"] == "why-distributed-systems-exist"


def test_message_is_saved_and_returned_by_history(client):
    session = client.get("/tutor/history/why-distributed-systems-exist").json()
    session_id = session["session_id"]

    save_user = client.post(
        "/tutor/message",
        json={"concept_id": "why-distributed-systems-exist", "session_id": session_id, "role": "user", "content": "Why does it exist?"},
    )
    save_assistant = client.post(
        "/tutor/message",
        json={"concept_id": "why-distributed-systems-exist", "session_id": session_id, "role": "assistant", "content": "Good question — what happens with one server?"},
    )
    assert save_user.status_code == 200
    assert save_assistant.status_code == 200

    history = client.get("/tutor/history/why-distributed-systems-exist").json()
    assert history["session_id"] == session_id
    assert history["messages"] == [
        {"role": "user", "content": "Why does it exist?"},
        {"role": "assistant", "content": "Good question — what happens with one server?"},
    ]


def test_history_returns_most_recent_session_when_multiple_exist(client):
    first = client.get("/tutor/history/why-distributed-systems-exist").json()
    client.post(
        "/tutor/message",
        json={"concept_id": "why-distributed-systems-exist", "session_id": first["session_id"], "role": "user", "content": "first session message"},
    )

    with connection() as conn:
        conn.execute("UPDATE sessions SET started_at = datetime('now', '-1 day') WHERE session_id=?", (first["session_id"],))

    second_session_id = "11111111-1111-1111-1111-111111111111"
    with connection() as conn:
        conn.execute("INSERT INTO sessions (session_id, concept_id) VALUES (?, ?)", (second_session_id, "why-distributed-systems-exist"))
    client.post(
        "/tutor/message",
        json={"concept_id": "why-distributed-systems-exist", "session_id": second_session_id, "role": "user", "content": "second session message"},
    )

    history = client.get("/tutor/history/why-distributed-systems-exist").json()
    assert history["session_id"] == second_session_id
    assert history["messages"] == [{"role": "user", "content": "second session message"}]


def test_delete_history_clears_messages_and_starts_a_fresh_session(client):
    first = client.get("/tutor/history/why-distributed-systems-exist").json()
    client.post(
        "/tutor/message",
        json={"concept_id": "why-distributed-systems-exist", "session_id": first["session_id"], "role": "user", "content": "hello"},
    )

    delete_response = client.delete("/tutor/history/why-distributed-systems-exist")
    assert delete_response.status_code == 200

    second = client.get("/tutor/history/why-distributed-systems-exist").json()
    assert second["session_id"] != first["session_id"]
    assert second["messages"] == []
