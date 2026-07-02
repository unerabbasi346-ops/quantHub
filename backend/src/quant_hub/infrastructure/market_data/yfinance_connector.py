# Governing specification: Doc 11 §1 — Market Data Connectors (Data Engineering)
#                          Doc 03 §Quantitative Libraries — yfinance
# Layer: Infrastructure — Doc 07 §Layers
# Dependency rule: infrastructure implements domain interfaces — Doc 07 §Dependency Rules
# Per Doc 00 §14.11
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import requests
import yfinance as yf

from quant_hub.domain.market_data.calendar import TimezoneCalendarService
from quant_hub.domain.market_data.connectors import MarketDataConnector
from quant_hub.domain.market_data.entities import AssetRef, RawOHLCVBar, RawTick
from quant_hub.infrastructure.market_data.calendar_service import SystemCalendarService
from quant_hub.infrastructure.market_data.retry import with_retry

# JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged): yfinance has no typed
# exception hierarchy of its own for network failures (unlike ccxt's
# NetworkError); it surfaces them as whatever its underlying HTTP client
# raises. requests.exceptions.RequestException covers the documented
# `requests`-based path; OSError is added as a broader fallback since
# yfinance 1.4.1's HTTP backend has changed across versions (curl_cffi
# alongside requests) and low-level connection/DNS/timeout failures
# commonly surface as OSError subclasses regardless of HTTP client.
_YFINANCE_RETRYABLE: tuple[type[BaseException], ...] = (requests.exceptions.RequestException, OSError)


