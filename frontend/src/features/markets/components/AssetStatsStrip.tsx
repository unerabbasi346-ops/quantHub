// Governing specification: handbook/ui/visual_engineering/13_VISUAL_DNA —
//   Voltrex-style asset pill strip: compact dark glass pills, horizontally
//   scrolling, one row always. Doc 00 §14.5/§14.7 DATA HONESTY: every price/
//   change figure is a real computed value from ingested bars (useAssets +
//   useBars), never fabricated.
'use client'

import { CryptoIcon } from '@/components/ui/CryptoIcon'
import { cn } from '@/lib/utils/cn'
import { computeDayChange } from '../analytics'
import type { Asset, OHLCVBar } from '../types'

const fmtPrice = (v: number) => v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })

export function AssetStatsStrip({
  assets,
  barsByAssetId,
  selectedId,
  onSelect,
}: {
  assets: Asset[]
  barsByAssetId: Map<string, OHLCVBar[]>
  selectedId: string
  onSelect: (asset: Asset) => void
}) {
  return (
    <div className="flex gap-2.5 overflow-x-auto pb-1">
      {assets.map((asset) => {
        const bars = barsByAssetId.get(asset.id) ?? []
        const dc = computeDayChange(bars)
        const selected = asset.id === selectedId
        return (
          <button
            key={asset.id}
            type="button"
            onClick={() => onSelect(asset)}
            className={cn(
              'flex shrink-0 items-center gap-2 rounded-full border bg-surface-raised/50 px-3.5 py-2 backdrop-blur-sm transition-colors',
              selected ? 'border-accent/60 bg-accent-soft' : 'border-border/60 hover:border-border-strong',
            )}
          >
            <CryptoIcon symbol={asset.symbol} size={18} />
            <span className={cn('text-xs font-medium', selected ? 'text-accent' : 'text-fg')}>
              {asset.symbol.split('/')[0]}
            </span>
            {dc ? (
              <>
                <span className="font-mono text-xs tabular-nums text-fg-muted">{fmtPrice(dc.last)}</span>
                <span className={cn('font-mono text-[11px] tabular-nums', dc.change >= 0 ? 'text-profit' : 'text-risk')}>
                  {dc.change >= 0 ? '+' : ''}
                  {dc.changePct.toFixed(2)}%
                </span>
              </>
            ) : (
              <span className="text-[11px] text-fg-subtle">…</span>
            )}
          </button>
        )
      })}
    </div>
  )
}
