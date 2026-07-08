// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout / §Data Visualization; §Interaction Standards.
// Doc 08 — Frontend Architecture (QH-008 v1.0) §Architecture / §State Management.
// Per Doc 00 §14.11
//
// REDESIGN + FEATURES (owner push):
//  - asset rows carry a real crypto icon + an inline price sparkline (not just
//    text + number);
//  - the candlestick chart gains a TIMEFRAME TOGGLE (1h / 4h / 1D). Only 1h is
//    ingested, so 4h/1D are HONESTLY DERIVED by client-side resampling of the
//    1h series (labeled "derived") — a real interactive choice from real data,
//    never fabricated bars;
//  - real BUY/SELL FILL MARKERS from the portfolio's filled orders for the
//    selected instrument are overlaid on the candles.
'use client'

import { useState } from 'react'
import { CandlestickChart } from 'lucide-react'
import {
  Badge,
  CryptoIcon,
  EmptyState,
  ErrorState,
  PageHeader,
  Section,
  Sparkline,
  StatCard,
} from '@/components/ui'
import { cn } from '@/lib/utils/cn'
import { usePortfolios } from '@/features/portfolio/hooks/usePortfolio'
import { useOrders } from '@/features/execution/hooks/useExecution'
import { useAssets, useBars } from '../hooks/useMarkets'
import type { Asset, OHLCVBar } from '../types'
import { PriceChart, type FillMarker } from './PriceChart'

const num = (v: string) => Number.parseFloat(v)
const fmtPrice = (v: string | number) =>
  Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const fmtVolume = (v: string | number) => Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 })
const fmtTime = (iso: string) =>
  new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })

// ── client-side timeframe resampling (honest: derived from the 1h series) ──
type Timeframe = '1h' | '4h' | '1D'
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
      high: String(Math.max(...highs)),
      low: String(Math.min(...lows)),
      close: g[g.length - 1].close,
      volume: String(vol),
    }
  })
}

export function MarketsShell() {
  const assetsQuery = useAssets()
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const assets = assetsQuery.data ?? []
  const activeId = selectedId ?? assets[0]?.id ?? ''
  const activeAsset = assets.find((a) => a.id === activeId) ?? null

  return (
    <div className="space-y-8">
      <PageHeader
        icon={<CandlestickChart size={18} />}
        title="Markets"
        subtitle="Live OHLCV market data — Phase 1 ingested bars."
      />

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[19rem_1fr]">
        <Section title="Instruments" actions={assetsQuery.isSuccess ? <Badge variant="neutral">{assets.length}</Badge> : null}>
          {assetsQuery.isLoading && <div className="skeleton h-40 w-full" />}
          {assetsQuery.isError && <ErrorState description="Could not load assets." onRetry={() => assetsQuery.refetch()} />}
          {assetsQuery.isSuccess && assets.length === 0 && (
            <EmptyState icon={<CandlestickChart size={20} />} title="No assets" description="No tradable assets are registered yet." />
          )}
          <div className="space-y-1">
            {assets.map((asset) => (
              <AssetRow key={asset.id} asset={asset} selected={asset.id === activeId} onSelect={() => setSelectedId(asset.id)} />
            ))}
          </div>
        </Section>

        <div className="min-w-0">
          {activeAsset ? (
            <AssetDetail asset={activeAsset} />
          ) : (
            !assetsQuery.isLoading &&
            !assetsQuery.isError && (
              <EmptyState icon={<CandlestickChart size={20} />} title="No asset selected" description="Select an instrument to view its chart." />
            )
          )}
        </div>
      </div>
    </div>
  )
}

function AssetRow({ asset, selected, onSelect }: { asset: Asset; selected: boolean; onSelect: () => void }) {
  const barsQuery = useBars(asset.id, '1h')
  const bars = barsQuery.data ?? []
  const closes = bars.slice(-24).map((b) => num(b.close))
  const last = bars.at(-1)
  const prev = bars.at(-2)
  const change = last && prev ? num(last.close) - num(prev.close) : null
  const changePct = change != null && prev ? (change / num(prev.close)) * 100 : null

  return (
    <button
      onClick={onSelect}
      aria-current={selected ? 'true' : undefined}
      className={cn(
        'flex w-full items-center gap-3 rounded-lg border px-3 py-2.5 text-left transition-colors duration-150',
        selected ? 'border-accent/40 bg-accent-soft' : 'border-transparent hover:bg-surface-hover',
      )}
    >
      <CryptoIcon symbol={asset.symbol} size={26} />
      <div className="min-w-0 flex-1">
        <div className={cn('truncate text-sm font-medium', selected ? 'text-accent' : 'text-fg')}>{asset.symbol}</div>
        <div className="text-[11px] uppercase tracking-wide text-fg-subtle">{asset.exchange}</div>
      </div>
      {closes.length > 1 && <Sparkline data={closes} width={64} height={24} />}
      <div className="text-right">
        {last ? (
          <>
            <div className="font-mono text-sm font-semibold tabular-nums text-fg">{fmtPrice(last.close)}</div>
            {changePct != null && (
              <div className={cn('font-mono text-[11px] tabular-nums', change! >= 0 ? 'text-profit' : 'text-risk')}>
                {change! >= 0 ? '+' : ''}{changePct.toFixed(2)}%
              </div>
            )}
          </>
        ) : (
          <span className="text-xs text-fg-subtle">…</span>
        )}
      </div>
    </button>
  )
}

