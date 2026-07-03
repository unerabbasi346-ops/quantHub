// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout: "... optional contextual panel ..."
// Per Doc 00 §14.11
//
// This is a composable primitive, not force-mounted into the global app
// shell — Doc 06 calls it "optional", so it is up to an individual feature
// page (Step 4.2+) to render it alongside its workspace content when it
// has something contextual to show (e.g. a selected instrument's detail).
// No global "panel slot"/store plumbing is added here since no feature has
// content for it yet — that would be designing for a hypothetical future
// requirement instead of the one thing Doc 06 actually asks for.
import type { ReactNode } from 'react'
import { cn } from '@/lib/utils/cn'

interface ContextPanelProps {
  title: string
  children: ReactNode
  className?: string
}

export function ContextPanel({ title, children, className }: ContextPanelProps) {
  return (
    <aside
      className={cn(
        'w-80 shrink-0 border-l border-border bg-surface p-4 overflow-y-auto',
        className,
      )}
      aria-label={title}
    >
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-fg-muted">
        {title}
      </h2>
      {children}
    </aside>
  )
}
