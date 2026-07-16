// Governing specification: Doc 14 §10.3 Backtesting; Doc 00 §14.5/§14.7 DATA
//   HONESTY. Section 4 — tabbed backtest analytics (Overview / Monthly
//   Returns / Trade Analysis), reusing the same honest derivations and
//   components already established on the Strategy detail page — this is
//   the same strategy's real data, viewed from the Portfolio workspace.
'use client'

import { useMemo } from 'react'
import { BarChart3, CalendarRange, LayoutGrid, ShieldQuestion, Sigma } from 'lucide-react'
import { Badge, EmptyState, Heatmap, Panel, Section, Tabs } from '@/components/ui'
import { consecutiveRuns, monthlyConvictionGrid, monthlyReturnsGrid } from '@/features/strategies/analytics'
import { ConsecutiveRunsChart } from '@/features/strategies/components/charts'
import { useMonthlyReturns, useStrategyMetrics } from '@/features/strategies/hooks/useStrategies'
import { PendingMetricTile, RealMetricTile, RealRingTile } from '@/features/strategies/components/metric-tiles'
import { fmtMoney, fmtReturnPct } from '@/features/strategies/components/tables'
import type { Backtest, Signal } from '@/features/strategies/types'
import { formatCount, formatMaxDrawdownPct, formatSharpe, formatSignalStrength, formatTimestamp } from '@/lib/utils/format'
import { longShortSplit } from '../analytics'
import { LongShortDonut } from './charts'

const fmtDate = (ts: string | null) => (ts ? formatTimestamp(ts) : '—')

function OverviewTab({ backtest }: { backtest: Backtest | null }) {
  const results = backtest?.results ?? null
  const retNum = backtest?.total_return != null ? Number.parseFloat(backtest.total_return) : null
  const tradeCount = backtest?.trade_count ?? results?.trade_count ?? null
  const realizedNum = results ? Number.parseFloat(results.realized_pnl) : null
  const avgTradePnl = realizedNum != null && tradeCount ? realizedNum / tradeCount : null
  const metricsQuery = useStrategyMetrics(backtest?.strategy_id ?? '')
  const metrics = metricsQuery.data

  if (!backtest) {
    return <EmptyState title="No backtest runs" description="This strategy has no backtest yet — metrics appear once one completes." />
  }

  return (
    <Panel className="grid grid-cols-2 gap-3 p-4 sm:grid-cols-3 lg:grid-cols-4">
      <RealMetricTile
        label="Backtest period"
        value={backtest.start_date && backtest.end_date ? `${fmtDate(backtest.start_date)} → ${fmtDate(backtest.end_date)}` : '—'}
      />
      <RealMetricTile label="Total return" value={fmtReturnPct(backtest.total_return)} tone={retNum == null ? 'default' : retNum >= 0 ? 'profit' : 'risk'} />
      <RealMetricTile label="Trade count" value={tradeCount != null ? formatCount(tradeCount) : '—'} />
      <RealMetricTile label="Realized P&L" value={results ? fmtMoney(results.realized_pnl) : '—'} tone={realizedNum == null ? 'default' : realizedNum >= 0 ? 'profit' : 'risk'} />
      <RealMetricTile label="Final capital" value={fmtMoney(backtest.final_capital)} />
      <RealMetricTile
        label="Avg trade P&L"
        value={avgTradePnl != null ? fmtMoney(String(avgTradePnl)) : '—'}
        tone={avgTradePnl == null ? 'default' : avgTradePnl >= 0 ? 'profit' : 'risk'}
        hint="realized ÷ trade count"
      />
      <PendingMetricTile label="Best trade" shell="number" />
      <PendingMetricTile label="Worst trade" shell="number" />
      {metrics?.win_rate != null ? (
        <RealRingTile label="Win rate" value={Number.parseFloat(metrics.win_rate)} />
      ) : (
        <PendingMetricTile label="Win rate" shell="ring" />
      )}
      {metrics?.sharpe_ratio != null ? (
        <RealMetricTile label="Sharpe ratio" value={formatSharpe(Number.parseFloat(metrics.sharpe_ratio))} />
      ) : (
        <PendingMetricTile label="Sharpe ratio" shell="number" />
      )}
      {metrics?.max_drawdown_pct != null ? (
        <RealMetricTile label="Max drawdown" value={formatMaxDrawdownPct(Number.parseFloat(metrics.max_drawdown_pct))} tone="risk" />
      ) : (
        <PendingMetricTile label="Max drawdown" shell="bar" />
      )}
    </Panel>
  )
}

