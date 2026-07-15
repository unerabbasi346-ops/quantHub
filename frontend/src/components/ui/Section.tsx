// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout: structure by section heading + thin divider rather than
//   wrapping every group in a bordered box (owner feedback: move away from
//   "everything is a bordered box" / reduce box-in-box nesting). A Section
//   is a labelled region of the workspace — a heading, an optional count/
//   action on the right, a hairline rule, then its content — with NO card
//   chrome. Reserve Card for content that genuinely needs visual grouping.
// Per Doc 00 §14.11
//
// MOTION (digital materialization): the section is a plain block — only its
// heading and description materialize (as text leaves, from the violet bloom).
// Its content is left to reveal itself component-by-component, so nothing
// animates the whole region as one unit (which would compound with the cards /
// tables cascading inside it).
'use client'

import type { ReactNode } from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils/cn'
import { useReveal } from '@/lib/motion'

interface SectionProps {
  title: string
  /** Optional Lucide icon shown before the title (VE_13: "Section headers with icons"). */
  icon?: ReactNode
  description?: ReactNode
  actions?: ReactNode
  children: ReactNode
  className?: string
  contentClassName?: string
}

// Doc 08 §Architecture: stateless presentation component.
export function Section({
  title,
  icon,
  description,
  actions,
  children,
  className,
  contentClassName,
}: SectionProps) {
  const titleReveal = useReveal('title')
  const descReveal = useReveal('text')
  const actionsReveal = useReveal('item')
  return (
    <section className={cn('space-y-4', className)}>
      <div className="flex items-end justify-between gap-4 border-b border-border pb-2.5">
        <div className="space-y-0.5">
          <motion.h2
            {...titleReveal}
            className="flex items-center gap-2 text-section-title font-semibold tracking-tight text-fg"
          >
            {icon && <span className="text-fg-subtle">{icon}</span>}
            {title}
          </motion.h2>
          {description && (
            <motion.p {...descReveal} className="text-body text-fg-muted">
              {description}
            </motion.p>
          )}
        </div>
        {actions && (
          // z-20 (explicit, not `auto`): framer-motion's `y` animation leaves a
          // permanent inline `transform: translateY(0px)` after settling (see
          // lib/motion/variants.ts's `visible` variant) — any non-`none`
          // transform establishes a stacking context (same mechanism the
          // `filter`-stripping comment in lib/motion/reveal.ts calls out for a
          // different property, just never cleaned up for `transform`). With
          // NO explicit z-index this context and content's charts/tables below
          // (Chart.tsx's own motion.div, same lingering-transform mechanism)
          // are peers ordered by paint order — the later-painted content wins
          // and can render its actions dropdown behind a chart. An explicit
          // z-index always outranks an implicit/auto one, regardless of DOM
          // order, so this fixes it for every Section usage at once (e.g.
          // Risk's OI-vs-price asset dropdown).
          <motion.div {...actionsReveal} className="relative z-20 flex shrink-0 items-center gap-2">
            {actions}
          </motion.div>
        )}
      </div>
      <div className={contentClassName}>{children}</div>
    </section>
  )
}
