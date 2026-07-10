// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0) §Layout,
//   §Dashboards. Doc 08 §Architecture (dashboard composes feature hooks).
//   Doc 00 §14.5 (data honesty). Per Doc 00 §14.11
//
// The dashboard's strategy hero (owner request, points 4–6): an auto-rotating
// conviction chart alongside one glowing card per registered strategy. Scales
// to any number of strategies (currently 2). Reads REAL core.strategies /
// core.signals / analytics.backtests only.
'use client'

import { Brain } from 'lucide-react'
import { Badge, EmptyState, ErrorState } from '@/components/ui'
import { useStrategies } from '@/features/strategies/hooks/useStrategies'
import { useStrategyPerformance } from '@/features/strategies/hooks/useStrategyPerformance'
import { RotatingStrategyChart } from '@/features/strategies/components/RotatingStrategyChart'
import { StrategyCard } from '@/features/strategies/components/StrategyCard'

export function StrategySection() {
  const query = useStrategies()
  const strategies = query.data ?? []
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
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
          <div className="skeleton h-80 xl:col-span-2" />
          <div className="space-y-4">
            <div className="skeleton h-40" />
            <div className="skeleton h-40" />
          </div>
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
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
          <div className="min-h-[22rem] xl:col-span-2">
            <RotatingStrategyChart items={performance} />
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-1">
            {performance.map((perf) => (
              <StrategyCard key={perf.strategy.id} perf={perf} />
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