function MonthlyReturnsTab({ signals, strategyId }: { signals: Signal[]; strategyId: string }) {
  const returnsQuery = useMonthlyReturns(strategyId)
  const rows = returnsQuery.data ?? []
  // REAL realized-P&L calendar (server-side, from executions) when execution
  // history exists; the signal-mean proxy only as a fallback.
  const monthlyPnl = useMemo(() => monthlyReturnsGrid(rows), [rows])
  const monthlyProxy = useMemo(() => monthlyConvictionGrid(signals), [signals])
  const isPnl = monthlyPnl.years.length > 0
  const monthly = isPnl ? monthlyPnl : monthlyProxy
  if (returnsQuery.isLoading) {
    return <div className="skeleton h-[240px] w-full" />
  }
  if (monthly.years.length === 0) {
    return <EmptyState title="Not enough trade history" description="Not enough signals yet to build a monthly grid." />
  }
  return (
    <Panel className="p-4">
      <Heatmap
        xLabels={monthly.months}
        yLabels={monthly.years}
        values={monthly.grid}
        mode="diverging"
        min={-monthly.maxAbs}
        max={monthly.maxAbs}
        height={Math.max(180, monthly.years.length * 70 + 90)}
        valueFormat={(v) => (isPnl ? fmtMoney(String(v)) : formatSignalStrength(v))}
      />
    </Panel>
  )
}

function TradeAnalysisTab({ signals }: { signals: Signal[] }) {
  const runs = useMemo(() => consecutiveRuns(signals), [signals])
  const split = useMemo(() => longShortSplit(signals.map((s) => Number.parseFloat(s.value))), [signals])

  return (
    <div className="space-y-6">
      <Section icon={<Sigma size={16} />} title="Trade P&L distribution" description="Distribution of realized trade outcomes by magnitude.">
        <Panel className="flex items-start gap-3 p-5">
          <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-warning-soft text-warning">
            <ShieldQuestion size={16} />
          </span>
          <div>
            <div className="flex items-center gap-2 text-sm font-medium text-fg">
              — <Badge variant="warning">requires per-trade data</Badge>
            </div>
            <p className="mt-1 text-xs leading-relaxed text-fg-muted">
              Backtest runs store aggregate results only (order counts, realized/unrealized P&L totals) — there is no
              per-trade fill record to bucket into a distribution. Shown honestly rather than approximated.
            </p>
          </div>
        </Panel>
      </Section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Section title="Consecutive signal direction" description="Streaks of same-direction signals, time-ordered.">
          <Panel className="p-4">
            <ConsecutiveRunsChart runs={runs} height={220} />
          </Panel>
        </Section>

        <Section title="Long vs short split" description="Signal direction split — not a fill/trade split (no per-trade data exists).">
          <Panel className="p-4">
            <LongShortDonut longCount={split.long} shortCount={split.short} flatCount={split.flat} height={240} />
          </Panel>
        </Section>
      </div>
    </div>
  )
}

export function BacktestAnalyticsTabs({ backtest, signals, strategyId }: { backtest: Backtest | null; signals: Signal[]; strategyId: string }) {
  return (
    <Section icon={<LayoutGrid size={16} />} title="Backtest analytics" description="This strategy's real backtest performance, browsable in place.">
      <Tabs
        items={[
          { value: 'overview', label: 'Overview', content: <OverviewTab backtest={backtest} /> },
          { value: 'monthly', label: 'Monthly Returns', content: <MonthlyReturnsTab signals={signals} strategyId={strategyId} /> },
          { value: 'trades', label: 'Trade Analysis', content: <TradeAnalysisTab signals={signals} /> },
        ]}
      />
    </Section>
  )
}
