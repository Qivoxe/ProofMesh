import hashlib

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.evidence_storage import MAX_FILE_SIZE_BYTES


@pytest.fixture
def client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("PROOFMESH_EVIDENCE_DIR", str(tmp_path / "evidence"))
    return TestClient(app)


@pytest.mark.parametrize(
    ("filename", "content_type", "content"),
    [
        ("scene.png", "image/png", b"\x89PNG\r\n\x1a\nproofmesh"),
        ("scene.jpg", "image/jpeg", b"\xff\xd8\xffproofmesh"),
        ("statement.pdf", "application/pdf", b"%PDF-1.4\nproofmesh"),
    ],
)
def test_upload_supported_evidence(client, filename, content_type, content) -> None:
    response = client.post("/api/v1/investigations", files={"file": (filename, content, content_type)})

    assert response.status_code == 201
    payload = response.json()
    assert payload["filename"] == filename
    assert payload["file_type"] == content_type
    assert payload["file_size"] == len(content)
    assert payload["sha256"] == hashlib.sha256(content).hexdigest()
    assert payload["investigation_id"]


def test_upload_rejects_unsupported_file(client) -> None:
    response = client.post("/api/v1/investigations", files={"file": ("notes.txt", b"unsupported", "text/plain")})

    assert response.status_code == 415


def test_upload_rejects_oversized_file(client) -> None:
    response = client.post(
        "/api/v1/investigations",
        files={"file": ("large.png", b"x" * (MAX_FILE_SIZE_BYTES + 1), "image/png")},
    )

    assert response.status_code == 413
