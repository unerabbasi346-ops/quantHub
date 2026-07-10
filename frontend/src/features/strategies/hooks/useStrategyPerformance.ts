// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0)
//   §State Management (TanStack Query), §Architecture (hooks hold data logic).
// Doc 14 §10.6.4 (Signal Recording), §10.3 (Backtesting). Doc 15 §11.1.5
//   (signal value = signed conviction). Per Doc 00 §14.11
//
// Derives the per-strategy performance view the dashboard's strategy cards and
// the auto-rotating chart both consume — from REAL data only:
//   - conviction series: the signed signal `value`s over time (core.signals),
//   - real return %: the latest backtest's total_return (analytics.backtests).
// Metrics that are NOT genuinely computed (drawdown, win rate) are deliberately
// absent here — the UI shows an honest "Not yet computed" state for them
// (F-18/F-21), never a fabricated number.
import { useQueries } from '@tanstack/react-query'
import type { LinePoint } from '@/components/ui'
import { strategiesService } from '../services/strategies.service'
import type { Backtest, Signal, Strategy } from '../types'

export interface StrategyPerformance {
  strategy: Strategy
  signals: Signal[]
  /** Signed conviction over time, oldest → newest (for the line chart). */
  convictionPoints: LinePoint[]
  /** Bare conviction values for a mini sparkline. */
  sparkline: number[]
  /** Latest backtest total_return as a raw string, or null if none exists. */
  latestReturn: string | null
  hasBacktest: boolean
  loading: boolean
}

const byTimeAsc = (a: Signal, b: Signal) => new Date(a.ts).getTime() - new Date(b.ts).getTime()

export function useStrategyPerformance(strategies: Strategy[]): StrategyPerformance[] {
  const signalQueries = useQueries({
    queries: strategies.map((s) => ({
      queryKey: ['signals', s.id],
      queryFn: () => strategiesService.getSignals(s.id),
      enabled: Boolean(s.id),
    })),
  })
  const backtestQueries = useQueries({
    queries: strategies.map((s) => ({
      queryKey: ['backtests', s.id],
      queryFn: () => strategiesService.getBacktests(s.id),
      enabled: Boolean(s.id),
    })),
  })

  return strategies.map((strategy, i) => {
    const signals = signalQueries[i]?.data ?? []
    const backtests: Backtest[] = backtestQueries[i]?.data ?? []
    const ordered = [...signals].sort(byTimeAsc)
    const convictionPoints: LinePoint[] = ordered.map((s) => ({
      label: new Date(s.ts).toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      }),
      value: Number.parseFloat(s.value),
    }))
    const latest = backtests[0] ?? null
    return {
      strategy,
      signals,
      convictionPoints,
      sparkline: convictionPoints.map((p) => p.value),
      latestReturn: latest?.total_return ?? null,
      hasBacktest: Boolean(latest),
      loading: Boolean(signalQueries[i]?.isLoading || backtestQueries[i]?.isLoading),
    }
  })
}
