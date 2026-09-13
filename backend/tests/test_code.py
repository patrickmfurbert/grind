def test_execute_python_returns_stdout(client):
    response = client.post("/code/execute", json={"language": "python", "code": "print(21 * 2)"})
    assert response.status_code == 200
    body = response.json()
    assert body["output"].strip() == "42"
    assert body["error"] == ""


def test_execute_captures_stderr_on_error(client):
    response = client.post("/code/execute", json={"language": "python", "code": "raise ValueError('boom')"})
    assert response.status_code == 200
    assert "boom" in response.json()["error"]


def test_execute_unsupported_language_returns_error_without_running(client):
    response = client.post("/code/execute", json={"language": "cobol", "code": "DISPLAY 'hi'."})
    assert response.status_code == 200
    body = response.json()
    assert body["output"] == ""
    assert "Unsupported language" in body["error"]


def test_execute_bash_snippet(client):
    response = client.post("/code/execute", json={"language": "bash", "code": "echo hello"})
    assert response.status_code == 200
    assert response.json()["output"].strip() == "hello"
