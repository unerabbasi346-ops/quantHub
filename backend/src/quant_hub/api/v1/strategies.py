# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
#   §API Standards: REST/FastAPI, versioned, Pydantic validation, OpenAPI.
# Doc 08 — Frontend Architecture (QH-008 v1.0) §API Layer: answers the
#   strategies feature's existing GET /v1/strategies call (features/strategies).
# Doc 10 — API Specification (QH-010 v1.0): shared ResponseEnvelope.
# Doc 14 §10.2 Strategy Governance (§10.2.5 versioning), §10.6.4 Signal
#   Recording, §10.3 Backtesting Engine — the read shapes this exposes.
# Doc 15 §11.1.5 — signals feed position sizing (context for the value field).
# Per Doc 00 §14.11
#
# Step 4.5, the Strategies + Backtests vertical slice: read endpoints over
# Phase 2's core.strategies / core.signals and Phase 3.7's analytics.backtests
# (all written by the real Signal->Order loop and backtest engine).
#
# JUDGMENT CALLS (Doc 00 §14.5/§14.7 — flagged):
#  1. snake_case JSON + Decimal-as-string, identical to Steps 4.2–4.4. A
#     signal's `value` is NUMERIC and a backtest's total_return/final_capital
#     are NUMERIC, so they are STRINGS here. The Step 0.5 strategies types
#     (camelCase, a speculative status union) are reconciled in the frontend.
#  2. HONEST F-9 REPRESENTATION (versioning gap — called out explicitly). Doc
#     14 §10.2.5 requires immutable version history + rollback, but the Step
#     1.1 schema keys core.strategies on `name` alone with no version-history
#     table, so re-registration OVERWRITES the prior version row in place
#     (F-9). StrategyOut therefore exposes `version` as the CURRENT registered
#     version ONLY — there is no history to list. This endpoint deliberately
#     offers no "versions" collection and no per-version lookup, so it cannot
#     imply a history that does not exist; the frontend annotates the version
#     column to say so. `status` is a free-form VARCHAR (real rows carry
#     'ACTIVE'; schema default 'INACTIVE') — typed as a plain string, not a
#     fixed enum the data does not honor.
#  3. OPAQUE PASSTHROUGH (P-1): a strategy's `config` and a signal's `metadata`
#     are stored verbatim and never interpreted by the platform (P-1). They are
#     passed through as JSON objects, not re-typed at the API boundary. A
#     backtest's `results` is likewise passed through: it is the engine's own
#     self-describing §10.3.7 summary (bars/fills/realized+unrealized P&L/
#     determinism hash) whose Decimal figures are already stored as strings.
#  4. SIGNAL FEED LIMIT: the signals feed is bounded (default 100, max 1000,
#     most-recent-first) — a strategy can have hundreds of immutable signal
#     events (481 per backtest strategy in the real Phase 3A data); an
#     unbounded feed is neither useful nor safe to serialize wholesale.
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query, status
from pydantic import BaseModel, field_serializer

from quant_hub.api.dependencies import (
    AssetRepo,
    BacktestRepo,
    DbSession,
    PortfolioRepo,
    PositionRepo,
    SignalRepo,
    StrategyRepo,
)
from quant_hub.api.envelope import ApiError, ErrorCode, ResponseEnvelope, ok
from quant_hub.domain.strategy_engine.entities import RecordedSignal, RegisteredStrategy
from quant_hub.domain.strategy_engine.implied_sizing import (
    assert_direction_matches_value,
    compute_direction,
    compute_implied_leverage,
    compute_implied_size_usdt,
)

# The lifecycle states the Activate/Deactivate control may set (Doc 14
# §10.2.6). Kept a small explicit allow-list — status is a free-form VARCHAR in
# the schema (F-9/Step 4.5), but the WRITE path validates against exactly the
# two states the dashboard control exposes, so an arbitrary string can never be
# written through this endpoint.
_SETTABLE_STATUSES = {"ACTIVE", "INACTIVE"}

router = APIRouter(tags=["strategies"])


class StrategyOut(BaseModel):
    """API shape of a core.strategies row — Doc 14 §10.2 / Doc 09 field names.

    `version` is the CURRENT registered version only (F-9 — no version history
    is retained by the schema; see module judgment call #2). `status` is a
    free-form string. `config` is opaque (P-1), passed through verbatim.
    """

    id: UUID
    name: str
    description: str | None
    version: str
    status: str
    config: dict[str, Any]
    portfolio_id: UUID | None
    created_at: datetime | None
    updated_at: datetime | None

    @classmethod
    def from_registered(cls, strategy: RegisteredStrategy) -> "StrategyOut":
        return cls(
            id=strategy.id,
            name=strategy.name,
            description=strategy.description,
            version=strategy.version,
            status=strategy.status,
            config=dict(strategy.config),
            portfolio_id=strategy.portfolio_id,
            created_at=strategy.created_at,
            updated_at=strategy.updated_at,
        )


