# Governing specification: Doc 11 §5 — Data Validation Engine (Data Engineering)
#                          Doc 11 §2 — Historical Data Ingestion (Validate pipeline stage)
# Layer: Domain — Doc 07 §Layers
# Per Doc 00 §14.11
#
# SCOPE (Step 1.6, per handbook/KNOWN_LIMITATIONS.md S-2 scope decision):
# implements Doc 11 §5's Schema/Completeness/Range/Consistency validation
# levels at a basic, solo-developer scope — NOT Part 6's full Data Quality
# Architecture (quality rules engine, quality gates, dataset certification,
# continuous quality monitoring, quality governance). Referential
# Integrity (§5's 5th validation level) is intentionally out of scope
# here: it is already enforced by the database's foreign-key constraints
# at persistence time (Step 1.1 migration: ohlcv_bars.asset_id and
# ticks.asset_id both REFERENCES assets(id)) — there is no separate
# reference dataset to check against in application code at this stage.
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from quant_hub.domain.market_data.entities import RawCorporateAction, RawOHLCVBar, RawTick

# JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged, not silently decided): a
# small clock-skew tolerance for the "timestamp not in the future" check,
# rather than a strict `ts > now()` rejection. A real exchange timestamp a
# few seconds/minutes ahead of local wall-clock time (network latency,
# minor clock drift between our host and the exchange) is not corrupt
# data and shouldn't be rejected as such. Doc 11 §5 does not specify a
# tolerance value.
_FUTURE_TOLERANCE = timedelta(minutes=5)


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of validating one bar/tick.

    Doc 11 §5 Failure Policy calls for "Generate validation reports" —
    scoped per S-2 to this per-record result (consumed by the caller to
    log a structured warning) rather than a separate report artifact/store.
    """

    is_valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)


def validate_bar(bar: RawOHLCVBar) -> ValidationResult:
    """Basic schema/completeness/range/consistency checks — Doc 11 §5, scoped per S-2."""
    errors: list[str] = []

    # Completeness (Doc 11 §5 "Completeness")
    if not bar.asset.symbol:
        errors.append("asset.symbol is empty")
    if not bar.asset.exchange:
        errors.append("asset.exchange is empty")
    if not bar.interval:
        errors.append("interval is empty")

    # Schema (Doc 11 §5 "Schema")
    if not isinstance(bar.ts, datetime):
        errors.append(f"ts is not a datetime: {type(bar.ts).__name__}")

    # Range (Doc 11 §5 "Range")
    for name in ("open", "high", "low", "close"):
        value = getattr(bar, name)
        if value <= 0:
            errors.append(f"{name}={value} is not > 0")
    if bar.volume < 0:
        errors.append(f"volume={bar.volume} is negative")
    if isinstance(bar.ts, datetime):
        now = datetime.now(timezone.utc)
        ts = bar.ts if bar.ts.tzinfo is not None else bar.ts.replace(tzinfo=timezone.utc)
        if ts > now + _FUTURE_TOLERANCE:
            errors.append(f"ts={bar.ts} is in the future (now={now})")

    # Consistency (Doc 11 §5 "Consistency") — JUDGMENT CALL: beyond the
    # user's literal examples (price>0, high>=low, volume>=0,
    # timestamp-not-future), also checks open/close fall within [low,
    # high]. Added under the same "range sanity check" spirit — a bar
    # where high < low, or close falls outside the [low, high] band, is
    # unambiguously corrupt data, and Doc 11 §5 lists "Consistency" as one
    # of its 5 validation levels. Flagged as an addition, not silently
    # invented scope creep.
    if bar.high < bar.low:
        errors.append(f"high={bar.high} < low={bar.low}")
    else:
        if not (bar.low <= bar.open <= bar.high):
            errors.append(f"open={bar.open} outside [low={bar.low}, high={bar.high}]")
        if not (bar.low <= bar.close <= bar.high):
            errors.append(f"close={bar.close} outside [low={bar.low}, high={bar.high}]")

    return ValidationResult(is_valid=not errors, errors=tuple(errors))


def validate_tick(tick: RawTick) -> ValidationResult:
    """Basic schema/completeness/range checks — Doc 11 §5, scoped per S-2."""
    errors: list[str] = []

    # Completeness
    if not tick.asset.symbol:
        errors.append("asset.symbol is empty")
    if not tick.asset.exchange:
        errors.append("asset.exchange is empty")
    if not tick.feed_origin:
        errors.append("feed_origin is empty")
    # JUDGMENT CALL: a tick with bid, ask, AND last all missing carries no
    # price information at all — treated as a completeness failure. The
    # Tick Contract (Doc 11 Cross-Document Data Contract Shapes) makes all
    # three individually optional; it does not say at least one is
    # required, but a tick with none of them is not meaningfully a tick.
    if tick.bid is None and tick.ask is None and tick.last is None:
        errors.append("bid, ask, and last are all missing — tick carries no price")

    # Schema
    if not isinstance(tick.ts, datetime):
        errors.append(f"ts is not a datetime: {type(tick.ts).__name__}")
    else:
        now = datetime.now(timezone.utc)
        ts = tick.ts if tick.ts.tzinfo is not None else tick.ts.replace(tzinfo=timezone.utc)
        if ts > now + _FUTURE_TOLERANCE:
            errors.append(f"ts={tick.ts} is in the future (now={now})")

    # Range
    for name in ("bid", "ask", "last"):
        value = getattr(tick, name)
        if value is not None and value <= 0:
            errors.append(f"{name}={value} is not > 0")
    for name in ("bid_size", "ask_size", "last_size", "volume"):
        value = getattr(tick, name)
        if value is not None and value < 0:
            errors.append(f"{name}={value} is negative")

    return ValidationResult(is_valid=not errors, errors=tuple(errors))


def validate_corporate_action(action: RawCorporateAction) -> ValidationResult:
    """Basic schema/completeness checks — Doc 11 §5/§3, scoped per S-2.

    JUDGMENT CALL: deliberately lighter than validate_bar/validate_tick —
    corporate actions are low-volume, low-risk data (a handful of rows
    per symbol per year, not a continuous time series), so the same
    range/consistency machinery isn't proportionate. Only completeness
    and the one range check with an unambiguous correct sign (ratio/
    amount must be positive) are checked.
    """
    errors: list[str] = []

    if not action.asset.symbol:
        errors.append("asset.symbol is empty")
    if not action.asset.exchange:
        errors.append("asset.exchange is empty")
    if not action.action_type:
        errors.append("action_type is empty")
    if not isinstance(action.ex_date, date):
        errors.append(f"ex_date is not a date: {type(action.ex_date).__name__}")

    # A split/dividend must carry at least one of ratio/amount — an
    # action with neither is not meaningfully describable.
    if action.ratio is None and action.amount is None:
        errors.append("ratio and amount are both missing — action carries no adjustment data")
    if action.ratio is not None and action.ratio <= 0:
        errors.append(f"ratio={action.ratio} is not > 0")
    if action.amount is not None and action.amount <= 0:
        errors.append(f"amount={action.amount} is not > 0")

    return ValidationResult(is_valid=not errors, errors=tuple(errors))
