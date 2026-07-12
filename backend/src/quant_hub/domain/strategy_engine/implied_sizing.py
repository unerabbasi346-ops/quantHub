# Governing specification: Doc 15 §11.1.5 — "conviction converted to position
#   sizes under risk constraints" (the Signal-adjacent framing this display
#   figure answers); Doc 14 §10.6.4 (Signal Generation Pipeline).
# Layer: Domain — Doc 07 §Layers (pure functions, no persistence, no I/O)
# Per Doc 00 §14.11
#
# ── WHAT THIS IS, AND — CRITICALLY — WHAT IT IS NOT ─────────────────────────
# This is a small, honest, DISPLAY-ONLY estimate answering "what would this
# raw signal imply about position size, given the strategy's currently
# configured capital?" — surfaced on the read-only GET .../signals feed so an
# operator glancing at a signal has a rough sense of scale.
#
# It is explicitly NOT the platform's real, governed position-sizing
# pipeline. That pipeline already exists at domain/portfolio/sizing.py
# (PositionSizer / SizingContext / SizingConstraints) + the reference
# LinearConvictionSizer, and is what ACTUALLY produces the sized notional
# that Order Generation consumes (Doc 15 §11.3.1, post the F-12 Construction
# → Sizing inversion) — it operates on a portfolio's post-construction
# target_weight, not a raw signal value, and applies real constraints
# (max_fraction, volatility targeting, risk limits). Naming here is
# DELIBERATELY DIFFERENT ("implied_*" throughout) so this module is never
# mistaken for that one: this is a signal-level, single-strategy, capital-only
# back-of-envelope figure with none of the real pipeline's risk constraints,
# never fed into order generation, and never a substitute for it.
#
# F-19 INTERACTION (flagged): `configured_capital` is an operator-set figure
# with NO backing NAV/cash ledger (see api/v1/portfolio.py, migration
# a7d2e1f04b93) — F-19 states it "does NOT feed leverage/risk math". This
# module is the first, explicitly-scoped exception: it feeds ONE honest,
# clearly-labeled DISPLAY figure (implied_size_usdt), not real leverage or
# risk-limit determination, which F-19 continues to correctly block. If
# configured_capital was never set, implied_size_usdt is None — never
# fabricated from an assumed capital figure.
from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal
from typing import Mapping

# Doc 15 §11.1.5 conviction sign -> desired directional exposure. FLAT is
# exactly zero conviction — not "close to zero" — matching Signal.value's
# exact Decimal representation (no epsilon/rounding tolerance invented).
DIRECTION_LONG = "LONG"
DIRECTION_SHORT = "SHORT"
DIRECTION_FLAT = "FLAT"

_ZERO = Decimal("0")
# JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged, same spirit as validation.py's
# _MAX_RATE_OF_CHANGE): no strategy configures a "leverage" key today (no
# reference strategy sets one) and core.positions.leverage is populated at
# fill-time, not upfront — so an UNLEVERAGED default is the only honest
# baseline for "no better information available", for both spot and perpetual.
_DEFAULT_LEVERAGE = Decimal("1.0")
_SIZE_QUANT = Decimal("0.00000001")  # 8dp, matching core.signals.value's NUMERIC(18,8) precision


def compute_direction(value: Decimal) -> str:
    """Direction implied by a signal's signed conviction — Doc 15 §11.1.5.

    Pure sign function: LONG if value > 0, SHORT if value < 0, FLAT if
    exactly 0. Because direction is ALWAYS derived from value (never stored
    or set independently), the two cannot drift apart by construction —
    `assert_direction_matches_value` below exists as an explicit, testable
    statement of that invariant, not a guard against a real divergence path.
    """
    if value > _ZERO:
        return DIRECTION_LONG
    if value < _ZERO:
        return DIRECTION_SHORT
    return DIRECTION_FLAT


def assert_direction_matches_value(value: Decimal, direction: str) -> None:
    """Consistency check: `direction` must be the sign of `value` — Task 4.

    Raises AssertionError on mismatch. Since every caller in this codebase
    obtains `direction` via `compute_direction(value)`, this can only fail if
    a caller passes a `direction` computed from a DIFFERENT value than the
    one the consistency check is asked to confirm — i.e. it is a structural
    invariant assertion, not a runtime data-quality gate. No behavior change:
    callers that already hold consistent (value, direction) pairs are
    unaffected.
    """
    expected = compute_direction(value)
    assert direction == expected, (
        f"direction={direction!r} does not match sign of value={value} "
        f"(expected {expected!r})"
    )


def compute_implied_size_usdt(value: Decimal, configured_capital: Decimal | None) -> Decimal | None:
    """Implied notional size in USDT: abs(conviction) * configured capital.

    Fractional-Kelly-style scaling per the task spec: full conviction
    (|value| == 1) implies the full configured capital; zero conviction
    implies zero size. Returns None — never a fabricated figure — when
    `configured_capital` was never set (F-19: no operator-configured capital
    exists to imply a size from).
    """
    if configured_capital is None:
        return None
    return (abs(value) * configured_capital).quantize(_SIZE_QUANT, rounding=ROUND_HALF_EVEN)


def compute_implied_leverage(
    strategy_config: Mapping[str, object],
    *,
    instrument_type: str | None,
    position_leverage: Decimal | None,
) -> Decimal:
    """Implied leverage for a signal's sizing estimate.

    Precedence (highest first):
      1. strategy_config["leverage"] — an explicit, strategy-declared figure,
         if the strategy's opaque (P-1) config happens to carry one.
      2. `position_leverage` — the REAL leverage already recorded on an open
         PERPETUAL position for this (portfolio, asset) pair (core.positions.
         leverage, migration e7a3c1f5b9d2), when `instrument_type ==
         "PERPETUAL"`. A spot instrument never has a margin/leverage concept
         per S-10, so this source is never consulted for SPOT.
      3. `_DEFAULT_LEVERAGE` (1.0) — the honest unleveraged baseline, used for
         SPOT always, and for PERPETUAL when no config/position figure exists.
    """
    configured = strategy_config.get("leverage")
    if configured is not None:
        return configured if isinstance(configured, Decimal) else Decimal(str(configured))
    if instrument_type == "PERPETUAL" and position_leverage is not None:
        return position_leverage
    return _DEFAULT_LEVERAGE
