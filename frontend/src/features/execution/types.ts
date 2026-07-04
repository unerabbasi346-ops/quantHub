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

export interface Order {
  id: UUID
  portfolio_id: UUID
  asset_id: UUID
  symbol: string | null
  exchange: string | null
  side: OrderSide
  order_type: string
  quantity: string
  filled_quantity: string
  average_price: string | null
  status: OrderStatus
  signal_id: UUID | null
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
}
