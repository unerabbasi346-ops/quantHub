# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
#   §API Standards: REST/FastAPI, versioned, Pydantic validation, OpenAPI.
# Doc 08 — Frontend Architecture (QH-008 v1.0) §API Layer: answers the
#   frontend portfolio service's existing calls GET /v1/portfolios and
#   GET /v1/portfolios/{id}/positions (features/portfolio/services).
# Doc 10 — API Specification (QH-010 v1.0): shared ResponseEnvelope.
# Doc 14 §10.6.6 — Position Management: the position read shape.
# Per Doc 00 §14.11
#
# Step 4.3, the Portfolio vertical slice: read endpoints over Phase 3.5's
# real core.portfolios / core.positions (PositionRepository written by the
# live Signal->Order->Fill loop).
#
# JUDGMENT CALLS (Doc 00 §14.5/§14.7 — flagged):
#  1. snake_case JSON + Decimal-as-string, identical to Step 4.2's markets
#     slice (see api/v1/markets.py) — quantity is NUMERIC(28,8), so it is a
#     STRING here too, not a number (the Step 0.5 frontend Position type had
#     `quantity: number`; reconciled to string in this step).
#  2. POSITION ENRICHMENT: a RecordedPosition carries only asset_id, but a
#     positions table is far more usable showing "BTC/USDT" than a UUID. The
#     endpoint resolves symbols by reusing Step 4.1's real
#     AssetRepository.get_by_id, deduplicated by asset_id (one lookup per
#     DISTINCT asset, not per row) — 1 positions query + N-distinct-asset
#     queries. At this data volume that's trivial; if a portfolio ever holds
#     many distinct assets, replace with a single positions⋈assets JOIN read
#     method. Kept as reuse-of-existing rather than a new JOIN method to
#     avoid widening the persistence surface for a non-issue.
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, status
from pydantic import BaseModel, field_serializer

from quant_hub.api.dependencies import AssetRepo, DbSession, PortfolioRepo, PositionRepo
from quant_hub.api.envelope import ApiError, ErrorCode, ResponseEnvelope, ok
from quant_hub.domain.market_data.entities import Asset
from quant_hub.domain.portfolio.entities import Portfolio
from quant_hub.domain.portfolio.positions import RecordedPosition

router = APIRouter(tags=["portfolio"])


class PortfolioOut(BaseModel):
    """API shape of a core.portfolios row — Doc 09 field names (snake_case).

    `configured_capital` (Decimal-as-string, or null when never configured) is
    an operator-set figure with NO backing NAV ledger — display/config only,
    does NOT feed leverage/risk math (F-19; see migration a7d2e1f04b93)."""

    id: UUID
    name: str
    description: str | None
    base_currency: str
    portfolio_type: str
    is_active: bool
    configured_capital: Decimal | None = None

    @field_serializer("configured_capital", when_used="json")
    def _serialize_capital(self, value: Decimal | None) -> str | None:
        return None if value is None else format(value, "f")


class PositionOut(BaseModel):
    """API shape of a core.positions row (Doc 14 §10.6.6), enriched with the
    asset's symbol/exchange/instrument_type for display. Decimal fields
    render as strings.

    `leverage`/`margin_used` (migration e7a3c1f5b9d2, S-10) are None for a
    spot/unleveraged position (honest absence, never a fabricated 1x/0) —
    only ever populated for a PERPETUAL position that has gone through the
    fill→position path. `instrument_type` (SPOT | PERPETUAL) is the same
    asset-resolved field added to markets' AssetOut, exposed here too so a
    client can decide whether to even show a leverage/margin column for this
    row. F-19 INTERACTION: margin_used is storage only, same as leverage —
    it is not backed by an authoritative equity/collateral ledger.
    """

    id: UUID
    portfolio_id: UUID
    asset_id: UUID
    symbol: str | None
    exchange: str | None
    instrument_type: str | None
    quantity: Decimal
    average_entry_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    realized_pnl_today: Decimal
    last_price: Decimal | None
    leverage: Decimal | None
    margin_used: Decimal | None
    is_closed: bool
    sequence_number: int

    @field_serializer(
        "quantity", "average_entry_price", "market_value", "unrealized_pnl",
        "realized_pnl_today", "last_price", "leverage", "margin_used",
        when_used="json",
    )
    def _serialize_decimal(self, value: Decimal | None) -> str | None:
        return None if value is None else format(value, "f")

    @classmethod
    def from_recorded(cls, position: RecordedPosition, asset: Asset | None) -> "PositionOut":
        return cls(
            id=position.id,
            portfolio_id=position.portfolio_id,
            asset_id=position.asset_id,
            symbol=asset.symbol if asset else None,
            exchange=asset.exchange if asset else None,
            instrument_type=asset.instrument_type if asset else None,
            quantity=position.quantity,
            average_entry_price=position.average_entry_price,
            market_value=position.market_value,
            unrealized_pnl=position.unrealized_pnl,
            realized_pnl_today=position.realized_pnl_today,
            last_price=position.last_price,
            leverage=position.leverage,
            margin_used=position.margin_used,
            is_closed=position.is_closed,
            sequence_number=position.sequence_number,
        )


