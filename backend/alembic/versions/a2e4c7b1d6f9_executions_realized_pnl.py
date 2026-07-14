"""core.executions.realized_pnl — fill-level realized P&L.

Governing specification:
Doc 14 §10.9.4 — Trade Recording: "the trade record shall capture ... P&L
  impact"; §10.9.5 — realized P&L "on trade execution" for closing trades.
Doc 09 — Database Architecture §Migration Strategy: additive migration
  chained onto the current head (b4f8e21ac9d3).
Doc 00 §14.11: cites governing document, section, invariant.

WHY NOW: the Execution page rebuild needs fill-level win/loss data (trade
ratio, P&L column, cumulative P&L, per-strategy P&L breakdown). The realized
P&L for a fill is ALREADY computed deterministically at fill time
(domain/portfolio/positions.py::apply_fill_to_position, called from
application/execution/service.py) but was only ever folded into
core.positions.realized_pnl_today (a daily-resetting position-level
aggregate) and discarded — never persisted onto the trade record it
conceptually belongs to (§10.9.3 "produces: realized_pnl for the portion of
an opposing position it closes"). This column captures that already-real
number rather than fabricating a new one.

DESIGN DECISIONS (JUDGMENT CALLS, §14.5/§14.7 — flagged):
  - NULLABLE: existing rows predate this column; a backfill script
    (scripts/backfill_execution_realized_pnl.py) replays the exact same
    apply_fill_to_position logic chronologically per (portfolio_id,
    asset_id) to populate them deterministically. Nullable stays the honest
    contract for any future row where backfill/computation is skipped,
    though the going-forward write path (service.py) always supplies it.
  - Same NUMERIC(20,4) scale as core.positions' P&L columns
    (_PNL_SCALE = 0.0001) — this is the same money-scale quantity.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "a2e4c7b1d6f9"
down_revision = "b4f8e21ac9d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "executions",
        sa.Column("realized_pnl", sa.Numeric(20, 4), nullable=True),
        schema="core",
    )


def downgrade() -> None:
    op.drop_column("executions", "realized_pnl", schema="core")
