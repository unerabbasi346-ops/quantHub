# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Presentation/API — Doc 07 §Layers
# Dependency injection wiring — Doc 07 §Implementation Rules
# Per Doc 00 §14.11
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from quant_hub.application.risk.service import RiskService
from quant_hub.domain.execution.interfaces import RiskApprovalInterface
from quant_hub.infrastructure.cache import get_redis
from quant_hub.infrastructure.database import get_session
from quant_hub.infrastructure.risk_approval_adapter import RiskApprovalAdapter
from quant_hub.infrastructure.risk_model_stub import StubRiskModel
from quant_hub.persistence.repositories.risk import (
    SQLAlchemyPreTradeRiskRepository,
    SQLAlchemyRiskAssessmentRepository,
    SQLAlchemyRiskLimitRepository,
    SQLAlchemyRiskSnapshotRepository,
)

# Annotated aliases consumed by route handlers via FastAPI Depends()
# Doc 07 §Implementation Rules: dependency injection for external resources
DbSession = Annotated[AsyncSession, Depends(get_session)]
CacheClient = Annotated[Redis, Depends(get_redis)]


def build_risk_gate(session: AsyncSession) -> RiskApprovalInterface:
    """Production pre-trade risk gate — Doc 02 mandatory gate / Doc 14 §10.7.5.

    FAIL-SAFE DI (re-verified Step 3.4, now that the real gate can REJECT):
    this is the ONLY production binding of the risk gate, and it always
    returns the REAL RiskApprovalAdapter over a real RiskService backed by
    real analytics.risk_limits / analytics.risk_assessments repositories.

    The always-approve StubRiskApprovalService (infrastructure/risk_approval.py)
    is deliberately NOT imported or referenced here — there is no config flag,
    environment branch, or default path that yields the stub in production. A
    misconfigured or "blocked" state therefore cannot silently downgrade the
    gate to unconditional approval; the worst case is the real gate FAILING
    CLOSED (default-deny per §10.7.5) inside RiskService.assess_pre_trade.
    "Blocked defaults to the real gate, not the stub" holds by construction:
    the stub is unreachable from the production wiring and exists only for
    tests that intentionally bypass risk evaluation.

    StubRiskModel is the P-1 risk-MODEL placeholder (portfolio metric
    computation, Step 3.6) — orthogonal to gate enforcement, which is real.
    """
    risk_service = RiskService(
        risk_model=StubRiskModel(),
        limits=SQLAlchemyRiskLimitRepository(session),
        assessments=SQLAlchemyRiskAssessmentRepository(session),
        snapshots=SQLAlchemyRiskSnapshotRepository(session),
        pretrade=SQLAlchemyPreTradeRiskRepository(session),
    )
    return RiskApprovalAdapter(risk_service)


async def get_risk_gate(session: DbSession) -> RiskApprovalInterface:
    """FastAPI provider for the mandatory pre-trade risk gate."""
    return build_risk_gate(session)


RiskGate = Annotated[RiskApprovalInterface, Depends(get_risk_gate)]