class SignalOut(BaseModel):
    """API shape of a core.signals row — Doc 14 §10.6.4 (immutable signal
    event). `value` (NUMERIC signed conviction, Doc 15 §11.1.5) renders as a
    string; `metadata` is opaque (P-1), passed through verbatim.

    ── IMPLIED SIZING FIELDS (task-scoped addition) ────────────────────────
    `direction`, `implied_size_usdt`, `implied_leverage` are all COMPUTED
    ON-THE-FLY at request time — Doc 07 §Layers pure functions in
    domain/strategy_engine/implied_sizing.py — and stored NOWHERE in
    core.signals. Deliberately not persisted columns:
      1. core.signals is a P-5 immutable append-only event log with no
         update path (migration 7c7482e4e00a) — freezing a capital-derived
         figure at signal-write time would go stale the instant the
         portfolio's configured_capital is later changed (PUT
         .../capital), and there is no update path to refresh it.
      2. Computing at read time means every signal's implied size always
         reflects the CURRENT configured_capital, exactly satisfying "any
         live signal recalculation should use the new value" without a
         schema migration or a background recompute job.
      3. `direction` is 100% derived from the already-stored `value` (its
         sign) — persisting a column for it would only invite drift.
    These are explicitly SIZING SUGGESTIONS derived from signal conviction
    and configured capital — NOT executed positions, and NOT the platform's
    real governed position-sizing pipeline (domain/portfolio/sizing.py,
    which sizes off post-construction target weights under real risk
    constraints). `implied_size_usdt` is null when the strategy has no
    linked portfolio or that portfolio has no configured_capital set (F-19:
    never fabricated from an assumed capital figure).
    """

    id: UUID
    strategy_id: UUID
    asset_id: UUID
    value: Decimal
    ts: datetime
    validation_status: str
    metadata: dict[str, Any]
    created_at: datetime | None
    direction: str
    implied_size_usdt: Decimal | None
    implied_leverage: Decimal

    @field_serializer("value", "implied_size_usdt", "implied_leverage", when_used="json")
    def _serialize_decimal(self, value: Decimal | None) -> str | None:
        return None if value is None else format(value, "f")

    @classmethod
    def from_recorded(
        cls,
        signal: RecordedSignal,
        *,
        configured_capital: Decimal | None,
        implied_leverage: Decimal,
    ) -> "SignalOut":
        direction = compute_direction(signal.value)
        assert_direction_matches_value(signal.value, direction)  # Task 4 consistency check
        return cls(
            id=signal.id,
            strategy_id=signal.strategy_id,
            asset_id=signal.asset_id,
            value=signal.value,
            ts=signal.ts,
            validation_status=signal.validation_status,
            metadata=dict(signal.metadata),
            created_at=signal.created_at,
            direction=direction,
            implied_size_usdt=compute_implied_size_usdt(signal.value, configured_capital),
            implied_leverage=implied_leverage,
        )


class BacktestOut(BaseModel):
    """API shape of an analytics.backtests row — Doc 14 §10.3.

    Promoted scalar columns plus the self-describing §10.3.7 `results` summary
    (fills, realized/unrealized P&L, determinism hash). total_return/
    trade_count/results/reproducibility_hash are null for a not-yet-COMPLETED
    (RUNNING) backtest. Decimal scalars render as strings; `results` figures
    are already strings inside the stored JSONB."""

    id: UUID
    strategy_id: UUID | None
    name: str
    status: str
    total_return: Decimal | None
    trade_count: int | None
    final_capital: Decimal | None
    reproducibility_hash: str | None
    results: dict[str, Any] | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    @field_serializer("total_return", "final_capital", when_used="json")
    def _serialize_decimal(self, value: Decimal | None) -> str | None:
        return None if value is None else format(value, "f")


def _serialize_backtest_row(row: dict[str, Any]) -> BacktestOut:
    # The repo returns a plain dict (start_date/end_date etc. are not needed by
    # the list view). model_validate maps the matching keys; extras ignored.
    return BacktestOut.model_validate(row)


@router.get(
    "/strategies",
    response_model=ResponseEnvelope[list[StrategyOut]],
    summary="List all registered strategies (the registry)",
)
async def list_strategies(repo: StrategyRepo) -> ResponseEnvelope[list[StrategyOut]]:
    strategies = await repo.list_all()
    return ok([StrategyOut.from_registered(s) for s in strategies])


@router.get(
    "/strategies/{strategy_id}",
    response_model=ResponseEnvelope[StrategyOut],
    summary="Get a single strategy by id",
)
async def get_strategy(strategy_id: UUID, repo: StrategyRepo) -> ResponseEnvelope[StrategyOut]:
    strategy = await repo.get_by_id(strategy_id)
    if strategy is None:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.RESOURCE_NOT_FOUND,
            f"Strategy {strategy_id} not found",
        )
    return ok(StrategyOut.from_registered(strategy))


