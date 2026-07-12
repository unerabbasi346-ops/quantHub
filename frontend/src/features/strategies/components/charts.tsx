// Governing specification: handbook/ui Doc 01 — Apache ECharts is the single
//   FROZEN analytics engine; every chart here builds an option through the
//   shared `Chart` wrapper + `chart-theme` tokens (Doc 04/13_VISUAL_DNA
//   "Every chart must appear custom engineered. Default chart appearances are
//   prohibited."). Doc 00 §14.5/§14.7 — DATA HONESTY: every series below is a
//   deterministic transform of real signals; nothing here is fabricated.
//
// Bespoke, page-specific compositions for the Strategy detail workspace
// (equity/conviction split-area, signal timeline scatter, consecutive-run
// bars). Kept feature-local rather than promoted to components/ui because
// they compose the generic primitives (Chart, chart-theme) for one page's
// exact shape, following the same pattern as markets/CorrelationMatrix
// building on the generic Heatmap.
'use client'

import { Chart } from '@/components/ui/Chart'
import { chartAxis, chartTooltip, type ChartTheme } from '@/components/ui/chart-theme'
import { EmptyState } from '@/components/ui/States'
import type { ConsecutiveRun, SignalPoint } from '../analytics'

const fmtTime = (ts: string) =>
  new Date(ts).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })

// ── Equity/conviction split-area: signed signal values over time, shaded
//    profit-green above zero and risk-red below — an honest "equity proxy"
//    (Doc 00: real per-step equity tracking doesn't exist yet, F-21), never
//    presented as a real P&L curve. ──
export function ConvictionEquityChart({
  points,
  height = 320,
}: {
  points: { label: string; value: number }[]
  height?: number
}) {
  if (points.length < 2) {
    return (
      <div style={{ height }}>
        <EmptyState title="Not enough signals" description="At least two signals are needed to plot the curve." />
      </div>
    )
  }

  const values = points.map((p) => p.value)
  const posData = values.map((v) => (v >= 0 ? v : 0))
  const negData = values.map((v) => (v < 0 ? v : 0))
  const dataMax = Math.max(...values, 0)
  const dataMin = Math.min(...values, 0)

  return (
    <Chart
      height={height}
      ariaLabel="Conviction equity curve with drawdown shading"
      option={(theme: ChartTheme) => {
        const axis = chartAxis(theme)
        return {
          tooltip: chartTooltip(theme, {
            trigger: 'axis',
            axisPointer: { type: 'line', lineStyle: { color: theme.alpha('fg', 0.25), width: 1 } },
            formatter: (params: unknown) => {
              const arr = params as { axisValue: string }[]
              const idx = points.findIndex((p) => p.label === arr[0]?.axisValue)
              const v = idx >= 0 ? values[idx] : 0
              return `${arr[0]?.axisValue}<br/><b style="color:${v >= 0 ? theme.profit : theme.risk}">${v >= 0 ? '+' : ''}${v.toFixed(4)}</b>`
            },
          }),
          grid: { left: 56, right: 16, top: 20, bottom: 28 },
          xAxis: {
            type: 'category',
            data: points.map((p) => p.label),
            boundaryGap: false,
            ...axis,
            splitLine: { show: false },
          },
          yAxis: {
            type: 'value',
            min: Math.min(dataMin * 1.1, -0.001),
            max: Math.max(dataMax * 1.1, 0.001),
            ...axis,
          },
          series: [
            {
              name: 'Conviction',
              type: 'line',
              data: values,
              symbol: 'none',
              lineStyle: { color: theme.fg, width: 1.5 },
              areaStyle: undefined,
              z: 3,
              markLine: {
                silent: true,
                symbol: 'none',
                lineStyle: { color: theme.borderStrong, type: 'dashed', width: 1 },
                data: [{ yAxis: 0 }],
                label: { show: false },
              },
            },
            {
              name: 'Above zero',
              type: 'line',
              data: posData,
              symbol: 'none',
              lineStyle: { opacity: 0 },
              z: 1,
              areaStyle: {
                color: {
                  type: 'linear',
                  x: 0, y: 0, x2: 0, y2: 1,
                  colorStops: [
                    { offset: 0, color: theme.alpha('profit', 0.32) },
                    { offset: 1, color: theme.alpha('profit', 0.02) },
                  ],
                },
              },
            },
            {
              name: 'Below zero',
              type: 'line',
              data: negData,
              symbol: 'none',
              lineStyle: { opacity: 0 },
              z: 1,
              areaStyle: {
                color: {
                  type: 'linear',
                  x: 0, y: 0, x2: 0, y2: 1,
                  colorStops: [
                    { offset: 0, color: theme.alpha('risk', 0.05) },
                    { offset: 1, color: theme.alpha('risk', 0.34) },
                  ],
                },
              },
            },
          ],
        }
      }}
    />
  )
}

