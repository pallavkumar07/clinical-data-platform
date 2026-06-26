"""Application entrypoint."""

from fastapi import FastAPI

from clinical_data_platform import __version__
from clinical_data_platform.api import health, patients
from clinical_data_platform.core.config import settings


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        debug=settings.debug,
    )
    app.include_router(health.router)
    app.include_router(patients.router)
    return app


app = create_app()


@app.get("/")
def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": f"Welcome to the {settings.app_name}"}
