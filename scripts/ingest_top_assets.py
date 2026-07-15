#!/usr/bin/env python
"""Bring every active asset's OHLCV history current in one pass (Hermes
data-pipeline freshness fix, live-testing follow-up). Loops
MarketDataIngestionService.ingest_ohlcv over every market_data.assets row
with is_active=TRUE, at whichever interval its existing bar history already
uses (1h for SPOT, 1d for PERPETUAL — matches what was previously
backfilled; this script tops up, it doesn't change interval granularity).

Run:  DATABASE_URL=... python scripts/ingest_top_assets.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_BACKEND_SRC = Path(__file__).resolve().parent.parent / "backend" / "src"
sys.path.insert(0, str(_BACKEND_SRC))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from quant_hub.application.market_data.service import MarketDataIngestionService  # noqa: E402
from quant_hub.infrastructure.database import engine  # noqa: E402
from quant_hub.infrastructure.market_data.ccxt_connector import CCXTConnector  # noqa: E402
from quant_hub.persistence.repositories.market_data import (  # noqa: E402
    SQLAlchemyAssetRepository,
    SQLAlchemyOHLCVRepository,
    SQLAlchemyTickRepository,
)

_INTERVAL_BY_INSTRUMENT_TYPE = {"SPOT": "1h", "PERPETUAL": "1d"}
_LIMIT = 5


async def main() -> None:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        rows = (
            await session.execute(
                text("SELECT symbol, exchange, instrument_type FROM market_data.assets WHERE is_active = TRUE ORDER BY symbol")
            )
        ).all()

    print(f"=== Ingesting {len(rows)} active assets ===\n")
    ok = failed = 0
    for symbol, exchange, instrument_type in rows:
        interval = _INTERVAL_BY_INSTRUMENT_TYPE.get(instrument_type, "1h")
        connector = CCXTConnector(exchange)
        try:
            async with AsyncSession(engine, expire_on_commit=False) as session:
                service = MarketDataIngestionService(
                    connector=connector,
                    assets=SQLAlchemyAssetRepository(session),
                    ohlcv=SQLAlchemyOHLCVRepository(session),
                    ticks=SQLAlchemyTickRepository(session),
                )
                result = await service.ingest_ohlcv(symbol, interval, limit=_LIMIT)
                await session.commit()
            print(f"  {symbol:16} {interval:3} fetched={result.fetched:3} persisted={result.persisted:3} rejected={result.rejected}")
            ok += 1
        except Exception as exc:  # noqa: BLE001 — reported per-symbol, never silently skipped
            print(f"  {symbol:16} {interval:3} FAILED: {exc}")
            failed += 1
        finally:
            await connector.close()

    print(f"\n=== {ok} succeeded, {failed} failed ===")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
