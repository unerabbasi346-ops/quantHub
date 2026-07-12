// Governing specification: handbook/ui Doc 01 — Apache ECharts engine; Doc 05
//   §Multi-Line; Doc 11 — legend + tooltip mandatory. Per Doc 00 §14.11
//
// Multi-series line over a shared x-axis (e.g. a strategy's fast/slow moving
// averages from signal metadata). MIGRATED from hand-rolled SVG onto the shared
// ECharts wrapper, keeping the EXACT public API (labels + Series[] with the same
// deliberate colour order) so callers render identical real data. Series colours
// resolve from the theme so they stay distinct and correct in both themes.
'use client'

import { Chart } from './Chart'
import { EmptyState } from './States'
import { chartAxis, chartTooltip, type ChartTheme } from './chart-theme'

export interface Series {
  name: string
  /** One value per shared x index (same length as `labels`). */
  values: number[]
}

interface MultiLineChartProps {
  labels: string[]
  series: Series[]
  height?: number
  valueFormat?: (v: number) => string
  className?: string
}

// Deliberate order so the common fast/slow pair is most distinct: brand violet,
// a cooler cyan-leaning info blend, amber, and a deeper orange-leaning risk
// blend — resolved from theme tokens (theme-correct in both modes), not
// literal hex, so the palette still recolors across the light/dark toggle.
const SERIES_COLORS = (t: ChartTheme) => [t.accent, t.alpha('info', 0.85), t.warning, t.alpha('risk', 0.75)]

export function MultiLineChart({
  labels,
  series,
  height = 240,
  valueFormat = (v) => v.toLocaleString(undefined, { maximumFractionDigits: 2 }),
  className,
}: MultiLineChartProps) {
  if (labels.length < 2 || series.length === 0) {
    return (
      <div style={{ height }} className={className}>
        <EmptyState title="Not enough data" description="At least two points are needed to plot a curve." />
      </div>
    )
  }

  return (
    <Chart
      className={className}
      height={height}
      ariaLabel={`Multi-line chart: ${series.map((s) => s.name).join(', ')}`}
      option={(theme: ChartTheme) => {
        const colors = SERIES_COLORS(theme)
        const axis = chartAxis(theme)
        return {
          color: colors,
          tooltip: chartTooltip(theme, {
            trigger: 'axis',
            axisPointer: { type: 'line', lineStyle: { color: theme.alpha('fg', 0.25), width: 1 } },
            valueFormatter: (v: unknown) => valueFormat(v as number),
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
            data: series.map((s) => s.name),
          },
          grid: { left: 52, right: 14, top: 40, bottom: 24 },
          xAxis: { type: 'category', data: labels, boundaryGap: false, ...axis, splitLine: { show: false } },
          yAxis: {
            type: 'value',
            scale: true,
            ...axis,
            axisLabel: { ...axis.axisLabel, formatter: (v: number) => valueFormat(v) },
          },
          series: series.map((s, i) => ({
            name: s.name,
            type: 'line',
            data: s.values,
            smooth: 0.2,
            showSymbol: false,
            lineStyle: { width: 2 },
            // Primary (first) series gets a soft gradient fill so it reads as
            // the lead indicator; the rest stay plain lines to avoid clutter.
            areaStyle:
              i === 0
                ? {
                    color: {
                      type: 'linear',
                      x: 0, y: 0, x2: 0, y2: 1,
                      colorStops: [
                        { offset: 0, color: theme.alpha('accent', 0.15) },
                        { offset: 1, color: theme.alpha('accent', 0) },
                      ],
                    },
                  }
                : undefined,
          })),
        }
      }}
    />
  )
}
