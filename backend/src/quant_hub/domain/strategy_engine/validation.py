# Governing specification: Doc 14 §10.6.4 — Signal Generation Pipeline, Signal Validation
#   ("Generated signals validated: value range checks, rate-of-change checks,
#   consistency checks against historical signal distribution. Invalid
#   signals shall be rejected and shall not generate orders.")
# Invariants: P-1, T-2 (a platform-level check must not embed a
#   strategy-specific numeric assumption into infrastructure)
# Layer: Domain — Doc 07 §Layers
# Per Doc 00 §14.11
#
# SCOPE (Step 2.2, mirroring the Step 1.6 / handbook S-2 proportionate-scoping
# approach): implements Doc 14 §10.6.4's three named check categories at a
# basic, solo-developer scope — NOT a statistical/enterprise validation
# framework. "Consistency checks against historical signal distribution" is
# scoped down to a structural temporal-ordering check (see below), the same
# way Step 1.6 scoped bar "Consistency" down to cross-field sanity checks
# rather than a full quality-rules engine.
#
# CRITICAL DIFFERENCE FROM Step 1.6 (market_data/validation.py) — flagged,
# not silently carried over: for bars/ticks, an invalid record is rejected
# AND NOT PERSISTED (logged only). For signals, Doc 14 §10.6.4 explicitly
# says "Every generated signal recorded ... with ... validation status" —
# i.e. even an INVALID signal must still be recorded (with
# validation_status reflecting the failure), only its ability to
# "generate orders" is what's blocked. Validity here therefore gates
# downstream order generation, NOT persistence — see
# application/strategy_engine (Step 2.2, recording side) for where this
# is honored.
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from quant_hub.domain.strategy_engine.entities import RecordedSignal, Signal

# Doc 14 §10.6.4: "Every generated signal recorded ... with ... validation
# status." Stamped by the platform (never by the plugin, per Step 2.1) onto
# the persisted RecordedSignal.validation_status column (VARCHAR(16), migration
# 7c7482e4e00a). Two values only, matching this step's scoped-down checks —
# no partial/warning tier, mirroring market_data's binary is_valid outcome.
VALIDATION_VALID = "VALID"
VALIDATION_INVALID = "INVALID"

# Same clock-skew tolerance and rationale as market_data/validation.py's
# _FUTURE_TOLERANCE — a signal timestamped a few seconds/minutes ahead of
# local wall-clock time (compute latency, minor clock drift) is not corrupt.
_FUTURE_TOLERANCE = timedelta(minutes=5)

# JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged): value range bound.
# Step 2.1 (already accepted) established `Signal.value` as a signed
# conviction score consumed by Doc 15 §11.1.5 Position Sizing ("conviction
# converted to position sizes"); a conviction score is conventionally
# normalized. [-1, 1] is chosen as that normalization convention. Doc 14
# §10.6.4 names "value range checks" as a required category but gives no
# number — this bound is this codebase's specific interpretation, building
# on Step 2.1's already-accepted "conviction" framing rather than inventing
# fresh scope. Revisit if a strategy design genuinely needs an unbounded or
# differently-scaled signal value.
_VALUE_MIN = Decimal("-1")
_VALUE_MAX = Decimal("1")

# JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged, UNCALIBRATED): rate-of-change
# threshold for consecutive signals from the same (strategy, asset) pair.
# Doc 14 §10.6.4 names "rate-of-change checks" as a category without a
# threshold. Given the value range above (full span = 2.0, a complete
# reversal from -1 to +1), 1.0 is chosen as a deliberately arbitrary
# midpoint default — same spirit as _FUTURE_TOLERANCE's 5-minute choice —
# NOT derived from any observed signal behavior, because no real
# signal-generating strategy exists yet to calibrate against (that is Step
# 2.4, a reference strategy). REVISIT TRIGGER: once Step 2.4's reference
# strategy produces multiple real consecutive signals from real market
# data, revisit this threshold against actually-observed deltas.
_MAX_RATE_OF_CHANGE = Decimal("1.0")


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of validating one signal.

    Deliberately a separate, small local type rather than reusing
    market_data.validation.ValidationResult (identical shape): that type's
    module is scoped to Doc 11 §5; this one is governed by Doc 14 §10.6.4.
    Coupling two differently-governed concepts to one shared type was
    judged worse than a five-line duplication — flagged, not an oversight.
    """

    is_valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)


def validate_signal(signal: Signal, previous: RecordedSignal | None = None) -> ValidationResult:
    """Range / rate-of-change / consistency checks — Doc 14 §10.6.4, scoped per Step 2.2.

    `previous` is the most recently RECORDED signal for the same
    (strategy_id, asset_id) pair, if any (looked up by the caller via
    SignalRepository.get_latest — see application-layer wiring). Rate-of-
    change and temporal-consistency checks are skipped (never fail) when
    `previous` is None — a strategy's first-ever signal for a given
    instrument has no history to be inconsistent with.
    """
    errors: list[str] = []

    # Completeness
    if not signal.asset.symbol:
        errors.append("asset.symbol is empty")
    if not signal.asset.exchange:
        errors.append("asset.exchange is empty")

    # Schema
    if not isinstance(signal.ts, datetime):
        errors.append(f"ts is not a datetime: {type(signal.ts).__name__}")
    else:
        now = datetime.now(timezone.utc)
        ts = signal.ts if signal.ts.tzinfo is not None else signal.ts.replace(tzinfo=timezone.utc)
        if ts > now + _FUTURE_TOLERANCE:
            errors.append(f"ts={signal.ts} is in the future (now={now})")

    # Range (§10.6.4 "value range checks") — strategy-agnostic core: reject
    # non-finite values regardless of what scale a strategy uses (P-1/T-2:
    # this part of the check embeds no strategy-specific assumption).
    if signal.value.is_nan() or signal.value.is_infinite():
        errors.append(f"value={signal.value} is not a finite number")
    elif not (_VALUE_MIN <= signal.value <= _VALUE_MAX):
        errors.append(f"value={signal.value} outside [{_VALUE_MIN}, {_VALUE_MAX}]")

    if previous is not None:
        # Consistency (§10.6.4 "consistency checks against historical
        # signal distribution") — SCOPED DOWN from a statistical
        # distribution comparison to structural temporal ordering: a
        # signal timestamped before the most recently recorded signal for
        # the same (strategy, asset) is inconsistent with recorded history
        # (out-of-order arrival), the unambiguous case in this category —
        # same "basic, not enterprise" scoping as Step 1.6.
        if signal.ts < previous.ts:
            errors.append(
                f"ts={signal.ts} is before previous recorded signal ts={previous.ts} "
                "— inconsistent with recorded history"
            )

        # Rate-of-change (§10.6.4 "rate-of-change checks")
        if not signal.value.is_nan() and not signal.value.is_infinite():
            delta = abs(signal.value - previous.value)
            if delta > _MAX_RATE_OF_CHANGE:
                errors.append(
                    f"value changed by {delta} from previous={previous.value} to "
                    f"current={signal.value} — exceeds rate-of-change threshold "
                    f"{_MAX_RATE_OF_CHANGE}"
                )

    return ValidationResult(is_valid=not errors, errors=tuple(errors))
