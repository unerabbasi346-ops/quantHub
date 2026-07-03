"""analytics: add risk_limits (governed limits) and risk_assessments (pre-trade checks).

Governing specification:
Doc 15 §11.5.7 — Risk Limit Framework: portfolio-level risk limits are
  governed assets (set by risk governance, monitored continuously per
  Port-4). This migration adds their persistent home, analytics.risk_limits.
Doc 14 §10.7.5 — Order Validation: "Risk Limit Checks — Order would not
  breach position limits, exposure limits, or loss limits after execution.
  ... Rejection reason shall be recorded. Rejections shall not be silently
  swallowed." Doc 14 §Pre-Trade Risk Check API Contract: the check produces
  {authorized, rejection_reason, individual_checks, check_id,
  computation_latency_ns}, and "All check results SHALL be recorded in the
  audit trail." This migration adds analytics.risk_assessments as that
  audit home.
Doc 09 — Database Architecture §Schema Organization: analytics schema;
  §Migration Strategy: additive migration chained onto the current head
  (d1f8b6c4a7e2 is not touched).
Doc 00 §14.11: implementation cites governing document, section, and invariant.

Context (S-5, handbook/KNOWN_LIMITATIONS.md — Phase 3A scope): Step 0.6
shipped the Risk Engine skeleton with real RiskLimit / RiskLimitAssessment
entities and RiskLimitRepository / RiskAssessmentRepository interfaces, but
the Step 1.1 schema (revision c3a8f2b91e4d) created only
analytics.risk_snapshots — there is NO analytics.risk_limits or
analytics.risk_assessments table, so the repositories were left as stubs
(get_active_limits -> [], save -> pass). Step 3.4 (real Pre-Trade Risk)
needs both tables so the gate can load real governed limits and record a
real, auditable authorize/reject decision per order.

TWO DISTINCT ARTIFACTS (JUDGMENT CALL, Doc 00 §14.5/§14.7 — flagged, not
silently overloaded):
  - analytics.risk_limits  <- governed limits (Doc 15 §11.5.7), read by the
    pre-trade gate. Portfolio-scoped (limits are "portfolio-level" per
    §11.5.7); no natural-key uniqueness constraint (a portfolio may carry a
    modification history of same-metric limits — same append-tolerant stance
    as core.signals, F-10). The evaluator is deterministic regardless of how
    many active limits share a metric_name (it checks all of them, ordered).
  - analytics.risk_assessments  <- the Doc 14 §10.7.5 PRE-TRADE CHECK audit
    record (one row per gate evaluation of one order: authorized,
    rejection_reason, individual_checks, check_id=id, latency). This is a
    DIFFERENT artifact from the Doc 15 §11.5.13 portfolio-level RiskAssessment
    domain entity (metrics + limit_assessments + breaches), which models a
    periodic portfolio risk snapshot and remains deferred (its natural home
    is analytics.risk_snapshots, already present, revisited in Step 3.6 —
    P&L + portfolio risk metrics). The name overlap with the §11.5.13
    RiskAssessment entity is noted so a future step does not conflate the
    two; see handbook/KNOWN_LIMITATIONS.md F-14.

Append-only (P-5): risk_assessments carries no updated_at — a pre-trade
check record is an immutable audit fact. risk_limits carries updated_at
because a limit is a governed, modifiable asset (§11.5.7 limit modification).

Indexes follow the Step 1.1 analytics/core convention (per-lookup-column
btree, DESC on time columns for latest-first reads).

Revision ID: b2e4c9d17a30
Revises: d1f8b6c4a7e2
Create Date: 2026-07-03
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "b2e4c9d17a30"
down_revision: str | None = "d1f8b6c4a7e2"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

_CREATE_RISK_LIMITS = """\
CREATE TABLE analytics.risk_limits (
    id                 UUID          PRIMARY KEY DEFAULT quanthub_uuid(),
    portfolio_id       UUID          NOT NULL REFERENCES core.portfolios(id),
    metric_name        VARCHAR(64)   NOT NULL,
    limit_value        NUMERIC(28,8) NOT NULL,
    warning_threshold  NUMERIC(28,8) NOT NULL,
    is_active          BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX risk_limits_portfolio_id_idx     ON analytics.risk_limits (portfolio_id);
CREATE INDEX risk_limits_portfolio_metric_idx ON analytics.risk_limits (portfolio_id, metric_name);
"""

_CREATE_RISK_ASSESSMENTS = """\
CREATE TABLE analytics.risk_assessments (
    id                      UUID          PRIMARY KEY DEFAULT quanthub_uuid(),
    order_id                UUID          NOT NULL REFERENCES core.orders(id),
    portfolio_id            UUID          NOT NULL REFERENCES core.portfolios(id),
    authorized              BOOLEAN       NOT NULL,
    rejection_reason        VARCHAR(256),
    individual_checks       JSONB         NOT NULL DEFAULT '[]',
    computation_latency_ns  BIGINT        NOT NULL,
    assessed_at             TIMESTAMPTZ   NOT NULL,
    created_at              TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX risk_assessments_order_id_idx          ON analytics.risk_assessments (order_id);
CREATE INDEX risk_assessments_portfolio_assessed_idx ON analytics.risk_assessments (portfolio_id, assessed_at DESC);
"""

_DROP_RISK_ASSESSMENTS = "DROP TABLE IF EXISTS analytics.risk_assessments;"
_DROP_RISK_LIMITS = "DROP TABLE IF EXISTS analytics.risk_limits;"


def upgrade() -> None:
    # Doc 15 §11.5.7 governed limits + Doc 14 §10.7.5 pre-trade check audit.
    op.execute(sa.text(_CREATE_RISK_LIMITS))
    op.execute(sa.text(_CREATE_RISK_ASSESSMENTS))


def downgrade() -> None:
    # Reverse creation order: risk_assessments has no dependents; drop it
    # first, then risk_limits. Doc 09 §Migration Strategy: downgrade restores
    # the prior schema shape (only analytics.risk_snapshots remains).
    op.execute(sa.text(_DROP_RISK_ASSESSMENTS))
    op.execute(sa.text(_DROP_RISK_LIMITS))
