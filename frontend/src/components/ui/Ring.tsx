// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Data Visualization: "clear, information-dense visualizations." A radial
//   gauge for a single bounded ratio (signal-validity rate, leverage vs a
//   reference) reads faster than a bare number (owner request: gauge/ring
//   stat displays). SVG-based, no charting dependency.
// Motion: framer-motion animates the arc sweep on mount (≤600ms), disabled
//   under prefers-reduced-motion via the global guard.
// Per Doc 00 §14.11
'use client'

import { motion, useReducedMotion } from 'framer-motion'
import type { ReactNode } from 'react'
import { cn } from '@/lib/utils/cn'

type RingTone = 'info' | 'profit' | 'risk' | 'warning'

const STROKE: Record<RingTone, string> = {
  info: 'hsl(var(--color-info))',
  profit: 'hsl(var(--color-profit))',
  risk: 'hsl(var(--color-risk))',
  warning: 'hsl(var(--color-warning))',
}

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

// Doc 08 §Architecture: stateless presentation component.
export function Ring({
  value,
  size = 128,
  thickness = 10,
  tone = 'info',
  centerLabel,
  centerSub,
  className,
}: RingProps) {
  const reduce = useReducedMotion()
  const clamped = Math.max(0, Math.min(1, Number.isFinite(value) ? value : 0))
  const r = (size - thickness) / 2
  const c = 2 * Math.PI * r
  const center = size / 2

  return (
    <div className={cn('relative inline-flex items-center justify-center', className)}>
      <svg width={size} height={size} className="-rotate-90" aria-hidden="true">
        <circle
          cx={center}
          cy={center}
          r={r}
          fill="none"
          stroke="hsl(var(--color-border))"
          strokeWidth={thickness}
        />
        <motion.circle
          cx={center}
          cy={center}
          r={r}
          fill="none"
          stroke={STROKE[tone]}
          strokeWidth={thickness}
          strokeLinecap="round"
          strokeDasharray={c}
          initial={{ strokeDashoffset: reduce ? c * (1 - clamped) : c }}
          animate={{ strokeDashoffset: c * (1 - clamped) }}
          transition={{ duration: reduce ? 0 : 0.6, ease: [0.22, 1, 0.36, 1] }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        {centerLabel != null && (
          <span className="font-mono text-lg font-semibold tabular-nums text-fg">
            {centerLabel}
          </span>
        )}
        {centerSub != null && (
          <span className="mt-0.5 max-w-[80%] text-[10px] uppercase tracking-wide text-fg-subtle">
            {centerSub}
          </span>
        )}
      </div>
    </div>
  )
}
