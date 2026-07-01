-- =============================================================================
-- Quant Hub — Physical Database Schema v0.1
-- =============================================================================
-- Governing specification: Doc 09 — Database Architecture (QH-009 v1.0)
-- Canonical field types anchored to: Doc 11 §7.10 cross-domain contracts
-- Schema separation: Doc 09 §Schema Organization (core, market_data, analytics, audit)
-- Entity standards: Doc 09 §Entity Standards (PK, timestamps, soft delete, FK, indexes)
-- Invariant compliance: P-3, P-5, P-13, P-14, T-5, D-9, D-10, Port-3
-- Per Doc 00 §14.11: implementation cites governing document, section, and invariant
--
-- Production deployment: managed exclusively via Alembic migrations (Doc 09 §Migration Strategy)
-- This file is the initial design reference; do not execute directly in production.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Schema creation
-- Doc 09 §Schema Organization: "Separate schemas where appropriate"
-- ---------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS market_data;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS audit;


-- =============================================================================
-- UUID v7 generator
-- Doc 11 §7.10: all contract identifiers are UUID v7 (time-sortable, RFC 9562)
-- Invariant: P-3 (Technology Independence) — no extension dependency
-- Implementation: PLpgSQL using gen_random_bytes() (PostgreSQL 14+ built-in)
--
-- Why PLpgSQL over pg_uuidv7 extension:
--   • No CREATE EXTENSION required — compatible with all managed PostgreSQL
--     environments (RDS, AlloyDB, Supabase, Cloud SQL) without superuser grants
--   • Deployable in the same Alembic migration as schema creation
--   • gen_random_bytes() is a PostgreSQL 14+ built-in (not pgcrypto) — CSPRNG
--     randomness without any extension
--   • RFC 9562 compliant: byte-level stamping guarantees exact spec layout
--   • Centralised: switching to a future native pg_uuid_v7() requires changing
--     only this function body, not every table definition
--
-- Byte layout (RFC 9562 §5.7):
--   Bytes 0-5  : 48-bit Unix timestamp in milliseconds (big-endian)
--   Byte  6    : top nibble = 0x7 (version), lower nibble = rand_a[0..3]
--   Byte  7    : rand_a[4..11]
--   Byte  8    : top 2 bits = 0b10 (variant), lower 6 bits = rand_b[0..5]
--   Bytes 9-15 : rand_b[6..61]
-- =============================================================================
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
  v_bytes := gen_random_bytes(16);
  -- Stamp bytes 0-5 with the 48-bit timestamp (big-endian)
  v_bytes := set_byte(v_bytes, 0, (v_ms >> 40) & 255);
  v_bytes := set_byte(v_bytes, 1, (v_ms >> 32) & 255);
  v_bytes := set_byte(v_bytes, 2, (v_ms >> 24) & 255);
  v_bytes := set_byte(v_bytes, 3, (v_ms >> 16) & 255);
  v_bytes := set_byte(v_bytes, 4, (v_ms >>  8) & 255);
  v_bytes := set_byte(v_bytes, 5,  v_ms        & 255);
  -- Set version = 7 in top nibble of byte 6
  v_bytes := set_byte(v_bytes, 6, (get_byte(v_bytes, 6) & x'0f'::int) | x'70'::int);
  -- Set variant = 10xx in top 2 bits of byte 8
  v_bytes := set_byte(v_bytes, 8, (get_byte(v_bytes, 8) & x'3f'::int) | x'80'::int);
  -- Format as RFC 4122 hyphenated UUID string
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


-- =============================================================================
-- SCHEMA: market_data
-- Covers Doc 09 domains: Market Data, Historical OHLCV
-- =============================================================================

-- ---------------------------------------------------------------------------
-- market_data.assets — instrument reference data
-- ---------------------------------------------------------------------------
CREATE TABLE market_data.assets (
    id              UUID        PRIMARY KEY DEFAULT quanthub_uuid(),
    -- quanthub_uuid() emits RFC 9562 UUID v7 (time-sortable) — Doc 11 §7.10
    symbol          VARCHAR(64) NOT NULL,   -- Doc 11 canonical contract: string(64)
    exchange        VARCHAR(16) NOT NULL,   -- Doc 11 canonical contract: string(16) (MIC code)
    asset_class     VARCHAR(32) NOT NULL,   -- EQUITY, FOREX, FUTURES, CRYPTO, ETF
    name            TEXT,
    currency        VARCHAR(8)  NOT NULL DEFAULT 'USD',
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),   -- Doc 09 §Entity Standards
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),   -- Doc 09 §Entity Standards
    deleted_at      TIMESTAMPTZ,                          -- optional soft delete (Doc 09 §Entity Standards)
    CONSTRAINT assets_symbol_exchange_uq UNIQUE (symbol, exchange)
);
CREATE INDEX assets_symbol_idx       ON market_data.assets (symbol);
CREATE INDEX assets_exchange_idx     ON market_data.assets (exchange);
CREATE INDEX assets_asset_class_idx  ON market_data.assets (asset_class);
-- Doc 09 §Indexing Strategy: "index frequently queried columns, timestamps, foreign keys, symbols"


