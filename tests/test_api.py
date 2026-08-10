import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def app_module(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    import app.main as main_module

    importlib.reload(main_module)
    import asyncio

    asyncio.run(main_module.initialize_database())
    return main_module


def test_health_endpoint(app_module):
    client = TestClient(app_module.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_playlist_flow(app_module):
    client = TestClient(app_module.app)
    create_response = client.post("/api/playlists", json={"name": "Favorites"})
    assert create_response.status_code == 200
    playlist = create_response.json()
    assert playlist["name"] == "Favorites"

    clone_response = client.post(f"/api/playlists/{playlist['id']}/clone")
    assert clone_response.status_code == 200
    cloned = clone_response.json()
    assert cloned["name"] == "Favorites"
    assert cloned["id"] != playlist["id"]


def test_download_request_is_deduplicated(app_module, monkeypatch):
    client = TestClient(app_module.app)
    calls = []

    def fake_background(request_id):
        calls.append(request_id)

    monkeypatch.setattr(app_module, "run_download_background", fake_background)

    first_response = client.post(
        "/api/requests/download",
        json={"youtube_url": "https://www.youtube.com/watch?v=abc123"},
    )
    assert first_response.status_code == 200
    assert first_response.json()["status"] == "queued"

    second_response = client.post(
        "/api/requests/download",
        json={"youtube_url": "https://www.youtube.com/watch?v=abc123"},
    )
    assert second_response.status_code == 200
    assert second_response.json()["status"] == "queued"
    assert len(calls) == 1
