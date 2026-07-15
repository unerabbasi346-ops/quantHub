// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout / §Data Visualization; §Interaction Standards.
// Doc 08 — Frontend Architecture (QH-008 v1.0) §Architecture / §State Management.
// handbook/ui/visual_engineering/13_VISUAL_DNA — Image 4 (EchoFi)/Image 3
//   (Voltrex) visual standard. Per Doc 00 §14.11
//
// DENSE MARKETS REBUILD (owner request) — four sections:
//  1. Horizontally scrolling real-data asset pill strip (Voltrex-style).
//  2. Full-width primary candlestick chart (TradingView Lightweight Charts,
//     kept) + volume + real BUY/SELL fill markers (now showing each fill's
//     implied direction/size/leverage from the real signals API) + a right
//     stats panel (price/24h range/volume/funding for perpetuals).
//  3. Three-column analytics grid: correlation matrix (existing, reused),
//     volume ranking, 24h performance ranking — all real, computed client-side.
//  4. Two-column market intelligence: funding-rate history (perpetuals only,
//     honest disclosure for spot) + a computed price-statistics panel
//     (replaces the old Recent Bars table).
'use client'

import { useMemo, useState } from 'react'
import { useQueries } from '@tanstack/react-query'
import { CandlestickChart } from 'lucide-react'
import { PageHeader } from '@/components/ui'
import { useSyncStore } from '@/lib/store/sync'
import { usePortfolios } from '@/features/portfolio/hooks/usePortfolio'
import { useOrders } from '@/features/execution/hooks/useExecution'
import { useStrategies } from '@/features/strategies/hooks/useStrategies'
import { strategiesService } from '@/features/strategies/services/strategies.service'
import type { Signal } from '@/features/strategies/types'
import { computePriceStats, mergeLatestBar, num, rankByPerformance, rankByVolume } from '../analytics'
import { useAllBars, useAssets, useBars, useFundingRates, useLatestBar } from '../hooks/useMarkets'
import type { Asset, OHLCVBar } from '../types'
import type { FillMarker } from './PriceChart'
import { AssetStatsStrip } from './AssetStatsStrip'
import { MarketChartSection, type Timeframe } from './MarketChartSection'
import { AnalyticsGrid } from './AnalyticsGrid'
import { MarketIntelligence } from './MarketIntelligence'

// Signal history depth for the marker-tooltip join — enough to cover any
// order placed against a strategy's real signal history (mirrors the
// Strategy detail workspace's own SIGNAL_HISTORY_LIMIT).
const SIGNAL_HISTORY_LIMIT = 1000
// Wide bar window for the selected asset's price-statistics panel (30-day
// return needs ~720 hourly bars; the backend caps at 1000).
const PRICE_STATS_BAR_LIMIT = 1000

// ── client-side timeframe resampling (honest: derived from the 1h series) ──
const TIMEFRAMES: Timeframe[] = ['1h', '4h', '1D']

function bucketKey(tf: Timeframe, ts: string): string {
  const d = new Date(ts)
  if (tf === '1D') return d.toISOString().slice(0, 10)
  const hours = Math.floor(d.getTime() / 3_600_000)
  return String(tf === '4h' ? Math.floor(hours / 4) : hours)
}

function resample(bars: OHLCVBar[], tf: Timeframe): OHLCVBar[] {
  if (tf === '1h') return bars
  const groups = new Map<string, OHLCVBar[]>()
  for (const b of bars) {
    const k = bucketKey(tf, b.ts)
    const g = groups.get(k)
    if (g) g.push(b)
    else groups.set(k, [b])
  }
  return [...groups.values()].map((g) => {
    const highs = g.map((b) => num(b.high))
    const lows = g.map((b) => num(b.low))
    const vol = g.reduce((s, b) => s + num(b.volume), 0)
    return {
      ...g[0],
      interval: tf,
      open: g[0].open,
      high: String(highs.reduce((a, b) => Math.max(a, b), -Infinity)),
      low: String(lows.reduce((a, b) => Math.min(a, b), Infinity)),
      close: g[g.length - 1].close,
      volume: String(vol),
    }
  })
}

