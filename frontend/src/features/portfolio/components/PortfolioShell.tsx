// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout: sidebar + workspace; §Components: cards, tables, badges;
//   §Visual Language: green=profit / red=risk (via pnlBadgeVariant);
//   §Interaction Standards: loading/success/error states.
// Doc 08 — Frontend Architecture (QH-008 v1.0)
//   §Architecture: feature module composes the shared design system + hooks;
//   §State Management: TanStack Query.
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
  pnlBadgeVariant,
} from '@/components/ui'
import { cn } from '@/lib/utils/cn'
import { usePortfolios, usePositions } from '../hooks/usePortfolio'
import type { Portfolio, Position } from '../types'

// Display formatters. The authoritative precise values are the API's Decimal
// strings; these are display-only (nothing downstream consumes them).
function fmtMoney(value: string): string {
  return Number.parseFloat(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

function fmtQty(value: string): string {
  return Number.parseFloat(value).toLocaleString(undefined, {
    maximumFractionDigits: 8,
  })
}

// P&L keeps up to 4 decimals so a small non-zero value (e.g. -0.0087) is not
// rounded away to 0.00 and mis-signed.
function fmtPnl(value: string): string {
  const n = Number.parseFloat(value)
  const formatted = n.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  })
  return n > 0 ? `+${formatted}` : formatted
}

export function PortfolioShell() {
  const portfoliosQuery = usePortfolios()
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const portfolios = portfoliosQuery.data ?? []
  const activeId = selectedId ?? portfolios[0]?.id ?? ''
  const activePortfolio = portfolios.find((p) => p.id === activeId) ?? null

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-fg">Portfolio</h1>
        <p className="mt-1 text-sm text-fg-muted">
          Positions and P&amp;L — Phase 3 recorded positions.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[18rem_1fr]">
        <PortfolioList
          query={portfoliosQuery}
          portfolios={portfolios}
          activeId={activeId}
          onSelect={setSelectedId}
        />
        <div className="min-w-0">
          {activePortfolio ? (
            <Positions portfolio={activePortfolio} />
          ) : (
            !portfoliosQuery.isLoading &&
            !portfoliosQuery.isError && (
              <Card>
                <CardContent>
                  <EmptyState
                    title="No portfolio selected"
                    description="Select a portfolio to view its positions."
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

function PortfolioList({
  query,
  portfolios,
  activeId,
  onSelect,
}: {
  query: ReturnType<typeof usePortfolios>
  portfolios: Portfolio[]
  activeId: string
  onSelect: (id: string) => void
}) {
  return (
    <Card className="h-fit">
      <CardHeader>
        <CardTitle>Portfolios</CardTitle>
        {query.isSuccess && <Badge variant="neutral">{portfolios.length}</Badge>}
      </CardHeader>
      <CardContent className="p-2">
        {query.isLoading && <LoadingState label="Loading portfolios…" />}
        {query.isError && (
          <ErrorState description="Could not load portfolios." onRetry={() => query.refetch()} />
        )}
        {query.isSuccess && portfolios.length === 0 && (
          <EmptyState title="No portfolios" description="No active portfolios exist yet." />
        )}
        {query.isSuccess &&
          portfolios.map((portfolio) => {
            const selected = portfolio.id === activeId
            return (
              <button
                key={portfolio.id}
                onClick={() => onSelect(portfolio.id)}
                aria-current={selected ? 'true' : undefined}
                className={cn(
                  'flex w-full flex-col gap-1 rounded-md px-3 py-2 text-left transition-colors',
                  selected
                    ? 'bg-info-soft text-info'
                    : 'text-fg-muted hover:bg-surface-hover hover:text-fg',
                )}
              >
                <span className="truncate text-sm font-medium">{portfolio.name}</span>
                <span className="text-xs uppercase tracking-wide text-fg-muted">
                  {portfolio.portfolio_type} · {portfolio.base_currency}
                </span>
              </button>
            )
          })}
      </CardContent>
    </Card>
  )
}

function Positions({ portfolio }: { portfolio: Portfolio }) {
  const positionsQuery = usePositions(portfolio.id)
  const positions = positionsQuery.data ?? []

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          {portfolio.name}
          <span className="ml-2 font-normal text-fg-muted">Positions</span>
        </CardTitle>
        {positionsQuery.isSuccess && <Badge variant="neutral">{positions.length}</Badge>}
      </CardHeader>
      <CardContent>
        {positionsQuery.isLoading && <LoadingState label="Loading positions…" />}
        {positionsQuery.isError && (
          <ErrorState
            description="Could not load positions."
            onRetry={() => positionsQuery.refetch()}
          />
        )}
        {positionsQuery.isSuccess && positions.length === 0 && (
          <EmptyState
            title="No positions"
            description="This portfolio holds no positions."
          />
        )}
        {positionsQuery.isSuccess && positions.length > 0 && (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Asset</TableHead>
                <TableHead>Quantity</TableHead>
                <TableHead>Avg Entry</TableHead>
                <TableHead>Market Value</TableHead>
                <TableHead>Unrealized P&amp;L</TableHead>
                <TableHead>Realized P&amp;L (today)</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {positions.map((position) => (
                <PositionRow key={position.id} position={position} />
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  )
}

function PositionRow({ position }: { position: Position }) {
  return (
    <TableRow>
      <TableCell>
        <span className="font-medium text-fg">{position.symbol ?? position.asset_id}</span>
        {position.exchange && (
          <span className="ml-2 text-xs uppercase text-fg-muted">{position.exchange}</span>
        )}
      </TableCell>
      <TableCell numeric>{fmtQty(position.quantity)}</TableCell>
      <TableCell numeric>{fmtMoney(position.average_entry_price)}</TableCell>
      <TableCell numeric>{fmtMoney(position.market_value)}</TableCell>
      <TableCell numeric>
        <Badge variant={pnlBadgeVariant(Number.parseFloat(position.unrealized_pnl))}>
          {fmtPnl(position.unrealized_pnl)}
        </Badge>
      </TableCell>
      <TableCell numeric>
        <Badge variant={pnlBadgeVariant(Number.parseFloat(position.realized_pnl_today))}>
          {fmtPnl(position.realized_pnl_today)}
        </Badge>
      </TableCell>
    </TableRow>
  )
}
