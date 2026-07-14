// Governing specification: Doc 14 §10.3 Backtesting; Doc 00 §14.5/§14.7 DATA
//   HONESTY. Section 4 — tabbed backtest analytics (Overview / Monthly
//   Returns / Trade Analysis), reusing the same honest derivations and
//   components already established on the Strategy detail page — this is
//   the same strategy's real data, viewed from the Portfolio workspace.
'use client'

import { useMemo } from 'react'
import { BarChart3, CalendarRange, LayoutGrid, ShieldQuestion, Sigma } from 'lucide-react'
import { Badge, EmptyState, Heatmap, Panel, Section, Tabs } from '@/components/ui'
import { consecutiveRuns, monthlyConvictionGrid } from '@/features/strategies/analytics'
import { ConsecutiveRunsChart } from '@/features/strategies/components/charts'
import { PendingMetricTile, RealMetricTile } from '@/features/strategies/components/metric-tiles'
import type { Backtest, Signal } from '@/features/strategies/types'
import { longShortSplit } from '../analytics'
import { LongShortDonut } from './charts'

const fmtReturnPct = (v: string | null) => (v === null ? '—' : `${(Number.parseFloat(v) * 100).toFixed(4)}%`)
const fmtMoney = (v: string | null) =>
  v === null ? '—' : Number.parseFloat(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })

function OverviewTab({ backtest }: { backtest: Backtest | null }) {
  const results = backtest?.results ?? null
  const retNum = backtest?.total_return != null ? Number.parseFloat(backtest.total_return) : null
  const tradeCount = backtest?.trade_count ?? results?.trade_count ?? null
  const realizedNum = results ? Number.parseFloat(results.realized_pnl) : null
  const avgTradePnl = realizedNum != null && tradeCount ? realizedNum / tradeCount : null

  if (!backtest) {
    return <EmptyState title="No backtest runs" description="This strategy has no backtest yet — metrics appear once one completes." />
  }

  return (
    <Panel className="grid grid-cols-2 gap-3 p-4 sm:grid-cols-3 lg:grid-cols-4">
      <RealMetricTile label="Total return" value={fmtReturnPct(backtest.total_return)} tone={retNum == null ? 'default' : retNum >= 0 ? 'profit' : 'risk'} />
      <RealMetricTile label="Trade count" value={tradeCount ?? '—'} />
      <RealMetricTile label="Realized P&L" value={results ? fmtMoney(results.realized_pnl) : '—'} tone={realizedNum == null ? 'default' : realizedNum >= 0 ? 'profit' : 'risk'} />
      <RealMetricTile label="Final capital" value={fmtMoney(backtest.final_capital)} />
      <RealMetricTile
        label="Avg trade P&L"
        value={avgTradePnl != null ? fmtMoney(String(avgTradePnl)) : '—'}
        tone={avgTradePnl == null ? 'default' : avgTradePnl >= 0 ? 'profit' : 'risk'}
        hint="realized ÷ trade count"
      />
      <PendingMetricTile label="Best trade" ticket="F-21" shell="number" />
      <PendingMetricTile label="Worst trade" ticket="F-21" shell="number" />
      <PendingMetricTile label="Win rate" ticket="F-21" shell="ring" />
      <PendingMetricTile label="Sharpe ratio" ticket="F-21" shell="number" />
      <PendingMetricTile label="Max drawdown" ticket="F-21" shell="bar" />
    </Panel>
  )
}

function MonthlyReturnsTab({ signals }: { signals: Signal[] }) {
  const monthly = useMemo(() => monthlyConvictionGrid(signals), [signals])
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
        valueFormat={(v) => `${v >= 0 ? '+' : ''}${v.toFixed(3)}`}
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
              Not computed <Badge variant="warning">requires per-trade data</Badge>
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

        <Section title="Long vs short split" description="Signal direction split — not a fill/trade split (no per-trade data exists, F-21).">
          <Panel className="p-4">
            <LongShortDonut longCount={split.long} shortCount={split.short} flatCount={split.flat} height={240} />
          </Panel>
        </Section>
      </div>
    </div>
  )
}

export function BacktestAnalyticsTabs({ backtest, signals }: { backtest: Backtest | null; signals: Signal[] }) {
  return (
    <Section icon={<LayoutGrid size={16} />} title="Backtest analytics" description="This strategy's real backtest performance, browsable in place.">
      <Tabs
        items={[
          { value: 'overview', label: 'Overview', content: <OverviewTab backtest={backtest} /> },
          { value: 'monthly', label: 'Monthly Returns', content: <MonthlyReturnsTab signals={signals} /> },
          { value: 'trades', label: 'Trade Analysis', content: <TradeAnalysisTab signals={signals} /> },
        ]}
      />
    </Section>
  )
}
