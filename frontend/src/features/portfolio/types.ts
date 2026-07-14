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
  // Operator-set capital figure (migration a7d2e1f04b93). Null when never
  // configured. Display/config only — has NO backing NAV ledger and does not
  // feed leverage/risk math (F-19 remains open).
  configured_capital: string | null
}

export interface Position {
  id: UUID
  portfolio_id: UUID
  asset_id: UUID
  symbol: string | null
  exchange: string | null
  // SPOT | PERPETUAL | null (asset-resolved; null if the asset lookup failed).
  instrument_type: string | null
  quantity: string
  average_entry_price: string
  market_value: string
  unrealized_pnl: string
  realized_pnl_today: string
  last_price: string | null
  // Migration e7a3c1f5b9d2 (S-10). Null for SPOT (honest absence, never a
  // fabricated 1x/0) — only populated for a PERPETUAL position. F-19:
  // margin_used is storage only, not backed by an authoritative equity ledger.
  leverage: string | null
  margin_used: string | null
  is_closed: boolean
  sequence_number: number
}
