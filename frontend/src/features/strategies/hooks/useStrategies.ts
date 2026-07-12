// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0)
// State Management: TanStack Query for server state — Doc 08 §State Management
// Architecture: hooks separate business logic from presentation — Doc 08 §Architecture
// Per Doc 00 §14.11
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { strategiesService } from '../services/strategies.service'

export function useStrategies() {
  return useQuery({ queryKey: ['strategies'], queryFn: strategiesService.getStrategies })
}

// Write: governed Activate/Deactivate transition (first real write). On
// success, invalidate the registry so the new status is reflected everywhere.
export function useSetStrategyStatus() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'ACTIVE' | 'INACTIVE' }) =>
      strategiesService.setStatus(id, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['strategies'] })
    },
  })
}

export function useSignals(strategyId: string, limit = 100) {
  return useQuery({
    queryKey: ['signals', strategyId, limit],
    queryFn: () => strategiesService.getSignals(strategyId, limit),
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
