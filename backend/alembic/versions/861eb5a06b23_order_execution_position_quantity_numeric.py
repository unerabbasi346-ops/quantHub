"""core.orders/executions/positions quantity columns: INTEGER -> NUMERIC(28,8)
(fractional-quantity fix — prerequisite for Phase 3 order/execution/position writes).

Governing specification:
Doc 09 — Database Architecture
  §Entity Standards: schema changes must preserve data fidelity for every
    entity — a column type that cannot losslessly represent a real
    fractional order/execution/position quantity (e.g. crypto orders below
    1 unit) violates this, same standard already applied to
    market_data.ohlcv_bars.volume (migration fcec1b5ac8a0, Step 1.4).
  §Migration Strategy: Alembic is the authoritative deployment path;
    additive/corrective migration chained onto the current head
    (7c7482e4e00a is not touched by this migration).
Doc 14 §10.7.5 — Pre-Trade Risk Check API: this contract types `quantity`
  as `integer`. This migration KNOWINGLY DIVERGES from that literal typing
  — see F-11 below.
Doc 00 §14.11: implementation cites governing document, section, and invariant.

Context (Phase 3 planning inventory, 2026-07-03; tracked as F-2/F-3/F-4
since the Phase 1 -> Phase 2 transition): core.orders.quantity,
core.orders.filled_quantity, core.executions.quantity, and
core.positions.quantity all shipped (Step 1.1, revision c3a8f2b91e4d) as
INTEGER. Phase 3 (Doc 14 Order Generation / Execution / Doc 15 Position
Sizing) is the first work that will actually write to these columns for
a strategy trading fractional-unit instruments (e.g. crypto) — exactly
the trigger condition F-2/F-3/F-4 named. This is the SAME CLASS OF BUG as
the confirmed ohlcv_bars.volume truncation (migration fcec1b5ac8a0,
Step 1.4), fixed here BEFORE any order/execution/position write code is
implemented, per S-4/S-5's explicit prerequisite-step discipline (this is
the "Step 2.5, conditional" step S-4 named, executed now as Step 3.0
since Phase 3 is where the trigger condition is actually met).

F-11 (handbook/KNOWN_LIMITATIONS.md): this is a DELIBERATE, FLAGGED
DIVERGENCE from Doc 14 §10.7.5's Pre-Trade Risk Check API contract, which
types `quantity` as `integer`, and from Doc 09's original Step 1.1 schema,
which matched that typing. This migration intentionally disagrees with
the docs' own integer typing because fractional crypto order/execution/
position quantities require it — the identical reasoning already
live-verified for ohlcv_bars.volume. Not a silent gap-fill: cite F-11
wherever these columns are subsequently read from or written to (order
generation, execution handling, position updates) so the NUMERIC choice
is never mistaken for an unflagged oversight.

JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged, not silently decided):
NUMERIC(28,8) chosen to match ohlcv_bars.volume's precision/scale exactly
(migration fcec1b5ac8a0) rather than the narrower NUMERIC(18,8) used by
price columns — quantities, like volume, are counts of units and need the
same wide-integer-part headroom for low-unit-price/high-supply
instruments. Neither Doc 09 nor Doc 14 specifies column-level
precision/scale for quantity fields.

Revision ID: 861eb5a06b23
Revises: 7c7482e4e00a
Create Date: 2026-07-03
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "861eb5a06b23"
down_revision: str | None = "7c7482e4e00a"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

_ALTER_TO_NUMERIC = """\
ALTER TABLE core.orders
    ALTER COLUMN quantity TYPE NUMERIC(28,8) USING quantity::numeric(28,8),
    ALTER COLUMN filled_quantity TYPE NUMERIC(28,8) USING filled_quantity::numeric(28,8),
    ALTER COLUMN filled_quantity SET DEFAULT 0;

ALTER TABLE core.executions
    ALTER COLUMN quantity TYPE NUMERIC(28,8) USING quantity::numeric(28,8);

ALTER TABLE core.positions
    ALTER COLUMN quantity TYPE NUMERIC(28,8) USING quantity::numeric(28,8),
    ALTER COLUMN quantity SET DEFAULT 0;
"""

_ALTER_TO_INTEGER = """\
ALTER TABLE core.orders
    ALTER COLUMN quantity TYPE INTEGER USING TRUNC(quantity)::integer,
    ALTER COLUMN filled_quantity TYPE INTEGER USING TRUNC(filled_quantity)::integer,
    ALTER COLUMN filled_quantity SET DEFAULT 0;

ALTER TABLE core.executions
    ALTER COLUMN quantity TYPE INTEGER USING TRUNC(quantity)::integer;

ALTER TABLE core.positions
    ALTER COLUMN quantity TYPE INTEGER USING TRUNC(quantity)::integer,
    ALTER COLUMN quantity SET DEFAULT 0;
"""


def upgrade() -> None:
    # F-2/F-3/F-4: acquired/computed fractional quantities must reach
    # persistence without lossy truncation. F-11: deliberate divergence
    # from Doc 14 §10.7.5's `integer` typing, flagged not silent.
    op.execute(sa.text(_ALTER_TO_NUMERIC))


def downgrade() -> None:
    # Doc 09 §Migration Strategy: downgrade restores the prior schema
    # shape. NOT data-fidelity-preserving — re-truncates any fractional
    # quantity written under NUMERIC back to whole units, by design (same
    # documented behavior as fcec1b5ac8a0's downgrade).
    op.execute(sa.text(_ALTER_TO_INTEGER))
