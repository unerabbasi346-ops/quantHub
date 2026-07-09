# Governing specification: Doc 11 §1/§2 — Market Data Connectors / normalization
#                          handbook/KNOWN_LIMITATIONS.md S-10 (SPOT|PERPETUAL scope)
# Per Doc 00 §14.11
#
# Pure, network-free tests for infer_instrument_type (Step 2 of perpetuals
# work) — the ccxt spot-vs-perpetual classifier used when stamping AssetRef.
from __future__ import annotations

import pytest

from quant_hub.domain.market_data.connectors import infer_instrument_type


@pytest.mark.parametrize(
    "symbol,expected",
    [
        ("BTC/USDT", "SPOT"),               # spot: no settle suffix
        ("ETH/USDT", "SPOT"),
        ("BTC/USDT:USDT", "PERPETUAL"),     # linear perp: settle suffix, no expiry
        ("ETH/USDT:USDT", "PERPETUAL"),
        ("BTC/USD:BTC", "PERPETUAL"),       # inverse perp still classifies PERPETUAL
        ("BTC/USDT:USDT-240329", "SPOT"),   # dated future (has expiry) — NOT a perp (S-10)
    ],
)
def test_symbol_convention_fallback(symbol: str, expected: str) -> None:
    # market=None -> ccxt unified-symbol convention path
    assert infer_instrument_type(symbol) == expected


def test_market_metadata_takes_precedence_over_symbol() -> None:
    # market['swap'] is authoritative: a swap flag makes it PERPETUAL even if
    # the symbol looks spot, and its absence makes it SPOT even if the symbol
    # carries a settle suffix.
    assert infer_instrument_type("BTC/USDT", {"swap": True}) == "PERPETUAL"
    assert infer_instrument_type("BTC/USDT:USDT", {"swap": False}) == "SPOT"


def test_market_metadata_missing_swap_key_is_spot() -> None:
    # A market dict without a truthy 'swap' is SPOT (not perpetual).
    assert infer_instrument_type("BTC/USDT", {"spot": True}) == "SPOT"
    assert infer_instrument_type("BTC/USDT", {}) == "SPOT"
