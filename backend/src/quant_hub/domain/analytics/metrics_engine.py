# Governing specification: Doc 14 §10.3.7 — Performance Metrics (Sharpe,
#   Sortino, Max Drawdown, Calmar, Profit Factor, Expectancy, Win Rate).
# Layer: Domain — Doc 07 §Layers (pure functions, no I/O, no persistence)
# Invariants: P-13 (deterministic computation)
# Scope: handbook/KNOWN_LIMITATIONS.md F-21 (resolved by this module + a real
#   per-step equity curve, application/backtesting/engine.py)
# Per Doc 00 §14.11
#
# Every function here is a pure, deterministic transform of a real equity
# curve or realized-P&L series — no fabricated inputs, no silent defaults
# standing in for missing data. Callers (the backtest engine, the metrics
# API) decide whether there is ENOUGH data to trust a figure (e.g. the API
# requires >=30 equity-curve steps before returning a Sharpe ratio) — this
# module always computes something well-defined from whatever it is given,
# using Decimal throughout (P-13: no float rounding drift between environments).
#
# UNIT CONVENTIONS (JUDGMENT CALL, §14.5/§14.7 — flagged): fields whose
# storage column is named with a "_pct" suffix (max_drawdown_pct) are
# PERCENTAGE numbers (0-100 scale); fields without that suffix (win_rate,
# sharpe_ratio, sortino_ratio, calmar_ratio, profit_factor) are dimensionless
# ratios or 0-1 fractions. This mirrors the existing analytics.backtests
# convention (total_return is a fraction, no "_pct" suffix).
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from quant_hub.domain.analytics.entities import ComputedMetrics

_ZERO = Decimal("0")
_ONE = Decimal("1")
_HUNDRED = Decimal("100")
# Doc 14 §10.3.7 / task spec: annualize using the standard 252-trading-day
# convention. FLAGGED: this is literal per the task's explicit instruction,
# not a data-driven inference from the backtest's actual bar interval — an
# hourly-bar backtest's per-step "day" is not really a trading day, so a
# Sharpe/Sortino computed this way over sub-daily bars overstates the
# annualization factor. Recorded here rather than silently deviating from
# the requested convention.
_TRADING_DAYS_PER_YEAR = Decimal("252")


def _safe_sqrt(value: Decimal) -> Decimal:
    if value <= _ZERO:
        return _ZERO
    return value.sqrt()


def compute_return_series(equity_curve: list[Decimal]) -> list[Decimal]:
    """Step-over-step fractional returns from a real equity curve.

    r_i = (equity_i - equity_{i-1}) / equity_{i-1}. A step whose PRIOR equity
    was exactly zero contributes 0 (never a divide-by-zero) — this should not
    occur for a backtest with positive initial_capital, but a pure function
    must still be total over its input domain.
    """
    if len(equity_curve) < 2:
        return []
    returns: list[Decimal] = []
    for prev, cur in zip(equity_curve, equity_curve[1:]):
        if prev == _ZERO:
            returns.append(_ZERO)
        else:
            returns.append((cur - prev) / prev)
    return returns


def _mean(values: list[Decimal]) -> Decimal:
    return sum(values, _ZERO) / Decimal(len(values)) if values else _ZERO


def _population_stdev(values: list[Decimal], mean: Decimal) -> Decimal:
    if len(values) < 1:
        return _ZERO
    variance = sum(((v - mean) ** 2 for v in values), _ZERO) / Decimal(len(values))
    return _safe_sqrt(variance)


def compute_sharpe(returns: list[Decimal], risk_free: Decimal = _ZERO) -> Decimal:
    """Annualized Sharpe ratio — mean excess return / stdev of returns,
    scaled by sqrt(252). Returns 0 (not a ZeroDivisionError) when there are
    fewer than 2 returns or the return series has zero variance (e.g. every
    step returned exactly the risk-free rate) — a flat series has no
    meaningful risk-adjusted figure, and 0 is the honest "undefined ->
    neutral" value rather than raising.
    """
    if len(returns) < 2:
        return _ZERO
    excess = [r - risk_free for r in returns]
    mean_excess = _mean(excess)
    stdev = _population_stdev(excess, mean_excess)
    if stdev == _ZERO:
        return _ZERO
    return (mean_excess / stdev) * _safe_sqrt(_TRADING_DAYS_PER_YEAR)


