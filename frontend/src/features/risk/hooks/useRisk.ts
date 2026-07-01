// Doc 08 §State Management: TanStack Query for server state
import { useQuery } from '@tanstack/react-query'
import { riskService } from '../services/risk.service'

export function useRiskSnapshot(portfolioId: string) {
  return useQuery({
    queryKey: ['risk', portfolioId],
    queryFn: () => riskService.getLatestSnapshot(portfolioId),
    enabled: Boolean(portfolioId),
    refetchInterval: 10_000,  // Doc 15 §Risk SLO: intraday update ≤10 s
  })
}
