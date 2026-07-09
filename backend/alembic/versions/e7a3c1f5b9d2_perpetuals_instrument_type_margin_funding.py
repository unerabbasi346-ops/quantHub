"""Perpetual-futures support: assets.instrument_type, positions margin fields, funding_rates.

Governing specification:
Doc 14 §10.6.6 — Position Management ("Margin Monitoring — Margin requirements
  monitored; margin breaches shall trigger alerts"): the margin/leverage fields
  added to core.positions have a direct doc hook, though Doc 14 does not detail
  their computation.
Doc 14 §10.9.5 — P&L Calculation ("Financing Costs — ... Interest on margin.
  Financing P&L separated from trading P&L"): the ONLY doc hook for perpetual
  funding. Funding is modelled here as a periodic financing cashflow tied to a
  perpetual instrument (market_data.funding_rates); the funding P&L that
  consumes it stays separate from trading P&L per this section.
Doc 11 §1/§2 — Market Data Connectors / Ingestion: market_data.assets and the
  new market_data.funding_rates follow the same shape/idempotency conventions
  as ohlcv_bars/ticks (natural-key UNIQUE, resolve-or-create on assets).
Doc 09 — Database Architecture §Migration Strategy: additive migration chained
  onto the current head (a7d2e1f04b93 untouched); new columns are either
  DEFAULTed-and-backfilled (instrument_type) or nullable (margin fields).
Doc 00 §14.11: cites governing document, section, invariant.

WHY NOW (revisits S-5): S-5 deferred SHORT/COVER, margin, and leverage because
  "the spot crypto instruments this Phase 3A slice exercises" had no derivative
  venue. The owner is a perpetual-futures trader, so that venue now exists —
  the exact trigger OrderSide's own scope-down note anticipated
  ("Deferred until a shortable/derivative venue and its position semantics
  exist"). This migration lays the persistence foundation; see handbook S-10.

DESIGN DECISIONS (JUDGMENT CALLS, §14.5/§14.7 — flagged, not silently decided):
  - instrument_type is SPOT | PERPETUAL only. Dated futures, options, and
    inverse-vs-linear contract distinctions are NOT modelled — the owner trades
    (linear, USDT-settled) perpetuals, and every asset ingested to date is spot.
    NOT NULL DEFAULT 'SPOT' backfills every existing row correctly (all spot).
  - core.positions margin fields are ALL NULLABLE. A spot position leaves them
    NULL (honest absence, same convention as configured_capital / migration
    a7d2e1f04b93) rather than a fabricated leverage=1 / margin=notional. Only a
    perpetual position populates them.
  - F-19 INTERACTION (flagged): margin_used / liquidation_price presuppose an
    authoritative equity/collateral figure, which F-19 records the platform does
    NOT have (equity is a caller-supplied parameter, no NAV/cash ledger). These
    columns are the STORAGE for margin state; the equity source that makes them
    authoritative remains F-19's open gap. Recorded so a future reader does not
    assume these columns imply a real collateral ledger exists.

market_data.funding_rates natural key is (asset_id, funding_time) — the same
  idempotent-ingestion pattern as ohlcv_bars (asset_id, interval, ts) and ticks,
  so re-fetching a funding window revises rather than duplicates (ON CONFLICT at
  the repository layer, Step 2). funding_rate is NUMERIC(18,10): funding rates
  are small fractional figures (e.g. 0.0001 = 0.01% per interval) needing more
  fractional precision than a price column.

Revision ID: e7a3c1f5b9d2
Revises: a7d2e1f04b93
Create Date: 2026-07-09
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "e7a3c1f5b9d2"
down_revision: str | None = "a7d2e1f04b93"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


_TABLE_FUNDING_RATES = """\
CREATE TABLE market_data.funding_rates (
    id                UUID           PRIMARY KEY DEFAULT quanthub_uuid(),
    asset_id          UUID           NOT NULL REFERENCES market_data.assets(id),
    funding_time      TIMESTAMPTZ    NOT NULL,
    funding_rate      NUMERIC(18,10) NOT NULL,
    mark_price        NUMERIC(18,8),
    next_funding_time TIMESTAMPTZ,
    interval_hours    INTEGER,
    source            VARCHAR(64),
    data_quality      VARCHAR(16)    NOT NULL DEFAULT 'CLEAN',
    created_at        TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    CONSTRAINT funding_rates_asset_funding_time_uq UNIQUE (asset_id, funding_time)
);
"""

_INDEXES = [
    "CREATE INDEX funding_rates_asset_id_idx     ON market_data.funding_rates (asset_id);",
    "CREATE INDEX funding_rates_funding_time_idx ON market_data.funding_rates (funding_time DESC);",
    "CREATE INDEX assets_instrument_type_idx     ON market_data.assets (instrument_type);",
]


def upgrade() -> None:
    # market_data.assets — spot vs perpetual distinction. NOT NULL DEFAULT 'SPOT'
    # backfills every existing row (all spot to date) in one statement.
    op.execute(
        sa.text(
            "ALTER TABLE market_data.assets "
            "ADD COLUMN IF NOT EXISTS instrument_type VARCHAR(16) NOT NULL DEFAULT 'SPOT'"
        )
    )

    # core.positions — margin state, all nullable (NULL = spot/unleveraged).
    op.execute(
        sa.text(
            "ALTER TABLE core.positions "
            "ADD COLUMN IF NOT EXISTS leverage NUMERIC(8,2)"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE core.positions "
            "ADD COLUMN IF NOT EXISTS margin_used NUMERIC(28,8)"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE core.positions "
            "ADD COLUMN IF NOT EXISTS liquidation_price NUMERIC(18,8)"
        )
    )

    # market_data.funding_rates — periodic funding cashflow per perpetual instrument.
    op.execute(sa.text(_TABLE_FUNDING_RATES))
    for stmt in _INDEXES:
        op.execute(sa.text(stmt))


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS market_data.funding_rates"))
    op.execute(sa.text("DROP INDEX IF EXISTS market_data.assets_instrument_type_idx"))
    op.execute(sa.text("ALTER TABLE core.positions DROP COLUMN IF EXISTS liquidation_price"))
    op.execute(sa.text("ALTER TABLE core.positions DROP COLUMN IF EXISTS margin_used"))
    op.execute(sa.text("ALTER TABLE core.positions DROP COLUMN IF EXISTS leverage"))
    op.execute(sa.text("ALTER TABLE market_data.assets DROP COLUMN IF EXISTS instrument_type"))
