#!/usr/bin/env python
# Governing specification: Doc 14 §10.6.4 (Signal Generation Pipeline)
#                          Doc 04 — Repository Structure (QH-004): scripts/ = "Automation
#                            utilities"; "No business logic inside scripts/" — this script
#                            only wires already-implemented backend components together and
#                            prints results, mirroring scripts/run_reference_strategy.py.
# Scope: handbook/KNOWN_LIMITATIONS.md S-10 (perpetual-futures support)
# Per Doc 00 §14.11
#
# Step 4 of the perpetuals work: the live, one-shot PROOF that the whole
# perpetual data path works end to end — real ccxt funding-rate ingestion
# (market_data.funding_rates) -> read back through
# MarketDataView.latest_funding_rates -> FundingRateBasisStrategy ->
# Validate + Record a Signal (Step 2.2). The perpetual analog of
# scripts/run_reference_strategy.py (which proved the spot OHLCV path).
# Not a test, not a mock — a real executable path against a live exchange
# and a live Postgres.
#
# Usage (from repo root, with a live Postgres reachable at DATABASE_URL):
#   python scripts/run_funding_rate_strategy.py \
#       [--symbol BTC/USDT:USDT] [--exchange binance] [--window 3] [--limit 8]
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

_BACKEND_SRC = Path(__file__).resolve().parent.parent / "backend" / "src"
sys.path.insert(0, str(_BACKEND_SRC))

from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from quant_hub.application.strategy_engine.engine import run_strategy_once  # noqa: E402
from quant_hub.application.strategy_engine.reference_strategies.funding_rate_basis import (  # noqa: E402
    FundingRateBasisStrategy,
)
from quant_hub.application.strategy_engine.signal_recording_service import (  # noqa: E402
    SignalRecordingService,
)
from quant_hub.domain.market_data.entities import FundingRate  # noqa: E402
from quant_hub.domain.strategy_engine.entities import StrategyRef  # noqa: E402
from quant_hub.infrastructure.database import engine  # noqa: E402
from quant_hub.infrastructure.market_data.ccxt_connector import CCXTConnector  # noqa: E402
from quant_hub.infrastructure.strategy_engine.market_data_view import (  # noqa: E402
    RepositoryBackedMarketDataView,
)
from quant_hub.infrastructure.strategy_engine.plugin_registry import register_plugin  # noqa: E402
from quant_hub.persistence.repositories.market_data import (  # noqa: E402
    SQLAlchemyAssetRepository,
    SQLAlchemyFundingRateRepository,
    SQLAlchemyOHLCVRepository,
    SQLAlchemyTickRepository,
)
from quant_hub.persistence.repositories.strategy_engine import (  # noqa: E402
    SQLAlchemySignalRepository,
    SQLAlchemyStrategyRepository,
)

_STRATEGY_NAME = "reference-funding-basis"


async def run(symbol: str, exchange: str, window: int, limit: int) -> None:
    register_plugin(_STRATEGY_NAME, FundingRateBasisStrategy)

    connector = CCXTConnector(exchange)
    try:
        # Acquire: real funding-rate history for the perpetual instrument.
        raw_rates = await connector.fetch_funding_rate_history(symbol, limit=limit)
        print(
            f"acquire: symbol={symbol} exchange={exchange} "
            f"funding_rows_fetched={len(raw_rates)}"
        )
        if not raw_rates:
            print("no funding data returned — is this a perpetual symbol? (e.g. BTC/USDT:USDT)")
            return

        async with AsyncSession(engine, expire_on_commit=False) as session:
            assets = SQLAlchemyAssetRepository(session)
            bars = SQLAlchemyOHLCVRepository(session)
            ticks = SQLAlchemyTickRepository(session)
            funding = SQLAlchemyFundingRateRepository(session)

            # Persist: resolve-or-create the perpetual asset (instrument_type
            # PERPETUAL carried on the RawFundingRate's AssetRef), then the
            # funding rows against it.
            asset_id = await assets.upsert(raw_rates[0].asset)
            persisted = await funding.upsert_funding_rates([
                FundingRate(
                    asset_id=asset_id,
                    funding_time=r.funding_time,
                    funding_rate=r.funding_rate,
                    source=r.source,
                )
                for r in raw_rates
            ])
            print(f"persist: asset_id={asset_id} instrument_type=PERPETUAL funding_persisted={persisted}")

            strategy_ref = StrategyRef(
                name=_STRATEGY_NAME,
                version="1.0.0",
                description=(
                    "Perpetual funding-carry reference strategy — proves the "
                    "perpetual funding data path end to end, not a real strategy"
                ),
                config={
                    "symbol": symbol,
                    "exchange": exchange,
                    "asset_class": "crypto",
                    "window": window,
                },
            )

            # Generate + Validate + Record through the same run_strategy_once
            # path the spot reference strategy uses — with a funding-backed view.
            recorded = await run_strategy_once(
                strategy_ref,
                strategies=SQLAlchemyStrategyRepository(session),
                assets=assets,
                view=RepositoryBackedMarketDataView(assets, bars, ticks, funding),
                recorder=SignalRecordingService(SQLAlchemySignalRepository(session)),
            )
            await session.commit()  # this script is the transaction-boundary owner

            print(f"registered strategy: name={_STRATEGY_NAME}")
            print(f"signals generated and recorded: {len(recorded)}")
            for s in recorded:
                print(
                    f"  signal_id={s.id} asset_id={s.asset_id} value={s.value} ts={s.ts} "
                    f"validation_status={s.validation_status} metadata={dict(s.metadata)}"
                )
    finally:
        await connector.close()
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the perpetual funding-rate reference strategy once, live.")
    parser.add_argument("--symbol", default="BTC/USDT:USDT", help="ccxt PERPETUAL symbol")
    parser.add_argument("--exchange", default="binance")
    parser.add_argument("--window", type=int, default=3)
    parser.add_argument("--limit", type=int, default=8, help="funding rows to ingest")
    args = parser.parse_args()
    asyncio.run(run(args.symbol, args.exchange, args.window, args.limit))


if __name__ == "__main__":
    main()
