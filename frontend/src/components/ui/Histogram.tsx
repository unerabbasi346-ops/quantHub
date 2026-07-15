// Governing specification: handbook/ui Doc 01 — Apache ECharts engine; Doc 05
//   §Histogram; Doc 11 — tooltip mandatory. Doc 03 — color communicates sign.
// Per Doc 00 §14.11
//
// Distribution histogram of a real numeric series (a strategy's signed
// conviction values). MIGRATED onto the shared ECharts wrapper. The BINNING is
// unchanged from the SVG original (same buckets, same counts) — only the render
// moved to ECharts — so it shows identical real data. Signed bars keep their
// semantic colouring (negative=risk, positive=profit) via theme tokens.
'use client'

import { useMemo } from 'react'
import { Chart } from './Chart'
import { EmptyState } from './States'
import { chartAxis, chartTooltip, type ChartTheme } from './chart-theme'

interface HistogramProps {
  values: number[]
  /** Number of buckets (default 11 — odd, so a zero-centred series has a middle bin). */
  buckets?: number
  height?: number
  /** Colour bars by sign around zero (for signed data like conviction). */
  signed?: boolean
  valueFormat?: (v: number) => string
  className?: string
}

export function Histogram({
  values,
  buckets = 11,
  height = 200,
  signed = true,
  valueFormat = (v) => v.toLocaleString(undefined, { maximumFractionDigits: 4 }),
  className,
}: HistogramProps) {
  // Identical binning to the original SVG implementation.
  const bins = useMemo(() => {
    if (values.length < 2) return []
    const min = values.reduce((a, b) => Math.min(a, b), Infinity)
    const max = values.reduce((a, b) => Math.max(a, b), -Infinity)
    const span = max - min || 1
    const w = span / buckets
    const out = Array.from({ length: buckets }, (_, i) => ({
      from: min + i * w,
      to: min + (i + 1) * w,
      count: 0,
    }))
    for (const v of values) {
      const idx = Math.min(buckets - 1, Math.floor((v - min) / w))
      out[idx].count++
    }
    return out
  }, [values, buckets])

  if (bins.length === 0) {
    return (
      <div style={{ height }} className={className}>
        <EmptyState title="Not enough data" description="At least two values are needed to plot a distribution." />
      </div>
    )
  }

  return (
    <Chart
      className={className}
      height={height}
      ariaLabel="Distribution histogram"
      option={(theme: ChartTheme) => {
        const axis = chartAxis(theme)
        return {
          tooltip: chartTooltip(theme, {
            trigger: 'item',
            formatter: (p: unknown) => {
              const b = bins[(p as { dataIndex: number }).dataIndex]
              return `<b>${b.count}</b> ${b.count === 1 ? 'signal' : 'signals'}<br/>${valueFormat(b.from)} … ${valueFormat(b.to)}`
            },
          }),
          grid: { left: 40, right: 14, top: 12, bottom: 24 },
          xAxis: {
            type: 'category',
            data: bins.map((b) => valueFormat((b.from + b.to) / 2)),
            ...axis,
            axisLabel: { ...axis.axisLabel, interval: Math.floor(buckets / 4) },
            splitLine: { show: false },
          },
          yAxis: {
            type: 'value',
            minInterval: 1,
            ...axis,
          },
          series: [
            {
              type: 'bar',
              data: bins.map((b) => ({
                value: b.count,
                itemStyle: {
                  color: signed ? ((b.from + b.to) / 2 < 0 ? theme.risk : theme.profit) : theme.info,
                  borderRadius: [2, 2, 0, 0],
                },
              })),
              barCategoryGap: '12%',
            },
          ],
        }
      }}
    />
  )
}
