# Governing specification: Doc 07 — Backend Architecture §Persistence Layer
#                          Doc 15 §11.5.7, §11.5.13 — Risk Limit Framework, Risk Artifacts
#                          Doc 09 — Database Schema (analytics schema)
# Layer: Persistence — Doc 07 §Layers
# Repository pattern — Doc 07 §Implementation Rules
# Per Doc 00 §14.11
from __future__ import annotations

from uuid import UUID

from quant_hub.domain.risk.entities import RiskAssessment, RiskLimit, RiskMetrics
from quant_hub.domain.risk.interfaces import (
    RiskAssessmentRepository,
    RiskLimitRepository,
    RiskSnapshotRepository,
)
from quant_hub.persistence.repositories.base import BaseRepository


class SQLAlchemyRiskLimitRepository(BaseRepository[object], RiskLimitRepository):
    """Concrete repository for governed risk limits — Doc 15 §11.5.7.

    Maps to analytics schema (analytics.risk_limits equivalent) per Doc 09.
    Portfolio-level limits supersede strategy limits per Port-5 — the persistence
    layer stores all limits; the service layer enforces precedence.
    """

    async def get_active_limits(self, portfolio_id: UUID) -> list[RiskLimit]:
        return []  # stub

    async def save_limit(self, limit: RiskLimit) -> None:
        pass  # stub


class SQLAlchemyRiskAssessmentRepository(BaseRepository[object], RiskAssessmentRepository):
    """Concrete repository for risk assessment artifacts — Doc 15 §11.5.13.

    Assessments are immutable governed artifacts per P-2 and P-5.
    Maps to analytics schema per Doc 09.
    """

    async def save(self, assessment: RiskAssessment) -> None:
        pass  # stub

    async def get_latest(self, portfolio_id: UUID) -> RiskAssessment | None:
        return None  # stub


class SQLAlchemyRiskSnapshotRepository(BaseRepository[object], RiskSnapshotRepository):
    """Concrete repository for analytics.risk_snapshots — Doc 09 §Schemas.

    Retained for real-time risk dashboard queries per Doc 15 §11.5.8.
    """

    async def get_latest(self, portfolio_id: UUID) -> object | None:
        return None  # stub

    async def save(self, snapshot: object) -> None:
        pass  # stub
