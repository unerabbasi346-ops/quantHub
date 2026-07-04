// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0)
// API Layer: all backend communication through centralized client — Doc 08 §API Layer
// Per Doc 00 §14.11
import { apiClient } from '@/lib/api/client'
import type { PreTradeAssessment, RiskLimit, RiskSnapshot } from '../types'

export const riskService = {
  // Latest portfolio risk snapshot — null when none has been computed yet
  // (api/v1/risk.py, Step 4.6). Paths reconciled to the portfolio-scoped
  // convention used by every other slice (/v1/portfolios/{id}/...).
  getSnapshot: (portfolioId: string) =>
    apiClient.get<RiskSnapshot | null>(`/v1/portfolios/${portfolioId}/risk/snapshot`),
  // Governed risk limits + current utilization.
  getLimits: (portfolioId: string) =>
    apiClient.get<RiskLimit[]>(`/v1/portfolios/${portfolioId}/risk/limits`),
  // Pre-trade assessment history (approved/rejected + reasons).
  getAssessments: (portfolioId: string, limit = 100) =>
    apiClient.get<PreTradeAssessment[]>(
      `/v1/portfolios/${portfolioId}/risk/assessments?limit=${limit}`,
    ),
}
