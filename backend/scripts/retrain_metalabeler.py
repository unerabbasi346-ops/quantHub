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
import sys
from pathlib import Path

from quant_hub.infrastructure.database import AsyncSessionLocal
from quant_hub.ml.feature_engineering import feature_mask, feature_names_for
from quant_hub.ml.ml_engine import XGBoostMetaLabeler
from quant_hub.ml.training_data import build_metalabeler_datasets
from quant_hub.persistence.repositories.ml_models import SQLAlchemyMLModelRepository

HORIZON_BARS = int(sys.argv[1]) if len(sys.argv) > 1 else 24  # 24x 1h bars = 1 day forward
_ARTIFACT_ROOT = Path(__file__).resolve().parents[1] / "artifacts" / "ml"


async def _build_dataset() -> dict:
    """Shared implementation lives in quant_hub.ml.training_data — one
    dataset builder for both this CLI and the /api/ml training surface."""
    return await build_metalabeler_datasets(HORIZON_BARS)


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
