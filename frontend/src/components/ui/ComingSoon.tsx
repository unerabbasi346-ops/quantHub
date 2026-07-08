// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Interaction Standards: a deferred module should present an intentional
//   "planned" state, not a bare sentence floating in a void (owner feedback
//   on Settings/Monitoring/Research). This is the canonical placeholder for
//   a route whose backend is deliberately deferred (S-6 / S-7): a centered
//   icon tile, a heading, a one-line explanation, an optional "Planned"
//   badge, and an optional bullet list of what it will hold.
// Per Doc 00 §14.11
import type { ReactNode } from 'react'
import { Badge } from './Badge'

interface ComingSoonProps {
  icon: ReactNode
  title: string
  description: string
  /** Short reference note, e.g. "Deferred per S-7". */
  note?: string
  /** Optional preview of planned contents. */
  planned?: string[]
}

// Doc 08 §Architecture: stateless presentation component.
export function ComingSoon({ icon, title, description, note, planned }: ComingSoonProps) {
  return (
    <div className="mx-auto flex min-h-[60vh] max-w-md flex-col items-center justify-center px-6 text-center">
      <div className="relative mb-6">
        <div
          aria-hidden
          className="absolute inset-0 -z-10 rounded-full bg-accent/20 blur-2xl"
        />
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-border-strong bg-surface-raised text-accent shadow-lg">
          {icon}
        </div>
      </div>
      <div className="mb-3 flex items-center gap-2">
        <h2 className="text-lg font-semibold tracking-tight text-fg">{title}</h2>
        <Badge variant="info">Planned</Badge>
      </div>
      <p className="max-w-sm text-sm leading-relaxed text-fg-muted">{description}</p>

      {planned && planned.length > 0 && (
        <ul className="mt-6 w-full max-w-xs space-y-2 text-left">
          {planned.map((item) => (
            <li
              key={item}
              className="flex items-center gap-2.5 rounded-lg border border-border bg-surface/60 px-3 py-2 text-sm text-fg-muted"
            >
              <span aria-hidden className="h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
              {item}
            </li>
          ))}
        </ul>
      )}

      {note && <p className="mt-6 text-xs text-fg-subtle">{note}</p>}
    </div>
  )
}