class YFinanceConnector(MarketDataConnector):
    """Equities market-data adapter over yfinance — Doc 11 §1, Doc 03 §Quantitative Libraries.

    JUDGMENT CALL (flagged per Doc 00 §14.5/§14.7 — not silently decided):
    the same vwap/trade_count/adjustment_factor/data_quality/symbol-
    normalization gaps documented on CCXTConnector apply here — yfinance's
    `history()` does not return vwap or trade counts, so those fields stay
    None/default rather than being estimated.

    GAP — no real tick feed: yfinance's free API exposes no genuine
    bid/ask/last-trade tick stream. `fetch_latest_tick` approximates a
    "tick" from `fast_info.last_price` (a delayed quote snapshot, not a
    trade print) and marks it `data_quality="ESTIMATED"` accordingly
    (using the enum from Doc 11's "Market Data Tick Contract"). This is a
    placeholder pending selection of a real equities tick-data vendor —
    Doc 11 does not name one — and MUST NOT be treated as production
    tick-level data.

    RESOLVED, NOT A RECURRING MYSTERY (investigated across Steps 1.2, 1.7,
    and confirmed a third time on 2026-07-02 at 07:40 ET / pre-market):
    `fetch_latest_tick` previously returned None for AAPL/MSFT/SPY. Root
    cause was a genuine, deterministic bug in this connector's own code —
    NOT market hours, NOT a deprecated/rate-limited field. yfinance
    1.4.1's `FastInfo.get(key)` only checks `key in self.keys()`, and
    `FastInfo.keys()` returns `_public_keys`, which holds only camelCase
    field names (e.g. "lastPrice"); the snake_case alias "last_price" is
    never in that set, so `.get("last_price")` silently returned its
    `default=None` on every call, unconditionally. Fixed by switching to
    attribute access (`fast_info.last_price`), which goes through
    `FastInfo.__getitem__`'s broader key-resolution logic instead (see
    `_fetch_last_price` below for the full trace). Confirmed
    market-hours-independent: `fast_info.last_price` returns a real price
    (falls back through 1y history / regularMarketPrice internally) even
    with markets closed — verified live pre-market on both 2026-07-02
    11:26 UTC and again at 11:40 UTC (07:26/07:40 ET, ~2h before the 9:30
    ET open), both times returning real, non-None prices for all three
    tickers. If `fetch_latest_tick` returns None again in the future, the
    cause is something NEW — do not re-investigate this closed root cause
    from scratch.

    TIMEZONE HANDLING (Step 1.5, Doc 11 §4 — supersedes the earlier Step 1.2
    simplification): yfinance's `history()` index is tz-aware in
    exchange-local time for intraday intervals but is sometimes tz-naive
    for daily+ intervals. Naive timestamps are now correctly localized as
    exchange-local time (via TimezoneCalendarService.to_utc) rather than
    assumed to already be UTC — see
    infrastructure/market_data/calendar_service.py for the exchange ->
    timezone mapping and its flagged limitations (single default US
    timezone for all yfinance symbols; no holiday/half-day awareness).

    yfinance is synchronous; calls run via asyncio.to_thread so this adapter
    can satisfy the async MarketDataConnector contract without blocking the
    event loop.

    RETRY (Step 1.8, Doc 11 §8 Error Recovery, scoped per S-2): both
    fetch_ohlcv and fetch_latest_tick retry the to_thread call itself
    (re-dispatching to a new thread each attempt, rather than sleeping
    inside the worker thread) on network-shaped exceptions — see
    _YFINANCE_RETRYABLE above — with exponential backoff, bounded at 3
    attempts (infrastructure/market_data/retry.py).
    """

    def __init__(self, calendar: TimezoneCalendarService | None = None) -> None:
        self.source_id = "yfinance"
        self._calendar = calendar or SystemCalendarService()

    async def fetch_ohlcv(
        self,
        symbol: str,
        interval: str,
        since: datetime | None = None,
        limit: int = 500,
    ) -> list[RawOHLCVBar]:
        async def _do_fetch() -> Any:
            return await asyncio.to_thread(self._fetch_history, symbol, interval, since)

        history = await with_retry(
            _do_fetch,
            retryable=_YFINANCE_RETRYABLE,
            context=f"YFinanceConnector.fetch_ohlcv(symbol={symbol}, interval={interval})",
        )
        asset = AssetRef(symbol=symbol, exchange=self.source_id, asset_class="equity")
        rows = history.tail(limit) if limit else history
        return [
            RawOHLCVBar(
                asset=asset,
                interval=interval,
                ts=self._calendar.to_utc(index.to_pydatetime(), exchange=self.source_id),
                open=Decimal(str(row["Open"])),
                high=Decimal(str(row["High"])),
                low=Decimal(str(row["Low"])),
                close=Decimal(str(row["Close"])),
                # RawOHLCVBar.volume is Decimal (Step 1.4, migration
                # fcec1b5ac8a0 widened the column for ccxt's fractional
                # crypto volumes); equity share counts from yfinance are
                # still whole units, so this stays an integer value, just
                # carried in a Decimal to satisfy the shared field type.
                volume=(
                    Decimal(int(row["Volume"]))
                    if row["Volume"] == row["Volume"]  # NaN guard
                    else Decimal("0")
                ),
                source=self.source_id,
            )
            for index, row in rows.iterrows()
        ]

    def _fetch_history(self, symbol: str, interval: str, since: datetime | None) -> Any:
        ticker = yf.Ticker(symbol)
        if since is not None:
            return ticker.history(interval=interval, start=since, auto_adjust=False)
        return ticker.history(interval=interval, period="max", auto_adjust=False)

    async def fetch_latest_tick(self, symbol: str) -> RawTick | None:
        async def _do_fetch() -> float | None:
            return await asyncio.to_thread(self._fetch_last_price, symbol)

        last_price = await with_retry(
            _do_fetch,
            retryable=_YFINANCE_RETRYABLE,
            context=f"YFinanceConnector.fetch_latest_tick(symbol={symbol})",
        )
        if last_price is None:
            return None
        asset = AssetRef(symbol=symbol, exchange=self.source_id, asset_class="equity")
        now = datetime.now(timezone.utc)
        return RawTick(
            asset=asset,
            ts=now,
            received_at=now,
            feed_origin=self.source_id,
            last=Decimal(str(last_price)),
            data_quality="ESTIMATED",  # see class docstring: not a real trade print
        )

    def _fetch_last_price(self, symbol: str) -> float | None:
        # BUG FIX (investigated per user request after ingest_latest_tick
        # returned None for AAPL/MSFT/SPY in Steps 1.2 and 1.7): this was
        # NOT a market-hours/deprecation/rate-limit issue. Root-caused via
        # yfinance 1.4.1 source: FastInfo.get(key) only checks
        # `key in self.keys()`, and `FastInfo.keys()` returns
        # `_public_keys`, which holds only the camelCase field names
        # (e.g. "lastPrice"). The snake_case alias "last_price" is never a
        # member of `_public_keys`, so `.get("last_price")` fell through
        # to its `default=None` on every call, deterministically,
        # regardless of market hours. Attribute access (`.last_price`) and
        # bracket access (`["last_price"]`) both go through
        # `FastInfo.__getitem__`, which checks the broader `_keys` set
        # (camelCase AND snake_case) and resolves correctly — confirmed
        # live: `fast_info.get("last_price")` -> None,
        # `fast_info.last_price` -> a real price, for the same object.
        return yf.Ticker(symbol).fast_info.last_price
