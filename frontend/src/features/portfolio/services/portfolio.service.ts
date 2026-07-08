// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0)
// API Layer: all backend communication through centralized client — Doc 08 §API Layer
// Per Doc 00 §14.11
import { apiClient } from '@/lib/api/client'
import type { Portfolio, Position } from '../types'

export const portfolioService = {
  getPortfolios: () => apiClient.get<Portfolio[]>('/v1/portfolios'),
  getPositions: (portfolioId: string) =>
    apiClient.get<Position[]>(`/v1/portfolios/${portfolioId}/positions`),
  // Write: set the operator-configured capital figure (F-19-honest — no NAV
  // ledger; api/v1/portfolio.py PUT /portfolios/{id}/capital).
  setCapital: (portfolioId: string, configured_capital: string) =>
    apiClient.put<Portfolio>(`/v1/portfolios/${portfolioId}/capital`, { configured_capital }),
}
