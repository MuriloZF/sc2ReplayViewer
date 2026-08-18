from fastapi import APIRouter

from backend.app.api.routes import health, replays

api_router = APIRouter()
api_router.include_router(health.router, tags=["system"])
api_router.include_router(replays.router, tags=["replays"])
