from io import BytesIO

import fitz
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("PROOFMESH_EVIDENCE_DIR", str(tmp_path / "evidence"))
    return TestClient(app)


def upload(client: TestClient, filename: str, content: bytes, content_type: str) -> str:
    response = client.post("/api/v1/investigations", files={"file": (filename, content, content_type)})
    assert response.status_code == 201
    return response.json()["investigation_id"]


def jpeg_with_exif() -> bytes:
    image = Image.new("RGB", (12, 8), color="navy")
    exif = Image.Exif()
    exif[305] = "Adobe Photoshop"
    exif[271] = "ProofMesh Camera"
    exif[272] = "PM-01"
    exif[36867] = "2025:01:02 12:00:00"
    exif[36868] = "2025:01:01 12:00:00"
    content = BytesIO()
    image.save(content, format="JPEG", exif=exif)
    return content.getvalue()


def sample_pdf() -> bytes:
    document = fitz.open()
    document.new_page()
    metadata = document.metadata
    metadata.update(
        {
            "author": "Case Analyst",
            "creator": "ProofMesh Test",
            "producer": "PyMuPDF",
            "creationDate": "D:20250101100000",
            "modDate": "D:20250102100000",
        }
    )
    document.set_metadata(metadata)
    content = document.tobytes()
    document.close()
    return content


def test_extracts_image_metadata_and_observed_findings(client) -> None:
    investigation_id = upload(client, "edited.jpg", jpeg_with_exif(), "image/jpeg")

    response = client.post(f"/api/v1/investigations/{investigation_id}/analyze/metadata")

    assert response.status_code == 200
    payload = response.json()
    assert payload["file_type"] == "image/jpeg"
    assert payload["metadata"]["dimensions"] == {"width": 12, "height": 8}
    assert payload["metadata"]["format"] == "JPEG"
    assert payload["metadata"]["software"] == "Adobe Photoshop"
    assert payload["metadata"]["camera"] == {"make": "ProofMesh Camera", "model": "PM-01"}
    assert {finding["kind"] for finding in payload["findings"]} == {
        "Editing software detected",
        "Metadata timestamp inconsistency",
    }


def test_reports_missing_image_exif_without_manipulation_claim(client) -> None:
    image = Image.new("RGB", (2, 3), color="white")
    content = BytesIO()
    image.save(content, format="PNG")
    investigation_id = upload(client, "plain.png", content.getvalue(), "image/png")

    response = client.post(f"/api/v1/investigations/{investigation_id}/analyze/metadata")

    assert response.status_code == 200
    findings = response.json()["findings"]
    assert findings == [{
        "kind": "Metadata unavailable",
        "message": "No embedded EXIF metadata was found. This alone does not indicate manipulation.",
        "heuristic": False,
    }]


def test_extracts_pdf_metadata(client) -> None:
    investigation_id = upload(client, "record.pdf", sample_pdf(), "application/pdf")

    response = client.post(f"/api/v1/investigations/{investigation_id}/analyze/metadata")

    assert response.status_code == 200
    metadata = response.json()["metadata"]
    assert metadata["page_count"] == 1
    assert metadata["author"] == "Case Analyst"
    assert metadata["creator"] == "ProofMesh Test"
    assert metadata["producer"] == "PyMuPDF"
    assert metadata["creation_date"] == "D:20250101100000"
    assert metadata["modification_date"] == "D:20250102100000"


def test_metadata_analysis_returns_not_found_for_unknown_investigation(client) -> None:
    response = client.post("/api/v1/investigations/missing/analyze/metadata")

    assert response.status_code == 404
