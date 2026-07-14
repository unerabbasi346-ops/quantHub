# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Domain — Doc 07 §Layers
# Schema shapes: Doc 09 §Entity Standards (market_data.assets / ohlcv_bars / ticks,
#   per the Step 1.1 Alembic migration); Doc 11 "Market Data Tick Contract"
#   (Cross-Document Data Contract Shapes) for the tick field set.
# Per Doc 00 §14.11
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class AssetRef:
    """Vendor-agnostic asset identity, used to resolve/create a market_data.assets row.

    JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged, not silently decided): Doc 11
    §4 refers to a "canonical instrument symbol per Document 11 normalization"
    but Doc 11 does not specify the normalization algorithm anywhere in the
    document. `symbol` here is the vendor-native symbol passed through
    unchanged (e.g. ccxt "BTC/USDT", yfinance "AAPL") rather than an invented
    canonical form. Revisit once Doc 11 defines the normalization rule.
    """

    symbol: str
    exchange: str
    asset_class: str
    name: str | None = None
    currency: str = "USD"
    # SPOT | PERPETUAL — migration e7a3c1f5b9d2. Distinguishes a spot instrument
    # (e.g. ccxt "BTC/USDT") from its perpetual future (ccxt "BTC/USDT:USDT")
    # for the SAME underlying. Defaults to SPOT so every existing caller/connector
    # that does not set it resolves a spot row unchanged (matches the column's
    # NOT NULL DEFAULT 'SPOT'). Ingestion stamps PERPETUAL from ccxt market
    # metadata (market['swap']) in Step 2.
    instrument_type: str = "SPOT"


@dataclass(frozen=True)
class Asset:
    """A persisted market_data.assets row — the READ counterpart to AssetRef.

    AssetRef is the vendor-agnostic identity used to RESOLVE-OR-CREATE a row
    (no id, consumed by ingestion). Asset is a row already persisted: it
    carries the surrogate `id` and `is_active`, and is what the read methods
    AssetRepository.get_by_id / list_active return.

    Added in Step 4.1 (API Foundation), the first real consumer of those two
    previously-stubbed read methods — mirroring the RawOHLCVBar (pre-persist)
    vs OHLCVBar (persisted) split already used in this module. Fields are the
    subset of market_data.assets (Step 1.1 migration) an API/read consumer
    needs; created_at/updated_at/deleted_at are intentionally omitted until a
    consumer needs them (Doc 00 §14.6 — additive, minimal).
    """

    id: UUID
    symbol: str
    exchange: str
    asset_class: str
    name: str | None
    currency: str
    is_active: bool
    # SPOT | PERPETUAL (migration e7a3c1f5b9d2). Additive with a default so the
    # Step 4.1 read path and its tests keep constructing Asset without it until
    # a consumer distinguishes spot from perpetual.
    instrument_type: str = "SPOT"


@dataclass(frozen=True)
class RawOHLCVBar:
    """Connector output prior to asset_id resolution — Doc 11 §2 Normalize stage.

    Optional fields default per the Step 1.1 migration's column defaults
    (market_data.ohlcv_bars: vwap/trade_count nullable, adjustment_factor
    DEFAULT 1.0, data_quality DEFAULT 'CLEAN') rather than an invented
    estimation rule — see connector docstrings for the specific gap.

    `volume: Decimal`, not int (Step 1.4 fix, migration fcec1b5ac8a0):
    exchange-reported volume is fractional base-asset units for crypto
    (live-observed e.g. 573.38622 BTC); an int field forced connectors to
    truncate it before it ever reached persistence, corrupting the value
    at the domain boundary regardless of what the DB column could hold.
    """

    asset: AssetRef
    interval: str
    ts: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    vwap: Decimal | None = None
    trade_count: int | None = None
    adjustment_factor: Decimal = Decimal("1.0")
    data_quality: str = "CLEAN"
    source: str = ""


