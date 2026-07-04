# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Presentation/API — Doc 07 §Layers
# Dependency injection wiring — Doc 07 §Implementation Rules
# Per Doc 00 §14.11
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from quant_hub.application.risk.service import RiskService
from quant_hub.domain.backtesting.interfaces import BacktestRepository
from quant_hub.domain.execution.interfaces import (
    ExecutionRepository,
    OrderRepository,
    RiskApprovalInterface,
)
from quant_hub.domain.market_data.interfaces import AssetRepository, OHLCVRepository
from quant_hub.domain.portfolio.interfaces import PortfolioRepository, PositionRepository
from quant_hub.domain.risk.interfaces import (
    PreTradeRiskRepository,
    RiskLimitRepository,
    RiskSnapshotRepository,
)
from quant_hub.domain.strategy_engine.interfaces import SignalRepository, StrategyRepository
from quant_hub.infrastructure.cache import get_redis
from quant_hub.infrastructure.database import get_session
from quant_hub.infrastructure.risk_approval_adapter import RiskApprovalAdapter
from quant_hub.infrastructure.risk_model import PositionExposureRiskModel
from quant_hub.persistence.repositories.backtesting import SQLAlchemyBacktestRepository
from quant_hub.persistence.repositories.execution import (
    SQLAlchemyExecutionRepository,
    SQLAlchemyOrderRepository,
)
from quant_hub.persistence.repositories.market_data import (
    SQLAlchemyAssetRepository,
    SQLAlchemyOHLCVRepository,
)
from quant_hub.persistence.repositories.strategy_engine import (
    SQLAlchemySignalRepository,
    SQLAlchemyStrategyRepository,
)
from quant_hub.persistence.repositories.portfolio import (
    SQLAlchemyPortfolioRepository,
    SQLAlchemyPositionRepository,
)
from quant_hub.persistence.repositories.risk import (
    SQLAlchemyPreTradeRiskRepository,
    SQLAlchemyRiskLimitRepository,
    SQLAlchemyRiskSnapshotRepository,
)

# Annotated aliases consumed by route handlers via FastAPI Depends()
# Doc 07 §Implementation Rules: dependency injection for external resources
DbSession = Annotated[AsyncSession, Depends(get_session)]
CacheClient = Annotated[Redis, Depends(get_redis)]


# Market-data read repositories — Step 4.1 (API Foundation). Each binds the
# domain repository interface to its SQLAlchemy implementation over the
# request-scoped session, so route handlers depend on the interface type
# (AssetRepository / OHLCVRepository), not the concrete class — Doc 07
# §Dependency Rules. Mirrors the RiskGate provider pattern below.
def get_asset_repository(session: DbSession) -> AssetRepository:
    return SQLAlchemyAssetRepository(session)


def get_ohlcv_repository(session: DbSession) -> OHLCVRepository:
    return SQLAlchemyOHLCVRepository(session)


AssetRepo = Annotated[AssetRepository, Depends(get_asset_repository)]
OHLCVRepo = Annotated[OHLCVRepository, Depends(get_ohlcv_repository)]


# Portfolio read repositories — Step 4.3 (Portfolio Vertical Slice).
def get_portfolio_repository(session: DbSession) -> PortfolioRepository:
    return SQLAlchemyPortfolioRepository(session)


def get_position_repository(session: DbSession) -> PositionRepository:
    return SQLAlchemyPositionRepository(session)


PortfolioRepo = Annotated[PortfolioRepository, Depends(get_portfolio_repository)]
PositionRepo = Annotated[PositionRepository, Depends(get_position_repository)]


# Execution read repositories — Step 4.4 (Execution Vertical Slice). Bind the
# domain interfaces (Order/ExecutionRepository) to their SQLAlchemy impls over
# the request-scoped session — the same read-only reuse of Phase 3.3/3.5's real
# repositories, no risk gate / write path involved on the read endpoints.
def get_order_repository(session: DbSession) -> OrderRepository:
    return SQLAlchemyOrderRepository(session)


def get_execution_repository(session: DbSession) -> ExecutionRepository:
    return SQLAlchemyExecutionRepository(session)


OrderRepo = Annotated[OrderRepository, Depends(get_order_repository)]
ExecutionRepo = Annotated[ExecutionRepository, Depends(get_execution_repository)]


