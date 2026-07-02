# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Infrastructure — Doc 07 §Layers
# Dependency rule: infrastructure implements interfaces defined by domain
#   — Doc 07 §Dependency Rules
# Doc 02 §Dependency Rules: strategies reach market data only through this
#   governed, read-only surface, never a connector/exchange directly.
# Per Doc 00 §14.11
#
# Step 2.4: concrete backing for domain/strategy_engine/strategy.py's
# MarketDataView ABC (Step 2.1) — the piece that lets a Strategy plugin
# read Phase 1's real ingested data. Composes the existing Phase 1
# repositories (AssetRepository, OHLCVRepository, TickRepository) rather
# than querying the database directly, so this class has zero SQL of its
# own — Doc 07 §Dependency Rules (infrastructure implements interfaces;
# this one happens to implement a domain interface by delegating to other
# already-implemented domain interfaces).
from __future__ import annotations

from collections.abc import Sequence

from quant_hub.domain.market_data.entities import AssetRef, OHLCVBar, Tick
from quant_hub.domain.market_data.interfaces import AssetRepository, OHLCVRepository, TickRepository
from quant_hub.domain.strategy_engine.strategy import MarketDataView


class RepositoryBackedMarketDataView(MarketDataView):
    """MarketDataView backed by the Phase 1 market-data repositories.

    JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged): resolves AssetRef ->
    asset_id via AssetRepository.get_by_symbol_exchange on EVERY call,
    rather than caching. Simplest correct implementation, proportionate to
    this step's scope (one reference strategy, not a high-frequency
    engine loop); revisit if profiling ever shows this resolution
    dominating a real strategy-invocation hot path. An unregistered asset
    (get_by_symbol_exchange returns None) is treated as "no data yet" —
    an empty sequence / None, not an error — consistent with how a
    freshly-registered strategy pointed at an instrument nobody has
    ingested yet should behave (return no signal, not raise).
    """

    def __init__(self, assets: AssetRepository, bars: OHLCVRepository, ticks: TickRepository) -> None:
        self._assets = assets
        self._bars = bars
        self._ticks = ticks

    async def latest_bars(
        self, asset: AssetRef, interval: str, limit: int = 100
    ) -> Sequence[OHLCVBar]:
        asset_id = await self._assets.get_by_symbol_exchange(asset.symbol, asset.exchange)
        if asset_id is None:
            return []
        return await self._bars.get_bars(asset_id, interval, limit)

    async def latest_tick(self, asset: AssetRef) -> Tick | None:
        asset_id = await self._assets.get_by_symbol_exchange(asset.symbol, asset.exchange)
        if asset_id is None:
            return None
        return await self._ticks.get_latest(asset_id)
