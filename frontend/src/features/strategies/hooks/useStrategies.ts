// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0)
// State Management: TanStack Query for server state — Doc 08 §State Management
// Architecture: hooks separate business logic from presentation — Doc 08 §Architecture
// Per Doc 00 §14.11
import { useQuery } from '@tanstack/react-query'
import { strategiesService } from '../services/strategies.service'

export function useStrategies() {
  return useQuery({ queryKey: ['strategies'], queryFn: strategiesService.getStrategies })
}

export function useSignals(strategyId: string) {
  return useQuery({
    queryKey: ['signals', strategyId],
    queryFn: () => strategiesService.getSignals(strategyId),
    enabled: Boolean(strategyId),
  })
}

export function useBacktests(strategyId: string) {
  return useQuery({
    queryKey: ['backtests', strategyId],
    queryFn: () => strategiesService.getBacktests(strategyId),
    enabled: Boolean(strategyId),
  })
}