@dataclass(frozen=True)
class OHLCVBar:
    """Persistence-ready OHLCV bar — market_data.ohlcv_bars (Doc 09, Step 1.1 migration,
    volume column widened to NUMERIC(28,8) by migration fcec1b5ac8a0 — Step 1.4)."""

    asset_id: UUID
    interval: str
    ts: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    vwap: Decimal | None = None
    trade_count: int | None = None
    adjustment_factor: Decimal = Decimal("1.0")
    data_quality: str = "CLEAN"
    source: str | None = None


@dataclass(frozen=True)
class RawTick:
    """Connector output prior to asset_id resolution — Doc 11 §2 Normalize stage.

    Field shapes follow Doc 11 "Market Data Tick Contract" (Cross-Document
    Data Contract Shapes) minus `tick_id`/`symbol`/`exchange`, which are
    assigned/resolved at persistence time (id generation, asset_id lookup).

    `bid_size`/`ask_size`/`last_size`/`volume`: `Decimal`, not `int` (F-1
    fix, migration 4253bf6672b9, Step 3.0) — exchange-reported sizes and
    volume are fractional base-asset units for crypto, the same reasoning
    already applied to OHLCVBar.volume (Step 1.4, migration fcec1b5ac8a0).
    An `int`-typed field forced connectors to truncate before the value
    ever reached persistence — confirmed as a live active bug in
    CCXTConnector.fetch_latest_tick's `volume` field, fixed in this step.
    """

    asset: AssetRef
    ts: datetime
    received_at: datetime
    feed_origin: str
    bid: Decimal | None = None
    ask: Decimal | None = None
    last: Decimal | None = None
    bid_size: Decimal | None = None
    ask_size: Decimal | None = None
    last_size: Decimal | None = None
    volume: Decimal | None = None
    conditions: tuple[str, ...] = field(default_factory=tuple)
    data_quality: str = "CLEAN"


@dataclass(frozen=True)
class Tick:
    """Persistence-ready tick — market_data.ticks (Doc 09, Step 1.1 migration,
    bid_size/ask_size/last_size/volume widened to NUMERIC(28,8) by migration
    4253bf6672b9 — Step 3.0, F-1)."""

    asset_id: UUID
    ts: datetime
    received_at: datetime
    feed_origin: str
    bid: Decimal | None = None
    ask: Decimal | None = None
    last: Decimal | None = None
    bid_size: Decimal | None = None
    ask_size: Decimal | None = None
    last_size: Decimal | None = None
    volume: Decimal | None = None
    conditions: tuple[str, ...] = field(default_factory=tuple)
    data_quality: str = "CLEAN"
    sequence_num: int | None = None


@dataclass(frozen=True)
class RawCorporateAction:
    """Connector output prior to asset_id resolution — Doc 11 §3 Corporate Actions Processing.

    JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged, Step 1.10): `action_type`
    is a free-form string, not an enum, matching the existing
    market_data.corporate_actions.action_type VARCHAR(32) column (Step
    1.1) rather than inventing a new type system. Values used by the
    yfinance connector (infrastructure/market_data/yfinance_connector.py):
    "DIVIDEND", "SPLIT", "REVERSE_SPLIT". Doc 11 §3 also lists Symbol
    Changes, Delistings, and Mergers as supported event types, but no
    connector implemented in Step 1.10 sources those (see connector
    docstring) — those action_type values are reserved, not yet produced.
    """

    asset: AssetRef
    action_type: str
    ex_date: date
    ratio: Decimal | None = None
    amount: Decimal | None = None
    currency: str | None = None
    record_date: date | None = None
    payment_date: date | None = None
    notes: str | None = None


