# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Persistence — Doc 07 §Layers
# Repository pattern — Doc 07 §Implementation Rules
# Per Doc 00 §14.11
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import text

from quant_hub.domain.portfolio.interfaces import PortfolioRepository, PositionRepository
from quant_hub.domain.portfolio.positions import RecordedPosition
from quant_hub.persistence.repositories.base import BaseRepository


class SQLAlchemyPortfolioRepository(BaseRepository[object], PortfolioRepository):
    """Concrete repository for core.portfolios."""

    async def get_by_id(self, portfolio_id: UUID) -> object | None:
        return None  # stub — not needed by the Step 3.5 loop

    async def list_active(self) -> list[object]:
        return []  # stub


_POSITION_COLS = (
    "id, portfolio_id, asset_id, quantity, average_entry_price, market_value, "
    "unrealized_pnl, realized_pnl_today, last_price, is_closed, sequence_number"
)


def _row_to_position(row: object) -> RecordedPosition:
    return RecordedPosition(
        id=row["id"],
        portfolio_id=row["portfolio_id"],
        asset_id=row["asset_id"],
        quantity=row["quantity"],
        average_entry_price=row["average_entry_price"],
        market_value=row["market_value"],
        unrealized_pnl=row["unrealized_pnl"],
        realized_pnl_today=row["realized_pnl_today"],
        last_price=row["last_price"],
        is_closed=row["is_closed"],
        sequence_number=row["sequence_number"],
    )


class SQLAlchemyPositionRepository(BaseRepository[object], PositionRepository):
    """Concrete repository for core.positions — Step 3.5, Doc 14 §10.6.6.

    Raw-SQL via sqlalchemy.text(); does not commit (caller owns the
    transaction boundary). Position quantity/average_entry_price are
    NUMERIC(28,8)/(18,8) after Step 3.0 (F-4/F-11).
    """

    async def get_by_portfolio(self, portfolio_id: UUID) -> list[RecordedPosition]:
        result = await self._session.execute(
            text(
                f"""
                SELECT {_POSITION_COLS}
                FROM core.positions
                WHERE portfolio_id = :portfolio_id
                ORDER BY asset_id
                """
            ),
            {"portfolio_id": portfolio_id},
        )
        return [_row_to_position(row) for row in result.mappings().all()]

    async def get_by_portfolio_and_asset(
        self, portfolio_id: UUID, asset_id: UUID
    ) -> RecordedPosition | None:
        result = await self._session.execute(
            text(
                f"""
                SELECT {_POSITION_COLS}
                FROM core.positions
                WHERE portfolio_id = :portfolio_id AND asset_id = :asset_id
                """
            ),
            {"portfolio_id": portfolio_id, "asset_id": asset_id},
        )
        row = result.mappings().one_or_none()
        return None if row is None else _row_to_position(row)

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
        """Write the next position snapshot — §10.6.6 / §10.9.5. INSERT ... ON
        CONFLICT on the (portfolio_id, asset_id) natural key
        (positions_portfolio_asset_uq, Step 1.1 schema), incrementing
        sequence_number on update. `unrealized_pnl` is SET (mark-to-market);
        `realized_pnl_today` ACCUMULATES realized_pnl_delta in SQL (race-safe).
        updated_at via clock_timestamp().
        """
        stmt = text(
            f"""
            INSERT INTO core.positions
                (portfolio_id, asset_id, quantity, average_entry_price, market_value,
                 unrealized_pnl, realized_pnl_today, last_price, last_price_at,
                 is_closed, sequence_number)
            VALUES
                (:portfolio_id, :asset_id, :quantity, :average_entry_price, :market_value,
                 :unrealized_pnl, :realized_pnl_delta, :last_price, :last_price_at,
                 :is_closed, 1)
            ON CONFLICT (portfolio_id, asset_id)
            DO UPDATE SET
                quantity            = EXCLUDED.quantity,
                average_entry_price = EXCLUDED.average_entry_price,
                market_value        = EXCLUDED.market_value,
                unrealized_pnl      = EXCLUDED.unrealized_pnl,
                realized_pnl_today  = core.positions.realized_pnl_today + :realized_pnl_delta,
                last_price          = EXCLUDED.last_price,
                last_price_at       = EXCLUDED.last_price_at,
                is_closed           = EXCLUDED.is_closed,
                sequence_number     = core.positions.sequence_number + 1,
                updated_at          = clock_timestamp()
            RETURNING {_POSITION_COLS}
            """
        )
        result = await self._session.execute(
            stmt,
            {
                "portfolio_id": portfolio_id,
                "asset_id": asset_id,
                "quantity": quantity,
                "average_entry_price": average_entry_price,
                "market_value": market_value,
                "unrealized_pnl": unrealized_pnl,
                "realized_pnl_delta": realized_pnl_delta,
                "last_price": last_price,
                "last_price_at": last_price_at,
                "is_closed": is_closed,
            },
        )
        return _row_to_position(result.mappings().one())