-- ---------------------------------------------------------------------------
-- market_data.ohlcv_bars — historical OHLCV
-- Doc 09 domain: Historical OHLCV
-- Doc 09 §Time-Series Data: "optimize historical market data for time-series workloads"
-- [JC-2] No partitioning applied at Phase 0. Doc 09 defers partitioning to
--        "future versions if scale demands it." Partition by (asset_id, interval, month)
--        when row counts warrant it.
-- ---------------------------------------------------------------------------
CREATE TABLE market_data.ohlcv_bars (
    id                UUID         PRIMARY KEY DEFAULT quanthub_uuid(),
    asset_id          UUID         NOT NULL REFERENCES market_data.assets(id),
    interval          VARCHAR(16)  NOT NULL,        -- 1m, 5m, 15m, 1h, 4h, 1d, 1w
    ts                TIMESTAMPTZ  NOT NULL,         -- bar open timestamp UTC
    open              NUMERIC(18,8) NOT NULL,        -- Doc 11 §contract: decimal(18,8)
    high              NUMERIC(18,8) NOT NULL,
    low               NUMERIC(18,8) NOT NULL,
    close             NUMERIC(18,8) NOT NULL,
    volume            BIGINT        NOT NULL DEFAULT 0,
    vwap              NUMERIC(18,8),
    trade_count       INTEGER,
    adjustment_factor NUMERIC(12,8) NOT NULL DEFAULT 1.0,
    data_quality      VARCHAR(16)   NOT NULL DEFAULT 'CLEAN',
    -- quality enum: CLEAN, ADJUSTED, ESTIMATED, CORRECTED (Doc 11 Tick contract)
    source            VARCHAR(64),                   -- Doc 11: feed_origin string(32) equivalent
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT ohlcv_bars_asset_interval_ts_uq UNIQUE (asset_id, interval, ts)
);
CREATE INDEX ohlcv_bars_asset_interval_ts_idx ON market_data.ohlcv_bars (asset_id, interval, ts DESC);
CREATE INDEX ohlcv_bars_ts_idx               ON market_data.ohlcv_bars (ts DESC);
-- Doc 09 §Indexing: timestamps and symbols are primary index targets


-- ---------------------------------------------------------------------------
-- market_data.ticks — real-time / raw tick data
-- Doc 09 domain: Market Data
-- [JC-3] Ticks are extremely high-volume in production. Doc 09 notes TimescaleDB
--        as a future option. At Phase 0 this is a regular table; migrate to
--        hypertable or separate store when tick volume exceeds operational threshold.
-- ---------------------------------------------------------------------------
CREATE TABLE market_data.ticks (
    id               UUID         PRIMARY KEY DEFAULT quanthub_uuid(),
    asset_id         UUID         NOT NULL REFERENCES market_data.assets(id),
    ts               TIMESTAMPTZ  NOT NULL,          -- exchange-reported, UTC microseconds (Doc 11)
    received_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(), -- platform ingestion timestamp
    bid              NUMERIC(18,8),
    ask              NUMERIC(18,8),
    last             NUMERIC(18,8),
    bid_size         INTEGER,                         -- Doc 11: integer
    ask_size         INTEGER,
    last_size        INTEGER,
    volume           BIGINT,                          -- Doc 11: integer (cumulative daily)
    conditions       TEXT[],                          -- Doc 11: list[string(8)] trade condition codes
    feed_origin      VARCHAR(32)  NOT NULL,           -- Doc 11: string(32)
    data_quality     VARCHAR(16)  NOT NULL DEFAULT 'CLEAN',
    sequence_num     BIGINT,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
    -- No updated_at or deleted_at: ticks are immutable ingestion records (I-1, P-2)
);
CREATE INDEX ticks_asset_ts_idx      ON market_data.ticks (asset_id, ts DESC);
CREATE INDEX ticks_feed_origin_idx   ON market_data.ticks (feed_origin);


