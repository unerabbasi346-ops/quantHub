# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Persistence — Doc 07 §Layers
# Repository pattern — Doc 07 §Implementation Rules
# Per Doc 00 §14.11
from __future__ import annotations

from uuid import UUID

from quant_hub.domain.risk.interfaces import RiskSnapshotRepository
from quant_hub.persistence.repositories.base import BaseRepository


class SQLAlchemyRiskSnapshotRepository(BaseRepository[object], RiskSnapshotRepository):
    """Concrete repository for analytics.risk_snapshots."""

    async def get_latest(self, portfolio_id: UUID) -> object | None:
        return None  # stub

    async def save(self, snapshot: object) -> None:
        pass  # stub
