// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0)
// State Management: TanStack Query for server state — Doc 08 §State Management
// Architecture: hooks separate business logic from presentation — Doc 08 §Architecture
// Per Doc 00 §14.11
import { useQuery } from '@tanstack/react-query'
import { riskService } from '../services/risk.service'

export function useRiskSnapshot(portfolioId: string) {
  return useQuery({
    queryKey: ['risk-snapshot', portfolioId],
    queryFn: () => riskService.getSnapshot(portfolioId),
    enabled: Boolean(portfolioId),
    refetchInterval: 10_000, // Doc 15 §Risk SLO: intraday update cadence
  })
}

export function useRiskLimits(portfolioId: string) {
  return useQuery({
    queryKey: ['risk-limits', portfolioId],
    queryFn: () => riskService.getLimits(portfolioId),
    enabled: Boolean(portfolioId),
  })
}

export function useRiskAssessments(portfolioId: string) {
  return useQuery({
    queryKey: ['risk-assessments', portfolioId],
    queryFn: () => riskService.getAssessments(portfolioId),
    enabled: Boolean(portfolioId),
  })
}
