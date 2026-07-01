// Doc 08 §API Layer: centralized client — Doc 08 §API Layer
import { apiClient } from '@/lib/api/client'
import type { Asset, OHLCVBar } from '../types'

export const marketsService = {
  getAssets: () =>
    apiClient.get<Asset[]>('/v1/assets'),
  getBars: (assetId: string, interval: string) =>
    apiClient.get<OHLCVBar[]>(`/v1/assets/${assetId}/bars?interval=${interval}`),
}
