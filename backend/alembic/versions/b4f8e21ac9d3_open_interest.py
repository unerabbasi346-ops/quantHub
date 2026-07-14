"""market_data.open_interest — perpetual open-interest history.

Governing specification:
Doc 14 §10.9.5 — P&L Calculation / Financing Costs: the same doc anchor
  funding_rates (migration e7a3c1f5b9d2) hooks to — open interest is a
  perpetual-only market-structure series with no dedicated Doc 14 section of
  its own, same genuine spec gap already flagged for funding.
Doc 11 §1/§2 — Market Data Connectors / Ingestion: follows the exact same
  natural-key/idempotent-ingestion shape as funding_rates and ohlcv_bars.
Doc 09 — Database Architecture §Migration Strategy: additive migration
  chained onto the current head (e7a3c1f5b9d2).
Doc 00 §14.11: cites governing document, section, invariant.

WHY NOW: closes the data gap that blocked Lanchester's OI-derived features
(handbook/LANCHESTER_INTEGRATION_INVESTIGATION.md — no-OI retrain was the
prior workaround) and enables an OI display on the Markets page.

DESIGN DECISIONS (JUDGMENT CALLS, §14.5/§14.7 — flagged):
  - COMPOSITE PRIMARY KEY (asset_id, ts) — no surrogate `id`, unlike
    funding_rates (which uses a UUID PK + separate UNIQUE constraint).
    Deliberately different from that precedent: this table's natural key IS
    the row identity (an OI observation is exactly one number per instrument
    per timestamp), so a surrogate id would be a redundant column with no
    consumer — same reasoning ohlcv_bars/ticks already apply as append-only
    natural-keyed series. ON CONFLICT targets the primary key directly.
  - `open_interest_usdt` NOT NULL, `open_interest_contracts` NULLABLE: ccxt's
    unified fetch_open_interest_history always returns `openInterestValue`
    (USDT-denominated) alongside `openInterestAmount` (contract count) on
    every exchange checked (Binance live-verified) — but a future connector
    might only expose the notional figure, so the contracts column stays
    optional rather than forcing a fabricated conversion.
  - PERPETUAL-only by convention, not by CHECK constraint: mirrors
    funding_rates (also has no instrument_type-enforcing constraint on
    itself) — a SPOT asset_id simply never has ingestion code that writes
    here (application/script-layer discipline, not a DB-enforced rule),
    consistent with how the existing funding_rates table draws the same
    boundary.

Revision ID: b4f8e21ac9d3
Revises: e7a3c1f5b9d2
Create Date: 2026-07-14
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "b4f8e21ac9d3"
down_revision: str | None = "e7a3c1f5b9d2"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


_TABLE_OPEN_INTEREST = """\
CREATE TABLE market_data.open_interest (
    asset_id                 UUID           NOT NULL REFERENCES market_data.assets(id),
    ts                       TIMESTAMPTZ    NOT NULL,
    open_interest_usdt       NUMERIC(28,8)  NOT NULL,
    open_interest_contracts  NUMERIC(28,8),
    source                   VARCHAR(64),
    data_quality             VARCHAR(16)    NOT NULL DEFAULT 'CLEAN',
    created_at               TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    PRIMARY KEY (asset_id, ts)
);
"""

_INDEXES = [
    "CREATE INDEX open_interest_ts_idx ON market_data.open_interest (ts DESC);",
]

_DROP_INDEXES = [
    "DROP INDEX IF EXISTS market_data.open_interest_ts_idx;",
]


def upgrade() -> None:
    op.execute(sa.text(_TABLE_OPEN_INTEREST))
    for stmt in _INDEXES:
        op.execute(sa.text(stmt))


def downgrade() -> None:
    for stmt in _DROP_INDEXES:
        op.execute(sa.text(stmt))
    op.execute(sa.text("DROP TABLE IF EXISTS market_data.open_interest"))
