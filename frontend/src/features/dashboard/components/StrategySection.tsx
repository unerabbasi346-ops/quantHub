// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0) §Layout,
//   §Dashboards. Doc 08 §Architecture (dashboard composes feature hooks).
//   Doc 00 §14.5 (data honesty). Per Doc 00 §14.11
//
// The dashboard's strategy workspace (owner request, points 4–6): one
// glowing card per registered strategy. The rotating conviction chart now
// lives in the Hero (HeroSection.tsx) — not duplicated here. Scales to any
// number of strategies (currently 2). Reads REAL core.strategies /
// core.signals / analytics.backtests only.
'use client'

import { Brain } from 'lucide-react'
import { Badge, EmptyState, ErrorState } from '@/components/ui'
import { useStrategies } from '@/features/strategies/hooks/useStrategies'
import { useStrategyPerformance } from '@/features/strategies/hooks/useStrategyPerformance'
import { StrategyCard } from '@/features/strategies/components/StrategyCard'

export function StrategySection() {
  const query = useStrategies()
  // Dashboard cards show the platform's EXECUTABLE strategies only (the
  // reference plugins that trade through the live engine). lancaster-ml-
  // momentum is signal-replay-only (no plugin) — its historical backtests
  // live on the Research page, but it isn't a live-trading card here.
  const strategies = (query.data ?? []).filter((s) => s.name.startsWith('reference-'))
  const performance = useStrategyPerformance(strategies)

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-fg-muted">
            <Brain size={16} />
          </span>
          <h2 className="text-sm font-semibold tracking-tight text-fg">Strategies</h2>
          {query.isSuccess && <Badge variant="neutral">{strategies.length}</Badge>}
        </div>
        <p className="text-[11px] text-fg-subtle">
          Live signals and backtest results per registered strategy
        </p>
      </div>

      {query.isLoading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <div className="skeleton h-40" />
          <div className="skeleton h-40" />
        </div>
      )}
      {query.isError && <ErrorState description="Could not load strategies." onRetry={() => query.refetch()} />}
      {query.isSuccess && strategies.length === 0 && (
        <EmptyState
          icon={<Brain size={20} />}
          title="No strategies registered"
          description="Register a strategy to see it here. Run: python scripts/register_strategy.py --all"
        />
      )}

      {query.isSuccess && strategies.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {performance.map((perf) => (
            <StrategyCard key={perf.strategy.id} perf={perf} />
          ))}
        </div>
      )}
    </section>
  )
}
