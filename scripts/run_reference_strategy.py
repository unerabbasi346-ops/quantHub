#!/usr/bin/env python
# Governing specification: Doc 14 §10.6.4 (Signal Generation Pipeline)
#                          Doc 04 — Repository Structure (QH-004): scripts/ = "Automation
#                            utilities"; "No business logic inside scripts/" — this script
#                            only wires already-implemented backend components together and
#                            prints results, mirroring scripts/run_ingestion.py's (Step 1.4)
#                            pattern.
# Per Doc 00 §14.11
#
# Step 2.4: live, one-shot runner proving the full vertical slice —
# Acquire (real Phase 1 ingested OHLCV, top-up ingested here for a
# guaranteed-fresh run) -> generate_signals (reference plugin) -> Validate
# + Record (Step 2.2) -> resolved against a registered strategy (Step 2.3).
# Not a test, not a mock — a real executable path.
#
# JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged): plugin registration
# (register_plugin) happens here, explicitly, in bootstrap code — not as
# an import-time side effect of importing the plugin module (see
# infrastructure/strategy_engine/plugin_registry.py's docstring for why).
#
# Usage (from repo root, with a live Postgres reachable at DATABASE_URL):
#   DATABASE_URL=postgresql+asyncpg://... python scripts/run_reference_strategy.py \
#       [--symbol BTC/USDT] [--exchange binance] [--interval 1h] \
#       [--short-window 5] [--long-window 20]
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

_BACKEND_SRC = Path(__file__).resolve().parent.parent / "backend" / "src"
sys.path.insert(0, str(_BACKEND_SRC))

from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from quant_hub.application.market_data.service import MarketDataIngestionService  # noqa: E402
from quant_hub.application.strategy_engine.engine import run_strategy_once  # noqa: E402
from quant_hub.application.strategy_engine.reference_strategies.moving_average_crossover import (  # noqa: E402
    MovingAverageCrossoverStrategy,
)
from quant_hub.application.strategy_engine.signal_recording_service import (  # noqa: E402
    SignalRecordingService,
)
from quant_hub.domain.strategy_engine.entities import StrategyRef  # noqa: E402
from quant_hub.infrastructure.database import engine  # noqa: E402
from quant_hub.infrastructure.market_data.ccxt_connector import CCXTConnector  # noqa: E402
from quant_hub.infrastructure.strategy_engine.market_data_view import (  # noqa: E402
    RepositoryBackedMarketDataView,
)
from quant_hub.infrastructure.strategy_engine.plugin_registry import register_plugin  # noqa: E402
from quant_hub.persistence.repositories.market_data import (  # noqa: E402
    SQLAlchemyAssetRepository,
    SQLAlchemyOHLCVRepository,
    SQLAlchemyTickRepository,
)
from quant_hub.persistence.repositories.strategy_engine import (  # noqa: E402
    SQLAlchemySignalRepository,
    SQLAlchemyStrategyRepository,
)

_STRATEGY_NAME = "reference-ma-crossover"


async def run(symbol: str, exchange: str, interval: str, short_window: int, long_window: int) -> None:
    register_plugin(_STRATEGY_NAME, MovingAverageCrossoverStrategy)

    connector = CCXTConnector(exchange)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            assets = SQLAlchemyAssetRepository(session)
            bars = SQLAlchemyOHLCVRepository(session)
            ticks = SQLAlchemyTickRepository(session)

            # Acquire: top up real Phase 1 ingested data so this run has
            # enough fresh history for the crossover, regardless of what
            # a previous session already persisted.
            ingestion = MarketDataIngestionService(connector=connector, assets=assets, ohlcv=bars, ticks=ticks)
            ingest_result = await ingestion.ingest_ohlcv(symbol, interval, limit=max(long_window + 5, 30))
            print(
                f"acquire: symbol={symbol} exchange={exchange} interval={interval} "
                f"fetched={ingest_result.fetched} persisted={ingest_result.persisted} "
                f"rejected={ingest_result.rejected}"
            )

            strategy_ref = StrategyRef(
                name=_STRATEGY_NAME,
                version="1.0.0",
                description="Trivial textbook MA-crossover reference plugin (Step 2.4) — proves pluggability, not a real strategy",
                config={
                    "symbol": symbol,
                    "exchange": exchange,
                    "asset_class": "crypto",
                    "interval": interval,
                    "short_window": short_window,
                    "long_window": long_window,
                },
            )

            recorded = await run_strategy_once(
                strategy_ref,
                strategies=SQLAlchemyStrategyRepository(session),
                assets=assets,
                view=RepositoryBackedMarketDataView(assets, bars, ticks),
                recorder=SignalRecordingService(SQLAlchemySignalRepository(session)),
            )
            # Repository methods never commit (Doc 07 — caller owns the
            # transaction boundary); this script is the caller.
            await session.commit()

            print(f"registered strategy: name={_STRATEGY_NAME}")
            print(f"signals generated and recorded: {len(recorded)}")
            for s in recorded:
                print(
                    f"  signal_id={s.id} strategy_id={s.strategy_id} asset_id={s.asset_id} "
                    f"value={s.value} ts={s.ts} validation_status={s.validation_status} "
                    f"metadata={dict(s.metadata)}"
                )
    finally:
        await connector.close()
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Step 2.4 reference strategy once, live.")
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument("--exchange", default="binance")
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--short-window", type=int, default=5)
    parser.add_argument("--long-window", type=int, default=20)
    args = parser.parse_args()
    asyncio.run(run(args.symbol, args.exchange, args.interval, args.short_window, args.long_window))


if __name__ == "__main__":
    main()
