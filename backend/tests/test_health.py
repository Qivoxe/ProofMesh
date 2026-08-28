from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_check_returns_proofmesh_status() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "proofmesh"}
