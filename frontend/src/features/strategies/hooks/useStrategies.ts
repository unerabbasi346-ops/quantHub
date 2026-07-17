// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0)
// State Management: TanStack Query for server state — Doc 08 §State Management
// Architecture: hooks separate business logic from presentation — Doc 08 §Architecture
// Per Doc 00 §14.11
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError } from '@/lib/api/client'
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

// Server-side monthly realized P&L calendar (one row per month) — bounded by
// calendar time, so a 5-year strategy never hits the signal feed's row cap.
export function useMonthlyReturns(strategyId: string) {
  return useQuery({
    queryKey: ['monthly-returns', strategyId],
    queryFn: () => strategiesService.getMonthlyReturns(strategyId),
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

// Computed metrics 404 when the strategy has no COMPLETED backtest yet —
// that's a real "no metrics" state, not a fetch failure, so it resolves to
// null instead of an error.
export function useStrategyMetrics(strategyId: string) {
  return useQuery({
    queryKey: ['strategy-metrics', strategyId],
    queryFn: async () => {
      try {
        return await strategiesService.getMetrics(strategyId)
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return null
        throw err
      }
    },
    enabled: Boolean(strategyId),
  })
}

export function useTradePnlDistribution(strategyId: string) {
  return useQuery({
    queryKey: ['trade-pnl-distribution', strategyId],
    queryFn: () => strategiesService.getTradePnlDistribution(strategyId),
    enabled: Boolean(strategyId),
  })
}
