// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0)
// State Management: TanStack Query for server state — Doc 08 §State Management
// Architecture: hooks separate business logic from presentation — Doc 08 §Architecture
// Per Doc 00 §14.11
import { useQuery } from '@tanstack/react-query'
import { executionService } from '../services/execution.service'

export function useOrders(portfolioId: string) {
  return useQuery({
    queryKey: ['orders', portfolioId],
    queryFn: () => executionService.getOrders(portfolioId),
    enabled: Boolean(portfolioId),
  })
}

export function useExecutions(orderId: string) {
  return useQuery({
    queryKey: ['executions', orderId],
    queryFn: () => executionService.getExecutions(orderId),
    enabled: Boolean(orderId),
  })
}
