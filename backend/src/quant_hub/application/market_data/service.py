# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Application — Doc 07 §Layers
# Service: Market Data — Doc 07 §Core Services
# Implementation rules: services are small and focused; no business logic in controllers
#   — Doc 07 §Implementation Rules
# Per Doc 00 §14.11
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from quant_hub.domain.market_data.connectors import MarketDataConnector
from quant_hub.domain.market_data.entities import OHLCVBar, Tick
from quant_hub.domain.market_data.interfaces import (
    AssetRepository,
    OHLCVRepository,
    TickRepository,
)


@dataclass(frozen=True)
class IngestionResult:
    """Outcome of one ingest_ohlcv() call — Doc 11 §2 Acquire/Persist stages.

    Step 1.4 addition: `fetched` and `persisted` are reported separately
    (rather than a single int) so callers can tell acquisition apart from
    persistence. Today `fetched == persisted` always, since Step 1.2
    explicitly scoped Validate (Doc 11 §2 pipeline stage, not built yet)
    out of this service — nothing currently filters/rejects a fetched bar
    before it reaches upsert_bars. The two counts will diverge once
    Validate exists, so this shape is future-proof rather than assuming
    equality.
    """

    fetched: int
    persisted: int


class MarketDataService:
    """Application service stub — business logic not implemented in Step 0.4.

    Receives repositories via constructor injection — Doc 07 §Implementation Rules.
    """

    def __init__(
        self,
        assets: AssetRepository,
        ohlcv: OHLCVRepository,
        ticks: TickRepository,
    ) -> None:
        self._assets = assets
        self._ohlcv = ohlcv
        self._ticks = ticks


class MarketDataIngestionService:
    """Historical OHLCV / latest-tick ingestion orchestration — Doc 11 §2.

    Implements the Acquire and Persist stages of the Doc 11 §2 pipeline
    (Acquire → Validate → Normalize → Enrich → Persist → Publish) by
    delegating Acquire to a MarketDataConnector and Persist to the
    market_data repositories; Normalize is partially done in the connector
    (see its docstring for flagged gaps).

    SCOPE NOTE (Step 1.2, flagged rather than silently narrowed): Validate
    (Doc 11 §5 Data Validation Engine), Enrich, and Publish are separate
    subsystems not built yet — this service does not run quality gates or
    publication events. It is a connector-to-repository wiring skeleton,
    not the full ETL/ELT pipeline described in Doc 11 §"ETL/ELT Framework".
    """

    def __init__(
        self,
        connector: MarketDataConnector,
        assets: AssetRepository,
        ohlcv: OHLCVRepository,
        ticks: TickRepository,
    ) -> None:
        self._connector = connector
        self._assets = assets
        self._ohlcv = ohlcv
        self._ticks = ticks

    async def ingest_ohlcv(
        self,
        symbol: str,
        interval: str,
        since: datetime | None = None,
        limit: int = 500,
    ) -> IngestionResult:
        """Acquire bars from the connector and persist them — Doc 11 §2 (Acquire, Persist)."""
        raw_bars = await self._connector.fetch_ohlcv(symbol, interval, since, limit)
        if not raw_bars:
            return IngestionResult(fetched=0, persisted=0)
        asset_id = await self._assets.upsert(raw_bars[0].asset)
        bars = [
            OHLCVBar(
                asset_id=asset_id,
                interval=bar.interval,
                ts=bar.ts,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
                vwap=bar.vwap,
                trade_count=bar.trade_count,
                adjustment_factor=bar.adjustment_factor,
                data_quality=bar.data_quality,
                source=bar.source,
            )
            for bar in raw_bars
        ]
        persisted = await self._ohlcv.upsert_bars(bars)
        return IngestionResult(fetched=len(raw_bars), persisted=persisted)

    async def ingest_latest_tick(self, symbol: str) -> None:
        """Acquire the latest tick from the connector and persist it — Doc 11 §2 (Acquire, Persist)."""
        raw_tick = await self._connector.fetch_latest_tick(symbol)
        if raw_tick is None:
            return
        asset_id = await self._assets.upsert(raw_tick.asset)
        tick = Tick(
            asset_id=asset_id,
            ts=raw_tick.ts,
            received_at=raw_tick.received_at,
            feed_origin=raw_tick.feed_origin,
            bid=raw_tick.bid,
            ask=raw_tick.ask,
            last=raw_tick.last,
            bid_size=raw_tick.bid_size,
            ask_size=raw_tick.ask_size,
            last_size=raw_tick.last_size,
            volume=raw_tick.volume,
            conditions=raw_tick.conditions,
            data_quality=raw_tick.data_quality,
        )
        await self._ticks.save_tick(tick)
