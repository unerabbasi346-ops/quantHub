// Governing specification: handbook/ui/visual_engineering/13_VISUAL_DNA —
//   Image 2 (Finor) hero: large equity chart + circular profit gauge + dense
//   stat quartet. Doc 00 §14.5/§14.7 DATA HONESTY.
//
// EQUITY CHART SOURCE (flagged deviation from the literal brief): the brief
// asks for "cumulative P&L from backtest fill data", but backtests only
// persist AGGREGATE results (orders_created/filled/rejected, realized/
// unrealized P&L totals, F-21) — there is no per-fill breakdown to cumulate.
// Reconstructing one from live core.executions' net_amount would plot
// CASH FLOW (cost basis for an open position reads as a huge "loss"), not
// P&L — a misleading chart, not an honest one. Reused the same pattern
// already approved on the Strategy detail page instead: the strategy's real
// signed-conviction signal curve as an "equity proxy" (ConvictionEquityChart),
// annotated with the real backtest total_return. Same honesty boundary,
// same component, just on this page too.
'use client'

import { LineChart as LineChartIcon, PieChart } from 'lucide-react'
import { Badge, Panel, Section } from '@/components/ui'
import { ConvictionEquityChart } from '@/features/strategies/components/charts'
import { RealMetricTile } from '@/features/strategies/components/metric-tiles'
import { fmtMoney, fmtReturnPct } from '@/features/strategies/components/tables'
import type { Backtest } from '@/features/strategies/types'
import { formatCount } from '@/lib/utils/format'
import { ReturnGauge } from './charts'

export function HeroRow({
  points,
  latestBacktest,
}: {
  points: { label: string; value: number }[]
  latestBacktest: Backtest | null
}) {
  const results = latestBacktest?.results ?? null
  const retNum = latestBacktest?.total_return != null ? Number.parseFloat(latestBacktest.total_return) * 100 : null

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[3fr_2fr]">
      <Section
        icon={<LineChartIcon size={16} />}
        title="Portfolio equity"
        description="Signed conviction over time — an honest equity proxy (per-step P&L isn't tracked yet), not a real cash P&L curve."
      >
        <Panel className="p-4">
          <ConvictionEquityChart points={points} height={340} />
          {latestBacktest?.total_return != null && (
            <div className="mt-3 flex justify-end">
              <Badge variant={retNum != null && retNum >= 0 ? 'profit' : 'risk'}>
                Latest backtest return · {fmtReturnPct(latestBacktest.total_return)}
              </Badge>
            </div>
          )}
        </Panel>
      </Section>

      <Section icon={<PieChart size={16} />} title="Performance" description="Real backtest return and results — nothing fabricated.">
        <Panel className="space-y-4 p-4">
          <ReturnGauge returnPct={retNum} height={200} />
          <div className="grid grid-cols-2 gap-3">
            <RealMetricTile
              label="Trade count"
              value={latestBacktest?.trade_count ?? results?.trade_count ? formatCount(latestBacktest?.trade_count ?? results?.trade_count ?? 0) : '—'}
            />
            <RealMetricTile
              label="Realized P&L"
              value={results ? fmtMoney(results.realized_pnl) : '—'}
              tone={results ? (Number.parseFloat(results.realized_pnl) >= 0 ? 'profit' : 'risk') : 'default'}
            />
            <RealMetricTile label="Final capital" value={fmtMoney(latestBacktest?.final_capital ?? null)} />
            <RealMetricTile
              label="Unrealized P&L"
              value={results ? fmtMoney(results.unrealized_pnl) : '—'}
              tone={results ? (Number.parseFloat(results.unrealized_pnl) >= 0 ? 'profit' : 'risk') : 'default'}
            />
          </div>
        </Panel>
      </Section>
    </div>
  )
}
