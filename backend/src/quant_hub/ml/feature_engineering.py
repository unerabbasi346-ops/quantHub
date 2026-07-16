# Governing specification: Doc 12 §8.2 Feature Store / §8.7 Model Serving —
#   Doc 14 §10.6.4's "Feature Computation" pipeline stage, upstream of Signal
#   Combination. Doc 00 §14.5/§14.7 DATA HONESTY: every feature computed from
#   real persisted market data, never fabricated.
# Layer: ML (domain-adjacent) — Doc 04 §Repository Structure.
# Per Doc 00 §14.11
#
# Task 0 ML-folder audit found ml_confidence/ml_probability meaningless: the
# only feature fed to XGBoostMetaLabeler was the signal's own raw `value`
# (api/v1/strategies.py's old placeholder `[[float(value)]]`). This module
# replaces that with a real feature vector built from data that genuinely
# EXISTS at signal-generation time — no lookahead.
#
# NO-LOOKAHEAD CONTRACT: this is a pure function over a MarketDataView. It
# never queries a database directly and never reads anything the view itself
# wasn't handed. Point-in-time correctness (§10.3.4 — "only data available at
# or before this timestamp") is NOT enforced here; it is the VIEW's job
# (PointInTimeMarketDataView for backtests/training, RepositoryBackedMarketDataView
# for live). This function is honest about that split: give it a view that
# leaks future data and its output will too. Callers building training data
# from historical core.signals MUST pass a point-in-time-clamped view.
from __future__ import annotations

import statistics

from quant_hub.domain.market_data.entities import OHLCVBar
from quant_hub.domain.strategy_engine.strategy import MarketDataView
from quant_hub.domain.strategy_engine.entities import Signal

# price_momentum_20/volatility_20 need 20 return-steps, i.e. 21 closes.
# volume_ratio's "20-period avg volume" needs the same 20-bar window (the
# current bar's own volume is bar[-1], averaged against the PRIOR 20 —
# hence 21 bars fetched, matching the momentum/volatility window exactly).
_BARS_NEEDED = 21


def _returns(closes: list[float]) -> list[float]:
    return [
        (closes[i] - closes[i - 1]) / closes[i - 1]
        for i in range(1, len(closes))
        if closes[i - 1] != 0
    ]


async def compute_signal_features(signal: Signal, view: MarketDataView, interval: str = "1h") -> dict[str, float]:
    """Real feature vector for one signal, built ONLY from data a
    point-in-time-correct `view` exposes for `signal.asset` — no lookahead.

    Feature set depends on the asset's instrument type (metalabeler retrain
    finding: funding_rate/open_interest_change are structurally 0 for every
    SPOT signal — 2 of 8 columns pure noise, dragging held-out accuracy
    below the majority-class baseline):
      SPOT      → the 6 SPOT_FEATURE_NAMES keys only
      PERPETUAL → all 8 PERP_FEATURE_NAMES keys

    Use `feature_names_for(instrument_type)` for the matching stable column
    order. A feature that genuinely cannot be computed (insufficient bar
    history, unfunded window) is 0.0 — "0 when unavailable", never a
    fabricated number.
    """
    bars: list[OHLCVBar] = list(await view.latest_bars(signal.asset, interval, limit=_BARS_NEEDED))
    closes = [float(b.close) for b in bars]
    volumes = [float(b.volume) for b in bars]

    price_momentum_5 = 0.0
    price_momentum_20 = 0.0
    volatility_20 = 0.0
    volume_ratio = 0.0

    if len(closes) >= 6 and closes[-6] != 0:
        price_momentum_5 = (closes[-1] - closes[-6]) / closes[-6]
    if len(closes) >= 21 and closes[-21] != 0:
        price_momentum_20 = (closes[-1] - closes[-21]) / closes[-21]
    if len(closes) >= 21:
        step_returns = _returns(closes[-21:])
        if len(step_returns) >= 2:
            volatility_20 = statistics.stdev(step_returns)
    if len(volumes) >= 21:
        prior_20 = volumes[-21:-1]
        avg_volume = sum(prior_20) / len(prior_20)
        if avg_volume != 0:
            volume_ratio = volumes[-1] / avg_volume

    signal_value = float(signal.value)
    features = {
        "price_momentum_5": price_momentum_5,
        "price_momentum_20": price_momentum_20,
        "volatility_20": volatility_20,
        "volume_ratio": volume_ratio,
        "signal_value": signal_value,
        "signal_abs": abs(signal_value),
    }

    if signal.asset.instrument_type == "PERPETUAL":
        funding_rate = 0.0
        funding = await view.latest_funding_rates(signal.asset, limit=1)
        if funding:
            funding_rate = float(funding[-1].funding_rate)

        open_interest_change = 0.0
        oi = await view.latest_open_interest(signal.asset, limit=2)
        if len(oi) >= 2 and oi[-2].open_interest_usdt != 0:
            prev = float(oi[-2].open_interest_usdt)
            curr = float(oi[-1].open_interest_usdt)
            open_interest_change = (curr - prev) / prev

        features["funding_rate"] = funding_rate
        features["open_interest_change"] = open_interest_change

    return features


SPOT_FEATURE_NAMES: tuple[str, ...] = (
    "price_momentum_5", "price_momentum_20", "volatility_20", "volume_ratio",
    "signal_value", "signal_abs",
)

PERP_FEATURE_NAMES: tuple[str, ...] = SPOT_FEATURE_NAMES + (
    "funding_rate", "open_interest_change",
)

# Backwards-compatible alias: the full (perpetual) feature set.
FEATURE_NAMES: tuple[str, ...] = PERP_FEATURE_NAMES


def feature_names_for(instrument_type: str) -> tuple[str, ...]:
    """Stable model column order for an asset's instrument type."""
    return PERP_FEATURE_NAMES if instrument_type == "PERPETUAL" else SPOT_FEATURE_NAMES


def feature_mask(instrument_type: str) -> dict[str, bool]:
    """Which of the full 8 features are active for this instrument type."""
    active = set(feature_names_for(instrument_type))
    return {name: name in active for name in PERP_FEATURE_NAMES}
