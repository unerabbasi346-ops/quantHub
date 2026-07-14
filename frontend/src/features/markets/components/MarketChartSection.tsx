// Governing specification: handbook/ui/visual_engineering/13_VISUAL_DNA —
//   Image 4 (EchoFi) layout: full-width dominant chart, decorative tool
//   column for visual depth, dense right stats panel. Doc 11 §Grid: 4-6%
//   opacity (already enforced inside PriceChart's chartAxis/grid options).
// Doc 00 §14.5/§14.7 DATA HONESTY: every stat below is a real computed value
//   from ingested bars/funding rows; funding is shown ONLY for PERPETUAL
//   instruments (a SPOT asset has no funding concept, so the row is omitted
//   entirely rather than shown empty).
'use client'

import { useEffect, useRef, useState } from 'react'
import {
  Check,
  ChevronDown,
  Crosshair,
  Layers,
  ZoomIn,
} from 'lucide-react'
import { Badge, CryptoIcon, EmptyState, ErrorState, Panel } from '@/components/ui'
import { cn } from '@/lib/utils/cn'
import { formatRate, formatReturn } from '@/lib/utils/format'
import { computeDayChange, num } from '../analytics'
import type { Asset, FundingRate, OHLCVBar } from '../types'
import { PriceChart, type FillMarker } from './PriceChart'

const fmtPrice = (v: number) => v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const fmtVolume = (v: number) => v.toLocaleString(undefined, { maximumFractionDigits: 2 })

export type Timeframe = '1h' | '4h' | '1D'
const TIMEFRAMES: Timeframe[] = ['1h', '4h', '1D']

// Purely decorative depth column (owner request) — no functionality wired
// yet, so each icon is inert (no onClick), never implying a feature that
// doesn't exist.
function ToolColumn() {
  return (
    <div className="flex w-8 shrink-0 flex-col items-center gap-4 pt-2">
      {[Crosshair, ZoomIn, Layers].map((Icon, i) => (
        <span key={i} className="flex h-7 w-7 items-center justify-center rounded-md text-fg-subtle/60">
          <Icon size={15} />
        </span>
      ))}
    </div>
  )
}

