# Governing specification: Doc 15 §11.1.5 — signal-implied sizing display figure
# Per Doc 00 §14.11
#
# No database needed — pure computation on domain/strategy_engine/implied_sizing.py.
from __future__ import annotations

from decimal import Decimal

import pytest

from quant_hub.domain.strategy_engine.implied_sizing import (
    DIRECTION_FLAT,
    DIRECTION_LONG,
    DIRECTION_SHORT,
    assert_direction_matches_value,
    compute_direction,
    compute_implied_leverage,
    compute_implied_size_usdt,
)


# ── Direction ────────────────────────────────────────────────────────────────

def test_direction_long_for_positive_value() -> None:
    assert compute_direction(Decimal("0.5")) == DIRECTION_LONG


def test_direction_short_for_negative_value() -> None:
    assert compute_direction(Decimal("-0.3")) == DIRECTION_SHORT


def test_direction_flat_for_zero_value() -> None:
    assert compute_direction(Decimal("0")) == DIRECTION_FLAT


def test_direction_long_at_upper_bound() -> None:
    assert compute_direction(Decimal("1")) == DIRECTION_LONG


def test_direction_short_at_lower_bound() -> None:
    assert compute_direction(Decimal("-1")) == DIRECTION_SHORT


# ── Task 4: direction/value consistency assertion ───────────────────────────

def test_consistency_assertion_passes_for_matching_pair() -> None:
    assert_direction_matches_value(Decimal("0.5"), DIRECTION_LONG)
    assert_direction_matches_value(Decimal("-0.5"), DIRECTION_SHORT)
    assert_direction_matches_value(Decimal("0"), DIRECTION_FLAT)


def test_consistency_assertion_fails_for_mismatched_pair() -> None:
    with pytest.raises(AssertionError):
        assert_direction_matches_value(Decimal("0.5"), DIRECTION_SHORT)
    with pytest.raises(AssertionError):
        assert_direction_matches_value(Decimal("-0.2"), DIRECTION_LONG)
    with pytest.raises(AssertionError):
        assert_direction_matches_value(Decimal("0"), DIRECTION_LONG)


# ── Implied size (capital scaling) ──────────────────────────────────────────

def test_implied_size_scales_with_full_conviction() -> None:
    # full conviction (|value|==1) implies the full configured capital
    assert compute_implied_size_usdt(Decimal("1"), Decimal("10000")) == Decimal("10000.00000000")


def test_implied_size_scales_with_partial_conviction() -> None:
    assert compute_implied_size_usdt(Decimal("0.5"), Decimal("10000")) == Decimal("5000.00000000")


def test_implied_size_is_zero_for_zero_conviction() -> None:
    assert compute_implied_size_usdt(Decimal("0"), Decimal("10000")) == Decimal("0.00000000")


def test_implied_size_uses_magnitude_regardless_of_sign() -> None:
    # SHORT conviction implies the same size magnitude as the equivalent LONG
    assert compute_implied_size_usdt(Decimal("-0.5"), Decimal("10000")) == compute_implied_size_usdt(
        Decimal("0.5"), Decimal("10000")
    )


def test_implied_size_scales_with_capital() -> None:
    small = compute_implied_size_usdt(Decimal("0.5"), Decimal("1000"))
    large = compute_implied_size_usdt(Decimal("0.5"), Decimal("100000"))
    assert small == Decimal("500.00000000")
    assert large == Decimal("50000.00000000")
    assert large == small * 100


def test_implied_size_is_none_without_configured_capital() -> None:
    # F-19: no operator-configured capital -> no fabricated size.
    assert compute_implied_size_usdt(Decimal("0.5"), None) is None


# ── Implied leverage ─────────────────────────────────────────────────────────

def test_leverage_defaults_to_one_for_spot() -> None:
    assert compute_implied_leverage({}, instrument_type="SPOT", position_leverage=None) == Decimal("1.0")


def test_leverage_ignores_position_leverage_for_spot() -> None:
    # SPOT has no margin/leverage concept (S-10) -> position_leverage never consulted.
    assert compute_implied_leverage(
        {}, instrument_type="SPOT", position_leverage=Decimal("5")
    ) == Decimal("1.0")


def test_leverage_defaults_to_one_for_perpetual_with_no_position() -> None:
    assert compute_implied_leverage({}, instrument_type="PERPETUAL", position_leverage=None) == Decimal("1.0")


def test_leverage_uses_position_leverage_for_perpetual() -> None:
    assert compute_implied_leverage(
        {}, instrument_type="PERPETUAL", position_leverage=Decimal("3")
    ) == Decimal("3")


def test_leverage_prefers_strategy_config_over_position() -> None:
    assert compute_implied_leverage(
        {"leverage": "2.5"}, instrument_type="PERPETUAL", position_leverage=Decimal("5")
    ) == Decimal("2.5")


def test_leverage_prefers_strategy_config_for_spot_too() -> None:
    assert compute_implied_leverage({"leverage": 2}, instrument_type="SPOT", position_leverage=None) == Decimal("2")
