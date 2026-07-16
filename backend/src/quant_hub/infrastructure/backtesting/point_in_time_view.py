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
from datetime import datetime

from quant_hub.domain.market_data.entities import AssetRef, FundingRate, OHLCVBar, OpenInterest, Tick
from quant_hub.domain.strategy_engine.strategy import MarketDataView


class PointInTimeMarketDataView(MarketDataView):
    """A MarketDataView over a fixed, already-clamped slice of bars.

    Constructed per simulation step with the bars visible AT and BEFORE that
    step (the engine passes `bars[: as_of + 1]`), for a single instrument +
    interval. `latest_bars` returns the trailing `limit` of that slice —
    identical semantics to the live view, so the strategy's moving-average
    logic behaves the same. `latest_tick` returns None: a bar-driven backtest
    has no tick stream (the strategy under test reads bars, not ticks).

    FUNDING (additive, migration e7a3c1f5b9d2 lineage): a funding-DRIVEN strategy
    (FundingRateBasisStrategy) reads `latest_funding_rates`, which the ABC
    defaults to empty — so without this, such a strategy would emit NO signal in
    a backtest replay. The engine now optionally passes the instrument's full
    funding series plus this step's `as_of` timestamp; `latest_funding_rates`
    then serves only funding observations at/before `as_of`, enforcing §10.3.4
    point-in-time correctness for funding exactly as the bar slice does for bars.
    Backward compatible: a caller that passes no funding (equities/spot backtests,
    every pre-existing construction site) gets the ABC's empty default unchanged.
    """

    def __init__(
        self,
        bars: Sequence[OHLCVBar],
        asset: AssetRef,
        interval: str,
        funding: Sequence[FundingRate] = (),
        open_interest: Sequence[OpenInterest] = (),
        as_of: datetime | None = None,
    ) -> None:
        self._bars = list(bars)
        self._asset = asset
        self._interval = interval
        # Funding kept sorted oldest->newest and clamped to as_of on read (point-in-time).
        self._funding = sorted(funding, key=lambda f: f.funding_time)
        # Same treatment for OI (migration b4f8e21ac9d3) as funding above.
        self._open_interest = sorted(open_interest, key=lambda o: o.ts)
        self._as_of = as_of

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

    async def latest_funding_rates(
        self, asset: AssetRef, limit: int = 100
    ) -> Sequence[FundingRate]:
        # Same instrument-scoping as latest_bars; unknown asset -> "no data".
        if (asset.symbol, asset.exchange) != (self._asset.symbol, self._asset.exchange):
            return []
        # §10.3.4: never reveal a funding observation dated after this step.
        visible = (
            self._funding
            if self._as_of is None
            else [f for f in self._funding if f.funding_time <= self._as_of]
        )
        return visible[-limit:] if 0 < limit < len(visible) else list(visible)

    async def latest_open_interest(
        self, asset: AssetRef, limit: int = 100
    ) -> Sequence[OpenInterest]:
        # Same instrument-scoping and §10.3.4 as_of clamp as latest_funding_rates.
        if (asset.symbol, asset.exchange) != (self._asset.symbol, self._asset.exchange):
            return []
        visible = (
            self._open_interest
            if self._as_of is None
            else [o for o in self._open_interest if o.ts <= self._as_of]
        )
        return visible[-limit:] if 0 < limit < len(visible) else list(visible)
