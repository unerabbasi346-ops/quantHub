# Governing specification: Doc 14 §10.3.7 — Performance Metrics. F-21.
# Per Doc 00 §14.11
#
# Hand-verified expected outputs for every pure function in
# domain/analytics/metrics_engine.py, plus the edge cases the task spec
# calls out explicitly (empty series, all wins, all losses, single step,
# zero-variance Sharpe, monotonically increasing max drawdown).
from __future__ import annotations

import math
from decimal import Decimal

from uuid import uuid4

from quant_hub.domain.analytics.metrics_engine import (
    compute_all_metrics,
    compute_annualized_return,
    compute_calmar,
    compute_expectancy,
    compute_max_drawdown,
    compute_profit_factor,
    compute_return_series,
    compute_sharpe,
    compute_sortino,
    compute_win_rate,
)


def D(v):
    return Decimal(str(v))


# ── compute_return_series ───────────────────────────────────────────────────

def test_return_series_hand_verified():
    series = compute_return_series([D(100), D(110), D(99)])
    assert series == [D("0.1"), D("-0.1")]


def test_return_series_empty_and_single_point():
    assert compute_return_series([]) == []
    assert compute_return_series([D(100)]) == []


def test_return_series_prior_zero_never_divides_by_zero():
    assert compute_return_series([D(0), D(50)]) == [D(0)]


# ── compute_sharpe ───────────────────────────────────────────────────────────

def test_sharpe_hand_verified():
    returns = [D("0.02"), D("0.01")]
    result = compute_sharpe(returns)
    expected = 3 * math.sqrt(252)  # mean=0.015, stdev=0.005, mean/stdev=3
    assert abs(float(result) - expected) < 1e-6


def test_sharpe_zero_variance_returns_zero_not_error():
    returns = [D("0.02"), D("0.02"), D("0.02")]
    assert compute_sharpe(returns) == D(0)


def test_sharpe_insufficient_data_returns_zero():
    assert compute_sharpe([]) == D(0)
    assert compute_sharpe([D("0.01")]) == D(0)


# ── compute_sortino ──────────────────────────────────────────────────────────

def test_sortino_hand_verified():
    returns = [D("0.02"), D("-0.01"), D("0.03"), D("-0.02")]
    result = compute_sortino(returns)
    # mean=0.005; downside sq = (0^2 + 0.01^2 + 0^2 + 0.02^2)/4 = 0.000125
    # downside_dev = sqrt(0.000125); sortino = (0.005/downside_dev)*sqrt(252)
    downside_dev = math.sqrt(0.000125)
    expected = (0.005 / downside_dev) * math.sqrt(252)
    assert abs(float(result) - expected) < 1e-4


def test_sortino_no_downside_returns_zero():
    returns = [D("0.01"), D("0.02"), D("0.03")]
    assert compute_sortino(returns) == D(0)


def test_sortino_insufficient_data_returns_zero():
    assert compute_sortino([]) == D(0)


# ── compute_max_drawdown ─────────────────────────────────────────────────────

def test_max_drawdown_hand_verified():
    equity = [D(100), D(120), D(90), D(110), D(80), D(130)]
    # peak sequence: 100 -> 120 -> (dd 25%) -> (dd 8.33%) -> (dd 33.33%) -> 130
    result = compute_max_drawdown(equity)
    assert abs(float(result) - 100 / 3) < 1e-6


def test_max_drawdown_monotonically_increasing_is_zero():
    equity = [D(100), D(110), D(120), D(130)]
    assert compute_max_drawdown(equity) == D(0)


def test_max_drawdown_empty_and_single_point():
    assert compute_max_drawdown([]) == D(0)
    assert compute_max_drawdown([D(100)]) == D(0)


# ── compute_calmar ───────────────────────────────────────────────────────────

def test_calmar_hand_verified():
    equity = [D(100), D(200), D(100)]  # exact 50% drawdown
    result = compute_calmar(equity, D("0.25"))
    assert result == D("0.5")


def test_calmar_zero_drawdown_returns_zero():
    equity = [D(100), D(150), D(200), D(300)]
    assert compute_calmar(equity, D("0.4")) == D(0)


# ── compute_profit_factor ────────────────────────────────────────────────────

def test_profit_factor_hand_verified():
    wins = [D(10), D(20), D(30)]
    losses = [D(-5), D(-15)]
    assert compute_profit_factor(wins, losses) == D(3)


