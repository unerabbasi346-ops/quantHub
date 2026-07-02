# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Application — Doc 07 §Layers
# Service: Market Data — Doc 07 §Core Services
# Implementation rules: services are small and focused; no business logic in controllers
#   — Doc 07 §Implementation Rules
# Per Doc 00 §14.11
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from quant_hub.domain.market_data.connectors import MarketDataConnector
from quant_hub.domain.market_data.entities import OHLCVBar, Tick
from quant_hub.domain.market_data.interfaces import (
    AssetRepository,
    OHLCVRepository,
    TickRepository,
)
from quant_hub.domain.market_data.quality import assess_bar_quality, assess_tick_quality
from quant_hub.domain.market_data.validation import validate_bar, validate_tick
from quant_hub.infrastructure.market_data.retry import RetryExhaustedError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestionResult:
    """Outcome of one ingest_ohlcv() call — Doc 11 §2 Acquire/Validate/Persist stages.

    Step 1.4: `fetched` and `persisted` reported separately so callers can
    tell acquisition apart from persistence. Step 1.6 adds `rejected`
    (Doc 11 §5 Data Validation Engine, scoped per handbook/
    KNOWN_LIMITATIONS.md S-2): bars failing basic schema/completeness/
    range/consistency checks are excluded before persistence.
    `fetched == persisted + rejected` whenever nothing else fails.

    Step 1.8 adds `acquire_failed` (Doc 11 §8 Error Recovery): True when
    the connector call exhausted its retries — distinguishes "the
    exchange had no new data" (fetched=0, acquire_failed=False) from "we
    couldn't reach the exchange at all" (fetched=0, acquire_failed=True),
    which `fetched == 0` alone can't tell apart.
    """

    fetched: int
    persisted: int
    rejected: int = 0
    acquire_failed: bool = False


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

    Implements the Acquire, Validate, and Persist stages of the Doc 11 §2
    pipeline (Acquire → Validate → Normalize → Enrich → Persist → Publish)
    by delegating Acquire to a MarketDataConnector, Validate to
    domain/market_data/validation.py (Step 1.6), and Persist to the
    market_data repositories; Normalize is partially done in the connector
    (see its docstring for flagged gaps).

    VALIDATE (Step 1.6, Doc 11 §5 Data Validation Engine): basic schema,
    completeness, range, and consistency checks run on every acquired
    bar/tick before persistence. Invalid records are rejected — logged
    with their errors and full field values, never persisted, never
    silently dropped — per Doc 11 §5 Failure Policy ("Reject invalid
    datasets... Generate validation reports"), scoped down per
    handbook/KNOWN_LIMITATIONS.md S-2 to a per-record structured log entry
    rather than a full quality-rules-engine/report artifact.

    QUALITY SCORING (Step 1.7, Doc 11 §6 Data Quality Scoring): every
    record surviving Validate gets a computed `data_quality` value (see
    domain/market_data/quality.py for the metric-by-metric scoping
    rationale) instead of a hardcoded default — bars pass through their
    connector-asserted quality (meaning "passed Step 1.6 Validate", not
    an unconditional constant); ticks additionally get a staleness check
    (Freshness/Timeliness, collapsed into one signal per S-2).

    SCOPE NOTE (Step 1.2, still current): Enrich and Publish are separate
    subsystems not built yet — this service does not run publication
    events. It is not the full ETL/ELT pipeline described in Doc 11
    §"ETL/ELT Framework" (out of scope per S-1).
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
        """Acquire, validate, and persist bars — Doc 11 §2 (Acquire, Validate, Persist)."""
        try:
            raw_bars = await self._connector.fetch_ohlcv(symbol, interval, since, limit)
        except RetryExhaustedError as exc:
            # Doc 11 §8: "No failed ingestion shall silently discard
            # records" — this IS the S-2-scoped dead-letter-queue/operator-
            # notification equivalent: a clear, structured ERROR log
            # (more severe than a per-record validation WARNING, since
            # nothing at all was acquired this cycle) rather than a raised
            # exception that would crash the whole caller/script, and
            # rather than a separate DLQ table/alerting system.
            logger.error(
                "ingest_ohlcv: acquire failed after retries, symbol=%s interval=%s "
                "attempts=%d last_error=%r",
                symbol, interval, exc.attempts, exc.last_error,
            )
            return IngestionResult(fetched=0, persisted=0, rejected=0, acquire_failed=True)

        if not raw_bars:
            return IngestionResult(fetched=0, persisted=0, rejected=0)

        valid_raw_bars = []
        rejected = 0
        for bar in raw_bars:
            result = validate_bar(bar)
            if result.is_valid:
                valid_raw_bars.append(bar)
            else:
                rejected += 1
                # Doc 11 §5 Failure Policy: "Reject invalid datasets...
                # Generate validation reports" — scoped per S-2 to a
                # structured log line (what failed + full record) rather
                # than a separate quarantine store/report artifact.
                logger.warning(
                    "ingest_ohlcv: rejected invalid bar, symbol=%s interval=%s "
                    "errors=%s bar=%r",
                    symbol, interval, list(result.errors), bar,
                )

        if not valid_raw_bars:
            return IngestionResult(fetched=len(raw_bars), persisted=0, rejected=rejected)

        asset_id = await self._assets.upsert(valid_raw_bars[0].asset)
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
                data_quality=assess_bar_quality(source_quality=bar.data_quality),
                source=bar.source,
            )
            for bar in valid_raw_bars
        ]
        persisted = await self._ohlcv.upsert_bars(bars)
        return IngestionResult(fetched=len(raw_bars), persisted=persisted, rejected=rejected)

    async def ingest_latest_tick(self, symbol: str) -> None:
        """Acquire, validate, and persist the latest tick — Doc 11 §2 (Acquire, Validate, Persist)."""
        try:
            raw_tick = await self._connector.fetch_latest_tick(symbol)
        except RetryExhaustedError as exc:
            # Doc 11 §8 — see ingest_ohlcv's acquire-failure log for the
            # same S-2-scoped reasoning.
            logger.error(
                "ingest_latest_tick: acquire failed after retries, symbol=%s "
                "attempts=%d last_error=%r",
                symbol, exc.attempts, exc.last_error,
            )
            return

        if raw_tick is None:
            return

        result = validate_tick(raw_tick)
        if not result.is_valid:
            # Doc 11 §5 Failure Policy — see ingest_ohlcv's rejection log
            # for the same S-2-scoped reasoning.
            logger.warning(
                "ingest_latest_tick: rejected invalid tick, symbol=%s errors=%s tick=%r",
                symbol, list(result.errors), raw_tick,
            )
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
            data_quality=assess_tick_quality(
                ts=raw_tick.ts,
                received_at=raw_tick.received_at,
                source_quality=raw_tick.data_quality,
            ),
        )
        await self._ticks.save_tick(tick)
