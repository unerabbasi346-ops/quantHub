# Governing specification: Doc 15 §11.3.4 (Risk-Based Sizing), Doc 14 §10.9.3
#   (Trade Lifecycle — TP/SL as the exit condition), §10.3.5 (Execution
#   Simulation). Per Doc 00 §14.11
#
# Engine step "TP/SL, one-trade rule, 2%/3% sizing, benchmark": pure,
# deterministic (P-13) functions the backtest engine calls per bar. No I/O,
# no repository access — every input is a value already in hand from the
# engine's own loop (bars it already fetched, a signal it already has).
from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal

from quant_hub.domain.market_data.entities import OHLCVBar

_BASE_PCT = Decimal("0.02")            # Rule 1: default 2% of capital
_HIGH_CONFIDENCE_PCT = Decimal("0.03")  # Rule 1: 3% when ml_confidence > threshold
_CONFIDENCE_THRESHOLD = Decimal("0.70")
_ATR_PERIOD = 14
_ATR_SL_MULTIPLE = Decimal("2")   # Rule 3 fallback: SL = entry - 2*ATR14
_ATR_TP_MULTIPLE = Decimal("3")   # Rule 3 fallback: TP = entry + 3*ATR14


def compute_position_size(capital: Decimal, ml_confidence: Decimal | None, leverage: Decimal) -> Decimal:
    """Rule 1 — 2%/3% risk sizing.

    Default 2% of `capital`; 3% when `ml_confidence` is supplied and > 0.70.
    NEVER exceeds 3% regardless of how high confidence is (the cap is a
    fixed pct choice, not a scaling function of confidence). Leverage
    multiplies the resulting notional (default 1x — no leverage). Returns
    the magnitude (unsigned) notional; the caller applies trade direction.
    """
    pct = _HIGH_CONFIDENCE_PCT if (ml_confidence is not None and ml_confidence > _CONFIDENCE_THRESHOLD) else _BASE_PCT
    return capital * pct * leverage


def compute_atr14(bars: Sequence[OHLCVBar]) -> Decimal:
    """14-period Average True Range from real bar data (Rule 3 fallback).

    True Range for bar i (i>0) = max(high-low, |high-prev_close|,
    |low-prev_close|) — the standard Wilder ATR definition. Uses the
    trailing `_ATR_PERIOD` true-range values (needs `_ATR_PERIOD`+1 bars,
    oldest->newest, to get `_ATR_PERIOD` TRs). Returns 0 when there isn't
    enough history — an honest "can't compute yet", never a fabricated value.
    """
    if len(bars) < _ATR_PERIOD + 1:
        return Decimal("0")
    window = bars[-(_ATR_PERIOD + 1):]
    true_ranges = []
    for i in range(1, len(window)):
        high, low, prev_close = window[i].high, window[i].low, window[i - 1].close
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        true_ranges.append(tr)
    return sum(true_ranges, Decimal("0")) / Decimal(len(true_ranges))


def compute_tp_sl(
    entry_price: Decimal,
    direction: int,
    metadata: Mapping[str, str],
    bars: Sequence[OHLCVBar],
) -> tuple[Decimal, Decimal]:
    """Rule 3 — TP/SL for a new trade, in P&L-favorable order (tp, sl).

    Prefers `ml_tp_suggestion`/`ml_sl_suggestion` from the signal's own
    metadata (P-1 opaque space — a strategy or upstream enrichment may stash
    these there) when BOTH parse as real Decimals. Falls back to the ATR14
    formula (SL = entry - 2*ATR, TP = entry + 3*ATR for a long; mirrored for
    a short) when they're absent or unparseable. `direction` is the trade's
    sign: 1 for long, -1 for short — TP/SL sit on opposite sides depending
    on which way the trade profits.
    """
    raw_tp = metadata.get("ml_tp_suggestion")
    raw_sl = metadata.get("ml_sl_suggestion")
    if raw_tp is not None and raw_sl is not None:
        try:
            return Decimal(raw_tp), Decimal(raw_sl)
        except (ValueError, ArithmeticError):
            pass  # fall through to ATR — an unparseable metadata value is not fatal

    atr = compute_atr14(bars)
    if direction >= 0:
        return entry_price + _ATR_TP_MULTIPLE * atr, entry_price - _ATR_SL_MULTIPLE * atr
    return entry_price - _ATR_TP_MULTIPLE * atr, entry_price + _ATR_SL_MULTIPLE * atr


def compute_benchmark_return(benchmark_bars: Sequence[OHLCVBar]) -> Decimal | None:
    """Rule 5 — buy-and-hold return of a benchmark instrument's bars over
    the backtest's own [start, end] window: (last.close - first.close) /
    first.close. None when fewer than 2 bars exist for the period (nothing
    to compute a return from) — never fabricated.
    """
    if len(benchmark_bars) < 2:
        return None
    first_close = benchmark_bars[0].close
    if first_close == 0:
        return None
    return (benchmark_bars[-1].close - first_close) / first_close


def compute_trade_return_pcts(entry_price: Decimal, exit_price: Decimal, direction: int) -> tuple[Decimal, Decimal]:
    """Rule 4 — (price_return_pct, market_move_pct).

    price_return_pct is signed to match trade direction (positive = the
    trade profited); market_move_pct is the same underlying price move,
    unsigned. Both 0 if entry_price is 0 (never divide by zero).
    """
    if entry_price == 0:
        return Decimal("0"), Decimal("0")
    raw_pct = (exit_price - entry_price) / entry_price * Decimal("100")
    return raw_pct * Decimal(direction), abs(raw_pct)
