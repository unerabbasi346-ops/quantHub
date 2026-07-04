# Governing specification: Doc 09 — Database Architecture (Step 1.1 schema,
#                          core.orders / core.executions; quantity NUMERIC
#                          after Step 3.0; signal_id after migration d1f8b6c4a7e2)
#                          Doc 07 §Dependency Rules / §Implementation Rules
#                          Doc 14 §10.7.3/§10.7.4 (Order Model/Lifecycle),
#                          §10.9.4 (Trade Recording)
# Per Doc 00 §14.11
#
# Exercises the READ paths the Step 4.4 blotter consumes:
#   SQLAlchemyOrderRepository.list_by_portfolio (type tightened this step)
#   SQLAlchemyExecutionRepository.get_by_order
# plus the fill-outcome fields (filled_quantity/average_price) surfaced onto
# RecordedOrder this step — verifying they default correctly on a fresh
# CREATED order and are populated after a real mark_filled, round-tripping
# through SQL. Mirrors test_strategy_repository.py / test_portfolio_repository.py.
# The write path (create/record/transitions) is also exercised end-to-end by
# test_execution_loop.py's fakes; here it runs against real Postgres.
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from quant_hub.domain.execution.entities import (
    Fill,
    OrderIntent,
    OrderSide,
    OrderType,
    TimeInForce,
)
from quant_hub.domain.market_data.entities import AssetRef
from quant_hub.persistence.repositories.execution import (
    SQLAlchemyExecutionRepository,
    SQLAlchemyOrderRepository,
)

_NOW = datetime(2026, 7, 4, 12, 0, tzinfo=timezone.utc)


def _unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


async def _mk_portfolio(session: AsyncSession) -> uuid.UUID:
    row = await session.execute(
        text("INSERT INTO core.portfolios (name) VALUES (:name) RETURNING id"),
        {"name": _unique("portfolio")},
    )
    return row.scalar_one()


async def _mk_asset(session: AsyncSession) -> tuple[uuid.UUID, AssetRef]:
    symbol = _unique("SYM")
    row = await session.execute(
        text(
            "INSERT INTO market_data.assets (symbol, exchange, asset_class) "
            "VALUES (:symbol, 'binance', 'crypto') RETURNING id"
        ),
        {"symbol": symbol},
    )
    return row.scalar_one(), AssetRef(symbol=symbol, exchange="binance", asset_class="crypto")


def _intent(portfolio_id: uuid.UUID, asset: AssetRef, *, side: OrderSide, qty: str) -> OrderIntent:
    q = Decimal(qty)
    return OrderIntent(
        idempotency_key=uuid.uuid4(),
        portfolio_id=portfolio_id,
        strategy_id=None,
        asset=asset,
        side=side,
        quantity=q,
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.DAY,
        reference_price=Decimal("60000"),
        target_quantity=q,
        current_quantity=Decimal("0"),
        delta_quantity=q,
        signal_id=None,
    )


async def test_list_by_portfolio_returns_empty_for_portfolio_without_orders(
    db_session: AsyncSession,
) -> None:
    repo = SQLAlchemyOrderRepository(db_session)
    portfolio_id = await _mk_portfolio(db_session)
    assert await repo.list_by_portfolio(portfolio_id) == []


async def test_list_by_portfolio_returns_only_that_portfolios_orders(
    db_session: AsyncSession,
) -> None:
    repo = SQLAlchemyOrderRepository(db_session)
    portfolio_a = await _mk_portfolio(db_session)
    portfolio_b = await _mk_portfolio(db_session)
    asset_id, asset = await _mk_asset(db_session)

    await repo.create(_intent(portfolio_a, asset, side=OrderSide.BUY, qty="0.01"), asset_id)
    await repo.create(_intent(portfolio_a, asset, side=OrderSide.SELL, qty="0.02"), asset_id)
    await repo.create(_intent(portfolio_b, asset, side=OrderSide.BUY, qty="0.03"), asset_id)

    orders = await repo.list_by_portfolio(portfolio_a)

    assert len(orders) == 2
    assert all(o.portfolio_id == portfolio_a for o in orders)


async def test_created_order_defaults_zero_filled_and_null_average_price(
    db_session: AsyncSession,
) -> None:
    # The Step 4.4 fill-outcome fields must reflect the pre-fill state on a
    # fresh CREATED order: nothing filled, no average price yet.
    repo = SQLAlchemyOrderRepository(db_session)
    portfolio_id = await _mk_portfolio(db_session)
    asset_id, asset = await _mk_asset(db_session)

    created = await repo.create(
        _intent(portfolio_id, asset, side=OrderSide.BUY, qty="0.01"), asset_id
    )

    assert created.filled_quantity == Decimal("0")
    assert created.average_price is None


async def test_mark_filled_surfaces_filled_quantity_and_average_price(
    db_session: AsyncSession,
) -> None:
    # Drives CREATED -> VALIDATED -> FILLED and asserts the returned
    # RecordedOrder now carries the very fill quantity/price it wrote —
    # the latent gap this step closes, verified round-tripping through SQL.
    repo = SQLAlchemyOrderRepository(db_session)
    portfolio_id = await _mk_portfolio(db_session)
    asset_id, asset = await _mk_asset(db_session)

    created = await repo.create(
        _intent(portfolio_id, asset, side=OrderSide.BUY, qty="0.01"), asset_id
    )
    await repo.mark_validated(created.id)
    filled = await repo.mark_filled(created.id, Decimal("0.01"), Decimal("61234.56"))

    assert filled.status.value == "FILLED"
    assert filled.filled_quantity == Decimal("0.01000000")
    assert filled.average_price == Decimal("61234.56000000")


async def test_get_by_order_returns_empty_for_order_without_fills(
    db_session: AsyncSession,
) -> None:
    orders = SQLAlchemyOrderRepository(db_session)
    executions = SQLAlchemyExecutionRepository(db_session)
    portfolio_id = await _mk_portfolio(db_session)
    asset_id, asset = await _mk_asset(db_session)

    created = await orders.create(
        _intent(portfolio_id, asset, side=OrderSide.BUY, qty="0.01"), asset_id
    )
    assert await executions.get_by_order(created.id) == []


async def test_get_by_order_returns_recorded_fills(db_session: AsyncSession) -> None:
    orders = SQLAlchemyOrderRepository(db_session)
    executions = SQLAlchemyExecutionRepository(db_session)
    portfolio_id = await _mk_portfolio(db_session)
    asset_id, asset = await _mk_asset(db_session)

    created = await orders.create(
        _intent(portfolio_id, asset, side=OrderSide.BUY, qty="0.01"), asset_id
    )
    await executions.record(
        Fill(
            order_id=created.id,
            portfolio_id=portfolio_id,
            asset_id=asset_id,
            side=OrderSide.BUY,
            quantity=Decimal("0.01"),
            price=Decimal("61000"),
            commission=Decimal("0"),
            venue="SIM",
            executed_at=_NOW,
        )
    )

    fills = await executions.get_by_order(created.id)

    assert len(fills) == 1
    assert fills[0].order_id == created.id
    assert fills[0].quantity == Decimal("0.01000000")
    assert fills[0].price == Decimal("61000.00000000")
    assert fills[0].side is OrderSide.BUY
    # net_amount for a BUY is signed cash-out (negative), commission included.
    assert fills[0].net_amount < 0
