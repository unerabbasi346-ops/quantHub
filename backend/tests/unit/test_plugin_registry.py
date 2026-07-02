# Governing specification: infrastructure/strategy_engine/plugin_registry.py — Step 2.4
# Per Doc 00 §14.11
from __future__ import annotations

from collections.abc import Sequence

import pytest

from quant_hub.domain.strategy_engine.strategy import MarketDataView, Strategy
from quant_hub.infrastructure.strategy_engine.plugin_registry import (
    PluginNotRegisteredError,
    register_plugin,
    resolve_plugin,
)


class _NullView(MarketDataView):
    async def latest_bars(self, asset, interval, limit=100):
        return []

    async def latest_tick(self, asset):
        return None


class _NoOpStrategy(Strategy):
    async def generate_signals(self, view, config) -> Sequence:
        return []


def test_resolve_unregistered_raises_clear_error() -> None:
    with pytest.raises(PluginNotRegisteredError):
        resolve_plugin("never-registered-xyz")


def test_register_then_resolve_returns_same_class() -> None:
    register_plugin("test-noop-strategy", _NoOpStrategy)

    resolved = resolve_plugin("test-noop-strategy")

    assert resolved is _NoOpStrategy
