// Governing specification: Doc 14 §10.9.5 (Financing Costs) — funding rate
//   history for PERPETUAL instruments only; a SPOT asset shown here gets an
//   honest disclosure, never an empty/misleading funding chart. Doc 00
//   §14.5/§14.7 DATA HONESTY: price statistics are computed client-side from
//   already-fetched real bars — no new endpoints, nothing fabricated.
'use client'

import { Info, Sigma } from 'lucide-react'
import { Badge, EmptyState, ErrorState, Panel, Section, type BadgeVariant } from '@/components/ui'
import { cn } from '@/lib/utils/cn'
import { formatRatio, formatReturn, formatVolatility } from '@/lib/utils/format'
import { fmtCompactVolume, momentumZone, type PriceStats } from '../analytics'
import type { Asset, FundingRate } from '../types'
import { FundingRateHistoryChart } from './charts'

const MOMENTUM_LABEL: Record<ReturnType<typeof momentumZone>, string> = {
  oversold: 'Oversold',
  neutral: 'Neutral',
  overbought: 'Overbought',
}
const MOMENTUM_VARIANT: Record<ReturnType<typeof momentumZone>, BadgeVariant> = {
  oversold: 'profit',
  neutral: 'neutral',
  overbought: 'risk',
}

function volatilityTone(pct: number): 'profit' | 'warning' | 'risk' {
  if (pct < 30) return 'profit'
  if (pct <= 60) return 'warning'
  return 'risk'
}

const fmtPrice = (v: number) => v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })

function FundingRateHistory({
  asset,
  rates,
  loading,
  error,
  onRetry,
}: {
  asset: Asset
  rates: FundingRate[]
  loading: boolean
  error: boolean
  onRetry: () => void
}) {
  const isPerp = asset.instrument_type === 'PERPETUAL'

  return (
    <Section icon={<Sigma size={16} />} title="Funding rate history" description="Positive = longs pay (bearish); negative = shorts pay (bullish).">
      <Panel className="p-4">
        {!isPerp ? (
          <div className="flex h-[260px] flex-col items-center justify-center gap-2 px-6 text-center">
            <Info size={18} className="text-fg-subtle" />
            <p className="text-sm text-fg-muted">Funding rates apply to perpetual instruments only.</p>
            <p className="text-xs text-fg-subtle">{asset.symbol} is a SPOT instrument — no funding cashflow exists for it.</p>
          </div>
        ) : loading ? (
          <div className="skeleton h-[260px] w-full" />
        ) : error ? (
          <ErrorState description="Could not load funding rates." onRetry={onRetry} />
        ) : rates.length === 0 ? (
          <EmptyState title="No funding history" description={`No funding observations ingested for ${asset.symbol} yet.`} />
        ) : (
          <FundingRateHistoryChart rates={rates} height={260} />
        )}
      </Panel>
    </Section>
  )
}

function StatTile({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <div className="flex flex-col gap-1 rounded-xl border border-border/60 bg-surface/40 px-3 py-3">
      <span className="text-[10px] font-medium uppercase tracking-wider text-fg-subtle">{label}</span>
      <span className="truncate font-mono text-metric-sm font-semibold tabular-nums text-fg">{value}</span>
      {hint && <span className="truncate text-[10px] text-fg-subtle">{hint}</span>}
    </div>
  )
}

function PriceStatistics({ asset, stats, barCount }: { asset: Asset; stats: PriceStats; barCount: number }) {
  return (
    <Section title="Price statistics" description={`Computed from ${barCount} real ${asset.symbol} bars — no fabricated figures.`}>
      <Panel className="grid grid-cols-2 gap-3 p-4">
        <div className="col-span-2 flex flex-col gap-1.5 rounded-xl border border-border/60 bg-surface/40 px-3 py-3">
          <span className="text-[10px] font-medium uppercase tracking-wider text-fg-subtle">7-day range</span>
          {stats.range7d ? (
            <>
              <div className="relative h-1.5 w-full rounded-full bg-surface">
                <div className="absolute inset-y-0 left-0 w-full rounded-full bg-info/50" />
              </div>
              <div className="flex items-center justify-between font-mono text-xs tabular-nums text-fg">
                <span>{fmtPrice(stats.range7d.low)}</span>
                <span>{fmtPrice(stats.range7d.high)}</span>
              </div>
            </>
          ) : (
            <span className="text-xs text-fg-subtle">Not enough bars yet.</span>
          )}
        </div>

        <StatTile
          label="30-day return"
          value={stats.return30d != null ? formatReturn(stats.return30d / 100) : '—'}
        />
        <StatTile label="7-day avg volume" value={stats.avgVolume7d != null ? fmtCompactVolume(stats.avgVolume7d) : '—'} />

        <StatTile
          label="Momentum"
          value={
            stats.momentumZScore != null ? (
              <Badge variant={MOMENTUM_VARIANT[momentumZone(stats.momentumZScore)]}>
                {MOMENTUM_LABEL[momentumZone(stats.momentumZScore)]} · z={formatRatio(stats.momentumZScore)}
              </Badge>
            ) : (
              '—'
            )
          }
          hint={stats.sma20 != null ? `SMA20 ${fmtPrice(stats.sma20)}` : undefined}
        />
        <StatTile
          label="Volatility (ann.)"
          value={
            stats.volatilityAnnualizedPct != null ? (
              <Badge variant={volatilityTone(stats.volatilityAnnualizedPct)}>
                {formatVolatility(stats.volatilityAnnualizedPct / 100)}
              </Badge>
            ) : (
              '—'
            )
          }
          hint="stdev of last 20 hourly returns"
        />
      </Panel>
    </Section>
  )
}

export function MarketIntelligence({
  asset,
  fundingRates,
  fundingLoading,
  fundingError,
  onRetryFunding,
  priceStats,
  barCount,
}: {
  asset: Asset
  fundingRates: FundingRate[]
  fundingLoading: boolean
  fundingError: boolean
  onRetryFunding: () => void
  priceStats: PriceStats
  barCount: number
}) {
  return (
    <div className={cn('grid grid-cols-1 items-start gap-6 lg:grid-cols-2')}>
      <FundingRateHistory asset={asset} rates={fundingRates} loading={fundingLoading} error={fundingError} onRetry={onRetryFunding} />
      <PriceStatistics asset={asset} stats={priceStats} barCount={barCount} />
    </div>
  )
}
