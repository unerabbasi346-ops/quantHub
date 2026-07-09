# Governing specification: Doc 11 §1 — Market Data Connectors (Data Engineering)
#                          Doc 03 §Quantitative Libraries — CCXT (exchange connectivity)
# Layer: Infrastructure — Doc 07 §Layers
# Dependency rule: infrastructure implements domain interfaces — Doc 07 §Dependency Rules
# Per Doc 00 §14.11
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import aiohttp
import ccxt.async_support as ccxt

from quant_hub.domain.market_data.connectors import (
    FundingRateConnector,
    MarketDataConnector,
    infer_instrument_type,
)
from quant_hub.domain.market_data.entities import (
    AssetRef,
    RawFundingRate,
    RawOHLCVBar,
    RawTick,
)
from quant_hub.infrastructure.market_data.retry import with_retry


class CCXTConnector(MarketDataConnector, FundingRateConnector):
    """Crypto market-data adapter over CCXT — Doc 11 §1, Doc 03 §Quantitative Libraries.

    JUDGMENT CALL (flagged per Doc 00 §14.5/§14.7 — not silently decided):
    Doc 11 §1 requires connectors to perform "schema normalization" but does
    not specify the exact ccxt-field -> platform-field mapping. ccxt's
    fetch_ohlcv does not return vwap or trade_count for most exchanges, so
    those are left None here (they are nullable columns per the Step 1.1
    migration) rather than estimated. adjustment_factor and data_quality are
    left at the Doc 09 schema defaults (1.0 / "CLEAN"). Symbol normalization
    (see AssetRef docstring) is likewise unspecified by Doc 11 — the
    vendor-native ccxt symbol (e.g. "BTC/USDT") passes through unchanged.

    GAP: source health monitoring (Doc 11 §1 Responsibilities) is not
    implemented. Retry policy is implemented (Step 1.8, Doc 11 §8 — see
    RETRY below); rate-limit handling beyond ccxt's built-in
    `enableRateLimit` is still not implemented. Only public/unauthenticated
    endpoints are used — no API credentials are handled, per Doc 00 §14.9.

    RETRY (Step 1.8, Doc 11 §8 Error Recovery, scoped per S-2): both
    fetch_ohlcv and fetch_latest_tick retry on ccxt.NetworkError (the
    common base for RequestTimeout, RateLimitExceeded, ExchangeNotAvailable,
    DDoSProtection — i.e. exactly Doc 11 §8's "network errors, rate
    limits, timeouts" trigger list) with exponential backoff, bounded at
    3 attempts (infrastructure/market_data/retry.py). Non-network ccxt
    errors (BadSymbol, AuthenticationError, etc.) are not retryable —
    retrying an invalid symbol wouldn't help — and propagate immediately.

    REAL-EXECUTION FINDING (Step 1.4 — flagged, not silently patched):
    ccxt.async_support's default aiohttp session resolves DNS via aiodns
    (c-ares), which failed outright in Step 1.4's first live run
    (`aiodns.error.DNSError: Could not contact DNS servers`) even though
    the OS resolver worked fine for the same host (verified via curl and
    urllib.request during that run). This is a known class of issue with
    c-ares on Windows / sandboxed or corporate DNS setups, not specific to
    one machine. An explicit aiohttp session using aiohttp's standard
    ThreadedResolver (OS getaddrinfo, same path curl/urllib use) is passed
    in below so the connector doesn't depend on aiodns succeeding. Doc 11
    does not specify DNS/session configuration, so this is filed as a
    portability fix, not an invented requirement.
    """

    def __init__(self, exchange_id: str) -> None:
        self.source_id = exchange_id
        exchange_class = getattr(ccxt, exchange_id)
        # Passing an explicit session makes ccxt treat it as caller-owned
        # (own_session=False internally) — it will NOT close this session
        # for us, so close() below must do it explicitly.
        self._session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
        )
        self._exchange = exchange_class({"enableRateLimit": True, "session": self._session})

    async def fetch_ohlcv(
        self,
        symbol: str,
        interval: str,
        since: datetime | None = None,
        limit: int = 500,
    ) -> list[RawOHLCVBar]:
        since_ms = int(since.timestamp() * 1000) if since is not None else None

        async def _do_fetch() -> list:
            return await self._exchange.fetch_ohlcv(
                symbol, timeframe=interval, since=since_ms, limit=limit
            )

        raw_rows = await with_retry(
            _do_fetch,
            retryable=(ccxt.NetworkError,),
            context=f"CCXTConnector.fetch_ohlcv(symbol={symbol}, interval={interval})",
        )
        asset = AssetRef(
            symbol=symbol,
            exchange=self.source_id,
            asset_class="crypto",
            # SPOT vs PERPETUAL from ccxt's own unified-symbol convention
            # (":" settle suffix -> perpetual), network-free — see
            # infer_instrument_type. The owner passes e.g. "BTC/USDT" (spot)
            # or "BTC/USDT:USDT" (USDT-margined perpetual) for the same
            # underlying, which resolve to distinct assets rows (distinct
            # symbol -> distinct assets_symbol_exchange_uq key).
            instrument_type=infer_instrument_type(symbol),
        )
        return [
            RawOHLCVBar(
                asset=asset,
                interval=interval,
                ts=datetime.fromtimestamp(row[0] / 1000, tz=timezone.utc),
                open=Decimal(str(row[1])),
                high=Decimal(str(row[2])),
                low=Decimal(str(row[3])),
                close=Decimal(str(row[4])),
                # Decimal(str(...)), not int(...): ccxt's volume is a float
                # of fractional base-asset units (e.g. 573.38622 BTC) —
                # truncating to int silently discarded real trade volume.
                # Fixed Step 1.4 alongside migration fcec1b5ac8a0. str()
                # first avoids Decimal(float) binary-representation noise.
                volume=Decimal(str(row[5])) if row[5] is not None else Decimal("0"),
                source=self.source_id,
            )
            for row in raw_rows
        ]

    async def fetch_latest_tick(self, symbol: str) -> RawTick | None:
        async def _do_fetch() -> dict:
            return await self._exchange.fetch_ticker(symbol)

        ticker = await with_retry(
            _do_fetch,
            retryable=(ccxt.NetworkError,),
            context=f"CCXTConnector.fetch_latest_tick(symbol={symbol})",
        )
        if not ticker:
            return None
        asset = AssetRef(
            symbol=symbol,
            exchange=self.source_id,
            asset_class="crypto",
            # SPOT vs PERPETUAL from ccxt's own unified-symbol convention
            # (":" settle suffix -> perpetual), network-free — see
            # infer_instrument_type. The owner passes e.g. "BTC/USDT" (spot)
            # or "BTC/USDT:USDT" (USDT-margined perpetual) for the same
            # underlying, which resolve to distinct assets rows (distinct
            # symbol -> distinct assets_symbol_exchange_uq key).
            instrument_type=infer_instrument_type(symbol),
        )
        now = datetime.now(timezone.utc)
        ts_ms = ticker.get("timestamp")
        return RawTick(
            asset=asset,
            ts=datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc) if ts_ms else now,
            received_at=now,
            feed_origin=self.source_id,
            bid=_to_decimal(ticker.get("bid")),
            ask=_to_decimal(ticker.get("ask")),
            last=_to_decimal(ticker.get("last")),
            # Decimal(str(...)), not int(...): ccxt's baseVolume is a float
            # representing fractional base-asset cumulative volume, same
            # field/reasoning as fetch_ohlcv's volume above — F-1 fix,
            # migration 4253bf6672b9 (Step 3.0). int() previously
            # truncated this silently on every live tick fetch.
            volume=_to_decimal(ticker.get("baseVolume")),
        )

    async def fetch_funding_rate_history(
        self,
        symbol: str,
        since: datetime | None = None,
        limit: int = 500,
    ) -> list[RawFundingRate]:
        """Historical perpetual funding rates via ccxt.fetch_funding_rate_history.

        ccxt returns rows shaped {timestamp, datetime, symbol, fundingRate,
        info, ...}; `fundingRate` is the fractional rate applied at that
        funding time. `mark_price`, `next_funding_time`, and `interval_hours`
        are left None — ccxt's unified funding-history row does not carry them
        (they live in the venue-specific `info` blob, which Doc 11's
        normalization mandate says not to leak through unchanged). Same retry
        policy as fetch_ohlcv (ccxt.NetworkError, bounded backoff). Same
        Decimal(str(...)) conversion as volume to avoid float-repr noise.

        The symbol must be a PERPETUAL ccxt symbol (e.g. "BTC/USDT:USDT");
        instrument_type is stamped from the symbol convention, so a
        mis-passed spot symbol produces SPOT-typed RawFundingRate rows that
        the repository/strategy layer can reject — funding on a spot asset is
        meaningless (FundingRateConnector docstring).
        """
        since_ms = int(since.timestamp() * 1000) if since is not None else None

        async def _do_fetch() -> list:
            return await self._exchange.fetch_funding_rate_history(
                symbol, since=since_ms, limit=limit
            )

        raw_rows = await with_retry(
            _do_fetch,
            retryable=(ccxt.NetworkError,),
            context=f"CCXTConnector.fetch_funding_rate_history(symbol={symbol})",
        )
        asset = AssetRef(
            symbol=symbol,
            exchange=self.source_id,
            asset_class="crypto",
            instrument_type=infer_instrument_type(symbol),
        )
        rates: list[RawFundingRate] = []
        for row in raw_rows:
            ts_ms = row.get("timestamp")
            rate = row.get("fundingRate")
            # A funding row with no timestamp or no rate is unusable — skip it
            # rather than fabricate a value (Doc 11 §2 normalize: no invented data).
            if ts_ms is None or rate is None:
                continue
            rates.append(
                RawFundingRate(
                    asset=asset,
                    funding_time=datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc),
                    funding_rate=Decimal(str(rate)),
                    source=self.source_id,
                )
            )
        return rates

    async def close(self) -> None:
        """Release the underlying ccxt client's network resources.

        ccxt.close() does not close caller-supplied sessions (see __init__
        comment), so the explicit ThreadedResolver session is closed here.
        """
        await self._exchange.close()
        await self._session.close()


def _to_decimal(value: float | int | None) -> Decimal | None:
    return Decimal(str(value)) if value is not None else None
