# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Persistence — Doc 07 §Layers
# Repository pattern — Doc 07 §Implementation Rules
# Per Doc 00 §14.11
from __future__ import annotations

from uuid import UUID

from quant_hub.domain.backtesting.interfaces import BacktestRepository
from quant_hub.persistence.repositories.base import BaseRepository


class SQLAlchemyBacktestRepository(BaseRepository[object], BacktestRepository):
    """Concrete repository for analytics.backtests."""

    async def get_by_id(self, backtest_id: UUID) -> object | None:
        return None  # stub

    async def list_by_strategy(self, strategy_id: UUID) -> list[object]:
        return []  # stub

    async def save(self, backtest: object) -> None:
        pass  # stub
