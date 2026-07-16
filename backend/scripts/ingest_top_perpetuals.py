"""One-off ingestion: expand to the top-20 liquid USDT-margined perpetual
pairs on Binance (queried live, not hardcoded). For every pair not already
registered as a PERPETUAL asset, ingest 5 years of 1h bars, funding-rate
history, and open-interest history via the existing real connectors/repos.

Same pattern as scripts/ingest_top_liquidity.py (spot) and
scripts/ingest_open_interest.py — real CCXTConnector, real repositories,
idempotent (safe to re-run — ON CONFLICT upsert throughout).

OHLCV/funding history are paginated forward from `since` in
CCXTConnector-sized batches (ccxt/Binance cap ~1000 candles per call) until
caught up to now. Open-interest history is NOT backfillable 5 years back —
Binance's OI-history endpoint only retains ~30 days (see
ingest_open_interest.py docstring) — so new assets get the same
most-recent-N OI window as everything else, not a fabricated longer one.

Run:  DATABASE_URL=... python scripts/ingest_top_perpetuals.py [N]
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone

import aiohttp
import ccxt.async_support as ccxt
from sqlalchemy import text

from quant_hub.domain.market_data.entities import FundingRate, OpenInterest
from quant_hub.infrastructure.database import AsyncSessionLocal
from quant_hub.infrastructure.market_data.ccxt_connector import CCXTConnector
from quant_hub.application.market_data.service import MarketDataIngestionService
from quant_hub.persistence.repositories.market_data import (
    SQLAlchemyAssetRepository,
    SQLAlchemyFundingRateRepository,
    SQLAlchemyOHLCVRepository,
    SQLAlchemyOpenInterestRepository,
    SQLAlchemyTickRepository,
)

TARGET_COUNT = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1] != "--symbol" else 20
INTERVAL = "1h"
BARS_PER_CALL = 1000
SINCE = datetime(2020, 1, 1, tzinfo=timezone.utc)
FUNDING_LIMIT_PER_CALL = 1000
OI_LIMIT = 500

# Same filter as ingest_top_liquidity.py — leveraged tokens and fiat-pegged
# stablecoins are liquid but useless as tradable strategy universe members.
LEVERAGED_SUFFIXES = ("UP", "DOWN", "BULL", "BEAR")
STABLE_BASES = {"DAI", "BUSD", "EUR", "USD", "EURI", "AEUR"}


def is_stablecoin(base: str) -> bool:
    return "USD" in base or base in STABLE_BASES


def is_leveraged(base: str) -> bool:
    return base.endswith(LEVERAGED_SUFFIXES) or any(t in base for t in ("3L", "3S", "5L", "5S"))


async def select_top_perp_pairs(n: int) -> list[str]:
    # Explicit ThreadedResolver session — the default aiodns resolver fails on
    # this host (see CCXTConnector docstring); reuse the same portability fix.
    session = aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
    )
    exchange = ccxt.binance({"enableRateLimit": True, "session": session})
    try:
        await exchange.load_markets()
        tickers = await exchange.fetch_tickers(params={"type": "future"})
    finally:
        await exchange.close()
        await session.close()

    candidates: list[tuple[str, float]] = []
    for symbol, t in tickers.items():
        m = exchange.markets.get(symbol)
        # USDT-margined perpetual swap only — no coin-margined, no dated futures.
        if not m or not m.get("swap") or not m.get("linear") or not m.get("active"):
            continue
        if m.get("quote") != "USDT":
            continue
        # Binance also lists "TRADIFI_PERPETUAL" contracts (tokenized
        # equities/commodities — SNDK, XAU, SOXL, ...) on the same USDT-M
        # futures venue. contractType distinguishes real crypto perpetuals
        # (info.contractType == "PERPETUAL") from those — excluded here since
        # "top liquid USDT perp pairs" means the crypto trading universe.
        if m.get("info", {}).get("contractType") != "PERPETUAL":
            continue
        base = m.get("base", "")
        if is_leveraged(base) or is_stablecoin(base):
            continue
        qv = t.get("quoteVolume")
        if qv is None:
            continue
        candidates.append((symbol, float(qv)))

    candidates.sort(key=lambda x: x[1], reverse=True)
    top = candidates[:n]
    print(f"Selected {len(top)} perpetual pairs by 24h quote volume:")
    for sym, qv in top:
        print(f"  {sym:16s} quoteVol={qv:,.0f} USDT")
    return [s for s, _ in top]


CALL_TIMEOUT = 30  # seconds — a single network call must never hang the whole run.


async def ingest_bars_5y(service: MarketDataIngestionService, session, symbol: str) -> int:
    # Commit after every batch (not once at the end of 5 years of history) —
    # ~44 batches/asset previously accumulated inside one open transaction,
    # each upsert using a per-row SAVEPOINT (thousands of them uncommitted at
    # once), which visibly degraded to a multi-minute stall partway through a
    # run. Small, bounded transactions per batch instead.
    cursor = SINCE
    total = 0
    while True:
        try:
            res = await asyncio.wait_for(
                service.ingest_ohlcv(symbol, INTERVAL, since=cursor, limit=BARS_PER_CALL), timeout=CALL_TIMEOUT
            )
        except asyncio.TimeoutError:
            print(f"    TIMEOUT fetching bars at cursor={cursor.isoformat()}, stopping early for {symbol}")
            raise
        total += res.persisted
        await session.commit()
        if res.fetched == 0:
            break
        # Advance past the last fetched bar. fetch_ohlcv doesn't return the
        # raw rows here, so re-derive the next cursor from the watermark it
        # just wrote rather than threading fetched-bar timestamps through
        # IngestionResult (keeps the existing return type untouched).
        cursor = cursor + timedelta(hours=BARS_PER_CALL if res.fetched == BARS_PER_CALL else res.fetched)
        if cursor >= datetime.now(timezone.utc):
            break
        if res.fetched < BARS_PER_CALL:
            break
    return total


async def ingest_funding_5y(connector: CCXTConnector, repo: SQLAlchemyFundingRateRepository, session, asset_id, symbol: str) -> int:
    cursor = SINCE
    total = 0
    while True:
        try:
            raw_rows = await asyncio.wait_for(
                connector.fetch_funding_rate_history(symbol, since=cursor, limit=FUNDING_LIMIT_PER_CALL), timeout=CALL_TIMEOUT
            )
        except asyncio.TimeoutError:
            print(f"    TIMEOUT fetching funding at cursor={cursor.isoformat()}, stopping early for {symbol}")
            raise
        if not raw_rows:
            break
        rates = [
            FundingRate(
                asset_id=asset_id,
                funding_time=r.funding_time,
                funding_rate=r.funding_rate,
                mark_price=r.mark_price,
                next_funding_time=r.next_funding_time,
                interval_hours=r.interval_hours,
            )
            for r in raw_rows
        ]
        total += await repo.upsert_funding_rates(rates)
        await session.commit()
        last_ts = raw_rows[-1].funding_time
        if last_ts <= cursor:
            break
        cursor = last_ts + timedelta(seconds=1)
        if cursor >= datetime.now(timezone.utc) or len(raw_rows) < FUNDING_LIMIT_PER_CALL:
            break
    return total


async def ingest_oi(connector: CCXTConnector, repo: SQLAlchemyOpenInterestRepository, asset_id, symbol: str) -> int:
    try:
        raw_rows = await asyncio.wait_for(
            connector.fetch_open_interest_history(symbol, since=None, limit=OI_LIMIT), timeout=CALL_TIMEOUT
        )
    except asyncio.TimeoutError:
        print("    TIMEOUT fetching OI, skipping")
        return 0
    rows = [
        OpenInterest(
            asset_id=asset_id,
            ts=r.ts,
            open_interest_usdt=r.open_interest_usdt,
            open_interest_contracts=r.open_interest_contracts,
            source=r.source,
            data_quality=r.data_quality,
        )
        for r in raw_rows
    ]
    return await repo.upsert_open_interest(rows)


async def ingest_one_symbol(symbol: str) -> None:
    # Fresh connector + session for exactly one symbol — invoked as its own
    # OS process (see shell driver in the module docstring) so a stuck
    # network call can be killed by `timeout` at the process level. Earlier
    # in-process asyncio.wait_for bounding proved unreliable for this: a
    # stall survived the timeout with no exception ever raised (env-specific
    # asyncio quirk, not chased further — process-level timeout sidesteps it
    # entirely and is strictly more reliable regardless of cause).
    connector = CCXTConnector("binance")
    try:
        async with AsyncSessionLocal() as session:
            asset_repo = SQLAlchemyAssetRepository(session)
            ohlcv_repo = SQLAlchemyOHLCVRepository(session)
            tick_repo = SQLAlchemyTickRepository(session)
            funding_repo = SQLAlchemyFundingRateRepository(session)
            oi_repo = SQLAlchemyOpenInterestRepository(session)
            service = MarketDataIngestionService(
                connector=connector, assets=asset_repo, ohlcv=ohlcv_repo, ticks=tick_repo,
            )

            bars = await ingest_bars_5y(service, session, symbol)
            print(f"  bars persisted:    {bars}", flush=True)

            asset_id = await asset_repo.get_by_symbol_exchange(symbol, "binance")
            if asset_id is None:
                print("  FAILED to resolve asset id after bar ingestion, skipping funding/OI", flush=True)
                return

            funding = await ingest_funding_5y(connector, funding_repo, session, asset_id, symbol)
            print(f"  funding persisted: {funding}", flush=True)

            oi = await ingest_oi(connector, oi_repo, asset_id, symbol)
            print(f"  OI persisted:      {oi} (Binance OI history caps at ~30 days)", flush=True)
            await session.commit()
    finally:
        await connector.close()


async def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--symbol":
        await ingest_one_symbol(sys.argv[2])
        return

    top_symbols = await select_top_perp_pairs(TARGET_COUNT)

    async with AsyncSessionLocal() as session:
        existing_rows = await session.execute(
            text("SELECT symbol FROM market_data.assets WHERE instrument_type = 'PERPETUAL' AND exchange = 'binance'")
        )
        existing = {row[0] for row in existing_rows.all()}

    already_existed = [s for s in top_symbols if s in existing]
    new_symbols = [s for s in top_symbols if s not in existing]

    print(f"\nAlready in DB ({len(already_existed)}): {', '.join(already_existed) or '(none)'}")
    print(f"New ({len(new_symbols)}): {', '.join(new_symbols) or '(none)'}\n")
    # Machine-readable line for the shell driver to parse — the human-facing
    # lines above stay unchanged.
    print(f"NEW_SYMBOLS={'|'.join(new_symbols)}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
