# Governing specification: domain/backtesting/trade_rules.py — Engine step
# "TP/SL, one-trade rule, 2%/3% sizing, benchmark". Per Doc 00 §14.11
#
# Pure-function tests for Rules 1 (sizing), 3 (ATR/TP-SL), 4 (return pcts),
# and 5 (benchmark) — no engine, no DB, no fakes needed.
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from quant_hub.domain.backtesting.trade_rules import (
    compute_atr14,
    compute_benchmark_return,
    compute_position_size,
    compute_tp_sl,
    compute_trade_return_pcts,
)
from quant_hub.domain.market_data.entities import OHLCVBar

_T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _bar(i: int, close: float, high: float | None = None, low: float | None = None) -> OHLCVBar:
    c = Decimal(str(close))
    return OHLCVBar(
        asset_id=uuid4(), interval="1h", ts=_T0 + timedelta(hours=i),
        open=c, high=Decimal(str(high)) if high is not None else c,
        low=Decimal(str(low)) if low is not None else c, close=c, volume=Decimal("1"),
    )


# ── Rule 1: 2%/3% sizing ────────────────────────────────────────────────────

def test_default_sizing_is_2_percent():
    size = compute_position_size(Decimal("100000"), None, Decimal("1"))
    assert size == Decimal("2000")  # 2% of 100000


def test_high_confidence_sizing_is_3_percent():
    size = compute_position_size(Decimal("100000"), Decimal("0.71"), Decimal("1"))
    assert size == Decimal("3000")  # 3% of 100000


def test_confidence_exactly_at_threshold_stays_2_percent():
    # Rule 1 says "> 0.70", not ">=" — the boundary itself does not upgrade.
    size = compute_position_size(Decimal("100000"), Decimal("0.70"), Decimal("1"))
    assert size == Decimal("2000")


def test_sizing_never_exceeds_3_percent_regardless_of_confidence():
    size = compute_position_size(Decimal("100000"), Decimal("0.99"), Decimal("1"))
    assert size == Decimal("3000")  # not 99%, capped exactly at 3%


def test_sizing_applies_leverage():
    size = compute_position_size(Decimal("100000"), None, Decimal("5"))
    assert size == Decimal("10000")  # 2% * 5x leverage


def test_sizing_low_confidence_stays_2_percent():
    size = compute_position_size(Decimal("100000"), Decimal("0.40"), Decimal("1"))
    assert size == Decimal("2000")


# ── Rule 3: ATR14 ────────────────────────────────────────────────────────────

def test_atr14_known_constant_true_range():
    # closes step by 2 every bar, high=low=close -> TR_i = |close_i - close_{i-1}| = 2 always.
    bars = [_bar(i, 100 + 2 * i) for i in range(16)]
    assert compute_atr14(bars) == Decimal("2")


def test_atr14_insufficient_history_is_zero():
    bars = [_bar(i, 100 + i) for i in range(5)]  # < 15 bars
    assert compute_atr14(bars) == Decimal("0")


# ── Rule 3: TP/SL ────────────────────────────────────────────────────────────

def test_tp_sl_prefers_metadata_when_present():
    bars = [_bar(i, 100 + 2 * i) for i in range(16)]
    metadata = {"ml_tp_suggestion": "150.00", "ml_sl_suggestion": "90.00"}
    tp, sl = compute_tp_sl(Decimal("100"), 1, metadata, bars)
    assert tp == Decimal("150.00")
    assert sl == Decimal("90.00")


def test_tp_sl_atr_fallback_long():
    bars = [_bar(i, 100 + 2 * i) for i in range(16)]  # ATR14 = 2
    tp, sl = compute_tp_sl(Decimal("100"), 1, {}, bars)
    assert tp == Decimal("106")  # entry + 3*ATR
    assert sl == Decimal("96")   # entry - 2*ATR


def test_tp_sl_atr_fallback_short():
    bars = [_bar(i, 100 + 2 * i) for i in range(16)]  # ATR14 = 2
    tp, sl = compute_tp_sl(Decimal("100"), -1, {}, bars)
    assert tp == Decimal("94")   # entry - 3*ATR (short profits on a drop)
    assert sl == Decimal("104")  # entry + 2*ATR


def test_tp_sl_unparseable_metadata_falls_back_to_atr():
    bars = [_bar(i, 100 + 2 * i) for i in range(16)]
    tp, sl = compute_tp_sl(Decimal("100"), 1, {"ml_tp_suggestion": "not-a-number", "ml_sl_suggestion": "90"}, bars)
    assert tp == Decimal("106")  # ATR fallback, not a crash


# ── Rule 4: per-trade return tracking ───────────────────────────────────────

def test_return_pcts_long_profit():
    price_return, market_move = compute_trade_return_pcts(Decimal("100"), Decimal("110"), 1)
    assert price_return == Decimal("10")
    assert market_move == Decimal("10")


def test_return_pcts_long_loss():
    price_return, market_move = compute_trade_return_pcts(Decimal("100"), Decimal("90"), 1)
    assert price_return == Decimal("-10")
    assert market_move == Decimal("10")  # unsigned


def test_return_pcts_short_profit_on_price_drop():
    # Price fell 10% — a SHORT profits, so price_return_pct must be POSITIVE
    # even though the raw price move is negative (sign matches direction).
    price_return, market_move = compute_trade_return_pcts(Decimal("100"), Decimal("90"), -1)
    assert price_return == Decimal("10")
    assert market_move == Decimal("10")


def test_return_pcts_short_loss_on_price_rise():
    price_return, market_move = compute_trade_return_pcts(Decimal("100"), Decimal("110"), -1)
    assert price_return == Decimal("-10")
    assert market_move == Decimal("10")


# ── Rule 5: benchmark ────────────────────────────────────────────────────────

def test_benchmark_return_buy_and_hold():
    bars = [_bar(0, 20000), _bar(1, 21000), _bar(2, 22000)]  # first->last
    ret = compute_benchmark_return(bars)
    assert ret == (Decimal("22000") - Decimal("20000")) / Decimal("20000")


def test_benchmark_return_none_when_insufficient_bars():
    assert compute_benchmark_return([_bar(0, 20000)]) is None
    assert compute_benchmark_return([]) is None
