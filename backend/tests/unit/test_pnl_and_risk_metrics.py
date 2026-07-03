# Governing specification: Doc 14 §10.9.5 (P&L Calculation), Doc 15 §11.5.3
#   (Risk Measurement); Port-3 / P-13 (determinism)
# Per Doc 00 §14.11
#
# Pure-computation tests for Step 3.6: realized/unrealized P&L (extending the
# position math) and the PositionExposureRiskModel. The real
# analytics.risk_snapshots write is exercised in the live verification.
from __future__ import annotations

from decimal import Decimal
from uuid import uuid4, uuid7

import pytest

from quant_hub.domain.portfolio.positions import RecordedPosition, apply_fill_to_position
from quant_hub.infrastructure.risk_model import PositionExposureRiskModel
from quant_hub.infrastructure.risk_model_stub import StubRiskModel

_PID = uuid4()


def _pos(qty: str, avg: str, market_value: str, last: str) -> RecordedPosition:
    return RecordedPosition(
        id=uuid7(), portfolio_id=_PID, asset_id=uuid4(),
        quantity=Decimal(qty), average_entry_price=Decimal(avg),
        market_value=Decimal(market_value), unrealized_pnl=Decimal("0"),
        realized_pnl_today=Decimal("0"), last_price=Decimal(last),
        is_closed=False, sequence_number=1,
    )


# ── Realized / unrealized P&L (§10.9.5) ─────────────────────────────────────

def test_open_has_no_realized_pnl_and_zero_unrealized_at_fill() -> None:
    u = apply_fill_to_position(Decimal("0"), Decimal("0"), Decimal("0.05"), Decimal("61000"))
    assert u.realized_pnl == Decimal("0.0000")
    assert u.unrealized_pnl == Decimal("0.0000")  # marked at the fill price


def test_partial_close_of_long_realizes_gain() -> None:
    # long 0.10 @ 60000, sell 0.04 @ 63000
    u = apply_fill_to_position(Decimal("0.10"), Decimal("60000"), Decimal("-0.04"), Decimal("63000"))
    assert u.realized_pnl == Decimal("1200.0000") / Decimal("10")  # (63000-60000)*0.04 = 120
    assert u.realized_pnl == Decimal("120.0000")
    # remaining 0.06 @ 60000 marked at 63000 -> (63000-60000)*0.06 = 180
    assert u.unrealized_pnl == Decimal("180.0000")
    assert u.average_entry_price == Decimal("60000.00000000")


def test_full_close_realizes_whole_pnl_and_flattens() -> None:
    u = apply_fill_to_position(Decimal("0.10"), Decimal("60000"), Decimal("-0.10"), Decimal("63000"))
    assert u.realized_pnl == Decimal("300.0000")   # (63000-60000)*0.10
    assert u.unrealized_pnl == Decimal("0.0000")   # flat
    assert u.is_closed is True


def test_closing_a_short_realizes_correct_sign() -> None:
    # short 0.10 @ 61000, buy 0.04 @ 60000 -> gain (bought back cheaper)
    u = apply_fill_to_position(Decimal("-0.10"), Decimal("61000"), Decimal("0.04"), Decimal("60000"))
    assert u.realized_pnl == Decimal("40.0000")    # (61000-60000)*0.04
    assert u.quantity == Decimal("-0.06000000")


def test_cross_zero_realizes_on_closed_leg_only() -> None:
    # long 0.05 @ 60000, sell 0.08 @ 63000 -> close 0.05 (realize), open short 0.03 @ 63000
    u = apply_fill_to_position(Decimal("0.05"), Decimal("60000"), Decimal("-0.08"), Decimal("63000"))
    assert u.realized_pnl == Decimal("150.0000")   # (63000-60000)*0.05
    assert u.quantity == Decimal("-0.03000000")
    assert u.average_entry_price == Decimal("63000.00000000")


# ── PositionExposureRiskModel (§11.5.3) ─────────────────────────────────────

@pytest.mark.asyncio
async def test_exposure_and_leverage_from_long_positions() -> None:
    model = PositionExposureRiskModel()
    positions = [_pos("0.05", "60000", "3050", "61000"), _pos("1", "100", "100", "100")]
    m = await model.compute_metrics(_PID, positions, Decimal("100000"))
    assert m.gross_exposure == Decimal("3150")     # 3050 + 100
    assert m.net_exposure == Decimal("3150")       # both long
    assert m.gross_leverage == Decimal("3150") / Decimal("100000")
    assert m.net_leverage == m.gross_leverage


@pytest.mark.asyncio
async def test_net_vs_gross_exposure_with_a_short() -> None:
    model = PositionExposureRiskModel()
    positions = [_pos("0.05", "60000", "3000", "60000"), _pos("-0.02", "60000", "-1200", "60000")]
    m = await model.compute_metrics(_PID, positions, Decimal("100000"))
    assert m.gross_exposure == Decimal("4200")     # |3000| + |−1200|
    assert m.net_exposure == Decimal("1800")       # 3000 + (−1200)


@pytest.mark.asyncio
async def test_deferred_metrics_are_zero_not_faked() -> None:
    model = PositionExposureRiskModel()
    m = await model.compute_metrics(_PID, [_pos("0.05", "60000", "3050", "61000")], Decimal("100000"))
    assert m.var_1d_99 == Decimal("0")
    assert m.cvar_1d_99 == Decimal("0")
    assert m.volatility_annualized == Decimal("0")
    assert m.max_drawdown == Decimal("0")
    assert m.beta == Decimal("0")


@pytest.mark.asyncio
async def test_zero_equity_yields_zero_leverage_not_divide_error() -> None:
    model = PositionExposureRiskModel()
    m = await model.compute_metrics(_PID, [_pos("0.05", "60000", "3050", "61000")], Decimal("0"))
    assert m.gross_exposure == Decimal("3050")     # exposure still computed
    assert m.gross_leverage == Decimal("0")        # leverage undefined -> 0


@pytest.mark.asyncio
async def test_empty_portfolio_is_all_zero() -> None:
    model = PositionExposureRiskModel()
    m = await model.compute_metrics(_PID, [], Decimal("100000"))
    assert m.gross_exposure == Decimal("0") and m.net_exposure == Decimal("0")


@pytest.mark.asyncio
async def test_stub_model_still_all_zero_for_tests() -> None:
    m = await StubRiskModel().compute_metrics(_PID, [], Decimal("100000"))
    assert m.gross_exposure == Decimal("0") and m.gross_leverage == Decimal("0")
