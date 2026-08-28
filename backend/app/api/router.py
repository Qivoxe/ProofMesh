from fastapi import APIRouter, File, UploadFile, status

from app.models.health import HealthResponse
from app.models.investigation import InvestigationResponse
from app.services.evidence_storage import store_evidence


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
