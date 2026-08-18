from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: Literal["ok"]


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check API availability",
    description="Returns a successful response when the API process is ready to accept requests.",
)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok")
