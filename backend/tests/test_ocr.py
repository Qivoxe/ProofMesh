from io import BytesIO

import fitz
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.services import ocr


class FakeTesseract:
    class Output:
        DICT = "DICT"

    @staticmethod
    def get_tesseract_version() -> str:
        return "5.0"

    @staticmethod
    def image_to_data(image, output_type):
        assert output_type == "DICT"
        assert image.width > 0 and image.height > 0
        return {
            "text": ["Proof", "Mesh", "", "ignored"],
            "conf": ["96.5", "88", "-1", "-1"],
            "left": [10, 42, 0, 0],
            "top": [20, 20, 0, 0],
            "width": [28, 30, 0, 0],
            "height": [12, 12, 0, 0],
        }


@pytest.fixture
def client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("PROOFMESH_EVIDENCE_DIR", str(tmp_path / "evidence"))
    return TestClient(app)


def upload(client: TestClient, filename: str, content: bytes, content_type: str) -> str:
    response = client.post("/api/v1/investigations", files={"file": (filename, content, content_type)})
    assert response.status_code == 201
    return response.json()["investigation_id"]


def test_extracts_image_text_confidence_and_overlay_boxes(client, monkeypatch) -> None:
    monkeypatch.setattr(ocr, "pytesseract", FakeTesseract)
    image = Image.new("RGB", (100, 60), "white")
    data = BytesIO()
    image.save(data, format="PNG")
    investigation_id = upload(client, "evidence.png", data.getvalue(), "image/png")

    response = client.post(f"/api/v1/investigations/{investigation_id}/analyze/ocr")

    assert response.status_code == 200
    payload = response.json()
    assert payload["text"] == "Proof Mesh"
    assert payload["average_confidence"] == 92.25
    assert payload["blocks"] == [
        {"text": "Proof", "confidence": 96.5, "x": 10, "y": 20, "width": 28, "height": 12, "page": 1},
        {"text": "Mesh", "confidence": 88.0, "x": 42, "y": 20, "width": 30, "height": 12, "page": 1},
    ]
    assert "source-image pixels" in payload["findings"][0]["message"]


def test_renders_pdf_pages_before_ocr(client, monkeypatch) -> None:
    monkeypatch.setattr(ocr, "pytesseract", FakeTesseract)
    document = fitz.open()
    document.new_page(width=144, height=144)
    data = document.tobytes()
    document.close()
    investigation_id = upload(client, "evidence.pdf", data, "application/pdf")

    response = client.post(f"/api/v1/investigations/{investigation_id}/analyze/ocr")

    assert response.status_code == 200
    payload = response.json()
    assert payload["text"] == "Proof Mesh"
    assert {block["page"] for block in payload["blocks"]} == {1}
    assert "rendered at 2x scale" in payload["findings"][0]["message"]


def test_returns_empty_fallback_when_tesseract_is_unavailable(client, monkeypatch) -> None:
    monkeypatch.setattr(ocr, "pytesseract", None)
    image = Image.new("RGB", (100, 60), "white")
    data = BytesIO()
    image.save(data, format="PNG")
    investigation_id = upload(client, "evidence.png", data.getvalue(), "image/png")

    response = client.post(f"/api/v1/investigations/{investigation_id}/analyze/ocr")

    assert response.status_code == 200
    assert response.json() == {
        "text": "",
        "blocks": [],
        "average_confidence": 0.0,
        "findings": [{
            "kind": "OCR unavailable",
            "message": "Tesseract OCR is not installed or is not available on the server PATH. Install Tesseract and retry.",
        }],
    }
