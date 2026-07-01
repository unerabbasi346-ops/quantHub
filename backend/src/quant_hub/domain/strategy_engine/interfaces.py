# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Domain — Doc 07 §Layers
# Service: Strategy Engine — Doc 07 §Core Services
# P-1: platform never assumes any specific strategy — strategies are opaque configs
# Per Doc 00 §14.11
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID


class StrategyRepository(ABC):
    """Persistence contract for core.strategies — Doc 07 §Implementation Rules.

    P-1: strategy config stored as opaque JSONB; domain never inspects strategy logic.
    """

    @abstractmethod
    async def get_by_id(self, strategy_id: UUID) -> object | None: ...

    @abstractmethod
    async def list_by_portfolio(self, portfolio_id: UUID) -> list[object]: ...
