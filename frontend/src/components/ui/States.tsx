// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Interaction Standards: "loading/success/error states."
// Doc 08 §Component Standards: reusable design-system components — Doc 08
// Per Doc 00 §14.11
//
// Canonical loading/empty/error presentational states — every feature
// module's data-driven view (Step 4.1+) should render one of these
// instead of a bespoke spinner/message, per Doc 06 "every component
// should have a reusable implementation."
import type { ReactNode } from 'react'
import { Button } from './Button'

// Doc 08 §Architecture: stateless presentation component.
export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-center justify-center gap-3 py-12 text-sm text-fg-muted"
    >
      <span
        aria-hidden="true"
        className="h-4 w-4 animate-spin rounded-full border-2 border-border border-t-info"
      />
      {label}
    </div>
  )
}

interface EmptyStateProps {
  title: string
  description?: string
  action?: ReactNode
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-12 text-center">
      <p className="text-sm font-medium text-fg">{title}</p>
      {description && <p className="max-w-sm text-sm text-fg-muted">{description}</p>}
      {action}
    </div>
  )
}

interface ErrorStateProps {
  title?: string
  description?: string
  onRetry?: () => void
}

// Doc 06 §Interaction Standards pairs error states with a clear recovery
// action where one exists (`onRetry`) rather than a dead-end message.
export function ErrorState({
  title = 'Something went wrong',
  description,
  onRetry,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center justify-center gap-3 rounded-lg border border-risk/30 bg-risk-soft py-12 text-center"
    >
      <p className="text-sm font-medium text-risk">{title}</p>
      {description && <p className="max-w-sm text-sm text-fg-muted">{description}</p>}
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  )
}
