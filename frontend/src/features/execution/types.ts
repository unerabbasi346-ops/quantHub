// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0) §API Layer
// Typed models mirroring the backend OrderOut / ExecutionOut
// (api/v1/execution.py, Step 4.4). Reconciled from the Step 0.5 speculative
// shapes (same reconciliation as Steps 4.2/4.3):
//   - snake_case field names (the real JSON contract);
//   - ALL Decimal fields are strings (quantity/filled_quantity NUMERIC(28,8),
//     average_price/price NUMERIC(18,8)) — the Step 0.5 `quantity: number` was
//     wrong for a fractional-crypto qty;
//   - side/status narrowed to the states actually modeled in Phase 3A: side
//     BUY/SELL only (OrderSide is S-5 scoped — no SHORT/COVER), status
//     CREATED/VALIDATED/REJECTED/FILLED only (the Step 3.5 lifecycle; the
//     Step 0.5 union listed ROUTED/PARTIALLY_FILLED/etc. that F-16 defers);
//   - Order enriched with symbol/exchange (resolved server-side) and its fill
//     outcome (filled_quantity/average_price, null until filled).
// Per Doc 00 §14.11
import type { UUID, ISOTimestamp } from '@/types'

export type OrderSide = 'BUY' | 'SELL'
export type OrderStatus = 'CREATED' | 'VALIDATED' | 'REJECTED' | 'FILLED'
// Order side directly encodes direction under S-5's BUY/SELL-only model
// (domain/strategy_engine/implied_sizing.py's LONG/SHORT constants reused
// server-side) — see api/v1/execution.py OrderOut.direction docstring.
export type Direction = 'LONG' | 'SHORT'

export interface Order {
  id: UUID
  portfolio_id: UUID
  asset_id: UUID
  symbol: string | null
  exchange: string | null
  side: OrderSide
  direction: Direction
  strategy_id: UUID | null
  strategy_name: string | null
  order_type: string
  quantity: string
  filled_quantity: string
  average_price: string | null
  status: OrderStatus
  signal_id: UUID | null
  // This fill's realized P&L (migration a2e4c7b1d6f9) — null only for a
  // not-yet-filled order (CREATED/VALIDATED/REJECTED never fills).
  realized_pnl: string | null
  created_at: ISOTimestamp
}

export interface Execution {
  id: UUID
  order_id: UUID
  portfolio_id: UUID
  asset_id: UUID
  side: OrderSide
  quantity: string
  price: string
  commission: string
  net_amount: string
  venue: string
  executed_at: ISOTimestamp
  realized_pnl: string | null
}
