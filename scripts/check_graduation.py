#!/usr/bin/env python
# Governing specification: Doc 05 — Engineering Standards (mandatory paper
#   trading before live). Doc 14 §10.5.9 (Paper-to-Live Promotion Gate),
#   §10.5.10 (Paper Trading Artifacts).
#   Doc 04 — Repository Structure (QH-004): scripts/ = "Automation utilities";
#   "No business logic inside scripts/" — this only wires the
#   already-implemented GraduationService to a session id and prints the record,
#   mirroring scripts/run_paper_session.py. The evaluation LOGIC lives in
#   domain/paper_trading/graduation.py.
# Per Doc 00 §14.11
#
# Step 5.4: run the graduation-criteria check against a completed paper session
# and print the honestly-reasoned pass/fail record. This is a RECORD tool — it
# records evidence into the session's artifacts; it does NOT promote anything to
# live trading (a human decides, Doc 05).
#
# Usage (from repo root, with a live Postgres reachable at DATABASE_URL):
#   DATABASE_URL=postgresql+asyncpg://... python scripts/check_graduation.py \
#       --session-id <uuid> [--min-bars 20] [--min-fills 1] [--max-deviation 0.05]
from __future__ import annotations

import argparse
import asyncio
import sys
from decimal import Decimal
from pathlib import Path
from uuid import UUID

_BACKEND_SRC = Path(__file__).resolve().parent.parent / "backend" / "src"
sys.path.insert(0, str(_BACKEND_SRC))

from quant_hub.application.paper_trading.graduation_service import GraduationService  # noqa: E402
from quant_hub.domain.paper_trading.graduation import GraduationThresholds  # noqa: E402
from quant_hub.infrastructure.database import AsyncSessionLocal, engine  # noqa: E402
from quant_hub.persistence.repositories.paper_trading import (  # noqa: E402
    SQLAlchemyPaperTradingSessionRepository,
)


async def run(args: argparse.Namespace) -> None:
    thresholds = GraduationThresholds(
        min_bars=args.min_bars,
        min_fills=args.min_fills,
        max_total_return_deviation=Decimal(str(args.max_deviation)),
    )
    try:
        async with AsyncSessionLocal() as session:
            service = GraduationService(SQLAlchemyPaperTradingSessionRepository(session))
            record = await service.evaluate(UUID(args.session_id), thresholds=thresholds)
            # Repository methods never commit (Doc 07 — caller owns the
            # transaction); this script is the caller recording the evidence.
            await session.commit()

        verdict = "PASS" if record.overall_pass else "FAIL"
        print(f"graduation check: session={args.session_id} overall={verdict}")
        print(
            f"thresholds: min_bars={thresholds.min_bars} min_fills={thresholds.min_fills} "
            f"max_total_return_deviation={thresholds.max_total_return_deviation}"
        )
        for c in record.criteria:
            print(f"  [{'PASS' if c.passed else 'FAIL'}] {c.id}: {c.detail}")
        print("deferred (not evaluated — F-18 / no live-limit exercise yet):")
        for d in record.deferred_criteria:
            print(f"  - {d}")
        print(
            "NOTE: record only — Doc 05 requires a human to authorise live promotion; "
            "this is not an automated live-trading gate."
        )
    finally:
        await engine.dispose()


def main() -> None:
    # The record embeds governing-doc citations (§, em dashes); emit UTF-8 so a
    # Windows cp1252 console renders them cleanly rather than as mojibake (the
    # stored JSONB is already correct UTF-8 — this is display only).
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Record the graduation-criteria pass/fail for a paper session (Step 5.4)."
    )
    parser.add_argument("--session-id", required=True, help="analytics.paper_trading_sessions.id")
    parser.add_argument("--min-bars", type=int, default=GraduationThresholds.min_bars)
    parser.add_argument("--min-fills", type=int, default=GraduationThresholds.min_fills)
    parser.add_argument(
        "--max-deviation", default=str(GraduationThresholds.max_total_return_deviation),
        help="max |paper - backtest total-return deviation| (default 0.05)",
    )
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