def test_profit_factor_all_wins_is_infinite():
    result = compute_profit_factor([D(10), D(20)], [])
    assert result == Decimal("Infinity")


def test_profit_factor_all_losses_is_zero():
    result = compute_profit_factor([], [D(-10), D(-20)])
    assert result == D(0)


def test_profit_factor_no_trades_is_zero():
    assert compute_profit_factor([], []) == D(0)


# ── compute_expectancy ───────────────────────────────────────────────────────

def test_expectancy_hand_verified():
    wins = [D(100), D(50)]
    losses = [D(-30), D(-20), D(-10)]
    win_rate = D("0.4")
    # avg_win=75, avg_loss=20; E = 0.4*75 - 0.6*20 = 30 - 12 = 18
    assert compute_expectancy(wins, losses, win_rate) == D(18)


def test_expectancy_all_wins():
    wins = [D(10), D(20)]
    assert compute_expectancy(wins, [], D("1")) == D(15)  # 1*15 - 0*0


def test_expectancy_all_losses():
    losses = [D(-10), D(-20)]
    assert compute_expectancy([], losses, D("0")) == D(-15)  # 0*0 - 1*15


# ── compute_win_rate ─────────────────────────────────────────────────────────

def test_win_rate_hand_verified():
    pnl = [D(10), D(-5), D(0), D(20), D(-15), D(0)]
    assert compute_win_rate(pnl) == D("0.5")


def test_win_rate_all_wins():
    assert compute_win_rate([D(10), D(20), D(30)]) == D(1)


def test_win_rate_all_losses():
    assert compute_win_rate([D(-10), D(-20)]) == D(0)


def test_win_rate_no_decided_trades_is_zero():
    assert compute_win_rate([]) == D(0)
    assert compute_win_rate([D(0), D(0)]) == D(0)


# ── compute_annualized_return ────────────────────────────────────────────────

def test_annualized_return_hand_verified():
    # 10% over 126 periods (half a "year" of 252) -> annualize by squaring
    # the compounding factor: (1.10)^2 - 1 = 0.21
    result = compute_annualized_return(D("0.10"), 126)
    assert abs(float(result) - 0.21) < 1e-9


def test_annualized_return_no_periods_returns_total_unchanged():
    assert compute_annualized_return(D("0.15"), 0) == D("0.15")


def test_annualized_return_total_loss_floors_at_negative_one():
    assert compute_annualized_return(D("-1.5"), 50) == D("-1")


# ── compute_all_metrics (orchestration + insufficient-data gating) ──────────

def test_all_metrics_insufficient_steps_nulls_ratio_metrics():
    # Only 5 steps (< 30) -> sharpe/sortino/calmar must be None, but
    # win_rate/max_drawdown/profit_factor/expectancy (which don't need 30
    # steps) are still real computed numbers.
    equity = [D(100), D(105), D(103), D(108), D(110), D(107)]
    trade_pnls = [D(5), D(-2)]
    metrics = compute_all_metrics(uuid4(), equity, trade_pnls)
    assert metrics.sharpe_ratio is None
    assert metrics.sortino_ratio is None
    assert metrics.calmar_ratio is None
    assert metrics.win_rate == D("0.5")
    assert metrics.max_drawdown_pct is not None
    assert metrics.profit_factor == D("2.5")
    assert metrics.expectancy_per_trade is not None


def test_all_metrics_no_trades_nulls_trade_dependent_metrics():
    equity = [D(100)] + [D(100 + i) for i in range(35)]
    metrics = compute_all_metrics(uuid4(), equity, [])
    assert metrics.win_rate is None
    assert metrics.profit_factor is None
    assert metrics.expectancy_per_trade is None
    # 36 equity points -> 35 returns, >= 30 -> ratio metrics ARE computed
    assert metrics.sharpe_ratio is not None
    assert metrics.max_drawdown_pct is not None


def test_all_metrics_enough_steps_computes_ratios():
    equity = [D(100)] + [D(100) + D(i) * D("0.3") for i in range(1, 31)]
    trade_pnls = [D(3), D(-1), D(2)]
    metrics = compute_all_metrics(uuid4(), equity, trade_pnls)
    assert metrics.sharpe_ratio is not None
    assert metrics.sortino_ratio is not None
    assert metrics.win_rate == D(2) / D(3)
