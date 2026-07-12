// Governing specification: handbook/ui/visual_engineering/13_VISUAL_DNA
//   (Command Palette listed as a core surface) and
//   05_GLASS_SURFACE_SYSTEM §Command Palette: "Must feel like a floating
//   operating system window. Use Strong glass, Blur, Premium elevation,
//   Smooth animation. Never resemble a standard dropdown."
// handbook/ui/01_UI_TECHNOLOGY_STANDARD §Component Library: shadcn/ui
//   (Radix primitives) is the FROZEN headless foundation — cmdk is the
//   library shadcn's own Command component wraps for the list/filter/
//   keyboard-navigation engine; Radix Dialog supplies the modal shell so
//   this stays visually identical to Modal.tsx's floating glass surface.
// Doc 00 §14.5/§14.7 DATA HONESTY: every result is a real strategy, real
//   asset, or a real route — no placeholder/fake entries.
// Per Doc 00 §14.11
'use client'

import { useEffect, useState } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { Command } from 'cmdk'
import { AnimatePresence, motion } from 'framer-motion'
import { useRouter } from 'next/navigation'
import { Brain, CandlestickChart, Search } from 'lucide-react'
import { cn } from '@/lib/utils/cn'
import { CARD_RADIUS } from './Card'
import { PRIMARY, OVERFLOW } from './TopBar'
import { useStrategies } from '@/features/strategies/hooks/useStrategies'
import { useAssets } from '@/features/markets/hooks/useMarkets'
import { useSyncStore } from '@/lib/store/sync'

// Module-level so any page can open the palette programmatically later
// (e.g. the TopBar search field) without prop-drilling — mirrors the
// Zustand pattern already used for cross-page selection sync.
let externalOpenSetter: ((open: boolean) => void) | null = null
export function openCommandPalette() {
  externalOpenSetter?.(true)
}

export function CommandPalette() {
  const [open, setOpen] = useState(false)
  const router = useRouter()
  const setSelectedStrategyId = useSyncStore((s) => s.setSelectedStrategyId)
  const setSelectedAssetSymbol = useSyncStore((s) => s.setSelectedAssetSymbol)

  // Real data only (Doc 00 §14.5) — the same registry/asset hooks every
  // other page reads from, no dedicated search endpoint invented.
  const strategiesQuery = useStrategies()
  const assetsQuery = useAssets()

  useEffect(() => {
    externalOpenSetter = setOpen
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setOpen((v) => !v)
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      externalOpenSetter = null
    }
  }, [])

  const go = (fn: () => void) => {
    fn()
    setOpen(false)
  }

  const strategies = strategiesQuery.data ?? []
  const assets = assetsQuery.data ?? []
  const pages = [...PRIMARY, ...OVERFLOW]

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <AnimatePresence>
        {open && (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild forceMount>
              <motion.div
                className="fixed inset-0 z-50 bg-bg/70 backdrop-blur-sm"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15, ease: 'easeOut' }}
              />
            </Dialog.Overlay>
            <div className="fixed inset-0 z-50 flex items-start justify-center px-4 pt-[15vh]">
              <Dialog.Content asChild forceMount>
                <motion.div
                  className={cn(
                    'relative w-full max-w-xl overflow-hidden border border-border/[0.1] bg-surface-raised/85 shadow-glow backdrop-blur-2xl',
                    CARD_RADIUS,
                  )}
                  initial={{ opacity: 0, scale: 0.96, y: -8 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.97, y: -4 }}
                  transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
                >
                  <Dialog.Title className="sr-only">Command palette</Dialog.Title>
                  <Dialog.Description className="sr-only">
                    Search strategies, assets, and pages across QuantHub
                  </Dialog.Description>
                  <Command shouldFilter loop label="Command palette" className="qh-command flex flex-col">
                    <div className="flex items-center gap-2.5 border-b border-border px-4">
                      <Search size={16} className="shrink-0 text-fg-subtle" />
                      <Command.Input
                        autoFocus
                        placeholder="Search strategies, assets, pages…"
                        className="h-12 flex-1 bg-transparent text-body text-fg outline-none placeholder:text-fg-subtle"
                      />
                      <kbd className="shrink-0 rounded border border-border px-1.5 py-0.5 text-[11px] text-fg-subtle">
                        Esc
                      </kbd>
                    </div>
                    <Command.List className="qh-scroll max-h-[60vh] overflow-y-auto p-2">
                      <Command.Empty className="px-3 py-8 text-center text-caption text-fg-subtle">
                        No results.
                      </Command.Empty>

                      <Command.Group heading="Pages">
                        {pages.map((p) => {
                          const Icon = p.icon
                          return (
                            <Command.Item
                              key={p.href}
                              value={p.label}
                              onSelect={() => go(() => router.push(p.href))}
                              className="flex items-center gap-2.5 px-3 py-2 text-body text-fg"
                            >
                              <Icon size={15} className="shrink-0 text-fg-muted" />
                              {p.label}
                            </Command.Item>
                          )
                        })}
                      </Command.Group>

                      {strategies.length > 0 && (
                        <Command.Group heading="Strategies">
                          {strategies.map((s) => (
                            <Command.Item
                              key={s.id}
                              value={`${s.name} strategy`}
                              onSelect={() =>
                                go(() => {
                                  setSelectedStrategyId(s.id)
                                  router.push(`/strategies/${s.id}`)
                                })
                              }
                              className="flex items-center gap-2.5 px-3 py-2 text-body text-fg"
                            >
                              <Brain size={15} className="shrink-0 text-fg-muted" />
                              <span className="flex-1 truncate">{s.name}</span>
                              <span className="shrink-0 text-caption text-fg-subtle">{s.status}</span>
                            </Command.Item>
                          ))}
                        </Command.Group>
                      )}

                      {assets.length > 0 && (
                        <Command.Group heading="Assets">
                          {assets.map((a) => (
                            <Command.Item
                              key={a.id}
                              value={`${a.symbol} asset`}
                              onSelect={() =>
                                go(() => {
                                  setSelectedAssetSymbol(a.symbol)
                                  router.push('/markets')
                                })
                              }
                              className="flex items-center gap-2.5 px-3 py-2 text-body text-fg"
                            >
                              <CandlestickChart size={15} className="shrink-0 text-fg-muted" />
                              <span className="flex-1 truncate">{a.symbol}</span>
                              <span className="shrink-0 text-caption text-fg-subtle">{a.exchange}</span>
                            </Command.Item>
                          ))}
                        </Command.Group>
                      )}
                    </Command.List>
                  </Command>
                </motion.div>
              </Dialog.Content>
            </div>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  )
}
