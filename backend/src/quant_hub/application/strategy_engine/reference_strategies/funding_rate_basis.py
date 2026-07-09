# Governing specification: Doc 14 §10.6.4 (Signal Combination); P-1 (Strategy Independence)
# Layer: Application — Doc 07 §Layers (a Strategy plugin; no I/O of its own —
#   reads only through the MarketDataView it is handed, per the Step 2.1 contract)
# Scope: handbook/KNOWN_LIMITATIONS.md S-10 (perpetual-futures support)
# Per Doc 00 §14.11
#
# Step 4 of the perpetuals work: the reference plugin that PROVES the
# perpetual data path works end-to-end — real funding-rate ingestion
# (market_data.funding_rates) -> read through MarketDataView.latest_funding_rates
# -> a Signal. It is the perpetual analog of moving_average_crossover.py
# (Step 2.4), which proved the spot OHLCV path.
#
# P-1 / Doc 00 §14.9 COMPLIANCE (flagged explicitly, exactly as the MA-crossover
# plugin flags itself): "funding carry" — taking the side of a perpetual that
# RECEIVES funding — is a generic, textbook property of perpetual futures, not
# modeled on, shaped like, or derived from any real strategy this platform is
# being built for (Lancaster or otherwise). It makes NO claim of economic
# validity; its sole purpose is to exercise the plumbing. P-1 permits naming a
# real strategy "only in negation" — this comment is exactly that.
from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal

from quant_hub.domain.market_data.entities import AssetRef
from quant_hub.domain.strategy_engine.entities import Signal
from quant_hub.domain.strategy_engine.strategy import MarketDataView, Strategy

# Step 2.2 Signal Validation value bounds, mirrored so this plugin never emits
# an out-of-range Signal (same reasoning as moving_average_crossover.py).
_VALUE_MIN = Decimal("-1")
_VALUE_MAX = Decimal("1")
_ZERO = Decimal("0")


class FundingRateBasisStrategy(Strategy):
    """Perpetual funding-carry reference plugin — proves the funding data path, not a real strategy.

    Reads recent funding rates for a PERPETUAL instrument through the
    MarketDataView (never a repository directly) and emits a signed conviction
    that leans toward the side which COLLECTS funding:

      - funding rate POSITIVE  -> longs pay shorts -> lean SHORT  -> negative value
      - funding rate NEGATIVE  -> shorts pay longs -> lean LONG   -> positive value

    So value = clamp(-mean_funding x scale, -1, 1): the sign is the inversion of
    the mean funding rate over the window; the magnitude scales the (tiny, e.g.
    0.0001/interval) rate up into the validated [-1, 1] conviction band.

    Config keys (opaque to the platform per P-1/T-2 — this plugin owns them):
      `symbol`     — ccxt PERPETUAL symbol, e.g. "BTC/USDT:USDT" (required)
      `exchange`   — e.g. "binance" (required)
      `asset_class`— default "crypto"
      `window`     — number of recent funding points to average (default 3)
      `scale`      — conviction scale factor (default 1000; JUDGMENT CALL below)

    `scale` (JUDGMENT CALL, Doc 00 §14.5/§14.7 — flagged): funding rates are
    small fractions (~1e-4 per interval), so a raw rate is a near-zero
    conviction. 1000 maps a 0.001 (0.1%) rate to full conviction (1.0) and a
    typical 0.0001 rate to 0.1 — a reasonable default for the reference band,
    NOT a tuned/validated parameter (this plugin makes no economic claim).
    Overridable via config.

    Emits NO signal (empty sequence — valid per the Strategy contract) when no
    funding data exists yet for the instrument (e.g. a spot symbol, or a perp
    not yet ingested — MarketDataView returns empty in both cases).
    """

    async def generate_signals(
        self, view: MarketDataView, config: Mapping[str, object]
    ) -> Sequence[Signal]:
        asset = AssetRef(
            symbol=str(config["symbol"]),
            exchange=str(config["exchange"]),
            asset_class=str(config.get("asset_class", "crypto")),
            instrument_type="PERPETUAL",
        )
        window = int(config.get("window", 3))  # type: ignore[arg-type]
        scale = Decimal(str(config.get("scale", "1000")))

        rates = await view.latest_funding_rates(asset, limit=window)
        if not rates:
            return []  # no funding data (spot, or perp not yet ingested)

        mean_funding = sum((r.funding_rate for r in rates), start=_ZERO) / Decimal(len(rates))
        raw = -mean_funding * scale  # invert: collect funding -> opposite side
        value = max(_VALUE_MIN, min(_VALUE_MAX, raw))

        return [
            Signal(
                asset=asset,
                value=value,
                ts=rates[-1].funding_time,
                metadata={
                    "mean_funding_rate": str(mean_funding),
                    "window": str(len(rates)),
                    "scale": str(scale),
                },
            )
        ]
