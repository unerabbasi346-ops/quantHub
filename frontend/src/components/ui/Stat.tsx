// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Components / §Data Visualization: consistent metric presentation. One
//   canonical KPI/stat treatment reused across dashboard, portfolio, risk —
//   so a "gross exposure" figure looks the same everywhere.
// Per Doc 00 §14.11
//
// MOTION (digital materialization): when `value` is a plain formatted string
// (e.g. "$1,234.56", "+2.3%"), it is routed through AnimatedNumber, which
// counts it up from zero AFTER the figure has sharpened — numbers resolve, then
// climb. Non-string / non-numeric values (JSX, "Not yet computed") render
// verbatim. StatCard, being its own boxed tile, self-reveals via the cascade.
'use client'

import type { ReactNode } from 'react'
import { motion, type HTMLMotionProps } from 'framer-motion'
import { cn } from '@/lib/utils/cn'
import { AnimatedNumber, useReveal } from '@/lib/motion'
import { glassSurface, type Elevation } from './Card'

type Tone = 'default' | 'profit' | 'risk' | 'info' | 'warning'

const TONE: Record<Tone, string> = {
  default: 'text-fg',
  profit: 'text-profit',
  risk: 'text-risk',
  info: 'text-info',
  warning: 'text-warning',
}

interface StatProps {
  label: ReactNode
  value: ReactNode
  hint?: ReactNode
  tone?: Tone
  /** Optional distinct icon for the metric (a Lucide node) — sits in a soft accent chip. */
  icon?: ReactNode
  className?: string
}

// Inline stat (no box) — for use inside a Section or Card content region.
export function Stat({ label, value, hint, tone = 'default', icon, className }: StatProps) {
  return (
    <div className={cn('min-w-0', className)}>
      <div className="flex items-center gap-2">
        {icon && (
          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-accent-soft text-accent">
            {icon}
          </span>
        )}
        <div className="truncate text-caption font-medium uppercase tracking-wider text-fg-subtle">
          {label}
        </div>
      </div>
      <div className={cn('mt-1 font-mono text-metric-sm font-semibold tabular-nums tracking-tight', TONE[tone])}>
        {typeof value === 'string' ? <AnimatedNumber value={value} /> : value}
      </div>
      {hint && <div className="mt-0.5 text-caption text-fg-muted">{hint}</div>}
    </div>
  )
}

// Boxed KPI tile — the ONE case where a single stat earns its own bordered
// card (owner feedback: reserve bordered cards for content that truly needs
// grouping, e.g. a single KPI). A subtle elevated surface by default; glow is
// reserved for Hero Chart / AI Workspace / active controls / focus states
// per VE_13 ("restrained glows... avoid excessive bloom") — pass
// `elevation="glow"` explicitly for one of those reserved contexts.
export function StatCard({
  label,
  value,
  hint,
  tone = 'default',
  icon,
  className,
  elevation = 'elevated',
  ...props
}: StatProps & Omit<HTMLMotionProps<'div'>, keyof StatProps> & { elevation?: Elevation }) {
  const reveal = useReveal('container')
  return (
    <motion.div
      {...reveal}
      className={cn(glassSurface(elevation), 'px-4 py-3.5', className)}
      {...props}
    >
      <Stat label={label} value={value} hint={hint} tone={tone} icon={icon} />
    </motion.div>
  )
}
