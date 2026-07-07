# Governing specification: Doc 05 — Engineering Standards (mandatory paper
#   trading before live). Doc 14 §10.5.9 (Paper-to-Live Promotion Gate — the
#   evidence recorded here), §10.5.10 (Paper Trading Artifacts — the session
#   `results` this reads and appends to).
# Layer: Application — Doc 07 §Layers (orchestration only; reads the session via
#   the repository, calls the PURE domain evaluator, records the evidence. No
#   SQL of its own; does not commit — the caller owns the transaction).
# Invariants: P-2 (promotion evidence recorded on the session artifact).
# Scope: handbook/KNOWN_LIMITATIONS.md S-8.
# Per Doc 00 §14.11
#
# Step 5.4 — the thin application seam over domain/paper_trading/graduation.py.
# It reads a completed session's Step 5.3 artifacts, evaluates the minimum
# graduation bar, and APPENDS the pass/fail record to the session's `results`
# JSONB as governed promotion evidence (§10.5.9/§10.5.10). It does NOT change
# session status and does NOT authorise live trading — a human decides (Doc 05).
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from uuid import UUID

from quant_hub.domain.paper_trading.graduation import (
    GraduationRecord,
    GraduationThresholds,
    evaluate_graduation,
)
from quant_hub.domain.paper_trading.interfaces import PaperTradingSessionRepository

# Recorded on the evidence so a reader is never misled that a mechanical pass is
# an authorisation — Doc 05 keeps the human in the loop.
_NOTE = (
    "record only — Doc 05 requires a human to authorise live promotion; this is "
    "evidence of the minimum eligibility bar, not an automated live-trading gate"
)


class GraduationService:
    """Evaluate-and-record the graduation criteria for a paper session.

    JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged): the record is APPENDED into
    the session's existing `results` JSONB under a `graduation` key (read-merge-
    write), rather than adding dedicated graduation columns — exactly the home
    the Step 5.0 migration reserved ("status='GRADUATED' + results suffice for
    now; dedicated graduation-evidence columns deferred to Step 5.4"). This step
    keeps that decision: a checklist record needs no schema change. True P-2
    immutability enforcement (locking the artifact after completion) is NOT built
    — no immutability mechanism exists on `results` yet (consistent with F-17's
    deferred immutable-event-stream); the record is append-only by convention.
    """

    def __init__(
        self,
        sessions: PaperTradingSessionRepository,
        *,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._sessions = sessions
        self._now = now

    async def evaluate(
        self, session_id: UUID, *, thresholds: GraduationThresholds | None = None
    ) -> GraduationRecord:
        """Read the session's Step 5.3 artifacts, evaluate the graduation bar,
        and record the evidence into results['graduation']. Returns the record.
        Raises ValueError if the session does not exist. Does not commit."""
        row = await self._sessions.get_by_id(session_id)
        if row is None:
            raise ValueError(f"paper trading session {session_id} not found")

        results = dict(row.get("results") or {})
        record = evaluate_graduation(
            status=str(row["status"]),
            bars_processed=int(results.get("bars_processed", 0) or 0),
            orders_filled=int(results.get("orders_filled", 0) or 0),
            comparison=results.get("comparison"),
            thresholds=thresholds,
        )

        results["graduation"] = self._to_dict(record)
        await self._sessions.update_runtime(session_id, results=results)
        return record

    def _to_dict(self, record: GraduationRecord) -> dict:
        """JSON-serializable evidence block for the `results` JSONB. Decimals are
        stringified (the repository json.dumps() this)."""
        return {
            "evaluated_at": self._now().isoformat(),
            "overall_pass": record.overall_pass,
            "criteria": [
                {"id": c.id, "passed": c.passed, "detail": c.detail} for c in record.criteria
            ],
            "thresholds": {
                "min_bars": record.thresholds.min_bars,
                "min_fills": record.thresholds.min_fills,
                "max_total_return_deviation": str(record.thresholds.max_total_return_deviation),
            },
            "deferred_criteria": list(record.deferred_criteria),
            "note": _NOTE,
        }
