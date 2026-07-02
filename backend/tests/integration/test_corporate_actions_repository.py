# Governing specification: Doc 11 §3 — Corporate Actions Processing
#                          Doc 09 — Database Architecture (migration 97e88a746f25, Step 1.10)
# Per Doc 00 §14.11
#
# Exercises SQLAlchemyCorporateActionsRepository against a live Postgres
# with migration 97e88a746f25 applied. Mirrors the OHLCV repository test
# structure: fresh insert, duplicate revision, mid-batch checkpoint
# isolation.
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from quant_hub.domain.market_data.entities import AssetRef, CorporateAction
from quant_hub.persistence.repositories.market_data import (
    SQLAlchemyAssetRepository,
    SQLAlchemyCorporateActionsRepository,
)


def _unique_symbol(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _action(asset_id: uuid.UUID, ex_date: date, amount: Decimal) -> CorporateAction:
    return CorporateAction(
        asset_id=asset_id,
        action_type="DIVIDEND",
        ex_date=ex_date,
        amount=amount,
        currency="USD",
    )


async def test_upsert_actions_fresh_insert_succeeds(db_session: AsyncSession) -> None:
    assets = SQLAlchemyAssetRepository(db_session)
    repo = SQLAlchemyCorporateActionsRepository(db_session)
    asset_id = await assets.upsert(
        AssetRef(symbol=_unique_symbol("CA"), exchange="yfinance", asset_class="equity")
    )
    ex_date = date(2026, 5, 11)

    count = await repo.upsert_actions([_action(asset_id, ex_date, Decimal("0.27"))])

    assert count == 1
    row = (
        await db_session.execute(
            text(
                "SELECT action_type, amount FROM market_data.corporate_actions "
                "WHERE asset_id = :aid AND ex_date = :ex_date"
            ),
            {"aid": asset_id, "ex_date": ex_date},
        )
    ).one()
    assert row.action_type == "DIVIDEND"
    assert row.amount == Decimal("0.27000000")


async def test_upsert_actions_duplicate_revises_not_duplicates(db_session: AsyncSession) -> None:
    assets = SQLAlchemyAssetRepository(db_session)
    repo = SQLAlchemyCorporateActionsRepository(db_session)
    asset_id = await assets.upsert(
        AssetRef(symbol=_unique_symbol("CA"), exchange="yfinance", asset_class="equity")
    )
    ex_date = date(2026, 5, 11)

    await repo.upsert_actions([_action(asset_id, ex_date, Decimal("0.27"))])
    await repo.upsert_actions([_action(asset_id, ex_date, Decimal("0.30"))])  # corrected amount

    count = (
        await db_session.execute(
            text(
                "SELECT COUNT(*) FROM market_data.corporate_actions "
                "WHERE asset_id = :aid AND ex_date = :ex_date"
            ),
            {"aid": asset_id, "ex_date": ex_date},
        )
    ).scalar_one()
    assert count == 1
    amount = (
        await db_session.execute(
            text(
                "SELECT amount FROM market_data.corporate_actions "
                "WHERE asset_id = :aid AND ex_date = :ex_date"
            ),
            {"aid": asset_id, "ex_date": ex_date},
        )
    ).scalar_one()
    assert amount == Decimal("0.30000000")  # latest write applied — DO UPDATE, not DO NOTHING


async def test_upsert_actions_isolates_mid_batch_failure(db_session: AsyncSession) -> None:
    """Same checkpoint-isolation guarantee as upsert_bars (Step 1.8) —
    reused via the identical per-row SAVEPOINT pattern."""
    assets = SQLAlchemyAssetRepository(db_session)
    repo = SQLAlchemyCorporateActionsRepository(db_session)
    asset_id = await assets.upsert(
        AssetRef(symbol=_unique_symbol("CA"), exchange="yfinance", asset_class="equity")
    )
    fake_asset_id = uuid.uuid4()

    batch = [
        _action(asset_id, date(2026, 1, 1), Decimal("0.10")),
        _action(fake_asset_id, date(2026, 2, 1), Decimal("0.20")),  # FK violation
        _action(asset_id, date(2026, 3, 1), Decimal("0.30")),
    ]

    count = await repo.upsert_actions(batch)

    assert count == 2
    rows = (
        await db_session.execute(
            text(
                "SELECT ex_date FROM market_data.corporate_actions "
                "WHERE asset_id = :aid ORDER BY ex_date"
            ),
            {"aid": asset_id},
        )
    ).all()
    assert [r.ex_date for r in rows] == [date(2026, 1, 1), date(2026, 3, 1)]


async def test_upsert_actions_split_and_reverse_split(db_session: AsyncSession) -> None:
    assets = SQLAlchemyAssetRepository(db_session)
    repo = SQLAlchemyCorporateActionsRepository(db_session)
    asset_id = await assets.upsert(
        AssetRef(symbol=_unique_symbol("CA"), exchange="yfinance", asset_class="equity")
    )

    split = CorporateAction(
        asset_id=asset_id, action_type="SPLIT", ex_date=date(2020, 8, 31), ratio=Decimal("4")
    )
    reverse = CorporateAction(
        asset_id=asset_id,
        action_type="REVERSE_SPLIT",
        ex_date=date(2021, 1, 1),
        ratio=Decimal("0.1"),
    )

    count = await repo.upsert_actions([split, reverse])

    assert count == 2
    rows = (
        await db_session.execute(
            text(
                "SELECT action_type, ratio FROM market_data.corporate_actions "
                "WHERE asset_id = :aid ORDER BY ex_date"
            ),
            {"aid": asset_id},
        )
    ).all()
    assert [(r.action_type, r.ratio) for r in rows] == [
        ("SPLIT", Decimal("4.000000")),
        ("REVERSE_SPLIT", Decimal("0.100000")),
    ]
