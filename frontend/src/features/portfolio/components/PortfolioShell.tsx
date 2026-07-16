// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout / §Data Visualization; §Interaction Standards.
// Doc 08 — Frontend Architecture (QH-008 v1.0) §Architecture / §State Management.
// handbook/ui/visual_engineering/13_VISUAL_DNA — Image 2 (Finor)/Image 1 (AI
//   Trading Bots) visual standard. Per Doc 00 §14.11
//
// DENSE PORTFOLIO REBUILD (owner request) — a STRATEGY selector now drives
// every section (previously a portfolio selector): (1) header summary strip,
// (2) equity/performance hero row, (3) position analytics (table/allocation/
// utilization), (4) tabbed backtest analytics, (5) cross-strategy comparison.
//
// STRATEGY <-> PORTFOLIO LINKAGE (flagged, real gap — not a bug in this
// page): every currently registered strategy has `portfolio_id: null` at the
// schema level (no registration flow sets it yet). Rather than silently
// inferring a linkage the schema doesn't establish (e.g. scanning all
// portfolios' orders for a matching signal_id — a real but indirect,
// easy-to-misread relationship), this page respects `strategy.portfolio_id`
// as authoritative: when set, Sections 1/3 show that portfolio's real NAV/
// positions; when null, they show an explicit "no linked portfolio"
// disclosure instead of guessing. Section 2 (equity proxy + backtest
// results) and Section 4 (backtest analytics) are keyed directly by
// strategy_id and render full real data regardless of the portfolio link.
'use client'

import { useMemo, useState } from 'react'
import { Wallet } from 'lucide-react'
import { EmptyState, ErrorState, PageHeader } from '@/components/ui'
import { useBacktests, useSignals, useStrategies } from '@/features/strategies/hooks/useStrategies'
import { usePortfolios, usePositions } from '../hooks/usePortfolio'
import { CapitalConfig } from './CapitalConfig'
import { PortfolioHeader } from './PortfolioHeader'
import { HeroRow } from './HeroRow'
import { PositionAnalytics } from './PositionAnalytics'
import { BacktestAnalyticsTabs } from './BacktestAnalyticsTabs'
import { StrategyComparison } from './StrategyComparison'

const SIGNAL_HISTORY_LIMIT = 1000
const fmtTime = (ts: string) => new Date(ts).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })

export function PortfolioShell() {
  const strategiesQuery = useStrategies()
  const strategies = useMemo(() => strategiesQuery.data ?? [], [strategiesQuery.data])
  const [selectedStrategyId, setSelectedStrategyId] = useState<string | null>(null)

  const activeStrategyId = selectedStrategyId ?? strategies[0]?.id ?? ''
  const activeStrategy = strategies.find((s) => s.id === activeStrategyId) ?? null

  const backtestsQuery = useBacktests(activeStrategyId)
  const backtests = backtestsQuery.data ?? []
  const latestBacktest = backtests[0] ?? null

  const signalsQuery = useSignals(activeStrategyId, SIGNAL_HISTORY_LIMIT)
  const signals = signalsQuery.data ?? []
  const orderedSignals = useMemo(() => [...signals].sort((a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime()), [signals])
  const points = useMemo(
    () => orderedSignals.map((s) => ({ label: fmtTime(s.ts), value: Number.parseFloat(s.value) })),
    [orderedSignals],
  )

  // Linked portfolio — see module docstring for why this is a strict lookup,
  // not an inferred one.
  const portfoliosQuery = usePortfolios()
  const portfolios = portfoliosQuery.data ?? []
  const linkedPortfolio = activeStrategy?.portfolio_id ? portfolios.find((p) => p.id === activeStrategy.portfolio_id) ?? null : null
  const positionsQuery = usePositions(linkedPortfolio?.id ?? '')
  const positions = positionsQuery.data ?? []

  return (
    <div className="space-y-8">
      <PageHeader
        icon={<Wallet size={18} />}
        title="Portfolio"
        subtitle="Strategy-driven NAV, positions and backtest performance — real recorded state."
      />

      {strategiesQuery.isLoading && <div className="skeleton h-24 w-full" />}
      {strategiesQuery.isError && <ErrorState description="Could not load strategies." onRetry={() => strategiesQuery.refetch()} />}
      {strategiesQuery.isSuccess && strategies.length === 0 && (
        <EmptyState icon={<Wallet size={20} />} title="No strategies" description="No strategies are registered yet." />
      )}

      {activeStrategy && (
        <>
          <PortfolioHeader
            strategies={strategies}
            activeStrategy={activeStrategy}
            onSelect={setSelectedStrategyId}
            linkedPortfolio={linkedPortfolio}
            positions={positions}
            positionsLoading={Boolean(linkedPortfolio) && positionsQuery.isLoading}
            backtestTotalReturn={latestBacktest?.total_return ?? null}
            backtestRealizedPnl={latestBacktest?.results?.realized_pnl ?? null}
            backtestUnrealizedPnl={latestBacktest?.results?.unrealized_pnl ?? null}
          />

          <HeroRow points={points} latestBacktest={latestBacktest} />

          <PositionAnalytics
            hasLinkedPortfolio={Boolean(linkedPortfolio)}
            linkedPortfolio={linkedPortfolio}
            positions={positions}
            positionsLoading={positionsQuery.isLoading}
            positionsError={positionsQuery.isError}
            onRetry={() => positionsQuery.refetch()}
            strategyId={activeStrategy.id}
          />

          <BacktestAnalyticsTabs backtest={latestBacktest} signals={signals} strategyId={activeStrategy.id} />

          <StrategyComparison strategies={strategies} />

          {linkedPortfolio && <CapitalConfig portfolio={linkedPortfolio} openMarketValue={positions.filter((p) => !p.is_closed).reduce((s, p) => s + Math.abs(Number.parseFloat(p.market_value)), 0)} />}
        </>
      )}
    </div>
  )
}
