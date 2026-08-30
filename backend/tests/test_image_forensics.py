from io import BytesIO

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("PROOFMESH_EVIDENCE_DIR", str(tmp_path / "evidence"))
    return TestClient(app)


def upload_image(client: TestClient, filename: str, image: Image.Image) -> str:
    content = BytesIO()
    image.save(content, format="PNG")
    response = client.post("/api/v1/investigations", files={"file": (filename, content.getvalue(), "image/png")})
    assert response.status_code == 201
    return response.json()["investigation_id"]


def test_image_analysis_reports_all_lightweight_signals(client) -> None:
    image = Image.new("RGB", (96, 64), color="gray")
    investigation_id = upload_image(client, "plain.png", image)

    response = client.post(f"/api/v1/investigations/{investigation_id}/analyze/image")

    assert response.status_code == 200
    payload = response.json()
    assert payload["overall_anomaly_score"] == pytest.approx(0.0)
    assert payload["suspicious_regions"] == []
    assert {signal["kind"] for signal in payload["signals"]} == {
        "Image dimensions",
        "Grayscale analysis",
        "Edge analysis",
        "Local noise analysis",
        "Compression inconsistency",
    }
    dimensions = next(signal for signal in payload["signals"] if signal["kind"] == "Image dimensions")
    assert dimensions["details"] == {"width": 96, "height": 64}


def test_image_analysis_returns_bounded_potential_anomaly_region(client) -> None:
    pixels = np.full((128, 128, 3), 128, dtype=np.uint8)
    random = np.random.default_rng(1234)
    pixels[48:80, 48:80] = random.integers(0, 256, size=(32, 32, 3), dtype=np.uint8)
    investigation_id = upload_image(client, "local-noise.png", Image.fromarray(pixels, "RGB"))

    response = client.post(f"/api/v1/investigations/{investigation_id}/analyze/image")

    assert response.status_code == 200
    payload = response.json()
    assert 0 < payload["overall_anomaly_score"] <= 1
    assert payload["suspicious_regions"]
    region = payload["suspicious_regions"][0]
    assert region["x"] < 80 and region["x"] + region["width"] > 48
    assert region["y"] < 80 and region["y"] + region["height"] > 48
    assert 0 <= region["confidence"] <= 1
    assert "Potentially manipulated region" in region["reason"]


def test_image_analysis_rejects_non_image_evidence(client) -> None:
    response = client.post(
        "/api/v1/investigations",
        files={"file": ("record.pdf", b"%PDF-1.4\nexample", "application/pdf")},
    )
    investigation_id = response.json()["investigation_id"]

    analysis = client.post(f"/api/v1/investigations/{investigation_id}/analyze/image")

    assert analysis.status_code == 415
