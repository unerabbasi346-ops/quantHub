// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0)
// Component Standards: reusable design-system component — Doc 08 §Component Standards
// Architecture: stateless presentation component — Doc 08 §Architecture
// Application Structure: navigation links cover all 8 feature modules — Doc 08 §Application Structure
// Accessibility: semantic nav, keyboard-navigable links — Doc 08 §Accessibility
// Per Doc 00 §14.11
import Link from 'next/link'

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

// Doc 08 §Architecture: UI components stateless when practical
export function SidebarNav() {
  return (
    <nav
      className="w-56 shrink-0 border-r bg-white flex flex-col py-4 px-3 gap-1"
      aria-label="Primary navigation"
    >
      <span className="px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
        Quant Hub
      </span>
      {NAV_ITEMS.map(({ href, label }) => (
        <Link
          key={href}
          href={href}
          className="rounded px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
        >
          {label}
        </Link>
      ))}
    </nav>
  )
}
