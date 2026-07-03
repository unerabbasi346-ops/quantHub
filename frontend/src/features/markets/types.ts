// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0) §API Layer
// Typed models mirroring the backend AssetOut / OHLCVBarOut (api/v1/markets.py,
// Step 4.1). Reconciled in Step 4.2 from the Step 0.5 speculative shapes:
//   - snake_case field names (the real JSON contract — matches Doc 09 columns
//     and Doc 10's own snake_case envelope fields), not camelCase;
//   - OHLCVBar has NO `id` (a bar's natural key is asset_id+interval+ts; the
//     domain entity carries no surrogate id and the endpoint doesn't emit one);
//   - all Decimal fields are strings (backend serializes Decimal as a
//     precision-preserving string, incl. `volume`), never number.
// Per Doc 00 §14.11
import type { UUID, ISOTimestamp } from '@/types'

export interface Asset {
  id: UUID
  symbol: string
  exchange: string
  asset_class: string
  name: string | null
  currency: string
  is_active: boolean
}

export interface OHLCVBar {
  asset_id: UUID
  interval: string
  ts: ISOTimestamp
  open: string
  high: string
  low: string
  close: string
  volume: string
  vwap: string | null
  trade_count: number | null
  adjustment_factor: string
  data_quality: string
  source: string | null
}
