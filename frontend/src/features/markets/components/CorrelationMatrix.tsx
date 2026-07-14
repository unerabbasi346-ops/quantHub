// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Data Visualization: a correlation heatmap. Owner request: "simple asset
//   price-correlation view."
// Doc 08 §Architecture: feature component over the correlation endpoint.
// Per Doc 00 §14.11
//
// EXPLICIT, PROMINENT SCOPE LABEL (flagged, Doc 00 §14.5/§14.7): this view is a
// descriptive PRICE-RETURN correlation between market instruments — NOT a
// portfolio risk metric. It is deliberately unrelated to F-18's deferred
// §11.5.3 portfolio risk measures (VaR / CVaR / beta / volatility / drawdown),
// which remain correctly deferred. The banner below states this so the matrix
// is never mistaken for portfolio risk.
'use client'

import type { ReactNode } from 'react'
import { Info } from 'lucide-react'
import { Badge, EmptyState, ErrorState, Heatmap, Panel, Section } from '@/components/ui'
import { useCorrelation } from '../hooks/useMarkets'

export function CorrelationMatrix({
  title = 'Price correlation',
  icon,
  compact = false,
}: {
  /** Caller-supplied title (Risk's usage labels this "Cross-asset
   *  correlation"; Markets keeps the original "Price correlation"). */
  title?: string
  icon?: ReactNode
  /** Smaller rendering for a shared/secondary placement (Markets' 3-column
   *  analytics grid) — Risk (the primary home for this analysis per Doc 00
   *  §14.5/§14.7 owner instruction) gets the full-size heatmap. */
  compact?: boolean
}) {
  const query = useCorrelation('1h')
  const data = query.data
  const height = compact ? 240 : Math.max(280, (data?.assets.length ?? 0) * 46 + 90)

  return (
    <Section
      icon={icon}
      title={title}
      description="Pairwise correlation of hourly price returns across ingested instruments."
      actions={data ? <Badge variant="neutral">{data.sample_size} obs · {data.interval}</Badge> : null}
    >
      {/* Prominent not-risk disclaimer */}
      <div className="mb-4 flex items-start gap-2 rounded-lg border border-info/25 bg-info-soft/40 px-3 py-2.5">
        <Info size={15} className="mt-0.5 shrink-0 text-info" />
        <p className="text-xs leading-relaxed text-fg-muted">
          <strong className="font-semibold text-fg">Market price-return correlation only.</strong>{' '}
          This is <strong className="font-semibold text-fg">not</strong> a portfolio risk metric — it is unrelated to VaR, CVaR,
          beta or volatility, which aren&apos;t computed yet (F-18). It describes how these instruments&apos; prices have moved together, nothing about capital at risk.
        </p>
      </div>

      {query.isLoading && <div className="skeleton h-56 w-full" />}
      {query.isError && <ErrorState description="Could not load correlation." onRetry={() => query.refetch()} />}
      {query.isSuccess && (!data || data.assets.length < 2) && (
        <EmptyState
          title="Not enough instruments"
          description="At least two instruments with an overlapping bar window are needed to correlate."
        />
      )}

      {query.isSuccess && data && data.assets.length >= 2 && (
        <Panel className="p-4">
          <Heatmap
            xLabels={data.assets.map((a) => a.symbol.split('/')[0])}
            yLabels={data.assets.map((a) => a.symbol.split('/')[0])}
            values={data.matrix}
            mode="diverging"
            height={height}
          />
        </Panel>
      )}
    </Section>
  )
}
