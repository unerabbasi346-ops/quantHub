// Governing specification: handbook/ui Doc 01 — Apache ECharts is the single
//   analytics chart engine; Doc 05 §Line/Area; Doc 11 — axes + tooltip + units
//   mandatory. Doc 03 §Empty States. Per Doc 00 §14.11
//
// Single-series area line over time — the strategy conviction curve (signed
// signal values) and backtest equity progression. MIGRATED from hand-rolled SVG
// onto the shared ECharts wrapper (single-engine consistency) while keeping the
// EXACT public API: same {label,value}[] input, same tone/zeroBaseline/height
// props, same "not enough data" guard — so every existing caller renders the
// identical real data, now with a themed axis, crosshair and tooltip.
'use client'

import { Chart } from './Chart'
import { EmptyState } from './States'
import { chartAxis, chartTooltip, type ChartTheme } from './chart-theme'

export interface LinePoint {
  /** X label (e.g. a timestamp) shown on hover. */
  label: string
  value: number
}

interface LineChartProps {
  data: LinePoint[]
  height?: number
  tone?: 'info' | 'profit' | 'risk'
  /** Draw a zero baseline (useful for signed conviction values). */
  zeroBaseline?: boolean
  valueFormat?: (v: number) => string
  className?: string
}

export function LineChart({
  data,
  height = 220,
  tone = 'info',
  zeroBaseline = false,
  valueFormat = (v) => v.toLocaleString(undefined, { maximumFractionDigits: 4 }),
  className,
}: LineChartProps) {
  if (!data || data.length < 2) {
    return (
      <div style={{ height }} className={className}>
        <EmptyState title="Not enough data" description="At least two points are needed to plot a curve." />
      </div>
    )
  }

  const values = data.map((d) => d.value)
  const dataMin = values.reduce((a, b) => Math.min(a, b), Infinity)
  const dataMax = values.reduce((a, b) => Math.max(a, b), -Infinity)
  const yMin = zeroBaseline ? Math.min(dataMin, 0) : undefined
  const yMax = zeroBaseline ? Math.max(dataMax, 0) : undefined

  return (
    <Chart
      className={className}
      height={height}
      ariaLabel="Line chart"
      option={(theme: ChartTheme) => {
        const color = theme[tone]
        const axis = chartAxis(theme)
        return {
          tooltip: chartTooltip(theme, {
            trigger: 'axis',
            axisPointer: { type: 'line', lineStyle: { color: theme.alpha('fg', 0.25), width: 1 } },
            formatter: (params: unknown) => {
              const p = (params as { axisValue: string; data: number }[])[0]
              return `${p.axisValue}<br/><b>${valueFormat(p.data)}</b>`
            },
          }),
          grid: { left: 52, right: 14, top: 12, bottom: 24 },
          xAxis: {
            type: 'category',
            data: data.map((d) => d.label),
            boundaryGap: false,
            ...axis,
            splitLine: { show: false },
          },
          yAxis: {
            type: 'value',
            scale: !zeroBaseline,
            min: yMin,
            max: yMax,
            ...axis,
            axisLabel: { ...axis.axisLabel, formatter: (v: number) => valueFormat(v) },
          },
          series: [
            {
              type: 'line',
              data: values,
              smooth: false,
              showSymbol: false,
              lineStyle: { color, width: 2 },
              itemStyle: { color },
              areaStyle: {
                color: {
                  type: 'linear',
                  x: 0, y: 0, x2: 0, y2: 1,
                  colorStops: [
                    { offset: 0, color: theme.alpha(tone, 0.22) },
                    { offset: 1, color: theme.alpha(tone, 0) },
                  ],
                },
              },
              // zero reference line for signed series
              markLine: zeroBaseline
                ? {
                    silent: true,
                    symbol: 'none',
                    lineStyle: { color: theme.borderStrong, type: 'dashed', width: 1 },
                    data: [{ yAxis: 0 }],
                    label: { show: false },
                  }
                : undefined,
            },
          ],
        }
      }}
    />
  )
}