def _portfolio_out(portfolio: Portfolio) -> PortfolioOut:
    return PortfolioOut.model_validate(portfolio, from_attributes=True)


@router.get(
    "/portfolios",
    response_model=ResponseEnvelope[list[PortfolioOut]],
    summary="List active portfolios",
)
async def list_portfolios(repo: PortfolioRepo) -> ResponseEnvelope[list[PortfolioOut]]:
    portfolios = await repo.list_active()
    return ok([_portfolio_out(p) for p in portfolios])


@router.get(
    "/portfolios/{portfolio_id}",
    response_model=ResponseEnvelope[PortfolioOut],
    summary="Get a single portfolio by id",
)
async def get_portfolio(
    portfolio_id: UUID, repo: PortfolioRepo
) -> ResponseEnvelope[PortfolioOut]:
    portfolio = await repo.get_by_id(portfolio_id)
    if portfolio is None:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.RESOURCE_NOT_FOUND,
            f"Portfolio {portfolio_id} not found",
        )
    return ok(_portfolio_out(portfolio))


@router.get(
    "/portfolios/{portfolio_id}/positions",
    response_model=ResponseEnvelope[list[PositionOut]],
    summary="Get positions for a portfolio",
)
async def get_portfolio_positions(
    portfolio_id: UUID,
    portfolio_repo: PortfolioRepo,
    position_repo: PositionRepo,
    asset_repo: AssetRepo,
) -> ResponseEnvelope[list[PositionOut]]:
    # 404 on an unknown portfolio so a client distinguishes "no such
    # portfolio" from "portfolio exists but holds no positions" (empty list).
    if await portfolio_repo.get_by_id(portfolio_id) is None:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.RESOURCE_NOT_FOUND,
            f"Portfolio {portfolio_id} not found",
        )
    positions = await position_repo.get_by_portfolio(portfolio_id)
    # Resolve each DISTINCT asset once (judgment call #2 in module docstring).
    assets: dict[UUID, Asset | None] = {}
    for pos in positions:
        if pos.asset_id not in assets:
            assets[pos.asset_id] = await asset_repo.get_by_id(pos.asset_id)
    return ok([PositionOut.from_recorded(p, assets[p.asset_id]) for p in positions])


class CapitalConfigIn(BaseModel):
    """Body for the capital-configuration control (F-19-honest, see below)."""

    configured_capital: Decimal


@router.put(
    "/portfolios/{portfolio_id}/capital",
    response_model=ResponseEnvelope[PortfolioOut],
    summary="Set a portfolio's configured capital (NOT a NAV ledger — F-19)",
)
async def set_portfolio_capital(
    portfolio_id: UUID,
    body: CapitalConfigIn,
    repo: PortfolioRepo,
    session: DbSession,
) -> ResponseEnvelope[PortfolioOut]:
    # HONEST F-19 SCOPE (flagged, mirrored in the UI): this stores an
    # operator-set capital figure only. It has NO backing NAV/cash ledger and
    # does NOT feed leverage or any risk-limit determination — a real §11.4
    # capital ledger stays deferred. 400 on a non-positive figure, 404 on an
    # unknown portfolio, then commit (repositories never commit, Doc 07).
    if body.configured_capital <= 0:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.VALIDATION_ERROR,
            "configured_capital must be a positive amount",
        )
    updated = await repo.set_configured_capital(portfolio_id, body.configured_capital)
    if updated is None:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.RESOURCE_NOT_FOUND,
            f"Portfolio {portfolio_id} not found",
        )
    await session.commit()
    return ok(_portfolio_out(updated))
