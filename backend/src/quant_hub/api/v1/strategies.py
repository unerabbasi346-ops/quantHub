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

import bisect
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, Query, Response, status
from pydantic import BaseModel, field_serializer
from sqlalchemy import text as sa_text

from quant_hub.api.dependencies import (
    AssetRepo,
    BacktestRepo,
    DbSession,
    FundingRateRepo,
    MLModelRepo,
    OHLCVRepo,
    OpenInterestRepo,
    PortfolioRepo,
    PositionRepo,
    SignalRepo,
    StrategyRepo,
)
from quant_hub.api.envelope import ApiError, ErrorCode, ResponseEnvelope, ok
from quant_hub.domain.market_data.entities import AssetRef
from quant_hub.domain.strategy_engine.entities import RecordedSignal, RegisteredStrategy
from quant_hub.domain.strategy_engine.entities import Signal as DomainSignal
from quant_hub.domain.strategy_engine.implied_sizing import (
    assert_direction_matches_value,
    compute_direction,
    compute_implied_leverage,
    compute_implied_size_usdt,
)
from quant_hub.domain.strategy_engine.strategy import MarketDataView
from quant_hub.infrastructure.backtesting.point_in_time_view import PointInTimeMarketDataView
from quant_hub.ml.feature_engineering import compute_signal_features, feature_names_for
from quant_hub.ml.ml_engine import XGBoostMetaLabeler
from quant_hub.ml.model_factory import create_model

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


@dataclass(frozen=True)
class MLSignalInsights:
    """Read-time-only ML enrichment for one signal — see SignalOut's ML
    SUGGESTION FIELDS docstring for the full set of judgment calls this
    represents. Never persisted anywhere.
    """

    confidence: Decimal | None
    probability: Decimal | None
    direction_agreement: bool | None
    tp_suggestion: Decimal | None
    sl_suggestion: Decimal | None
    breakeven: Decimal | None


_TP_STDEV_MULTIPLE = Decimal("2")    # flagged convention, see SignalOut docstring point 4
_SL_STDEV_MULTIPLE = Decimal("1.5")  # flagged convention, see SignalOut docstring point 4
_VOLATILITY_WINDOW = 20              # task spec: "20-period price std dev"


