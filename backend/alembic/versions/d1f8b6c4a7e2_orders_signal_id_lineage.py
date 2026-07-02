"""core.orders: add dedicated signal_id column (FK-enforced signal lineage).

Governing specification:
Doc 14 §10.6.5 — Order Generation: "Orders shall be created with complete
  lineage to the originating signal."
Doc 14 §10.7.3 — Order Model: canonical order specification lists a
  "Signal Reference — Lineage to the originating signal" field.
Doc 09 — Database Architecture §Migration Strategy: Alembic is the
  authoritative deployment path; additive migration chained onto the
  current head (4253bf6672b9 is not touched by this migration).
Doc 00 §14.11: implementation cites governing document, section, and invariant.

Context (F-13, handbook/KNOWN_LIMITATIONS.md — Step 3.3 finding,
2026-07-03): the Step 1.1 schema (revision c3a8f2b91e4d) shipped
core.orders with NO signal_id column, despite §10.6.5/§10.7.3 requiring
signal lineage. Step 3.3's first implementation stored
OrderIntent.signal_id into the existing `correlation_id` column as a
best-effort substitute — flagged at the time as COLUMN-OVERLOADING, not
merely a missing-FK gap: `correlation_id` already has an established,
distinct platform meaning (Doc 10 §6 event envelope, Doc 10 §8 Logging &
Observability "Request ID"/"Correlation ID" as separate fields, Doc 14
§10.1.8 event correlation identifiers, and the sibling
audit.audit_log.correlation_id column, Step 1.1 schema — all
request/event-tracing, not signal lineage). This migration resolves F-13
by adding the dedicated column §10.7.3 actually specifies, so
correlation_id can be left genuinely free for its real purpose.

NULLABLE (per this step's explicit instruction): not every order
originates from a signal — a manually-placed order, or an order from a
future non-signal-driven source, legitimately has no signal to reference.
§10.7.3 does not state the Signal Reference is mandatory on every order,
only that lineage exists "to the originating signal" when there is one.

FOREIGN KEY to core.signals(id): closes the referential-integrity gap
F-13 called out (a previously unenforced UUID substitute in
correlation_id). No ON DELETE clause specified — signals are append-only
(P-5, Step 2.2) and never deleted by any code path today, so the default
NO ACTION is sufficient; revisit only if a signal-deletion path is ever
introduced.

Index added following the Step 1.1 schema's own convention for
core.orders' other lineage/lookup columns (orders_portfolio_id_idx,
orders_strategy_id_idx, orders_asset_id_idx, etc.) — signal_id is a
foreign-key lookup column of the same kind.

Revision ID: d1f8b6c4a7e2
Revises: 4253bf6672b9
Create Date: 2026-07-03
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "d1f8b6c4a7e2"
down_revision: str | None = "4253bf6672b9"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

_ADD_SIGNAL_ID = """\
ALTER TABLE core.orders
    ADD COLUMN signal_id UUID REFERENCES core.signals(id);

CREATE INDEX orders_signal_id_idx ON core.orders (signal_id);
"""

_DROP_SIGNAL_ID = """\
DROP INDEX IF EXISTS core.orders_signal_id_idx;

ALTER TABLE core.orders
    DROP COLUMN IF EXISTS signal_id;
"""


def upgrade() -> None:
    # F-13 resolution: dedicated, FK-enforced signal lineage column per
    # Doc 14 §10.6.5/§10.7.3, closing the correlation_id column-overloading
    # risk flagged in the Step 3.3 finding.
    op.execute(sa.text(_ADD_SIGNAL_ID))


def downgrade() -> None:
    # Doc 09 §Migration Strategy: downgrade restores the prior schema
    # shape. Any signal_id values written under this column are lost —
    # acceptable, symmetric with every other downgrade in this chain
    # (e.g. 861eb5a06b23's NUMERIC -> INTEGER truncation).
    op.execute(sa.text(_DROP_SIGNAL_ID))
