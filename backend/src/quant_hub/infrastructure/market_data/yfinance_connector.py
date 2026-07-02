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

import yfinance as yf

from quant_hub.domain.market_data.connectors import MarketDataConnector
from quant_hub.domain.market_data.entities import AssetRef, RawOHLCVBar, RawTick


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

    JUDGMENT CALL — timezone handling: Doc 11 §4 requires timestamps
    normalized to UTC. yfinance's `history()` index is tz-aware in exchange-
    local time for intraday intervals but is sometimes tz-naive for daily+
    intervals; Doc 11 does not specify how to treat naive timestamps from a
    vendor. Naive timestamps are treated here as already representing UTC
    instant equivalents (attached, not converted) — a simplification flagged
    for revisit once a real timezone/calendar service (Doc 11 §4) exists.

    yfinance is synchronous; calls run via asyncio.to_thread so this adapter
    can satisfy the async MarketDataConnector contract without blocking the
    event loop.
    """

    def __init__(self) -> None:
        self.source_id = "yfinance"

    async def fetch_ohlcv(
        self,
        symbol: str,
        interval: str,
        since: datetime | None = None,
        limit: int = 500,
    ) -> list[RawOHLCVBar]:
        history = await asyncio.to_thread(self._fetch_history, symbol, interval, since)
        asset = AssetRef(symbol=symbol, exchange=self.source_id, asset_class="equity")
        rows = history.tail(limit) if limit else history
        return [
            RawOHLCVBar(
                asset=asset,
                interval=interval,
                ts=_to_utc(index),
                open=Decimal(str(row["Open"])),
                high=Decimal(str(row["High"])),
                low=Decimal(str(row["Low"])),
                close=Decimal(str(row["Close"])),
                volume=int(row["Volume"]) if row["Volume"] == row["Volume"] else 0,  # NaN guard
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
        last_price = await asyncio.to_thread(self._fetch_last_price, symbol)
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
        return yf.Ticker(symbol).fast_info.get("last_price")


def _to_utc(ts: Any) -> datetime:
    dt = ts.to_pydatetime()
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
