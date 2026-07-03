# Governing specification: Doc 15 §11.2 — Portfolio Construction; P-1, P-13
# Per Doc 00 §14.11
#
# No database needed — pure computation on domain/portfolio/construction.py +
# application/portfolio/construction_service.py + the reference methodology.
#
# F-12 inversion: Construction runs FIRST and aggregates constituent strategy
# CONVICTIONS (Signal.value) into a portfolio target weight — it no longer
# consumes already-sized PositionSizingDecision outputs.
from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from quant_hub.application.portfolio.construction_service import PortfolioConstructionService
from quant_hub.application.portfolio.reference_constructors.weighted_sum import (
    WeightedSumConstructor,
)
from quant_hub.domain.market_data.entities import AssetRef
from quant_hub.domain.portfolio.construction import StrategyContribution
from quant_hub.domain.strategy_engine.entities import Signal

_ASSET = AssetRef(symbol="BTC/USDT", exchange="binance", asset_class="crypto")
_OTHER_ASSET = AssetRef(symbol="ETH/USDT", exchange="binance", asset_class="crypto")
_TS = datetime(2026, 7, 3, tzinfo=timezone.utc)
_SERVICE = PortfolioConstructionService()


def _contribution(asset: AssetRef, conviction: str, weight: str = "1") -> StrategyContribution:
    return StrategyContribution(
        strategy_id=uuid4(),
        strategy_weight=Decimal(weight),
        signal=Signal(asset=asset, value=Decimal(conviction), ts=_TS),
    )


# ── Single-strategy pass-through (today's only exercisable case, Step 2.4) ──

def test_single_strategy_weight_one_passes_conviction_through() -> None:
    # With one strategy at weight=1, target_weight == the raw conviction —
    # the construction output Position Sizing (Step 3.1) then sizes.
    contribution = _contribution(_ASSET, "0.05", weight="1")
    result = WeightedSumConstructor().construct([contribution])

    assert result.target_weight == Decimal("0.05")
    assert result.asset == _ASSET


def test_single_strategy_negative_conviction_produces_negative_weight() -> None:
    result = WeightedSumConstructor().construct([_contribution(_ASSET, "-0.025")])
    assert result.target_weight == Decimal("-0.025")


# ── Multi-strategy generalization (synthetic — no second real strategy exists yet) ──

def test_multi_strategy_aggregation_sums_weighted_contributions() -> None:
    # Two synthetic strategies, unequal strategy_weight, same instrument.
    c1 = _contribution(_ASSET, "0.04", weight="0.6")
    c2 = _contribution(_ASSET, "0.02", weight="0.4")
    result = WeightedSumConstructor().construct([c1, c2])

    # 0.6*0.04 + 0.4*0.02 = 0.024 + 0.008 = 0.032
    assert result.target_weight == Decimal("0.032")


def test_multi_strategy_contributions_can_offset() -> None:
    long = _contribution(_ASSET, "0.05", weight="1")
    short = _contribution(_ASSET, "-0.05", weight="1")
    result = WeightedSumConstructor().construct([long, short])
    assert result.target_weight == Decimal("0")


def test_aggregation_transparency_preserves_all_contributions() -> None:
    # §11.2.6 "Aggregation Transparency": each strategy's contribution visible.
    c1 = _contribution(_ASSET, "0.04", weight="0.6")
    c2 = _contribution(_ASSET, "0.02", weight="0.4")
    result = WeightedSumConstructor().construct([c1, c2])

    assert result.contributions == (c1, c2)


def test_empty_contributions_rejected() -> None:
    with pytest.raises(ValueError):
        WeightedSumConstructor().construct([])


# ── Service: multi-instrument grouping ──────────────────────────────────────

def test_service_groups_contributions_by_instrument() -> None:
    contributions = [
        _contribution(_ASSET, "0.05", weight="1"),
        _contribution(_OTHER_ASSET, "0.01", weight="1"),
    ]
    results = _SERVICE.construct_portfolio(WeightedSumConstructor(), contributions)

    by_symbol = {r.asset.symbol: r for r in results}
    assert len(results) == 2
    assert by_symbol["BTC/USDT"].target_weight == Decimal("0.05")
    assert by_symbol["ETH/USDT"].target_weight == Decimal("0.01")


def test_service_aggregates_multiple_strategies_same_instrument() -> None:
    contributions = [
        _contribution(_ASSET, "0.04", weight="0.6"),
        _contribution(_ASSET, "0.02", weight="0.4"),
    ]
    results = _SERVICE.construct_portfolio(WeightedSumConstructor(), contributions)

    assert len(results) == 1
    assert results[0].target_weight == Decimal("0.032")


# ── Determinism (§11.2.11 / P-13) and immutability (§11.2.10 / P-2) ─────────

def test_construction_is_deterministic() -> None:
    c1 = _contribution(_ASSET, "0.04", weight="0.6")
    c2 = _contribution(_ASSET, "0.02", weight="0.4")
    r1 = WeightedSumConstructor().construct([c1, c2])
    r2 = WeightedSumConstructor().construct([c1, c2])
    assert r1 == r2


def test_result_is_frozen_immutable() -> None:
    result = WeightedSumConstructor().construct([_contribution(_ASSET, "0.05")])
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.target_weight = Decimal("0")  # type: ignore[misc]
