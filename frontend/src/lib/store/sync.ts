// Governing specification: handbook/ui/11_GLOBAL_UI_SYSTEM §GLOBAL
//   SYNCHRONIZATION: "This is mandatory. Every workspace SHALL remain
//   synchronized. Selecting Strategy updates Dashboard, Portfolio,
//   Execution, Risk, Market, Backtest, Signals. Selecting Asset updates
//   every page. ... No manual refresh. No inconsistent state."
//
// SCOPE (read the spec's intent, don't guess past it): QuantHub is a
// client-routed SPA — only one page is ever mounted at a time, so "every
// workspace remains synchronized" cannot mean simultaneous live updates on
// unmounted pages. The buildable reading is a single shared selection that
// survives navigation: whichever Strategy/Asset the operator selected on
// one page becomes the DEFAULT scope the next page opens with, instead of
// each page independently defaulting to "first item in the list." Zustand
// state already survives client-side route changes without a reload, which
// satisfies "No manual refresh. No inconsistent state" directly — no
// persistence layer is needed for that guarantee.
//
// Only Strategy and Asset are wired here. The spec also names Trade and
// Time: this codebase has no cross-page "Trade" entity distinct from an
// Order, and no shared timeframe control outside the Markets page's own
// local toggle — wiring sync for either would mean inventing a data concept
// that doesn't exist, which Doc 00's data-honesty principle rules out.
// Flagged as a known gap, not silently skipped.
import { create } from 'zustand'

interface SyncState {
  selectedStrategyId: string | null
  setSelectedStrategyId: (id: string | null) => void

  selectedAssetSymbol: string | null
  setSelectedAssetSymbol: (symbol: string | null) => void
}

export const useSyncStore = create<SyncState>((set) => ({
  selectedStrategyId: null,
  setSelectedStrategyId: (id) => set({ selectedStrategyId: id }),

  selectedAssetSymbol: null,
  setSelectedAssetSymbol: (symbol) => set({ selectedAssetSymbol: symbol }),
}))
