# Governing specification: Doc 15 §11.2 — Portfolio Construction; P-1, P-13
# Per Doc 00 §14.11
#
# No database needed — pure computation on domain/portfolio/construction.py +
# application/portfolio/construction_service.py + the reference methodology.
from __future__ import annotations

import dataclasses
from decimal import Decimal
from uuid import uuid4

import pytest

from quant_hub.application.portfolio.construction_service import PortfolioConstructionService
from quant_hub.application.portfolio.reference_constructors.weighted_sum import (
    WeightedSumConstructor,
)
from quant_hub.domain.market_data.entities import AssetRef
from quant_hub.domain.portfolio.construction import StrategyContribution
from quant_hub.domain.portfolio.sizing import PositionSizingDecision

_ASSET = AssetRef(symbol="BTC/USDT", exchange="binance", asset_class="crypto")
_OTHER_ASSET = AssetRef(symbol="ETH/USDT", exchange="binance", asset_class="crypto")
_SERVICE = PortfolioConstructionService()


def _decision(asset: AssetRef, target_notional: str, portfolio_value: str = "100000") -> PositionSizingDecision:
    return PositionSizingDecision(
        asset=asset,
        target_notional=Decimal(target_notional),
        raw_notional=Decimal(target_notional),
        constrained=False,
        portfolio_value=Decimal(portfolio_value),
    )


def _contribution(asset: AssetRef, target_notional: str, weight: str = "1", portfolio_value: str = "100000") -> StrategyContribution:
    return StrategyContribution(
        strategy_id=uuid4(),
        strategy_weight=Decimal(weight),
        decision=_decision(asset, target_notional, portfolio_value),
    )


# ── Single-strategy identity (today's only exercisable case, Step 2.4) ──────

def test_single_strategy_weight_one_is_identity_transform() -> None:
    # With one strategy at weight=1, target_weight == target_notional / portfolio_value
    # exactly — proving Step 3.1's output passes through unchanged.
    contribution = _contribution(_ASSET, "5000", weight="1", portfolio_value="100000")
    result = WeightedSumConstructor().construct([contribution])

    assert result.target_weight == Decimal("0.05")
    assert result.asset == _ASSET
    assert result.portfolio_value == Decimal("100000")


def test_single_strategy_negative_notional_produces_negative_weight() -> None:
    contribution = _contribution(_ASSET, "-2500", portfolio_value="100000")
    result = WeightedSumConstructor().construct([contribution])
    assert result.target_weight == Decimal("-0.025")


# ── Multi-strategy generalization (synthetic — no second real strategy exists yet) ──

def test_multi_strategy_aggregation_sums_weighted_contributions() -> None:
    # Two synthetic strategies, unequal strategy_weight, same instrument.
    c1 = _contribution(_ASSET, "4000", weight="0.6", portfolio_value="100000")
    c2 = _contribution(_ASSET, "2000", weight="0.4", portfolio_value="100000")
    result = WeightedSumConstructor().construct([c1, c2])

    # (0.6*4000 + 0.4*2000) / 100000 = (2400 + 800) / 100000 = 0.032
    assert result.target_weight == Decimal("0.032")


def test_multi_strategy_contributions_can_offset() -> None:
    long = _contribution(_ASSET, "5000", weight="1", portfolio_value="100000")
    short = _contribution(_ASSET, "-5000", weight="1", portfolio_value="100000")
    result = WeightedSumConstructor().construct([long, short])
    assert result.target_weight == Decimal("0")


def test_aggregation_transparency_preserves_all_contributions() -> None:
    # §11.2.6 "Aggregation Transparency": each strategy's contribution visible.
    c1 = _contribution(_ASSET, "4000", weight="0.6")
    c2 = _contribution(_ASSET, "2000", weight="0.4")
    result = WeightedSumConstructor().construct([c1, c2])

    assert result.contributions == (c1, c2)


def test_mismatched_portfolio_value_rejected() -> None:
    c1 = _contribution(_ASSET, "4000", portfolio_value="100000")
    c2 = _contribution(_ASSET, "2000", portfolio_value="200000")
    with pytest.raises(ValueError, match="portfolio_value"):
        WeightedSumConstructor().construct([c1, c2])


def test_empty_contributions_rejected() -> None:
    with pytest.raises(ValueError):
        WeightedSumConstructor().construct([])


# ── Service: multi-instrument grouping ──────────────────────────────────────

def test_service_groups_contributions_by_instrument() -> None:
    contributions = [
        _contribution(_ASSET, "5000", weight="1"),
        _contribution(_OTHER_ASSET, "1000", weight="1"),
    ]
    results = _SERVICE.construct_portfolio(WeightedSumConstructor(), contributions)

    by_symbol = {r.asset.symbol: r for r in results}
    assert len(results) == 2
    assert by_symbol["BTC/USDT"].target_weight == Decimal("0.05")
    assert by_symbol["ETH/USDT"].target_weight == Decimal("0.01")


def test_service_aggregates_multiple_strategies_same_instrument() -> None:
    contributions = [
        _contribution(_ASSET, "4000", weight="0.6"),
        _contribution(_ASSET, "2000", weight="0.4"),
    ]
    results = _SERVICE.construct_portfolio(WeightedSumConstructor(), contributions)

    assert len(results) == 1
    assert results[0].target_weight == Decimal("0.032")


# ── Determinism (§11.2.11 / P-13) and immutability (§11.2.10 / P-2) ─────────

def test_construction_is_deterministic() -> None:
    c1 = _contribution(_ASSET, "4000", weight="0.6")
    c2 = _contribution(_ASSET, "2000", weight="0.4")
    r1 = WeightedSumConstructor().construct([c1, c2])
    r2 = WeightedSumConstructor().construct([c1, c2])
    assert r1 == r2


def test_result_is_frozen_immutable() -> None:
    result = WeightedSumConstructor().construct([_contribution(_ASSET, "5000")])
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.target_weight = Decimal("0")  # type: ignore[misc]
