"""market_data.corporate_actions idempotency: composite unique constraint (asset_id, action_type, ex_date).

Governing specification:
Doc 11 — Data Engineering
  §2 Historical Data Ingestion, Requirements: "Idempotent ingestion" —
    the same requirement already applied to assets/ohlcv_bars/ticks
    (Step 1.1/1.2/1.3) applies equally to corporate actions; there is no
    reason this table should be the exception.
  §3 Corporate Actions Processing, Rules: "Adjustments are versioned.
    Original raw values remain preserved." — an idempotency key lets
    re-ingestion revise a corporate action record (e.g. a dividend amount
    finalized closer to payment date) without creating duplicate rows,
    while leaving market_data.ohlcv_bars entirely untouched (Step 1.10
    does not write to ohlcv_bars at all, which is how "raw values remain
    preserved" is actually satisfied here — see the Step 1.10 service).
Doc 09 — Database Architecture §Migration Strategy: additive migration
  chained onto the existing revision history, not a hand-edit of an
  already-applied revision.
Doc 00 §14.11: implementation cites governing document, section, invariant.

Context (Step 1.10): market_data.corporate_actions shipped (Step 1.1,
revision c3a8f2b91e4d) with no unique constraint — the exact same gap
ticks had before migration a428732d6bfe (Step 1.2 follow-up, item 7).
Rather than waiting to be asked twice, this migration proactively closes
the same gap for corporate_actions before any repository code writes to
it, following that precedent.

JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged, not silently decided): the
natural key chosen is (asset_id, action_type, ex_date) — one action of a
given type per asset per ex-date. Doc 11 §3 does not specify a natural
key. KNOWN LIMITATION: this would collide if an issuer legitimately posts
two distinct actions of the SAME type on the SAME ex-date (e.g. a special
dividend and a regular dividend both ex-dated the same day) — the second
would revise the first via ON CONFLICT DO UPDATE rather than being stored
as a separate row. Doc 11 does not provide a field that would
disambiguate this case (no per-action sequence/identifier), so this is
the strongest key available from the current schema; revisit if Doc 11 or
a real data source ever surfaces same-day same-type multi-action cases.

Revision ID: 97e88a746f25
Revises: fcec1b5ac8a0
Create Date: 2026-07-02
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "97e88a746f25"
down_revision: str | None = "fcec1b5ac8a0"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

_ADD_CORPORATE_ACTIONS_IDEMPOTENCY_UQ = """\
ALTER TABLE market_data.corporate_actions
    ADD CONSTRAINT corporate_actions_asset_type_exdate_uq UNIQUE (asset_id, action_type, ex_date);
"""

_DROP_CORPORATE_ACTIONS_IDEMPOTENCY_UQ = """\
ALTER TABLE market_data.corporate_actions
    DROP CONSTRAINT IF EXISTS corporate_actions_asset_type_exdate_uq;
"""


def upgrade() -> None:
    # Doc 11 §2 Requirements: "Idempotent ingestion" — corporate_actions
    # shipped (Step 1.1) with no natural key; this adds one before Step
    # 1.10's repository/connector code writes to the table.
    op.execute(sa.text(_ADD_CORPORATE_ACTIONS_IDEMPOTENCY_UQ))


def downgrade() -> None:
    # Doc 09 §Migration Strategy: downgrade restores the prior schema shape.
    op.execute(sa.text(_DROP_CORPORATE_ACTIONS_IDEMPOTENCY_UQ))
