// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout: "Persistent sidebar ... responsive grid, modular widgets."
// Component Standards: reusable design-system component — Doc 08 §Component Standards
// Application Structure: navigation links cover all 9 feature modules — Doc 08 §Application Structure
// Accessibility: semantic nav, keyboard-navigable links, current-page state — Doc 06 §Accessibility
// Per Doc 00 §14.11
//
// REDESIGN (owner feedback): the sidebar now carries a per-item lucide icon,
// collapses to an icon-only rail that still shows the brand mark, and groups
// links into labelled sections. Collapsed items expose their label via the
// native title tooltip so the icon-only rail stays navigable.
'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Activity,
  ArrowLeftRight,
  Brain,
  CandlestickChart,
  FlaskConical,
  LayoutDashboard,
  Settings,
  ShieldAlert,
  Wallet,
  type LucideIcon,
} from 'lucide-react'
import { useUIStore } from '@/lib/store/ui'
import { cn } from '@/lib/utils/cn'
import { BrandMark } from './BrandMark'

interface NavItem {
  href: string
  label: string
  icon: LucideIcon
}

const NAV_GROUPS: { heading: string; items: NavItem[] }[] = [
  {
    heading: 'Overview',
    items: [{ href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard }],
  },
  {
    heading: 'Trading',
    items: [
      { href: '/portfolio', label: 'Portfolio', icon: Wallet },
      { href: '/markets', label: 'Markets', icon: CandlestickChart },
      { href: '/execution', label: 'Execution', icon: ArrowLeftRight },
    ],
  },
  {
    heading: 'Analysis',
    items: [
      { href: '/strategies', label: 'Strategies', icon: Brain },
      { href: '/risk', label: 'Risk', icon: ShieldAlert },
      { href: '/research', label: 'Research', icon: FlaskConical },
    ],
  },
  {
    heading: 'System',
    items: [
      { href: '/monitoring', label: 'Monitoring', icon: Activity },
      { href: '/settings', label: 'Settings', icon: Settings },
    ],
  },
]

export function SidebarNav() {
  const pathname = usePathname()
  const open = useUIStore((s) => s.sidebarOpen)

  return (
    <nav
      className={cn(
        'shrink-0 border-r border-border bg-surface/80 backdrop-blur-sm flex flex-col transition-[width] duration-200 ease-out',
        open ? 'w-60' : 'w-[4.25rem]',
      )}
      aria-label="Primary navigation"
    >
      {/* Brand */}
      <div className={cn('flex h-14 items-center gap-2.5 border-b border-border px-4', !open && 'justify-center px-0')}>
        <BrandMark size={26} />
        {open && (
          <span className="text-[15px] font-semibold tracking-tight text-fg">
            Quant<span className="text-info">Hub</span>
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-2.5 py-3">
        {NAV_GROUPS.map((group) => (
          <div key={group.heading} className="mb-4 last:mb-0">
            <p
              className={cn(
                'px-2.5 pb-1.5 text-[10px] font-semibold uppercase tracking-widest text-fg-subtle',
                !open && 'text-center px-0',
              )}
            >
              {open ? group.heading : '·'}
            </p>
            <div className="space-y-0.5">
              {group.items.map(({ href, label, icon: Icon }) => {
                const active = pathname === href || pathname?.startsWith(`${href}/`)
                return (
                  <Link
                    key={href}
                    href={href}
                    title={!open ? label : undefined}
                    aria-current={active ? 'page' : undefined}
                    className={cn(
                      'group relative flex items-center gap-3 rounded-lg px-2.5 py-2 text-sm transition-colors duration-150',
                      active
                        ? 'bg-info-soft text-info font-medium'
                        : 'text-fg-muted hover:bg-surface-hover hover:text-fg',
                      !open && 'justify-center px-0',
                    )}
                  >
                    {active && (
                      <span
                        aria-hidden
                        className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-r bg-info"
                      />
                    )}
                    <Icon size={18} strokeWidth={2} className="shrink-0" />
                    {open && <span className="truncate">{label}</span>}
                  </Link>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Environment footer */}
      <div className={cn('border-t border-border px-3 py-3', !open && 'px-0')}>
        <div
          className={cn(
            'flex items-center gap-2 rounded-lg bg-surface-hover/50 px-2.5 py-1.5',
            !open && 'justify-center',
          )}
        >
          <span aria-hidden className="h-2 w-2 shrink-0 rounded-full bg-profit shadow-[0_0_6px] shadow-profit/60" />
          {open && <span className="text-[11px] font-medium text-fg-muted">Local · connected</span>}
        </div>
      </div>
    </nav>
  )
}
