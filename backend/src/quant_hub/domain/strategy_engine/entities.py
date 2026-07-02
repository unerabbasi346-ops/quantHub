# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Domain — Doc 07 §Layers (value objects, no persistence)
# Signal shape source: Doc 14 §10.6.4 (Signal Generation Pipeline), consumed by
#   Doc 15 §11.1.5 (Position Sizing); immutability per P-5; P-1 opacity boundary.
# Per Doc 00 §14.11
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from types import MappingProxyType
from typing import Mapping

from quant_hub.domain.market_data.entities import AssetRef


@dataclass(frozen=True)
class Signal:
    """A single trading signal emitted by a strategy plugin — Doc 14 §10.6.4.

    ── PROPOSED CONTRACT FILLING A NAMED GAP (Doc 00 §14.5 / §14.7) ──────────
    This is a JUDGMENT CALL, flagged, not silently invented. Doc 14 §10.6.4
    (Signal Generation Pipeline) names "Signal Combination", "Signal
    Validation", and "Signal Recording" and states a signal is "recorded as
    immutable event per P-5 with timestamp, values, and validation status" —
    but Doc 14 provides NO field-level Signal model the way §10.7.3 provides a
    canonical Order Model. The Phase 2 planning inventory (2026-07-02) confirmed
    this gap. The shape below is the minimal set needed for the platform's own
    (non-strategy) stages to function; every field is justified against doc
    text rather than assumed. Revisit if Doc 14 later defines a Signal model.

    ── WHAT THIS IS (the strategy-EMITTED signal), and what it deliberately is not ──
    This models what a strategy plugin RETURNS. It intentionally omits three
    things that are stamped downstream by the platform, NOT forged by the
    plugin (mirrors the Raw*/persistence split in market_data entities):
      • signal_id      — assigned at Signal Recording (Step 2.2), so a plugin
                         cannot fabricate an identity. Referenced later by an
                         Order's "Signal Reference" lineage field (§10.7.3).
      • validation_status — assigned by the platform's Signal Validation stage
                         (§10.6.4), which runs AFTER the plugin emits. A plugin
                         must not self-certify its output as valid.
      • strategy_id    — stamped by the Strategy Engine from the registered
                         strategy it invoked (T-5 auditability / T-2). Trusting
                         the plugin to report its own identity would let it
                         misattribute signals.
    The recorded/validated Signal shape (with those three) is Step 2.2 scope.

    ── FIELD JUSTIFICATIONS ──────────────────────────────────────────────────
    asset:   Which instrument the signal concerns. §10.7.3 Order Model requires
             an "Instrument — Instrument identifier"; the Order is generated
             from the signal, so the signal must name the instrument. Reuses
             the platform's existing vendor-agnostic instrument identity
             (market_data.AssetRef) rather than defining a parallel type —
             not redefining an existing platform concept (Doc 00 §14.6).
    value:   The single platform-meaningful scalar. §10.6.4 Signal Validation
             performs "value range checks, rate-of-change checks" — i.e. the
             platform validates a numeric signal value; §10.8/§10.6.4 Signal
             Recording records "values". Modelled SIGNED: sign encodes desired
             directional exposure, magnitude encodes conviction, which is
             exactly what Doc 15 §11.1.5 Position Sizing consumes ("conviction
             converted to position sizes under risk constraints"). Decimal for
             exact arithmetic, consistent with all price/quantity fields in
             this codebase. Deliberately does NOT prescribe Order Side
             (Buy/Sell/Short/Cover, §10.7.3): a signed conviction against a
             current position is translated to a Side downstream by position
             sizing / order generation, not by the strategy.
    ts:      §10.6.4 / §10.8 both require a signal "timestamp". Signal
             generation time (tz-aware UTC, per the platform's UTC convention).
    metadata: OPAQUE per P-1. §10.6.4 says "Signal combination logic is
             external to platform per P-1" and records "values" (plural). A
             strategy may attach its own internal values here; the platform
             records them verbatim for the P-5 immutable audit event but NEVER
             interprets them — exactly how core.strategies.config is stored as
             opaque JSONB. Read-only view (MappingProxyType) to preserve
             frozen-dataclass immutability.
    """

    asset: AssetRef
    value: Decimal
    ts: datetime
    metadata: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
