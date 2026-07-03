# Governing specification: Doc 14 §10.3.4 — Historical Data Consumption
#   (Point-in-Time Correctness)
# Layer: Infrastructure — Doc 07 §Layers (implements a domain interface)
# Doc 02 §Dependency Rules: strategies reach market data only through this
#   governed, read-only surface.
# Invariants: P-13 (deterministic), Doc 14 §10.3.4 point-in-time correctness
# Per Doc 00 §14.11
#
# Step 3.7: the ONLY backtest-specific data surface. It backs the SAME
# MarketDataView contract the reference strategy already reads through in live
# operation (RepositoryBackedMarketDataView, Step 2.4) — so the strategy code
# runs unchanged in a backtest — but serves an in-memory, chronologically
# CLAMPED bar list instead of a live repository. That clamping is what enforces
# §10.3.4: "at each timestamp, only data available at or before that timestamp
# shall be accessible to the strategy." The engine advances the as-of point one
# bar at a time and hands the strategy a view over bars[0..as_of] only, so the
# strategy can never see a future bar.
from __future__ import annotations

from collections.abc import Sequence

from quant_hub.domain.market_data.entities import AssetRef, OHLCVBar, Tick
from quant_hub.domain.strategy_engine.strategy import MarketDataView


class PointInTimeMarketDataView(MarketDataView):
    """A MarketDataView over a fixed, already-clamped slice of bars.

    Constructed per simulation step with the bars visible AT and BEFORE that
    step (the engine passes `bars[: as_of + 1]`), for a single instrument +
    interval. `latest_bars` returns the trailing `limit` of that slice —
    identical semantics to the live view, so the strategy's moving-average
    logic behaves the same. `latest_tick` returns None: a bar-driven backtest
    has no tick stream (the strategy under test reads bars, not ticks).
    """

    def __init__(self, bars: Sequence[OHLCVBar], asset: AssetRef, interval: str) -> None:
        self._bars = list(bars)
        self._asset = asset
        self._interval = interval

    async def latest_bars(
        self, asset: AssetRef, interval: str, limit: int = 100
    ) -> Sequence[OHLCVBar]:
        # Only this backtest's instrument+interval has data; anything else is
        # "no data" (empty), matching how the live view treats an unknown asset.
        if (asset.symbol, asset.exchange) != (self._asset.symbol, self._asset.exchange):
            return []
        if interval != self._interval:
            return []
        return self._bars[-limit:] if 0 < limit < len(self._bars) else list(self._bars)

    async def latest_tick(self, asset: AssetRef) -> Tick | None:
        return None
