"""core.signals: immutable Signal-recording table for the Strategy Plugin Interface.

Governing specification:
Doc 14 — Trading Infrastructure §10.6.4 Signal Generation Pipeline:
  "Signal Recording — Every generated signal recorded as immutable event
  per P-5 with timestamp, values, and validation status." Also §10.7.3
  Order Model: an Order carries a "Signal Reference — Lineage to the
  originating signal", confirming Signal is a persisted, referenceable
  artifact distinct from (and upstream of) an Order.
Doc 09 — Database Architecture §Migration Strategy: Alembic is the
  authoritative deployment path; additive migration chained onto the
  current head (97e88a746f25), not a hand-edit of an already-applied
  revision.
Invariants: P-5 (Complete Audit Trail / immutability), T-5 (Complete
  Trade Auditability — "Signal — Trading signal generated per Section
  10.6.4. Signal recorded with values, timestamp, and validation status",
  Doc 14 §Trade Lifecycle), P-1 / T-2 (strategy-emitted `value`/`metadata`
  stored opaquely, never interpreted by platform code — see column notes).
Doc 00 §14.11: implementation cites governing document, section, and invariant.

Context (Step 2.2, Phase 2 — Strategy Plugin Interface, following Step
2.1's accepted Strategy/Signal domain contract, domain/strategy_engine/
entities.py + strategy.py): persists the Signal shape proposed in Step
2.1, plus signal_id (this table's `id`), `strategy_id`, and
`validation_status` — all three explicitly STAMPED BY THE PLATFORM, never
supplied by the strategy plugin itself (Step 2.1 design: a plugin cannot
self-attribute or self-certify its own output).

SCHEMA PLACEMENT (JUDGMENT CALL, flagged per Doc 00 §14.5/§14.7): placed
in the `core` schema, not `market_data`. The Step 1.1 initial migration's
own section comment groups `core` as "Orders, Executions, Positions,
Portfolios, Strategies, Notifications" — the trade-lifecycle domain
(Doc 14 §Trade Lifecycle lists Signal as the first trade-lifecycle
state, immediately before Order Created). A signal is conceptually
adjacent to core.strategies/core.orders, not to market_data's raw
ingested feed data. Not stated explicitly by Doc 09 (which predates this
table), so flagged rather than silently assumed.

COLUMN NOTES:
  - `value` NUMERIC(18,8): reuses the platform's existing price-column
    precision (market_data.ohlcv_bars.open/high/low/close use the same
    NUMERIC(18,8)) rather than inventing a new precision — Doc 00 §14.6
    (don't redefine an existing platform concept where an existing one
    fits). Step 2.1 already establishes `value` as a signed, [-1, 1]
    bounded conviction score (see domain/strategy_engine/validation.py,
    this same step, for where that bound is enforced).
  - `metadata` JSONB NOT NULL DEFAULT '{}': strategy-opaque per P-1/T-2,
    same storage pattern as `core.strategies.config` — the platform
    persists it verbatim for the P-5 audit event and never inspects it.
  - No `updated_at`, no `deleted_at`: deliberately absent. P-5 immutable
    event + this step's explicit "no update path" requirement — mirrors
    `market_data.ticks` (Step 1.1), the codebase's other append-only,
    event-shaped table, which likewise has no `updated_at`/`deleted_at`.
  - No idempotency/uniqueness constraint on (strategy_id, asset_id, ts):
    JUDGMENT CALL, flagged as an OPEN GAP, not silently resolved. Doc 11
    §2's ingestion tables (bars/ticks) carry an explicit "idempotent
    ingestion" requirement because they consume an unreliable external
    network feed subject to retries (resolved by migration a428732d6bfe
    for ticks). Doc 14 §10.6.4 states no equivalent idempotency
    requirement for internally-computed signals, and no signal-generating
    service exists yet to observe real retry behavior against (that is
    Step 2.4, a reference strategy). Revisit — most likely by adding a
    uniqueness constraint or a de-duplication rule at the recording
    service layer — once a real signal-generation service exists and its
    retry/re-invocation behavior can be observed, mirroring how the ticks
    idempotency gap was resolved only after Step 1.2 surfaced it as a
    concrete problem rather than being speculatively designed for upfront.

Revision ID: 7c7482e4e00a
Revises: 97e88a746f25
Create Date: 2026-07-02
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "7c7482e4e00a"
down_revision: str | None = "97e88a746f25"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

_TABLE_CORE_SIGNALS = """\
CREATE TABLE core.signals (
    id                 UUID          PRIMARY KEY DEFAULT quanthub_uuid(),
    strategy_id        UUID          NOT NULL REFERENCES core.strategies(id),
    asset_id           UUID          NOT NULL REFERENCES market_data.assets(id),
    value              NUMERIC(18,8) NOT NULL,
    ts                 TIMESTAMPTZ   NOT NULL,
    validation_status  VARCHAR(16)   NOT NULL,
    metadata           JSONB         NOT NULL DEFAULT '{}',
    created_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
"""

_DROP_TABLE_CORE_SIGNALS = "DROP TABLE IF EXISTS core.signals;"

_INDEXES = [
    "CREATE INDEX signals_strategy_asset_ts_idx ON core.signals (strategy_id, asset_id, ts DESC);",
    "CREATE INDEX signals_ts_idx               ON core.signals (ts DESC);",
    "CREATE INDEX signals_validation_status_idx ON core.signals (validation_status);",
]

_DROP_INDEXES = [
    "DROP INDEX IF EXISTS core.signals_strategy_asset_ts_idx;",
    "DROP INDEX IF EXISTS core.signals_ts_idx;",
    "DROP INDEX IF EXISTS core.signals_validation_status_idx;",
]


def upgrade() -> None:
    # Doc 14 §10.6.4 Signal Recording; T-5 Trade Lifecycle "Signal" stage.
    op.execute(sa.text(_TABLE_CORE_SIGNALS))
    for ddl in _INDEXES:
        op.execute(sa.text(ddl))


def downgrade() -> None:
    # Doc 09 §Migration Strategy: downgrade must restore database to prior state.
    for ddl in _DROP_INDEXES:
        op.execute(sa.text(ddl))
    op.execute(sa.text(_DROP_TABLE_CORE_SIGNALS))
