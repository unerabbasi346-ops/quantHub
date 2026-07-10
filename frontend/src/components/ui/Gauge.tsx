// Governing specification: handbook/ui Doc 04 — Strategy Health Card / System
//   Health use a "Gauge"; Doc 05 §Gauge Charts. Doc 03 — color communicates
//   state, never decoration. Per Doc 00 §14.11
//
// Reusable single-value gauge for a genuinely-computed scalar in a bounded range
// (e.g. capital utilization %, a health score). The needle color follows
// thresholds so the reading is semantic (green→amber→red). Callers MUST pass a
// real value; there is no placeholder mode — an uncomputed metric shows an
// EmptyState instead of a fabricated gauge (data honesty).
'use client'

import { Chart } from './Chart'
import type { ChartTheme } from './chart-theme'

interface GaugeProps {
  value: number
  min?: number
  max?: number
  height?: number
  /** Unit suffix shown under the value, e.g. '%'. */
  unit?: string
  /** Fraction thresholds (0..1 of range) → tone. Ascending. Default profit→warn→risk. */
  invert?: boolean
  valueFormat?: (v: number) => string
  className?: string
}

export function Gauge({
  value,
  min = 0,
  max = 100,
  height = 200,
  unit = '',
  invert = false,
  valueFormat = (v) => v.toFixed(0),
  className,
}: GaugeProps) {
  return (
    <Chart
      className={className}
      height={height}
      ariaLabel={`Gauge: ${valueFormat(value)}${unit}`}
      option={(theme: ChartTheme) => {
        // Low→high color ramp. `invert` flips it for metrics where high is bad
        // (e.g. utilization/leverage) vs good (e.g. health score).
        const stops: [number, string][] = invert
          ? [[0.6, theme.profit], [0.85, theme.warning], [1, theme.risk]]
          : [[0.4, theme.risk], [0.7, theme.warning], [1, theme.profit]]
        return {
          series: [
            {
              type: 'gauge',
              min,
              max,
              radius: '100%',
              center: ['50%', '62%'],
              startAngle: 210,
              endAngle: -30,
              progress: { show: false },
              pointer: { width: 4, itemStyle: { color: theme.fg } },
              anchor: { show: true, size: 8, itemStyle: { color: theme.fg } },
              axisLine: { lineStyle: { width: 10, color: stops } },
              axisTick: { distance: -14, length: 4, lineStyle: { color: theme.fgSubtle, width: 1 } },
              splitLine: { distance: -16, length: 10, lineStyle: { color: theme.fgSubtle, width: 1.5 } },
              axisLabel: { distance: -6, color: theme.fgSubtle, fontFamily: theme.fontMono, fontSize: 9 },
              title: { show: false },
              detail: {
                valueAnimation: true,
                offsetCenter: [0, '38%'],
                formatter: `${valueFormat(value)}${unit}`,
                color: theme.fg,
                fontFamily: theme.fontMono,
                fontWeight: 600,
                fontSize: 20,
              },
              data: [{ value }],
            },
          ],
        }
      }}
    />
  )
}
