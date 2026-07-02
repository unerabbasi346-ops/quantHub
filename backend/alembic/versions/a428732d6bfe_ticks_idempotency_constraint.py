"""market_data.ticks idempotency: composite unique constraint (asset_id, ts, feed_origin).

Governing specification:
Doc 11 — Data Engineering & Data Pipeline Architecture
  §2 Historical Data Ingestion, Requirements: "Idempotent ingestion" — every
    ingestion pipeline (ticks included) shall be safe to retry/redeliver
    without producing duplicate records.
  Cross-Document Data Contract Shapes -> Market Data Tick Contract: defines
    the tick field set (symbol/exchange -> asset_id, timestamp -> ts,
    feed_origin) this constraint is built from.
Doc 09 — Database Architecture §Migration Strategy: Alembic is the
  authoritative deployment path; schema changes are additive migrations,
  not hand-edits to already-applied revisions.
Doc 00 §14.11: implementation cites governing document, section, and invariant.

Context (Step 1.2 follow-up item 7): market_data.ticks (Step 1.1, revision
c3a8f2b91e4d) shipped with no unique constraint, so TickRepository.save_tick
(Step 1.2, domain/market_data/interfaces.py) could not be made idempotent —
flagged as a gap in the Step 1.2 report rather than silently left
unresolved. This migration is purely additive: c3a8f2b91e4d is not
hand-edited, per Doc 09 §Migration Strategy (already-applied/accepted
revisions are forward-only artifacts).

JUDGMENT CALL (flagged per Doc 00 §14.5/§14.7 — not silently decided):
the natural key chosen is (asset_id, ts, feed_origin) — the practical
equivalent of "(asset_id, timestamp, source)" using this schema's actual
column names. There is no `source` column on market_data.ticks (`source`
only exists on ohlcv_bars); `feed_origin` is the Doc 11 Tick Contract field
that plays the equivalent role for ticks ("Document 11 feed identifier,
e.g. nyse_taq_a, cme_mdp").

KNOWN LIMITATION, not resolved by this migration: this key assumes at most
one tick per (asset, exchange-reported timestamp, feed) triple. A genuinely
high-frequency feed with sub-timestamp-resolution trade rates could produce
two distinct real ticks that collide on this key, and the second would be
rejected/dropped rather than deduplicating a true retry. A vendor-provided
monotonic per-feed sequence number would close this gap, but Doc 11 does
not mandate one, and the existing nullable `sequence_num` column is not
populated by every connector (see infrastructure/market_data/*_connector.py
from Step 1.2), so it cannot be relied on as the sole key today. This is
the strongest key available from Doc 11's contract shapes as currently
written; revisit if/when Doc 11 specifies a mandatory per-feed sequence
number.

Consequence for callers: TickRepository.save_tick implementations
(Step 1.3+) MUST perform an idempotent write (e.g. INSERT ... ON CONFLICT
(asset_id, ts, feed_origin) DO NOTHING) rather than a bare INSERT, or
legitimate retries will raise IntegrityError instead of being absorbed.

Revision ID: a428732d6bfe
Revises: c3a8f2b91e4d
Create Date: 2026-07-02
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "a428732d6bfe"
down_revision: str | None = "c3a8f2b91e4d"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

_ADD_TICKS_IDEMPOTENCY_UQ = """\
ALTER TABLE market_data.ticks
    ADD CONSTRAINT ticks_asset_ts_feed_origin_uq UNIQUE (asset_id, ts, feed_origin);
"""

_DROP_TICKS_IDEMPOTENCY_UQ = """\
ALTER TABLE market_data.ticks
    DROP CONSTRAINT IF EXISTS ticks_asset_ts_feed_origin_uq;
"""


def upgrade() -> None:
    # Doc 11 §2 Requirements: "Idempotent ingestion" — market_data.ticks
    # shipped (Step 1.1) with no natural key; this adds one so
    # TickRepository.save_tick (Step 1.2) can be implemented idempotently.
    op.execute(sa.text(_ADD_TICKS_IDEMPOTENCY_UQ))


def downgrade() -> None:
    # Doc 09 §Migration Strategy: downgrade must restore database to prior state.
    op.execute(sa.text(_DROP_TICKS_IDEMPOTENCY_UQ))
