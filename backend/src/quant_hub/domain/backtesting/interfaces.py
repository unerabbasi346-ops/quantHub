# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Domain — Doc 07 §Layers
# Service: Backtesting — Doc 07 §Core Services
# Per Doc 00 §14.11
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID


class BacktestRepository(ABC):
    """Persistence contract for analytics.backtests — Doc 07 §Implementation Rules."""

    @abstractmethod
    async def get_by_id(self, backtest_id: UUID) -> object | None: ...

    @abstractmethod
    async def list_by_strategy(self, strategy_id: UUID) -> list[object]: ...

    @abstractmethod
    async def save(self, backtest: object) -> None: ...
