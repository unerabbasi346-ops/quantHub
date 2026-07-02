# Governing specification: Doc 14 §10.6.5 — Order Generation ("Order Quantity"); P-13
# Per Doc 00 §14.11
#
# No database — pure computation on domain/execution/order_generation.py +
# its value objects. The persistence write (SQLAlchemyOrderRepository.create)
# and the service's asset resolution / key minting are exercised in the
# integration + live verification, not here.
from __future__ import annotations

import dataclasses
from decimal import Decimal
from uuid import uuid4, uuid7

import pytest

from quant_hub.domain.execution.entities import (
    CurrentPosition,
    OrderSide,
    OrderType,
    TargetPosition,
    TimeInForce,
)
from quant_hub.domain.execution.order_generation import compute_order_intent
from quant_hub.domain.market_data.entities import AssetRef

_ASSET = AssetRef(symbol="BTC/USDT", exchange="binance", asset_class="crypto")


def _target(weight: str, price: str, pv: str = "100000") -> TargetPosition:
    return TargetPosition(
        asset=_ASSET,
        target_weight=Decimal(weight),
        portfolio_value=Decimal(pv),
        reference_price=Decimal(price),
    )


def _current(qty: str) -> CurrentPosition:
    return CurrentPosition(asset=_ASSET, quantity=Decimal(qty))


def _compute(target: TargetPosition, current: CurrentPosition, *, min_quantity: str = "0"):
    return compute_order_intent(
        target=target,
        current=current,
        portfolio_id=uuid4(),
        strategy_id=uuid4(),
        signal_id=uuid4(),
        idempotency_key=uuid7(),
        min_quantity=Decimal(min_quantity),
    )


# ── Derived target arithmetic (§10.6.5 Order Quantity) ──────────────────────

def test_target_notional_and_quantity_are_derived() -> None:
    target = _target("0.05", "60000", pv="100000")
    assert target.target_notional == Decimal("5000.00")
    # 5000 / 60000 = 0.08333... (unrounded on the value object)
    assert target.target_quantity == Decimal("5000.00") / Decimal("60000")


# ── Flat -> BUY (the live-demo case) ────────────────────────────────────────

def test_flat_position_produces_buy_for_positive_target() -> None:
    order = _compute(_target("0.05", "60000"), _current("0"))
    assert order is not None
    assert order.side is OrderSide.BUY
    assert order.quantity == Decimal("0.08333333")  # ROUND_DOWN to 8 dp
    assert order.delta_quantity == Decimal("0.08333333")
    assert order.current_quantity == Decimal("0")
    assert order.order_type is OrderType.MARKET
    assert order.time_in_force is TimeInForce.DAY


def test_negative_target_from_flat_produces_sell() -> None:
    order = _compute(_target("-0.05", "60000"), _current("0"))
    assert order is not None
    assert order.side is OrderSide.SELL
    assert order.quantity == Decimal("0.08333333")


# ── Rebalance against an existing position (delta, §10.6.5) ──────────────────

def test_increase_existing_long_buys_the_delta() -> None:
    # target 0.08333333, hold 0.05 -> BUY 0.03333333
    order = _compute(_target("0.05", "60000"), _current("0.05"))
    assert order is not None
    assert order.side is OrderSide.BUY
    assert order.quantity == Decimal("0.03333333")


def test_reduce_existing_long_sells_the_delta() -> None:
    # target 0.08333333, hold 0.10 -> SELL 0.01666667
    order = _compute(_target("0.05", "60000"), _current("0.10"))
    assert order is not None
    assert order.side is OrderSide.SELL
    assert order.quantity == Decimal("0.01666667")


def test_cross_zero_produces_single_net_order() -> None:
    # target long 0.08333333, currently short -0.02 -> BUY 0.10333333 (net, no split)
    order = _compute(_target("0.05", "60000"), _current("-0.02"))
    assert order is not None
    assert order.side is OrderSide.BUY
    assert order.quantity == Decimal("0.10333333")


# ── No-op when already at target ────────────────────────────────────────────

def test_exact_target_is_a_noop() -> None:
    # quantized target is 0.08333333; holding exactly that -> None
    assert _compute(_target("0.05", "60000"), _current("0.08333333")) is None


def test_within_min_quantity_is_a_noop() -> None:
    # delta 0.00000001 <= min_quantity 0.0001 -> suppressed
    order = _compute(
        _target("0.05", "60000"), _current("0.08333332"), min_quantity="0.0001"
    )
    assert order is None


def test_delta_above_min_quantity_still_orders() -> None:
    order = _compute(
        _target("0.05", "60000"), _current("0.05"), min_quantity="0.0001"
    )
    assert order is not None
    assert order.quantity == Decimal("0.03333333")


# ── Quantization (ROUND_DOWN, never overshoot) ──────────────────────────────

def test_quantity_is_round_down_to_eight_dp() -> None:
    # 1/3 -> 0.33333333 (truncated, not 0.33333334)
    order = _compute(_target("0.30000000", "300000", pv="1000000"), _current("0"))
    # notional 300000, price 300000 -> 1.0 exactly
    assert order is not None and order.quantity == Decimal("1.00000000")
    # a non-terminating case: notional 100000 / price 3 = 33333.333...
    order2 = _compute(_target("1", "3", pv="100000"), _current("0"))
    assert order2 is not None
    assert order2.quantity == Decimal("33333.33333333")


# ── Determinism (P-13) ──────────────────────────────────────────────────────

def test_deterministic_given_same_key() -> None:
    key = uuid7()
    pid, sid, sig = uuid4(), uuid4(), uuid4()
    kwargs = dict(
        target=_target("0.05", "60000"),
        current=_current("0.01"),
        portfolio_id=pid,
        strategy_id=sid,
        signal_id=sig,
        idempotency_key=key,
        min_quantity=Decimal("0"),
    )
    assert compute_order_intent(**kwargs) == compute_order_intent(**kwargs)


# ── Validation guards ───────────────────────────────────────────────────────

def test_non_positive_price_rejected() -> None:
    with pytest.raises(ValueError, match="reference_price"):
        _compute(_target("0.05", "0"), _current("0"))


def test_negative_min_quantity_rejected() -> None:
    with pytest.raises(ValueError, match="min_quantity"):
        _compute(_target("0.05", "60000"), _current("0"), min_quantity="-1")


# ── Immutability (P-2 / §10.7) ──────────────────────────────────────────────

def test_order_intent_is_frozen() -> None:
    order = _compute(_target("0.05", "60000"), _current("0"))
    assert order is not None
    with pytest.raises(dataclasses.FrozenInstanceError):
        order.quantity = Decimal("0")  # type: ignore[misc]
