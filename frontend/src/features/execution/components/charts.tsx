// Governing specification: handbook/ui Doc 01 — Apache ECharts is the single
//   FROZEN analytics engine. Doc 00 §14.5/§14.7 DATA HONESTY: every series
//   below is a deterministic transform of real order/execution/signal data.
'use client'

import { useMemo } from 'react'
import { Chart } from '@/components/ui/Chart'
import { chartAxis, chartTooltip, type ChartTheme } from '@/components/ui/chart-theme'
import { EmptyState } from '@/components/ui/States'
import { formatCapital } from '@/lib/utils/format'
import type { CumulativePnlPoint, FunnelStage, HourBucket, StrategyPnlRow } from '../analytics'

const fmtUsdt = (v: number): string => formatCapital(v)

// ── Fill size distribution — histogram over real fill notionals (USDT). ──
export function FillSizeHistogram({ notionals, height = 220 }: { notionals: number[]; height?: number }) {
  const buckets = 10
  const bins = useMemo(() => {
    if (notionals.length < 2) return []
    // Not Math.min(...notionals)/Math.max(...notionals) — spreading 100k+
    // fills into a function call blows the JS call stack (RangeError).
    const min = notionals.reduce((a, b) => Math.min(a, b), Infinity)
    const max = notionals.reduce((a, b) => Math.max(a, b), -Infinity)
    const span = max - min || 1
    const w = span / buckets
    const out = Array.from({ length: buckets }, (_, i) => ({ from: min + i * w, to: min + (i + 1) * w, count: 0 }))
    for (const v of notionals) {
      const idx = Math.min(buckets - 1, Math.floor((v - min) / w))
      out[idx].count++
    }
    return out
  }, [notionals])

  if (bins.length === 0) {
    return (
      <div style={{ height }}>
        <EmptyState title="Not enough fills" description="At least two fills are needed to plot a size distribution." />
      </div>
    )
  }

  return (
    <Chart
      height={height}
      ariaLabel="Fill size distribution"
      option={(theme: ChartTheme) => {
        const axis = chartAxis(theme)
        return {
          tooltip: chartTooltip(theme, {
            trigger: 'item',
            formatter: (p: unknown) => {
              const b = bins[(p as { dataIndex: number }).dataIndex]
              return `<b>${b.count}</b> ${b.count === 1 ? 'fill' : 'fills'}<br/>${fmtUsdt(b.from)} … ${fmtUsdt(b.to)}`
            },
          }),
          grid: { left: 40, right: 14, top: 12, bottom: 28 },
          xAxis: {
            type: 'category',
            data: bins.map((b) => fmtUsdt((b.from + b.to) / 2)),
            ...axis,
            axisLabel: { ...axis.axisLabel, interval: 1, rotate: 30 },
            splitLine: { show: false },
          },
          yAxis: { type: 'value', minInterval: 1, ...axis },
          series: [
            {
              type: 'bar',
              data: bins.map((b) => ({ value: b.count, itemStyle: { color: theme.accent, borderRadius: [2, 2, 0, 0] } })),
              barCategoryGap: '12%',
            },
          ],
        }
      }}
    />
  )
}

// ── Orders by hour (UTC) — current hour highlighted violet. ──
export function OrdersByHourChart({ buckets, height = 220 }: { buckets: HourBucket[]; height?: number }) {
  const hasData = buckets.some((b) => b.count > 0)
  if (!hasData) {
    return (
      <div style={{ height }}>
        <EmptyState title="No orders yet" description="Order activity by hour appears once orders exist." />
      </div>
    )
  }
  const currentUtcHour = new Date().getUTCHours()

  return (
    <Chart
      height={height}
      ariaLabel="Order activity by hour"
      option={(theme: ChartTheme) => {
        const axis = chartAxis(theme)
        return {
          tooltip: chartTooltip(theme, {
            trigger: 'item',
            formatter: (p: unknown) => {
              const b = buckets[(p as { dataIndex: number }).dataIndex]
              return `${String(b.hour).padStart(2, '0')}:00 UTC<br/><b>${b.count}</b> ${b.count === 1 ? 'order' : 'orders'}`
            },
          }),
          grid: { left: 32, right: 14, top: 12, bottom: 24 },
          xAxis: {
            type: 'category',
            data: buckets.map((b) => String(b.hour).padStart(2, '0')),
            ...axis,
            axisLabel: { ...axis.axisLabel, interval: 1 },
            splitLine: { show: false },
          },
          yAxis: { type: 'value', minInterval: 1, ...axis },
          series: [
            {
              type: 'bar',
              data: buckets.map((b) => ({
                value: b.count,
                itemStyle: {
                  color: b.hour === currentUtcHour ? theme.accent : theme.alpha('fg', 0.28),
                  borderRadius: [2, 2, 0, 0],
                },
              })),
              barCategoryGap: '18%',
            },
          ],
        }
      }}
    />
  )
}

