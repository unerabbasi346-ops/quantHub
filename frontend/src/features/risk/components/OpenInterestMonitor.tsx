// Governing specification: Doc 14 §10.9.5 Financing Costs anchor (shared
//   with funding); migration b4f8e21ac9d3 (market_data.open_interest). Doc 00
//   §14.5/§14.7 DATA HONESTY: OI is real (just ingested); price is the
//   corresponding SPOT instrument's real bars, since NO perpetual asset
//   currently has its own OHLCV history ingested (verified live) — labeled
//   explicitly rather than silently conflating the two instruments.
'use client'

import { useEffect, useRef, useState } from 'react'
import { Check, ChevronDown, Info, TrendingUp } from 'lucide-react'
import { Badge, EmptyState, ErrorState, Panel, Section } from '@/components/ui'
import { cn } from '@/lib/utils/cn'
import { useAssets, useBars, useOpenInterest } from '@/features/markets/hooks/useMarkets'
import type { Asset } from '@/features/markets/types'
import type { Position } from '@/features/portfolio/types'
import { computeOiDivergence } from '../analytics'
import { OpenInterestPriceChart } from './charts'

function spotSymbolFor(perpSymbol: string): string {
  // ccxt perpetual convention: "BASE/QUOTE:SETTLE" -> spot "BASE/QUOTE".
  return perpSymbol.split(':')[0]
}

function AssetDropdown({ assets, active, onSelect }: { assets: Asset[]; active: Asset | null; onSelect: (a: Asset) => void }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open) return
    const onClick = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false)
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [open])

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded-lg border border-border bg-surface-raised/50 px-2.5 py-1.5 text-sm hover:border-border-strong"
      >
        <span className="font-medium text-fg">{active?.symbol ?? 'Select…'}</span>
        <ChevronDown size={14} className={cn('text-fg-subtle transition-transform', open && 'rotate-180')} />
      </button>
      {open && (
        <div className="absolute right-0 top-full z-50 mt-1.5 max-h-72 w-56 overflow-y-auto rounded-xl border border-border bg-surface-raised p-1.5 shadow-lg qh-scroll">
          {assets.map((a) => (
            <button
              key={a.id}
              type="button"
              onClick={() => {
                onSelect(a)
                setOpen(false)
              }}
              className={cn(
                'flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-sm transition-colors',
                a.id === active?.id ? 'bg-accent-soft text-accent' : 'text-fg-muted hover:bg-surface-hover hover:text-fg',
              )}
            >
              <span className="min-w-0 flex-1 truncate">{a.symbol}</span>
              {a.id === active?.id && <Check size={14} className="shrink-0" />}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export function OpenInterestMonitor({ positions }: { positions: Position[] }) {
  const assetsQuery = useAssets()
  const assets = assetsQuery.data ?? []
  const perpetuals = assets.filter((a) => a.instrument_type === 'PERPETUAL')

  // Default to the selected strategy's own perpetual exposure, if it holds
  // one — this is what makes the section actually react to the strategy
  // selector instead of always opening on BTC regardless of what's active.
  // Falls back to BTC/USDT:USDT (then any perpetual) when the portfolio
  // holds no perpetual position, so the section is never empty by default.
  // The dropdown still lets the user browse any other perpetual manually.
  const heldPerpAssetId = positions.find((p) => !p.is_closed && perpetuals.some((a) => a.id === p.asset_id))?.asset_id
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const active = perpetuals.find((a) => a.id === selectedId)
    ?? perpetuals.find((a) => a.id === heldPerpAssetId)
    ?? perpetuals.find((a) => a.symbol === 'BTC/USDT:USDT')
    ?? perpetuals[0]
    ?? null

  const oiQuery = useOpenInterest(active?.id ?? '', Boolean(active))
  const oiRows = oiQuery.data ?? []

  const spotSymbol = active ? spotSymbolFor(active.symbol) : null
  const spotAsset = spotSymbol ? assets.find((a) => a.symbol === spotSymbol) : undefined
  const barsQuery = useBars(spotAsset?.id ?? '', '1h', 500)
  const bars = barsQuery.data ?? []
  const priceSeries = bars.map((b) => ({ ts: b.ts, close: Number.parseFloat(b.close) }))

  const divergence = oiRows.length > 1 && bars.length > 1 ? computeOiDivergence(oiRows, bars) : []
  const bullishCount = divergence.filter((d) => d.signal === 'bullish').length
  const bearishCount = divergence.filter((d) => d.signal === 'bearish').length

  return (
    <Section
      icon={<TrendingUp size={16} />}
      title="Open interest vs price"
      description={
        <span className="flex items-center gap-1.5">
          <Info size={12} className="shrink-0" />
          OI rising with price = bullish confirmation (green); OI rising with price falling = bearish confirmation (red).
        </span>
      }
      actions={
        <div className="flex items-center gap-2">
          {(bullishCount > 0 || bearishCount > 0) && (
            <>
              {bullishCount > 0 && <Badge variant="profit">{bullishCount} bullish</Badge>}
              {bearishCount > 0 && <Badge variant="risk">{bearishCount} bearish</Badge>}
            </>
          )}
          {perpetuals.length > 0 && <AssetDropdown assets={perpetuals} active={active} onSelect={(a) => setSelectedId(a.id)} />}
        </div>
      }
    >
      <Panel className="p-4">
        {assetsQuery.isLoading || oiQuery.isLoading ? (
          <div className="skeleton h-[360px] w-full" />
        ) : oiQuery.isError ? (
          <ErrorState description="Could not load open interest." onRetry={() => oiQuery.refetch()} />
        ) : !active ? (
          <EmptyState title="No perpetual instruments" description="No PERPETUAL assets are registered yet." />
        ) : (
          <>
            {spotAsset && (
              <p className="mb-1 text-[11px] text-fg-subtle">
                Price from <span className="font-mono text-fg-muted">{spotAsset.symbol}</span> (spot) — no bars are ingested for the perpetual instrument itself.
              </p>
            )}
            {oiRows.length > 1 && bars.length > 1 && divergence.length === 0 && (
              <p className="mb-3 text-[11px] text-fg-subtle">
                No divergence signals in this window — OI and price history don&apos;t currently overlap closely enough to compare (real data, not a bug).
              </p>
            )}
            <OpenInterestPriceChart oiRows={oiRows} priceSeries={priceSeries} divergence={divergence} height={360} />
          </>
        )}
      </Panel>
    </Section>
  )
}
