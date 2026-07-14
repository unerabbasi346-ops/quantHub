# Hermes monitor: strategy status + signal frequency, read directly off
# core.strategies / core.signals / analytics.backtests via raw SQL — NOT the
# strategy_engine repository layer, per the package's import boundary (see
# quant_hub/hermes/__init__.py). This module only reads counts and
# timestamps; it never evaluates a signal or a strategy's own logic.
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class StrategyLifecycle:
    strategy_id: str
    name: str
    status: str
    last_signal_ts: datetime | None
    signals_24h: int
    valid_rate_24h: float | None  # fraction 0..1; None when signals_24h == 0
    latest_backtest_status: str | None
    latest_backtest_completed_at: datetime | None


async def get_strategy_lifecycle(session: AsyncSession) -> list[StrategyLifecycle]:
    rows = (
        await session.execute(
            text(
                """
                WITH signal_stats AS (
                    SELECT
                        strategy_id,
                        MAX(ts) AS last_signal_ts,
                        COUNT(*) FILTER (WHERE ts >= now() - INTERVAL '24 hours') AS signals_24h,
                        COUNT(*) FILTER (
                            WHERE ts >= now() - INTERVAL '24 hours' AND validation_status = 'VALID'
                        ) AS valid_signals_24h
                    FROM core.signals
                    GROUP BY strategy_id
                ),
                latest_backtest AS (
                    SELECT DISTINCT ON (strategy_id)
                        strategy_id, status, completed_at
                    FROM analytics.backtests
                    WHERE strategy_id IS NOT NULL
                    ORDER BY strategy_id, created_at DESC
                )
                SELECT
                    s.id AS strategy_id,
                    s.name,
                    s.status,
                    ss.last_signal_ts,
                    COALESCE(ss.signals_24h, 0) AS signals_24h,
                    ss.valid_signals_24h,
                    lb.status AS latest_backtest_status,
                    lb.completed_at AS latest_backtest_completed_at
                FROM core.strategies s
                LEFT JOIN signal_stats ss ON ss.strategy_id = s.id
                LEFT JOIN latest_backtest lb ON lb.strategy_id = s.id
                WHERE s.deleted_at IS NULL
                ORDER BY s.name
                """
            )
        )
    ).all()

    out: list[StrategyLifecycle] = []
    for row in rows:
        signals_24h = row.signals_24h
        valid_rate = (row.valid_signals_24h / signals_24h) if signals_24h and row.valid_signals_24h is not None else None
        out.append(
            StrategyLifecycle(
                strategy_id=str(row.strategy_id),
                name=row.name,
                status=row.status,
                last_signal_ts=row.last_signal_ts,
                signals_24h=signals_24h,
                valid_rate_24h=valid_rate,
                latest_backtest_status=row.latest_backtest_status,
                latest_backtest_completed_at=row.latest_backtest_completed_at,
            )
        )
    return out
