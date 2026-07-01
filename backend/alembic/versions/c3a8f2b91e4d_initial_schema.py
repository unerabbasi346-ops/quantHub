"""Initial schema: 4 schemas, quanthub_uuid() function, 20 tables, 50 indexes.

Governing specification: Doc 09 — Database Architecture (QH-009 v1.0)
  §Schema Organization: 4 schemas (core, market_data, analytics, audit)
  §Entity Standards: UUID PK, TIMESTAMPTZ, soft delete, FK integrity, indexes
  §Migration Strategy: Alembic is the authoritative deployment path
  §Indexing Strategy: timestamps, FKs, symbols, strategy identifiers
  §Transactions: critical trading operations execute atomically
  §Security: no credentials, API keys, or secrets in application tables
Doc 11 §7.10: UUID v7 (RFC 9562) for all contract identifiers → quanthub_uuid()
Doc 00 §14.11: implementation cites governing document, section, and invariant
Invariants: P-2 (Immutability), P-3 (Technology Independence), P-5 (Audit Trail),
            P-13 (Deterministic State), P-14 (Security by Design),
            T-5 (Complete Trade Auditability), I-1 (Immutable Records),
            D-9 (Zero-Trust Data Security), D-10 (Data Classification),
            Port-3 (Deterministic Portfolio State), Port-4 (Continuous Risk Monitoring)

Corresponds to: configs/schema.sql (design reference — not executed directly)
schema.sql header: "Production deployment: managed exclusively via Alembic migrations"

Revision ID: c3a8f2b91e4d
Revises: (none — initial migration)
Create Date: 2026-07-02
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "c3a8f2b91e4d"
down_revision: str | None = None
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


# ---------------------------------------------------------------------------
# SQL helpers — the complete DDL is split into logical named constants so that
# failures pinpoint exactly which object failed, and future readers can
# navigate directly to the relevant section.
# ---------------------------------------------------------------------------

# Split into individual statements — psycopg2 cursor.execute() expects one statement per call
_SCHEMA_CORE       = "CREATE SCHEMA IF NOT EXISTS core"
_SCHEMA_MARKET_DATA = "CREATE SCHEMA IF NOT EXISTS market_data"
_SCHEMA_ANALYTICS  = "CREATE SCHEMA IF NOT EXISTS analytics"
_SCHEMA_AUDIT      = "CREATE SCHEMA IF NOT EXISTS audit"

# Doc 11 §7.10: UUID v7 (RFC 9562) — PLpgSQL, no extension dependency (P-3)
_QUANTHUB_UUID_FUNCTION = """\
CREATE OR REPLACE FUNCTION quanthub_uuid()
RETURNS UUID
LANGUAGE PLPGSQL
VOLATILE
AS $$
DECLARE
  v_ms    BIGINT;
  v_bytes BYTEA;
  v_hex   TEXT;
BEGIN
  v_ms    := (EXTRACT(EPOCH FROM clock_timestamp()) * 1000)::BIGINT;
  v_bytes := decode(replace(gen_random_uuid()::text, '-', ''), 'hex');
  v_bytes := set_byte(v_bytes, 0, ((v_ms >> 40) & 255)::integer);
  v_bytes := set_byte(v_bytes, 1, ((v_ms >> 32) & 255)::integer);
  v_bytes := set_byte(v_bytes, 2, ((v_ms >> 24) & 255)::integer);
  v_bytes := set_byte(v_bytes, 3, ((v_ms >> 16) & 255)::integer);
  v_bytes := set_byte(v_bytes, 4, ((v_ms >>  8) & 255)::integer);
  v_bytes := set_byte(v_bytes, 5,  (v_ms        & 255)::integer);
  v_bytes := set_byte(v_bytes, 6, (get_byte(v_bytes, 6) & x'0f'::int) | x'70'::int);
  v_bytes := set_byte(v_bytes, 8, (get_byte(v_bytes, 8) & x'3f'::int) | x'80'::int);
  v_hex   := encode(v_bytes, 'hex');
  RETURN (
    substring(v_hex,  1, 8) || '-' ||
    substring(v_hex,  9, 4) || '-' ||
    substring(v_hex, 13, 4) || '-' ||
    substring(v_hex, 17, 4) || '-' ||
    substring(v_hex, 21, 12)
  )::UUID;
