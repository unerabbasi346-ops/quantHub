// Doc 08 §API Layer: centralized client
import { apiClient } from '@/lib/api/client'
import type { RiskSnapshot } from '../types'

export const riskService = {
  getLatestSnapshot: (portfolioId: string) =>
    apiClient.get<RiskSnapshot>(`/v1/risk/portfolios/${portfolioId}/latest`),
}
