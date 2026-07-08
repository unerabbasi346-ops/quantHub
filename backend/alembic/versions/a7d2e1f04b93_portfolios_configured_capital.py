"""core.portfolios: add configured_capital (operator-set capital, NOT a NAV ledger).

Governing specification:
Doc 15 §11.4 — Capital Allocation (deferred entirely per S-5): a real capital
  system tracks deposits/withdrawals/financing/realized-P&L roll-up into a
  persisted, platform-computed equity figure. This migration does NOT build
  that. It adds a single, nullable, operator-CONFIGURED capital figure so the
  dashboard can carry a portfolio's intended capital base.
Doc 09 — Database Architecture §Migration Strategy: additive migration chained
  onto the current head (f1c8a3e94d20 untouched); nullable column, no backfill.
Doc 00 §14.11: cites governing document, section, invariant.

F-19 (flagged, NOT resolved here — this is the honest crux): configured_capital
  is a bare operator-supplied number with NO backing NAV/cash ledger, exactly
  the missing authoritative-equity source F-19 records. It is deliberately a
  SEPARATE column from any computed equity precisely so it is never mistaken
  for one: leverage/risk math (RiskService, §11.5.3) continues to take its
  `equity` as an explicit caller parameter and does NOT read this column, so
  setting capital here does NOT silently feed leverage or any risk-limit
  determination. The UI labels the control accordingly. F-19 stays open; a real
  §11.4 ledger remains deferred. Recorded so a future reader does not assume
  this column is a real equity source.

Type NUMERIC(28,8) matches the money-precision convention established for
  core.positions/orders/executions after Step 3.0 (F-2/F-3/F-4). Nullable: a
  portfolio that has never had capital configured reads NULL (honest absence),
  not a fabricated 0.

Revision ID: a7d2e1f04b93
Revises: f1c8a3e94d20
Create Date: 2026-07-08
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "a7d2e1f04b93"
down_revision: str | None = "f1c8a3e94d20"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    # Additive, nullable — no backfill (NULL = "never configured", honest).
    op.execute(
        sa.text(
            "ALTER TABLE core.portfolios "
            "ADD COLUMN IF NOT EXISTS configured_capital NUMERIC(28,8)"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE core.portfolios DROP COLUMN IF EXISTS configured_capital"))