-- ---------------------------------------------------------------------------
-- market_data.corporate_actions
-- Doc 09 domain: Market Data (supporting)
-- [JC-4] Not listed as a named domain in Doc 09 but is required reference data
--        for adjusted historical prices (part of Historical OHLCV domain).
-- ---------------------------------------------------------------------------
CREATE TABLE market_data.corporate_actions (
    id              UUID         PRIMARY KEY DEFAULT quanthub_uuid(),
    asset_id        UUID         NOT NULL REFERENCES market_data.assets(id),
    action_type     VARCHAR(32)  NOT NULL,    -- DIVIDEND, SPLIT, MERGER, SPINOFF
    ex_date         DATE         NOT NULL,
    record_date     DATE,
    payment_date    DATE,
    ratio           NUMERIC(12,6),            -- split ratio (e.g. 2.0 for 2-for-1)
    amount          NUMERIC(18,8),            -- dividend amount
    currency        VARCHAR(8),
    notes           TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX ca_asset_exdate_idx ON market_data.corporate_actions (asset_id, ex_date);


-- ---------------------------------------------------------------------------
-- market_data.market_calendar — exchange trading calendar
-- [JC-5] Supporting table for Historical OHLCV domain. Not a named Doc 09
--        domain but required for bar/tick time-range queries.
-- ---------------------------------------------------------------------------
CREATE TABLE market_data.market_calendar (
    id              UUID         PRIMARY KEY DEFAULT quanthub_uuid(),
    exchange        VARCHAR(16)  NOT NULL,
    date            DATE         NOT NULL,
    is_trading_day  BOOLEAN      NOT NULL DEFAULT TRUE,
    open_time       TIME,
    close_time      TIME,
    early_close_time TIME,
    timezone        VARCHAR(64)  NOT NULL DEFAULT 'America/New_York',
    notes           TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT market_calendar_exchange_date_uq UNIQUE (exchange, date)
);
CREATE INDEX market_calendar_exchange_date_idx ON market_data.market_calendar (exchange, date);


-- ---------------------------------------------------------------------------
-- market_data.fx_rates — foreign exchange rates
-- [JC-6] Not a named Doc 09 domain but required by Doc 15 §Multi-Currency Spec
--        (FX from Doc 11 Gold layer, ≤5min refresh). Placed in market_data
--        schema as it is market reference data sourced from Doc 11 Gold layer.
-- ---------------------------------------------------------------------------
CREATE TABLE market_data.fx_rates (
    id              UUID         PRIMARY KEY DEFAULT quanthub_uuid(),
    base_currency   VARCHAR(8)   NOT NULL,
    quote_currency  VARCHAR(8)   NOT NULL,
    rate            NUMERIC(18,8) NOT NULL,
    ts              TIMESTAMPTZ  NOT NULL,
    source          VARCHAR(64),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT fx_rates_currencies_ts_uq UNIQUE (base_currency, quote_currency, ts)
    -- Immutable after creation — rates are historical facts (I-1)
);
CREATE INDEX fx_rates_currencies_ts_idx ON market_data.fx_rates (base_currency, quote_currency, ts DESC);


-- =============================================================================
-- SCHEMA: core
-- Covers Doc 09 domains: Orders, Executions, Positions, Portfolios, Strategies,
--                        Notifications, User Preferences
-- [JC-7] 'users' table added as implied parent of User Preferences domain.
--        Doc 09 names "User Preferences" not "Users" but a FK-integrity parent
--        is required per Doc 09 §Entity Standards ("Foreign-key integrity").
-- =============================================================================

-- ---------------------------------------------------------------------------
-- core.users — application user identities
-- Doc 09 §Security: no credentials, API keys, or secrets in application tables
-- [JC-7] See above. No password column by design.
-- ---------------------------------------------------------------------------
CREATE TABLE core.users (
    id              UUID         PRIMARY KEY DEFAULT quanthub_uuid(),
    email           VARCHAR(320) NOT NULL UNIQUE,
    display_name    VARCHAR(256),
    role            VARCHAR(64)  NOT NULL DEFAULT 'analyst',
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    -- No password_hash, api_key, api_secret, or credential columns.
    -- D-9: every access request shall be authenticated; mechanism is Deferred
    --   Technology Decision #6 (OIDC / API key / local session — not yet resolved).
    -- Doc 09 §Security: "never store API secrets or plaintext credentials in application tables"
    -- Doc 00 §14.9: AI agents shall never access credentials
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ                           -- soft delete (Doc 09 §Entity Standards)
);
CREATE INDEX users_email_idx ON core.users (email);


-- ---------------------------------------------------------------------------
-- core.user_preferences — Doc 09 domain: User Preferences
-- ---------------------------------------------------------------------------
CREATE TABLE core.user_preferences (
    id               UUID         PRIMARY KEY DEFAULT quanthub_uuid(),
    user_id          UUID         NOT NULL REFERENCES core.users(id),
    preference_key   VARCHAR(256) NOT NULL,
    preference_value JSONB        NOT NULL,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT user_prefs_user_key_uq UNIQUE (user_id, preference_key)
);
CREATE INDEX user_prefs_user_id_idx ON core.user_preferences (user_id);


-- ---------------------------------------------------------------------------
-- core.portfolios — Doc 09 domain: Portfolios
-- ---------------------------------------------------------------------------
CREATE TABLE core.portfolios (
    id              UUID         PRIMARY KEY DEFAULT quanthub_uuid(),
    name            VARCHAR(256) NOT NULL,
    description     TEXT,
    base_currency   VARCHAR(8)   NOT NULL DEFAULT 'USD',  -- Doc 15: base currency USD
    portfolio_type  VARCHAR(32)  NOT NULL DEFAULT 'LIVE', -- LIVE, PAPER, BACKTEST
    owner_id        UUID         REFERENCES core.users(id),
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);
CREATE INDEX portfolios_owner_id_idx ON core.portfolios (owner_id);
CREATE INDEX portfolios_type_idx     ON core.portfolios (portfolio_type);
-- Doc 09 §Indexing: strategy identifiers; portfolio_type serves this role here


-- ---------------------------------------------------------------------------
-- core.strategies — Doc 09 domain: Strategies
-- P-1: platform never assumes any specific strategy. Config is opaque JSONB.
-- No strategy logic lives here — this is registration metadata only.
-- ---------------------------------------------------------------------------
CREATE TABLE core.strategies (
    id              UUID         PRIMARY KEY DEFAULT quanthub_uuid(),
    name            VARCHAR(256) NOT NULL UNIQUE,
    description     TEXT,
    version         VARCHAR(64)  NOT NULL,
    status          VARCHAR(32)  NOT NULL DEFAULT 'INACTIVE',
    -- status: INACTIVE, PAPER, LIVE, ARCHIVED
    config          JSONB        NOT NULL DEFAULT '{}',
    -- P-1: config is external strategy parameters, opaque to the platform
    portfolio_id    UUID         REFERENCES core.portfolios(id),
    registered_by   UUID         REFERENCES core.users(id),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);
CREATE INDEX strategies_portfolio_id_idx ON core.strategies (portfolio_id);
CREATE INDEX strategies_status_idx      ON core.strategies (status);
-- Doc 09 §Indexing: strategy identifiers


-- ---------------------------------------------------------------------------
-- core.orders — Doc 09 domain: Orders
-- Doc 09 §Transactions: "critical trading operations must execute atomically"
-- Doc 11 Order Lifecycle Event Contract anchors field names and types.
-- T-5: Complete Trade Auditability — no deleted_at; orders are immutable records.
-- ---------------------------------------------------------------------------
CREATE TABLE core.orders (
    id               UUID         PRIMARY KEY DEFAULT quanthub_uuid(),
    -- Doc 11 §7.10: idempotency_key is a UUID v7 generated by the strategy per
    -- unique order intent. Doc 14 §10.7.5: used by OMS for exactly-once processing;
    -- 24-hour deduplication window; new key required on order modification.
    -- This is distinct from client_order_id (see below).
    idempotency_key  UUID         NOT NULL UNIQUE,
    -- Broker-facing reconciliation reference (FIX ClOrdID equivalent).
    -- Submitted externally to the exchange; may be human-readable or broker-specific.
    -- [JC-8] Typed VARCHAR(128) to accommodate non-UUID broker reference formats.
    -- Distinct from idempotency_key: idempotency_key is platform-internal dedup;
    -- client_order_id is the external order reference for broker/exchange reconciliation.
    client_order_id  VARCHAR(128) UNIQUE,
    correlation_id   UUID,                              -- Doc 11: correlation_id for P-5 traceability
    portfolio_id     UUID         NOT NULL REFERENCES core.portfolios(id),
    strategy_id      UUID         REFERENCES core.strategies(id),
    asset_id         UUID         NOT NULL REFERENCES market_data.assets(id),
    order_type       VARCHAR(32)  NOT NULL,
    -- Doc 11: enum{MARKET,LIMIT,STOP,STOP_LIMIT,OCO,TRAILING_STOP}
    side             VARCHAR(16)  NOT NULL,
    -- Doc 11: enum{BUY,SELL,SELL_SHORT,BUY_TO_COVER}
    quantity         INTEGER      NOT NULL,             -- Doc 11: integer (lots or shares)
    limit_price      NUMERIC(18,8),                    -- Doc 11: decimal(18,8)
    stop_price       NUMERIC(18,8),
    time_in_force    VARCHAR(8)   NOT NULL DEFAULT 'DAY',
    -- Doc 11: enum{DAY,GTC,IOC,FOK,GTD}
    status           VARCHAR(32)  NOT NULL DEFAULT 'CREATED',
    -- Doc 11: enum{CREATED,VALIDATED,ROUTED,ACKNOWLEDGED,PARTIALLY_FILLED,
    --              FILLED,REJECTED,CANCELLED,CANCEL_PENDING,EXPIRED}
    filled_quantity  INTEGER      NOT NULL DEFAULT 0,  -- Doc 11: integer
    average_price    NUMERIC(18,8),                    -- Doc 11: decimal(18,8)
    broker_order_id  VARCHAR(256),
    venue            VARCHAR(16),                      -- Doc 11: exchange string(16)
    submitted_at     TIMESTAMPTZ,
    filled_at        TIMESTAMPTZ,
    cancelled_at     TIMESTAMPTZ,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
    -- No deleted_at: T-5 Complete Trade Auditability — order records are immutable
);
CREATE INDEX orders_portfolio_id_idx      ON core.orders (portfolio_id);
CREATE INDEX orders_strategy_id_idx       ON core.orders (strategy_id);
CREATE INDEX orders_asset_id_idx          ON core.orders (asset_id);
CREATE INDEX orders_status_idx            ON core.orders (status);
CREATE INDEX orders_created_at_idx        ON core.orders (created_at DESC);
CREATE INDEX orders_idempotency_key_idx   ON core.orders (idempotency_key);
CREATE INDEX orders_client_order_id_idx   ON core.orders (client_order_id);
CREATE INDEX orders_correlation_id_idx    ON core.orders (correlation_id);
-- Doc 09 §Indexing: timestamps, foreign keys, symbols, strategy identifiers all covered


-- ---------------------------------------------------------------------------
-- core.executions — Doc 09 domain: Executions
-- Doc 09 §Transactions: fills update positions atomically in same transaction
-- T-5: immutable records — no deleted_at
-- ---------------------------------------------------------------------------
CREATE TABLE core.executions (
    id              UUID         PRIMARY KEY DEFAULT quanthub_uuid(),
    order_id        UUID         NOT NULL REFERENCES core.orders(id),
    portfolio_id    UUID         NOT NULL REFERENCES core.portfolios(id),
    asset_id        UUID         NOT NULL REFERENCES market_data.assets(id),
    side            VARCHAR(16)  NOT NULL,
    quantity        INTEGER      NOT NULL,              -- Doc 11: integer
    price           NUMERIC(18,8) NOT NULL,             -- Doc 11: decimal(18,8)
    commission      NUMERIC(18,8) NOT NULL DEFAULT 0,
    net_amount      NUMERIC(20,4) NOT NULL,             -- Doc 11 Position: decimal(20,4)
    currency        VARCHAR(8)   NOT NULL DEFAULT 'USD',
    broker_exec_id  VARCHAR(256),
    venue           VARCHAR(16),
    executed_at     TIMESTAMPTZ  NOT NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
    -- No updated_at or deleted_at: immutable fill record (T-5, I-1)
);
CREATE INDEX executions_order_id_idx     ON core.executions (order_id);
CREATE INDEX executions_portfolio_id_idx ON core.executions (portfolio_id);
CREATE INDEX executions_asset_id_idx     ON core.executions (asset_id);
CREATE INDEX executions_executed_at_idx  ON core.executions (executed_at DESC);


-- ---------------------------------------------------------------------------
-- core.positions — Doc 09 domain: Positions
-- Doc 09 §Transactions: position updates must be atomic with executions
-- Doc 11 Position Update Contract anchors field names and types.
-- [JC-9] Positions table holds CURRENT state only. Historical position snapshots
--        belong in analytics.risk_snapshots (Port-3 Deterministic Portfolio State).
--        Point-in-time position reconstruction uses execution records + audit log.
-- ---------------------------------------------------------------------------
CREATE TABLE core.positions (
    id                 UUID         PRIMARY KEY DEFAULT quanthub_uuid(),
    portfolio_id       UUID         NOT NULL REFERENCES core.portfolios(id),
    asset_id           UUID         NOT NULL REFERENCES market_data.assets(id),
    quantity           INTEGER      NOT NULL DEFAULT 0,    -- Doc 11: integer, signed (long > 0)
    average_entry_price NUMERIC(18,8) NOT NULL DEFAULT 0, -- Doc 11: decimal(18,8)
    market_value       NUMERIC(20,4) NOT NULL DEFAULT 0,  -- Doc 11: decimal(20,4)
    unrealized_pnl     NUMERIC(20,4) NOT NULL DEFAULT 0,  -- Doc 11: decimal(20,4)
    realized_pnl_today NUMERIC(20,4) NOT NULL DEFAULT 0,  -- Doc 11: decimal(20,4)
    currency           VARCHAR(8)    NOT NULL DEFAULT 'USD',
    is_closed          BOOLEAN       NOT NULL DEFAULT FALSE, -- Doc 11: boolean
    sequence_number    BIGINT        NOT NULL DEFAULT 0,   -- Doc 11: monotonically increasing
    last_price         NUMERIC(18,8),
    last_price_at      TIMESTAMPTZ,
    created_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT positions_portfolio_asset_uq UNIQUE (portfolio_id, asset_id)
);
CREATE INDEX positions_portfolio_id_idx ON core.positions (portfolio_id);
CREATE INDEX positions_asset_id_idx     ON core.positions (asset_id);


-- ---------------------------------------------------------------------------
-- core.notifications — Doc 09 domain: Notifications
-- [JC-10] Placed in core schema (not analytics) as notifications are operational
--         (order fills, risk breaches) rather than derived analytical output.
-- ---------------------------------------------------------------------------
CREATE TABLE core.notifications (
    id              UUID         PRIMARY KEY DEFAULT quanthub_uuid(),
    user_id         UUID         REFERENCES core.users(id),
    channel         VARCHAR(32)  NOT NULL,
    -- Doc 10 §Notification channels: EMAIL, WEBHOOK, SMS, PUSH, DISCORD
    event_type      VARCHAR(128) NOT NULL,
    -- Doc 10 events: ORDER_FILLED, RISK_BREACH, PIPELINE_FAILED,
    --                TRAINING_COMPLETE, BACKTEST_FINISHED, DEPLOYMENT_COMPLETED
    title           VARCHAR(512) NOT NULL,
    body            TEXT         NOT NULL,
    payload         JSONB,
    status          VARCHAR(32)  NOT NULL DEFAULT 'PENDING',
    -- PENDING, SENT, DELIVERED, FAILED
    sent_at         TIMESTAMPTZ,
    error_message   TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX notifications_user_id_idx    ON core.notifications (user_id);
CREATE INDEX notifications_event_type_idx ON core.notifications (event_type);
CREATE INDEX notifications_status_idx     ON core.notifications (status);
CREATE INDEX notifications_created_at_idx ON core.notifications (created_at DESC);


-- =============================================================================
-- SCHEMA: analytics
-- Covers Doc 09 domains: Research, Backtests, Machine Learning, Risk
-- =============================================================================

-- ---------------------------------------------------------------------------
-- analytics.research_projects — Doc 09 domain: Research (parent container)
-- [JC-11] "Research" domain split into research_projects + experiments to model
--         the hierarchy implied by Doc 13 (Research Workspaces + Experiments).
--         Doc 09 names only "Research" as a single domain.
-- ---------------------------------------------------------------------------
CREATE TABLE analytics.research_projects (
    id              UUID         PRIMARY KEY DEFAULT quanthub_uuid(),
    name            VARCHAR(256) NOT NULL,
    description     TEXT,
    hypothesis      TEXT,
    status          VARCHAR(32)  NOT NULL DEFAULT 'ACTIVE',
    -- ACTIVE, COMPLETED, ARCHIVED
    owner_id        UUID         REFERENCES core.users(id),
    tags            TEXT[],
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);
CREATE INDEX research_projects_owner_id_idx ON analytics.research_projects (owner_id);
CREATE INDEX research_projects_status_idx   ON analytics.research_projects (status);


-- ---------------------------------------------------------------------------
-- analytics.experiments — Doc 09 domain: Research (experiment records)
-- R-1: reproducibility_hash captures code+data+config+env+seeds signature
-- ---------------------------------------------------------------------------
CREATE TABLE analytics.experiments (
    id                    UUID         PRIMARY KEY DEFAULT quanthub_uuid(),
    project_id            UUID         NOT NULL REFERENCES analytics.research_projects(id),
    name                  VARCHAR(256) NOT NULL,
    description           TEXT,
    hypothesis            TEXT,
    status                VARCHAR(32)  NOT NULL DEFAULT 'DRAFT',
    -- DRAFT, RUNNING, COMPLETED, FAILED
    config                JSONB        NOT NULL DEFAULT '{}',
    results               JSONB,
    reproducibility_hash  VARCHAR(128),   -- R-1: SHA-256 of code+data+config+seeds
    started_at            TIMESTAMPTZ,
    completed_at          TIMESTAMPTZ,
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX experiments_project_id_idx ON analytics.experiments (project_id);
CREATE INDEX experiments_status_idx     ON analytics.experiments (status);


-- ---------------------------------------------------------------------------
-- analytics.backtests — Doc 09 domain: Backtests
-- T-1: reproducibility_hash required for deterministic backtest replay
-- ---------------------------------------------------------------------------
CREATE TABLE analytics.backtests (
    id                   UUID         PRIMARY KEY DEFAULT quanthub_uuid(),
    strategy_id          UUID         REFERENCES core.strategies(id),
    name                 VARCHAR(256) NOT NULL,
    description          TEXT,
    status               VARCHAR(32)  NOT NULL DEFAULT 'QUEUED',
    -- QUEUED, RUNNING, SUCCEEDED, FAILED, CANCELLED
    config               JSONB        NOT NULL,
    -- capital, commission, slippage, execution_model, universe, date_range
    start_date           DATE         NOT NULL,
    end_date             DATE         NOT NULL,
    initial_capital      NUMERIC(20,4) NOT NULL,    -- Doc 11: decimal(20,4)
    final_capital        NUMERIC(20,4),
    total_return         NUMERIC(12,8),              -- fractional (e.g. 0.2341 = 23.41%)
    sharpe_ratio         NUMERIC(10,6),
    max_drawdown         NUMERIC(10,6),
    trade_count          INTEGER,
    results              JSONB,
    -- full equity curve, trade log, performance and risk metrics
    reproducibility_hash VARCHAR(128),               -- T-1: deterministic replay identifier
    started_at           TIMESTAMPTZ,
    completed_at         TIMESTAMPTZ,
    created_by           UUID         REFERENCES core.users(id),
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX backtests_strategy_id_idx ON analytics.backtests (strategy_id);
CREATE INDEX backtests_status_idx      ON analytics.backtests (status);
CREATE INDEX backtests_created_at_idx  ON analytics.backtests (created_at DESC);


-- ---------------------------------------------------------------------------
-- analytics.ml_models — Doc 09 domain: Machine Learning
-- M-3: 8-state lifecycle (status enum)
-- M-8: 4 risk tiers (risk_tier enum)
-- ---------------------------------------------------------------------------
CREATE TABLE analytics.ml_models (
    id              UUID         PRIMARY KEY DEFAULT quanthub_uuid(),
    name            VARCHAR(256) NOT NULL,
    version         VARCHAR(64)  NOT NULL,
    status          VARCHAR(32)  NOT NULL DEFAULT 'DRAFT',
    -- M-3 lifecycle: DRAFT, TRAINING, VALIDATION, STAGING, PRODUCTION,
    --                ARCHIVED, RETIRED, DESTROYED
    model_type      VARCHAR(128) NOT NULL,
    risk_tier       VARCHAR(16)  NOT NULL DEFAULT 'LOW',
    -- M-8: LOW (advisory), MEDIUM (signal gen), HIGH (portfolio), CRITICAL (autonomous)
    framework       VARCHAR(64),
    -- [JC-12] artifact_path stores the registry path, not the binary.
    --         Model binaries are never stored as table columns (Doc 09 §Performance).
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
CREATE INDEX ml_models_status_idx    ON analytics.ml_models (status);
CREATE INDEX ml_models_risk_tier_idx ON analytics.ml_models (risk_tier);


-- ---------------------------------------------------------------------------
-- analytics.risk_snapshots — Doc 09 domain: Risk
-- Port-3: deterministic portfolio state (immutable snapshots)
-- Port-4: continuous risk monitoring — snapshots are the persistence layer
-- [JC-13] Risk is a point-in-time calculation. One snapshot per portfolio per
--         computation event. No updated_at or deleted_at — snapshots are
--         immutable (Port-3, I-1).
-- ---------------------------------------------------------------------------
CREATE TABLE analytics.risk_snapshots (
    id               UUID         PRIMARY KEY DEFAULT quanthub_uuid(),
    portfolio_id     UUID         NOT NULL REFERENCES core.portfolios(id),
    snapshot_at      TIMESTAMPTZ  NOT NULL,
    var_1d_95        NUMERIC(20,4),   -- 95% 1-day VaR in base currency
    var_1d_99        NUMERIC(20,4),   -- 99% 1-day VaR
    cvar_1d_95       NUMERIC(20,4),   -- CVaR / Expected Shortfall
    gross_exposure   NUMERIC(20,4),
    net_exposure     NUMERIC(20,4),
    leverage         NUMERIC(10,6),
    drawdown_current NUMERIC(10,6),   -- fractional (e.g. 0.05 = 5%)
    drawdown_max     NUMERIC(10,6),
    risk_metrics     JSONB        NOT NULL DEFAULT '{}',
    -- full metric payload: all VaR methods, stress tests, factor exposures
    breaches         JSONB,
    -- any limit breaches at snapshot time (T-6 circuit breaker thresholds)
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
    -- Immutable: Port-3, I-1
);
CREATE INDEX risk_snapshots_portfolio_ts_idx ON analytics.risk_snapshots (portfolio_id, snapshot_at DESC);
CREATE INDEX risk_snapshots_snapshot_at_idx  ON analytics.risk_snapshots (snapshot_at DESC);


-- =============================================================================
-- SCHEMA: audit
-- Covers Doc 09 domain: Audit Logs
-- P-5: every governed action → immutable audit record
-- F-6: full auditability — complete trails enable reconstruction
-- D-7.11.5: immutable governance evidence
-- I-6: complete auditability of every governed action
-- =============================================================================

-- ---------------------------------------------------------------------------
-- audit.audit_log — Doc 09 domain: Audit Logs
-- Immutable after creation. No updated_at, no deleted_at, no ON DELETE CASCADE.
-- ---------------------------------------------------------------------------
CREATE TABLE audit.audit_log (
    id              UUID         PRIMARY KEY DEFAULT quanthub_uuid(),
    actor_id        UUID,
    -- nullable: system and agent-initiated events may have no human actor
    actor_type      VARCHAR(32)  NOT NULL,    -- USER, SYSTEM, AGENT
    action          VARCHAR(128) NOT NULL,
    -- CREATE, READ, UPDATE, DELETE, APPROVE, REJECT, PROMOTE, HALT, RESTORE
    resource_type   VARCHAR(128) NOT NULL,
    -- orders, positions, strategies, ml_models, backtests, portfolios, etc.
    resource_id     UUID,
    state_before    JSONB,                    -- P-5: state before the action
    state_after     JSONB,                    -- P-5: state after the action
    policy_ref      TEXT,
    -- invariant or decision reference, e.g. "T-5", "P-5", "D-7.12.5"
    outcome         VARCHAR(32)  NOT NULL,    -- SUCCESS, FAILURE, BLOCKED
    ip_address      INET,
    session_id      VARCHAR(256),
    correlation_id  UUID,                     -- P-5: links to the originating event
    occurred_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
    -- No updated_at, no deleted_at. Audit records are permanently immutable.
    -- Deletion requires formal authorization + irreversible process per D-7.4.4.
);
CREATE INDEX audit_log_actor_id_idx          ON audit.audit_log (actor_id);
CREATE INDEX audit_log_resource_type_id_idx  ON audit.audit_log (resource_type, resource_id);
CREATE INDEX audit_log_action_idx            ON audit.audit_log (action);
CREATE INDEX audit_log_occurred_at_idx       ON audit.audit_log (occurred_at DESC);
CREATE INDEX audit_log_correlation_id_idx    ON audit.audit_log (correlation_id);
-- Doc 09 §Indexing: timestamps and correlation identifiers are primary targets


-- =============================================================================
-- End of schema.sql
-- Production schema changes: Alembic migrations only (Doc 09 §Migration Strategy)
-- No manual production schema edits permitted (Doc 09 §Migration Strategy)
-- =============================================================================
