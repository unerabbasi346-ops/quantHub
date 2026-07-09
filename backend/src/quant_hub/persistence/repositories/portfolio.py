# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Persistence — Doc 07 §Layers
# Repository pattern — Doc 07 §Implementation Rules
# Per Doc 00 §14.11
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import text

from quant_hub.domain.portfolio.entities import Portfolio
from quant_hub.domain.portfolio.interfaces import PortfolioRepository, PositionRepository
from quant_hub.domain.portfolio.positions import RecordedPosition
from quant_hub.persistence.repositories.base import BaseRepository

_PORTFOLIO_COLS = (
    "id, name, description, base_currency, portfolio_type, is_active, created_at, "
    "configured_capital"
)


def _row_to_portfolio(row: object) -> Portfolio:
    return Portfolio(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        base_currency=row["base_currency"],
        portfolio_type=row["portfolio_type"],
        is_active=row["is_active"],
        created_at=row["created_at"],
        configured_capital=row["configured_capital"],
    )


class SQLAlchemyPortfolioRepository(BaseRepository[object], PortfolioRepository):
    """Concrete repository for core.portfolios.

    get_by_id / list_active implemented in Step 4.3 (Portfolio Vertical
    Slice), their first real consumer — previously stubbed (not needed by the
    Step 3.5 write loop). Raw-SQL via text(), same approach as every other
    repository here; does not commit (caller owns the transaction).
    """

    async def get_by_id(self, portfolio_id: UUID) -> Portfolio | None:
        result = await self._session.execute(
            text(
                f"SELECT {_PORTFOLIO_COLS} FROM core.portfolios "
                "WHERE id = :portfolio_id AND deleted_at IS NULL"
            ),
            {"portfolio_id": portfolio_id},
        )
        row = result.mappings().one_or_none()
        return None if row is None else _row_to_portfolio(row)

    async def list_active(self) -> list[Portfolio]:
        # is_active = TRUE AND deleted_at IS NULL: is_active is the explicit
        # active flag, deleted_at the soft-delete tombstone. Ordered
        # (created_at, id) for a stable, deterministic list.
        result = await self._session.execute(
            text(
                f"SELECT {_PORTFOLIO_COLS} FROM core.portfolios "
                "WHERE is_active = TRUE AND deleted_at IS NULL "
                "ORDER BY created_at, id"
            )
        )
        return [_row_to_portfolio(row) for row in result.mappings().all()]

    async def set_configured_capital(
        self, portfolio_id: UUID, amount: Decimal
    ) -> Portfolio | None:
        """Set the operator-configured capital figure (migration a7d2e1f04b93),
        returning the updated portfolio or None if absent.

        F-19 (flagged): this writes ONLY the configured_capital column — it does
        NOT touch any equity/leverage computation (there is no NAV ledger; risk
        math still takes equity as an explicit parameter). Setting capital here
        has no effect on leverage or risk-limit determination by construction.
        updated_at via clock_timestamp() (frozen-transaction reason, as
        elsewhere). Does not commit (caller owns the transaction)."""
        result = await self._session.execute(
            text(
                f"""
                UPDATE core.portfolios
                SET configured_capital = :amount, updated_at = clock_timestamp()
                WHERE id = :id AND deleted_at IS NULL
                RETURNING {_PORTFOLIO_COLS}
                """
            ),
            {"id": portfolio_id, "amount": amount},
        )
        row = result.mappings().one_or_none()
        return None if row is None else _row_to_portfolio(row)


_POSITION_COLS = (
    "id, portfolio_id, asset_id, quantity, average_entry_price, market_value, "
    "unrealized_pnl, realized_pnl_today, last_price, is_closed, sequence_number, "
    "leverage, margin_used, liquidation_price"
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
        leverage=row["leverage"],
        margin_used=row["margin_used"],
        liquidation_price=row["liquidation_price"],
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
        leverage: Decimal | None = None,
        margin_used: Decimal | None = None,
        liquidation_price: Decimal | None = None,
    ) -> RecordedPosition:
        """Write the next position snapshot — §10.6.6 / §10.9.5. INSERT ... ON
        CONFLICT on the (portfolio_id, asset_id) natural key
        (positions_portfolio_asset_uq, Step 1.1 schema), incrementing
        sequence_number on update. `unrealized_pnl` is SET (mark-to-market);
        `realized_pnl_today` ACCUMULATES realized_pnl_delta in SQL (race-safe).
        updated_at via clock_timestamp().

        MARGIN (migration e7a3c1f5b9d2, §10.6.6): `leverage`/`margin_used`/
        `liquidation_price` are SET on every write, including to NULL — a spot
        position (leverage None) writes NULL, and a perpetual position that
        closes flat writes its leverage back to NULL, so the margin columns
        never carry stale state from a prior fill. Additive keyword args with
        None defaults so the spot write path (which omits them) is unchanged.
        """
        stmt = text(
            f"""
            INSERT INTO core.positions
                (portfolio_id, asset_id, quantity, average_entry_price, market_value,
                 unrealized_pnl, realized_pnl_today, last_price, last_price_at,
                 is_closed, sequence_number, leverage, margin_used, liquidation_price)
            VALUES
                (:portfolio_id, :asset_id, :quantity, :average_entry_price, :market_value,
                 :unrealized_pnl, :realized_pnl_delta, :last_price, :last_price_at,
                 :is_closed, 1, :leverage, :margin_used, :liquidation_price)
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
                leverage            = EXCLUDED.leverage,
                margin_used         = EXCLUDED.margin_used,
                liquidation_price   = EXCLUDED.liquidation_price,
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
                "leverage": leverage,
                "margin_used": margin_used,
                "liquidation_price": liquidation_price,
            },
        )
        return _row_to_position(result.mappings().one())

    async def reset_realized_pnl_today(self, portfolio_id: UUID) -> Decimal:
        """F-20 daily reset — Doc 14 §10.5.7 / §10.9.5. Sum the portfolio's
        current realized_pnl_today (the completed day's realized P&L), then zero
        it on every position, returning that sum for the caller to fold into a
        session-lifetime figure. Two statements (SUM then UPDATE) so the caller
        gets the pre-reset total; the UPDATE skips already-zero rows so it does
        not bump updated_at / sequence on untouched positions. Does not commit.
        """
        total = (
            await self._session.execute(
                text(
                    "SELECT COALESCE(SUM(realized_pnl_today), 0) "
                    "FROM core.positions WHERE portfolio_id = :portfolio_id"
                ),
                {"portfolio_id": portfolio_id},
            )
        ).scalar_one()
        await self._session.execute(
            text(
                "UPDATE core.positions "
                "SET realized_pnl_today = 0, updated_at = clock_timestamp() "
                "WHERE portfolio_id = :portfolio_id AND realized_pnl_today <> 0"
            ),
            {"portfolio_id": portfolio_id},
        )
        return total
