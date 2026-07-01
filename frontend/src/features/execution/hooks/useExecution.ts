// Doc 08 §State Management: TanStack Query for server state
import { useQuery } from '@tanstack/react-query'
import { executionService } from '../services/execution.service'

export function useOrders(portfolioId: string) {
  return useQuery({
    queryKey: ['orders', portfolioId],
    queryFn: () => executionService.getOrders(portfolioId),
    enabled: Boolean(portfolioId),
  })
}
