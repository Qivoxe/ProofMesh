"""Transparent, deterministic evidence-signal fusion.

The Evidence Integrity Score measures the absence of heuristic concerns in the
available analyses. It is not, and must not be interpreted as, a probability of
fraud or manipulation.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

from app.models.investigation import (
    CopyMoveAnalysisResponse,
    DocumentForensicsResponse,
    EvidenceFusionResponse,
    ImageForensicsResponse,
    MetadataAnalysisResponse,
    NormalizedFusionSignal,
    OCRAnalysisResponse,
)
from app.services.copy_move_detection import analyze_copy_move
from app.services.document_forensics import analyze_document_forensics
from app.services.evidence_storage import investigation_file
from app.services.image_forensics import IMAGE_SUFFIXES, analyze_image_forensics
from app.services.metadata_analysis import analyze_metadata
from app.services.ocr import analyze_ocr


CATEGORY_ORDER = ("metadata", "image", "ocr", "document", "cross_signal")
DEFAULT_WEIGHTS = {
    "metadata": 0.15,
    "image": 0.30,
    "ocr": 0.10,
    "document": 0.25,
    "cross_signal": 0.20,
}


def configured_fusion_weights(environment: Mapping[str, str] | None = None) -> dict[str, float]:
    """Read non-negative category weights and normalize them to one deterministically."""
    values = environment or os.environ
    configured: dict[str, float] = {}
    for category, default in DEFAULT_WEIGHTS.items():
        raw = values.get(f"PROOFMESH_FUSION_{category.upper()}_WEIGHT")
        try:
            configured[category] = float(raw) if raw is not None and float(raw) >= 0 else default
        except ValueError:
            configured[category] = default
    total = sum(configured.values())
    if total <= 0:
        configured = DEFAULT_WEIGHTS.copy()
        total = sum(configured.values())
    return {category: configured[category] / total for category in CATEGORY_ORDER}


def _signal(category: str, kind: str, message: str, concern: float) -> NormalizedFusionSignal:
    return NormalizedFusionSignal(
        category=category,
        kind=kind,
        message=message,
        normalized_concern=round(max(0.0, min(1.0, concern)), 4),
    )


def _metadata_signals(result: MetadataAnalysisResponse | None) -> list[NormalizedFusionSignal]:
    if result is None:
        return []
    signals: list[NormalizedFusionSignal] = []
    for finding in result.findings:
        kind = finding.kind.lower()
        if "unavailable" in kind:
            concern = 0.0
        elif finding.heuristic:
            concern = 0.55
        elif "editing software" in kind:
            concern = 0.20
        else:
            concern = 0.25
        signals.append(_signal("metadata", finding.kind, finding.message, concern))
    return signals


def _image_signals(result: ImageForensicsResponse | None) -> list[NormalizedFusionSignal]:
    if result is None:
        return []
    signals = [_signal(
        "image",
        "Image anomaly aggregate",
        "Aggregate lightweight image-analysis concern.",
        result.overall_anomaly_score,
    )]
    for signal in result.signals:
        if signal.kind in {"Compression inconsistency", "Local image anomaly"}:
            signals.append(_signal("image", signal.kind, signal.message, signal.confidence))
    return signals


def _copy_move_signals(result: CopyMoveAnalysisResponse | None) -> list[NormalizedFusionSignal]:
    if result is None:
        return []
    return [
        _signal("image", signal.kind, signal.message, signal.confidence)
        for signal in result.signals
        if "unavailable" not in signal.kind.lower() and "no spatially" not in signal.kind.lower()
    ]


def _ocr_signals(result: OCRAnalysisResponse | None) -> list[NormalizedFusionSignal]:
    if result is None:
        return []
    unavailable = any(finding.kind == "OCR unavailable" for finding in result.findings)
    if unavailable:
        return [_signal("ocr", "OCR unavailable", "OCR was unavailable and does not add integrity concern.", 0.0)]
    # Low OCR confidence affects the reliability of text-layout checks, not the
    # likelihood of manipulation. Its capped concern prevents it from dominating.
    recognition_concern = max(0.0, (50.0 - result.average_confidence) / 100)
    signals = [_signal(
        "ocr",
        "OCR recognition quality",
        "Lower OCR confidence reduces certainty in text-based review signals.",
        recognition_concern,
    )]
    for finding in result.findings:
        if finding.kind == "OCR failed":
            signals.append(_signal("ocr", finding.kind, finding.message, 0.10))
    return signals


def _document_signals(result: DocumentForensicsResponse | None) -> list[NormalizedFusionSignal]:
    if result is None:
        return []
    excluded = {"OCR unavailable", "Image-region relationship unavailable"}
    return [
        _signal("document", finding.kind, finding.message, finding.confidence)
        for finding in result.findings
        if finding.kind not in excluded
    ]


def _cross_signals(
    document: DocumentForensicsResponse | None,
    category_concerns: Mapping[str, float],
) -> list[NormalizedFusionSignal]:
    signals: list[NormalizedFusionSignal] = []
    if document and document.ocr_region_relationships:
        maximum_overlap = max(relationship.overlap_ratio for relationship in document.ocr_region_relationships)
        signals.append(_signal(
            "cross_signal",
            "OCR/image-region corroboration",
            "OCR text overlaps a region highlighted by image analysis.",
            maximum_overlap,
        ))
    corroborated = sorted(
        (category_concerns[category] for category in ("metadata", "image", "document") if category_concerns[category] > 0),
        reverse=True,
    )
    if len(corroborated) >= 2:
        signals.append(_signal(
            "cross_signal",
            "Multiple analysis categories",
            "More than one independent analysis category reported a review signal.",
            min(corroborated[0], corroborated[1]),
        ))
    return signals


def _risk_level(score: float) -> str:
    if score >= 85:
        return "LOW"
    if score >= 70:
        return "MODERATE"
    if score >= 45:
        return "ELEVATED"
    return "HIGH"


def fuse_evidence(
    metadata: MetadataAnalysisResponse | None,
    image: ImageForensicsResponse | None,
    copy_move: CopyMoveAnalysisResponse | None,
    ocr: OCRAnalysisResponse | None,
    document: DocumentForensicsResponse | None,
    *,
    weights: Mapping[str, float] | None = None,
) -> EvidenceFusionResponse:
    """Normalize supplied analyses and calculate the reproducible integrity score."""
    if weights is None:
        normalized_weights = configured_fusion_weights()
    else:
        supplied = {category: max(0.0, float(weights.get(category, 0.0))) for category in CATEGORY_ORDER}
        total = sum(supplied.values())
        normalized_weights = (
            {category: supplied[category] / total for category in CATEGORY_ORDER}
            if total > 0 else configured_fusion_weights({})
        )

    signals = (
        _metadata_signals(metadata)
        + _image_signals(image)
        + _copy_move_signals(copy_move)
        + _ocr_signals(ocr)
        + _document_signals(document)
    )
    category_concerns = {
        category: max((signal.normalized_concern for signal in signals if signal.category == category), default=0.0)
        for category in CATEGORY_ORDER
    }
    cross_signals = _cross_signals(document, category_concerns)
    signals.extend(cross_signals)
    category_concerns["cross_signal"] = max(
        (signal.normalized_concern for signal in cross_signals),
        default=0.0,
    )

    weighted_concern = sum(normalized_weights[category] * category_concerns[category] for category in CATEGORY_ORDER)
    score = round(100 * (1 - weighted_concern), 2)
    risk_level = _risk_level(score)
    available = {
        "metadata": metadata is not None,
        "image": image is not None or copy_move is not None,
        "ocr": ocr is not None and not any(finding.kind == "OCR unavailable" for finding in ocr.findings),
        "document": document is not None and not any(finding.kind == "OCR unavailable" for finding in document.findings),
        "cross_signal": document is not None and image is not None,
    }
    confidence = round(100 * sum(normalized_weights[category] for category in CATEGORY_ORDER if available[category]), 2)
    ordered_signals = sorted(signals, key=lambda signal: (CATEGORY_ORDER.index(signal.category), -signal.normalized_concern, signal.kind, signal.message))
    findings = [signal for signal in ordered_signals if signal.normalized_concern > 0]
    category_scores = {category: round(category_concerns[category] * 100, 2) for category in CATEGORY_ORDER}
    response_weights = {category: round(normalized_weights[category], 6) for category in CATEGORY_ORDER}
    explanation = (
        f"Evidence Integrity Score is {score:.2f}/100 ({risk_level} risk). It starts at 100 and subtracts "
        f"{100 - score:.2f} weighted concern points from normalized metadata, image, OCR, document, and cross-signal inputs. "
        "This reproducible heuristic is not a probability of fraud or manipulation."
    )
    return EvidenceFusionResponse(
        evidence_integrity_score=score,
        risk_level=risk_level,
        findings=findings,
        normalized_signals=ordered_signals,
        category_concern_scores=category_scores,
        weights=response_weights,
        confidence=confidence,
        explanation=explanation,
    )


def analyze_evidence_fusion(investigation_id: str) -> EvidenceFusionResponse:
    """Run applicable analyses for stored evidence and fuse their results."""
    path = investigation_file(investigation_id)
    metadata = analyze_metadata(investigation_id)
    is_image = path.suffix.lower() in IMAGE_SUFFIXES
    image = analyze_image_forensics(investigation_id) if is_image else None
    copy_move = analyze_copy_move(investigation_id) if is_image else None
    ocr = analyze_ocr(investigation_id)
    document = analyze_document_forensics(investigation_id)
    return fuse_evidence(metadata, image, copy_move, ocr, document)
