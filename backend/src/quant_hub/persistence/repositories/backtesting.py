# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
#                          Doc 14 §10.3 — Backtesting Engine Architecture
#                          Doc 09 — Database Schema (analytics.backtests)
# Layer: Persistence — Doc 07 §Layers
# Repository pattern — Doc 07 §Implementation Rules
# Per Doc 00 §14.11
#
# Step 3.7: real create/complete against analytics.backtests (Step 1.1 schema).
# Raw-SQL via sqlalchemy.text(); does not commit (caller owns the transaction).
from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import text

from quant_hub.domain.backtesting.entities import BacktestConfig, BacktestResult
from quant_hub.domain.backtesting.interfaces import BacktestRepository
from quant_hub.persistence.repositories.base import BaseRepository


def _config_to_json(config: BacktestConfig) -> dict:
    # §10.3.3 configuration recorded as a governed artifact. Execution
    # assumptions are fixed (F-16 simulated full fill), recorded so the
    # backtest is self-describing; random_seeds is N/A (no randomness, F-21).
    return {
        "symbol": config.symbol,
        "exchange": config.exchange,
        "asset_class": config.asset_class,
        "interval": config.interval,
        "strategy_config": {k: str(v) for k, v in dict(config.strategy_config).items()},
        "max_position_pct": str(config.max_position_pct),
        "execution_assumptions": "simulated full fill at bar close, zero slippage/commission (F-16)",
        "random_seeds": None,
    }


def _result_to_json(result: BacktestResult) -> dict:
    return {
        "bars_processed": result.bars_processed,
        "signals_generated": result.signals_generated,
        "orders_created": result.orders_created,
        "orders_filled": result.orders_filled,
        "orders_rejected": result.orders_rejected,
        "final_position_quantity": str(result.final_position_quantity),
        "realized_pnl": str(result.realized_pnl),
        "unrealized_pnl": str(result.unrealized_pnl),
        "final_capital": str(result.final_capital),
        "total_return": str(result.total_return),
        "trade_count": result.trade_count,
        "reproducibility_hash": result.reproducibility_hash,
    }


class SQLAlchemyBacktestRepository(BaseRepository[object], BacktestRepository):
    """Concrete repository for analytics.backtests — Step 3.7, Doc 14 §10.3."""

    async def create(self, config: BacktestConfig, strategy_id: UUID) -> UUID:
        """Register a RUNNING backtest (§10.3.3 config recorded, started_at set)."""
        stmt = text(
            """
            INSERT INTO analytics.backtests
                (strategy_id, name, status, config, start_date, end_date,
                 initial_capital, started_at)
            VALUES
                (:strategy_id, :name, 'RUNNING', CAST(:config AS JSONB), :start_date, :end_date,
                 :initial_capital, clock_timestamp())
            RETURNING id
            """
        )
        result = await self._session.execute(
            stmt,
            {
                "strategy_id": strategy_id,
                "name": config.name,
                "config": json.dumps(_config_to_json(config)),
                "start_date": config.start.date(),
                "end_date": config.end.date(),
                "initial_capital": config.initial_capital,
            },
        )
        return result.scalar_one()

    async def complete(self, backtest_id: UUID, result: BacktestResult) -> None:
        """Record results and mark COMPLETED (§10.3.6/§10.3.7).

        sharpe_ratio / max_drawdown columns are left NULL — deferred (F-21/F-18:
        need a per-step return series / equity curve this engine does not
        accumulate). The full result summary lives in the results JSONB.
        """
        await self._session.execute(
            text(
                """
                UPDATE analytics.backtests
                SET status = 'COMPLETED',
                    final_capital = :final_capital,
                    total_return = :total_return,
                    trade_count = :trade_count,
                    results = CAST(:results AS JSONB),
                    reproducibility_hash = :reproducibility_hash,
                    completed_at = clock_timestamp(),
                    updated_at = clock_timestamp()
                WHERE id = :id
                """
            ),
            {
                "id": backtest_id,
                "final_capital": result.final_capital,
                "total_return": result.total_return,
                "trade_count": result.trade_count,
                "results": json.dumps(_result_to_json(result)),
                "reproducibility_hash": result.reproducibility_hash,
            },
        )

    async def get_by_id(self, backtest_id: UUID) -> object | None:
        result = await self._session.execute(
            text(
                """
                SELECT id, strategy_id, name, status, config, start_date, end_date,
                       initial_capital, final_capital, total_return, trade_count,
                       results, reproducibility_hash, started_at, completed_at
                FROM analytics.backtests
                WHERE id = :id
                """
            ),
            {"id": backtest_id},
        )
        row = result.mappings().one_or_none()
        return None if row is None else dict(row)

    async def list_by_strategy(self, strategy_id: UUID) -> list[object]:
        # Enriched in Step 4.5 (the backtests view, GET /v1/strategies/{id}/
        # backtests): the summary columns plus the self-describing §10.3.7
        # results JSONB (fills, realized/unrealized P&L, determinism hash) so
        # the view renders a backtest fully without a per-row detail fetch.
        # total_return/trade_count/results/hash are NULL for a not-yet-COMPLETED
        # backtest (RUNNING) — the caller renders those as absent.
        result = await self._session.execute(
            text(
                """
                SELECT id, strategy_id, name, status, total_return, trade_count,
                       final_capital, reproducibility_hash, results,
                       started_at, completed_at, created_at
                FROM analytics.backtests
                WHERE strategy_id = :strategy_id
                ORDER BY created_at DESC
                """
            ),
            {"strategy_id": strategy_id},
        )
        return [dict(row) for row in result.mappings().all()]
