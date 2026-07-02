#!/usr/bin/env python
# Governing specification: Doc 11 — Data Engineering (§2 Historical Data Ingestion)
#                          Doc 04 — Repository Structure (QH-004): scripts/ = "Automation
#                            utilities"; "No business logic inside scripts/" — this script
#                            only wires already-implemented backend components together and
#                            prints results; the Acquire/Persist logic itself lives in
#                            backend/src/quant_hub/application/market_data/service.py (Doc 07).
# Per Doc 00 §14.11
#
# Manual, one-shot runner for the Step 1.2/1.3 ingestion pipeline: fetches
# OHLCV bars from a real exchange via CCXTConnector and persists them via
# the Step 1.3 SQLAlchemy repositories. First real executable path through
# the ingestion system (Step 1.4) — not a test, not a mock.
#
# JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged): default symbol/exchange/
# interval/limit below are an arbitrary but small, fixed, public-endpoint
# choice for a first smoke run, since neither Doc 11 nor Doc 03 name a
# specific symbol for manual verification. All four are overridable via
# CLI flags rather than hardcoded, so this script is not a single-purpose
# throwaway.
#
# Usage (from repo root, with a live Postgres reachable at DATABASE_URL):
#   DATABASE_URL=postgresql+asyncpg://... python scripts/run_ingestion.py \
#       [--symbol BTC/USDT] [--exchange binance] [--interval 1h] [--limit 24]
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# backend/ is a separate, unpackaged src-layout project (Doc 04: scripts/
# lives at repo root, outside backend/) — bootstrap it onto sys.path rather
# than requiring callers to set PYTHONPATH themselves.
_BACKEND_SRC = Path(__file__).resolve().parent.parent / "backend" / "src"
sys.path.insert(0, str(_BACKEND_SRC))

from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from quant_hub.application.market_data.service import MarketDataIngestionService  # noqa: E402
from quant_hub.infrastructure.database import engine  # noqa: E402
from quant_hub.infrastructure.market_data.ccxt_connector import CCXTConnector  # noqa: E402
from quant_hub.persistence.repositories.market_data import (  # noqa: E402
    SQLAlchemyAssetRepository,
    SQLAlchemyOHLCVRepository,
    SQLAlchemyTickRepository,
)


async def run(symbol: str, exchange: str, interval: str, limit: int) -> None:
    connector = CCXTConnector(exchange)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            service = MarketDataIngestionService(
                connector=connector,
                assets=SQLAlchemyAssetRepository(session),
                ohlcv=SQLAlchemyOHLCVRepository(session),
                ticks=SQLAlchemyTickRepository(session),
            )
            result = await service.ingest_ohlcv(symbol, interval, limit=limit)
            # Repository methods never commit (Doc 07 — transaction ownership
            # belongs to the caller); this script is the caller.
            await session.commit()
            print(f"symbol={symbol} exchange={exchange} interval={interval} limit={limit}")
            print(f"fetched={result.fetched} persisted={result.persisted}")
    finally:
        await connector.close()
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one market-data ingestion cycle.")
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument("--exchange", default="binance")
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--limit", type=int, default=24)
    args = parser.parse_args()
    asyncio.run(run(args.symbol, args.exchange, args.interval, args.limit))


if __name__ == "__main__":
    main()
