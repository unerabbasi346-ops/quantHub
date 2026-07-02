# Governing specification: Doc 07 §Layers; Doc 14 §10.6.4; P-1, T-2
# Per Doc 00 §14.11
#
# Proves the Step 2.1 strategy plugin contract holds structurally:
#   - Signal is an immutable value object with opaque, read-only metadata
#   - Strategy / MarketDataView are enforceable ABCs
#   - a plugin's only output type is Signal (no order/position/sizing surface)
from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from quant_hub.domain.market_data.entities import AssetRef, OHLCVBar, Tick
from quant_hub.domain.strategy_engine.entities import Signal
from quant_hub.domain.strategy_engine.strategy import MarketDataView, Strategy

_ASSET = AssetRef(symbol="BTC/USDT", exchange="binance", asset_class="crypto")


def _signal(**overrides: object) -> Signal:
    defaults: dict[str, object] = dict(
        asset=_ASSET, value=Decimal("0.75"), ts=datetime(2026, 7, 2, tzinfo=timezone.utc)
    )
    defaults.update(overrides)
    return Signal(**defaults)  # type: ignore[arg-type]


def test_signal_is_frozen_immutable() -> None:
    sig = _signal()
    with pytest.raises(dataclasses.FrozenInstanceError):
        sig.value = Decimal("1.0")  # type: ignore[misc]


def test_signal_metadata_defaults_empty_and_is_read_only() -> None:
    sig = _signal()
    assert dict(sig.metadata) == {}
    with pytest.raises(TypeError):  # MappingProxyType rejects mutation
        sig.metadata["k"] = "v"  # type: ignore[index]


def test_signal_metadata_is_opaque_passthrough() -> None:
    # P-1: platform records strategy-internal values verbatim, never interprets them.
    sig = _signal(metadata={"raw_alpha": "1.23", "regime": "trending"})
    assert sig.metadata["raw_alpha"] == "1.23"
    assert sig.metadata["regime"] == "trending"


def test_signal_value_is_signed_conviction() -> None:
    assert _signal(value=Decimal("-0.4")).value < 0  # short-side conviction
    assert _signal(value=Decimal("0.9")).value > 0  # long-side conviction


def test_signal_carries_no_order_or_sizing_fields() -> None:
    # The boundary made structural: a Signal exposes no quantity/price/side/
    # order-type surface — those are downstream (Doc 15 §11.1.5, Doc 14 §10.6.5).
    field_names = {f.name for f in dataclasses.fields(Signal)}
    assert field_names == {"asset", "value", "ts", "metadata"}
    for forbidden in ("quantity", "price", "side", "order_type", "signal_id",
                      "strategy_id", "validation_status"):
        assert forbidden not in field_names


def test_strategy_and_view_are_abstract() -> None:
    with pytest.raises(TypeError):
        Strategy()  # type: ignore[abstract]
    with pytest.raises(TypeError):
        MarketDataView()  # type: ignore[abstract]


@pytest.mark.asyncio
async def test_a_concrete_plugin_emits_only_signals() -> None:
    """A trivial (non-Lancaster, per P-1) reference plugin compiles against the
    contract, receives only a read-only view, and returns only Signals."""

    class _FakeView(MarketDataView):
        async def latest_bars(self, asset, interval, limit=100) -> Sequence[OHLCVBar]:
            return []

        async def latest_tick(self, asset) -> Tick | None:
            return None

    class _AlwaysLongOne(Strategy):
        async def generate_signals(self, view: MarketDataView) -> Sequence[Signal]:
            # Whatever a strategy does internally is opaque; it can ONLY read the
            # view and can ONLY return Signals.
            await view.latest_tick(_ASSET)
            return [_signal(value=Decimal("1"))]

    signals = await _AlwaysLongOne().generate_signals(_FakeView())

    assert len(signals) == 1
    assert all(isinstance(s, Signal) for s in signals)
    assert signals[0].value == Decimal("1")


@pytest.mark.asyncio
async def test_empty_signal_sequence_is_valid() -> None:
    class _Abstains(Strategy):
        async def generate_signals(self, view: MarketDataView) -> Sequence[Signal]:
            return []

    class _NullView(MarketDataView):
        async def latest_bars(self, asset, interval, limit=100):
            return []

        async def latest_tick(self, asset):
            return None

    assert await _Abstains().generate_signals(_NullView()) == []