END;
$$;
"""

# =============================================================================
# SCHEMA: market_data
# Doc 09 domains: Market Data, Historical OHLCV
# =============================================================================

_TABLE_MARKET_DATA_ASSETS = """\
CREATE TABLE market_data.assets (
    id              UUID        PRIMARY KEY DEFAULT quanthub_uuid(),
    symbol          VARCHAR(64) NOT NULL,
    exchange        VARCHAR(16) NOT NULL,
    asset_class     VARCHAR(32) NOT NULL,
    name            TEXT,
    currency        VARCHAR(8)  NOT NULL DEFAULT 'USD',
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ,
    CONSTRAINT assets_symbol_exchange_uq UNIQUE (symbol, exchange)
);
"""

_TABLE_MARKET_DATA_OHLCV_BARS = """\
CREATE TABLE market_data.ohlcv_bars (
    id                UUID          PRIMARY KEY DEFAULT quanthub_uuid(),
    asset_id          UUID          NOT NULL REFERENCES market_data.assets(id),
    interval          VARCHAR(16)   NOT NULL,
    ts                TIMESTAMPTZ   NOT NULL,
    open              NUMERIC(18,8) NOT NULL,
    high              NUMERIC(18,8) NOT NULL,
    low               NUMERIC(18,8) NOT NULL,
    close             NUMERIC(18,8) NOT NULL,
    volume            BIGINT        NOT NULL DEFAULT 0,
    vwap              NUMERIC(18,8),
    trade_count       INTEGER,
    adjustment_factor NUMERIC(12,8) NOT NULL DEFAULT 1.0,
    data_quality      VARCHAR(16)   NOT NULL DEFAULT 'CLEAN',
    source            VARCHAR(64),
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT ohlcv_bars_asset_interval_ts_uq UNIQUE (asset_id, interval, ts)
);
"""

_TABLE_MARKET_DATA_TICKS = """\
CREATE TABLE market_data.ticks (
    id               UUID          PRIMARY KEY DEFAULT quanthub_uuid(),
    asset_id         UUID          NOT NULL REFERENCES market_data.assets(id),
    ts               TIMESTAMPTZ   NOT NULL,
    received_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    bid              NUMERIC(18,8),
    ask              NUMERIC(18,8),
    last             NUMERIC(18,8),
    bid_size         INTEGER,
    ask_size         INTEGER,
    last_size        INTEGER,
    volume           BIGINT,
    conditions       TEXT[],
    feed_origin      VARCHAR(32)   NOT NULL,
    data_quality     VARCHAR(16)   NOT NULL DEFAULT 'CLEAN',
    sequence_num     BIGINT,
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
"""

_TABLE_MARKET_DATA_CORPORATE_ACTIONS = """\
CREATE TABLE market_data.corporate_actions (
    id              UUID          PRIMARY KEY DEFAULT quanthub_uuid(),
    asset_id        UUID          NOT NULL REFERENCES market_data.assets(id),
    action_type     VARCHAR(32)   NOT NULL,
    ex_date         DATE          NOT NULL,
    record_date     DATE,
    payment_date    DATE,
    ratio           NUMERIC(12,6),
    amount          NUMERIC(18,8),
    currency        VARCHAR(8),
    notes           TEXT,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
"""

_TABLE_MARKET_DATA_MARKET_CALENDAR = """\
CREATE TABLE market_data.market_calendar (
    id               UUID        PRIMARY KEY DEFAULT quanthub_uuid(),
    exchange         VARCHAR(16) NOT NULL,
    date             DATE        NOT NULL,
    is_trading_day   BOOLEAN     NOT NULL DEFAULT TRUE,
    open_time        TIME,
    close_time       TIME,
    early_close_time TIME,
    timezone         VARCHAR(64) NOT NULL DEFAULT 'America/New_York',
    notes            TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT market_calendar_exchange_date_uq UNIQUE (exchange, date)
);
"""

_TABLE_MARKET_DATA_FX_RATES = """\
CREATE TABLE market_data.fx_rates (
    id              UUID          PRIMARY KEY DEFAULT quanthub_uuid(),
    base_currency   VARCHAR(8)    NOT NULL,
    quote_currency  VARCHAR(8)    NOT NULL,
    rate            NUMERIC(18,8) NOT NULL,
    ts              TIMESTAMPTZ   NOT NULL,
    source          VARCHAR(64),
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT fx_rates_currencies_ts_uq UNIQUE (base_currency, quote_currency, ts)
);
"""

# =============================================================================
# SCHEMA: core
# Doc 09 domains: Orders, Executions, Positions, Portfolios, Strategies,
#                 Notifications, User Preferences
# =============================================================================

_TABLE_CORE_USERS = """\
CREATE TABLE core.users (
    id              UUID         PRIMARY KEY DEFAULT quanthub_uuid(),
    email           VARCHAR(320) NOT NULL UNIQUE,
    display_name    VARCHAR(256),
    role            VARCHAR(64)  NOT NULL DEFAULT 'analyst',
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);
"""

_TABLE_CORE_USER_PREFERENCES = """\
CREATE TABLE core.user_preferences (
    id               UUID         PRIMARY KEY DEFAULT quanthub_uuid(),
    user_id          UUID         NOT NULL REFERENCES core.users(id),
    preference_key   VARCHAR(256) NOT NULL,
    preference_value JSONB        NOT NULL,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT user_prefs_user_key_uq UNIQUE (user_id, preference_key)
);
"""

_TABLE_CORE_PORTFOLIOS = """\
CREATE TABLE core.portfolios (
    id              UUID         PRIMARY KEY DEFAULT quanthub_uuid(),
    name            VARCHAR(256) NOT NULL,
    description     TEXT,
    base_currency   VARCHAR(8)   NOT NULL DEFAULT 'USD',
    portfolio_type  VARCHAR(32)  NOT NULL DEFAULT 'LIVE',
    owner_id        UUID         REFERENCES core.users(id),
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);
"""

_TABLE_CORE_STRATEGIES = """\
CREATE TABLE core.strategies (
    id              UUID         PRIMARY KEY DEFAULT quanthub_uuid(),
    name            VARCHAR(256) NOT NULL UNIQUE,
    description     TEXT,
    version         VARCHAR(64)  NOT NULL,
    status          VARCHAR(32)  NOT NULL DEFAULT 'INACTIVE',
    config          JSONB        NOT NULL DEFAULT '{}',
    portfolio_id    UUID         REFERENCES core.portfolios(id),
    registered_by   UUID         REFERENCES core.users(id),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);
"""

_TABLE_CORE_ORDERS = """\
CREATE TABLE core.orders (
    id               UUID          PRIMARY KEY DEFAULT quanthub_uuid(),
    idempotency_key  UUID          NOT NULL UNIQUE,
    client_order_id  VARCHAR(128)  UNIQUE,
    correlation_id   UUID,
    portfolio_id     UUID          NOT NULL REFERENCES core.portfolios(id),
    strategy_id      UUID          REFERENCES core.strategies(id),
    asset_id         UUID          NOT NULL REFERENCES market_data.assets(id),
    order_type       VARCHAR(32)   NOT NULL,
    side             VARCHAR(16)   NOT NULL,
    quantity         INTEGER       NOT NULL,
    limit_price      NUMERIC(18,8),
    stop_price       NUMERIC(18,8),
    time_in_force    VARCHAR(8)    NOT NULL DEFAULT 'DAY',
    status           VARCHAR(32)   NOT NULL DEFAULT 'CREATED',
    filled_quantity  INTEGER       NOT NULL DEFAULT 0,
    average_price    NUMERIC(18,8),
    broker_order_id  VARCHAR(256),
    venue            VARCHAR(16),
    submitted_at     TIMESTAMPTZ,
    filled_at        TIMESTAMPTZ,
    cancelled_at     TIMESTAMPTZ,
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
"""

_TABLE_CORE_EXECUTIONS = """\
CREATE TABLE core.executions (
    id              UUID          PRIMARY KEY DEFAULT quanthub_uuid(),
    order_id        UUID          NOT NULL REFERENCES core.orders(id),
    portfolio_id    UUID          NOT NULL REFERENCES core.portfolios(id),
    asset_id        UUID          NOT NULL REFERENCES market_data.assets(id),
    side            VARCHAR(16)   NOT NULL,
    quantity        INTEGER       NOT NULL,
    price           NUMERIC(18,8) NOT NULL,
    commission      NUMERIC(18,8) NOT NULL DEFAULT 0,
    net_amount      NUMERIC(20,4) NOT NULL,
    currency        VARCHAR(8)    NOT NULL DEFAULT 'USD',
    broker_exec_id  VARCHAR(256),
    venue           VARCHAR(16),
    executed_at     TIMESTAMPTZ   NOT NULL,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
"""

_TABLE_CORE_POSITIONS = """\
CREATE TABLE core.positions (
    id                  UUID          PRIMARY KEY DEFAULT quanthub_uuid(),
    portfolio_id        UUID          NOT NULL REFERENCES core.portfolios(id),
    asset_id            UUID          NOT NULL REFERENCES market_data.assets(id),
    quantity            INTEGER       NOT NULL DEFAULT 0,
    average_entry_price NUMERIC(18,8) NOT NULL DEFAULT 0,
    market_value        NUMERIC(20,4) NOT NULL DEFAULT 0,
    unrealized_pnl      NUMERIC(20,4) NOT NULL DEFAULT 0,
    realized_pnl_today  NUMERIC(20,4) NOT NULL DEFAULT 0,
    currency            VARCHAR(8)    NOT NULL DEFAULT 'USD',
    is_closed           BOOLEAN       NOT NULL DEFAULT FALSE,
    sequence_number     BIGINT        NOT NULL DEFAULT 0,
    last_price          NUMERIC(18,8),
    last_price_at       TIMESTAMPTZ,
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT positions_portfolio_asset_uq UNIQUE (portfolio_id, asset_id)
);
"""

_TABLE_CORE_NOTIFICATIONS = """\
CREATE TABLE core.notifications (
    id              UUID         PRIMARY KEY DEFAULT quanthub_uuid(),
    user_id         UUID         REFERENCES core.users(id),
    channel         VARCHAR(32)  NOT NULL,
    event_type      VARCHAR(128) NOT NULL,
    title           VARCHAR(512) NOT NULL,
    body            TEXT         NOT NULL,
    payload         JSONB,
    status          VARCHAR(32)  NOT NULL DEFAULT 'PENDING',
    sent_at         TIMESTAMPTZ,
    error_message   TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
"""

# =============================================================================
# SCHEMA: analytics
# Doc 09 domains: Research, Backtests, Machine Learning, Risk
# =============================================================================

_TABLE_ANALYTICS_RESEARCH_PROJECTS = """\
CREATE TABLE analytics.research_projects (
    id              UUID         PRIMARY KEY DEFAULT quanthub_uuid(),
    name            VARCHAR(256) NOT NULL,
    description     TEXT,
    hypothesis      TEXT,
    status          VARCHAR(32)  NOT NULL DEFAULT 'ACTIVE',
    owner_id        UUID         REFERENCES core.users(id),
    tags            TEXT[],
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);
"""

_TABLE_ANALYTICS_EXPERIMENTS = """\
CREATE TABLE analytics.experiments (
    id                    UUID         PRIMARY KEY DEFAULT quanthub_uuid(),
    project_id            UUID         NOT NULL REFERENCES analytics.research_projects(id),
    name                  VARCHAR(256) NOT NULL,
    description           TEXT,
    hypothesis            TEXT,
    status                VARCHAR(32)  NOT NULL DEFAULT 'DRAFT',
    config                JSONB        NOT NULL DEFAULT '{}',
    results               JSONB,
    reproducibility_hash  VARCHAR(128),
    started_at            TIMESTAMPTZ,
    completed_at          TIMESTAMPTZ,
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
"""

_TABLE_ANALYTICS_BACKTESTS = """\
CREATE TABLE analytics.backtests (
    id                   UUID          PRIMARY KEY DEFAULT quanthub_uuid(),
    strategy_id          UUID          REFERENCES core.strategies(id),
    name                 VARCHAR(256)  NOT NULL,
    description          TEXT,
    status               VARCHAR(32)   NOT NULL DEFAULT 'QUEUED',
    config               JSONB         NOT NULL,
    start_date           DATE          NOT NULL,
    end_date             DATE          NOT NULL,
    initial_capital      NUMERIC(20,4) NOT NULL,
    final_capital        NUMERIC(20,4),
    total_return         NUMERIC(12,8),
    sharpe_ratio         NUMERIC(10,6),
    max_drawdown         NUMERIC(10,6),
    trade_count          INTEGER,
    results              JSONB,
    reproducibility_hash VARCHAR(128),
    started_at           TIMESTAMPTZ,
    completed_at         TIMESTAMPTZ,
    created_by           UUID          REFERENCES core.users(id),
    created_at           TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
"""

_TABLE_ANALYTICS_ML_MODELS = """\
CREATE TABLE analytics.ml_models (
    id              UUID         PRIMARY KEY DEFAULT quanthub_uuid(),
    name            VARCHAR(256) NOT NULL,
    version         VARCHAR(64)  NOT NULL,
    status          VARCHAR(32)  NOT NULL DEFAULT 'DRAFT',
    model_type      VARCHAR(128) NOT NULL,
    risk_tier       VARCHAR(16)  NOT NULL DEFAULT 'LOW',
    framework       VARCHAR(64),
    artifact_path   TEXT,
    config          JSONB        NOT NULL DEFAULT '{}',
    metrics         JSONB,
    experiment_id   UUID         REFERENCES analytics.experiments(id),
    deployed_at     TIMESTAMPTZ,
    retired_at      TIMESTAMPTZ,
    created_by      UUID         REFERENCES core.users(id),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT ml_models_name_version_uq UNIQUE (name, version)
);
"""

_TABLE_ANALYTICS_RISK_SNAPSHOTS = """\
CREATE TABLE analytics.risk_snapshots (
    id               UUID          PRIMARY KEY DEFAULT quanthub_uuid(),
    portfolio_id     UUID          NOT NULL REFERENCES core.portfolios(id),
    snapshot_at      TIMESTAMPTZ   NOT NULL,
    var_1d_95        NUMERIC(20,4),
    var_1d_99        NUMERIC(20,4),
    cvar_1d_95       NUMERIC(20,4),
    gross_exposure   NUMERIC(20,4),
    net_exposure     NUMERIC(20,4),
    leverage         NUMERIC(10,6),
    drawdown_current NUMERIC(10,6),
    drawdown_max     NUMERIC(10,6),
    risk_metrics     JSONB         NOT NULL DEFAULT '{}',
    breaches         JSONB,
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
"""

# =============================================================================
# SCHEMA: audit
# Doc 09 domain: Audit Logs
# P-5, F-6, D-7.11.5, I-6: every governed action → immutable audit record
# =============================================================================

_TABLE_AUDIT_AUDIT_LOG = """\
CREATE TABLE audit.audit_log (
    id              UUID         PRIMARY KEY DEFAULT quanthub_uuid(),
    actor_id        UUID,
    actor_type      VARCHAR(32)  NOT NULL,
    action          VARCHAR(128) NOT NULL,
    resource_type   VARCHAR(128) NOT NULL,
    resource_id     UUID,
    state_before    JSONB,
    state_after     JSONB,
    policy_ref      TEXT,
    outcome         VARCHAR(32)  NOT NULL,
    ip_address      INET,
    session_id      VARCHAR(256),
    correlation_id  UUID,
    occurred_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
"""

# =============================================================================
# Indexes — Doc 09 §Indexing Strategy
# =============================================================================

_INDEXES_MARKET_DATA = [
    "CREATE INDEX assets_symbol_idx        ON market_data.assets (symbol);",
    "CREATE INDEX assets_exchange_idx      ON market_data.assets (exchange);",
    "CREATE INDEX assets_asset_class_idx   ON market_data.assets (asset_class);",
    "CREATE INDEX ohlcv_bars_asset_interval_ts_idx ON market_data.ohlcv_bars (asset_id, interval, ts DESC);",
    "CREATE INDEX ohlcv_bars_ts_idx        ON market_data.ohlcv_bars (ts DESC);",
    "CREATE INDEX ticks_asset_ts_idx       ON market_data.ticks (asset_id, ts DESC);",
    "CREATE INDEX ticks_feed_origin_idx    ON market_data.ticks (feed_origin);",
    "CREATE INDEX ca_asset_exdate_idx      ON market_data.corporate_actions (asset_id, ex_date);",
    "CREATE INDEX market_calendar_exchange_date_idx ON market_data.market_calendar (exchange, date);",
    "CREATE INDEX fx_rates_currencies_ts_idx ON market_data.fx_rates (base_currency, quote_currency, ts DESC);",
]

_INDEXES_CORE = [
    "CREATE INDEX users_email_idx             ON core.users (email);",
    "CREATE INDEX user_prefs_user_id_idx      ON core.user_preferences (user_id);",
    "CREATE INDEX portfolios_owner_id_idx     ON core.portfolios (owner_id);",
    "CREATE INDEX portfolios_type_idx         ON core.portfolios (portfolio_type);",
    "CREATE INDEX strategies_portfolio_id_idx ON core.strategies (portfolio_id);",
    "CREATE INDEX strategies_status_idx       ON core.strategies (status);",
    "CREATE INDEX orders_portfolio_id_idx     ON core.orders (portfolio_id);",
    "CREATE INDEX orders_strategy_id_idx      ON core.orders (strategy_id);",
    "CREATE INDEX orders_asset_id_idx         ON core.orders (asset_id);",
    "CREATE INDEX orders_status_idx           ON core.orders (status);",
    "CREATE INDEX orders_created_at_idx       ON core.orders (created_at DESC);",
    "CREATE INDEX orders_idempotency_key_idx  ON core.orders (idempotency_key);",
    "CREATE INDEX orders_client_order_id_idx  ON core.orders (client_order_id);",
    "CREATE INDEX orders_correlation_id_idx   ON core.orders (correlation_id);",
    "CREATE INDEX executions_order_id_idx     ON core.executions (order_id);",
    "CREATE INDEX executions_portfolio_id_idx ON core.executions (portfolio_id);",
    "CREATE INDEX executions_asset_id_idx     ON core.executions (asset_id);",
    "CREATE INDEX executions_executed_at_idx  ON core.executions (executed_at DESC);",
    "CREATE INDEX positions_portfolio_id_idx  ON core.positions (portfolio_id);",
    "CREATE INDEX positions_asset_id_idx      ON core.positions (asset_id);",
    "CREATE INDEX notifications_user_id_idx    ON core.notifications (user_id);",
    "CREATE INDEX notifications_event_type_idx ON core.notifications (event_type);",
    "CREATE INDEX notifications_status_idx     ON core.notifications (status);",
    "CREATE INDEX notifications_created_at_idx ON core.notifications (created_at DESC);",
]

_INDEXES_ANALYTICS = [
    "CREATE INDEX research_projects_owner_id_idx ON analytics.research_projects (owner_id);",
    "CREATE INDEX research_projects_status_idx   ON analytics.research_projects (status);",
    "CREATE INDEX experiments_project_id_idx     ON analytics.experiments (project_id);",
    "CREATE INDEX experiments_status_idx         ON analytics.experiments (status);",
    "CREATE INDEX backtests_strategy_id_idx      ON analytics.backtests (strategy_id);",
    "CREATE INDEX backtests_status_idx           ON analytics.backtests (status);",
    "CREATE INDEX backtests_created_at_idx       ON analytics.backtests (created_at DESC);",
    "CREATE INDEX ml_models_status_idx           ON analytics.ml_models (status);",
    "CREATE INDEX ml_models_risk_tier_idx        ON analytics.ml_models (risk_tier);",
    "CREATE INDEX risk_snapshots_portfolio_ts_idx ON analytics.risk_snapshots (portfolio_id, snapshot_at DESC);",
    "CREATE INDEX risk_snapshots_snapshot_at_idx  ON analytics.risk_snapshots (snapshot_at DESC);",
]

_INDEXES_AUDIT = [
    "CREATE INDEX audit_log_actor_id_idx         ON audit.audit_log (actor_id);",
    "CREATE INDEX audit_log_resource_type_id_idx ON audit.audit_log (resource_type, resource_id);",
    "CREATE INDEX audit_log_action_idx           ON audit.audit_log (action);",
    "CREATE INDEX audit_log_occurred_at_idx      ON audit.audit_log (occurred_at DESC);",
    "CREATE INDEX audit_log_correlation_id_idx   ON audit.audit_log (correlation_id);",
]

# Total indexes: 10 + 24 + 11 + 5 = 50


def upgrade() -> None:
    # 1 — Schemas (Doc 09 §Schema Organization)
    # One execute per statement — psycopg2 cursor.execute() expects a single command
    op.execute(sa.text(_SCHEMA_MARKET_DATA))
    op.execute(sa.text(_SCHEMA_CORE))
    op.execute(sa.text(_SCHEMA_ANALYTICS))
    op.execute(sa.text(_SCHEMA_AUDIT))

    # 2 — UUID v7 generator (Doc 11 §7.10, P-3)
    op.execute(sa.text(_QUANTHUB_UUID_FUNCTION))

    # 3 — market_data schema tables (dependency order: assets first)
    op.execute(sa.text(_TABLE_MARKET_DATA_ASSETS))
    op.execute(sa.text(_TABLE_MARKET_DATA_OHLCV_BARS))
    op.execute(sa.text(_TABLE_MARKET_DATA_TICKS))
    op.execute(sa.text(_TABLE_MARKET_DATA_CORPORATE_ACTIONS))
    op.execute(sa.text(_TABLE_MARKET_DATA_MARKET_CALENDAR))
    op.execute(sa.text(_TABLE_MARKET_DATA_FX_RATES))

    # 4 — core schema tables (dependency order: users → portfolios → strategies → orders)
    op.execute(sa.text(_TABLE_CORE_USERS))
    op.execute(sa.text(_TABLE_CORE_USER_PREFERENCES))
    op.execute(sa.text(_TABLE_CORE_PORTFOLIOS))
    op.execute(sa.text(_TABLE_CORE_STRATEGIES))
    op.execute(sa.text(_TABLE_CORE_ORDERS))
    op.execute(sa.text(_TABLE_CORE_EXECUTIONS))
    op.execute(sa.text(_TABLE_CORE_POSITIONS))
    op.execute(sa.text(_TABLE_CORE_NOTIFICATIONS))

    # 5 — analytics schema tables (experiments refs research_projects; ml_models refs experiments)
    op.execute(sa.text(_TABLE_ANALYTICS_RESEARCH_PROJECTS))
    op.execute(sa.text(_TABLE_ANALYTICS_EXPERIMENTS))
    op.execute(sa.text(_TABLE_ANALYTICS_BACKTESTS))
    op.execute(sa.text(_TABLE_ANALYTICS_ML_MODELS))
    op.execute(sa.text(_TABLE_ANALYTICS_RISK_SNAPSHOTS))

    # 6 — audit schema (no FK dependencies on other schemas)
    op.execute(sa.text(_TABLE_AUDIT_AUDIT_LOG))

    # 7 — Indexes (Doc 09 §Indexing Strategy)
    for ddl in (
        *_INDEXES_MARKET_DATA,
        *_INDEXES_CORE,
        *_INDEXES_ANALYTICS,
        *_INDEXES_AUDIT,
    ):
        op.execute(sa.text(ddl))


def downgrade() -> None:
    # Drop schemas in reverse FK dependency order.
    # CASCADE drops all contained tables, constraints, and indexes automatically.
    # Doc 09 §Migration Strategy: downgrade must restore database to prior state.
    op.execute(sa.text("DROP SCHEMA IF EXISTS audit CASCADE"))
    op.execute(sa.text("DROP SCHEMA IF EXISTS analytics CASCADE"))
    op.execute(sa.text("DROP SCHEMA IF EXISTS core CASCADE"))
    op.execute(sa.text("DROP SCHEMA IF EXISTS market_data CASCADE"))
    # quanthub_uuid() lives in public schema — not removed by schema CASCADE above
    op.execute(sa.text("DROP FUNCTION IF EXISTS quanthub_uuid()"))
