// Governing specification: handbook/ui Doc 01 — Apache ECharts is the single
//   FROZEN analytics engine. Doc 00 §14.5/§14.7 DATA HONESTY: every series
//   below is a deterministic transform of real position/OI/bar data.
'use client'

import { Chart } from '@/components/ui/Chart'
import { chartAxis, chartTooltip, type ChartTheme } from '@/components/ui/chart-theme'
import { EmptyState } from '@/components/ui/States'
import { formatCapital, formatOI } from '@/lib/utils/format'
import type { ConcentrationRow, DivergencePoint, LeverageRow } from '../analytics'
import type { OpenInterest } from '@/features/markets/types'

const fmtCompact = (v: number): string => formatCapital(v)

// ── Exposure gauge: gross exposure as % of configured capital, task-specific
//    color zones (green <50%, amber 50-80%, red >80%) — deliberately its own
//    bespoke option rather than reusing components/ui/Gauge's 3-zone default
//    (whose thresholds are 40/70/100, tuned for a different metric). ──
export function ExposureGauge({ utilizationPct, height = 220 }: { utilizationPct: number | null; height?: number }) {
  if (utilizationPct == null) {
    return (
      <div style={{ height }}>
        <EmptyState title="No capital configured" description="Exposure % needs a configured capital figure to divide against." />
      </div>
    )
  }
  const clamped = Math.min(utilizationPct, 120)

  return (
    <Chart
      height={height}
      ariaLabel={`Gross exposure ${utilizationPct.toFixed(1)}% of capital`}
      option={(theme: ChartTheme) => ({
        series: [
          {
            type: 'gauge',
            min: 0,
            max: 100,
            radius: '100%',
            center: ['50%', '62%'],
            startAngle: 210,
            endAngle: -30,
            progress: { show: true, width: 14, itemStyle: { color: theme.fg } },
            pointer: { show: false },
            axisLine: {
              lineStyle: {
                width: 14,
                color: [
                  [0.5, theme.profit],
                  [0.8, theme.warning],
                  [1, theme.risk],
                ],
              },
            },
            axisTick: { show: false },
            splitLine: { distance: -20, length: 10, lineStyle: { color: theme.alpha('fg', 0.25), width: 1.5 } },
            axisLabel: { distance: -28, color: theme.fgSubtle, fontFamily: theme.fontMono, fontSize: 9 },
            detail: {
              valueAnimation: true,
              offsetCenter: [0, '18%'],
              formatter: () => `${utilizationPct.toFixed(1)}%`,
              color: utilizationPct > 80 ? theme.risk : utilizationPct >= 50 ? theme.warning : theme.profit,
              fontFamily: theme.fontMono,
              fontWeight: 700,
              fontSize: 24,
            },
            data: [{ value: clamped }],
          },
        ],
      })}
    />
  )
}

// ── Concentration risk: horizontal bar, highest concentration at top,
//    gradient green (small) -> red (large) per bar. ──
export function ConcentrationChart({ rows, height = 260 }: { rows: ConcentrationRow[]; height?: number }) {
  if (rows.length === 0) {
    return (
      <div style={{ height }}>
        <EmptyState title="No open positions" description="Concentration appears once this portfolio holds open positions." />
      </div>
    )
  }

  return (
    <Chart
      height={height}
      ariaLabel="Position concentration risk"
      option={(theme: ChartTheme) => {
        const axis = chartAxis(theme)
        return {
          tooltip: chartTooltip(theme, {
            trigger: 'item',
            formatter: (p: unknown) => {
              const d = p as { dataIndex: number }
              const r = rows[d.dataIndex]
              return `${r.symbol}<br/><b>${r.pctOfPortfolio.toFixed(1)}%</b> of portfolio · ${fmtCompact(r.value)}`
            },
          }),
          grid: { left: 78, right: 40, top: 8, bottom: 8 },
          xAxis: { type: 'value', ...axis, axisLabel: { ...axis.axisLabel, formatter: (v: number) => `${v}%` } },
          yAxis: { type: 'category', data: rows.map((r) => r.symbol.split('/')[0]), inverse: true, ...axis, splitLine: { show: false } },
          series: [
            {
              type: 'bar',
              data: rows.map((r) => {
                // Linear interpolate profit -> warning -> risk by concentration %.
                const t = Math.min(r.pctOfPortfolio / 50, 1) // saturate red at 50%+ concentration
                const color = t < 0.5 ? theme.profit : t < 0.8 ? theme.warning : theme.risk
                return { value: r.pctOfPortfolio, itemStyle: { color, borderRadius: [0, 3, 3, 0] } }
              }),
              barMaxWidth: 20,
              label: {
                show: true,
                position: 'right',
                color: theme.fgMuted,
                fontFamily: theme.fontMono,
                fontSize: 10,
                formatter: (p: unknown) => `${(p as { value: number }).value.toFixed(1)}%`,
              },
            },
          ],
        }
      }}
    />
  )
}

