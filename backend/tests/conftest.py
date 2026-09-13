import pytest
from fastapi.testclient import TestClient

from backend.app.config import get_settings
from backend.app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A TestClient with an isolated, per-test SQLite database and upload directory."""
    monkeypatch.setenv("SQLITE_DB_PATH", str(tmp_path / "grind-test.db"))
    monkeypatch.setenv("PDF_UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    get_settings.cache_clear()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()
