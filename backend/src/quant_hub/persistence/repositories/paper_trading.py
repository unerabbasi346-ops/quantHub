# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
#                          Doc 14 §10.5 — Paper Trading Architecture
#                          Doc 09 — Database Schema (analytics.paper_trading_sessions)
# Layer: Persistence — Doc 07 §Layers
# Repository pattern — Doc 07 §Implementation Rules
# Per Doc 00 §14.11
#
# Step 5.0: real create/get/update against analytics.paper_trading_sessions
# (migration f1c8a3e94d20). Raw-SQL via sqlalchemy.text(); does not commit
# (caller owns the transaction boundary). Structured as the live-market sibling
# of SQLAlchemyBacktestRepository — returns plain dict rows on read.
from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text

from quant_hub.domain.paper_trading.interfaces import PaperTradingSessionRepository
from quant_hub.persistence.repositories.base import BaseRepository

# Full column projection, shared so get_by_id's shape never drifts from the table.
_SESSION_COLS = (
    "id, strategy_id, portfolio_id, backtest_id, name, description, status, "
    "config, initial_capital, realized_pnl, unrealized_pnl, last_pnl_reset_at, "
    "results, started_at, ended_at, created_by, created_at, updated_at"
)


class SQLAlchemyPaperTradingSessionRepository(
    BaseRepository[object], PaperTradingSessionRepository
):
    """Concrete repository for analytics.paper_trading_sessions — Doc 14 §10.5.

    Owns the governed session record (§10.5.3 config, status, session-lifetime
    P&L). The trades a session produces live in core.* via portfolio_type=
    'PAPER' (T-3 parity) and are not this repository's concern. Does not commit.
    """

    async def create(
        self,
        *,
        strategy_id: UUID,
        portfolio_id: UUID,
        name: str,
        config: dict,
        initial_capital: Decimal,
        description: str | None = None,
        backtest_id: UUID | None = None,
        created_by: UUID | None = None,
    ) -> UUID:
        """Register a RUNNING session (§10.5.3 config recorded; started_at,
        status default at the table; realized/unrealized P&L start at 0)."""
        result = await self._session.execute(
            text(
                """
                INSERT INTO analytics.paper_trading_sessions
                    (strategy_id, portfolio_id, backtest_id, name, description,
                     status, config, initial_capital, created_by)
                VALUES
                    (:strategy_id, :portfolio_id, :backtest_id, :name, :description,
                     'RUNNING', CAST(:config AS JSONB), :initial_capital, :created_by)
                RETURNING id
                """
            ),
            {
                "strategy_id": strategy_id,
                "portfolio_id": portfolio_id,
                "backtest_id": backtest_id,
                "name": name,
                "description": description,
                "config": json.dumps(config),
                "initial_capital": initial_capital,
                "created_by": created_by,
            },
        )
        return result.scalar_one()

    async def get_by_id(self, session_id: UUID) -> object | None:
        result = await self._session.execute(
            text(f"SELECT {_SESSION_COLS} FROM analytics.paper_trading_sessions WHERE id = :id"),
            {"id": session_id},
        )
        row = result.mappings().one_or_none()
        return None if row is None else dict(row)

    async def update_runtime(
        self,
        session_id: UUID,
        *,
        status: str | None = None,
        realized_pnl: Decimal | None = None,
        unrealized_pnl: Decimal | None = None,
        last_pnl_reset_at: datetime | None = None,
        ended_at: datetime | None = None,
        results: dict | None = None,
    ) -> None:
        """Partial update via COALESCE — only non-None arguments change a column,
        every other column keeps its current value. Safe here because none of
        these fields is ever reset value->NULL through this path (ended_at,
        last_pnl_reset_at, results only ever go NULL->value). updated_at is
        always bumped (clock_timestamp(), matching the backtests sibling)."""
        await self._session.execute(
            text(
                """
                UPDATE analytics.paper_trading_sessions
                SET status            = COALESCE(:status, status),
                    realized_pnl      = COALESCE(:realized_pnl, realized_pnl),
                    unrealized_pnl    = COALESCE(:unrealized_pnl, unrealized_pnl),
                    last_pnl_reset_at = COALESCE(:last_pnl_reset_at, last_pnl_reset_at),
                    ended_at          = COALESCE(:ended_at, ended_at),
                    results           = COALESCE(CAST(:results AS JSONB), results),
                    updated_at        = clock_timestamp()
                WHERE id = :id
                """
            ),
            {
                "id": session_id,
                "status": status,
                "realized_pnl": realized_pnl,
                "unrealized_pnl": unrealized_pnl,
                "last_pnl_reset_at": last_pnl_reset_at,
                "ended_at": ended_at,
                "results": json.dumps(results) if results is not None else None,
            },
        )
