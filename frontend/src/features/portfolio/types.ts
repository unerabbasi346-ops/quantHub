// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0) §API Layer
// Typed models mirroring the backend PortfolioOut / PositionOut
// (api/v1/portfolio.py, Step 4.3). Reconciled from the Step 0.5 speculative
// shapes (same reconciliation as Step 4.2's markets types):
//   - snake_case field names (the real JSON contract);
//   - ALL Decimal fields are strings incl. `quantity` (NUMERIC(28,8)) —
//     the Step 0.5 `quantity: number` was wrong for a fractional-crypto qty;
//   - Position is enriched with symbol/exchange (resolved server-side).
// Per Doc 00 §14.11
import type { UUID } from '@/types'

export interface Portfolio {
  id: UUID
  name: string
  description: string | null
  base_currency: string
  portfolio_type: string
  is_active: boolean
}

export interface Position {
  id: UUID
  portfolio_id: UUID
  asset_id: UUID
  symbol: string | null
  exchange: string | null
  quantity: string
  average_entry_price: string
  market_value: string
  unrealized_pnl: string
  realized_pnl_today: string
  last_price: string | null
  is_closed: boolean
  sequence_number: number
}
