"""Ingest perpetual open-interest history for every PERPETUAL asset already
registered in market_data.assets — closes the OI data gap that blocked
Lanchester's OI features (handbook/LANCHESTER_INTEGRATION_INVESTIGATION.md)
and enables a Markets page OI display.

Same pattern as scripts/ingest_top_liquidity.py: real CCXTConnector, real
repositories, idempotent (safe to re-run — ON CONFLICT upsert on the
(asset_id, ts) primary key).

EXCHANGE LIMITATION (see CCXTConnector.fetch_open_interest_history
docstring): Binance's OI-history endpoint only retains ~30 days — `since` is
therefore left unset (most-recent-N via `limit`) rather than requesting a
longer window that would error.

Run:  DATABASE_URL=... python scripts/ingest_open_interest.py [limit]
"""
from __future__ import annotations

import asyncio
import sys

from quant_hub.domain.market_data.entities import OpenInterest
from quant_hub.infrastructure.database import AsyncSessionLocal
from quant_hub.infrastructure.market_data.ccxt_connector import CCXTConnector
from quant_hub.persistence.repositories.market_data import (
    SQLAlchemyAssetRepository,
    SQLAlchemyOpenInterestRepository,
)

LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 500


async def main() -> None:
    connector = CCXTConnector("binance")
    total_persisted = 0
    try:
        async with AsyncSessionLocal() as session:
            assets_repo = SQLAlchemyAssetRepository(session)
            oi_repo = SQLAlchemyOpenInterestRepository(session)

            all_assets = await assets_repo.list_active()
            perpetuals = [a for a in all_assets if a.instrument_type == "PERPETUAL"]
            print(f"Found {len(perpetuals)} PERPETUAL assets to ingest OI for.")

            for asset in perpetuals:
                try:
                    raw_rows = await connector.fetch_open_interest_history(
                        asset.symbol, since=None, limit=LIMIT
                    )
                except Exception as exc:  # noqa: BLE001 — report and continue other assets
                    print(f"  {asset.symbol:20s} FAILED: {exc!r}")
                    continue

                resolved_rows = [
                    OpenInterest(
                        asset_id=asset.id,
                        ts=r.ts,
                        open_interest_usdt=r.open_interest_usdt,
                        open_interest_contracts=r.open_interest_contracts,
                        source=r.source,
                        data_quality=r.data_quality,
                    )
                    for r in raw_rows
                ]
                persisted = await oi_repo.upsert_open_interest(resolved_rows)
                total_persisted += persisted
                latest = resolved_rows[-1] if resolved_rows else None
                latest_desc = (
                    f"latest={latest.ts.isoformat()} oi_usdt={latest.open_interest_usdt}"
                    if latest
                    else "no rows"
                )
                print(f"  {asset.symbol:20s} fetched={len(raw_rows)} persisted={persisted} {latest_desc}")

            await session.commit()
    finally:
        await connector.close()

    print(f"\nDone. {total_persisted} OI rows persisted.")


if __name__ == "__main__":
    asyncio.run(main())
