// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0)
// State Management: TanStack Query for server state — Doc 08 §State Management
// Architecture: hooks separate business logic from presentation — Doc 08 §Architecture
// Per Doc 00 §14.11
import { useQuery } from '@tanstack/react-query'
import { executionService } from '../services/execution.service'

export function useOrders(portfolioId: string, limit?: number) {
  return useQuery({
    queryKey: ['orders', portfolioId, limit],
    queryFn: () => executionService.getOrders(portfolioId, limit),
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

export function useOrdersByStrategy(strategyId: string, limit?: number) {
  return useQuery({
    queryKey: ['orders-by-strategy', strategyId, limit],
    queryFn: () => executionService.getOrdersByStrategy(strategyId, limit),
    enabled: Boolean(strategyId),
  })
}

export function useExecutionsByStrategy(strategyId: string, limit?: number) {
  return useQuery({
    queryKey: ['executions-by-strategy', strategyId, limit],
    queryFn: () => executionService.getExecutionsByStrategy(strategyId, limit),
    enabled: Boolean(strategyId),
  })
}
