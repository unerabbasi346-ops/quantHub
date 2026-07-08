// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0)
// State Management: TanStack Query for server state — Doc 08 §State Management
// Architecture: hooks separate business logic from presentation — Doc 08 §Architecture
// Per Doc 00 §14.11
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { portfolioService } from '../services/portfolio.service'

export function usePortfolios() {
  return useQuery({
    queryKey: ['portfolios'],
    queryFn: portfolioService.getPortfolios,
  })
}

export function usePositions(portfolioId: string) {
  return useQuery({
    queryKey: ['positions', portfolioId],
    queryFn: () => portfolioService.getPositions(portfolioId),
    enabled: Boolean(portfolioId),
  })
}

// Write: set configured capital (F-19-honest). On success, invalidate the
// portfolios list so the new figure is reflected everywhere it's shown.
export function useSetCapital(portfolioId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (amount: string) => portfolioService.setCapital(portfolioId, amount),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['portfolios'] })
    },
  })
}