// ── Signal -> execution funnel, with drop-off % labeled between stages. ──
export function SignalExecutionFunnel({ stages, height = 220 }: { stages: FunnelStage[]; height?: number }) {
  if (stages.every((s) => s.value === 0)) {
    return (
      <div style={{ height }}>
        <EmptyState title="No signals yet" description="The signal-to-execution funnel appears once this strategy has emitted signals." />
      </div>
    )
  }

  return (
    <Chart
      height={height}
      ariaLabel="Signal to execution flow"
      option={(theme: ChartTheme) => {
        const axis = chartAxis(theme)
        return {
          tooltip: chartTooltip(theme, {
            trigger: 'item',
            formatter: (p: unknown) => {
              const s = stages[(p as { dataIndex: number }).dataIndex]
              return `${s.label}<br/><b>${s.value}</b>`
            },
          }),
          grid: { left: 110, right: 40, top: 8, bottom: 8 },
          xAxis: { type: 'value', ...axis, splitLine: { show: false } },
          yAxis: { type: 'category', data: stages.map((s) => s.label), inverse: true, ...axis, splitLine: { show: false } },
          series: [
            {
              type: 'bar',
              data: stages.map((s, i) => {
                const prev = i > 0 ? stages[i - 1].value : s.value
                const dropPct = prev > 0 ? ((prev - s.value) / prev) * 100 : 0
                const t = i / Math.max(stages.length - 1, 1)
                return {
                  value: s.value,
                  itemStyle: { color: theme.accent, opacity: 1 - t * 0.35, borderRadius: [0, 3, 3, 0] },
                  label: {
                    show: i > 0,
                    formatter: () => (i > 0 && dropPct > 0 ? `-${dropPct.toFixed(0)}%` : ''),
                  },
                }
              }),
              barMaxWidth: 26,
              label: {
                show: true,
                position: 'right',
                color: theme.fgMuted,
                fontFamily: theme.fontMono,
                fontSize: 11,
                formatter: (p: unknown) => String((p as { value: number }).value),
              },
            },
          ],
        }
      }}
    />
  )
}

// ── Cumulative realized P&L over time — green above zero, red below. ──
export function CumulativePnlChart({ points, height = 260 }: { points: CumulativePnlPoint[]; height?: number }) {
  if (points.length === 0) {
    return (
      <div style={{ height }}>
        <EmptyState title="No fills yet" description="Cumulative P&L appears once this strategy has filled orders." />
      </div>
    )
  }

  return (
    <Chart
      height={height}
      ariaLabel="Cumulative realized P&L over time"
      option={(theme: ChartTheme) => {
        const axis = chartAxis(theme)
        const last = points[points.length - 1].cumulative
        const lineColor = last >= 0 ? theme.profit : theme.risk
        return {
          tooltip: chartTooltip(theme, {
            trigger: 'axis',
            formatter: (params: unknown) => {
              const arr = params as { value: [number, number]; axisValueLabel: string }[]
              const v = arr[0]?.value[1] ?? 0
              return `${arr[0]?.axisValueLabel}<br/>Cumulative: <b>${v >= 0 ? '+' : ''}${v.toFixed(2)}</b>`
            },
          }),
          grid: { left: 56, right: 16, top: 16, bottom: 28 },
          xAxis: { type: 'time', ...axis, splitLine: { show: false } },
          yAxis: { type: 'value', ...axis, axisLabel: { ...axis.axisLabel, formatter: (v: number) => fmtUsdt(v) } },
          series: [
            {
              type: 'line',
              data: points.map((p) => [new Date(p.ts).getTime(), p.cumulative]),
              symbol: 'none',
              lineStyle: { color: lineColor, width: 2 },
              areaStyle: {
                color: {
                  type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                  colorStops: [
                    { offset: 0, color: theme.alpha(last >= 0 ? 'profit' : 'risk', 0.28) },
                    { offset: 1, color: theme.alpha(last >= 0 ? 'profit' : 'risk', 0.02) },
                  ],
                },
              },
              markLine: {
                silent: true,
                symbol: 'none',
                lineStyle: { color: theme.alpha('fg', 0.3), type: 'dashed', width: 1 },
                data: [{ yAxis: 0 }],
              },
            },
          ],
        }
      }}
    />
  )
}

// ── Realized P&L by strategy — colored bars by sign. ──
export function PnlByStrategyChart({ rows, height = 220 }: { rows: StrategyPnlRow[]; height?: number }) {
  if (rows.length === 0) {
    return (
      <div style={{ height }}>
        <EmptyState title="No filled trades yet" description="P&L by strategy appears once fills exist for a strategy." />
      </div>
    )
  }

  return (
    <Chart
      height={height}
      ariaLabel="P&L by strategy"
      option={(theme: ChartTheme) => {
        const axis = chartAxis(theme)
        return {
          tooltip: chartTooltip(theme, {
            trigger: 'item',
            formatter: (p: unknown) => {
              const r = rows[(p as { dataIndex: number }).dataIndex]
              return `${r.strategyName}<br/><b>${r.pnl >= 0 ? '+' : ''}${r.pnl.toFixed(2)}</b>`
            },
          }),
          grid: { left: 56, right: 16, top: 16, bottom: 48 },
          xAxis: {
            type: 'category',
            data: rows.map((r) => r.strategyName),
            ...axis,
            axisLabel: { ...axis.axisLabel, rotate: rows.length > 3 ? 20 : 0 },
            splitLine: { show: false },
          },
          yAxis: { type: 'value', ...axis, axisLabel: { ...axis.axisLabel, formatter: (v: number) => fmtUsdt(v) } },
          series: [
            {
              type: 'bar',
              data: rows.map((r) => ({
                value: r.pnl,
                itemStyle: { color: r.pnl >= 0 ? theme.profit : theme.risk, borderRadius: [3, 3, 0, 0] },
              })),
              barMaxWidth: 48,
            },
          ],
        }
      }}
    />
  )
}