function AssetDropdown({ assets, active, onSelect }: { assets: Asset[]; active: Asset; onSelect: (a: Asset) => void }) {
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
        <CryptoIcon symbol={active.symbol} size={18} />
        <span className="font-medium text-fg">{active.symbol}</span>
        <ChevronDown size={14} className={cn('text-fg-subtle transition-transform', open && 'rotate-180')} />
      </button>
      {open && (
        <div className="absolute left-0 top-full z-30 mt-1.5 max-h-72 w-56 overflow-y-auto rounded-xl border border-border bg-surface-raised p-1.5 shadow-lg qh-scroll">
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
                a.id === active.id ? 'bg-accent-soft text-accent' : 'text-fg-muted hover:bg-surface-hover hover:text-fg',
              )}
            >
              <CryptoIcon symbol={a.symbol} size={16} />
              <span className="min-w-0 flex-1 truncate">{a.symbol}</span>
              {a.id === active.id && <Check size={14} className="shrink-0" />}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export function MarketChartSection({
  asset,
  assets,
  onSelectAsset,
  tf,
  setTf,
  bars,
  barsLoading,
  barsError,
  onRetry,
  markers,
  latestFunding,
}: {
  asset: Asset
  assets: Asset[]
  onSelectAsset: (a: Asset) => void
  tf: Timeframe
  setTf: (t: Timeframe) => void
  bars: OHLCVBar[]
  barsLoading: boolean
  barsError: boolean
  onRetry: () => void
  markers: FillMarker[]
  latestFunding: FundingRate | null
}) {
  const dc = computeDayChange(bars)
  const isPerp = asset.instrument_type === 'PERPETUAL'
  const fundingRate = latestFunding ? num(latestFunding.funding_rate) : null
  // Positive funding = longs pay shorts = bearish signal -> risk red;
  // negative = shorts pay longs = bullish -> profit green (task spec).
  const fundingTone = fundingRate == null ? null : fundingRate >= 0 ? 'risk' : 'profit'

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[2fr_16rem]">
      <Panel className="flex gap-2 p-4" elevation="elevated">
        <ToolColumn />
        <div className="min-w-0 flex-1">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <AssetDropdown assets={assets} active={asset} onSelect={onSelectAsset} />
            <div className="flex items-center gap-1 rounded-lg border border-border bg-surface-raised p-0.5">
              {TIMEFRAMES.map((t) => (
                <button
                  key={t}
                  onClick={() => setTf(t)}
                  className={cn(
                    'rounded-md px-2.5 py-1 text-xs font-medium transition-colors',
                    tf === t ? 'bg-accent text-accent-fg' : 'text-fg-muted hover:text-fg',
                  )}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          {barsLoading && <div className="skeleton h-[420px] w-full" />}
          {barsError && <ErrorState description="Could not load bars." onRetry={onRetry} />}
          {!barsLoading && !barsError && bars.length === 0 && (
            <EmptyState title="No bars" description={`No bars ingested for ${asset.symbol} yet.`} />
          )}
          {!barsLoading && !barsError && bars.length > 0 && (
            <>
              {markers.length > 0 && (
                <div className="mb-2 flex items-center gap-3 text-[11px] text-fg-muted">
                  <span className="flex items-center gap-1"><span className="text-profit">▲</span> Buy fill</span>
                  <span className="flex items-center gap-1"><span className="text-risk">▼</span> Sell fill</span>
                  <span className="text-fg-subtle">· {markers.length} overlaid · hover for implied sizing</span>
                </div>
              )}
              <PriceChart bars={bars} markers={markers} />
            </>
          )}
        </div>
      </Panel>

      {/* Right stats panel */}
      <Panel className="space-y-4 p-5">
        {dc ? (
          <>
            <div>
              <div className="text-[11px] uppercase tracking-wide text-fg-subtle">{asset.symbol}</div>
              <div className={cn('mt-1 font-mono text-2xl font-bold tabular-nums', dc.change >= 0 ? 'text-profit' : 'text-risk')}>
                {fmtPrice(dc.last)}
              </div>
              <div className={cn('font-mono text-sm tabular-nums', dc.change >= 0 ? 'text-profit' : 'text-risk')}>
                {formatReturn(dc.changePct / 100)} · 24h
              </div>
            </div>

            <div className="space-y-1.5 border-t border-border pt-3">
              <div className="flex items-center justify-between text-xs">
                <span className="text-fg-subtle">24h low</span>
                <span className="text-fg-subtle">24h high</span>
              </div>
              <div className="relative h-1.5 w-full rounded-full bg-surface">
                <div
                  className="absolute inset-y-0 rounded-full bg-accent/50"
                  style={{
                    left: '0%',
                    width: dc.high > dc.low ? `${Math.min(100, Math.max(0, ((dc.last - dc.low) / (dc.high - dc.low)) * 100))}%` : '100%',
                  }}
                />
              </div>
              <div className="flex items-center justify-between font-mono text-xs tabular-nums text-fg">
                <span>{fmtPrice(dc.low)}</span>
                <span>{fmtPrice(dc.high)}</span>
              </div>
            </div>

            <div className="flex items-center justify-between border-t border-border pt-3 text-sm">
              <span className="text-fg-subtle">24h volume</span>
              <span className="font-mono text-fg">{fmtVolume(dc.volume)}</span>
            </div>

            {isPerp && (
              <div className="flex items-center justify-between border-t border-border pt-3 text-sm">
                <span className="text-fg-subtle">Funding rate</span>
                {fundingRate != null ? (
                  <span className={cn('font-mono', fundingTone === 'risk' ? 'text-risk' : 'text-profit')}>
                    {formatRate(fundingRate)}
                  </span>
                ) : (
                  <Badge variant="neutral">no data</Badge>
                )}
              </div>
            )}
          </>
        ) : (
          <div className="flex h-40 items-center justify-center text-sm text-fg-muted">Not enough bars yet.</div>
        )}
      </Panel>
    </div>
  )
}
