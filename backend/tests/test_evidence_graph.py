from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.models.investigation import (
    CopyMoveAnalysisResponse,
    DocumentForensicsFinding,
    DocumentForensicsResponse,
    ImageForensicsResponse,
    ImageForensicsSignal,
    MetadataAnalysisResponse,
    MetadataFinding,
    OCRAnalysisResponse,
    OCRBlock,
    OCRRegionRelationship,
    SuspiciousRegion,
)
from app.services import evidence_graph


@pytest.fixture
def client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("PROOFMESH_EVIDENCE_DIR", str(tmp_path / "evidence"))
    return TestClient(app)


def test_constructs_evidence_backed_graph(client, monkeypatch) -> None:
    monkeypatch.setattr(evidence_graph, "analyze_metadata", lambda _: MetadataAnalysisResponse(
        investigation_id="ignored",
        file_type="image/png",
        metadata={"timestamps": {"DateTimeOriginal": "2025:01:02 12:00:00"}},
        findings=[MetadataFinding(kind="Metadata timestamp inconsistency", message="Timestamp differs.", heuristic=True)],
    ))
    monkeypatch.setattr(evidence_graph, "analyze_image_forensics", lambda _: ImageForensicsResponse(
        signals=[ImageForensicsSignal(kind="Compression inconsistency", message="Difference found.", confidence=0.8)],
        suspicious_regions=[SuspiciousRegion(
            x=10, y=20, width=50, height=30, confidence=0.8, reason="Potentially manipulated region: Compression inconsistency."
        )],
        overall_anomaly_score=0.8,
    ))
    monkeypatch.setattr(evidence_graph, "analyze_copy_move", lambda _: CopyMoveAnalysisResponse())
    monkeypatch.setattr(evidence_graph, "analyze_ocr", lambda _: OCRAnalysisResponse(blocks=[OCRBlock(
        text="Date", confidence=90, x=20, y=25, width=25, height=10, page=1
    )], average_confidence=90))
    monkeypatch.setattr(evidence_graph, "analyze_document_forensics", lambda _: DocumentForensicsResponse(
        findings=[DocumentForensicsFinding(
            kind="Text rendering/layout inconsistency", message="Position differs.", confidence=0.7, block_indexes=[0]
        )],
        ocr_region_relationships=[OCRRegionRelationship(
            ocr_block_index=0, suspicious_region_index=0, page=1, overlap_ratio=1.0, message="Overlap."
        )],
    ))
    content = BytesIO()
    Image.new("RGB", (100, 80), "white").save(content, format="PNG")
    upload = client.post("/api/v1/investigations", files={"file": ("record.png", content.getvalue(), "image/png")})
    investigation_id = upload.json()["investigation_id"]

    response = client.get(f"/api/v1/investigations/{investigation_id}/graph")

    assert response.status_code == 200
    payload = response.json()
    node_types = {node["node_type"] for node in payload["nodes"]}
    assert {
        "Artifact", "Metadata", "Timestamp", "OCR Text", "Suspicious Region", "Image Signal", "Document Signal", "Finding"
    } <= node_types
    assert all(node["investigation_id"] == investigation_id for node in payload["nodes"])
    assert all(node["evidence_reference"] for node in payload["nodes"])
    relationships = {edge["relationship"] for edge in payload["edges"]}
    assert {"HAS_METADATA", "CONTAINS", "SUPPORTS", "CONFLICTS_WITH", "OVERLAPS", "INDICATES"} <= relationships


def test_graph_is_stable_for_the_same_analysis_outputs(client, monkeypatch) -> None:
    monkeypatch.setattr(evidence_graph, "analyze_metadata", lambda _: MetadataAnalysisResponse(
        investigation_id="ignored", file_type="image/png", metadata={}, findings=[]
    ))
    monkeypatch.setattr(evidence_graph, "analyze_image_forensics", lambda _: ImageForensicsResponse(overall_anomaly_score=0))
    monkeypatch.setattr(evidence_graph, "analyze_copy_move", lambda _: CopyMoveAnalysisResponse())
    monkeypatch.setattr(evidence_graph, "analyze_ocr", lambda _: OCRAnalysisResponse())
    monkeypatch.setattr(evidence_graph, "analyze_document_forensics", lambda _: DocumentForensicsResponse())
    content = BytesIO()
    Image.new("RGB", (100, 80), "white").save(content, format="PNG")
    upload = client.post("/api/v1/investigations", files={"file": ("record.png", content.getvalue(), "image/png")})
    investigation_id = upload.json()["investigation_id"]

    first = client.get(f"/api/v1/investigations/{investigation_id}/graph")
    second = client.get(f"/api/v1/investigations/{investigation_id}/graph")

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
