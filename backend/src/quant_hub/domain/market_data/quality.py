# Governing specification: Doc 11 §6 — Data Quality Scoring (Data Engineering)
# Layer: Domain — Doc 07 §Layers
# Per Doc 00 §14.11
#
# SCOPE (Step 1.7, per handbook/KNOWN_LIMITATIONS.md S-2 scope decision):
# Doc 11 §6 lists 5 relevant quality metrics (Completeness, Accuracy,
# Freshness, Consistency, Timeliness — a subset of D-7 §7.9.5's canonical
# 10) and says "Each published dataset receives a quality score with
# supporting metrics." This is implemented as simple computed flags
# stored in the existing `data_quality` VARCHAR(16) column (Doc 09,
# Step 1.1 migration) — NOT a numeric multi-metric score with supporting
# detail (that would need new schema, which is out of scope for this
# step; the task explicitly said to work within the existing column) and
# NOT Part 6's full Data Quality Architecture (quality rules engine,
# quality gates, dataset certification — out of scope per S-1).
#
# How the 5 metrics map onto what's actually computed here (flagged, not
# silently narrowed):
#   Completeness, Consistency — already fully gated by Step 1.6's Validate
#     stage (domain/market_data/validation.py). Nothing reaches this
#     module that didn't already pass those checks, so they are not
#     re-scored as separate metrics here, only implicitly satisfied.
#   Accuracy — NOT computed. Assessing whether a value correctly
#     represents reality needs a reference/ground-truth source to compare
#     against; none exists in this pipeline (Doc 11 does not name one).
#     Flagged as out of scope rather than approximated with an invented
#     heuristic.
#   Freshness, Timeliness — collapsed into a single staleness check
#     (Doc 11's Part 2 §6 summary does not operationally distinguish
#     them; Part 6, which might, is out of scope per S-1). Applied to
#     ticks only — see assess_tick_quality for why bars are excluded.
from __future__ import annotations

from datetime import datetime, timedelta, timezone

QUALITY_CLEAN = "CLEAN"
QUALITY_STALE = "STALE"

# JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged): same 5-minute tolerance
# philosophy as Step 1.6's future-timestamp check — a "latest tick" more
# than this old is treated as stale. Doc 11 §6 does not specify a value.
_TICK_FRESHNESS_TOLERANCE = timedelta(minutes=5)


def assess_bar_quality(*, source_quality: str) -> str:
    """Doc 11 §6 quality assessment for a bar reaching Persist — scoped per S-2.

    JUDGMENT CALL: Freshness/Timeliness are deliberately NOT applied to
    historical OHLCV bars. A bar's `ts` being far in the past is normal
    and expected for historical backfill (Doc 11 §2 "Historical Data
    Ingestion") — it is not a quality defect the way a stale "latest
    tick" is. Inventing an ingestion-lag-relative-to-interval heuristic
    to approximate bar freshness was considered and rejected: it would be
    either meaningless during backfills or an arbitrary threshold Doc 11
    does not specify, i.e. exactly the kind of invented-and-uninspected
    scope this module is trying to avoid.

    Net effect: the returned value is the connector-asserted quality,
    passed through. This is a real computation, not a no-op — reaching
    this function at all now specifically means "passed Step 1.6
    Validate", replacing the old unconditional hardcoded default.
    """
    return source_quality


def assess_tick_quality(*, ts: datetime, received_at: datetime, source_quality: str) -> str:
    """Doc 11 §6 quality assessment for a tick reaching Persist — scoped per S-2.

    JUDGMENT CALL: `source_quality` (e.g. yfinance's "ESTIMATED" — Step
    1.2, meaning "this is a delayed quote snapshot, not a real trade
    print") is preserved rather than overwritten if it's already anything
    other than the default CLEAN. That flag is a provenance signal (what
    KIND of measurement this is) — Doc 11 §6's correctness/timeliness
    metrics don't supersede it, they're a separate question. Staleness is
    only computed/applied when the connector hasn't already asserted a
    more specific flag.
    """
    if source_quality != QUALITY_CLEAN:
        return source_quality
    now = received_at if received_at.tzinfo is not None else received_at.replace(tzinfo=timezone.utc)
    ts_aware = ts if ts.tzinfo is not None else ts.replace(tzinfo=timezone.utc)
    if now - ts_aware > _TICK_FRESHNESS_TOLERANCE:
        return QUALITY_STALE
    return QUALITY_CLEAN
