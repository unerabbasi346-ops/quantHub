# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
#   §API Standards: "REST using FastAPI. Version endpoints. Validate all
#   requests with Pydantic ... Document endpoints with OpenAPI."
# Doc 08 — Frontend Architecture (QH-008 v1.0) §API Layer: the frontend's
#   centralized client already calls GET /v1/assets and
#   GET /v1/assets/{id}/bars (features/markets/services) — these are the
#   endpoints that answer those calls (paths kept identical to avoid churn).
# Doc 10 — API Specification (QH-010 v1.0): responses use the shared
#   ResponseEnvelope (api/envelope.py).
# Doc 11 — Data Engineering: the OHLCV/asset field shapes these expose.
# Per Doc 00 §14.11
#
# Step 4.1, the FIRST real read endpoints beyond /health — the markets
# vertical slice, chosen as the API-foundation proof-of-concept because it
# is the least dependency-heavy (pure reads over Phase-1-ingested
# market_data.*, no risk gate / order pipeline involved).
#
# JUDGMENT CALLS (Doc 00 §14.5/§14.7 — flagged, not silently decided):
#  1. FIELD NAMING is snake_case, matching Doc 10's own envelope fields
#     (error_code, request_id) and the Doc 09 / DB column names. The Step
#     0.5 frontend types (features/markets/types.ts) currently assume
#     camelCase (assetClass, isActive, assetId) — that speculative scaffold
#     is reconciled to snake_case (or given a client-side transform) in
#     Step 4.2 when the frontend is actually wired; the API is the contract
#     source of truth, not the pre-existing draft types.
#  2. DECIMAL fields (OHLC, volume, vwap, adjustment_factor) serialize as
#     JSON STRINGS, not floats — these are financial values and must not
#     round-trip through IEEE-754. The Step 0.5 frontend OHLCVBar type has
#     `volume: number`; that becomes a string in Step 4.2.
#  3. The bar response has NO surrogate `id`: the domain OHLCVBar entity
#     doesn't carry one (a bar's natural key is asset_id+interval+ts) and
#     get_bars doesn't select it. The Step 0.5 frontend OHLCVBar.id field
#     is dropped in Step 4.2.
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Query, status
from pydantic import BaseModel, field_serializer

from quant_hub.api.dependencies import AssetRepo, OHLCVRepo
from quant_hub.api.envelope import ApiError, ErrorCode, ResponseEnvelope, ok

router = APIRouter(tags=["markets"])


class AssetOut(BaseModel):
    """API shape of a market_data.assets row — Doc 09 field names (snake_case)."""

    id: UUID
    symbol: str
    exchange: str
    asset_class: str
    name: str | None
    currency: str
    is_active: bool


class OHLCVBarOut(BaseModel):
    """API shape of a market_data.ohlcv_bars row — Doc 11 OHLCV contract.

    Decimal fields are rendered as strings (see module judgment call #2).
    """

    asset_id: UUID
    interval: str
    ts: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    vwap: Decimal | None = None
    trade_count: int | None = None
    adjustment_factor: Decimal
    data_quality: str
    source: str | None = None

    @field_serializer(
        "open", "high", "low", "close", "volume", "vwap", "adjustment_factor",
        when_used="json",
    )
    def _serialize_decimal(self, value: Decimal | None) -> str | None:
        # format(v, "f") avoids scientific notation for very small/large
        # magnitudes; None (nullable vwap) passes through unchanged.
        return None if value is None else format(value, "f")


@router.get(
    "/assets",
    response_model=ResponseEnvelope[list[AssetOut]],
    summary="List active tradable assets",
)
async def list_assets(repo: AssetRepo) -> ResponseEnvelope[list[AssetOut]]:
    assets = await repo.list_active()
    return ok([AssetOut.model_validate(a, from_attributes=True) for a in assets])


@router.get(
    "/assets/{asset_id}",
    response_model=ResponseEnvelope[AssetOut],
    summary="Get a single asset by id",
)
async def get_asset(asset_id: UUID, repo: AssetRepo) -> ResponseEnvelope[AssetOut]:
    asset = await repo.get_by_id(asset_id)
    if asset is None:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.RESOURCE_NOT_FOUND,
            f"Asset {asset_id} not found",
        )
    return ok(AssetOut.model_validate(asset, from_attributes=True))


@router.get(
    "/assets/{asset_id}/bars",
    response_model=ResponseEnvelope[list[OHLCVBarOut]],
    summary="Get OHLCV bars for an asset",
)
async def get_asset_bars(
    asset_id: UUID,
    asset_repo: AssetRepo,
    bar_repo: OHLCVRepo,
    interval: str = Query("1h", description="Bar interval, e.g. '1h', '1d'"),
    limit: int = Query(100, ge=1, le=1000, description="Max most-recent bars"),
) -> ResponseEnvelope[list[OHLCVBarOut]]:
    # 404 on an unknown asset so a client can distinguish "no such asset"
    # from "asset exists but has no bars for this interval" (the latter is a
    # legitimate empty list, not an error).
    if await asset_repo.get_by_id(asset_id) is None:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.RESOURCE_NOT_FOUND,
            f"Asset {asset_id} not found",
        )
    bars = await bar_repo.get_bars(asset_id, interval, limit)
    return ok([OHLCVBarOut.model_validate(b, from_attributes=True) for b in bars])
