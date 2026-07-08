// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Data Visualization: "clear, information-dense visualizations." A
//   responsive SVG line chart for a single series over time — the strategy
//   conviction curve (signal values) and backtest equity progression (owner
//   request: "different charts, curves" from data that already exists).
//   Pure SVG + a light hover crosshair; no charting dependency, so it stays
//   fully styleable with the theme tokens.
// Per Doc 00 §14.11
'use client'

import { useState } from 'react'
import { cn } from '@/lib/utils/cn'

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

const TONE_STROKE: Record<NonNullable<LineChartProps['tone']>, string> = {
  info: 'hsl(var(--color-info))',
  profit: 'hsl(var(--color-profit))',
  risk: 'hsl(var(--color-risk))',
}

export function LineChart({
  data,
  height = 220,
  tone = 'info',
  zeroBaseline = false,
  valueFormat = (v) => v.toLocaleString(undefined, { maximumFractionDigits: 4 }),
  className,
}: LineChartProps) {
  const [hover, setHover] = useState<number | null>(null)
  const width = 100 // viewBox units; scales responsively via preserveAspectRatio=none on x

  if (!data || data.length < 2) {
    return (
      <div
        style={{ height }}
        className={cn('flex items-center justify-center text-sm text-fg-muted', className)}
      >
        Not enough data to plot.
      </div>
    )
  }

  const values = data.map((d) => d.value)
  let min = Math.min(...values)
  let max = Math.max(...values)
  if (zeroBaseline) {
    min = Math.min(min, 0)
    max = Math.max(max, 0)
  }
  const span = max - min || 1
  const padY = 8
  const plotH = height - padY * 2

  const x = (i: number) => (i / (data.length - 1)) * width
  const y = (v: number) => padY + (1 - (v - min) / span) * plotH

  const line = data
    .map((d, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(3)} ${y(d.value).toFixed(3)}`)
    .join(' ')
  const area = `${line} L${width} ${height - padY} L0 ${height - padY} Z`
  const stroke = TONE_STROKE[tone]
  const zeroY = zeroBaseline ? y(0) : null

  return (
    <div className={cn('relative w-full', className)}>
      <svg
        width="100%"
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        className="overflow-visible"
        onMouseLeave={() => setHover(null)}
        onMouseMove={(e) => {
          const rect = e.currentTarget.getBoundingClientRect()
          const rel = (e.clientX - rect.left) / rect.width
          setHover(Math.max(0, Math.min(data.length - 1, Math.round(rel * (data.length - 1)))))
        }}
      >
        <defs>
          <linearGradient id={`lc-${tone}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={stroke} stopOpacity="0.2" />
            <stop offset="100%" stopColor={stroke} stopOpacity="0" />
          </linearGradient>
        </defs>
        {zeroY != null && (
          <line
            x1="0"
            y1={zeroY}
            x2={width}
            y2={zeroY}
            stroke="hsl(var(--color-border-strong))"
            strokeWidth="0.4"
            strokeDasharray="1.5 1.5"
            vectorEffect="non-scaling-stroke"
          />
        )}
        <path d={area} fill={`url(#lc-${tone})`} />
        <path
          d={line}
          fill="none"
          stroke={stroke}
          strokeWidth="1.5"
          vectorEffect="non-scaling-stroke"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        {hover != null && (
          <>
            <line
              x1={x(hover)}
              y1="0"
              x2={x(hover)}
              y2={height}
              stroke="hsl(var(--color-fg) / 0.25)"
              strokeWidth="0.4"
              vectorEffect="non-scaling-stroke"
            />
            <circle cx={x(hover)} cy={y(data[hover].value)} r="1.6" fill={stroke} vectorEffect="non-scaling-stroke" />
          </>
        )}
      </svg>
      {hover != null && (
        <div className="pointer-events-none absolute left-2 top-2 rounded-md border border-border bg-surface-raised/95 px-2.5 py-1.5 text-xs shadow-md">
          <div className="font-mono font-semibold tabular-nums text-fg">{valueFormat(data[hover].value)}</div>
          <div className="text-[11px] text-fg-muted">{data[hover].label}</div>
        </div>
      )}
    </div>
  )
}