def compute_sortino(returns: list[Decimal], risk_free: Decimal = _ZERO) -> Decimal:
    """Annualized Sortino ratio — mean excess return / downside deviation.

    Downside deviation is computed over ALL periods (standard Sortino
    definition: upside periods contribute 0 to the downside sum, not
    excluded from the denominator's period count). Returns 0 when there are
    fewer than 2 returns or no downside deviation exists (e.g. every return
    was >= the risk-free rate) — never a divide-by-zero.
    """
    if len(returns) < 2:
        return _ZERO
    excess = [r - risk_free for r in returns]
    mean_excess = _mean(excess)
    downside_sq = sum((min(e, _ZERO) ** 2 for e in excess), _ZERO) / Decimal(len(excess))
    downside_dev = _safe_sqrt(downside_sq)
    if downside_dev == _ZERO:
        return _ZERO
    return (mean_excess / downside_dev) * _safe_sqrt(_TRADING_DAYS_PER_YEAR)


def compute_max_drawdown(equity_curve: list[Decimal]) -> Decimal:
    """Maximum peak-to-trough decline, as a PERCENTAGE (0-100 scale).

    Tracks a running peak; drawdown at each point is (peak - equity) / peak.
    A monotonically increasing series never falls below its running peak, so
    this returns 0 — not a fabricated small positive number. Returns 0 for
    an empty or single-point curve (no drawdown is observable with <2 points).
    """
    if len(equity_curve) < 2:
        return _ZERO
    peak = equity_curve[0]
    max_dd = _ZERO
    for value in equity_curve[1:]:
        if value > peak:
            peak = value
        elif peak > _ZERO:
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
    return max_dd * _HUNDRED


def compute_calmar(equity_curve: list[Decimal], annualized_return: Decimal) -> Decimal:
    """Calmar ratio — annualized return / max drawdown (both as fractions).

    Returns 0 when max drawdown is exactly 0 (e.g. a monotonically
    increasing equity curve) rather than an undefined/infinite ratio — a
    strategy with no drawdown has nothing to divide by, and 0 signals
    "not meaningfully computable", not "zero return".
    """
    max_dd_pct = compute_max_drawdown(equity_curve)
    if max_dd_pct == _ZERO:
        return _ZERO
    return annualized_return / (max_dd_pct / _HUNDRED)


def compute_profit_factor(wins: list[Decimal], losses: list[Decimal]) -> Decimal:
    """Gross profit / gross loss (both positive magnitudes).

    Returns Decimal('Infinity') when there are wins but no losses (a
    genuinely unbounded ratio — the honest value, not a fabricated cap) and
    0 when there are neither wins nor losses (no decided trades at all). The
    API layer renders a non-finite Decimal as an honest null (JSON has no
    Infinity literal), per the "never a fabricated number" mandate.
    """
    gross_win = sum(wins, _ZERO)
    gross_loss = abs(sum(losses, _ZERO))
    if gross_loss == _ZERO:
        return Decimal("Infinity") if gross_win > _ZERO else _ZERO
    return gross_win / gross_loss


def compute_expectancy(wins: list[Decimal], losses: list[Decimal], win_rate: Decimal) -> Decimal:
    """Expected P&L per trade — E = win_rate*avg_win - (1-win_rate)*avg_loss.

    `avg_win`/`avg_loss` (magnitude) default to 0 when their side of the
    trade history is empty, so an all-wins or all-losses series still
    produces a defined figure rather than raising.
    """
    avg_win = sum(wins, _ZERO) / Decimal(len(wins)) if wins else _ZERO
    avg_loss = abs(sum(losses, _ZERO)) / Decimal(len(losses)) if losses else _ZERO
    return win_rate * avg_win - (_ONE - win_rate) * avg_loss


