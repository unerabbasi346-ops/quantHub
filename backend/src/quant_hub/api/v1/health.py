# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Presentation/API — Doc 07 §Layers
# Observability: health endpoints — Doc 07 §Logging & Observability
# API standards: Pydantic response schema, OpenAPI summary — Doc 07 §API Standards
# Per Doc 00 §14.11
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service liveness check",
    tags=["health"],
)
async def health() -> HealthResponse:
    # Doc 07 §Logging & Observability: health endpoint; no business logic per §Implementation Rules
    return HealthResponse(status="ok", version="1.0.0")