@router.get(
    "/strategies/{strategy_id}/signals",
    response_model=ResponseEnvelope[list[SignalOut]],
    summary="Get the recent signal feed for a strategy, with implied sizing",
)
async def get_strategy_signals(
    strategy_id: UUID,
    strategy_repo: StrategyRepo,
    signal_repo: SignalRepo,
    portfolio_repo: PortfolioRepo,
    asset_repo: AssetRepo,
    position_repo: PositionRepo,
    limit: int = Query(100, ge=1, le=1000, description="Max most-recent signals"),
) -> ResponseEnvelope[list[SignalOut]]:
    # 404 on an unknown strategy so a client distinguishes "no such strategy"
    # from "strategy exists but has emitted no signals" (a legitimate empty).
    strategy = await strategy_repo.get_by_id(strategy_id)
    if strategy is None:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.RESOURCE_NOT_FOUND,
            f"Strategy {strategy_id} not found",
        )
    signals = await signal_repo.list_by_strategy(strategy_id, limit)

    # ── Implied sizing inputs (Task 2/3) ─────────────────────────────────
    # configured_capital: F-19-honest — None unless the strategy is linked to
    # a portfolio that has actually had capital configured via PUT
    # .../capital. Read fresh on every request, so a just-updated capital
    # figure is reflected immediately (no caching, no staleness).
    configured_capital: Decimal | None = None
    if strategy.portfolio_id is not None:
        portfolio = await portfolio_repo.get_by_id(strategy.portfolio_id)
        if portfolio is not None:
            configured_capital = portfolio.configured_capital

    # implied_leverage per signal: strategy.config["leverage"] short-circuits
    # everything (checked first, cheaply, per signal); only when absent do we
    # need each signal's asset instrument_type + (for PERPETUAL) its open
    # position's real leverage — resolved once per DISTINCT asset_id, mirroring
    # the dedup pattern in api/v1/portfolio.py's position enrichment.
    assets: dict[UUID, Any] = {}
    positions: dict[UUID, Any] = {}

    async def _implied_leverage_for(asset_id: UUID) -> Decimal:
        if asset_id not in assets:
            assets[asset_id] = await asset_repo.get_by_id(asset_id)
        asset = assets[asset_id]
        instrument_type = asset.instrument_type if asset is not None else None
        position_leverage = None
        if instrument_type == "PERPETUAL" and strategy.portfolio_id is not None:
            if asset_id not in positions:
                positions[asset_id] = await position_repo.get_by_portfolio_and_asset(
                    strategy.portfolio_id, asset_id
                )
            position = positions[asset_id]
            position_leverage = position.leverage if position is not None else None
        return compute_implied_leverage(
            strategy.config, instrument_type=instrument_type, position_leverage=position_leverage
        )

    out: list[SignalOut] = []
    for s in signals:
        leverage = await _implied_leverage_for(s.asset_id)
        out.append(
            SignalOut.from_recorded(s, configured_capital=configured_capital, implied_leverage=leverage)
        )
    return ok(out)


@router.get(
    "/strategies/{strategy_id}/backtests",
    response_model=ResponseEnvelope[list[BacktestOut]],
    summary="Get backtest results for a strategy",
)
async def get_strategy_backtests(
    strategy_id: UUID,
    strategy_repo: StrategyRepo,
    backtest_repo: BacktestRepo,
) -> ResponseEnvelope[list[BacktestOut]]:
    if await strategy_repo.get_by_id(strategy_id) is None:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.RESOURCE_NOT_FOUND,
            f"Strategy {strategy_id} not found",
        )
    rows = await backtest_repo.list_by_strategy(strategy_id)
    return ok([_serialize_backtest_row(row) for row in rows])


class StrategyStatusIn(BaseModel):
    """Body for the Activate/Deactivate control — a governed §10.2.6 transition."""

    status: str


@router.patch(
    "/strategies/{strategy_id}/status",
    response_model=ResponseEnvelope[StrategyOut],
    summary="Activate/deactivate a strategy (governed lifecycle transition)",
)
async def set_strategy_status(
    strategy_id: UUID,
    body: StrategyStatusIn,
    repo: StrategyRepo,
    session: DbSession,
) -> ResponseEnvelope[StrategyOut]:
    # The first real WRITE endpoint in the dashboard. Validate the requested
    # state against the explicit allow-list (§10.2.6 governed transition), 404
    # on an unknown strategy, then commit — repositories never commit
    # (transaction ownership belongs to the API layer, Doc 07).
    requested = body.status.strip().upper()
    if requested not in _SETTABLE_STATUSES:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.VALIDATION_ERROR,
            f"status must be one of {sorted(_SETTABLE_STATUSES)}, got {body.status!r}",
        )
    updated = await repo.set_status(strategy_id, requested)
    if updated is None:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.RESOURCE_NOT_FOUND,
            f"Strategy {strategy_id} not found",
        )
    await session.commit()
    return ok(StrategyOut.from_registered(updated))
