// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout / §Typography: consistent page framing. This is the single
//   page-title pattern every route reuses so the heading size, subtitle
//   tone, and top-of-page spacing rhythm are identical across all 9 pages
//   (owner feedback: typography/spacing should repeat predictably, not vary
//   page to page).
// Per Doc 00 §14.11
//
// MOTION (digital materialization): the header is the first thing to resolve on
// a page. The icon chip and heading emerge from the violet bloom, the subtitle
// and actions follow a beat later via their own cascade delays — the "bar →
// title → actions" sequence, achieved with no per-page wiring.
'use client'

import type { ReactNode } from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils/cn'
import { useReveal } from '@/lib/motion'

interface PageHeaderProps {
  title: string
  subtitle?: ReactNode
  icon?: ReactNode
  actions?: ReactNode
  className?: string
}

// Doc 08 §Architecture: stateless presentation component.
export function PageHeader({ title, subtitle, icon, actions, className }: PageHeaderProps) {
  // The <header> stays a plain block; only its inner leaves materialize, so
  // nothing animates the whole row as a unit (which would compound with the
  // per-leaf cascade below it).
  const iconReveal = useReveal('item')
  const titleReveal = useReveal('title')
  const subtitleReveal = useReveal('text')
  const actionsReveal = useReveal('item')
  return (
    <header className={cn('flex items-start justify-between gap-4', className)}>
      <div className="flex items-start gap-3">
        {icon && (
          <motion.span
            {...iconReveal}
            className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border bg-surface-raised text-accent shadow-sm"
          >
            {icon}
          </motion.span>
        )}
        <div>
          <motion.h1 {...titleReveal} className="text-page-title font-semibold tracking-tight text-fg">
            {title}
          </motion.h1>
          {subtitle && (
            <motion.p {...subtitleReveal} className="mt-1 text-body text-fg-muted">
              {subtitle}
            </motion.p>
          )}
        </div>
      </div>
      {actions && (
        <motion.div {...actionsReveal} className="flex shrink-0 items-center gap-2">
          {actions}
        </motion.div>
      )}
    </header>
  )
}
