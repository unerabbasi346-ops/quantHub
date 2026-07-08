// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout: structure by section heading + thin divider rather than
//   wrapping every group in a bordered box (owner feedback: move away from
//   "everything is a bordered box" / reduce box-in-box nesting). A Section
//   is a labelled region of the workspace — a heading, an optional count/
//   action on the right, a hairline rule, then its content — with NO card
//   chrome. Reserve Card for content that genuinely needs visual grouping.
// Per Doc 00 §14.11
import type { ReactNode } from 'react'
import { cn } from '@/lib/utils/cn'

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
  return (
    <section className={cn('space-y-4', className)}>
      <div className="flex items-end justify-between gap-4 border-b border-border pb-2.5">
        <div className="space-y-0.5">
          <h2 className="text-[13px] font-semibold uppercase tracking-wider text-fg-subtle">
            {title}
          </h2>
          {description && <p className="text-sm text-fg-muted">{description}</p>}
        </div>
        {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </div>
      <div className={contentClassName}>{children}</div>
    </section>
  )
}
