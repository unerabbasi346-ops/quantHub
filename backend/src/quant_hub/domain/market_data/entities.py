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
