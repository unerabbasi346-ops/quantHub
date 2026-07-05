"""analytics: add paper_trading_sessions (governed live-market validation runs).

Governing specification:
Doc 14 §10.5 — Paper Trading Architecture: "the final pre-live validation
  gate." §10.5.3 (Paper Trading Configuration) enumerates the canonical
  session spec — session identifier, strategy reference+version, period
  (optional end; indefinite sessions permitted), instrument universe, data
  feeds, execution assumptions, risk parameters, initial capital. §10.5.9
  (Paper-to-Live Promotion Gate) gates promotion on a completed session.
  §10.5.10 (Paper Trading Artifacts) requires each session produce governed
  artifacts (trade/P&L history, comparison reports, config snapshot). This
  migration adds analytics.paper_trading_sessions as the session's home.
Doc 09 — Database Architecture §Schema Organization ("Separate schemas where
  appropriate: core, market_data, analytics, audit"): analytics schema;
  §Migration Strategy: additive migration chained onto the current head
  (b2e4c9d17a30 is not touched).
Doc 00 §14.11: implementation cites governing document, section, invariant.
Invariants: T-3 Paper-Live Parity (paper reuses the live trade path; only
  fills are simulated), P-2 (immutable promotion evidence — §10.5.9/§10.5.10).

Context (S-6/S-7/Phase 5 planning, handbook/KNOWN_LIMITATIONS.md): Phase 5
  builds paper trading as the continuous, live-market analogue of the Step
  3.7 backtest — the same Step 3.1-3.5 pipeline running against live bars as
  they arrive, rather than a single historical replay. Step 5.0 is the
  schema+repository prerequisite (migration-first, mirroring Step 3.0/S-4
  discipline); the continuous runner is 5.2, session lifecycle/artifacts +
  the F-20 daily-reset + the single-number paper-vs-backtest comparison are
  5.3, and the graduation-criteria record is 5.4.

SCHEMA PLACEMENT (JUDGMENT CALL, Doc 00 §14.5/§14.7 — flagged):
  analytics.paper_trading_sessions is the live-market SIBLING of
  analytics.backtests. Both are strategy-VALIDATION run records: a backtest
  evaluates a strategy over historical data, a paper session evaluates it
  against live markets. It is deliberately NOT in `core` — `core` holds the
  live operational trade entities (orders/executions/positions) that the
  session PRODUCES through the shared pipeline; those already exist and the
  session merely references the owning strategy/portfolio, exactly as a
  backtest does while writing its trades to core.* (F-21: the backtest wrote
  962 core.orders while its run metadata lived in analytics.backtests).

RECONCILES a pre-existing skeleton note (flagged, not silently overridden):
  domain/paper_trading/interfaces.py (Step 0.x) states "Paper trading shares
  the Order/Execution/Position schema with live trading (portfolio_type=
  'PAPER' in core.portfolios). No separate persistence table required." That
  is TRUE for the TRADE ARTIFACTS — paper orders/fills/positions do reuse
  core.* tagged portfolio_type='PAPER', preserving T-3 parity, and this
  migration adds NONE of those. It is INCOMPLETE for the SESSION-GOVERNANCE
  record: §10.5.3 config, §10.5.9 promotion gate, and §10.5.10 artifacts have
  no home in core.*, precisely as analytics.backtests provides one for a
  backtest run. This table is that home, not a duplicate of the core trade
  tables.

FIELDS INCLUDED NOW vs DEFERRED (per Step 5.3's stated needs, avoiding a
  second migration for known-imminent columns):
  - realized_pnl (session-LIFETIME, accumulates and does NOT reset) is
    distinct from core.positions.realized_pnl_today (a DAILY figure that F-20
    resets at day boundaries): a session spanning multiple days needs a
    lifetime realized figure for its §10.5.10 artifacts that survives those
    resets. This is why it is a real session column, not a positions dup.
  - unrealized_pnl is the latest mark-to-market snapshot (§10.5.7 real-time
    P&L); last_pnl_reset_at is the F-20 daily-reset bookkeeping the 5.3 runner
    reads to know when the next day-boundary reset is due; backtest_id is the
    §10.5.8 paper-vs-backtest comparison baseline (nullable — a session need
    not reference one); results JSONB holds §10.5.10 artifacts + the 5.3
    single-number comparison.
  - DEFERRED (added when their consumer exists, not speculatively): per-bar
    monitoring counters (§10.5.7 — 5.2, can live in results JSONB), dedicated
    graduation-evidence columns (§10.5.9 — 5.4; status='GRADUATED' + results
    suffice for now), and execution-assumption versioning (§10.5.6 — F-16
    simulated-fill realism stays deferred; parity means paper uses the same
    minimal Step 3.5 fill as live).

DELIBERATE DIFFERENCE from the analytics.backtests sibling: NO
  reproducibility_hash column. A backtest is deterministic (P-13, §10.3.6); a
  paper session runs against live, wall-clock-timed, non-reproducible data, so
  a replay hash would be meaningless. Flagged so its absence is not read as an
  oversight.

F-19 (flagged, not solved here): initial_capital is a caller-supplied figure
  with no backing NAV/cash ledger — the same missing authoritative-equity
  source F-19 records. A session's leverage-based figures are only as correct
  as this input; a real capital ledger remains deferred (Doc 15 §11.4).

Status is free-form VARCHAR(32) (RUNNING | STOPPED | GRADUATED), matching the
  established stance (analytics.backtests.status; Step 4.5 free-form status
  typing) — no DB enum. Indexes follow the analytics convention (per-lookup
  btree; DESC on the time column for latest-first reads), mirroring
  backtests_strategy_id_idx / _status_idx / _created_at_idx.

Revision ID: f1c8a3e94d20
Revises: b2e4c9d17a30
Create Date: 2026-07-05
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "f1c8a3e94d20"
down_revision: str | None = "b2e4c9d17a30"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

_CREATE_PAPER_TRADING_SESSIONS = """\
CREATE TABLE analytics.paper_trading_sessions (
    id                 UUID          PRIMARY KEY DEFAULT quanthub_uuid(),
    strategy_id        UUID          NOT NULL REFERENCES core.strategies(id),
    portfolio_id       UUID          NOT NULL REFERENCES core.portfolios(id),
    backtest_id        UUID          REFERENCES analytics.backtests(id),
    name               VARCHAR(256)  NOT NULL,
    description        TEXT,
    status             VARCHAR(32)   NOT NULL DEFAULT 'RUNNING',
    config             JSONB         NOT NULL DEFAULT '{}',
    initial_capital    NUMERIC(20,4) NOT NULL,
    realized_pnl       NUMERIC(28,8) NOT NULL DEFAULT 0,
    unrealized_pnl     NUMERIC(28,8) NOT NULL DEFAULT 0,
    last_pnl_reset_at  TIMESTAMPTZ,
    results            JSONB,
    started_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    ended_at           TIMESTAMPTZ,
    created_by         UUID          REFERENCES core.users(id),
    created_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX paper_trading_sessions_strategy_id_idx  ON analytics.paper_trading_sessions (strategy_id);
CREATE INDEX paper_trading_sessions_portfolio_id_idx ON analytics.paper_trading_sessions (portfolio_id);
CREATE INDEX paper_trading_sessions_status_idx       ON analytics.paper_trading_sessions (status);
CREATE INDEX paper_trading_sessions_started_at_idx   ON analytics.paper_trading_sessions (started_at DESC);
"""

_DROP_PAPER_TRADING_SESSIONS = "DROP TABLE IF EXISTS analytics.paper_trading_sessions;"


def upgrade() -> None:
    # Doc 14 §10.5.3 session config + §10.5.9 promotion gate + §10.5.10 artifacts.
    op.execute(sa.text(_CREATE_PAPER_TRADING_SESSIONS))


def downgrade() -> None:
    # analytics.paper_trading_sessions has no dependents (no table references
    # it). Doc 09 §Migration Strategy: downgrade restores the prior schema shape.
    op.execute(sa.text(_DROP_PAPER_TRADING_SESSIONS))
