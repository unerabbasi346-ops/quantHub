# Unit checks for domain/strategy_engine/signal_quality.py — pure function,
# no I/O. Covers the hard-SKIP weak band, TRADE/REVIEW/SKIP thresholds, and
# the missing-input renormalization (no fabricated components).
from decimal import Decimal

from quant_hub.domain.strategy_engine.signal_quality import (
    WEAK_STRENGTH_THRESHOLD,
    evaluate_signal_quality,
)


def test_weak_signal_is_hard_skip_even_with_confident_ml() -> None:
    q = evaluate_signal_quality(Decimal("0.01"), ml_probability=Decimal("0.95"))
    assert q.recommendation == "SKIP"
    assert q.strength < WEAK_STRENGTH_THRESHOLD
    assert any("weak signal" in r for r in q.reasons)


def test_strong_signal_with_agreeing_ml_trades() -> None:
    q = evaluate_signal_quality(Decimal("0.9"), ml_probability=Decimal("0.8"))
    assert q.recommendation == "TRADE"
    assert q.ml_agreement is True
    assert q.quality_score >= Decimal("0.6")


def test_strong_signal_with_disagreeing_ml_lands_in_review_or_skip() -> None:
    q = evaluate_signal_quality(Decimal("0.9"), ml_probability=Decimal("0.1"))
    assert q.ml_agreement is False
    assert q.recommendation in ("REVIEW", "SKIP")


def test_no_ml_input_renormalizes_to_strength_only() -> None:
    q = evaluate_signal_quality(Decimal("0.8"))
    assert q.ml_agreement is None
    assert q.regime_favorable is None
    # strength is the only component -> score == strength
    assert abs(float(q.quality_score) - 0.8) < 1e-9
    assert q.recommendation == "TRADE"


def test_moderate_signal_without_ml_reviews() -> None:
    q = evaluate_signal_quality(Decimal("0.4"))
    assert q.recommendation == "REVIEW"


def test_negative_value_uses_absolute_strength() -> None:
    q = evaluate_signal_quality(Decimal("-0.7"), ml_probability=Decimal("0.7"))
    assert q.strength == Decimal("0.7")
    assert q.recommendation == "TRADE"
