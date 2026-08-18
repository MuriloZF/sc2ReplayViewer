from fastapi import FastAPI

from backend.app.api.router import api_router
from backend.app.config import get_settings


def create_app() -> FastAPI:
    """Build the API application so tests and deployments share one setup path."""

    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        summary="Analyze StarCraft II replay files and expose timeline data.",
    )
    application.include_router(api_router, prefix=settings.api_prefix)
    return application


app = create_app()