async def _compute_ml_insights(
    signal: DomainSignal, model: XGBoostMetaLabeler, view: MarketDataView, interval: str
) -> MLSignalInsights | None:
    """Real bars + a real, real-feature-engineered model prediction — never
    fabricated. Returns None when fewer than _VOLATILITY_WINDOW bars exist
    (an honest "not enough history" case, not a fabricated volatility), and
    also None when the deployed model rejects the feature vector (ValueError
    — e.g. a model trained on a different feature set/version). Degrading to
    "no insights" is the honest outcome for a genuine feature-shape
    mismatch, not a 500.

    The feature vector is built by ml/feature_engineering.py's
    compute_signal_features — 8 real features (price momentum, volatility,
    volume ratio, funding rate, OI change, signal conviction), replacing the
    old single-feature `[signal.value]` placeholder (see SignalOut docstring
    point 2, now resolved). `view` must already be point-in-time-correct for
    `signal.ts` — this function trusts it and does not re-check.
    """
    bars = list(await view.latest_bars(signal.asset, interval, limit=_VOLATILITY_WINDOW))
    if len(bars) < _VOLATILITY_WINDOW:
        return None
    closes = [b.close for b in bars[-_VOLATILITY_WINDOW:]]
    entry_price = closes[-1]
    mean = sum(closes, Decimal(0)) / Decimal(len(closes))
    variance = sum(((c - mean) ** 2 for c in closes), Decimal(0)) / Decimal(len(closes))
    stdev = variance.sqrt()

    features = await compute_signal_features(signal, view, interval)
    # Column set/order matches the instrument type the model was trained for
    # (SPOT models: 6 features; PERPETUAL: 8) — feature_engineering owns both.
    names = feature_names_for(signal.asset.instrument_type)
    X = pd.DataFrame([[features[name] for name in names]], columns=list(names))
    try:
        probability = float(model.predict(X)[0])
    except ValueError:
        return None
    confidence = max(probability, 1 - probability)

    return MLSignalInsights(
        confidence=Decimal(str(confidence)),
        probability=Decimal(str(probability)),
        direction_agreement=probability > 0.5,
        tp_suggestion=entry_price + _TP_STDEV_MULTIPLE * stdev,
        sl_suggestion=entry_price - _SL_STDEV_MULTIPLE * stdev,
        breakeven=entry_price,
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

    ── ML SUGGESTION FIELDS (task-scoped addition, heavily flagged) ────────
    `ml_confidence`/`ml_probability`/`ml_direction_agreement` are populated
    ONLY when a DEPLOYED analytics.ml_models row of type
    "XGBoost_MetaLabeler" exists (api/ml.py's /train endpoint) — otherwise
    every ml_* field is null (never a fabricated figure). Even when present:

      1. NEVER WRITTEN TO Signal.metadata. Doc 14 §10.6.4 / P-1 docstring on
         domain/strategy_engine/entities.py::Signal.metadata is explicit:
         that field is the STRATEGY PLUGIN's own opaque space, recorded
         verbatim and "NEVER interpreted" by the platform. Having THIS
         platform-level ML feature write into it would violate that
         contract on every signal, strategy-specific or not. These fields
         are computed at READ TIME onto the API response instead — the
         exact same pattern already established for direction/
         implied_size_usdt/implied_leverage above, never persisted, never
         touching core.signals.
      2. REAL FEATURE ENGINEERING (resolves the Task 0 ML-folder audit
         finding): the feature vector is ml/feature_engineering.py's
         compute_signal_features — 8 real features (5/20-period price
         momentum, 20-period volatility, volume ratio, funding rate, OI
         change, signal conviction and its magnitude) built from a
         point-in-time-correct MarketDataView scoped to this signal's own
         `ts` (bars/funding/OI truncated to <= ts before construction, so
         the model never sees data from after the signal it's scoring).
      3. ml_direction_agreement approximates "does ML agree with this
         signal" as predicted_probability > 0.5 — XGBoostMetaLabeler is a
         META-LABELER (predicts P(this already-decided trade is
         profitable)), not a directional classifier, so it has no
         independent "direction" opinion to compare against the signal's
         sign. This is the closest honest proxy, not a literal agreement
         check.
      4. ml_tp_suggestion/ml_sl_suggestion are REAL: entry_price is the
         latest real bar's close, volatility is the real sample stdev of
         the last 20 real closes (get_bars_range/get_bars), TP = entry +
         2×stdev, SL = entry − 1.5×stdev (a 2:1 reward:risk convention,
         flagged constants — Doc 14 specifies no particular multiplier).
         Both are null when fewer than 20 bars exist for the asset.
      5. ml_breakeven = entry_price exactly. This platform's simulated
         fills always carry zero commission (F-16) — an honest breakeven
         estimate given real zero fees, not a fabricated fee assumption.
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
    ml_confidence: Decimal | None = None
    ml_probability: Decimal | None = None
    ml_direction_agreement: bool | None = None
    ml_tp_suggestion: Decimal | None = None
    ml_sl_suggestion: Decimal | None = None
    ml_breakeven: Decimal | None = None

    @field_serializer(
        "value", "implied_size_usdt", "implied_leverage", "ml_confidence",
        "ml_probability", "ml_tp_suggestion", "ml_sl_suggestion", "ml_breakeven",
        when_used="json",
    )
    def _serialize_decimal(self, value: Decimal | None) -> str | None:
        return None if value is None else format(value, "f")

    @classmethod
    def from_recorded(
        cls,
        signal: RecordedSignal,
        *,
        configured_capital: Decimal | None,
        implied_leverage: Decimal,
        ml_insights: "MLSignalInsights | None" = None,
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
            ml_confidence=ml_insights.confidence if ml_insights else None,
            ml_probability=ml_insights.probability if ml_insights else None,
            ml_direction_agreement=ml_insights.direction_agreement if ml_insights else None,
            ml_tp_suggestion=ml_insights.tp_suggestion if ml_insights else None,
            ml_sl_suggestion=ml_insights.sl_suggestion if ml_insights else None,
            ml_breakeven=ml_insights.breakeven if ml_insights else None,
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
    # The instrument this backtest ran against — read from config->>'symbol'
    # (BacktestConfig.symbol was already stored in the config JSONB at
    # creation time; this just promotes it to a top-level field). None for
    # a pre-existing row whose config predates this field being read.
    symbol: str | None = None
    start_date: datetime | None
    end_date: datetime | None
    total_return: Decimal | None
    trade_count: int | None
    final_capital: Decimal | None
    reproducibility_hash: str | None
    results: dict[str, Any] | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    # Rule 5 (Engine step): BTC/USDT buy-and-hold over the same window, for
    # comparing against total_return. None on a backtest run before that
    # column existed, or when no benchmark instrument was ingested.
    benchmark_return: Decimal | None = None

    @field_serializer("total_return", "final_capital", "benchmark_return", when_used="json")
    def _serialize_decimal(self, value: Decimal | None) -> str | None:
        return None if value is None else format(value, "f")


def _serialize_backtest_row(row: dict[str, Any]) -> BacktestOut:
    # The repo returns a plain dict including start_date/end_date (the
    # backtest's requested window) — model_validate maps matching keys.
    return BacktestOut.model_validate(row)


@router.get(
    "/strategies",
    response_model=ResponseEnvelope[list[StrategyOut]],
    summary="List all registered strategies (the registry)",
)
async def list_strategies(repo: StrategyRepo, response: Response) -> ResponseEnvelope[list[StrategyOut]]:
    # Perf pass: the strategy registry rarely changes mid-session — 30s
    # cache, called from the dashboard strategy hero + every strategies page.
    response.headers["Cache-Control"] = "public, max-age=30"
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
    bars_repo: OHLCVRepo,
    funding_repo: FundingRateRepo,
    oi_repo: OpenInterestRepo,
    ml_repo: MLModelRepo,
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

    # ── ML suggestion inputs (Task 2C) — see SignalOut's ML SUGGESTION
    # FIELDS docstring for the full set of flagged judgment calls. Loaded
    # ONCE per request (not per signal): the deployed model artifact and,
    # per DISTINCT asset_id, its most recent _VOLATILITY_WINDOW bars.
    # Per-instrument-type models (SPOT: 6 features, PERPETUAL: 8); the
    # un-suffixed legacy "XGBoost_MetaLabeler" registration is the fallback
    # so pre-split deployments keep serving until both retrains have run.
    ml_models: dict[str, XGBoostMetaLabeler] = {}
    for _itype in ("SPOT", "PERPETUAL"):
        ml_record = await ml_repo.get_latest_deployed(f"XGBoost_MetaLabeler_{_itype}")
        if ml_record is None:
            ml_record = await ml_repo.get_latest_deployed("XGBoost_MetaLabeler")
        if ml_record is None:
            continue
        try:
            candidate = create_model("XGBoost_MetaLabeler", dict(ml_record.config))
            candidate.load_model(ml_record.artifact_path)
            ml_models[_itype] = candidate
        except (FileNotFoundError, OSError, ValueError):
            # The registry row exists but its artifact file is missing/
            # unreadable — degrade to "no model available" rather than a
            # 500, matching the "never fabricated" mandate (no insights is
            # honest; a crash is not).
            pass

    interval = str(strategy.config.get("interval", "1h"))
    # Per-distinct-asset caches for point-in-time view construction: full
    # available history fetched ONCE per asset (not per signal), then
    # locally truncated to <= each signal's own ts below — §10.3.4
    # point-in-time correctness (no lookahead), same dedup-per-distinct-id
    # pattern as _implied_leverage_for above.
    asset_refs: dict[UUID, AssetRef] = {}
    bars_by_asset: dict[UUID, list[Any]] = {}
    funding_by_asset: dict[UUID, list[Any]] = {}
    oi_by_asset: dict[UUID, list[Any]] = {}

    async def _view_for(asset_id: UUID, as_of: datetime) -> tuple[AssetRef, MarketDataView] | None:
        if asset_id not in assets:
            assets[asset_id] = await asset_repo.get_by_id(asset_id)
        asset = assets[asset_id]
        if asset is None:
            return None
        if asset_id not in asset_refs:
            asset_refs[asset_id] = AssetRef(
                symbol=asset.symbol, exchange=asset.exchange,
                asset_class="crypto", instrument_type=asset.instrument_type,
            )
            bars_by_asset[asset_id] = await bars_repo.get_bars(asset_id, interval, limit=100_000)
            funding_by_asset[asset_id] = await funding_repo.get_funding_rates(asset_id, limit=100_000)
            oi_by_asset[asset_id] = await oi_repo.get_open_interest_history(asset_id, limit=100_000)
        all_bars = bars_by_asset[asset_id]
        # Bars are oldest->newest; truncate to strictly-before-or-at as_of so
        # the view can never see a bar the signal itself postdates (no
        # lookahead) — bisect on the sorted ts column.
        idx = bisect.bisect_right([b.ts for b in all_bars], as_of)
        return asset_refs[asset_id], PointInTimeMarketDataView(
            bars=all_bars[:idx],
            asset=asset_refs[asset_id],
            interval=interval,
            funding=funding_by_asset[asset_id],
            open_interest=oi_by_asset[asset_id],
            as_of=as_of,
        )

    out: list[SignalOut] = []
    for s in signals:
        leverage = await _implied_leverage_for(s.asset_id)
        ml_insights = None
        if ml_models:
            resolved = await _view_for(s.asset_id, s.ts)
            if resolved is not None:
                asset_ref, view = resolved
                ml_model = ml_models.get(asset_ref.instrument_type)
                if ml_model is not None:
                    domain_signal = DomainSignal(asset=asset_ref, value=s.value, ts=s.ts)
                    ml_insights = await _compute_ml_insights(domain_signal, ml_model, view, interval)
        out.append(
            SignalOut.from_recorded(
                s, configured_capital=configured_capital, implied_leverage=leverage, ml_insights=ml_insights
            )
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


class MonthlyReturnOut(BaseModel):
    """One month's REAL realized trading P&L for a strategy, aggregated
    server-side from core.executions rows (via core.orders.strategy_id).
    Absolute P&L in the execution currency, not a percent — the platform has
    no per-month capital ledger, and fabricating a denominator would violate
    Doc 00 §14.5 data honesty. NUMERIC as string, matching every other money
    field in this module.
    """

    year: int
    month: int  # 1-12
    realized_pnl: Decimal
    trade_count: int

    @field_serializer("realized_pnl")
    def _serialize_pnl(self, v: Decimal) -> str:
        return str(v)


@router.get(
    "/strategies/{strategy_id}/monthly-returns",
    response_model=ResponseEnvelope[list[MonthlyReturnOut]],
    summary="Monthly realized P&L for a strategy, computed from executions",
)
async def get_strategy_monthly_returns(
    strategy_id: UUID,
    strategy_repo: StrategyRepo,
    session: DbSession,
) -> ResponseEnvelope[list[MonthlyReturnOut]]:
    """One row per calendar month with at least one execution — bounded by
    calendar time (60 rows for 5 years), not by execution count, so the
    monthly heatmap never needs to page through the signal feed's 1000-row
    cap."""
    if await strategy_repo.get_by_id(strategy_id) is None:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.RESOURCE_NOT_FOUND,
            f"Strategy {strategy_id} not found",
        )
    result = await session.execute(
        sa_text(
            """
            SELECT EXTRACT(YEAR FROM e.executed_at)::int AS year,
                   EXTRACT(MONTH FROM e.executed_at)::int AS month,
                   COALESCE(SUM(e.realized_pnl), 0) AS realized_pnl,
                   COUNT(*)::int AS trade_count
            FROM core.executions e
            JOIN core.orders o ON o.id = e.order_id
            WHERE o.strategy_id = :strategy_id AND e.realized_pnl IS NOT NULL
            GROUP BY 1, 2
            ORDER BY 1, 2
            """
        ),
        {"strategy_id": strategy_id},
    )
    return ok([
        MonthlyReturnOut(
            year=row.year, month=row.month,
            realized_pnl=row.realized_pnl, trade_count=row.trade_count,
        )
        for row in result
    ])


class ComputedMetricsOut(BaseModel):
    """API shape of analytics.backtest_computed_metrics (F-21, migration
    c7d3f9a2e5b8) — the Doc 14 §10.3.7 metric suite for a strategy's most
    recent COMPLETED backtest. Every field is `null` when it genuinely could
    not be computed (see domain/analytics/metrics_engine.py's insufficient-
    data gating and the infinite-profit_factor persistence note) — never a
    fabricated number.
    """

    backtest_id: UUID
    win_rate: Decimal | None
    sharpe_ratio: Decimal | None
    sortino_ratio: Decimal | None
    max_drawdown_pct: Decimal | None
    calmar_ratio: Decimal | None
    profit_factor: Decimal | None
    expectancy_per_trade: Decimal | None

    @field_serializer(
        "win_rate", "sharpe_ratio", "sortino_ratio", "max_drawdown_pct",
        "calmar_ratio", "profit_factor", "expectancy_per_trade", when_used="json",
    )
    def _serialize_decimal(self, value: Decimal | None) -> str | None:
        return None if value is None else format(value, "f")


@router.get(
    "/strategies/{strategy_id}/metrics",
    response_model=ResponseEnvelope[ComputedMetricsOut],
    summary="Get computed performance metrics for a strategy's most recent completed backtest",
)
async def get_strategy_metrics(
    strategy_id: UUID,
    strategy_repo: StrategyRepo,
    backtest_repo: BacktestRepo,
) -> ResponseEnvelope[ComputedMetricsOut]:
    if await strategy_repo.get_by_id(strategy_id) is None:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.RESOURCE_NOT_FOUND,
            f"Strategy {strategy_id} not found",
        )
    latest = await backtest_repo.get_latest_completed_by_strategy(strategy_id)
    if latest is None:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.RESOURCE_NOT_FOUND,
            f"Strategy {strategy_id} has no completed backtest to compute metrics from",
        )
    metrics = await backtest_repo.get_computed_metrics(latest["id"])
    if metrics is None:
        # A COMPLETED backtest that predates this feature (ran before
        # migration c7d3f9a2e5b8) has no computed-metrics row at all — every
        # field renders as an honest null rather than raising.
        return ok(
            ComputedMetricsOut(
                backtest_id=latest["id"], win_rate=None, sharpe_ratio=None, sortino_ratio=None,
                max_drawdown_pct=None, calmar_ratio=None, profit_factor=None, expectancy_per_trade=None,
            )
        )
    return ok(
        ComputedMetricsOut(
            backtest_id=metrics.backtest_run_id,
            win_rate=metrics.win_rate,
            sharpe_ratio=metrics.sharpe_ratio,
            sortino_ratio=metrics.sortino_ratio,
            max_drawdown_pct=metrics.max_drawdown_pct,
            calmar_ratio=metrics.calmar_ratio,
            profit_factor=metrics.profit_factor,
            expectancy_per_trade=metrics.expectancy_per_trade,
        )
    )


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