// ── Leverage utilization: bar per open position; `maxLeverage` (from a real
//    risk limit, if one is configured for this metric) draws a threshold
//    markLine — omitted entirely when no such limit exists (never a
//    fabricated threshold). ──
export function LeverageUtilizationChart({
  rows,
  maxLeverage,
  height = 260,
}: {
  rows: LeverageRow[]
  maxLeverage: number | null
  height?: number
}) {
  if (rows.length === 0) {
    return (
      <div style={{ height }}>
        <EmptyState title="No open positions" description="Leverage appears once this portfolio holds open positions." />
      </div>
    )
  }

  return (
    <Chart
      height={height}
      ariaLabel="Leverage utilization per position"
      option={(theme: ChartTheme) => {
        const axis = chartAxis(theme)
        return {
          tooltip: chartTooltip(theme, {
            trigger: 'item',
            formatter: (p: unknown) => {
              const d = p as { dataIndex: number }
              const r = rows[d.dataIndex]
              return `${r.symbol}<br/><b>${r.leverage.toFixed(1)}x</b>`
            },
          }),
          grid: { left: 56, right: 16, top: 16, bottom: 28 },
          xAxis: { type: 'category', data: rows.map((r) => r.symbol.split('/')[0]), ...axis, splitLine: { show: false } },
          yAxis: { type: 'value', ...axis, axisLabel: { ...axis.axisLabel, formatter: (v: number) => `${v}x` } },
          series: [
            {
              type: 'bar',
              data: rows.map((r) => ({
                value: r.leverage,
                itemStyle: { color: r.leverage > 1 ? theme.accent : theme.alpha('fg', 0.3), borderRadius: [3, 3, 0, 0] },
              })),
              barMaxWidth: 32,
              markLine: maxLeverage
                ? {
                    silent: true,
                    symbol: 'none',
                    lineStyle: { color: theme.risk, type: 'dashed', width: 1.5 },
                    label: { formatter: `max ${maxLeverage}x`, color: theme.risk, fontFamily: theme.fontMono, fontSize: 10 },
                    data: [{ yAxis: maxLeverage }],
                  }
                : undefined,
            },
          ],
        }
      }}
    />
  )
}

// ── Open interest vs price: dual-axis area (OI) + line (price), with
//    divergence markers (bullish/bearish confirmation per computeOiDivergence). ──
export function OpenInterestPriceChart({
  oiRows,
  priceSeries,
  divergence,
  height = 360,
}: {
  oiRows: OpenInterest[]
  priceSeries: { ts: string; close: number }[]
  divergence: DivergencePoint[]
  height?: number
}) {
  if (oiRows.length < 2) {
    return (
      <div style={{ height }}>
        <EmptyState title="Not enough OI history" description="At least two open-interest observations are needed to plot a trend." />
      </div>
    )
  }

  return (
    <Chart
      height={height}
      ariaLabel="Open interest vs price"
      option={(theme: ChartTheme) => {
        const axis = chartAxis(theme)
        const divergenceByTs = new Map(divergence.map((d) => [d.ts, d]))
        return {
          tooltip: chartTooltip(theme, {
            trigger: 'axis',
            formatter: (params: unknown) => {
              const arr = params as { seriesName: string; value: [number, number]; axisValueLabel: string }[]
              const lines = arr.map((p) => {
                if (p.seriesName === 'Open interest') return `OI: <b>${formatOI(p.value[1])}</b>`
                return `Price: <b>${p.value[1].toLocaleString(undefined, { maximumFractionDigits: 2 })}</b>`
              })
              return `${arr[0]?.axisValueLabel}<br/>${lines.join('<br/>')}`
            },
          }),
          legend: {
            top: 8,
            right: 8,
            icon: 'circle',
            itemWidth: 8,
            itemHeight: 8,
            backgroundColor: theme.alpha('surface', 0.5),
            borderRadius: 6,
            padding: [4, 8],
            textStyle: { color: theme.fgMuted, fontFamily: theme.fontMono, fontSize: 11 },
            data: ['Open interest', 'Price'],
          },
          grid: { left: 64, right: 64, top: 44, bottom: 28 },
          xAxis: { type: 'time', ...axis, splitLine: { show: false } },
          yAxis: [
            {
              type: 'value',
              name: 'OI (USDT)',
              nameTextStyle: { color: theme.fgSubtle, fontSize: 10 },
              ...axis,
              axisLabel: { ...axis.axisLabel, formatter: (v: number) => formatOI(v) },
            },
            {
              type: 'value',
              name: 'Price',
              nameTextStyle: { color: theme.fgSubtle, fontSize: 10 },
              scale: true,
              ...axis,
              splitLine: { show: false },
            },
          ],
          series: [
            {
              name: 'Open interest',
              type: 'line',
              yAxisIndex: 0,
              data: oiRows.map((r) => [new Date(r.ts).getTime(), Number.parseFloat(r.open_interest_usdt)]),
              symbol: 'none',
              lineStyle: { color: theme.accent, width: 2 },
              areaStyle: {
                color: {
                  type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                  colorStops: [
                    { offset: 0, color: theme.alpha('accent', 0.28) },
                    { offset: 1, color: theme.alpha('accent', 0.02) },
                  ],
                },
              },
              markPoint: {
                symbol: 'circle',
                symbolSize: 8,
                data: oiRows
                  .filter((r) => divergenceByTs.has(r.ts))
                  .map((r) => {
                    const d = divergenceByTs.get(r.ts)!
                    return {
                      name: d.signal,
                      coord: [new Date(r.ts).getTime(), Number.parseFloat(r.open_interest_usdt)],
                      itemStyle: { color: d.signal === 'bullish' ? theme.profit : theme.risk },
                    }
                  }),
              },
            },
            {
              name: 'Price',
              type: 'line',
              yAxisIndex: 1,
              data: priceSeries.map((p) => [new Date(p.ts).getTime(), p.close]),
              symbol: 'none',
              lineStyle: { color: theme.fgMuted, width: 1.5, type: 'dashed' },
            },
          ],
        }
      }}
    />
  )
}
