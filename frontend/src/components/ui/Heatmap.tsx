// Governing specification: handbook/ui Doc 04 — Correlation Matrix is a
//   "Professional Heatmap, Interactive, Hover Values"; Doc 10 §Correlation;
//   Doc 11 — tooltip + hover mandatory. Per Doc 00 §14.11
//
// Reusable matrix heatmap. Diverging mode maps -1→risk / 0→neutral / +1→profit
// (correlation), sequential mode maps a single-hue ramp (magnitudes). The caller
// supplies real values; nulls render as empty cells (no fabricated zero).
'use client'

import { Chart } from './Chart'
import { chartTooltip, type ChartTheme } from './chart-theme'

interface HeatmapProps {
  xLabels: string[]
  yLabels: string[]
  /** values[y][x]; null = no data for that cell. */
  values: (number | null)[][]
  height?: number
  /** 'diverging' for correlation (-1..1), 'sequential' for magnitudes (0..max). */
  mode?: 'diverging' | 'sequential'
  min?: number
  max?: number
  valueFormat?: (v: number) => string
  className?: string
}

export function Heatmap({
  xLabels,
  yLabels,
  values,
  height = 320,
  mode = 'diverging',
  min = mode === 'diverging' ? -1 : 0,
  max = 1,
  valueFormat = (v) => v.toFixed(2),
  className,
}: HeatmapProps) {
  const points: [number, number, number][] = []
  values.forEach((row, y) => {
    row.forEach((v, x) => {
      if (v !== null && Number.isFinite(v)) points.push([x, y, v])
    })
  })
  return (
    <Chart
      className={className}
      height={height}
      ariaLabel="Heatmap"
      option={(theme: ChartTheme) => ({
        tooltip: chartTooltip(theme, {
          formatter: (p: unknown) => {
            const d = p as { data: [number, number, number] }
            const [x, y, v] = d.data
            return `${yLabels[y]} · ${xLabels[x]}<br/><b>${valueFormat(v)}</b>`
          },
        }),
        grid: { left: 70, right: 16, top: 16, bottom: 44 },
        xAxis: {
          type: 'category',
          data: xLabels,
          splitArea: { show: true },
          axisLine: { lineStyle: { color: theme.border } },
          axisTick: { show: false },
          axisLabel: { color: theme.fgSubtle, fontFamily: theme.fontMono, fontSize: 10, rotate: xLabels.length > 8 ? 45 : 0 },
        },
        yAxis: {
          type: 'category',
          data: yLabels,
          splitArea: { show: true },
          axisLine: { lineStyle: { color: theme.border } },
          axisTick: { show: false },
          axisLabel: { color: theme.fgSubtle, fontFamily: theme.fontMono, fontSize: 10 },
        },
        visualMap: {
          min,
          max,
          // Map color on the VALUE dimension (index 2 of [x, y, value]). Without
          // this, ECharts can default to a coordinate dimension whose range sits
          // outside [min,max], marking every cell out-of-range → unpainted.
          dimension: 2,
          calculable: true,
          orient: 'horizontal',
          left: 'center',
          bottom: 0,
          itemWidth: 12,
          itemHeight: 90,
          textStyle: { color: theme.fgSubtle, fontFamily: theme.fontMono, fontSize: 10 },
          inRange: {
            color:
              mode === 'diverging'
                ? [theme.risk, theme.borderStrong, theme.profit]
                : [theme.borderStrong, theme.info],
          },
        },
        series: [
          {
            type: 'heatmap',
            data: points,
            label: {
              show: xLabels.length <= 12,
              color: theme.fg,
              fontFamily: theme.fontMono,
              fontSize: 10,
              formatter: (p: unknown) => valueFormat((p as { data: [number, number, number] }).data[2]),
            },
            itemStyle: { borderColor: theme.surfaceRaised, borderWidth: 2, borderRadius: 2 },
            emphasis: { itemStyle: { borderColor: theme.borderStrong, borderWidth: 2 } },
          },
        ],
      })}
    />
  )
}
