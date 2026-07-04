# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Domain — Doc 07 §Layers
# Service: Portfolio — Doc 07 §Core Services
# Per Doc 00 §14.11
from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from uuid import UUID

from quant_hub.domain.portfolio.entities import Portfolio
from quant_hub.domain.portfolio.positions import RecordedPosition


class PortfolioRepository(ABC):
    """Persistence contract for core.portfolios — Doc 07 §Implementation Rules."""

    @abstractmethod
    async def get_by_id(self, portfolio_id: UUID) -> Portfolio | None:
        """The persisted Portfolio for `portfolio_id`, or None if absent.

        Return type tightened from `object` to `Portfolio` in Step 4.3, its
        first real consumer (GET /v1/portfolios/{id}).
        """
        ...

    @abstractmethod
    async def list_active(self) -> list[Portfolio]:
        """All active (non-soft-deleted) portfolios, ordered stably.

        Return type tightened from `list[object]` to `list[Portfolio]` in
        Step 4.3, its first real consumer (GET /v1/portfolios).
        """
        ...


class PositionRepository(ABC):
    """Persistence contract for core.positions — Doc 07 §Implementation Rules."""

    @abstractmethod
    async def get_by_portfolio(self, portfolio_id: UUID) -> list[RecordedPosition]:
        """All positions for `portfolio_id`, ordered by asset_id.

        Return type tightened from `list[object]` to `list[RecordedPosition]`
        in Step 4.3 (the concrete impl already returns RecordedPosition; the
        contract now says so).
        """
        ...

    @abstractmethod
    async def get_by_portfolio_and_asset(
        self, portfolio_id: UUID, asset_id: UUID
    ) -> RecordedPosition | None: ...

    @abstractmethod
    async def upsert(
        self,
        portfolio_id: UUID,
        asset_id: UUID,
        *,
        quantity: Decimal,
        average_entry_price: Decimal,
        market_value: Decimal,
        unrealized_pnl: Decimal,
        realized_pnl_delta: Decimal,
        last_price: Decimal,
        last_price_at: object,
        is_closed: bool,
    ) -> RecordedPosition:
        """Write the next position snapshot — Doc 14 §10.6.6 (position updated
        on every fill). Upsert on the (portfolio_id, asset_id) natural key,
        incrementing sequence_number. `unrealized_pnl` is set to the mark-to-
        market value; `realized_pnl_delta` is ADDED to realized_pnl_today
        (Step 3.6, §10.9.5). Does not commit (caller owns the transaction).
        """
        ...
