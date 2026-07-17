# Governing specification: Doc 14 §10.6.4 Signal Generation Pipeline — the
#   "Signal Validation" / quality stage between raw signal and sizing.
# Layer: Domain — Doc 07 §Layers (pure function; no I/O, no persistence).
# Doc 00 §14.5/§14.7 DATA HONESTY: quality is computed ONLY from inputs that
#   really exist for the signal — a missing input (no deployed ML model, no
#   regime detector) drops out of the weighting entirely rather than being
#   fabricated as neutral-but-present. A quality score is a SUGGESTION for
#   review/skip triage, never a guarantee.
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

# Below this |value| a signal is conviction noise — the same order of
# magnitude the reference sizers would round to a dust position anyway.
WEAK_STRENGTH_THRESHOLD = Decimal("0.05")

# Component weights when every input is available. Renormalized over the
# subset that actually exists (see module docstring — no fabricated inputs).
_WEIGHTS = {"strength": 0.4, "ml_agreement": 0.4, "regime": 0.2}

_TRADE_THRESHOLD = 0.60
_SKIP_THRESHOLD = 0.35


@dataclass(frozen=True)
class SignalQuality:
    """Quality assessment for one signal, from available inputs only."""

    strength: Decimal              # abs(signal.value), 0..1
    ml_agreement: bool | None      # None = no deployed ML model prediction available
    regime_favorable: bool | None  # None = no deployed regime detector available
    quality_score: Decimal         # 0..1, weighted over AVAILABLE components
    recommendation: str            # TRADE | SKIP | REVIEW
    reasons: tuple[str, ...]       # human-readable, why this recommendation


def evaluate_signal_quality(
    value: Decimal,
    *,
    ml_probability: Decimal | None = None,
    regime_favorable: bool | None = None,
) -> SignalQuality:
    """Score one signal's tradability from what genuinely exists for it.

    - strength: |value| clamped to [0, 1]; below WEAK_STRENGTH_THRESHOLD the
      signal is a hard SKIP regardless of other components (a dust-sized
      conviction is untradeable however confident the model is).
    - ml_agreement: the deployed metalabeler's P(profitable) for the signal's
      OWN direction; > 0.5 agrees. None when no model prediction exists.
    - regime_favorable: a deployed regime detector's verdict. None when none
      is deployed.

    quality_score = weighted mean over the components that exist, weights
    renormalized. Recommendation: >= 0.60 TRADE, < 0.35 SKIP, else REVIEW.
    """
    strength = min(abs(value), Decimal("1"))
    reasons: list[str] = []

    components: dict[str, float] = {"strength": float(strength)}
    if ml_probability is not None:
        agrees = ml_probability > Decimal("0.5")
        components["ml_agreement"] = float(ml_probability) if agrees else float(ml_probability)
        reasons.append(
            f"ML {'agrees' if agrees else 'disagrees'} with direction "
            f"(P={float(ml_probability):.2f})"
        )
    if regime_favorable is not None:
        components["regime"] = 1.0 if regime_favorable else 0.0
        reasons.append(f"regime {'favorable' if regime_favorable else 'unfavorable'}")

    total_weight = sum(_WEIGHTS[name] for name in components)
    score = sum(_WEIGHTS[name] * v for name, v in components.items()) / total_weight
    quality_score = Decimal(str(round(score, 4)))

    ml_agreement = None if ml_probability is None else ml_probability > Decimal("0.5")

    if strength < WEAK_STRENGTH_THRESHOLD:
        reasons.insert(0, f"weak signal: |value|={float(strength):.4f} < {float(WEAK_STRENGTH_THRESHOLD)}")
        recommendation = "SKIP"
    elif score >= _TRADE_THRESHOLD:
        reasons.insert(0, f"quality {score:.2f} >= {_TRADE_THRESHOLD}")
        recommendation = "TRADE"
    elif score < _SKIP_THRESHOLD:
        reasons.insert(0, f"quality {score:.2f} < {_SKIP_THRESHOLD}")
        recommendation = "SKIP"
    else:
        reasons.insert(0, f"quality {score:.2f} in review band [{_SKIP_THRESHOLD}, {_TRADE_THRESHOLD})")
        recommendation = "REVIEW"

    return SignalQuality(
        strength=strength,
        ml_agreement=ml_agreement,
        regime_favorable=regime_favorable,
        quality_score=quality_score,
        recommendation=recommendation,
        reasons=tuple(reasons),
    )
