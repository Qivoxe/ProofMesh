from fastapi import APIRouter

from app.models.health import HealthResponse


api_router = APIRouter()


@api_router.get("/health", response_model=HealthResponse, tags=["system"])
def health_check() -> HealthResponse:
    """Return the service readiness state."""
    return HealthResponse()