function AssetDetail({ asset }: { asset: Asset }) {
  const [tf, setTf] = useState<Timeframe>('1h')
  const barsQuery = useBars(asset.id, '1h')
  const bars = barsQuery.data ?? []
  const view = resample(bars, tf)

  // Real fill markers: the first portfolio's FILLED orders for THIS instrument.
  const portfoliosQuery = usePortfolios()
  const portfolioId = portfoliosQuery.data?.[0]?.id ?? ''
  const ordersQuery = useOrders(portfolioId)
  const markers: FillMarker[] = (ordersQuery.data ?? [])
    .filter((o) => o.asset_id === asset.id && o.status === 'FILLED')
    .map((o) => ({ time: Math.floor(Date.parse(o.created_at) / 1000), side: o.side }))

  const last = bars.at(-1)
  const first24 = bars.slice(-24)
  const dayChange = last && first24[0] ? num(last.close) - num(first24[0].close) : null
  const dayChangePct = dayChange != null && first24[0] ? (dayChange / num(first24[0].close)) * 100 : null
  const hi = first24.length ? Math.max(...first24.map((b) => num(b.high))) : null
  const lo = first24.length ? Math.min(...first24.map((b) => num(b.low))) : null

  return (
    <div className="space-y-8">
      <Section
        title={`${asset.symbol} · price`}
        description={
          <span className="flex items-center gap-2">
            <span>{asset.exchange} · {tf}{tf !== '1h' && <span className="text-fg-subtle"> (derived)</span>}</span>
            {markers.length > 0 && (
              <span className="text-fg-subtle">· {markers.length} fills overlaid</span>
            )}
          </span>
        }
        actions={
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
        }
      >
        <div className="rounded-xl border border-border-strong bg-surface-raised p-4 shadow-lg">
          {barsQuery.isLoading && <div className="skeleton h-[420px] w-full" />}
          {barsQuery.isError && <ErrorState description="Could not load bars." onRetry={() => barsQuery.refetch()} />}
          {barsQuery.isSuccess && view.length === 0 && (
            <EmptyState title="No bars" description={`No bars ingested for ${asset.symbol} yet.`} />
          )}
          {barsQuery.isSuccess && view.length > 0 && (
            <>
              <div className="mb-3 flex items-center gap-4">
                {markers.length > 0 && (
                  <div className="flex items-center gap-3 text-[11px] text-fg-muted">
                    <span className="flex items-center gap-1"><span className="text-profit">▲</span> Buy fill</span>
                    <span className="flex items-center gap-1"><span className="text-risk">▼</span> Sell fill</span>
                  </div>
                )}
              </div>
              <PriceChart bars={view} markers={markers} />
            </>
          )}
        </div>
      </Section>

      {/* Stat strip fills the space that used to sit empty beside the table */}
      {last && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard label="Last price" value={fmtPrice(last.close)} />
          <StatCard
            label="24h change"
            value={dayChangePct != null ? `${dayChange! >= 0 ? '+' : ''}${dayChangePct.toFixed(2)}%` : '—'}
            tone={dayChange != null ? (dayChange >= 0 ? 'profit' : 'risk') : 'default'}
          />
          <StatCard label="24h high" value={hi != null ? fmtPrice(hi) : '—'} />
          <StatCard label="24h low" value={lo != null ? fmtPrice(lo) : '—'} />
        </div>
      )}

      {barsQuery.isSuccess && view.length > 0 && <RecentBars bars={view} tf={tf} />}
    </div>
  )
}

function RecentBars({ bars, tf }: { bars: OHLCVBar[]; tf: Timeframe }) {
  const recent = [...bars].reverse().slice(0, 15)
  return (
    <Section title="Recent bars" actions={<Badge variant="neutral">{bars.length} {tf} bars</Badge>}>
      <div className="overflow-hidden rounded-xl border border-border bg-surface-raised shadow-sm">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-[11px] uppercase tracking-wider text-fg-subtle">
              <th className="px-4 py-2.5 text-left font-semibold">Time</th>
              <th className="px-4 py-2.5 text-right font-semibold">Open</th>
              <th className="px-4 py-2.5 text-right font-semibold">High</th>
              <th className="px-4 py-2.5 text-right font-semibold">Low</th>
              <th className="px-4 py-2.5 text-right font-semibold">Close</th>
              <th className="px-4 py-2.5 text-right font-semibold">Volume</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/70">
            {recent.map((bar) => {
              const upBar = num(bar.close) >= num(bar.open)
              return (
                <tr key={bar.ts} className="transition-colors hover:bg-surface-hover/60">
                  <td className="px-4 py-2.5 text-fg-muted">{fmtTime(bar.ts)}</td>
                  <td className="px-4 py-2.5 text-right font-mono tabular-nums text-fg">{fmtPrice(bar.open)}</td>
                  <td className="px-4 py-2.5 text-right font-mono tabular-nums text-fg">{fmtPrice(bar.high)}</td>
                  <td className="px-4 py-2.5 text-right font-mono tabular-nums text-fg">{fmtPrice(bar.low)}</td>
                  <td className={cn('px-4 py-2.5 text-right font-mono tabular-nums', upBar ? 'text-profit' : 'text-risk')}>
                    {fmtPrice(bar.close)}
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono tabular-nums text-fg-muted">{fmtVolume(bar.volume)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </Section>
  )
}
