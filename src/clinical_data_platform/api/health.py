"""Health check endpoints."""

from fastapi import APIRouter

from clinical_data_platform import __version__
from clinical_data_platform.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": __version__,
        "environment": settings.environment,
    }
