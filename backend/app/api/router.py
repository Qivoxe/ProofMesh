from fastapi import APIRouter, File, UploadFile, status

from app.models.health import HealthResponse
from app.models.investigation import CopyMoveAnalysisResponse, ImageForensicsResponse, InvestigationResponse, MetadataAnalysisResponse
from app.services.copy_move_detection import analyze_copy_move
from app.services.evidence_storage import store_evidence
from app.services.image_forensics import analyze_image_forensics
from app.services.metadata_analysis import analyze_metadata


api_router = APIRouter()


@api_router.get("/health", response_model=HealthResponse, tags=["system"])
def health_check() -> HealthResponse:
    """Return the service readiness state."""
    return HealthResponse()


@api_router.post(
    "/api/v1/investigations",
    response_model=InvestigationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["investigations"],
)
async def create_investigation(file: UploadFile = File(...)) -> InvestigationResponse:
    """Store an evidence file and return immutable intake metadata."""
    return await store_evidence(file)


@api_router.post(
    "/api/v1/investigations/{investigation_id}/analyze/metadata",
    response_model=MetadataAnalysisResponse,
    tags=["investigations"],
)
def analyze_investigation_metadata(investigation_id: str) -> MetadataAnalysisResponse:
    """Extract source metadata without making manipulation claims from absent metadata."""
    return analyze_metadata(investigation_id)


@api_router.post(
    "/api/v1/investigations/{investigation_id}/analyze/image",
    response_model=ImageForensicsResponse,
    tags=["investigations"],
)
def analyze_investigation_image(investigation_id: str) -> ImageForensicsResponse:
    """Measure lightweight image-forensic heuristics without asserting image manipulation."""
    return analyze_image_forensics(investigation_id)


@api_router.post(
    "/api/v1/investigations/{investigation_id}/analyze/copy-move",
    response_model=CopyMoveAnalysisResponse,
    tags=["investigations"],
)
def analyze_investigation_copy_move(investigation_id: str) -> CopyMoveAnalysisResponse:
    """Find visually duplicated image areas using bounded local-feature matching."""
    return analyze_copy_move(investigation_id)
