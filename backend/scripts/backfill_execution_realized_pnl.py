"""Backfill core.executions.realized_pnl for fills recorded before migration
a2e4c7b1d6f9 added the column.

Governing specification: Doc 14 §10.9.3/§10.9.5 (realized P&L "on trade
execution"); domain/portfolio/positions.py::apply_fill_to_position is the
ONLY place this platform computes realized P&L, and it is deterministic
(P-13) given a starting (quantity=0, average_price=0) and the exact sequence
of prior fills. Replaying that same pure function chronologically per
(portfolio_id, asset_id) reproduces exactly what the live fill path would
have written, had the column existed from the start — not an approximation.

Idempotent: always recomputes and overwrites every row for a given
(portfolio_id, asset_id) pair from scratch, so re-running after new fills
land is safe (it just redoes cheap in-memory arithmetic and re-UPDATEs).

Run:  DATABASE_URL=... python scripts/backfill_execution_realized_pnl.py
"""
from __future__ import annotations

import asyncio

from sqlalchemy import text

from quant_hub.domain.execution.entities import OrderSide
from quant_hub.domain.portfolio.positions import apply_fill_to_position
from quant_hub.infrastructure.database import AsyncSessionLocal

_ZERO = __import__("decimal").Decimal("0")


async def main() -> None:
    async with AsyncSessionLocal() as session:
        pairs = (
            await session.execute(
                text("SELECT DISTINCT portfolio_id, asset_id FROM core.executions")
            )
        ).all()

        total_rows = 0
        for portfolio_id, asset_id in pairs:
            fills = (
                await session.execute(
                    text(
                        """
                        SELECT id, side, quantity, price
                        FROM core.executions
                        WHERE portfolio_id = :portfolio_id AND asset_id = :asset_id
                        ORDER BY executed_at, id
                        """
                    ),
                    {"portfolio_id": portfolio_id, "asset_id": asset_id},
                )
            ).mappings().all()

            cur_qty = _ZERO
            cur_avg = _ZERO
            for row in fills:
                side = OrderSide(row["side"])
                signed_qty = row["quantity"] if side is OrderSide.BUY else -row["quantity"]
                update = apply_fill_to_position(cur_qty, cur_avg, signed_qty, row["price"])
                await session.execute(
                    text("UPDATE core.executions SET realized_pnl = :pnl WHERE id = :id"),
                    {"pnl": update.realized_pnl, "id": row["id"]},
                )
                cur_qty = update.quantity
                cur_avg = update.average_entry_price
                total_rows += 1

        await session.commit()
        print(f"backfilled realized_pnl for {total_rows} execution rows across {len(pairs)} (portfolio, asset) pairs")


if __name__ == "__main__":
    asyncio.run(main())
