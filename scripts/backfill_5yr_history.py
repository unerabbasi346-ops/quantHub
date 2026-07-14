#!/usr/bin/env python
"""One-off backfill: extend OHLCV/funding history to ~5 years (2020-01-01 -> now)
for the two ACTIVE reference strategies' instruments, so their backtests can run
over Doc 14's target window instead of the few-day/1.6yr windows that existed
before (live-testing bug-fix pass, item 0).

- BTC/USDT   1h  (reference-ma-crossover)
- BTC/USDT:USDT 1d + funding rate history (reference-funding-basis)

Paginates via CCXTConnector.fetch_ohlcv/fetch_funding_rate_history using
`since` + limit=1000, advancing since to (last bar ts + 1 interval) each page,
stopping when a page returns fewer rows than requested (caught up to "now").
Idempotent — upsert on the existing (asset_id, interval, ts) / (asset_id,
funding_time) unique constraints, safe to re-run.

Run:  DATABASE_URL=... python scripts/backfill_5yr_history.py
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_BACKEND_SRC = Path(__file__).resolve().parent.parent / "backend" / "src"
sys.path.insert(0, str(_BACKEND_SRC))

from quant_hub.application.market_data.service import MarketDataIngestionService  # noqa: E402
from quant_hub.domain.market_data.entities import FundingRate  # noqa: E402
from quant_hub.infrastructure.database import AsyncSessionLocal  # noqa: E402
from quant_hub.infrastructure.market_data.ccxt_connector import CCXTConnector  # noqa: E402
from quant_hub.persistence.repositories.market_data import (  # noqa: E402
    SQLAlchemyAssetRepository,
    SQLAlchemyFundingRateRepository,
    SQLAlchemyOHLCVRepository,
    SQLAlchemyTickRepository,
)

_START = datetime(2020, 1, 1, tzinfo=timezone.utc)
_PAGE = 1000

_INTERVAL_DELTA = {"1h": timedelta(hours=1), "1d": timedelta(days=1)}


async def _backfill_ohlcv(symbol: str, interval: str) -> None:
    connector = CCXTConnector("binance")
    total_fetched = total_persisted = 0
    since = _START
    step = _INTERVAL_DELTA[interval]
    try:
        while True:
            async with AsyncSessionLocal() as session:
                assets = SQLAlchemyAssetRepository(session)
                bars = SQLAlchemyOHLCVRepository(session)
                ticks = SQLAlchemyTickRepository(session)
                ingestion = MarketDataIngestionService(
                    connector=connector, assets=assets, ohlcv=bars, ticks=ticks
                )
                result = await ingestion.ingest_ohlcv(symbol, interval, since=since, limit=_PAGE)
                await session.commit()

            total_fetched += result.fetched
            total_persisted += result.persisted
            print(
                f"  {symbol} {interval} since={since.isoformat()} "
                f"fetched={result.fetched} persisted={result.persisted} "
                f"rejected={result.rejected} acquire_failed={result.acquire_failed}"
            )
            if result.acquire_failed or result.fetched == 0:
                break

            # advance `since` past the last bar we just fetched
            next_since = since + step * result.fetched
            if next_since <= since:
                break
            since = next_since
            if since > datetime.now(timezone.utc):
                break
    finally:
        await connector.close()
    print(f"{symbol} {interval}: TOTAL fetched={total_fetched} persisted={total_persisted}\n")


async def _backfill_funding(symbol: str) -> None:
    connector = CCXTConnector("binance")
    total_persisted = 0
    since = _START
    try:
        while True:
            async with AsyncSessionLocal() as session:
                assets = SQLAlchemyAssetRepository(session)
                funding = SQLAlchemyFundingRateRepository(session)
                raw_rows = await connector.fetch_funding_rate_history(symbol, since=since, limit=_PAGE)
                if not raw_rows:
                    break
                asset_id = await assets.upsert(raw_rows[0].asset)
                rates = [
                    FundingRate(
                        asset_id=asset_id,
                        funding_time=r.funding_time,
                        funding_rate=r.funding_rate,
                    )
                    for r in raw_rows
                ]
                persisted = await funding.upsert_funding_rates(rates)
                await session.commit()

            total_persisted += persisted
            last_ts = raw_rows[-1].funding_time
            print(
                f"  {symbol} funding since={since.isoformat()} "
                f"fetched={len(raw_rows)} persisted={persisted} last_ts={last_ts.isoformat()}"
            )
            if len(raw_rows) < _PAGE:
                break
            next_since = last_ts + timedelta(seconds=1)
            if next_since <= since:
                break
            since = next_since
            if since > datetime.now(timezone.utc):
                break
    finally:
        await connector.close()
    print(f"{symbol} funding: TOTAL persisted={total_persisted}\n")


async def main() -> None:
    print("=== Backfilling BTC/USDT 1h (reference-ma-crossover) ===")
    await _backfill_ohlcv("BTC/USDT", "1h")
    print("=== Backfilling BTC/USDT:USDT 1d (reference-funding-basis) ===")
    await _backfill_ohlcv("BTC/USDT:USDT", "1d")
    print("=== Backfilling BTC/USDT:USDT funding rate history ===")
    await _backfill_funding("BTC/USDT:USDT")


if __name__ == "__main__":
    asyncio.run(main())
