"""analytics.backtest_equity_curve + analytics.backtest_computed_metrics — F-21.

Governing specification:
Doc 14 §10.3.7 — Performance Metrics: the full metric suite (Sharpe/Sortino/
  Calmar/max drawdown/win rate/profit factor/expectancy) that BacktestResult's
  docstring (domain/backtesting/entities.py) flags as deferred pending "a
  per-step equity-curve / return series this single-pass engine does not
  accumulate" (F-21, same data gap as F-18).
Doc 09 — Database Architecture §Migration Strategy: additive migration
  chained onto the current head (a2e4c7b1d6f9).
Doc 00 §14.11: cites governing document, section, invariant.

WHY NOW: closes F-21 by having the backtest engine accumulate a real
per-step equity curve (mark-to-market at every bar, not only fill bars) and
computing the metric suite from it deterministically (P-13).

DESIGN DECISIONS (JUDGMENT CALLS, §14.5/§14.7 — flagged):
  - `analytics.backtests` ALREADY HAS `sharpe_ratio`/`max_drawdown` columns
    (initial schema, migration c3a8f2b91e4d) that were always left NULL
    (persistence/repositories/backtesting.py's `complete()` docstring says so
    explicitly). This migration does NOT repurpose those two columns: the
    task's spec asks for a dedicated `analytics.backtest_computed_metrics`
    table carrying a wider metric set (win_rate/sortino/calmar/profit_factor/
    expectancy) that has no columns on `analytics.backtests` at all — a
    single new table is the honest single source of truth for the full
    suite, rather than splitting it across an old two-column stub and a new
    table. The two legacy NULL columns are left exactly as they are
    (untouched, still NULL) — a future cleanup could backfill or drop them,
    out of scope here.
  - COMPOSITE PRIMARY KEY (backtest_run_id, step) on the equity curve, no
    surrogate id — same reasoning as market_data.open_interest (migration
    b4f8e21ac9d3): the natural key IS the row identity (one equity
    observation per backtest per step).
  - `backtest_computed_metrics` uses `backtest_run_id` itself as the PRIMARY
    KEY (one metrics row per backtest, computed once after the run
    completes) rather than a surrogate id.

Revision ID: c7d3f9a2e5b8
Revises: a2e4c7b1d6f9
Create Date: 2026-07-14
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "c7d3f9a2e5b8"
down_revision: str | None = "a2e4c7b1d6f9"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


_TABLE_EQUITY_CURVE = """\
CREATE TABLE analytics.backtest_equity_curve (
    backtest_run_id  UUID           NOT NULL REFERENCES analytics.backtests(id),
    step             INTEGER        NOT NULL,
    ts               TIMESTAMPTZ    NOT NULL,
    portfolio_value  NUMERIC(28,8)  NOT NULL,
    return_pct       NUMERIC(28,8)  NOT NULL,
    PRIMARY KEY (backtest_run_id, step)
);
"""

_TABLE_COMPUTED_METRICS = """\
CREATE TABLE analytics.backtest_computed_metrics (
    backtest_run_id       UUID           PRIMARY KEY REFERENCES analytics.backtests(id),
    win_rate              NUMERIC(10,6),
    sharpe_ratio          NUMERIC(10,6),
    sortino_ratio         NUMERIC(10,6),
    max_drawdown_pct      NUMERIC(10,6),
    calmar_ratio          NUMERIC(10,6),
    profit_factor         NUMERIC(10,6),
    expectancy_per_trade  NUMERIC(28,8),
    computed_at           TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);
"""

_INDEXES = [
    "CREATE INDEX backtest_equity_curve_ts_idx ON analytics.backtest_equity_curve (backtest_run_id, ts);",
]

_DROP_INDEXES = [
    "DROP INDEX IF EXISTS analytics.backtest_equity_curve_ts_idx;",
]


def upgrade() -> None:
    op.execute(sa.text(_TABLE_EQUITY_CURVE))
    op.execute(sa.text(_TABLE_COMPUTED_METRICS))
    for stmt in _INDEXES:
        op.execute(sa.text(stmt))


def downgrade() -> None:
    for stmt in _DROP_INDEXES:
        op.execute(sa.text(stmt))
    op.execute(sa.text("DROP TABLE IF EXISTS analytics.backtest_computed_metrics"))
    op.execute(sa.text("DROP TABLE IF EXISTS analytics.backtest_equity_curve"))
