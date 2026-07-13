// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0) §API Layer
// All backend communication through the centralized client (which unwraps the
// Doc 10 envelope's `.data`, Step 4.2) — Doc 08 §API Layer.
// Per Doc 00 §14.11
import { apiClient } from '@/lib/api/client'
import type { Asset, CorrelationMatrix, FundingRate, OHLCVBar } from '../types'

// Default bar window for the chart. The backend caps `limit` at 1000
// (api/v1/markets.py); 500 covers the full currently-ingested BTC/USDT 1h
// history without hitting the cap. `interval` is URL-encoded because a bar
// interval could contain characters that need escaping.
const DEFAULT_BAR_LIMIT = 500

export const marketsService = {
  getAssets: () => apiClient.get<Asset[]>('/v1/assets'),
  getBars: (assetId: string, interval: string, limit: number = DEFAULT_BAR_LIMIT) =>
    apiClient.get<OHLCVBar[]>(
      `/v1/assets/${assetId}/bars?interval=${encodeURIComponent(interval)}&limit=${limit}`,
    ),
  // Price-return correlation matrix across ingested instruments (NOT risk).
  getCorrelation: (interval = '1h') =>
    apiClient.get<CorrelationMatrix>(`/v1/markets/correlation?interval=${encodeURIComponent(interval)}`),
  // Perpetual funding-rate history (Doc 14 §10.9.5) — empty array for a SPOT
  // asset_id, never an error (nothing is ever ingested for SPOT).
  getFundingRates: (assetId: string, limit = 500) =>
    apiClient.get<FundingRate[]>(`/v1/assets/${assetId}/funding-rates?limit=${limit}`),
}