@dataclass(frozen=True)
class CorporateAction:
    """Persistence-ready — market_data.corporate_actions (Doc 09, Step 1.1 migration,
    idempotency constraint added by migration 97e88a746f25 — Step 1.10)."""

    asset_id: UUID
    action_type: str
    ex_date: date
    ratio: Decimal | None = None
    amount: Decimal | None = None
    currency: str | None = None
    record_date: date | None = None
    payment_date: date | None = None
    notes: str | None = None


@dataclass(frozen=True)
class RawFundingRate:
    """Connector output prior to asset_id resolution — a periodic perpetual
    funding observation (migration e7a3c1f5b9d2, Step 2 of perpetuals work).

    Funding is the periodic cashflow between long and short holders of a
    perpetual future — Doc 14 has no funding concept of its own, so this is
    modelled as the §10.9.5 "Financing Costs" input (kept separate from
    trading P&L). Sourced from ccxt's fetch_funding_rate_history for a
    PERPETUAL instrument (`asset.instrument_type == "PERPETUAL"`); a SPOT
    instrument has no funding.

    `funding_rate` is the fractional rate applied at `funding_time` (e.g.
    Decimal("0.0001") = 0.01% per interval). `mark_price` / `next_funding_time`
    / `interval_hours` are nullable — ccxt does not always return them for
    historical funding rows.
    """

    asset: AssetRef
    funding_time: datetime
    funding_rate: Decimal
    mark_price: Decimal | None = None
    next_funding_time: datetime | None = None
    interval_hours: int | None = None
    source: str | None = None
    data_quality: str = "CLEAN"


@dataclass(frozen=True)
class FundingRate:
    """Persistence-ready funding observation — market_data.funding_rates
    (migration e7a3c1f5b9d2). The asset_id-resolved counterpart to
    RawFundingRate, mirroring the RawOHLCVBar/OHLCVBar split.

    Idempotent on funding_rates_asset_funding_time_uq (asset_id, funding_time)
    — the same idempotent-ingestion pattern as ohlcv_bars, so re-fetching a
    funding window revises rather than duplicates.
    """

    asset_id: UUID
    funding_time: datetime
    funding_rate: Decimal
    mark_price: Decimal | None = None
    next_funding_time: datetime | None = None
    interval_hours: int | None = None
    source: str | None = None
    data_quality: str = "CLEAN"


@dataclass(frozen=True)
class RawOpenInterest:
    """Connector output prior to asset_id resolution — a periodic perpetual
    open-interest observation (migration b4f8e21ac9d3).

    Open interest (total outstanding notional/contracts on a perpetual) has
    no Doc 14 section of its own — same genuine spec gap already flagged for
    RawFundingRate, hooked to the same §10.9.5 Financing Costs anchor since
    both are perpetual-only market-structure series. Sourced from ccxt's
    fetch_open_interest_history for a PERPETUAL instrument
    (`asset.instrument_type == "PERPETUAL"`); a SPOT instrument has no OI.

    `open_interest_usdt` is the notional value (ccxt's `openInterestValue`,
    USDT-denominated on a linear perp). `open_interest_contracts` (ccxt's
    `openInterestAmount`) is nullable — a future connector might not expose
    both, and never fabricated when absent.
    """

    asset: AssetRef
    ts: datetime
    open_interest_usdt: Decimal
    open_interest_contracts: Decimal | None = None
    source: str | None = None
    data_quality: str = "CLEAN"


@dataclass(frozen=True)
class OpenInterest:
    """Persistence-ready open-interest observation — market_data.open_interest
    (migration b4f8e21ac9d3). The asset_id-resolved counterpart to
    RawOpenInterest, mirroring the RawFundingRate/FundingRate split.

    Idempotent on the (asset_id, ts) PRIMARY KEY — the same idempotent-
    ingestion pattern as ohlcv_bars/funding_rates, so re-fetching an OI
    window revises rather than duplicates.
    """

    asset_id: UUID
    ts: datetime
    open_interest_usdt: Decimal
    open_interest_contracts: Decimal | None = None
    source: str | None = None
    data_quality: str = "CLEAN"
