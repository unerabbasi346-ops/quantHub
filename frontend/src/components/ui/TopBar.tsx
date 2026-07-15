// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout: "top command bar, central workspace." §Visual Language:
//   "Dark-first theme." §Accessibility: semantic nav, keyboard-navigable.
// Component Standards: reusable design-system component — Doc 08 §Component Standards
// Per Doc 00 §14.11
//
// NAVIGATION RESTRUCTURE (owner request): navigation moves from the left
// vertical sidebar to this HORIZONTAL top bar. All 9 feature routes are
// reachable from here. GROUPING CHOICE (flagged — owner asked for a proposed
// primary/overflow split):
//   PRIMARY (always inline on desktop): Dashboard, Portfolio, Markets,
//     Execution, Strategies, Risk — the six with real Phase 1–4 data and the
//     daily trading/analysis workflow.
//   OVERFLOW ("More" menu): Research, Monitoring, Settings — the three that are
//     deferred / placeholder-stage per S-6 (no research module, no monitoring
//     pipeline, single-user settings). Demoting them to an overflow menu is an
//     honest reflection of their current secondary status, not a hierarchy
//     invented for looks.
// Below the lg breakpoint the primary row collapses into the same menu so all
// nine stay reachable (S-6: full multi-device parity is still deferred; this is
// a graceful single-menu fallback, not a full mobile nav).
'use client'

import { useEffect, useRef, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { DURATION, EASE_OUT } from '@/lib/motion'
import {
  Activity,
  ArrowLeftRight,
  Bell,
  Brain,
  CandlestickChart,
  ChevronDown,
  FlaskConical,
  LayoutDashboard,
  Menu,
  Search,
  Settings,
  ShieldAlert,
  Wallet,
  type LucideIcon,
} from 'lucide-react'
import { useUIStore } from '@/lib/store/ui'
import { cn } from '@/lib/utils/cn'
import { BrandMark } from './BrandMark'
import { glassSurface } from './Card'
import { Tooltip } from './Tooltip'
import { openCommandPalette } from './CommandPalette'

export interface NavItem {
  href: string
  label: string
  icon: LucideIcon
}

// Primary routes render inline on desktop; overflow routes live in the "More"
// menu. See the grouping-choice note in the file header.
// Exported so CommandPalette can list "pages" from the same single source
// of truth instead of duplicating the route list (Doc 08 §Component
// Standards: no duplicated UI implementations).
export const PRIMARY: NavItem[] = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/portfolio', label: 'Portfolio', icon: Wallet },
  { href: '/markets', label: 'Markets', icon: CandlestickChart },
  { href: '/execution', label: 'Execution', icon: ArrowLeftRight },
  { href: '/strategies', label: 'Strategies', icon: Brain },
  { href: '/risk', label: 'Risk', icon: ShieldAlert },
]
export const OVERFLOW: NavItem[] = [
  { href: '/research', label: 'Research', icon: FlaskConical },
  { href: '/monitoring', label: 'Monitoring', icon: Activity },
  { href: '/settings', label: 'Settings', icon: Settings },
]

function isActive(pathname: string | null, href: string): boolean {
  return pathname === href || Boolean(pathname?.startsWith(`${href}/`))
}

/** Close a popover when a click lands outside its ref, or Escape is pressed. */
function useDismiss(open: boolean, close: () => void) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open) return
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) close()
    }
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && close()
    document.addEventListener('mousedown', onClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [open, close])
  return ref
}

function NavLink({ item, pathname }: { item: NavItem; pathname: string | null }) {
  const active = isActive(pathname, item.href)
  const Icon = item.icon
  return (
    <Link
      href={item.href}
      aria-current={active ? 'page' : undefined}
      className={cn(
        'relative flex items-center gap-2 rounded-lg px-3 py-1.5 text-nav font-medium transition-colors duration-150',
        active
          ? 'bg-accent-soft text-accent'
          : 'text-fg-muted hover:bg-surface-hover hover:text-fg',
      )}
    >
      <Icon size={16} strokeWidth={2} className="shrink-0" />
      <span>{item.label}</span>
    </Link>
  )
}

