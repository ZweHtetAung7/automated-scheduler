from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_settings_defaults() -> None:
    response = client.get("/api/settings/defaults")
    assert response.status_code == 200
    assert response.json()["study.max_hours_per_day"] == 5
