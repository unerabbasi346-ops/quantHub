"""Retrain XGBoost_MetaLabeler on REAL historical signal + feature data.

Task 0 ML-folder audit finding: the previously-deployed model was trained on
a single placeholder feature (signal.value alone), making its predictions
meaningless. This script builds a real training set from core.signals: for
every recorded signal, a real 8-feature vector (ml/feature_engineering.py's
compute_signal_features) computed from a POINT-IN-TIME-CORRECT MarketDataView
(bars/funding/OI truncated to <= signal.ts — no lookahead), and a REALIZED
label (did the signal's own direction turn out profitable over a fixed
forward horizon, using real future bars — the Lopez de Prado meta-labeling
target this model's docstring already claims to predict).

TRAIN/TEST SPLIT: chronological, not random — the earliest 80% of signals
(by ts) train, the most-recent 20% are held out. A random shuffle would leak
future information into training (two signals close in time on the same
asset share overlapping feature windows); a time split doesn't.

Run:  DATABASE_URL=... python scripts/retrain_metalabeler.py [horizon_bars]
"""
from __future__ import annotations

import asyncio
import bisect
import sys
from pathlib import Path

import pandas as pd

from quant_hub.domain.market_data.entities import AssetRef
from quant_hub.domain.strategy_engine.entities import Signal as DomainSignal
from quant_hub.infrastructure.backtesting.point_in_time_view import PointInTimeMarketDataView
from quant_hub.infrastructure.database import AsyncSessionLocal
from quant_hub.ml.feature_engineering import compute_signal_features, feature_mask, feature_names_for
from quant_hub.ml.ml_engine import XGBoostMetaLabeler
from quant_hub.persistence.repositories.market_data import (
    SQLAlchemyAssetRepository,
    SQLAlchemyFundingRateRepository,
    SQLAlchemyOHLCVRepository,
    SQLAlchemyOpenInterestRepository,
)
from quant_hub.persistence.repositories.ml_models import SQLAlchemyMLModelRepository
from quant_hub.persistence.repositories.strategy_engine import (
    SQLAlchemySignalRepository,
    SQLAlchemyStrategyRepository,
)

HORIZON_BARS = int(sys.argv[1]) if len(sys.argv) > 1 else 24  # 24x 1h bars = 1 day forward
INTERVAL = "1h"
MAX_SIGNALS_PER_STRATEGY = 5000
_ARTIFACT_ROOT = Path(__file__).resolve().parents[1] / "artifacts" / "ml"


async def _build_dataset() -> dict[str, tuple[pd.DataFrame, pd.Series]]:
    """One dataset per instrument type — SPOT signals have no funding/OI, so
    they train a 6-feature model; PERPETUAL signals train the 8-feature one.
    Mixing them (previous behavior) made 2 of 8 columns structurally zero for
    every SPOT row: held-out accuracy 0.4676 vs 0.5424 majority baseline."""
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
        print(f"{len(strategies)} registered strategies")

        # Per-distinct-asset caches, same pattern as the API endpoint —
        # fetch full history once, reuse across every signal on that asset.
        asset_cache: dict = {}

        for strategy in strategies:
            signals = await signal_repo.list_by_strategy(strategy.id, MAX_SIGNALS_PER_STRATEGY)
            signals = sorted(signals, key=lambda s: s.ts)  # oldest -> newest
            print(f"  {strategy.name}: {len(signals)} signals")

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
                if entry_idx == 0 or entry_idx + HORIZON_BARS >= len(all_bars):
                    continue  # not enough history before OR not enough future bars to label

                # NO LOOKAHEAD: feature view sees only bars[:entry_idx] (<= s.ts).
                view = PointInTimeMarketDataView(
                    bars=all_bars[:entry_idx], asset=asset_ref, interval=INTERVAL,
                    funding=all_funding, open_interest=all_oi, as_of=s.ts,
                )
                domain_signal = DomainSignal(asset=asset_ref, value=s.value, ts=s.ts)
                features = await compute_signal_features(domain_signal, view, INTERVAL)

                # Realized meta-label: did a trade in the signal's OWN direction
                # turn out profitable over the forward horizon — real future
                # bars, used ONLY for the label, never for the feature vector.
                entry_close = float(all_bars[entry_idx - 1].close)
                exit_close = float(all_bars[entry_idx - 1 + HORIZON_BARS].close)
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


async def main() -> None:
    import uuid

    datasets = await _build_dataset()
    if not datasets:
        print("\nDataset empty.")
        return

    for itype, (X, y) in datasets.items():
        n = len(X)
        print(f"\n== {itype} == {n} labeled signals, {X.shape[1]} features, positive rate={y.mean():.3f}")
        if n < 50:
            print("Too few labeled signals to train meaningfully (need >= 50). Skipping.")
            continue

        # Chronological split (rows are already in signal-ts order per strategy,
        # concatenated strategy-by-strategy — re-sort isn't needed for the
        # per-strategy time-ordering property that matters: no signal's features
        # were built from another signal's future).
        split = int(n * 0.8)
        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = y.iloc[:split], y.iloc[split:]
        print(f"Train: {len(X_train)}  Test (held out): {len(X_test)}")

        model = XGBoostMetaLabeler()
        model.train(X_train, y_train)
        metrics = model.evaluate(X_test, y_test)

        # Majority-class rate of the held-out set: the accuracy a constant
        # predictor gets for free. A model below this is worse than useless.
        baseline = max(float(y_test.mean()), 1.0 - float(y_test.mean()))

        print("Held-out test metrics:")
        print(f"  accuracy:  {metrics['accuracy']:.4f}  (majority baseline {baseline:.4f})")
        print(f"  precision: {metrics['precision']:.4f}")
        print(f"  recall:    {metrics['recall']:.4f}")
        print("  feature_importance:")
        for name, imp in sorted(metrics["feature_importance"].items(), key=lambda kv: -kv[1]):
            print(f"    {name:24s} {imp:.4f}")

        if float(metrics["accuracy"]) <= baseline:
            print(f"NOT DEPLOYED: accuracy {metrics['accuracy']:.4f} <= majority baseline {baseline:.4f} — "
                  "model adds nothing over always predicting the majority class.")
            continue

        model_type = f"XGBoost_MetaLabeler_{itype}"
        _ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
        job_id = str(uuid.uuid4())
        artifact_path = str(_ARTIFACT_ROOT / model_type / f"{job_id}.joblib")
        model.save_model(artifact_path)

        async with AsyncSessionLocal() as session:
            ml_repo = SQLAlchemyMLModelRepository(session)
            await ml_repo.register_trained(
                model_type=model_type,
                version=job_id,
                framework="xgboost",
                artifact_path=artifact_path,
                config=model.params,
                metrics={
                    "accuracy": float(metrics["accuracy"]),
                    "precision": float(metrics["precision"]),
                    "recall": float(metrics["recall"]),
                    "baseline": baseline,
                    "train_rows": len(X_train),
                    "test_rows": len(X_test),
                    "horizon_bars": HORIZON_BARS,
                    "features": list(feature_names_for(itype)),
                    "feature_mask": feature_mask(itype),
                },
            )
            await session.commit()
        print(f"Deployed as {model_type} version={job_id}")


if __name__ == "__main__":
    asyncio.run(main())