# Strategy/signal/backtest read repositories — Step 4.5 (Strategies +
# Backtests Vertical Slice). Reuse of Phase 2's Strategy/SignalRepository and
# Phase 3.7's BacktestRepository — read-only, no write path on these endpoints.
def get_strategy_repository(session: DbSession) -> StrategyRepository:
    return SQLAlchemyStrategyRepository(session)


def get_signal_repository(session: DbSession) -> SignalRepository:
    return SQLAlchemySignalRepository(session)


def get_backtest_repository(session: DbSession) -> BacktestRepository:
    return SQLAlchemyBacktestRepository(session)


StrategyRepo = Annotated[StrategyRepository, Depends(get_strategy_repository)]
SignalRepo = Annotated[SignalRepository, Depends(get_signal_repository)]
BacktestRepo = Annotated[BacktestRepository, Depends(get_backtest_repository)]


# Risk read repositories — Step 4.6 (Risk Vertical Slice). Reuse of Phase 3.4's
# RiskLimit/PreTradeRisk repositories and Phase 3.6's RiskSnapshotRepository —
# read-only on these endpoints (no gate evaluation, no snapshot write).
def get_risk_limit_repository(session: DbSession) -> RiskLimitRepository:
    return SQLAlchemyRiskLimitRepository(session)


def get_pretrade_risk_repository(session: DbSession) -> PreTradeRiskRepository:
    return SQLAlchemyPreTradeRiskRepository(session)


def get_risk_snapshot_repository(session: DbSession) -> RiskSnapshotRepository:
    return SQLAlchemyRiskSnapshotRepository(session)


RiskLimitRepo = Annotated[RiskLimitRepository, Depends(get_risk_limit_repository)]
PreTradeRiskRepo = Annotated[PreTradeRiskRepository, Depends(get_pretrade_risk_repository)]
RiskSnapshotRepo = Annotated[RiskSnapshotRepository, Depends(get_risk_snapshot_repository)]


def get_risk_service(session: DbSession) -> RiskService:
    """The real RiskService for read-side reuse (Step 4.6): the risk limits view
    reuses RiskService.check_limits (Doc 15 §11.5.8) to compute utilization of
    continuous-monitoring limits against the latest snapshot — the same
    comparison logic the monitoring path uses, not a re-derivation."""
    return build_risk_service(session)


RiskServiceDep = Annotated[RiskService, Depends(get_risk_service)]


def build_risk_service(session: AsyncSession) -> RiskService:
    """The production RiskService — Doc 15 §11.5 / Doc 02 mandatory gate.

    Single construction point for the risk engine: the real
    PositionExposureRiskModel (Step 3.6, §11.5.3 exposure/leverage) plus real
    analytics.risk_limits / risk_assessments / risk_snapshots repositories.
    Used both for the pre-trade gate (below) and for portfolio risk snapshots.
    """
    return RiskService(
        risk_model=PositionExposureRiskModel(),
        limits=SQLAlchemyRiskLimitRepository(session),
        snapshots=SQLAlchemyRiskSnapshotRepository(session),
        pretrade=SQLAlchemyPreTradeRiskRepository(session),
    )


def build_risk_gate(session: AsyncSession) -> RiskApprovalInterface:
    """Production pre-trade risk gate — Doc 02 mandatory gate / Doc 14 §10.7.5.

    FAIL-SAFE DI (re-verified Step 3.4, now that the real gate can REJECT):
    this is the ONLY production binding of the risk gate, and it always
    returns the REAL RiskApprovalAdapter over the real RiskService.

    The always-approve StubRiskApprovalService (infrastructure/risk_approval.py)
    is deliberately NOT imported or referenced here — there is no config flag,
    environment branch, or default path that yields the stub in production. A
    misconfigured or "blocked" state therefore cannot silently downgrade the
    gate to unconditional approval; the worst case is the real gate FAILING
    CLOSED (default-deny per §10.7.5) inside RiskService.assess_pre_trade.
    "Blocked defaults to the real gate, not the stub" holds by construction:
    the stub is unreachable from the production wiring and exists only for
    tests that intentionally bypass risk evaluation.
    """
    return RiskApprovalAdapter(build_risk_service(session))


async def get_risk_gate(session: DbSession) -> RiskApprovalInterface:
    """FastAPI provider for the mandatory pre-trade risk gate."""
    return build_risk_gate(session)


RiskGate = Annotated[RiskApprovalInterface, Depends(get_risk_gate)]