def compute_win_rate(realized_pnl_list: list[Decimal]) -> Decimal:
    """Fraction (0-1) of DECIDED trades (nonzero realized P&L) that were
    wins. A fill with exactly 0 realized P&L (a pure open/add — no existing
    position closed) carries no win/loss verdict and is excluded from both
    the numerator and denominator, matching the Execution page's
    computeTradeRatio convention (frontend/src/features/execution/analytics.ts).
    Returns 0 when there are no decided trades at all.
    """
    wins = [p for p in realized_pnl_list if p > _ZERO]
    losses = [p for p in realized_pnl_list if p < _ZERO]
    decided = len(wins) + len(losses)
    if decided == 0:
        return _ZERO
    return Decimal(len(wins)) / Decimal(decided)


def compute_annualized_return(total_return: Decimal, num_periods: int) -> Decimal:
    """Annualizes a whole-period return using the same 252-trading-day
    convention as Sharpe/Sortino (same literal-per-spec caveat applies).
    Returns `total_return` unchanged when there are no periods to annualize
    over. A total_return <= -100% has no real-valued annualized equivalent
    (the compounding base would be <= 0) — returns -1 (total loss) as the
    honest floor rather than raising or fabricating a number.

    Uses float exponentiation for the fractional power (Decimal has no
    fractional-exponent **) — acceptable here since this is a display
    estimate, not part of the deterministic trade replay P-13 governs.
    """
    if num_periods <= 0:
        return total_return
    base = float(_ONE + total_return)
    if base <= 0.0:
        return Decimal("-1")
    annualized = base ** (float(_TRADING_DAYS_PER_YEAR) / num_periods) - 1.0
    return Decimal(str(annualized))


# Doc 14 §10.3.7 / task spec 1D: Sharpe/Sortino/Calmar need a meaningful
# sample — the API's own instruction ("need at least 30 steps for Sharpe").
_MIN_STEPS_FOR_RATIO_METRICS = 30


def compute_all_metrics(
    backtest_run_id: UUID,
    equity_curve: list[Decimal],
    trade_pnls: list[Decimal],
) -> ComputedMetrics:
    """Orchestrates the full Doc 14 §10.3.7 metric suite for one backtest
    run, applying the "insufficient data -> honest None" gate on top of the
    pure compute_* functions above (which are total over their input domain
    and return a defined 0 for a degenerate case a caller must still
    interpret — this function is that interpreter).

    `equity_curve` is the FULL per-step portfolio_value series, INCLUDING
    the step-0 baseline. `trade_pnls` is the list of realized P&L deltas
    from closing events during this run (steps with zero delta excluded
    already by the caller).
    """
    returns = compute_return_series(equity_curve)
    wins = [p for p in trade_pnls if p > _ZERO]
    losses = [p for p in trade_pnls if p < _ZERO]
    decided = len(wins) + len(losses)

    win_rate = compute_win_rate(trade_pnls) if decided > 0 else None
    max_drawdown_pct = compute_max_drawdown(equity_curve) if len(equity_curve) >= 2 else None

    has_enough_steps = len(returns) >= _MIN_STEPS_FOR_RATIO_METRICS
    sharpe_ratio = compute_sharpe(returns) if has_enough_steps else None
    sortino_ratio = compute_sortino(returns) if has_enough_steps else None

    calmar_ratio = None
    if has_enough_steps and max_drawdown_pct is not None and equity_curve[0] != _ZERO:
        total_return = (equity_curve[-1] - equity_curve[0]) / equity_curve[0]
        annualized_return = compute_annualized_return(total_return, len(returns))
        calmar_ratio = compute_calmar(equity_curve, annualized_return)

    profit_factor = compute_profit_factor(wins, losses) if decided > 0 else None
    expectancy_per_trade = (
        compute_expectancy(wins, losses, win_rate) if decided > 0 and win_rate is not None else None
    )

    return ComputedMetrics(
        backtest_run_id=backtest_run_id,
        win_rate=win_rate,
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
        max_drawdown_pct=max_drawdown_pct,
        calmar_ratio=calmar_ratio,
        profit_factor=profit_factor,
        expectancy_per_trade=expectancy_per_trade,
    )
