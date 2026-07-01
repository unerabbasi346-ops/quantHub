# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Domain — Doc 07 §Layers
# Service: Portfolio — Doc 07 §Core Services
# Per Doc 00 §14.11
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID


class PortfolioRepository(ABC):
    """Persistence contract for core.portfolios — Doc 07 §Implementation Rules."""

    @abstractmethod
    async def get_by_id(self, portfolio_id: UUID) -> object | None: ...

    @abstractmethod
    async def list_active(self) -> list[object]: ...


class PositionRepository(ABC):
    """Persistence contract for core.positions — Doc 07 §Implementation Rules."""

    @abstractmethod
    async def get_by_portfolio(self, portfolio_id: UUID) -> list[object]: ...

    @abstractmethod
    async def get_by_portfolio_and_asset(
        self, portfolio_id: UUID, asset_id: UUID
    ) -> object | None: ...
