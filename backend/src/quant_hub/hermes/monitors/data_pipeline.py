# Hermes monitor: ingestion freshness per asset, read directly off
# market_data.ohlcv_bars / market_data.funding_rates via raw SQL — no
# repository/domain import, per the package's import boundary (see
# quant_hub/hermes/__init__.py). market_data is not one of the four barred
# domains, but a raw SELECT keeps this monitor trivially read-only either way.
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

STATUS_FRESH = "FRESH"
STATUS_STALE = "STALE"
STATUS_DEAD = "DEAD"

# Doc-3 task spec, verbatim: green <1h, amber 1-24h, red >24h.
_FRESH_SECONDS = 3600
_STALE_SECONDS = 86400


def _staleness_status(staleness_seconds: float | None) -> str:
    if staleness_seconds is None:
        return STATUS_DEAD
    if staleness_seconds < _FRESH_SECONDS:
        return STATUS_FRESH
    if staleness_seconds < _STALE_SECONDS:
        return STATUS_STALE
    return STATUS_DEAD


@dataclass(frozen=True)
class AssetFreshness:
    asset_id: str
    symbol: str
    instrument_type: str
    last_bar_ts: datetime | None
    bar_count: int
    staleness_seconds: float | None
    status: str


@dataclass(frozen=True)
class FundingFreshness:
    asset_id: str
    symbol: str
    last_funding_ts: datetime | None
    staleness_seconds: float | None
    status: str


async def get_asset_freshness(session: AsyncSession) -> list[AssetFreshness]:
    rows = (
        await session.execute(
            text(
                """
                SELECT
                    a.id AS asset_id,
                    a.symbol,
                    a.instrument_type,
                    MAX(b.ts) AS last_bar_ts,
                    COUNT(b.id) AS bar_count
                FROM market_data.assets a
                LEFT JOIN market_data.ohlcv_bars b ON b.asset_id = a.id
                WHERE a.is_active = TRUE
                GROUP BY a.id, a.symbol, a.instrument_type
                ORDER BY a.symbol
                """
            )
        )
    ).all()

    now = datetime.now(timezone.utc)
    out: list[AssetFreshness] = []
    for row in rows:
        last_ts = row.last_bar_ts
        staleness = (now - last_ts).total_seconds() if last_ts is not None else None
        out.append(
            AssetFreshness(
                asset_id=str(row.asset_id),
                symbol=row.symbol,
                instrument_type=row.instrument_type,
                last_bar_ts=last_ts,
                bar_count=row.bar_count,
                staleness_seconds=staleness,
                status=_staleness_status(staleness),
            )
        )
    return out


async def get_funding_freshness(session: AsyncSession) -> list[FundingFreshness]:
    rows = (
        await session.execute(
            text(
                """
                SELECT
                    a.id AS asset_id,
                    a.symbol,
                    MAX(f.funding_time) AS last_funding_ts
                FROM market_data.assets a
                LEFT JOIN market_data.funding_rates f ON f.asset_id = a.id
                WHERE a.is_active = TRUE AND a.instrument_type = 'PERPETUAL'
                GROUP BY a.id, a.symbol
                ORDER BY a.symbol
                """
            )
        )
    ).all()

    now = datetime.now(timezone.utc)
    out: list[FundingFreshness] = []
    for row in rows:
        last_ts = row.last_funding_ts
        staleness = (now - last_ts).total_seconds() if last_ts is not None else None
        out.append(
            FundingFreshness(
                asset_id=str(row.asset_id),
                symbol=row.symbol,
                last_funding_ts=last_ts,
                staleness_seconds=staleness,
                status=_staleness_status(staleness),
            )
        )
    return out
