# Governing specification: Doc 09 — Database Architecture (Step 1.1 schema,
#                          core.portfolios / core.positions)
#                          Doc 07 §Dependency Rules / §Implementation Rules
# Per Doc 00 §14.11
#
# Exercises SQLAlchemyPortfolioRepository / SQLAlchemyPositionRepository.
# get_by_portfolio against a live Postgres. Mirrors
# test_strategy_repository.py's structure — these methods were previously
# stubs (return None / []) with no consumer and no test coverage; Step 4.3's
# api/v1/portfolio.py is their first real consumer. get_by_portfolio_and_asset
# and upsert are already exercised end-to-end by test_execution_loop.py's
# Signal->Order->Fill loop; this file covers the read paths that loop doesn't
# reach (get_by_id, list_active, and a multi-portfolio get_by_portfolio).
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from quant_hub.persistence.repositories.portfolio import (
    SQLAlchemyPortfolioRepository,
    SQLAlchemyPositionRepository,
)


def _unique_name(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


async def _mk_portfolio(
    session: AsyncSession, *, is_active: bool = True, deleted: bool = False
) -> uuid.UUID:
    deleted_expr = "clock_timestamp()" if deleted else "NULL"
    row = await session.execute(
        text(
            f"INSERT INTO core.portfolios (name, is_active, deleted_at) "
            f"VALUES (:name, :is_active, {deleted_expr}) RETURNING id"
        ),
        {"name": _unique_name("portfolio"), "is_active": is_active},
    )
    return row.scalar_one()


async def _mk_asset(session: AsyncSession) -> uuid.UUID:
    row = await session.execute(
        text(
            "INSERT INTO market_data.assets (symbol, exchange, asset_class) "
            "VALUES (:symbol, 'binance', 'crypto') RETURNING id"
        ),
        {"symbol": _unique_name("SYM")},
    )
    return row.scalar_one()


async def test_get_by_id_returns_none_for_unknown_id(db_session: AsyncSession) -> None:
    repo = SQLAlchemyPortfolioRepository(db_session)
    assert await repo.get_by_id(uuid.uuid4()) is None


async def test_get_by_id_returns_portfolio_for_known_id(db_session: AsyncSession) -> None:
    portfolio_id = await _mk_portfolio(db_session)

    repo = SQLAlchemyPortfolioRepository(db_session)
    resolved = await repo.get_by_id(portfolio_id)

    assert resolved is not None
    assert resolved.id == portfolio_id
    assert resolved.is_active is True


async def test_get_by_id_excludes_soft_deleted(db_session: AsyncSession) -> None:
    portfolio_id = await _mk_portfolio(db_session, deleted=True)

    repo = SQLAlchemyPortfolioRepository(db_session)
    assert await repo.get_by_id(portfolio_id) is None


async def test_list_active_excludes_inactive_and_soft_deleted(db_session: AsyncSession) -> None:
    active_id = await _mk_portfolio(db_session, is_active=True)
    inactive_id = await _mk_portfolio(db_session, is_active=False)
    deleted_id = await _mk_portfolio(db_session, is_active=True, deleted=True)

    repo = SQLAlchemyPortfolioRepository(db_session)
    ids = {p.id for p in await repo.list_active()}

    # The dev DB carries portfolios from other (already-committed) sessions,
    # so this asserts membership, not an exact count.
    assert active_id in ids
    assert inactive_id not in ids
    assert deleted_id not in ids


async def test_get_by_portfolio_returns_only_that_portfolios_positions(
    db_session: AsyncSession,
) -> None:
    portfolio_a = await _mk_portfolio(db_session)
    portfolio_b = await _mk_portfolio(db_session)
    asset_a = await _mk_asset(db_session)
    asset_b = await _mk_asset(db_session)
    now = datetime.now(timezone.utc)

    positions = SQLAlchemyPositionRepository(db_session)
    await positions.upsert(
        portfolio_a, asset_a,
        quantity=Decimal("1"), average_entry_price=Decimal("100"),
        market_value=Decimal("100"), unrealized_pnl=Decimal("0"),
        realized_pnl_delta=Decimal("0"), last_price=Decimal("100"),
        last_price_at=now, is_closed=False,
    )
    await positions.upsert(
        portfolio_b, asset_b,
        quantity=Decimal("2"), average_entry_price=Decimal("200"),
        market_value=Decimal("400"), unrealized_pnl=Decimal("0"),
        realized_pnl_delta=Decimal("0"), last_price=Decimal("200"),
        last_price_at=now, is_closed=False,
    )

    result = await positions.get_by_portfolio(portfolio_a)

    assert len(result) == 1
    assert result[0].portfolio_id == portfolio_a
    assert result[0].asset_id == asset_a
