# Governing specification: Doc 14 §10.7.5 — Pre-Trade Risk Check (audit records)
#                          Doc 15 §11.5.3/§11.5.8 — Risk snapshots / monitoring
#                          Doc 09 — Database Architecture (analytics.risk_*, migration b2e4c9d17a30)
#                          Doc 07 §Dependency Rules / §Implementation Rules
# Per Doc 00 §14.11
#
# Exercises the READ paths the Step 4.6 risk slice adds:
#   SQLAlchemyPreTradeRiskRepository.list_by_portfolio (assessment history)
#   SQLAlchemyRiskSnapshotRepository.get_latest_record  (raw snapshot incl. the
#     F-18 `deferred` marker + breaches, which get_latest drops)
# against a live Postgres. The save/get_by_order write path is already exercised
# by the Step 3.4/3.6 unit + live paths; here the new reads run against real
# rows. Mirrors test_execution_repository.py / test_backtest_repository.py.
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from quant_hub.domain.risk.entities import (
    PreTradeCheck,
    PreTradeRiskResult,
    RiskMetrics,
)
from quant_hub.persistence.repositories.risk import (
    SQLAlchemyPreTradeRiskRepository,
    SQLAlchemyRiskSnapshotRepository,
)

_NOW = datetime(2026, 7, 4, 12, 0, tzinfo=timezone.utc)


def _unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


async def _mk_portfolio(session: AsyncSession) -> uuid.UUID:
    row = await session.execute(
        text("INSERT INTO core.portfolios (name) VALUES (:n) RETURNING id"),
        {"n": _unique("risk-pf")},
    )
    return row.scalar_one()


async def _mk_order(session: AsyncSession, portfolio_id: uuid.UUID) -> uuid.UUID:
    asset_id = (
        await session.execute(
            text(
                "INSERT INTO market_data.assets (symbol, exchange, asset_class) "
                "VALUES (:s, 'binance', 'crypto') RETURNING id"
            ),
            {"s": _unique("SYM")},
        )
    ).scalar_one()
    row = await session.execute(
        text(
            "INSERT INTO core.orders "
            "(idempotency_key, portfolio_id, asset_id, order_type, side, quantity, time_in_force) "
            "VALUES (:k, :p, :a, 'MARKET', 'BUY', 0.01, 'DAY') RETURNING id"
        ),
        {"k": uuid.uuid4(), "p": portfolio_id, "a": asset_id},
    )
    return row.scalar_one()


def _assessment(
    order_id: uuid.UUID,
    portfolio_id: uuid.UUID,
    *,
    authorized: bool,
    assessed_at: datetime,
) -> PreTradeRiskResult:
    reason = None if authorized else "position_size limit breached: projected 0.011 exceeds limit 0.005"
    checks = (
        PreTradeCheck(
            check_name="risk_limit:position_size",
            passed=authorized,
            detail="ok" if authorized else "position_size: projected=0.011 vs limit=0.005 -> breach",
        ),
    )
    return PreTradeRiskResult(
        check_id=uuid.uuid4(),
        order_id=order_id,
        portfolio_id=portfolio_id,
        authorized=authorized,
        rejection_reason=reason,
        individual_checks=checks,
        computation_latency_ns=123456,
        assessed_at=assessed_at,
    )


def _metrics(portfolio_id: uuid.UUID, *, computed_at: datetime, gross: str) -> RiskMetrics:
    zero = Decimal("0")
    return RiskMetrics(
        portfolio_id=portfolio_id,
        var_1d_99=zero, cvar_1d_99=zero, volatility_annualized=zero,
        max_drawdown=zero, beta=zero,
        gross_exposure=Decimal(gross), net_exposure=Decimal(gross),
        gross_leverage=Decimal("0.00006196"), net_leverage=Decimal("0.00006196"),
        computed_at=computed_at,
    )


# ── pre-trade assessment history ────────────────────────────────────────────
async def test_list_by_portfolio_returns_empty_for_portfolio_without_assessments(
    db_session: AsyncSession,
) -> None:
    repo = SQLAlchemyPreTradeRiskRepository(db_session)
    portfolio_id = await _mk_portfolio(db_session)
    assert await repo.list_by_portfolio(portfolio_id, 100) == []


async def test_list_by_portfolio_returns_recent_first_with_reasons(
    db_session: AsyncSession,
) -> None:
    repo = SQLAlchemyPreTradeRiskRepository(db_session)
    portfolio_id = await _mk_portfolio(db_session)
    approved_order = await _mk_order(db_session, portfolio_id)
    rejected_order = await _mk_order(db_session, portfolio_id)

    # Approved earlier, rejected later — expect the rejected one first.
    await repo.save(_assessment(approved_order, portfolio_id, authorized=True, assessed_at=_NOW - timedelta(minutes=5)))
    await repo.save(_assessment(rejected_order, portfolio_id, authorized=False, assessed_at=_NOW))

    history = await repo.list_by_portfolio(portfolio_id, 100)

    assert len(history) == 2
    assert history[0].authorized is False
    assert "breached" in (history[0].rejection_reason or "")
    assert history[0].individual_checks[0].passed is False
    assert history[1].authorized is True
    assert history[1].rejection_reason is None


async def test_list_by_portfolio_respects_limit(db_session: AsyncSession) -> None:
    repo = SQLAlchemyPreTradeRiskRepository(db_session)
    portfolio_id = await _mk_portfolio(db_session)
    for i in range(3):
        order = await _mk_order(db_session, portfolio_id)
        await repo.save(_assessment(order, portfolio_id, authorized=True, assessed_at=_NOW - timedelta(minutes=i)))

    assert len(await repo.list_by_portfolio(portfolio_id, 2)) == 2


# ── portfolio risk snapshot (raw record with F-18 deferred marker) ──────────
async def test_get_latest_record_none_when_no_snapshot(db_session: AsyncSession) -> None:
    repo = SQLAlchemyRiskSnapshotRepository(db_session)
    portfolio_id = await _mk_portfolio(db_session)
    assert await repo.get_latest_record(portfolio_id) is None


async def test_get_latest_record_surfaces_exposure_and_deferred_marker(
    db_session: AsyncSession,
) -> None:
    repo = SQLAlchemyRiskSnapshotRepository(db_session)
    portfolio_id = await _mk_portfolio(db_session)

    await repo.save(_metrics(portfolio_id, computed_at=_NOW, gross="61.9600"), breaches=())

    record = await repo.get_latest_record(portfolio_id)

    assert record is not None
    rm = record["risk_metrics"]
    # real computed exposure/leverage
    assert rm["gross_exposure"] == "61.9600"
    assert rm["net_exposure"] == "61.9600"
    # the F-18 deferred marker is present and names exactly the deferred metrics
    assert set(rm["deferred"]) == {
        "var_1d_99", "cvar_1d_99", "volatility_annualized", "max_drawdown", "beta",
    }
    assert record["breaches"] == []


async def test_get_latest_record_returns_most_recent(db_session: AsyncSession) -> None:
    repo = SQLAlchemyRiskSnapshotRepository(db_session)
    portfolio_id = await _mk_portfolio(db_session)

    await repo.save(_metrics(portfolio_id, computed_at=_NOW - timedelta(hours=1), gross="10.0000"), breaches=())
    await repo.save(_metrics(portfolio_id, computed_at=_NOW, gross="61.9600"), breaches=())

    record = await repo.get_latest_record(portfolio_id)

    assert record is not None
    assert record["risk_metrics"]["gross_exposure"] == "61.9600"  # the newer snapshot
