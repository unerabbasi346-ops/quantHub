// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout / §Data Visualization; §Interaction Standards.
// Doc 08 — Frontend Architecture (QH-008 v1.0) §Architecture / §State Management.
// Doc 14 §10.7.4 Order Lifecycle (CREATED/VALIDATED/REJECTED/FILLED); §10.7.3.
// handbook/ui visual standard — Image 1 (AI Trading Bots) trade ratio + dense
//   metric cards; Image 4 (EchoFi) multi-widget analytics grid.
// Per Doc 00 §14.11
//
// DENSE EXECUTION REBUILD (owner request) — five sections, scoped by a
// STRATEGY selector (not portfolio): orders/executions carry strategy_id
// directly (real FK lineage, api/v1/execution.py GET /strategies/{id}/orders
// & /executions), so scoping by strategy needs no portfolio_id detour — all
// 3 registered strategies currently have portfolio_id=null, which would make
// a portfolio-linkage requirement (the Strategy/Portfolio/Risk pages'
// pattern) hide the one strategy that actually has real orders.
//
// Section 5's "P&L by strategy" widget is the one exception to the
// strategy-scoped feed: it deliberately fetches EVERY registered strategy's
// orders (useQueries, mirroring MarketsShell's useSignalsById pattern) so the
// cross-strategy comparison the task asks for isn't a trivial single bar.
'use client'

import { useMemo, useState } from 'react'
import { useQueries } from '@tanstack/react-query'
import { ArrowLeftRight } from 'lucide-react'
import { PageHeader } from '@/components/ui'
import { useSignals, useStrategies } from '@/features/strategies/hooks/useStrategies'
import { executionService } from '../services/execution.service'
import { useExecutionsByStrategy, useOrdersByStrategy } from '../hooks/useExecution'
import type { Order } from '../types'
import { ExecutionHeader } from './ExecutionHeader'
import { ExecutionOverview } from './ExecutionOverview'
import { AnalyticsGrid } from './AnalyticsGrid'
import { OrderBlotter } from './OrderBlotter'
import { ExecutionQuality } from './ExecutionQuality'

const SIGNAL_HISTORY_LIMIT = 1000

export function ExecutionShell() {
  const strategiesQuery = useStrategies()
  const strategies = strategiesQuery.data ?? []
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const activeId = selectedId ?? strategies[0]?.id ?? ''
  const activeStrategy = strategies.find((s) => s.id === activeId) ?? null

  const ordersQuery = useOrdersByStrategy(activeId)
  const executionsQuery = useExecutionsByStrategy(activeId)
  const signalsQuery = useSignals(activeId, SIGNAL_HISTORY_LIMIT)

  const orders = ordersQuery.data ?? []
  const executions = executionsQuery.data ?? []
  const signals = signalsQuery.data ?? []

  // Cross-strategy P&L comparison for Section 5 — every registered
  // strategy's orders, independent of the header's single selection.
  const allStrategyOrders = useQueries({
    queries: strategies.map((s) => ({
      queryKey: ['orders-by-strategy', s.id],
      queryFn: () => executionService.getOrdersByStrategy(s.id),
      enabled: strategies.length > 0,
    })),
  })
  const allOrders = useMemo<Order[]>(
    () => allStrategyOrders.flatMap((q) => q.data ?? []),
    [allStrategyOrders],
  )

  const loading = strategiesQuery.isLoading || ordersQuery.isLoading || executionsQuery.isLoading

  return (
    <div className="space-y-14">
      <PageHeader
        icon={<ArrowLeftRight size={18} />}
        title="Execution"
        subtitle="Order & execution analytics — real fills, real strategy lineage."
      />

      <ExecutionHeader
        strategies={strategies}
        activeStrategy={activeStrategy}
        onSelect={setSelectedId}
        orders={orders}
        executions={executions}
        loading={loading}
      />

      {activeStrategy && (
        <>
          <ExecutionOverview orders={orders} executions={executions} />
          <AnalyticsGrid orders={orders} executions={executions} signals={signals} />
          <OrderBlotter orders={orders} executions={executions} />
          <ExecutionQuality orders={allOrders} executions={executions} />
        </>
      )}
    </div>
  )
}
