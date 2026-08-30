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


def upload_png(client: TestClient, image: Image.Image, filename: str = "image.png") -> str:
    content = BytesIO()
    image.save(content, format="PNG")
    response = client.post("/api/v1/investigations", files={"file": (filename, content.getvalue(), "image/png")})
    assert response.status_code == 201
    return response.json()["investigation_id"]


def test_detects_spatially_consistent_copy_move_regions(client) -> None:
    pixels = np.full((256, 256, 3), 180, dtype=np.uint8)
    texture = np.random.default_rng(44).integers(0, 256, size=(64, 64, 3), dtype=np.uint8)
    pixels[32:96, 32:96] = texture
    pixels[144:208, 144:208] = texture
    investigation_id = upload_png(client, Image.fromarray(pixels, "RGB"))

    response = client.post(f"/api/v1/investigations/{investigation_id}/analyze/copy-move")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["suspicious_regions"]) == 2
    assert all("Potential copy-move region" in region["reason"] for region in payload["suspicious_regions"])
    assert any(region["x"] < 96 and region["y"] < 96 for region in payload["suspicious_regions"])
    assert any(region["x"] + region["width"] > 144 and region["y"] + region["height"] > 144 for region in payload["suspicious_regions"])


@pytest.mark.parametrize(
    ("image", "expected_message"),
    [
        (Image.new("RGB", (24, 24), "white"), "too small"),
        (Image.new("RGB", (128, 128), "white"), "blank or near-uniform"),
        (Image.new("RGB", (128, 128), "gray"), "blank or near-uniform"),
    ],
)
def test_handles_tiny_blank_and_low_texture_images_gracefully(client, image, expected_message) -> None:
    investigation_id = upload_png(client, image)

    response = client.post(f"/api/v1/investigations/{investigation_id}/analyze/copy-move")

    assert response.status_code == 200
    payload = response.json()
    assert payload["suspicious_regions"] == []
    assert expected_message in payload["signals"][0]["message"]


def test_handles_non_blank_low_texture_image_gracefully(client) -> None:
    gradient = np.linspace(120, 136, 128, dtype=np.uint8)
    pixels = np.repeat(np.tile(gradient, (128, 1))[:, :, None], 3, axis=2)
    investigation_id = upload_png(client, Image.fromarray(pixels, "RGB"))

    response = client.post(f"/api/v1/investigations/{investigation_id}/analyze/copy-move")

    assert response.status_code == 200
    payload = response.json()
    assert payload["suspicious_regions"] == []
    assert "too little texture" in payload["signals"][0]["message"]
