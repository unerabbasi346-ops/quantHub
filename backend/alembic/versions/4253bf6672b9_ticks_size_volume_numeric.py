"""market_data.ticks size/volume columns: INTEGER/BIGINT -> NUMERIC(28,8)
(fractional-size fix, F-1 — closes the last quantity-precision item from
the Phase 3 dependency-chain table alongside Step 3.0's order/execution/
position fix).

Governing specification:
Doc 09 — Database Architecture §Entity Standards: schema changes must
  preserve data fidelity — a column type that cannot losslessly represent
  a connector's real fractional output value violates this, the same
  standard already applied to ohlcv_bars.volume (migration fcec1b5ac8a0,
  Step 1.4) and core.orders/executions/positions.quantity (migration
  861eb5a06b23, Step 3.0).
Doc 09 §Migration Strategy: additive migration chained onto the current
  head (861eb5a06b23 is not touched by this migration).
Doc 11 §1/§2: acquired data must reach Persist without lossy
  normalization — a value truncated in Python before the INSERT is
  corrupted regardless of what the DB column can hold.
Doc 00 §14.11: implementation cites governing document, section, and invariant.

Context (F-1, tracked since the Phase 1->Phase 2 transition, closed here
per explicit Step 3.0 instruction: "cheap to close now while doing the
others"): market_data.ticks.bid_size/ask_size/last_size shipped (Step
1.1, revision c3a8f2b91e4d) as INTEGER; volume shipped as BIGINT.

LIVE ACTIVE CORRUPTION FOUND while implementing this migration (Doc 00
§14.5 — flagged immediately, not silently left): CCXTConnector.
fetch_latest_tick (infrastructure/market_data/ccxt_connector.py) contains
`volume=int(ticker["baseVolume"])` — ccxt's baseVolume is a real float
representing fractional base-asset cumulative volume (the exact field
whose OHLCV-bar counterpart was already fixed in migration
fcec1b5ac8a0/Step 1.4). This is the identical bug class, in the tick path
instead of the bar path: every live fetch_latest_tick call silently
truncates a real fractional volume to a whole number. Fixed in this same
step (see connector diff) — not deferred, since the DB-only widening
here would not have stopped the truncation, which happens in Python
BEFORE the value ever reaches the SQL parameter. bid_size/ask_size/
last_size have no active writer today (no connector currently populates
them — verified via code search), so there is no live corruption for
those three; the domain-entity type widening (RawTick/Tick: int | None ->
Decimal | None, this same step) is preventive, closing the gap before a
future connector could reintroduce the ohlcv_bars.volume bug pattern for
size fields.

F-11 (handbook/KNOWN_LIMITATIONS.md): this migration is part of the same
deliberate, flagged divergence documented under F-11 for Step 3.0's
orders/executions/positions fix — Doc 14 §10.7.5 types order-related
quantity as `integer`; this migration extends the same NUMERIC choice to
market-data-side size/volume fields for the same fractional-crypto reason,
though F-11 itself is scoped to the order/execution/position columns
specifically named in Doc 14 §10.7.5's contract.

JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged): NUMERIC(28,8) chosen to
match ohlcv_bars.volume and core.orders/executions/positions.quantity
exactly (migrations fcec1b5ac8a0, 861eb5a06b23) — same "count of units,
needs wide integer-part headroom" reasoning. Neither Doc 09 nor Doc 11
specifies column-level precision/scale for these fields.

Revision ID: 4253bf6672b9
Revises: 861eb5a06b23
Create Date: 2026-07-03
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "4253bf6672b9"
down_revision: str | None = "861eb5a06b23"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

_ALTER_TO_NUMERIC = """\
ALTER TABLE market_data.ticks
    ALTER COLUMN bid_size TYPE NUMERIC(28,8) USING bid_size::numeric(28,8),
    ALTER COLUMN ask_size TYPE NUMERIC(28,8) USING ask_size::numeric(28,8),
    ALTER COLUMN last_size TYPE NUMERIC(28,8) USING last_size::numeric(28,8),
    ALTER COLUMN volume TYPE NUMERIC(28,8) USING volume::numeric(28,8);
"""

_ALTER_TO_INTEGER_BIGINT = """\
ALTER TABLE market_data.ticks
    ALTER COLUMN bid_size TYPE INTEGER USING TRUNC(bid_size)::integer,
    ALTER COLUMN ask_size TYPE INTEGER USING TRUNC(ask_size)::integer,
    ALTER COLUMN last_size TYPE INTEGER USING TRUNC(last_size)::integer,
    ALTER COLUMN volume TYPE BIGINT USING TRUNC(volume)::bigint;
"""


def upgrade() -> None:
    # F-1: acquired fractional tick sizes/volume must reach persistence
    # without lossy truncation, matching the ohlcv_bars.volume precedent.
    op.execute(sa.text(_ALTER_TO_NUMERIC))


def downgrade() -> None:
    # Doc 09 §Migration Strategy: downgrade restores the prior schema
    # shape. NOT data-fidelity-preserving — re-truncates any fractional
    # value written under NUMERIC back to whole units, by design (same
    # documented behavior as fcec1b5ac8a0's and 861eb5a06b23's downgrades).
    op.execute(sa.text(_ALTER_TO_INTEGER_BIGINT))
