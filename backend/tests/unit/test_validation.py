# Governing specification: Doc 11 §5 — Data Validation Engine (Data Engineering)
# Per Doc 00 §14.11
#
# No database needed — pure logic on domain/market_data/validation.py.
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from quant_hub.domain.market_data.entities import AssetRef, RawOHLCVBar, RawTick
from quant_hub.domain.market_data.validation import validate_bar, validate_tick

_ASSET = AssetRef(symbol="BTC/USDT", exchange="binance", asset_class="crypto")


def _valid_bar(**overrides: object) -> RawOHLCVBar:
    defaults: dict[object, object] = dict(
        asset=_ASSET,
        interval="1h",
        ts=datetime.now(timezone.utc) - timedelta(hours=1),
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("95"),
        close=Decimal("105"),
        volume=Decimal("10.5"),
        source="binance",
    )
    defaults.update(overrides)
    return RawOHLCVBar(**defaults)  # type: ignore[arg-type]


def _valid_tick(**overrides: object) -> RawTick:
    defaults: dict[object, object] = dict(
        asset=_ASSET,
        ts=datetime.now(timezone.utc),
        received_at=datetime.now(timezone.utc),
        feed_origin="binance",
        last=Decimal("100"),
    )
    defaults.update(overrides)
    return RawTick(**defaults)  # type: ignore[arg-type]


def test_valid_bar_passes() -> None:
    result = validate_bar(_valid_bar())
    assert result.is_valid is True
    assert result.errors == ()


def test_bar_rejects_zero_or_negative_price() -> None:
    result = validate_bar(_valid_bar(open=Decimal("0")))
    assert result.is_valid is False
    assert any("open" in e for e in result.errors)


def test_bar_rejects_high_less_than_low() -> None:
    result = validate_bar(_valid_bar(high=Decimal("50"), low=Decimal("95")))
    assert result.is_valid is False
    assert any("high" in e and "low" in e for e in result.errors)


def test_bar_rejects_negative_volume() -> None:
    result = validate_bar(_valid_bar(volume=Decimal("-1")))
    assert result.is_valid is False
    assert any("volume" in e for e in result.errors)


def test_bar_rejects_future_timestamp() -> None:
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    result = validate_bar(_valid_bar(ts=future))
    assert result.is_valid is False
    assert any("future" in e for e in result.errors)


def test_bar_allows_small_clock_skew() -> None:
    almost_now = datetime.now(timezone.utc) + timedelta(seconds=30)
    result = validate_bar(_valid_bar(ts=almost_now))
    assert result.is_valid is True


def test_bar_rejects_close_outside_high_low_band() -> None:
    result = validate_bar(_valid_bar(close=Decimal("200")))
    assert result.is_valid is False
    assert any("close" in e for e in result.errors)


def test_bar_rejects_empty_symbol() -> None:
    bad_asset = AssetRef(symbol="", exchange="binance", asset_class="crypto")
    result = validate_bar(_valid_bar(asset=bad_asset))
    assert result.is_valid is False
    assert any("symbol" in e for e in result.errors)


def test_bar_reports_multiple_errors_at_once() -> None:
    result = validate_bar(_valid_bar(open=Decimal("-1"), volume=Decimal("-5")))
    assert result.is_valid is False
    assert len(result.errors) >= 2


def test_valid_tick_passes() -> None:
    result = validate_tick(_valid_tick())
    assert result.is_valid is True


def test_tick_rejects_all_prices_missing() -> None:
    result = validate_tick(_valid_tick(last=None))
    assert result.is_valid is False
    assert any("no price" in e for e in result.errors)


def test_tick_rejects_negative_price() -> None:
    result = validate_tick(_valid_tick(last=Decimal("-1")))
    assert result.is_valid is False
    assert any("last" in e for e in result.errors)


def test_tick_rejects_future_timestamp() -> None:
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    result = validate_tick(_valid_tick(ts=future))
    assert result.is_valid is False
    assert any("future" in e for e in result.errors)


def test_tick_rejects_negative_size() -> None:
    result = validate_tick(_valid_tick(last_size=-5))
    assert result.is_valid is False
    assert any("last_size" in e for e in result.errors)
