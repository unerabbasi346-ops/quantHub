# Governing specification: Doc 14 §10.3 — Backtesting Engine Architecture
#                          Doc 09 — Database Architecture (analytics.backtests, Step 1.1 schema)
#                          Doc 07 §Dependency Rules / §Implementation Rules
# Per Doc 00 §14.11
#
# Exercises the read path the Step 4.5 backtests view consumes —
# SQLAlchemyBacktestRepository.list_by_strategy, enriched this step to carry
# the promoted metric columns + the self-describing §10.3.7 results JSONB
# (fills, realized/unrealized P&L, determinism hash). create/complete are the
# real write path (Step 3.7); here they run against live Postgres to set up the
# row, then the enriched list read is verified. Mirrors
# test_strategy_repository.py / test_execution_repository.py.
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from quant_hub.domain.backtesting.entities import BacktestConfig, BacktestResult
from quant_hub.persistence.repositories.backtesting import SQLAlchemyBacktestRepository

_T0 = datetime(2026, 6, 1, tzinfo=timezone.utc)


def _unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


async def _mk_strategy(session: AsyncSession) -> uuid.UUID:
    row = await session.execute(
        text("INSERT INTO core.strategies (name, version) VALUES (:n, '1.0') RETURNING id"),
        {"n": _unique("bt-strat")},
    )
    return row.scalar_one()


def _config() -> BacktestConfig:
    return BacktestConfig(
        name="repo-test", symbol="BTC/USDT", exchange="binance", asset_class="crypto",
        interval="1h", strategy_config={"short_window": 5}, start=_T0,
        end=_T0 + timedelta(hours=10), initial_capital=Decimal("1000000"),
        max_position_pct=Decimal("0.10"),
    )


def _result() -> BacktestResult:
    return BacktestResult(
        bars_processed=500, signals_generated=481, orders_created=481,
        orders_filled=481, orders_rejected=0,
        final_position_quantity=Decimal("0.00405983"), realized_pnl=Decimal("-91.3799"),
        unrealized_pnl=Decimal("-0.0087"), final_capital=Decimal("999908.6114"),
        total_return=Decimal("-0.0000913886"), trade_count=481,
        reproducibility_hash="abc123def456",
    )


async def test_list_by_strategy_returns_empty_for_strategy_without_backtests(
    db_session: AsyncSession,
) -> None:
    repo = SQLAlchemyBacktestRepository(db_session)
    strategy_id = await _mk_strategy(db_session)
    assert await repo.list_by_strategy(strategy_id) == []


async def test_list_by_strategy_surfaces_completed_metrics_and_results(
    db_session: AsyncSession,
) -> None:
    # create (RUNNING) -> complete (COMPLETED) -> the enriched list read must
    # surface the promoted metric columns AND the self-describing results JSONB
    # (fills, realized/unrealized P&L, determinism hash) the view renders.
    repo = SQLAlchemyBacktestRepository(db_session)
    strategy_id = await _mk_strategy(db_session)

    backtest_id = await repo.create(_config(), strategy_id)
    await repo.complete(backtest_id, _result())

    rows = await repo.list_by_strategy(strategy_id)

    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == backtest_id
    assert row["status"] == "COMPLETED"
    # The promoted total_return column is NUMERIC(scale 8) — it rounds to 8 dp;
    # the FULL precision is preserved in the results JSONB (asserted below).
    assert row["total_return"] == Decimal("-0.00009139")
    assert row["trade_count"] == 481
    assert row["reproducibility_hash"] == "abc123def456"
    # results JSONB round-trips as a dict with Decimals stored as strings, at
    # full (unrounded) precision.
    assert row["results"]["total_return"] == "-0.0000913886"
    assert row["results"]["orders_filled"] == 481
    assert row["results"]["realized_pnl"] == "-91.3799"
    assert row["results"]["unrealized_pnl"] == "-0.0087"


async def test_list_by_strategy_running_backtest_has_null_metrics(
    db_session: AsyncSession,
) -> None:
    # A created-but-not-completed backtest lists with null metrics/results —
    # the view renders those as absent, never as a fabricated zero.
    repo = SQLAlchemyBacktestRepository(db_session)
    strategy_id = await _mk_strategy(db_session)

    backtest_id = await repo.create(_config(), strategy_id)

    rows = await repo.list_by_strategy(strategy_id)

    assert len(rows) == 1
    assert rows[0]["id"] == backtest_id
    assert rows[0]["status"] == "RUNNING"
    assert rows[0]["total_return"] is None
    assert rows[0]["trade_count"] is None
    assert rows[0]["results"] is None
    assert rows[0]["reproducibility_hash"] is None
