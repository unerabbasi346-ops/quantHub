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

import { Info } from 'lucide-react'
import { Badge, EmptyState, ErrorState, Section } from '@/components/ui'
import { CryptoIcon } from '@/components/ui'
import { useCorrelation } from '../hooks/useMarkets'

// Diverging cell background: +1 -> profit green, 0 -> transparent, -1 -> risk red.
function cellStyle(v: number | null): React.CSSProperties {
  if (v === null) return {}
  const mag = Math.min(1, Math.abs(v))
  const hue = v >= 0 ? 'var(--color-profit)' : 'var(--color-risk)'
  return { background: `hsl(${hue} / ${(0.12 + mag * 0.55).toFixed(3)})` }
}

function fmtCell(v: number | null): string {
  return v === null ? '—' : v.toFixed(2)
}

export function CorrelationMatrix() {
  const query = useCorrelation('1h')
  const data = query.data

  return (
    <Section
      title="Price correlation"
      description="Pairwise correlation of hourly price returns across ingested instruments."
      actions={data ? <Badge variant="neutral">{data.sample_size} obs · {data.interval}</Badge> : null}
    >
      {/* Prominent not-risk disclaimer */}
      <div className="mb-4 flex items-start gap-2 rounded-lg border border-info/25 bg-info-soft/40 px-3 py-2.5">
        <Info size={15} className="mt-0.5 shrink-0 text-info" />
        <p className="text-xs leading-relaxed text-fg-muted">
          <strong className="font-semibold text-fg">Market price-return correlation only.</strong>{' '}
          This is <strong className="font-semibold text-fg">not</strong> a portfolio risk metric — it is unrelated to VaR, CVaR,
          beta or volatility, which remain deferred (F-18). It describes how these instruments&apos; prices have moved together, nothing about capital at risk.
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
        <div className="overflow-x-auto rounded-xl border border-border bg-surface-raised p-4 shadow-sm">
          <table className="border-separate border-spacing-1">
            <thead>
              <tr>
                <th className="w-28" />
                {data.assets.map((a) => (
                  <th key={a.id} className="px-1 pb-2">
                    <div className="flex flex-col items-center gap-1">
                      <CryptoIcon symbol={a.symbol} size={20} />
                      <span className="text-[10px] font-medium text-fg-muted">{a.symbol.split('/')[0]}</span>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.assets.map((rowAsset, i) => (
                <tr key={rowAsset.id}>
                  <td className="pr-3">
                    <div className="flex items-center gap-2">
                      <CryptoIcon symbol={rowAsset.symbol} size={20} />
                      <span className="text-xs font-medium text-fg">{rowAsset.symbol.split('/')[0]}</span>
                    </div>
                  </td>
                  {data.matrix[i].map((v, j) => (
                    <td
                      key={j}
                      style={cellStyle(v)}
                      title={`${rowAsset.symbol} · ${data.assets[j].symbol}: ${fmtCell(v)}`}
                      className="h-11 w-16 rounded-md text-center align-middle font-mono text-xs tabular-nums text-fg"
                    >
                      {fmtCell(v)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Section>
  )
}