// Every strategy's real signal history, keyed by signal id — the join table
// for marker tooltips (order.signal_id -> direction/implied_size_usdt/
// implied_leverage). Small platform (a handful of strategies), so fetching
// each strategy's full signal feed is proportionate. Uses useQueries (a
// SINGLE hook call over an array of query configs) rather than calling
// useSignals per-strategy in a loop — the latter would violate the Rules of
// Hooks the moment the strategy count changes between renders (e.g. while
// useStrategies is still loading) — the same pattern already established in
// features/strategies/hooks/useStrategyPerformance.ts.
function useSignalsById(): Map<string, Signal> {
  const strategiesQuery = useStrategies()
  const strategies = strategiesQuery.data ?? []
  const signalQueries = useQueries({
    queries: strategies.map((s) => ({
      queryKey: ['signals', s.id, SIGNAL_HISTORY_LIMIT],
      queryFn: () => strategiesService.getSignals(s.id, SIGNAL_HISTORY_LIMIT),
      enabled: Boolean(s.id),
    })),
  })
  return useMemo(() => {
    const map = new Map<string, Signal>()
    for (const q of signalQueries) {
      for (const s of q.data ?? []) map.set(s.id, s)
    }
    return map
  }, [signalQueries])
}

export function MarketsShell() {
  const assetsQuery = useAssets()
  const assets = useMemo(() => assetsQuery.data ?? [], [assetsQuery.data])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [tf, setTf] = useState<Timeframe>('1h')

  // Global Synchronization (Doc 11): an asset selected elsewhere (Dashboard
  // Hero) is the default instrument this page opens on.
  const syncedSymbol = useSyncStore((s) => s.selectedAssetSymbol)
  const setSyncedSymbol = useSyncStore((s) => s.setSelectedAssetSymbol)

  const syncedId = syncedSymbol ? assets.find((a) => a.symbol === syncedSymbol)?.id : undefined

  const selectAsset = (asset: Asset) => {
    setSelectedId(asset.id)
    setSyncedSymbol(asset.symbol)
  }

  // Every asset's 1h bars in one batch (Section 1 pill strip, Section 3
  // rankings) — the selected asset's chart reads the SAME cached query
  // (identical key), so this is not a duplicate fetch for the active asset.
  const allBarsQueries = useAllBars(assets, '1h')
  const barsByAssetId = useMemo(() => {
    const map = new Map<string, OHLCVBar[]>()
    assets.forEach((a, i) => map.set(a.id, allBarsQueries[i]?.data ?? []))
    return map
  }, [assets, allBarsQueries])

  // Default selection prefers the first asset that actually HAS ingested
  // bars (some registered instruments have no OHLCV history yet) — falls
  // back to assets[0] while bars are still loading, then self-corrects once
  // real data arrives. Never silently picks a data-less instrument once a
  // real one is known to exist.
  const firstAssetWithBars = assets.find((a) => (barsByAssetId.get(a.id)?.length ?? 0) > 0)?.id
  const activeId = selectedId ?? syncedId ?? firstAssetWithBars ?? assets[0]?.id ?? ''
  const activeAsset = assets.find((a) => a.id === activeId) ?? null

  // The pill strip only makes sense for instruments that actually have
  // ingested history — a dead ticker with zero bars can't show a price or
  // change, so it's excluded from the strip rather than shown as a
  // permanent "…" placeholder.
  const assetsWithBars = useMemo(
    () => assets.filter((a) => (barsByAssetId.get(a.id)?.length ?? 0) > 0),
    [assets, barsByAssetId],
  )

  const activeBars = barsByAssetId.get(activeId) ?? []

  // Live-updating chart (owner request) — polls the single most-recent 1h
  // bar every 30s and folds it into the raw series before resampling, so
  // 4h/1D views pick it up too. Restricted to instruments CCXT can actually
  // quote live: binance-sourced SPOT/PERPETUAL (excludes the "sim" REGTEST
  // asset, which has no real exchange behind it).
  const canGoLive = activeAsset?.exchange === 'binance'
    && (activeAsset.instrument_type === 'SPOT' || activeAsset.instrument_type === 'PERPETUAL')
  const latestBarQuery = useLatestBar(activeId, '1h', Boolean(canGoLive))
  const liveBars = useMemo(
    () => mergeLatestBar(activeBars, latestBarQuery.data ?? null),
    [activeBars, latestBarQuery.data],
  )
  const view = resample(liveBars, tf)
  const activeBarsQueryIndex = assets.findIndex((a) => a.id === activeId)
  const activeBarsQuery = activeBarsQueryIndex >= 0 ? allBarsQueries[activeBarsQueryIndex] : undefined

  const volumeRanking = useMemo(
    () => rankByVolume(assets.map((a) => ({ assetId: a.id, symbol: a.symbol, bars: barsByAssetId.get(a.id) ?? [] }))),
    [assets, barsByAssetId],
  )
  const performanceRanking = useMemo(
    () => rankByPerformance(assets.map((a) => ({ assetId: a.id, symbol: a.symbol, bars: barsByAssetId.get(a.id) ?? [] }))),
    [assets, barsByAssetId],
  )

  // Funding rates — only meaningful for PERPETUAL; the hook itself gates the
  // network call on this so a SPOT selection never fires it.
  const isPerp = activeAsset?.instrument_type === 'PERPETUAL'
  const fundingQuery = useFundingRates(activeId, Boolean(isPerp))

  // Wider bar window for the price-statistics panel (30d return needs ~720
  // hourly bars — the default 500-bar cache doesn't cover it).
  const priceStatsBarsQuery = useBars(activeId, '1h', PRICE_STATS_BAR_LIMIT)
  const priceStats = useMemo(() => computePriceStats(priceStatsBarsQuery.data ?? []), [priceStatsBarsQuery.data])

  // Real fill markers, enriched with the real implied-sizing fields from the
  // signal that produced each fill (order.signal_id -> Signal). An order with
  // no signal_id (manually placed) or an unresolved signal_id simply omits
  // those fields — never a fabricated value.
  const signalsById = useSignalsById()
  const portfoliosQuery = usePortfolios()
  const portfolioId = portfoliosQuery.data?.[0]?.id ?? ''
  const ordersQuery = useOrders(portfolioId)
  const markers: FillMarker[] = (ordersQuery.data ?? [])
    .filter((o) => o.asset_id === activeId && o.status === 'FILLED')
    .map((o) => {
      const signal = o.signal_id ? signalsById.get(o.signal_id) : undefined
      return {
        time: Math.floor(Date.parse(o.created_at) / 1000),
        side: o.side,
        direction: signal?.direction,
        impliedSizeUsdt: signal?.implied_size_usdt,
        impliedLeverage: signal?.implied_leverage,
      }
    })

  const latestFunding = fundingQuery.data?.at(-1) ?? null

  return (
    <div className="space-y-8">
      <PageHeader
        icon={<CandlestickChart size={18} />}
        title="Markets"
        subtitle="Live OHLCV market data, cross-asset analytics, and perpetual funding — Phase 1/S-10 ingested data."
      />

      {assetsQuery.isLoading && <div className="skeleton h-16 w-full rounded-full" />}
      {assetsQuery.isError && <div className="text-sm text-risk">Could not load assets.</div>}

      {activeAsset && (
        <>
          <AssetStatsStrip assets={assetsWithBars} barsByAssetId={barsByAssetId} selectedId={activeId} onSelect={selectAsset} />

          <MarketChartSection
            asset={activeAsset}
            assets={assets}
            onSelectAsset={selectAsset}
            tf={tf}
            setTf={setTf}
            bars={view}
            barsLoading={Boolean(activeBarsQuery?.isLoading)}
            barsError={Boolean(activeBarsQuery?.isError)}
            onRetry={() => activeBarsQuery?.refetch()}
            markers={markers}
            latestFunding={latestFunding}
          />

          <AnalyticsGrid volumeRanking={volumeRanking} performanceRanking={performanceRanking} selectedAssetId={activeId} />

          <MarketIntelligence
            asset={activeAsset}
            fundingRates={fundingQuery.data ?? []}
            fundingLoading={Boolean(isPerp) && fundingQuery.isLoading}
            fundingError={Boolean(isPerp) && fundingQuery.isError}
            onRetryFunding={() => fundingQuery.refetch()}
            priceStats={priceStats}
            barCount={priceStatsBarsQuery.data?.length ?? 0}
          />
        </>
      )}
    </div>
  )
}
