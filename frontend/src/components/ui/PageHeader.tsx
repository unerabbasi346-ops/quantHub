// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout / §Typography: consistent page framing. This is the single
//   page-title pattern every route reuses so the heading size, subtitle
//   tone, and top-of-page spacing rhythm are identical across all 9 pages
//   (owner feedback: typography/spacing should repeat predictably, not vary
//   page to page).
// Per Doc 00 §14.11
import type { ReactNode } from 'react'
import { cn } from '@/lib/utils/cn'

interface PageHeaderProps {
  title: string
  subtitle?: ReactNode
  icon?: ReactNode
  actions?: ReactNode
  className?: string
}

// Doc 08 §Architecture: stateless presentation component.
export function PageHeader({ title, subtitle, icon, actions, className }: PageHeaderProps) {
  return (
    <header className={cn('flex items-start justify-between gap-4', className)}>
      <div className="flex items-start gap-3">
        {icon && (
          <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border bg-surface-raised text-info shadow-sm">
            {icon}
          </span>
        )}
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-fg">{title}</h1>
          {subtitle && (
            <p className="mt-1 text-sm leading-relaxed text-fg-muted">{subtitle}</p>
          )}
        </div>
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </header>
  )
}
