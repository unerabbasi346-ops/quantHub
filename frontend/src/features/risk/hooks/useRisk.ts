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
    // Raised from 10s (perf pass) — 10s was the fastest poll on the
    // platform and ran even when Risk wasn't the visible page. 60s minimum
    // per the perf pass's "nothing faster than 30s" rule; risk snapshots
    // don't need sub-minute freshness for an intraday, not HFT, workflow.
    refetchInterval: 60_000,
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
