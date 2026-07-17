// Governing specification: handbook/ui Doc 01 — Apache ECharts is the single
//   FROZEN analytics engine; every chart here builds an option through the
//   shared `Chart` wrapper + `chart-theme` tokens. Doc 00 §14.5/§14.7 DATA
//   HONESTY: every series below is a deterministic transform of real backend
//   data; nothing here is fabricated.
//
// Bespoke, page-specific compositions for the Portfolio workspace. Kept
// feature-local (not promoted to components/ui) the same way strategies/
// components/charts.tsx and markets/components/charts.tsx compose the
// generic Chart/chart-theme primitives for their own page's exact shape.
'use client'

import { Chart } from '@/components/ui/Chart'
import type { ChartTheme } from '@/components/ui/chart-theme'
import { EmptyState } from '@/components/ui/States'
import { formatBacktestReturn } from '@/lib/utils/format'

// ── Return gauge: a single real backtest total_return %, semi-circle gauge,
//    colored profit/risk by sign — "like Image 2's Total Profits circular
//    gauge" but two-tone (not the multi-zone health-style Gauge.tsx), since a
//    return figure is simply good (>=0) or bad (<0), not a graduated risk
//    scale. Range is symmetric around the value's own magnitude so the
//    needle never pins at an arbitrary fixed scale. ──
export function ReturnGauge({
  returnPct,
  height = 220,
}: {
  returnPct: number | null
  height?: number
}) {
  if (returnPct == null) {
    return (
      <div style={{ height }}>
        <EmptyState title="No backtest yet" description="Return appears once this strategy has a completed backtest run." />
      </div>
    )
  }

  const magnitude = Math.max(Math.abs(returnPct) * 1.4, 1)

  return (
    <Chart
      height={height}
      ariaLabel={`Backtest return ${formatBacktestReturn(returnPct / 100)}`}
      option={(theme: ChartTheme) => {
        const color = returnPct >= 0 ? theme.profit : theme.risk
        return {
          series: [
            {
              type: 'gauge',
              min: -magnitude,
              max: magnitude,
              radius: '100%',
              center: ['50%', '62%'],
              startAngle: 210,
              endAngle: -30,
              progress: {
                show: true,
                width: 14,
                itemStyle: { color },
              },
              pointer: { show: false },
              axisLine: { lineStyle: { width: 14, color: [[1, theme.alpha('fg', 0.08)]] } },
              axisTick: { show: false },
              splitLine: {
                distance: -20,
                length: 10,
                lineStyle: { color: theme.alpha('fg', 0.2), width: 1.5 },
              },
              axisLabel: { show: false },
              title: { show: false },
              detail: {
                valueAnimation: true,
                offsetCenter: [0, '10%'],
                // Small real returns (e.g. -0.0028%) round to a misleading
                // "-0.00%" at 2dp — scale precision to the magnitude so a
                // genuinely tiny figure still reads as nonzero.
                formatter: () => formatBacktestReturn(returnPct / 100),
                color,
                fontFamily: theme.fontMono,
                fontWeight: 700,
                fontSize: 26,
              },
              data: [{ value: returnPct }],
            },
          ],
        }
      }}
    />
  )
}

// ── Long vs Short signal split: a donut of how many recorded signals leaned
//    LONG vs SHORT vs FLAT — real, from the strategy's own signal signs. NOT
//    a fill/trade-direction split (no per-trade fill data exists at the
//    backtest level, F-21) — labeled accordingly by the caller. ──
export function LongShortDonut({
  longCount,
  shortCount,
  flatCount,
  height = 240,
}: {
  longCount: number
  shortCount: number
  flatCount: number
  height?: number
}) {
  const total = longCount + shortCount + flatCount
  if (total === 0) {
    return (
      <div style={{ height }}>
        <EmptyState title="No signals" description="This strategy has emitted no signals yet." />
      </div>
    )
  }

  const slices = [
    { name: 'Long', value: longCount, tone: 'profit' as const },
    { name: 'Short', value: shortCount, tone: 'risk' as const },
    ...(flatCount > 0 ? [{ name: 'Flat', value: flatCount, tone: 'info' as const }] : []),
  ]

  return (
    <Chart
      height={height}
      ariaLabel="Long vs short signal split"
      option={(theme: ChartTheme) => {
        const toneColor = { profit: theme.profit, risk: theme.risk, info: theme.info }
        return {
          tooltip: {
            trigger: 'item',
            backgroundColor: theme.alpha('surfaceRaised', 0.72),
            borderColor: theme.alpha('border', 0.5),
            textStyle: { color: theme.fg, fontFamily: theme.fontMono, fontSize: 12 },
            extraCssText: 'border-radius:12px;backdrop-filter:blur(12px);',
            formatter: (p: unknown) => {
              const d = p as { name: string; value: number; percent: number }
              return `${d.name}<br/><b>${d.value}</b> · ${d.percent.toFixed(1)}%`
            },
          },
          legend: {
            bottom: 0,
            icon: 'circle',
            itemWidth: 8,
            itemHeight: 8,
            textStyle: { color: theme.fgMuted, fontFamily: theme.fontMono, fontSize: 11 },
          },
          series: [
            {
              type: 'pie',
              radius: ['52%', '78%'],
              center: ['50%', '44%'],
              avoidLabelOverlap: true,
              itemStyle: { borderColor: theme.surfaceRaised, borderWidth: 2, borderRadius: 3 },
              label: { show: false },
              data: slices.map((s) => ({ name: s.name, value: s.value, itemStyle: { color: toneColor[s.tone] } })),
            },
          ],
        }
      }}
    />
  )
}
