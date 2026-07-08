# Governing specification: Doc 07 §Layers (domain pure logic). Doc 00 §14.11.
#
# Unit tests for the pure price-return correlation calculator
# (domain/market_data/correlation.py). No DB — the function is deterministic
# over its inputs, so these pin the exact statistical behaviour and the honest
# "undefined -> None" handling.
from __future__ import annotations

from decimal import Decimal

from quant_hub.domain.market_data.correlation import compute_return_correlations


def test_identical_series_are_perfectly_correlated() -> None:
    closes = [Decimal("100"), Decimal("110"), Decimal("121"), Decimal("133.1")]
    result = compute_return_correlations({"A": closes, "B": list(closes)})
    assert result.labels == ("A", "B")
    assert result.sample_size == 3  # 4 prices -> 3 returns
    # diagonal is 1, and two identical series correlate at +1
    assert result.matrix[0][0] == 1.0
    assert result.matrix[1][1] == 1.0
    assert abs(result.matrix[0][1] - 1.0) < 1e-9
    assert abs(result.matrix[1][0] - 1.0) < 1e-9


def test_inverse_series_are_negatively_correlated() -> None:
    # B moves opposite to A on every step -> perfect -1 return correlation
    a = [100.0, 110.0, 99.0, 118.8]
    b = [100.0, 90.0, 99.0, 79.2]
    result = compute_return_correlations({"A": a, "B": b})
    assert result.matrix[0][1] is not None
    assert result.matrix[0][1] < -0.99


def test_constant_series_yields_none_not_fake_zero() -> None:
    # A flat price series has zero variance -> correlation is undefined, and
    # must be reported as None (honest), never fabricated as 0 or 1.
    result = compute_return_correlations(
        {"FLAT": [50.0, 50.0, 50.0], "MOVES": [10.0, 12.0, 11.0]}
    )
    assert result.matrix[0][0] is None  # even the diagonal is undefined for a constant series
    assert result.matrix[0][1] is None
    assert result.matrix[1][0] is None
    assert result.matrix[1][1] == 1.0  # the varying series still has a defined self-correlation


def test_result_is_bounded_and_symmetric() -> None:
    result = compute_return_correlations(
        {
            "A": [100.0, 101.0, 103.0, 102.0, 105.0],
            "B": [200.0, 205.0, 202.0, 208.0, 210.0],
        }
    )
    r_ab = result.matrix[0][1]
    r_ba = result.matrix[1][0]
    assert r_ab is not None and -1.0 <= r_ab <= 1.0
    assert r_ab == r_ba  # correlation is symmetric


def test_empty_input_is_safe() -> None:
    result = compute_return_correlations({})
    assert result.labels == ()
    assert result.matrix == ()
    assert result.sample_size == 0
