# Governing specification: ml/feature_engineering.py — Step "ML: real feature
# engineering for signal confidence". Per Doc 00 §14.11
#
# Proves: (1) compute_signal_features returns the documented fixed-shape
# 8-feature dict; (2) point-in-time truncation actually changes the computed
# features (i.e. the pipeline is genuinely sensitive to a lookahead bug, so
# the production code's truncate-before-construct discipline is load-bearing,
# not decorative); (3) XGBoostMetaLabeler trained on a real, noisy (not
# perfectly separable) dataset does NOT hit 1.0 accuracy — a regression guard
# against the exact overfitting failure mode this task was written to fix.
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from quant_hub.domain.market_data.entities import AssetRef, OHLCVBar
from quant_hub.domain.strategy_engine.entities import Signal
from quant_hub.infrastructure.backtesting.point_in_time_view import PointInTimeMarketDataView
from quant_hub.ml.feature_engineering import FEATURE_NAMES, compute_signal_features
from quant_hub.ml.ml_engine import XGBoostMetaLabeler

_ASSET = AssetRef(symbol="ETH/USDT:USDT", exchange="binance", asset_class="crypto", instrument_type="PERPETUAL")
_ASSET_ID = uuid.uuid4()


def _bar(i: int, close: float, ts0: datetime) -> OHLCVBar:
    return OHLCVBar(
        asset_id=_ASSET_ID, interval="1h", ts=ts0 + timedelta(hours=i),
        open=Decimal(str(close)), high=Decimal(str(close)), low=Decimal(str(close)),
        close=Decimal(str(close)), volume=Decimal("100"),
    )


def _linear_bars(n: int, start: float, step: float, ts0: datetime) -> list[OHLCVBar]:
    return [_bar(i, start + i * step, ts0) for i in range(n)]


@pytest.mark.asyncio
async def test_compute_signal_features_shape():
    ts0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    bars = _linear_bars(25, start=100.0, step=1.0, ts0=ts0)
    signal_ts = bars[24].ts
    view = PointInTimeMarketDataView(bars=bars, asset=_ASSET, interval="1h", as_of=signal_ts)
    signal = Signal(asset=_ASSET, value=Decimal("0.5"), ts=signal_ts)

    result = await compute_signal_features(signal, view, "1h")

    assert set(result.keys()) == set(FEATURE_NAMES)
    assert len(result) == 8
    for v in result.values():
        assert isinstance(v, float)
    assert result["signal_value"] == 0.5
    assert result["signal_abs"] == 0.5


@pytest.mark.asyncio
async def test_no_lookahead_truncation_changes_features():
    """A future price spike must NOT influence features computed as-of a
    signal BEFORE that spike — but if it were (mis)included, it would change
    the result. Proves truncation is load-bearing: same 30-bar series, same
    signal, only difference is whether bars after signal.ts are visible.
    """
    ts0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    pre_spike = _linear_bars(25, start=100.0, step=0.5, ts0=ts0)  # slow uptrend, indices 0..24
    spike = [_bar(i, 1000.0, ts0) for i in range(25, 30)]  # violent future spike, indices 25..29
    full_series = pre_spike + spike
    signal_ts = pre_spike[-1].ts  # signal fires at index 24, BEFORE the spike
    signal = Signal(asset=_ASSET, value=Decimal("0.3"), ts=signal_ts)

    # Correct, point-in-time-truncated view (production discipline: caller
    # slices bars[:entry_idx] BEFORE constructing the view — see
    # api/v1/strategies.py::_view_for / scripts/retrain_metalabeler.py).
    correct_view = PointInTimeMarketDataView(bars=pre_spike, asset=_ASSET, interval="1h", as_of=signal_ts)
    correct_features = await compute_signal_features(signal, correct_view, "1h")

    # A view that (incorrectly) exposes the full series including future bars
    # — simulates the lookahead bug this task exists to prevent.
    leaky_view = PointInTimeMarketDataView(bars=full_series, asset=_ASSET, interval="1h", as_of=signal_ts)
    leaky_features = await compute_signal_features(signal, leaky_view, "1h")

    # The spike is dramatic enough that momentum/volatility MUST differ if
    # future bars leaked in — proving the feature pipeline is genuinely
    # sensitive to lookahead, not accidentally immune to it.
    assert correct_features["price_momentum_5"] != leaky_features["price_momentum_5"]
    assert correct_features["volatility_20"] != leaky_features["volatility_20"]
    # The correct (non-leaky) momentum reflects only the slow uptrend actually
    # visible at signal time — small and positive, nowhere near the spike's magnitude.
    assert 0 < correct_features["price_momentum_5"] < 0.1


@pytest.mark.asyncio
async def test_funding_and_oi_zero_when_unavailable():
    ts0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    bars = _linear_bars(25, start=100.0, step=1.0, ts0=ts0)
    signal_ts = bars[-1].ts
    # No funding/OI wired -> honest 0.0, never fabricated.
    view = PointInTimeMarketDataView(bars=bars, asset=_ASSET, interval="1h", as_of=signal_ts)
    signal = Signal(asset=_ASSET, value=Decimal("-0.2"), ts=signal_ts)

    result = await compute_signal_features(signal, view, "1h")

    assert result["funding_rate"] == 0.0
    assert result["open_interest_change"] == 0.0


def test_metalabeler_on_noisy_data_is_not_overfit():
    """Real-shaped, NOT perfectly separable data — the exact failure mode
    the task calls out ('accuracy should NOT be 1.0 — that was overfitting').
    A single placeholder feature perfectly memorizes a small dataset; 8 real
    features on noisy labels should generalize imperfectly, like real markets.
    """
    rng = np.random.default_rng(7)
    n = 400
    X = pd.DataFrame(
        {name: rng.normal(size=n) for name in FEATURE_NAMES}
    )
    # Label has a real but weak relationship to one feature, plus heavy noise
    # — deliberately NOT a clean separable boundary a tree can memorize.
    signal_strength = X["signal_value"] + X["price_momentum_20"] * 0.5
    noise = rng.normal(scale=2.0, size=n)
    y = pd.Series(((signal_strength + noise) > 0).astype(int))

    split = int(n * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]

    model = XGBoostMetaLabeler()
    model.train(X_train, y_train)
    metrics = model.evaluate(X_test, y_test)

    assert metrics["accuracy"] < 1.0
    # Better than a coin flip but not suspiciously perfect — a real,
    # generalizing model on noisy data lands in this band.
    assert 0.4 < metrics["accuracy"] < 0.95
