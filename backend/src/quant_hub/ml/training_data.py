# Governing specification: Doc 12 §8.2 Feature Store — the labeled-dataset
#   builder for the metalabeler, extracted from scripts/retrain_metalabeler.py
#   so both the CLI retrain and the /api/ml training surface share ONE
#   implementation (no drift between the two).
# Layer: ML (domain-adjacent). Doc 00 §14.5/§14.7 DATA HONESTY: every row is
#   a REAL recorded signal with a point-in-time-correct feature vector and a
#   REALIZED forward-return label — no synthetic rows, no lookahead.
from __future__ import annotations

import bisect

import pandas as pd

from quant_hub.domain.market_data.entities import AssetRef
from quant_hub.domain.strategy_engine.entities import Signal as DomainSignal
from quant_hub.infrastructure.backtesting.point_in_time_view import PointInTimeMarketDataView
from quant_hub.infrastructure.database import AsyncSessionLocal
from quant_hub.ml.feature_engineering import compute_signal_features, feature_names_for
from quant_hub.persistence.repositories.market_data import (
    SQLAlchemyAssetRepository,
    SQLAlchemyFundingRateRepository,
    SQLAlchemyOHLCVRepository,
    SQLAlchemyOpenInterestRepository,
)
from quant_hub.persistence.repositories.strategy_engine import (
    SQLAlchemySignalRepository,
    SQLAlchemyStrategyRepository,
)

INTERVAL = "1h"
MAX_SIGNALS_PER_STRATEGY = 5000


async def build_metalabeler_datasets(
    horizon_bars: int = 24,
) -> dict[str, tuple[pd.DataFrame, pd.Series]]:
    """One labeled dataset per instrument type ("SPOT"/"PERPETUAL"), built
    from every strategy's recorded signals. Rows are per-strategy
    chronological (oldest -> newest), so a positional 80/20 split is a valid
    time split. Instrument types with zero labelable signals are absent from
    the result (honest — e.g. perp signal assets missing 1h bars)."""
    rows: dict[str, list[dict[str, float]]] = {"SPOT": [], "PERPETUAL": []}
    labels: dict[str, list[int]] = {"SPOT": [], "PERPETUAL": []}

    async with AsyncSessionLocal() as session:
        strategy_repo = SQLAlchemyStrategyRepository(session)
        signal_repo = SQLAlchemySignalRepository(session)
        asset_repo = SQLAlchemyAssetRepository(session)
        bars_repo = SQLAlchemyOHLCVRepository(session)
        funding_repo = SQLAlchemyFundingRateRepository(session)
        oi_repo = SQLAlchemyOpenInterestRepository(session)

        strategies = await strategy_repo.list_all()

        # Per-distinct-asset caches — fetch full history once per asset.
        asset_cache: dict = {}

        for strategy in strategies:
            signals = await signal_repo.list_by_strategy(strategy.id, MAX_SIGNALS_PER_STRATEGY)
            signals = sorted(signals, key=lambda s: s.ts)  # oldest -> newest

            for s in signals:
                if s.asset_id not in asset_cache:
                    asset = await asset_repo.get_by_id(s.asset_id)
                    if asset is None:
                        asset_cache[s.asset_id] = None
                        continue
                    asset_ref = AssetRef(
                        symbol=asset.symbol, exchange=asset.exchange,
                        asset_class="crypto", instrument_type=asset.instrument_type,
                    )
                    all_bars = await bars_repo.get_bars(s.asset_id, INTERVAL, limit=200_000)
                    all_funding = await funding_repo.get_funding_rates(s.asset_id, limit=200_000)
                    all_oi = await oi_repo.get_open_interest_history(s.asset_id, limit=200_000)
                    asset_cache[s.asset_id] = (asset_ref, all_bars, all_funding, all_oi)
                cached = asset_cache[s.asset_id]
                if cached is None:
                    continue
                asset_ref, all_bars, all_funding, all_oi = cached
                if not all_bars:
                    continue

                bar_ts = [b.ts for b in all_bars]
                entry_idx = bisect.bisect_right(bar_ts, s.ts)  # first bar strictly after s.ts
                if entry_idx == 0 or entry_idx + horizon_bars >= len(all_bars):
                    continue  # not enough history before OR not enough future bars to label

                # NO LOOKAHEAD: feature view sees only bars[:entry_idx] (<= s.ts).
                view = PointInTimeMarketDataView(
                    bars=all_bars[:entry_idx], asset=asset_ref, interval=INTERVAL,
                    funding=all_funding, open_interest=all_oi, as_of=s.ts,
                )
                domain_signal = DomainSignal(asset=asset_ref, value=s.value, ts=s.ts)
                features = await compute_signal_features(domain_signal, view, INTERVAL)

                # Realized meta-label: did a trade in the signal's OWN direction
                # profit over the forward horizon — real future bars, used ONLY
                # for the label, never the feature vector.
                entry_close = float(all_bars[entry_idx - 1].close)
                exit_close = float(all_bars[entry_idx - 1 + horizon_bars].close)
                if entry_close == 0 or float(s.value) == 0:
                    continue
                realized_return = (exit_close - entry_close) / entry_close
                direction = 1.0 if float(s.value) > 0 else -1.0
                label = 1 if direction * realized_return > 0 else 0

                itype = asset_ref.instrument_type
                rows[itype].append(features)
                labels[itype].append(label)

    return {
        itype: (
            pd.DataFrame(rows[itype], columns=list(feature_names_for(itype))),
            pd.Series(labels[itype], name="profitable"),
        )
        for itype in rows
        if rows[itype]
    }
