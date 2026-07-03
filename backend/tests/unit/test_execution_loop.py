# Governing specification: Doc 14 §10.7.4 (Order Lifecycle), §10.8.6 (Fill
#   Handling), §10.9 (Trade Lifecycle), §10.6.6 (Position Management); P-13
# Per Doc 00 §14.11
#
# Pure-computation + fake-repo tests for Step 3.5 (simulated execution). The
# real core.executions / core.positions writes and the SQL transition guards
# are exercised in the live/integration verification, not here.
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4, uuid7

import pytest

from quant_hub.application.execution.service import ExecutionService
from quant_hub.domain.execution.entities import (
    OrderSide,
    OrderStatus,
    OrderType,
    RecordedExecution,
    RecordedOrder,
    TimeInForce,
)
from quant_hub.domain.execution.interfaces import RiskDecision
from quant_hub.domain.execution.simulation import simulate_fill
from quant_hub.domain.portfolio.positions import RecordedPosition, apply_fill_to_position
from quant_hub.domain.risk.entities import PreTradeRiskRequest

_NOW = datetime(2026, 7, 3, 12, 0, tzinfo=timezone.utc)


def _order(side: OrderSide = OrderSide.BUY, qty: str = "0.05000000") -> RecordedOrder:
    return RecordedOrder(
        id=uuid7(),
        idempotency_key=uuid7(),
        portfolio_id=uuid4(),
        strategy_id=uuid4(),
        asset_id=uuid4(),
        side=side,
        quantity=Decimal(qty),
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.DAY,
        status=OrderStatus.CREATED,
        signal_id=uuid4(),
        created_at=_NOW,
    )


def _request(order: RecordedOrder, price: str = "61000") -> PreTradeRiskRequest:
    return PreTradeRiskRequest(
        order_id=order.id, portfolio_id=order.portfolio_id, strategy_id=order.strategy_id,
        asset_id=order.asset_id, side=order.side, quantity=order.quantity,
        price=Decimal(price), current_quantity=Decimal("0"),
        portfolio_value=Decimal("100000"), timestamp=_NOW,
    )


# ── simulate_fill (§10.8.6 / §10.5) ─────────────────────────────────────────

def test_simulate_fill_is_full_fill_at_market_zero_commission() -> None:
    order = _order(OrderSide.BUY, "0.04844492")
    fill = simulate_fill(order, Decimal("61562.5"), _NOW)
    assert fill.quantity == order.quantity          # full fill
    assert fill.price == Decimal("61562.50000000")  # quantized to 8dp
    assert fill.commission == Decimal("0")
    assert fill.venue == "SIM"
    assert fill.order_id == order.id and fill.asset_id == order.asset_id


def test_fill_signed_quantity_and_notional() -> None:
    buy = simulate_fill(_order(OrderSide.BUY, "2"), Decimal("100"), _NOW)
    sell = simulate_fill(_order(OrderSide.SELL, "2"), Decimal("100"), _NOW)
    assert buy.signed_quantity == Decimal("2") and buy.gross_notional == Decimal("200")
    assert sell.signed_quantity == Decimal("-2")


# ── apply_fill_to_position (§10.6.6 / §10.9.3) ──────────────────────────────

def test_open_long_from_flat_sets_average_to_fill_price() -> None:
    u = apply_fill_to_position(Decimal("0"), Decimal("0"), Decimal("0.05"), Decimal("61000"))
    assert u.quantity == Decimal("0.05000000")
    assert u.average_entry_price == Decimal("61000.00000000")
    assert u.is_closed is False


def test_add_same_direction_weighted_average() -> None:
    u = apply_fill_to_position(Decimal("0.05"), Decimal("61000"), Decimal("0.05"), Decimal("63000"))
    assert u.quantity == Decimal("0.10000000")
    assert u.average_entry_price == Decimal("62000.00000000")


def test_partial_close_keeps_average() -> None:
    u = apply_fill_to_position(Decimal("0.10"), Decimal("62000"), Decimal("-0.04"), Decimal("64000"))
    assert u.quantity == Decimal("0.06000000")
    assert u.average_entry_price == Decimal("62000.00000000")  # unchanged
    assert u.is_closed is False


def test_full_close_resets_and_flags_closed() -> None:
    u = apply_fill_to_position(Decimal("0.10"), Decimal("62000"), Decimal("-0.10"), Decimal("64000"))
    assert u.quantity == Decimal("0")
    assert u.average_entry_price == Decimal("0")
    assert u.is_closed is True


def test_cross_zero_opens_new_position_at_fill_price() -> None:
    # long 0.05, sell 0.08 -> short 0.03 at the fill price
    u = apply_fill_to_position(Decimal("0.05"), Decimal("61000"), Decimal("-0.08"), Decimal("64000"))
    assert u.quantity == Decimal("-0.03000000")
    assert u.average_entry_price == Decimal("64000.00000000")


def test_open_short_from_flat() -> None:
    u = apply_fill_to_position(Decimal("0"), Decimal("0"), Decimal("-0.05"), Decimal("61000"))
    assert u.quantity == Decimal("-0.05000000")
    assert u.average_entry_price == Decimal("61000.00000000")


# ── ExecutionService orchestration (fakes) ──────────────────────────────────


