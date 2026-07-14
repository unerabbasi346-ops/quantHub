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
  // SPOT | PERPETUAL (migration e7a3c1f5b9d2 / S-10). A SPOT instrument has
  // no funding concept — callers use this to decide whether to even ask for
  // funding-rate data, not the funding endpoint (which just returns empty).
  instrument_type: string
}

// A market_data.funding_rates row (Doc 14 §10.9.5) — PERPETUAL-only periodic
// financing cashflow. Empty for a SPOT asset_id (never ingested), not an error.
export interface FundingRate {
  asset_id: UUID
  funding_time: ISOTimestamp
  funding_rate: string
  mark_price: string | null
  next_funding_time: ISOTimestamp | null
  interval_hours: number | null
}

// A market_data.open_interest row (migration b4f8e21ac9d3) — PERPETUAL-only.
// The API 404s for a SPOT asset_id rather than returning empty (deliberately
// different from the funding-rates endpoint's own choice).
export interface OpenInterest {
  asset_id: UUID
  ts: ISOTimestamp
  open_interest_usdt: string
  open_interest_contracts: string | null
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

// Price-return correlation (api/v1/markets.py GET /markets/correlation).
// A DESCRIPTIVE price-return correlation between instruments — NOT a portfolio
// risk metric, and unrelated to F-18's deferred VaR/CVaR/beta. `matrix[i][j]`
// is the Pearson correlation of returns; null where undefined (constant series).
export interface CorrelationAsset {
  id: UUID
  symbol: string
}

export interface CorrelationMatrix {
  interval: string
  sample_size: number
  assets: CorrelationAsset[]
  matrix: (number | null)[][]
}
