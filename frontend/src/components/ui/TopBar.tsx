// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout: "Persistent sidebar, top command bar, central workspace,
//   optional contextual panel, responsive grid, modular widgets."
//   §Visual Language: "Dark-first theme, optional light mode."
// Component Standards: reusable design-system component — Doc 08 §Component Standards
// Per Doc 00 §14.11
'use client'

import { useEffect, useState } from 'react'
import { useUIStore } from '@/lib/store/ui'
import { Button } from './Button'

// Doc 08 §Architecture: local UI-only state (theme/sidebar) read from the
// shared store, not owned here — Doc 08 §State Management.
export function TopBar() {
  const sidebarOpen = useUIStore((s) => s.sidebarOpen)
  const toggleSidebar = useUIStore((s) => s.toggleSidebar)
  const theme = useUIStore((s) => s.theme)
  const toggleTheme = useUIStore((s) => s.toggleTheme)

  // Doc 08 hydration safety: the store's `theme` starts as the SSR default
  // ('dark') and only reflects the persisted choice after the client-side
  // effect below runs — render the toggle label from mounted state to
  // avoid a hydration mismatch against the blocking script in layout.tsx.
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-surface px-4">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="sm"
          aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          onClick={toggleSidebar}
        >
          <MenuIcon />
        </Button>
      </div>
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          aria-label="Toggle theme"
          onClick={toggleTheme}
        >
          {mounted && theme === 'dark' ? <SunIcon /> : <MoonIcon />}
        </Button>
      </div>
    </header>
  )
}

function MenuIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function SunIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="2" />
      <path
        d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  )
}

function MoonIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinejoin="round"
      />
    </svg>
  )
}