// ── Signal timeline scatter: every recorded signal, x=time, y=conviction,
//    color by sign, size by magnitude — Section 4's "Signal Intelligence". ──
export function SignalTimelineScatter({ points, height = 260 }: { points: SignalPoint[]; height?: number }) {
  if (points.length === 0) {
    return (
      <div style={{ height }}>
        <EmptyState title="No signals" description="This strategy has emitted no signals yet." />
      </div>
    )
  }

  const maxAbs = Math.max(...points.map((p) => Math.abs(p.value)), 1e-9)

  return (
    <Chart
      height={height}
      ariaLabel="Signal timeline scatter"
      option={(theme: ChartTheme) => {
        const axis = chartAxis(theme)
        return {
          tooltip: chartTooltip(theme, {
            trigger: 'item',
            formatter: (p: unknown) => {
              const d = p as { data: [number, number] }
              const v = d.data[1]
              return `${fmtTime(new Date(d.data[0]).toISOString())}<br/><b style="color:${v >= 0 ? theme.profit : theme.risk}">${v >= 0 ? '+' : ''}${v.toFixed(4)}</b>`
            },
          }),
          grid: { left: 56, right: 16, top: 20, bottom: 28 },
          xAxis: { type: 'time', ...axis, splitLine: { show: false } },
          yAxis: { type: 'value', scale: true, ...axis },
          series: [
            {
              type: 'scatter',
              data: points.map((p) => [new Date(p.ts).getTime(), p.value]),
              symbolSize: (val: number[]) => 4 + (Math.abs(val[1]) / maxAbs) * 14,
              itemStyle: {
                color: (params: unknown) => {
                  const v = (params as { data: [number, number] }).data[1]
                  return v >= 0 ? theme.alpha('profit', 0.75) : theme.alpha('risk', 0.75)
                },
              },
            },
          ],
        }
      }}
    />
  )
}

// ── Consecutive signal direction: bar per run, height = run length, sign
//    keeps the strategy's "streakiness" honest and purely sign-derived. ──
export function ConsecutiveRunsChart({ runs, height = 220 }: { runs: ConsecutiveRun[]; height?: number }) {
  if (runs.length === 0) {
    return (
      <div style={{ height }}>
        <EmptyState title="No signals" description="This strategy has emitted no signals yet." />
      </div>
    )
  }

  return (
    <Chart
      height={height}
      ariaLabel="Consecutive signal direction runs"
      option={(theme: ChartTheme) => {
        const axis = chartAxis(theme)
        return {
          tooltip: chartTooltip(theme, {
            trigger: 'item',
            formatter: (p: unknown) => {
              const d = p as { dataIndex: number }
              const r = runs[d.dataIndex]
              return `${r.sign > 0 ? 'Positive' : 'Negative'} run · <b>${r.length}</b> signal${r.length === 1 ? '' : 's'}<br/>from ${fmtTime(r.startTs)}`
            },
          }),
          grid: { left: 44, right: 16, top: 16, bottom: 24 },
          xAxis: {
            type: 'category',
            data: runs.map((_, i) => String(i + 1)),
            ...axis,
            axisLabel: { ...axis.axisLabel, interval: Math.max(0, Math.floor(runs.length / 12)) },
            splitLine: { show: false },
          },
          yAxis: { type: 'value', minInterval: 1, ...axis },
          series: [
            {
              type: 'bar',
              data: runs.map((r) => ({
                value: r.sign * r.length,
                itemStyle: { color: r.sign > 0 ? theme.profit : theme.risk, borderRadius: r.sign > 0 ? [2, 2, 0, 0] : [0, 0, 2, 2] },
              })),
              barCategoryGap: '18%',
            },
          ],
        }
      }}
    />
  )
}
