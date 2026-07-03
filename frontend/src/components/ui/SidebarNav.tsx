// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout: "Persistent sidebar ... responsive grid, modular widgets."
// Component Standards: reusable design-system component — Doc 08 §Component Standards
// Architecture: stateless presentation component — Doc 08 §Architecture
// Application Structure: navigation links cover all 9 feature modules — Doc 08 §Application Structure
// Accessibility: semantic nav, keyboard-navigable links, current-page state — Doc 06 §Accessibility
// Per Doc 00 §14.11
'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useUIStore } from '@/lib/store/ui'
import { cn } from '@/lib/utils/cn'

const NAV_ITEMS = [
  { href: '/dashboard',  label: 'Dashboard'   },
  { href: '/portfolio',  label: 'Portfolio'   },
  { href: '/markets',    label: 'Markets'     },
  { href: '/strategies', label: 'Strategies'  },
  { href: '/risk',       label: 'Risk'        },
  { href: '/research',   label: 'Research'    },
  { href: '/execution',  label: 'Execution'   },
  { href: '/monitoring', label: 'Monitoring'  },
  { href: '/settings',   label: 'Settings'    },
] as const

// Doc 08 §Architecture: UI components stateless when practical — the only
// state read here (sidebarOpen) is shared UI chrome state, not owned by
// this component (lib/store/ui.ts).
export function SidebarNav() {
  const pathname = usePathname()
  const sidebarOpen = useUIStore((s) => s.sidebarOpen)

  return (
    <nav
      className={cn(
        'shrink-0 border-r border-border bg-surface flex flex-col py-4 px-3 gap-1 transition-[width]',
        sidebarOpen ? 'w-56' : 'w-16',
      )}
      aria-label="Primary navigation"
    >
      <span
        className={cn(
          'px-3 py-2 text-xs font-semibold text-fg-muted uppercase tracking-wider whitespace-nowrap overflow-hidden',
          !sidebarOpen && 'text-center px-0',
        )}
      >
        {sidebarOpen ? 'Quant Hub' : 'QH'}
      </span>
      {NAV_ITEMS.map(({ href, label }) => {
        const active = pathname === href || pathname?.startsWith(`${href}/`)
        return (
          <Link
            key={href}
            href={href}
            aria-current={active ? 'page' : undefined}
            className={cn(
              'rounded-md px-3 py-2 text-sm transition-colors whitespace-nowrap overflow-hidden',
              active
                ? 'bg-info-soft text-info font-medium'
                : 'text-fg-muted hover:bg-surface-hover hover:text-fg',
              !sidebarOpen && 'text-center px-0',
            )}
          >
            {sidebarOpen ? label : label.slice(0, 1)}
          </Link>
        )
      })}
    </nav>
  )
}
