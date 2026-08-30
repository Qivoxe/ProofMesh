from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.models.investigation import (
    ImageForensicsResponse,
    ImageForensicsSignal,
    OCRAnalysisResponse,
    OCRBlock,
    OCRFinding,
    SuspiciousRegion,
)
from app.services import document_forensics


@pytest.fixture
def client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("PROOFMESH_EVIDENCE_DIR", str(tmp_path / "evidence"))
    return TestClient(app)


def upload_png(client: TestClient) -> str:
    data = BytesIO()
    Image.new("RGB", (400, 120), "white").save(data, format="PNG")
    response = client.post("/api/v1/investigations", files={"file": ("document.png", data.getvalue(), "image/png")})
    assert response.status_code == 201
    return response.json()["investigation_id"]


def test_reports_layout_duplicates_and_ocr_image_region_relationships(client, monkeypatch) -> None:
    blocks = [
        OCRBlock(text="Alpha", confidence=90, x=10, y=10, width=30, height=10, page=1),
        OCRBlock(text="Beta", confidence=90, x=45, y=10, width=30, height=10, page=1),
        OCRBlock(text="Alpha", confidence=90, x=10, y=40, width=30, height=10, page=1),
        OCRBlock(text="Gamma", confidence=90, x=320, y=40, width=40, height=10, page=1),
        OCRBlock(text="Alpha", confidence=90, x=80, y=70, width=30, height=10, page=1),
        OCRBlock(text="Note", confidence=90, x=115, y=70, width=30, height=10, page=1),
    ]
    monkeypatch.setattr(document_forensics, "analyze_ocr", lambda _: OCRAnalysisResponse(text="", blocks=blocks))
    monkeypatch.setattr(document_forensics, "analyze_image_forensics", lambda _: ImageForensicsResponse(
        signals=[ImageForensicsSignal(kind="test", message="test", confidence=0)],
        suspicious_regions=[SuspiciousRegion(
            x=0, y=0, width=100, height=35, confidence=0.8, reason="Potentially manipulated region: Local image anomaly."
        )],
        overall_anomaly_score=0.8,
    ))
    investigation_id = upload_png(client)

    response = client.post(f"/api/v1/investigations/{investigation_id}/analyze/document")

    assert response.status_code == 200
    payload = response.json()
    layout_analyses = {finding["details"].get("analysis") for finding in payload["findings"]}
    assert {"unusual_spacing", "alignment_inconsistency", "inconsistent_text_density", "unusual_text_positioning"} <= layout_analyses
    assert any(finding["kind"] == "Duplicated OCR text" for finding in payload["findings"])
    assert any(finding["kind"] == "Suspicious OCR/image overlap" for finding in payload["findings"])
    assert payload["ocr_region_relationships"]
    assert payload["ocr_region_relationships"][0]["overlap_ratio"] > 0


def test_handles_unavailable_ocr_without_failing(client, monkeypatch) -> None:
    monkeypatch.setattr(document_forensics, "analyze_ocr", lambda _: OCRAnalysisResponse(findings=[OCRFinding(
        kind="OCR unavailable", message="Tesseract is absent."
    )]))
    monkeypatch.setattr(document_forensics, "analyze_image_forensics", lambda _: ImageForensicsResponse(overall_anomaly_score=0))
    investigation_id = upload_png(client)

    response = client.post(f"/api/v1/investigations/{investigation_id}/analyze/document")

    assert response.status_code == 200
    assert response.json() == {
        "findings": [{
            "kind": "OCR unavailable",
            "message": "Tesseract is absent.",
            "confidence": 0.0,
            "page": None,
            "block_indexes": [],
            "details": {"source": "ocr"},
        }],
        "ocr_region_relationships": [],
    }
