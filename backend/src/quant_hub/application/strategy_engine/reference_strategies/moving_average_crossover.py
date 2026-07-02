# Governing specification: Doc 14 §10.6.4 (Signal Combination); P-1 (Strategy Independence)
# Layer: Application — Doc 07 §Layers (a Strategy plugin implementation; no
#   I/O of its own — reads only through the MarketDataView it's handed, per
#   the domain-defined Strategy contract, Step 2.1)
# Per Doc 00 §14.11
#
# Step 2.4: a trivial, textbook reference plugin. Its ONLY purpose is to
# prove Steps 2.1-2.3's Strategy/MarketDataView/StrategyRepository/
# SignalRepository interfaces are genuinely pluggable end-to-end (see
# scripts/run_reference_strategy.py for the live wiring). It is not
# intended to trade anything and makes no claim of economic validity.
#
# P-1 / Doc 00 §14.9 COMPLIANCE (flagged explicitly, since this is exactly
# the kind of code P-1 warns against getting wrong): a two-window moving-
# average crossover is one of the most generic, textbook-standard technical
# indicators that exists — it is not modeled on, shaped like, or derived
# from any real strategy this platform is being built for (Lancaster or
# otherwise). P-1 permits references to named strategies "only in
# negation" — this comment is exactly that: stating what this is NOT.
from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal

from quant_hub.domain.market_data.entities import AssetRef
from quant_hub.domain.strategy_engine.entities import Signal
from quant_hub.domain.strategy_engine.strategy import MarketDataView, Strategy

# Value-range bound enforced by Signal Validation (Step 2.2,
# domain/strategy_engine/validation.py's _VALUE_MIN/_VALUE_MAX) — mirrored
# here so this plugin never emits a Signal that Step 2.2 would reject
# outright on range grounds, keeping the crossover's raw divergence signal
# meaningfully clamped rather than silently invalid.
_VALUE_MIN = Decimal("-1")
_VALUE_MAX = Decimal("1")


class MovingAverageCrossoverStrategy(Strategy):
    """Two-window moving-average crossover — a reference plugin, not a real strategy.

    Reads its own instrument and window sizes from the opaque `config`
    passed to generate_signals (Step 2.3's resolved config-delivery
    mechanism) — expected keys: `symbol`, `exchange`, `asset_class`
    (default "crypto"), `interval` (default "1h"), `short_window`
    (default 5), `long_window` (default 20). Per P-1/T-2, the platform
    never inspects or validates these keys — an unregistered/malformed
    config simply fails at the strategy's own KeyError/ValueError, which
    is the plugin's problem, not the platform's.

    Emits a signed conviction proportional to (short_MA - long_MA) /
    long_MA, clamped to Step 2.2's validated [-1, 1] range — sign encodes
    direction (short above long -> positive/long-biased conviction),
    magnitude encodes how far apart the two averages have diverged,
    relative to the long average's own scale. Emits NO signal (empty
    sequence — a valid, expected return per the Strategy contract) when
    there isn't yet enough history to compute both averages.
    """

    async def generate_signals(
        self, view: MarketDataView, config: Mapping[str, object]
    ) -> Sequence[Signal]:
        asset = AssetRef(
            symbol=str(config["symbol"]),
            exchange=str(config["exchange"]),
            asset_class=str(config.get("asset_class", "crypto")),
        )
        interval = str(config.get("interval", "1h"))
        short_window = int(config.get("short_window", 5))  # type: ignore[arg-type]
        long_window = int(config.get("long_window", 20))  # type: ignore[arg-type]

        bars = await view.latest_bars(asset, interval, limit=long_window)
        if len(bars) < long_window:
            return []  # not enough history yet to compute both averages

        closes = [bar.close for bar in bars]
        short_ma = sum(closes[-short_window:], start=Decimal("0")) / short_window
        long_ma = sum(closes, start=Decimal("0")) / long_window

        if long_ma == 0:
            return []  # degenerate case, no meaningful divergence ratio

        raw = (short_ma - long_ma) / long_ma
        value = max(_VALUE_MIN, min(_VALUE_MAX, raw))

        return [
            Signal(
                asset=asset,
                value=value,
                ts=bars[-1].ts,
                metadata={"short_ma": str(short_ma), "long_ma": str(long_ma)},
            )
        ]
