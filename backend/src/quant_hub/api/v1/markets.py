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

from quant_hub.api.dependencies import AssetRepo, FundingRateRepo, OHLCVRepo, OpenInterestRepo
from quant_hub.api.envelope import ApiError, ErrorCode, ResponseEnvelope, ok
from quant_hub.domain.market_data.correlation import compute_return_correlations

router = APIRouter(tags=["markets"])


class AssetOut(BaseModel):
    """API shape of a market_data.assets row — Doc 09 field names (snake_case).

    `instrument_type` (SPOT | PERPETUAL, migration e7a3c1f5b9d2 / S-10) lets a
    client decide whether funding-rate data is even meaningful for this
    instrument — a SPOT asset has no funding concept and the funding-rates
    endpoint below legitimately returns an empty list for one, not an error.
    """

    id: UUID
    symbol: str
    exchange: str
    asset_class: str
    name: str | None
    currency: str
    is_active: bool
    instrument_type: str = "SPOT"


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


# ── Price-return correlation (owner-requested standalone view) ──────────────
# SCOPE (flagged, and mirrored in the UI label): this is a descriptive
# PRICE-RETURN correlation matrix between ingested instruments — NOT a
# portfolio risk metric, and explicitly unrelated to F-18's deferred §11.5.3
# risk measures (VaR/CVaR/beta/volatility/drawdown), which stay deferred. It
# consumes only Phase-1 OHLCV closes and the pure domain calculator
# (domain/market_data/correlation.py). See that module for the full boundary.
class CorrelationAssetOut(BaseModel):
    id: UUID
    symbol: str


class CorrelationOut(BaseModel):
    """A square return-correlation matrix over the active instruments that
    share an aligned bar window. `assets[i]` labels row/column i of `matrix`.
    A cell is null where the coefficient is undefined (a constant series).
    `sample_size` is the number of aligned return observations."""

    interval: str
    sample_size: int
    assets: list[CorrelationAssetOut]
    matrix: list[list[float | None]]


@router.get(
    "/markets/correlation",
    response_model=ResponseEnvelope[CorrelationOut],
    summary="Price-return correlation matrix across ingested instruments (NOT portfolio risk)",
)
async def get_correlation(
    asset_repo: AssetRepo,
    bar_repo: OHLCVRepo,
    interval: str = Query("1h", description="Bar interval to correlate over"),
    limit: int = Query(200, ge=2, le=1000, description="Max most-recent bars per asset"),
) -> ResponseEnvelope[CorrelationOut]:
    assets = await asset_repo.list_active()

    # Gather each asset's (ts -> close) for the interval; keep only assets with
    # at least two bars (a single bar yields no return).
    closes_by_symbol: dict[str, dict[datetime, float]] = {}
    included: list[CorrelationAssetOut] = []
    ts_sets: list[set[datetime]] = []
    for asset in assets:
        bars = await bar_repo.get_bars(asset.id, interval, limit)
        if len(bars) < 2:
            continue
        series = {b.ts: float(b.close) for b in bars}
        closes_by_symbol[asset.symbol] = series
        ts_sets.append(set(series.keys()))
        included.append(CorrelationAssetOut(id=asset.id, symbol=asset.symbol))

    # Align on the timestamps common to every included asset (an honest
    # intersection — correlation is only meaningful over concurrent bars).
    common = sorted(set.intersection(*ts_sets)) if ts_sets else []
    aligned = {
        a.symbol: [closes_by_symbol[a.symbol][ts] for ts in common] for a in included
    }

    result = compute_return_correlations(aligned)
    return ok(
        CorrelationOut(
            interval=interval,
            sample_size=result.sample_size,
            assets=included,
            matrix=[list(row) for row in result.matrix],
        )
    )


# ── Funding rates (perpetuals only) — Doc 14 §10.9.5 "Financing Costs" ──────
# S-10: funding is a PERPETUAL-only cashflow series (market_data.funding_rates,
# migration e7a3c1f5b9d2). A SPOT asset_id has no funding rows by construction
# (nothing ever ingests them for SPOT) — this endpoint therefore returns an
# honest empty list for a SPOT asset rather than a 400/404; the caller (asset's
# own instrument_type, exposed above) is what decides whether to even show a
# funding UI, not this endpoint refusing the request.
class FundingRateOut(BaseModel):
    """API shape of a market_data.funding_rates row — Doc 14 §10.9.5."""

    asset_id: UUID
    funding_time: datetime
    funding_rate: Decimal
    mark_price: Decimal | None = None
    next_funding_time: datetime | None = None
    interval_hours: int | None = None

    @field_serializer("funding_rate", "mark_price", when_used="json")
    def _serialize_decimal(self, value: Decimal | None) -> str | None:
        return None if value is None else format(value, "f")


@router.get(
    "/assets/{asset_id}/funding-rates",
    response_model=ResponseEnvelope[list[FundingRateOut]],
    summary="Get perpetual funding-rate history for an asset (empty for SPOT)",
)
async def get_asset_funding_rates(
    asset_id: UUID,
    asset_repo: AssetRepo,
    funding_repo: FundingRateRepo,
    limit: int = Query(100, ge=1, le=1000, description="Max most-recent funding observations"),
) -> ResponseEnvelope[list[FundingRateOut]]:
    if await asset_repo.get_by_id(asset_id) is None:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.RESOURCE_NOT_FOUND,
            f"Asset {asset_id} not found",
        )
    rates = await funding_repo.get_funding_rates(asset_id, limit)
    return ok([FundingRateOut.model_validate(r, from_attributes=True) for r in rates])


# ── Open interest (perpetuals only) — same §10.9.5 anchor as funding rates ──
# JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged, deliberately DIFFERENT from the
# funding-rates endpoint's own choice above): this endpoint 404s for a SPOT
# instrument rather than returning an honest empty list. Both are defensible
# ("empty" is equally true for a series that structurally can't exist on this
# asset); this one 404s per explicit owner instruction so a client asking for
# OI on a spot asset gets an unambiguous rejection rather than a silent empty
# array it might mistake for "not ingested yet".
class OpenInterestOut(BaseModel):
    """API shape of a market_data.open_interest row — Doc 14 §10.9.5."""

    asset_id: UUID
    ts: datetime
    open_interest_usdt: Decimal
    open_interest_contracts: Decimal | None = None

    @field_serializer("open_interest_usdt", "open_interest_contracts", when_used="json")
    def _serialize_decimal(self, value: Decimal | None) -> str | None:
        return None if value is None else format(value, "f")


@router.get(
    "/assets/{asset_id}/open-interest",
    response_model=ResponseEnvelope[list[OpenInterestOut]],
    summary="Get perpetual open-interest history for an asset (404 for SPOT)",
)
async def get_asset_open_interest(
    asset_id: UUID,
    asset_repo: AssetRepo,
    oi_repo: OpenInterestRepo,
    limit: int = Query(100, ge=1, le=1000, description="Max most-recent OI observations"),
) -> ResponseEnvelope[list[OpenInterestOut]]:
    asset = await asset_repo.get_by_id(asset_id)
    if asset is None:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.RESOURCE_NOT_FOUND,
            f"Asset {asset_id} not found",
        )
    if asset.instrument_type != "PERPETUAL":
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.RESOURCE_NOT_FOUND,
            f"Asset {asset_id} ({asset.symbol}) is SPOT — open interest only exists for PERPETUAL instruments",
        )
    rows = await oi_repo.get_open_interest_history(asset_id, limit)
    return ok([OpenInterestOut.model_validate(r, from_attributes=True) for r in rows])