class _FakeOrderRepo:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def mark_validated(self, order_id: UUID) -> RecordedOrder:
        self.calls.append("validated")
        return _replace_status(self._order, OrderStatus.VALIDATED)

    async def mark_rejected(self, order_id: UUID) -> RecordedOrder:
        self.calls.append("rejected")
        return _replace_status(self._order, OrderStatus.REJECTED)

    async def mark_filled(self, order_id: UUID, filled_quantity: Decimal, average_price: Decimal) -> RecordedOrder:
        self.calls.append("filled")
        self.filled = (filled_quantity, average_price)
        return _replace_status(self._order, OrderStatus.FILLED)


def _replace_status(order: RecordedOrder, status: OrderStatus) -> RecordedOrder:
    import dataclasses
    return dataclasses.replace(order, status=status)


class _FakeExecutionRepo:
    def __init__(self) -> None:
        self.recorded: list = []

    async def record(self, fill) -> RecordedExecution:
        rec = RecordedExecution(
            id=uuid7(), order_id=fill.order_id, portfolio_id=fill.portfolio_id,
            asset_id=fill.asset_id, side=fill.side, quantity=fill.quantity, price=fill.price,
            commission=fill.commission, net_amount=fill.gross_notional, venue=fill.venue,
            executed_at=fill.executed_at, created_at=_NOW,
        )
        self.recorded.append(rec)
        return rec

    async def get_by_order(self, order_id: UUID):  # pragma: no cover
        return list(self.recorded)


class _FakePositionRepo:
    def __init__(self, current: RecordedPosition | None = None) -> None:
        self.current = current
        self.upserted: dict | None = None

    async def get_by_portfolio(self, portfolio_id: UUID):  # pragma: no cover
        return []

    async def get_by_portfolio_and_asset(self, portfolio_id: UUID, asset_id: UUID):
        return self.current

    async def upsert(self, portfolio_id, asset_id, **kw) -> RecordedPosition:
        self.upserted = kw
        return RecordedPosition(
            id=uuid7(), portfolio_id=portfolio_id, asset_id=asset_id,
            quantity=kw["quantity"], average_entry_price=kw["average_entry_price"],
            market_value=kw["market_value"], unrealized_pnl=kw["unrealized_pnl"],
            realized_pnl_today=kw["realized_pnl_delta"], last_price=kw["last_price"],
            is_closed=kw["is_closed"], sequence_number=1,
        )


class _FakeGate:
    def __init__(self, decision: RiskDecision) -> None:
        self.decision = decision

    async def evaluate(self, order: object) -> RiskDecision:
        return self.decision


def _service(gate_decision: RiskDecision, current_pos: RecordedPosition | None = None):
    orders = _FakeOrderRepo()
    executions = _FakeExecutionRepo()
    positions = _FakePositionRepo(current_pos)
    svc = ExecutionService(orders, executions, positions, _FakeGate(gate_decision))
    return svc, orders, executions, positions


@pytest.mark.asyncio
async def test_approved_order_fills_and_updates_position() -> None:
    order = _order(OrderSide.BUY, "0.05")
    svc, orders, executions, positions = _service(RiskDecision(approved=True, reason="ok"))
    orders._order = order
    outcome = await svc.process_order(order, _request(order, "61000"), _NOW)

    assert outcome.terminal_status is OrderStatus.FILLED
    assert outcome.approved is True and outcome.rejection_reason is None
    assert orders.calls == ["validated", "filled"]        # never "rejected"
    assert orders.filled == (Decimal("0.05"), Decimal("61000.00000000"))
    assert len(executions.recorded) == 1
    # flat -> long: position qty 0.05 @ 61000, market_value 0.05*61000 = 3050.0000
    assert positions.upserted["quantity"] == Decimal("0.05000000")
    assert positions.upserted["average_entry_price"] == Decimal("61000.00000000")
    assert positions.upserted["market_value"] == Decimal("3050.0000")
    # opened at the fill price -> unrealized 0, no realized P&L on an open
    assert positions.upserted["unrealized_pnl"] == Decimal("0.0000")
    assert positions.upserted["realized_pnl_delta"] == Decimal("0.0000")
    assert outcome.position.quantity == Decimal("0.05000000")


@pytest.mark.asyncio
async def test_rejected_order_does_not_fill_or_touch_position() -> None:
    order = _order(OrderSide.BUY, "5")
    svc, orders, executions, positions = _service(
        RiskDecision(approved=False, reason="gross_exposure limit breached")
    )
    orders._order = order
    outcome = await svc.process_order(order, _request(order, "61000"), _NOW)

    assert outcome.terminal_status is OrderStatus.REJECTED
    assert outcome.approved is False
    assert "gross_exposure" in outcome.rejection_reason
    assert orders.calls == ["rejected"]                   # no validate/fill
    assert executions.recorded == []                      # no execution
    assert positions.upserted is None                     # position untouched


@pytest.mark.asyncio
async def test_second_buy_averages_into_existing_position() -> None:
    order = _order(OrderSide.BUY, "0.05")
    existing = RecordedPosition(
        id=uuid7(), portfolio_id=order.portfolio_id, asset_id=order.asset_id,
        quantity=Decimal("0.05"), average_entry_price=Decimal("60000"),
        market_value=Decimal("3000"), unrealized_pnl=Decimal("0"),
        realized_pnl_today=Decimal("0"), last_price=Decimal("60000"),
        is_closed=False, sequence_number=1,
    )
    svc, orders, executions, positions = _service(RiskDecision(approved=True), existing)
    orders._order = order
    await svc.process_order(order, _request(order, "62000"), _NOW)
    # 0.05@60000 + 0.05@62000 -> 0.10 @ 61000
    assert positions.upserted["quantity"] == Decimal("0.10000000")
    assert positions.upserted["average_entry_price"] == Decimal("61000.00000000")
