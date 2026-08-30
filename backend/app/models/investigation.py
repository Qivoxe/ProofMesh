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
