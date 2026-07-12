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
  description?: ReactNode
  actions?: ReactNode
  children: ReactNode
  className?: string
  contentClassName?: string
}

// Doc 08 §Architecture: stateless presentation component.
export function Section({
  title,
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
            className="text-section-title font-semibold tracking-tight text-fg"
          >
            {title}
          </motion.h2>
          {description && (
            <motion.p {...descReveal} className="text-body text-fg-muted">
              {description}
            </motion.p>
          )}
        </div>
        {actions && (
          <motion.div {...actionsReveal} className="flex shrink-0 items-center gap-2">
            {actions}
          </motion.div>
        )}
      </div>
      <div className={contentClassName}>{children}</div>
    </section>
  )
}
