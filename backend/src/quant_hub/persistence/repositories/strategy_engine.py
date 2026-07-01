# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Persistence — Doc 07 §Layers
# Repository pattern — Doc 07 §Implementation Rules
# P-1: strategy config is opaque JSONB; repository never interprets it
# Per Doc 00 §14.11
from __future__ import annotations

from uuid import UUID

from quant_hub.domain.strategy_engine.interfaces import StrategyRepository
from quant_hub.persistence.repositories.base import BaseRepository


class SQLAlchemyStrategyRepository(BaseRepository[object], StrategyRepository):
    """Concrete repository for core.strategies."""

    async def get_by_id(self, strategy_id: UUID) -> object | None:
        return None  # stub

    async def list_by_portfolio(self, portfolio_id: UUID) -> list[object]:
        return []  # stub
