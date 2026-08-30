from typing import Any

from pydantic import BaseModel, Field


class InvestigationResponse(BaseModel):
    investigation_id: str
    filename: str
    file_type: str
    file_size: int
    sha256: str


class MetadataFinding(BaseModel):
    kind: str
    message: str
    heuristic: bool = False


class MetadataAnalysisResponse(BaseModel):
    investigation_id: str
    file_type: str
    metadata: dict[str, Any]
    findings: list[MetadataFinding] = Field(default_factory=list)


class ImageForensicsSignal(BaseModel):
    """A measured image characteristic; it is not a conclusion of manipulation."""

    kind: str
    message: str
    confidence: float = Field(ge=0, le=1)
    details: dict[str, Any] = Field(default_factory=dict)


class SuspiciousRegion(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    confidence: float = Field(ge=0, le=1)
    reason: str


class ImageForensicsResponse(BaseModel):
    signals: list[ImageForensicsSignal] = Field(default_factory=list)
    suspicious_regions: list[SuspiciousRegion] = Field(default_factory=list)
    overall_anomaly_score: float = Field(ge=0, le=1)


class CopyMoveAnalysisResponse(BaseModel):
    """Potential copied areas and non-definitive processing signals."""

    signals: list[ImageForensicsSignal] = Field(default_factory=list)
    suspicious_regions: list[SuspiciousRegion] = Field(default_factory=list)


class OCRBlock(BaseModel):
    """A word-level OCR result in source-image pixels."""

    text: str
    confidence: float = Field(ge=0, le=100)
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    page: int = Field(ge=1)


class OCRFinding(BaseModel):
    kind: str
    message: str


class OCRAnalysisResponse(BaseModel):
    text: str = ""
    blocks: list[OCRBlock] = Field(default_factory=list)
    average_confidence: float = Field(default=0, ge=0, le=100)
    findings: list[OCRFinding] = Field(default_factory=list)


class DocumentForensicsFinding(BaseModel):
    kind: str
    message: str
    confidence: float = Field(ge=0, le=1)
    page: int | None = Field(default=None, ge=1)
    block_indexes: list[int] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class OCRRegionRelationship(BaseModel):
    ocr_block_index: int = Field(ge=0)
    suspicious_region_index: int = Field(ge=0)
    page: int = Field(ge=1)
    overlap_ratio: float = Field(ge=0, le=1)
    message: str


class DocumentForensicsResponse(BaseModel):
    findings: list[DocumentForensicsFinding] = Field(default_factory=list)
    ocr_region_relationships: list[OCRRegionRelationship] = Field(default_factory=list)


class NormalizedFusionSignal(BaseModel):
    category: str
    kind: str
    message: str
    normalized_concern: float = Field(ge=0, le=1)


class EvidenceFusionResponse(BaseModel):
    evidence_integrity_score: float = Field(ge=0, le=100)
    risk_level: str
    findings: list[NormalizedFusionSignal] = Field(default_factory=list)
    normalized_signals: list[NormalizedFusionSignal] = Field(default_factory=list)
    category_concern_scores: dict[str, float] = Field(default_factory=dict)
    weights: dict[str, float] = Field(default_factory=dict)
    confidence: float = Field(ge=0, le=100)
    explanation: str


class EvidenceGraphNode(BaseModel):
    id: str
    node_type: str
    label: str
    investigation_id: str
    evidence_reference: str


class EvidenceGraphEdge(BaseModel):
    source: str
    target: str
    relationship: str


class EvidenceGraphResponse(BaseModel):
    nodes: list[EvidenceGraphNode] = Field(default_factory=list)
    edges: list[EvidenceGraphEdge] = Field(default_factory=list)
