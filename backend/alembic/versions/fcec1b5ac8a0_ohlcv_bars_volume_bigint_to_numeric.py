"""market_data.ohlcv_bars.volume: BIGINT -> NUMERIC(28,8) (fractional-volume fix).

Governing specification:
Doc 09 — Database Architecture
  §Entity Standards: schema changes must preserve data fidelity/auditability
    for every entity — a column type that cannot losslessly represent a
    connector's real output value violates this.
  §Migration Strategy: Alembic is the authoritative deployment path;
    schema changes are additive/corrective migrations chained onto the
    existing revision history, not hand-edits to already-applied revisions
    (a428732d6bfe is not touched by this migration).
Doc 11 — Data Engineering
  §1 Market Data Connectors: adapter responsibilities include "schema
    normalization" — normalization must not silently discard precision
    the source actually returns.
  §2 Historical Data Ingestion, Pipeline Stages (Acquire -> ... -> Persist):
    a value acquired from a connector must reach Persist intact.
Doc 00 §14.11: implementation cites governing document, section, and invariant.

Context (Step 1.4 live-execution finding, confirmed by the user as active
data corruption, not deferrable): market_data.ohlcv_bars.volume shipped
(Step 1.1, revision c3a8f2b91e4d) as BIGINT. CCXTConnector.fetch_ohlcv
(Step 1.2/1.4) receives ccxt's real fetch_ohlcv volume field as a float
representing fractional base-asset units (live-observed example: BTC/USDT
1h bar with volume 573.38622 BTC). Storing that in a BIGINT column forces
truncation to an integer (573), silently discarding the fractional part on
every crypto bar ingested to date.

JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged, not silently decided):
NUMERIC(28,8) chosen over matching the existing OHLC price columns'
NUMERIC(18,8) exactly. 8 decimal places matches typical exchange base-unit
precision (Doc 11 does not specify a required precision, this mirrors the
existing vwap/price column scale). The wider integer part (20 digits vs.
price columns' 10) is intentional headroom: unlike price, volume is a
*count* of units and needs to safely hold outlier cases price columns
never see — very-low-unit-price/high-supply tokens can post daily base-unit
volumes many orders of magnitude larger than their price. This is a
judgment call, not a value mandated by Doc 09 or Doc 11 (neither document
specifies column-level precision/scale standards).

Revision ID: fcec1b5ac8a0
Revises: a428732d6bfe
Create Date: 2026-07-02
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "fcec1b5ac8a0"
down_revision: str | None = "a428732d6bfe"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

_ALTER_VOLUME_TO_NUMERIC = """\
ALTER TABLE market_data.ohlcv_bars
    ALTER COLUMN volume TYPE NUMERIC(28,8) USING volume::numeric(28,8),
    ALTER COLUMN volume SET DEFAULT 0;
"""

_ALTER_VOLUME_TO_BIGINT = """\
ALTER TABLE market_data.ohlcv_bars
    ALTER COLUMN volume TYPE BIGINT USING TRUNC(volume)::bigint,
    ALTER COLUMN volume SET DEFAULT 0;
"""


def upgrade() -> None:
    # Doc 11 §1/§2: acquired data must reach Persist without lossy
    # normalization; BIGINT could not hold ccxt's real fractional volume.
    op.execute(sa.text(_ALTER_VOLUME_TO_NUMERIC))


def downgrade() -> None:
    # Doc 09 §Migration Strategy: downgrade restores the prior schema shape.
    # NOT data-fidelity-preserving — this re-truncates any fractional
    # volume written under NUMERIC back to whole units, by design (a
    # downgrade undoes the schema, it cannot undo already-lost precision
    # the other direction; this direction knowingly discards it again).
    op.execute(sa.text(_ALTER_VOLUME_TO_BIGINT))
