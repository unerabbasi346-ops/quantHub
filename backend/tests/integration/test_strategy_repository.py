# Governing specification: Doc 09 — Database Architecture (Step 1.1 schema, core.strategies)
#                          Doc 07 §Dependency Rules / §Implementation Rules
# Per Doc 00 §14.11
#
# Exercises SQLAlchemyStrategyRepository against a live Postgres. Mirrors
# test_market_data_repositories.py's AssetRepository.upsert test structure
# (Step 1.3) — the pattern this step's upsert explicitly mirrors.
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from quant_hub.domain.strategy_engine.entities import StrategyRef
from quant_hub.persistence.repositories.strategy_engine import SQLAlchemyStrategyRepository


def _unique_name(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


async def test_upsert_fresh_insert_succeeds(db_session: AsyncSession) -> None:
    repo = SQLAlchemyStrategyRepository(db_session)
    name = _unique_name("strat")

    strategy_id = await repo.upsert(
        StrategyRef(name=name, version="1.0.0", description="test", config={"lookback": 20})
    )

    assert isinstance(strategy_id, uuid.UUID)
    resolved = await repo.get_by_id(strategy_id)
    assert resolved is not None
    assert resolved.name == name
    assert resolved.version == "1.0.0"
    assert resolved.description == "test"
    assert resolved.config == {"lookback": 20}
    assert resolved.status == "INACTIVE"  # schema default, untouched by upsert


async def test_upsert_same_name_resolves_not_duplicates(db_session: AsyncSession) -> None:
    repo = SQLAlchemyStrategyRepository(db_session)
    name = _unique_name("strat")

    first_id = await repo.upsert(StrategyRef(name=name, version="1.0.0", config={"a": 1}))
    second_id = await repo.upsert(StrategyRef(name=name, version="1.1.0", config={"a": 2}))

    assert first_id == second_id  # idempotent re-registration, no duplicate row
    resolved = await repo.get_by_id(first_id)
    assert resolved is not None
    assert resolved.version == "1.1.0"  # latest write applied
    assert resolved.config == {"a": 2}


async def test_upsert_never_touches_status(db_session: AsyncSession) -> None:
    from sqlalchemy import text

    repo = SQLAlchemyStrategyRepository(db_session)
    name = _unique_name("strat")

    strategy_id = await repo.upsert(StrategyRef(name=name, version="1.0.0"))
    # Simulate a governed lifecycle transition (Doc 14 §10.2.6) happening
    # out-of-band from resolve-or-register.
    await db_session.execute(
        text("UPDATE core.strategies SET status = 'LIVE' WHERE id = :id"), {"id": strategy_id}
    )

    # Re-registering (e.g. redeploying the same strategy config) must not
    # silently reset a live strategy back to INACTIVE.
    await repo.upsert(StrategyRef(name=name, version="1.0.1"))

    resolved = await repo.get_by_id(strategy_id)
    assert resolved is not None
    assert resolved.status == "LIVE"
    assert resolved.version == "1.0.1"


async def test_get_by_id_returns_none_for_unknown_id(db_session: AsyncSession) -> None:
    repo = SQLAlchemyStrategyRepository(db_session)
    assert await repo.get_by_id(uuid.uuid4()) is None


async def test_list_by_portfolio_returns_registered_strategies(db_session: AsyncSession) -> None:
    from sqlalchemy import text

    repo = SQLAlchemyStrategyRepository(db_session)
    portfolio_id = (
        await db_session.execute(
            text("INSERT INTO core.portfolios (name) VALUES (:name) RETURNING id"),
            {"name": _unique_name("portfolio")},
        )
    ).scalar_one()

    await repo.upsert(StrategyRef(name=_unique_name("strat"), version="1.0.0", portfolio_id=portfolio_id))
    await repo.upsert(StrategyRef(name=_unique_name("strat"), version="1.0.0", portfolio_id=portfolio_id))

    strategies = await repo.list_by_portfolio(portfolio_id)

    assert len(strategies) == 2
    assert all(s.portfolio_id == portfolio_id for s in strategies)


async def test_opaque_config_round_trips_verbatim(db_session: AsyncSession) -> None:
    # P-1/T-2: the platform stores config verbatim, never interprets it —
    # verify nested/mixed-type JSON round-trips exactly.
    repo = SQLAlchemyStrategyRepository(db_session)
    config = {"lookback": 20, "threshold": 0.5, "tags": ["momentum", "daily"], "nested": {"a": 1}}

    strategy_id = await repo.upsert(
        StrategyRef(name=_unique_name("strat"), version="1.0.0", config=config)
    )

    resolved = await repo.get_by_id(strategy_id)
    assert resolved is not None
    assert resolved.config == config