export function TopBar() {
  const pathname = usePathname()
  const theme = useUIStore((s) => s.theme)
  const toggleTheme = useUIStore((s) => s.toggleTheme)
  const reduce = useReducedMotion()

  // The bar lives in the persistent layout, so this materializes ONCE on the
  // first app load (not on route changes): the bar settles from the top, then
  // the nav and the right-hand utilities resolve a beat later — a left-to-right
  // "chrome coming online" feel. No filter here (it would fight the bar's own
  // backdrop-blur); a crisp opacity + slide is enough above the page wash.
  // BUG THIS FIXES (Phase 5 — same root cause `lib/motion/reveal.ts` already
  // documents): `useReducedMotion()` reports `false` on the server and on
  // client hydration's first render, then flips to `true` a render or two
  // later for a real reduced-motion user. The old `reduce ? {} : {...}`
  // withheld `initial`/`animate`/`transition` entirely on that later render —
  // but withholding `animate` tells framer to stop asserting ANY target, not
  // to jump to a visible one, so these 3 elements (header, primary nav, right
  // utilities) froze at whatever opacity/y they'd reached the instant `reduce`
  // flipped, sometimes still invisible. The fix: always assert the SAME
  // `animate` target and only zero out the motion when reduced, so framer
  // unconditionally lands on the resolved (visible) style every render.
  const enter = (delay: number) => ({
    initial: reduce ? false : { opacity: 0, y: -8 },
    animate: { opacity: 1, y: 0 },
    transition: reduce ? { duration: 0 } : { duration: DURATION.text, ease: EASE_OUT, delay },
  })

  const [moreOpen, setMoreOpen] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const moreRef = useDismiss(moreOpen, () => setMoreOpen(false))
  const mobileRef = useDismiss(mobileOpen, () => setMobileOpen(false))

  const overflowActive = OVERFLOW.some((i) => isActive(pathname, i.href))

  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])
  // Close menus on route change.
  useEffect(() => {
    setMoreOpen(false)
    setMobileOpen(false)
  }, [pathname])

  return (
    <motion.header
      {...enter(0)}
      className="relative z-30 flex h-[72px] shrink-0 items-center gap-2 border-b border-border bg-surface/80 px-4 backdrop-blur-md"
    >
      {/* Brand */}
      <Link href="/dashboard" className="flex shrink-0 items-center gap-2.5 pr-2" aria-label="QuantHub — Dashboard">
        <BrandMark size={26} />
        <span className="hidden text-[15px] font-semibold tracking-tight text-fg sm:inline">
          Quant<span className="text-accent">Hub</span>
        </span>
      </Link>

      <div className="mx-1 hidden h-6 w-px bg-border lg:block" aria-hidden />

      {/* Primary nav (desktop) */}
      <motion.nav {...enter(0.1)} className="hidden items-center gap-0.5 lg:flex" aria-label="Primary navigation">
        {PRIMARY.map((item) => (
          <NavLink key={item.href} item={item} pathname={pathname} />
        ))}

        {/* Overflow "More" menu */}
        <div className="relative" ref={moreRef}>
          <button
            type="button"
            aria-haspopup="menu"
            aria-expanded={moreOpen}
            onClick={() => setMoreOpen((v) => !v)}
            className={cn(
              'flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-nav font-medium transition-colors duration-150',
              overflowActive || moreOpen
                ? 'bg-accent-soft text-accent'
                : 'text-fg-muted hover:bg-surface-hover hover:text-fg',
            )}
          >
            More
            <ChevronDown size={14} className={cn('transition-transform duration-150', moreOpen && 'rotate-180')} />
          </button>
          {moreOpen && (
            <div
              role="menu"
              className={cn(glassSurface('elevated'), 'absolute left-0 top-full mt-1.5 w-48 origin-top-left animate-scale-in p-1.5')}
            >
              {OVERFLOW.map((item) => {
                const active = isActive(pathname, item.href)
                const Icon = item.icon
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    role="menuitem"
                    aria-current={active ? 'page' : undefined}
                    className={cn(
                      'flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-nav transition-colors',
                      active ? 'bg-accent-soft text-accent' : 'text-fg-muted hover:bg-surface-hover hover:text-fg',
                    )}
                  >
                    <Icon size={16} className="shrink-0" />
                    {item.label}
                  </Link>
                )
              })}
            </div>
          )}
        </div>
      </motion.nav>

      {/* Mobile menu trigger (below lg) */}
      <div className="relative lg:hidden" ref={mobileRef}>
        <button
          type="button"
          aria-label="Open navigation menu"
          aria-haspopup="menu"
          aria-expanded={mobileOpen}
          onClick={() => setMobileOpen((v) => !v)}
          className="flex h-9 items-center gap-1.5 rounded-lg px-2.5 text-nav font-medium text-fg-muted transition-colors hover:bg-surface-hover hover:text-fg"
        >
          <Menu size={18} />
          <span className="hidden sm:inline">Menu</span>
        </button>
        {mobileOpen && (
          <div
            role="menu"
            className={cn(glassSurface('elevated'), 'absolute left-0 top-full mt-1.5 w-56 origin-top-left animate-scale-in p-1.5')}
          >
            {[...PRIMARY, ...OVERFLOW].map((item) => {
              const active = isActive(pathname, item.href)
              const Icon = item.icon
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  role="menuitem"
                  aria-current={active ? 'page' : undefined}
                  className={cn(
                    'flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-nav transition-colors',
                    active ? 'bg-accent-soft text-accent' : 'text-fg-muted hover:bg-surface-hover hover:text-fg',
                  )}
                >
                  <Icon size={16} className="shrink-0" />
                  {item.label}
                </Link>
              )
            })}
          </div>
        )}
      </div>

      {/* Right utilities */}
      <motion.div {...enter(0.18)} className="ml-auto flex items-center gap-1.5">
        {/* Global search — REAL functionality: opens the Ctrl+K command
            palette (Doc 13/05). No longer a styled placeholder. */}
        <button
          type="button"
          onClick={openCommandPalette}
          aria-label="Search (opens command palette)"
          className="hidden max-w-xs flex-1 items-center gap-2 rounded-lg border border-border/70 bg-surface-raised/60 py-2 pl-3 pr-2 text-left backdrop-blur-md transition-colors hover:border-border-strong/80 hover:bg-surface-hover/70 xl:flex"
        >
          <Search size={15} className="shrink-0 text-fg-subtle" />
          <span className="flex-1 truncate text-nav text-fg-subtle">Search…</span>
          <kbd className="shrink-0 rounded border border-border px-1.5 py-0.5 text-[11px] text-fg-subtle">⌘K</kbd>
        </button>

        <Tooltip content={mounted && theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}>
          <button
            type="button"
            aria-label="Toggle theme"
            onClick={toggleTheme}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-fg-muted transition-colors hover:bg-surface-hover hover:text-fg"
          >
            {mounted && theme === 'dark' ? <SunIcon /> : <MoonIcon />}
          </button>
        </Tooltip>

        {/* Notifications — honest placeholder (no notification pipeline; S-6).
            Fully glass-polished per Doc 09; the tooltip states its real,
            not-yet-wired state instead of a silent browser title attribute. */}
        <Tooltip content="Notifications — planned, no alert pipeline yet">
          <button
            type="button"
            aria-label="Notifications (coming soon)"
            className="relative flex h-8 w-8 items-center justify-center rounded-lg text-fg-muted transition-colors hover:bg-surface-hover hover:text-fg"
          >
            <Bell size={18} />
            <span aria-hidden className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-warning ring-2 ring-surface" />
          </button>
        </Tooltip>

        <div className="mx-1 h-6 w-px bg-border" aria-hidden />

        {/* User — honest placeholder (G-AUTH-1: single-user local, no real auth). */}
        <Tooltip content="Local operator — real accounts deferred">
          <button
            type="button"
            aria-label="Account (single-user local platform)"
            className="flex items-center gap-2 rounded-lg py-1 pl-1 pr-2 transition-colors hover:bg-surface-hover"
          >
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-accent to-info text-xs font-semibold text-accent-fg">
              QH
            </span>
            <span className="hidden text-nav font-medium text-fg-muted lg:inline">Operator</span>
          </button>
        </Tooltip>
      </motion.div>
    </motion.header>
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
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
    </svg>
  )
}
