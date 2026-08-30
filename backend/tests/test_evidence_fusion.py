from app.models.investigation import (
    CopyMoveAnalysisResponse,
    DocumentForensicsFinding,
    DocumentForensicsResponse,
    ImageForensicsResponse,
    ImageForensicsSignal,
    MetadataAnalysisResponse,
    MetadataFinding,
    OCRAnalysisResponse,
    OCRFinding,
    OCRRegionRelationship,
)
from app.services.evidence_fusion import configured_fusion_weights, fuse_evidence


def sample_inputs():
    metadata = MetadataAnalysisResponse(
        investigation_id="case-1",
        file_type="image/png",
        metadata={},
        findings=[MetadataFinding(
            kind="Metadata timestamp inconsistency", message="Timestamp order differs.", heuristic=True
        )],
    )
    image = ImageForensicsResponse(
        overall_anomaly_score=0.7,
        signals=[ImageForensicsSignal(
            kind="Compression inconsistency", message="Recompression differs locally.", confidence=0.6
        )],
    )
    copy_move = CopyMoveAnalysisResponse(signals=[ImageForensicsSignal(
        kind="Spatially consistent repeated features", message="Repeated local features.", confidence=0.8
    )])
    ocr = OCRAnalysisResponse(average_confidence=92)
    document = DocumentForensicsResponse(
        findings=[DocumentForensicsFinding(
            kind="Text rendering/layout inconsistency", message="Spacing differs.", confidence=0.65
        )],
        ocr_region_relationships=[OCRRegionRelationship(
            ocr_block_index=0, suspicious_region_index=0, page=1, overlap_ratio=0.5,
            message="OCR/image overlap."
        )],
    )
    return metadata, image, copy_move, ocr, document


def test_same_input_produces_exactly_the_same_fusion_result() -> None:
    inputs = sample_inputs()
    weights = {"metadata": 0.15, "image": 0.30, "ocr": 0.10, "document": 0.25, "cross_signal": 0.20}

    first = fuse_evidence(*inputs, weights=weights)
    second = fuse_evidence(*inputs, weights=weights)

    assert first.model_dump() == second.model_dump()
    assert first.evidence_integrity_score == 38.5
    assert first.risk_level == "HIGH"
    assert "not a probability of fraud" in first.explanation


def test_weights_are_configurable_and_renormalized() -> None:
    inputs = sample_inputs()
    image_weighted = fuse_evidence(*inputs, weights={
        "metadata": 0,
        "image": 4,
        "ocr": 0,
        "document": 0,
        "cross_signal": 0,
    })

    assert image_weighted.weights == {
        "metadata": 0.0,
        "image": 1.0,
        "ocr": 0.0,
        "document": 0.0,
        "cross_signal": 0.0,
    }
    assert image_weighted.evidence_integrity_score == 20.0
    assert configured_fusion_weights({"PROOFMESH_FUSION_IMAGE_WEIGHT": "3"})["image"] > 0.3


def test_unavailable_ocr_reduces_coverage_without_creating_a_risk_finding() -> None:
    metadata, image, copy_move, _, document = sample_inputs()
    result = fuse_evidence(
        metadata,
        image,
        copy_move,
        OCRAnalysisResponse(findings=[OCRFinding(kind="OCR unavailable", message="Not installed.")]),
        document,
    )

    assert result.confidence == 90.0
    assert not any(finding.kind == "OCR unavailable" for finding in result.findings)
