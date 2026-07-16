"""core.executions trade-result columns + analytics.backtests.benchmark_return.

Governing specification:
Doc 14 §10.9.4 — Trade Recording: the closing fill of a trade records its
  outcome (exit reason, realized move).
Doc 14 §10.3.7/§10.3.8 — Performance Metrics / Benchmark Specification: a
  backtest's total_return is only interpretable against a benchmark.
Doc 09 — Database Architecture §Migration Strategy: additive migration
  chained onto the current head (c7d3f9a2e5b8).
Doc 00 §14.11: cites governing document, section, invariant.

WHY NOW: the backtest engine's new TP/SL + one-trade-at-a-time step (Engine:
TP/SL, one-trade rule, 2%/3% sizing, benchmark) needs somewhere to persist a
trade's realized outcome and a backtest's benchmark comparison. Both are
computed by real engine logic — never fabricated.

DESIGN DECISIONS (JUDGMENT CALLS, §14.5/§14.7 — flagged):
  - core.executions.price_return_pct/market_move_pct/exit_reason: NULLABLE,
    same precedent as migration a2e4c7b1d6f9's realized_pnl — populated ONLY
    on a backtest trade's CLOSING fill (entry fills and every live/paper fill
    have no TP/SL concept and stay NULL, never backfilled with a fabricated
    value).
  - NUMERIC(10,4): a percentage return column, not a money amount — 4 decimal
    places matches this schema's other percentage-shaped NUMERIC columns
    (e.g. core.positions' return-style fields), far smaller range than the
    NUMERIC(20,4) money-scale columns.
  - exit_reason VARCHAR(20): a small fixed vocabulary (TP_HIT/SL_HIT/
    END_OF_DATA) — VARCHAR with an app-level check, not a DB CHECK
    constraint or enum type, matching this schema's existing convention for
    free-form-but-bounded status strings (e.g. core.orders.status).
  - analytics.backtests.benchmark_return NUMERIC(28,8): identical scale to
    the existing total_return column it is compared against (same migration
    c7d3f9a2e5b8 precedent) — nullable, since not every backtest configures
    a benchmark instrument.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "d3f7a2c9b5e1"
down_revision = "c7d3f9a2e5b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "executions",
        sa.Column("price_return_pct", sa.Numeric(10, 4), nullable=True),
        schema="core",
    )
    op.add_column(
        "executions",
        sa.Column("market_move_pct", sa.Numeric(10, 4), nullable=True),
        schema="core",
    )
    op.add_column(
        "executions",
        sa.Column("exit_reason", sa.String(20), nullable=True),
        schema="core",
    )
    op.add_column(
        "backtests",
        sa.Column("benchmark_return", sa.Numeric(28, 8), nullable=True),
        schema="analytics",
    )


def downgrade() -> None:
    op.drop_column("backtests", "benchmark_return", schema="analytics")
    op.drop_column("executions", "exit_reason", schema="core")
    op.drop_column("executions", "market_move_pct", schema="core")
    op.drop_column("executions", "price_return_pct", schema="core")
