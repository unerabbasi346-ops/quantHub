// Governing specification: handbook/ui Doc 04 — "Progress Ring" / "Mini Gauge"
//   micro-visualization; Doc 01 — Apache ECharts engine. Per Doc 00 §14.11
//
// Radial progress ring for a single bounded ratio (signal-validity rate, fill
// rate, directional exposure). MIGRATED from hand-rolled SVG onto the shared
// ECharts wrapper (single engine) while keeping the EXACT public API: same
// 0..1 `value`, size/thickness/tone, and ReactNode centerLabel/centerSub. The
// centre content stays an HTML overlay so callers can pass rich nodes; the ring
// itself is an ECharts gauge, so it inherits the one theme + motion system.
'use client'

import type { ReactNode } from 'react'
import { Chart } from './Chart'
import { cn } from '@/lib/utils/cn'
import type { ChartTheme } from './chart-theme'

type RingTone = 'info' | 'profit' | 'risk' | 'warning'

interface RingProps {
  /** Fraction 0..1 of the ring to fill. Values outside are clamped. */
  value: number
  size?: number
  thickness?: number
  tone?: RingTone
  /** Big centered label (e.g. "92%"). */
  centerLabel?: ReactNode
  /** Small caption under the center label. */
  centerSub?: ReactNode
  className?: string
}

export function Ring({
  value,
  size = 128,
  thickness = 10,
  tone = 'info',
  centerLabel,
  centerSub,
  className,
}: RingProps) {
  const clamped = Math.max(0, Math.min(1, Number.isFinite(value) ? value : 0))
  // Gauge radius must pull in by half the ring thickness so the stroke fits the
  // square box exactly (matches the old SVG r = (size - thickness) / 2).
  const radiusPct = 100 - (thickness / size) * 100

  return (
    <div
      className={cn('relative inline-flex items-center justify-center', className)}
      style={{ width: size, height: size }}
    >
      <Chart
        height={size}
        ariaLabel={typeof centerLabel === 'string' ? `${centerLabel} ${centerSub ?? ''}`.trim() : 'Progress ring'}
        option={(theme: ChartTheme) => ({
          series: [
            {
              type: 'gauge',
              startAngle: 90,
              endAngle: -270,
              min: 0,
              max: 1,
              radius: `${radiusPct}%`,
              center: ['50%', '50%'],
              pointer: { show: false },
              progress: {
                show: true,
                width: thickness,
                roundCap: true,
                itemStyle: { color: theme[tone] },
              },
              axisLine: { lineStyle: { width: thickness, color: [[1, theme.border]] } },
              axisTick: { show: false },
              splitLine: { show: false },
              axisLabel: { show: false },
              title: { show: false },
              detail: { show: false },
              data: [{ value: clamped }],
            },
          ],
        })}
      />
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
        {centerLabel != null && (
          <span className="font-mono text-lg font-semibold tabular-nums text-fg">{centerLabel}</span>
        )}
        {centerSub != null && (
          <span className="mt-0.5 max-w-[80%] text-[10px] uppercase tracking-wide text-fg-subtle">{centerSub}</span>
        )}
      </div>
    </div>
  )
}
