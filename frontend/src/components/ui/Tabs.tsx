// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Components: "Standardize ... tabs ..."
//   §Accessibility: "Keyboard navigation ... meaningful labels."
// Per Doc 00 §14.11
//
// No headless-UI/Radix dependency exists in this project (Doc 08 §Technology
// does not name one for tabs) — a minimal accessible implementation using
// native ARIA tab-pattern roles, kept local to this one component.
'use client'

import { useId, useState, type ReactNode } from 'react'
import { cn } from '@/lib/utils/cn'

export interface TabItem {
  value: string
  label: string
  content: ReactNode
}

interface TabsProps {
  items: TabItem[]
  defaultValue?: string
  className?: string
}

// Doc 08 §Architecture: local UI-only state (active tab), isolated to this
// component — Doc 08 §State Management "keep local UI state isolated."
export function Tabs({ items, defaultValue, className }: TabsProps) {
  const [active, setActive] = useState(defaultValue ?? items[0]?.value)
  const baseId = useId()

  return (
    <div className={className}>
      <div role="tablist" className="flex gap-1 border-b border-border" aria-label="Tabs">
        {items.map((item) => {
          const selected = item.value === active
          return (
            <button
              key={item.value}
              role="tab"
              id={`${baseId}-tab-${item.value}`}
              aria-selected={selected}
              aria-controls={`${baseId}-panel-${item.value}`}
              tabIndex={selected ? 0 : -1}
              onClick={() => setActive(item.value)}
              className={cn(
                'border-b-2 px-3 py-2 text-sm font-medium transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-info focus-visible:ring-offset-2 focus-visible:ring-offset-bg',
                selected
                  ? 'border-info text-fg'
                  : 'border-transparent text-fg-muted hover:text-fg',
              )}
            >
              {item.label}
            </button>
          )
        })}
      </div>
      {items.map((item) => (
        <div
          key={item.value}
          role="tabpanel"
          id={`${baseId}-panel-${item.value}`}
          aria-labelledby={`${baseId}-tab-${item.value}`}
          hidden={item.value !== active}
          className="pt-4"
        >
          {item.value === active ? item.content : null}
        </div>
      ))}
    </div>
  )
}
