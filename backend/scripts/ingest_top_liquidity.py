"""One-off ingestion: pick the current top-liquidity USDT spot pairs on
Binance (queried live, not hardcoded) and ingest recent 1h bars for each via
the existing Phase 1 MarketDataService. Idempotent (upsert) — safe to re-run.

Run:  DATABASE_URL=... python scripts/ingest_top_liquidity.py [N]
"""
from __future__ import annotations

import asyncio
import sys

import aiohttp
import ccxt.async_support as ccxt

from quant_hub.infrastructure.database import AsyncSessionLocal
from quant_hub.infrastructure.market_data.ccxt_connector import CCXTConnector
from quant_hub.application.market_data.service import MarketDataIngestionService
from quant_hub.persistence.repositories.market_data import (
    SQLAlchemyAssetRepository,
    SQLAlchemyOHLCVRepository,
    SQLAlchemyTickRepository,
)

TARGET_COUNT = int(sys.argv[1]) if len(sys.argv) > 1 else 13
INTERVAL = "1h"
BARS = 120

# Leveraged tokens and fiat-pegged stablecoins are liquid but useless as
# tradable strategy universe members / correlation inputs, so exclude them.
LEVERAGED_SUFFIXES = ("UP", "DOWN", "BULL", "BEAR")
STABLE_BASES = {"DAI", "BUSD", "EUR", "USD", "EURI", "AEUR"}


def is_stablecoin(base: str) -> bool:
    # Any USD-pegged token (USDC, FDUSD, TUSD, USDP, USD1, RLUSD, USDD, ...)
    # trades ~1.0 vs USDT — useless as a correlation input — so drop anything
    # whose ticker carries "USD", plus the explicit non-USD-named stables.
    return "USD" in base or base in STABLE_BASES


def is_leveraged(base: str) -> bool:
    return base.endswith(LEVERAGED_SUFFIXES) or any(t in base for t in ("3L", "3S", "5L", "5S"))


async def select_top_pairs(n: int) -> list[str]:
    # Explicit ThreadedResolver session — the default aiodns resolver fails on
    # this host (see CCXTConnector docstring); reuse the same portability fix.
    session = aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
    )
    exchange = ccxt.binance({"enableRateLimit": True, "session": session})
    try:
        await exchange.load_markets()
        tickers = await exchange.fetch_tickers()
    finally:
        await exchange.close()
        await session.close()

    candidates: list[tuple[str, float]] = []
    for symbol, t in tickers.items():
        m = exchange.markets.get(symbol)
        if not m or not m.get("spot") or not m.get("active"):
            continue
        if m.get("quote") != "USDT":
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
    print(f"Selected {len(top)} pairs by 24h quote volume:")
    for sym, qv in top:
        print(f"  {sym:14s} quoteVol={qv:,.0f} USDT")
    return [s for s, _ in top]


async def main() -> None:
    symbols = await select_top_pairs(TARGET_COUNT)

    connector = CCXTConnector("binance")
    total_persisted = 0
    try:
        async with AsyncSessionLocal() as session:
            service = MarketDataIngestionService(
                connector=connector,
                assets=SQLAlchemyAssetRepository(session),
                ohlcv=SQLAlchemyOHLCVRepository(session),
                ticks=SQLAlchemyTickRepository(session),
            )
            for sym in symbols:
                res = await service.ingest_ohlcv(sym, INTERVAL, since=None, limit=BARS)
                total_persisted += res.persisted
                print(f"  {sym:14s} fetched={res.fetched} persisted={res.persisted} rejected={res.rejected}")
            await session.commit()
    finally:
        await connector.close()

    print(f"\nDone. {len(symbols)} assets, {total_persisted} bars persisted.")


if __name__ == "__main__":
    asyncio.run(main())
