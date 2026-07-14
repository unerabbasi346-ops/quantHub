// Governing specification: handbook/ui Doc 01 — Apache ECharts is the single
//   FROZEN analytics engine. Doc 00 §14.5/§14.7 DATA HONESTY: the gauge
//   renders Hermes's own real, server-computed 0-100 composite — nothing
//   here recomputes or fabricates a score.
'use client'

import { Chart } from '@/components/ui/Chart'
import type { ChartTheme } from '@/components/ui/chart-theme'

// ── Overall health gauge — green >=80, amber 50-79, red <50 (task spec:
//    "0-100, green/amber/red"), same bespoke-zones pattern as Risk's
//    ExposureGauge, just with the color direction reversed (here, high is
//    good). ──
export function HealthGauge({ score, height = 220 }: { score: number; height?: number }) {
  const clamped = Math.min(Math.max(score, 0), 100)

  return (
    <Chart
      height={height}
      ariaLabel={`System health score ${score.toFixed(1)} of 100`}
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
                  [0.5, theme.risk],
                  [0.8, theme.warning],
                  [1, theme.profit],
                ],
              },
            },
            axisTick: { show: false },
            splitLine: { distance: -20, length: 10, lineStyle: { color: theme.alpha('fg', 0.25), width: 1.5 } },
            axisLabel: { distance: -28, color: theme.fgSubtle, fontFamily: theme.fontMono, fontSize: 9 },
            detail: {
              valueAnimation: true,
              offsetCenter: [0, '18%'],
              formatter: () => score.toFixed(0),
              color: score >= 80 ? theme.profit : score >= 50 ? theme.warning : theme.risk,
              fontFamily: theme.fontMono,
              fontWeight: 700,
              fontSize: 28,
            },
            data: [{ value: clamped }],
          },
        ],
      })}
    />
  )
}
