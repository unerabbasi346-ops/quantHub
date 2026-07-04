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
from quant_hub.domain.execution.interfaces import RiskApprovalInterface
from quant_hub.domain.market_data.interfaces import AssetRepository, OHLCVRepository
from quant_hub.domain.portfolio.interfaces import PortfolioRepository, PositionRepository
from quant_hub.infrastructure.cache import get_redis
from quant_hub.infrastructure.database import get_session
from quant_hub.infrastructure.risk_approval_adapter import RiskApprovalAdapter
from quant_hub.infrastructure.risk_model import PositionExposureRiskModel
from quant_hub.persistence.repositories.market_data import (
    SQLAlchemyAssetRepository,
    SQLAlchemyOHLCVRepository,
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
