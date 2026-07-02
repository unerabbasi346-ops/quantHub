# Governing specification: Doc 15 §11.3 — Position Sizing; P-1, P-13
# Per Doc 00 §14.11
#
# No database needed — pure computation on domain/portfolio/sizing.py +
# application/portfolio/sizing_service.py + the reference methodology.
from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from quant_hub.application.portfolio.reference_sizers.linear_conviction import (
    LinearConvictionSizer,
)
from quant_hub.application.portfolio.sizing_service import PositionSizingService
from quant_hub.domain.market_data.entities import AssetRef
from quant_hub.domain.portfolio.sizing import (
    PositionSizer,
    SizingConstraints,
    SizingContext,
)
from quant_hub.domain.strategy_engine.entities import Signal

_ASSET = AssetRef(symbol="BTC/USDT", exchange="binance", asset_class="crypto")


def _signal(value: str) -> Signal:
    return Signal(asset=_ASSET, value=Decimal(value), ts=datetime(2026, 7, 3, tzinfo=timezone.utc))


def _ctx(value: str, portfolio_value: str = "100000", volatility: str | None = None, **config) -> SizingContext:
    return SizingContext(
        signal=_signal(value),
        portfolio_value=Decimal(portfolio_value),
        volatility=Decimal(volatility) if volatility is not None else None,
        config=config,
    )


_SERVICE = PositionSizingService()


# ── Reference methodology (LinearConvictionSizer) ───────────────────────────

def test_linear_sizer_scales_notional_by_conviction() -> None:
    sizer = LinearConvictionSizer()
    # full conviction 1.0, max_fraction 0.05, AUM 100k → 5000 notional
    assert sizer.size(_ctx("1.0", max_fraction="0.05")) == Decimal("5000.000")
    # half conviction → half notional
    assert sizer.size(_ctx("0.5", max_fraction="0.05")) == Decimal("2500.0000")


def test_linear_sizer_sign_follows_conviction() -> None:
    sizer = LinearConvictionSizer()
    assert sizer.size(_ctx("-0.4", max_fraction="0.05")) < 0  # short target
    assert sizer.size(_ctx("0.4", max_fraction="0.05")) > 0   # long target


def test_linear_sizer_volatility_targeting_scales_inversely() -> None:
    sizer = LinearConvictionSizer()
    # target_vol 0.10, realized vol 0.20 → scale 0.5
    ctx = _ctx("1.0", volatility="0.20", max_fraction="0.05", target_vol="0.10")
    # raw = 1.0 * 0.05 * 100000 * (0.10/0.20) = 5000 * 0.5 = 2500
    assert sizer.size(ctx) == Decimal("2500.0000000000000000000000000")


def test_linear_sizer_ignores_volatility_without_target_vol() -> None:
    sizer = LinearConvictionSizer()
    # volatility supplied but no target_vol in config → not vol-targeted
    assert sizer.size(_ctx("1.0", volatility="0.20", max_fraction="0.05")) == Decimal("5000.000")


# ── Platform mechanism (PositionSizingService constraint clamp) ─────────────

def test_service_passes_through_when_within_cap() -> None:
    decision = _SERVICE.size_position(
        LinearConvictionSizer(),
        _ctx("0.5", max_fraction="0.05"),               # raw = 2500
        SizingConstraints(max_position_pct=Decimal("0.05")),  # cap = 5000
    )
    assert decision.target_notional == Decimal("2500.0000")
    assert decision.raw_notional == Decimal("2500.0000")
    assert decision.constrained is False


def test_service_clamps_long_target_to_cap() -> None:
    # vol targeting pushes raw above the cap; platform must clamp it.
    decision = _SERVICE.size_position(
        LinearConvictionSizer(),
        _ctx("1.0", volatility="0.05", max_fraction="0.05", target_vol="0.20"),  # raw = 5000 * 4 = 20000
        SizingConstraints(max_position_pct=Decimal("0.05")),  # cap = 5000
    )
    assert decision.raw_notional == Decimal("20000.0000000000000000000000000")
    assert decision.target_notional == Decimal("5000.00")  # clamped to cap
    assert decision.constrained is True


def test_service_clamps_short_target_symmetrically() -> None:
    decision = _SERVICE.size_position(
        LinearConvictionSizer(),
        _ctx("-1.0", volatility="0.05", max_fraction="0.05", target_vol="0.20"),  # raw = -20000
        SizingConstraints(max_position_pct=Decimal("0.05")),  # cap magnitude = 5000
    )
    assert decision.target_notional == Decimal("-5000.00")  # clamped, sign preserved
    assert decision.constrained is True


def test_service_conviction_cannot_override_constraint() -> None:
    # §11.3.1: "conviction shall not override risk constraints" — even a
    # methodology returning an enormous raw size is bounded by the platform.
    class _RunawaySizer(PositionSizer):
        def size(self, context: SizingContext) -> Decimal:
            return Decimal("999999999")

    decision = _SERVICE.size_position(
        _RunawaySizer(),
        _ctx("1.0"),
        SizingConstraints(max_position_pct=Decimal("0.10")),  # cap = 10000
    )
    assert decision.target_notional == Decimal("10000.00")
    assert decision.constrained is True


def test_decision_carries_instrument_and_portfolio_value() -> None:
    decision = _SERVICE.size_position(
        LinearConvictionSizer(), _ctx("0.5"), SizingConstraints(max_position_pct=Decimal("0.05"))
    )
    assert decision.asset == _ASSET
    assert decision.portfolio_value == Decimal("100000")


# ── Determinism (§11.3.10 / P-13) and immutability (§11.3.9 / P-2) ──────────

def test_sizing_is_deterministic() -> None:
    args = (LinearConvictionSizer(), _ctx("0.37", max_fraction="0.05"), SizingConstraints(max_position_pct=Decimal("0.05")))
    d1 = _SERVICE.size_position(*args)
    d2 = _SERVICE.size_position(*args)
    assert d1 == d2  # identical inputs → identical decision


def test_decision_is_frozen_immutable() -> None:
    decision = _SERVICE.size_position(
        LinearConvictionSizer(), _ctx("0.5"), SizingConstraints(max_position_pct=Decimal("0.05"))
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        decision.target_notional = Decimal("0")  # type: ignore[misc]


def test_config_is_opaque_passthrough() -> None:
    # P-1: the platform never inspects methodology config; the methodology
    # reads its own keys. SizingContext stores whatever it's given.
    ctx = _ctx("1.0", max_fraction="0.03", target_vol="0.15", custom_key="ignored")
    assert ctx.config["max_fraction"] == "0.03"
    assert ctx.config["custom_key"] == "ignored"
