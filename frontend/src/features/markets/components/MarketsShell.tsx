// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout: sidebar + workspace; §Components: cards, tables;
//   §Interaction Standards: loading/success/error states.
// Doc 08 — Frontend Architecture (QH-008 v1.0)
//   §Architecture: feature module composes presentation from the shared
//   design system + feature hooks; §State Management: TanStack Query.
// Per Doc 00 §14.11
'use client'

import { useState } from 'react'
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  ErrorState,
  LoadingState,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui'
import { cn } from '@/lib/utils/cn'
import { useAssets, useBars } from '../hooks/useMarkets'
import type { Asset, OHLCVBar } from '../types'
import { PriceChart } from './PriceChart'

// Only 1h data is currently ingested (Phase 1). Interval selection is a
// deliberate future addition (would need real multi-interval data first) —
// fixed to 1h for now rather than showing empty states for absent intervals.
const INTERVAL = '1h'

// Display formatting only — the authoritative precise values are the API's
// Decimal strings (features/markets/types.ts). toLocaleString here is purely
// for a readable table; nothing downstream consumes these formatted values.
function fmtPrice(value: string): string {
  return Number.parseFloat(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

function fmtVolume(value: string): string {
  return Number.parseFloat(value).toLocaleString(undefined, {
    maximumFractionDigits: 4,
  })
}

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function MarketsShell() {
  const assetsQuery = useAssets()
  const [selectedId, setSelectedId] = useState<string | null>(null)

  // Default to the first asset until the user picks one.
  const assets = assetsQuery.data ?? []
  const activeId = selectedId ?? assets[0]?.id ?? ''
  const activeAsset = assets.find((a) => a.id === activeId) ?? null

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-fg">Markets</h1>
        <p className="mt-1 text-sm text-fg-muted">
          Live OHLCV market data — Phase 1 ingested bars.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[16rem_1fr]">
        <AssetList
          query={assetsQuery}
          assets={assets}
          activeId={activeId}
          onSelect={setSelectedId}
        />
        <div className="min-w-0 space-y-6">
          {activeAsset ? (
            <AssetDetail asset={activeAsset} />
          ) : (
            !assetsQuery.isLoading &&
            !assetsQuery.isError && (
              <Card>
                <CardContent>
                  <EmptyState
                    title="No asset selected"
                    description="Select an asset to view its price chart and bars."
                  />
                </CardContent>
              </Card>
            )
          )}
        </div>
      </div>
    </div>
  )
}

function AssetList({
  query,
  assets,
  activeId,
  onSelect,
}: {
  query: ReturnType<typeof useAssets>
  assets: Asset[]
  activeId: string
  onSelect: (id: string) => void
}) {
  return (
    <Card className="h-fit">
      <CardHeader>
        <CardTitle>Assets</CardTitle>
        {query.isSuccess && <Badge variant="neutral">{assets.length}</Badge>}
      </CardHeader>
      <CardContent className="p-2">
        {query.isLoading && <LoadingState label="Loading assets…" />}
        {query.isError && (
          <ErrorState
            description="Could not load assets."
            onRetry={() => query.refetch()}
          />
        )}
        {query.isSuccess && assets.length === 0 && (
          <EmptyState title="No assets" description="No tradable assets are registered yet." />
        )}
        {query.isSuccess &&
          assets.map((asset) => {
            const selected = asset.id === activeId
            return (
              <button
                key={asset.id}
                onClick={() => onSelect(asset.id)}
                aria-current={selected ? 'true' : undefined}
                className={cn(
                  'flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm transition-colors',
                  selected
                    ? 'bg-info-soft text-info'
                    : 'text-fg-muted hover:bg-surface-hover hover:text-fg',
                )}
              >
                <span className="font-medium">{asset.symbol}</span>
                <span className="text-xs uppercase text-fg-muted">{asset.exchange}</span>
              </button>
            )
          })}
      </CardContent>
    </Card>
  )
}

function AssetDetail({ asset }: { asset: Asset }) {
  const barsQuery = useBars(asset.id, INTERVAL)
  const bars = barsQuery.data ?? []

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>
            {asset.symbol}
            <span className="ml-2 font-normal text-fg-muted">
              {asset.exchange} · {INTERVAL}
            </span>
          </CardTitle>
          <Badge variant={asset.is_active ? 'profit' : 'neutral'}>
            {asset.asset_class}
          </Badge>
        </CardHeader>
        <CardContent>
          {barsQuery.isLoading && <LoadingState label="Loading bars…" />}
          {barsQuery.isError && (
            <ErrorState
              description="Could not load price bars."
              onRetry={() => barsQuery.refetch()}
            />
          )}
          {barsQuery.isSuccess && bars.length === 0 && (
            <EmptyState
              title="No bars"
              description={`No ${INTERVAL} bars ingested for ${asset.symbol} yet.`}
            />
          )}
          {barsQuery.isSuccess && bars.length > 0 && <PriceChart bars={bars} />}
        </CardContent>
      </Card>

      {barsQuery.isSuccess && bars.length > 0 && <RecentBars bars={bars} />}
    </>
  )
}

function RecentBars({ bars }: { bars: OHLCVBar[] }) {
  // Newest first, most recent 20 — the chart already shows the full window;
  // this is the tabular detail view (Doc 06 §Components: tables).
  const recent = [...bars].reverse().slice(0, 20)
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent bars</CardTitle>
        <Badge variant="neutral">{bars.length} total</Badge>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Time</TableHead>
              <TableHead>Open</TableHead>
              <TableHead>High</TableHead>
              <TableHead>Low</TableHead>
              <TableHead>Close</TableHead>
              <TableHead>Volume</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {recent.map((bar) => (
              <TableRow key={bar.ts}>
                <TableCell>{fmtTime(bar.ts)}</TableCell>
                <TableCell numeric>{fmtPrice(bar.open)}</TableCell>
                <TableCell numeric>{fmtPrice(bar.high)}</TableCell>
                <TableCell numeric>{fmtPrice(bar.low)}</TableCell>
                <TableCell numeric>{fmtPrice(bar.close)}</TableCell>
                <TableCell numeric>{fmtVolume(bar.volume)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
