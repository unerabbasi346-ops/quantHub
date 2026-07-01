# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Persistence — Doc 07 §Layers
# Repository pattern — Doc 07 §Implementation Rules
# Per Doc 00 §14.11
from __future__ import annotations

from uuid import UUID

from quant_hub.domain.portfolio.interfaces import PortfolioRepository, PositionRepository
from quant_hub.persistence.repositories.base import BaseRepository


class SQLAlchemyPortfolioRepository(BaseRepository[object], PortfolioRepository):
    """Concrete repository for core.portfolios."""

    async def get_by_id(self, portfolio_id: UUID) -> object | None:
        return None  # stub

    async def list_active(self) -> list[object]:
        return []  # stub


class SQLAlchemyPositionRepository(BaseRepository[object], PositionRepository):
    """Concrete repository for core.positions."""

    async def get_by_portfolio(self, portfolio_id: UUID) -> list[object]:
        return []  # stub

    async def get_by_portfolio_and_asset(
        self, portfolio_id: UUID, asset_id: UUID
    ) -> object | None:
        return None  # stub
