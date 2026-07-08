// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout: "Persistent sidebar, top command bar, central workspace,
//   optional contextual panel, responsive grid, modular widgets."
//   §Visual Language: "Dark-first theme, optional light mode."
// Component Standards: reusable design-system component — Doc 08 §Component Standards
// Per Doc 00 §14.11
//
// REDESIGN (owner feedback): the top bar had almost nothing in it. It now
// carries real utility presence — a global search field, a notifications
// bell, and a user avatar — alongside the sidebar toggle and theme switch.
//
// HONEST PLACEHOLDER SCOPE (Doc 00 §14.5/§14.7 — flagged): search,
// notifications, and the user menu are STYLED, NON-FUNCTIONAL placeholders.
// There is no search index, no notification/audit pipeline (none exists —
// see S-6 monitoring deferral), and no real auth/user (G-AUTH-1: single-user
// local platform). They are marked with title tooltips and disabled/decorative
// so they read as "planned", never implying capability the platform lacks.
'use client'

import { useEffect, useState } from 'react'
import { Bell, PanelLeft, Search } from 'lucide-react'
import { useUIStore } from '@/lib/store/ui'
import { Button } from './Button'

export function TopBar() {
  const toggleSidebar = useUIStore((s) => s.toggleSidebar)
  const sidebarOpen = useUIStore((s) => s.sidebarOpen)
  const theme = useUIStore((s) => s.theme)
  const toggleTheme = useUIStore((s) => s.toggleTheme)

  // Hydration-safe theme label (see original note): render the theme-driven
  // icon only after mount so SSR ('dark' default) never mismatches.
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])

  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border bg-surface/70 px-4 backdrop-blur-sm">
      <Button
        variant="ghost"
        size="sm"
        aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
        onClick={toggleSidebar}
        className="px-2"
      >
        <PanelLeft size={18} />
      </Button>

      {/* Global search — styled placeholder (no search index exists yet) */}
      <div className="relative hidden max-w-md flex-1 sm:block">
        <Search
          size={15}
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-fg-subtle"
        />
        <input
          type="text"
          placeholder="Search markets, strategies, orders…"
          aria-label="Search (coming soon)"
          title="Search is a styled placeholder — not yet functional"
          className="h-9 w-full rounded-lg border border-border bg-surface-raised/60 pl-9 pr-16 text-sm text-fg placeholder:text-fg-subtle transition-colors focus:border-border-strong focus:bg-surface-raised focus:outline-none"
        />
        <kbd className="pointer-events-none absolute right-2.5 top-1/2 hidden -translate-y-1/2 rounded border border-border bg-surface px-1.5 py-0.5 font-mono text-[10px] text-fg-subtle md:inline-block">
          ⌘K
        </kbd>
      </div>

      <div className="ml-auto flex items-center gap-1.5">
        <Button
          variant="ghost"
          size="sm"
          aria-label="Toggle theme"
          onClick={toggleTheme}
          className="px-2"
        >
          {mounted && theme === 'dark' ? <SunIcon /> : <MoonIcon />}
        </Button>

        {/* Notifications — styled placeholder (no notification pipeline; S-6) */}
        <button
          type="button"
          aria-label="Notifications (coming soon)"
          title="Notifications — planned (no alert pipeline yet)"
          className="relative flex h-8 w-8 items-center justify-center rounded-lg text-fg-muted transition-colors hover:bg-surface-hover hover:text-fg"
        >
          <Bell size={18} />
          <span
            aria-hidden
            className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-warning ring-2 ring-surface"
          />
        </button>

        <div className="mx-1 h-6 w-px bg-border" aria-hidden />

        {/* User — styled placeholder (G-AUTH-1: single-user local, no real auth) */}
        <button
          type="button"
          aria-label="Account (single-user local platform)"
          title="Local operator — real accounts deferred (G-AUTH-1)"
          className="flex items-center gap-2 rounded-lg py-1 pl-1 pr-2 transition-colors hover:bg-surface-hover"
        >
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-accent to-info text-xs font-semibold text-accent-fg">
            QH
          </span>
          <span className="hidden text-sm font-medium text-fg-muted lg:inline">Operator</span>
        </button>
      </div>
    </header>
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
