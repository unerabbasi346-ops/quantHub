// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout: sidebar + workspace; §Components: cards, tables, badges;
//   §Visual Language: green=profit / red=risk (via pnlBadgeVariant);
//   §Interaction Standards: loading/success/error states.
// Doc 08 — Frontend Architecture (QH-008 v1.0)
//   §Architecture: feature module composes the shared design system + hooks;
//   §State Management: TanStack Query.
// Per Doc 00 §14.11
//
// REDESIGN (owner feedback): fixed the dead space below the old positions
// table by leading with a KPI stat strip (aggregate market value / P&L /
// count) and structuring the workspace with Sections + thin dividers rather
// than nesting tables inside bordered cards inside a grid. The capital-
// configuration control (F-19-honest) is composed here from the sibling
// CapitalConfig component.
'use client'

import { useState } from 'react'
import { Wallet } from 'lucide-react'
import {
  Badge,
  EmptyState,
  ErrorState,
  PageHeader,
  Section,
  SkeletonStats,
  SkeletonTable,
  StatCard,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  CryptoIcon,
  pnlBadgeVariant,
} from '@/components/ui'
import { cn } from '@/lib/utils/cn'
import { usePortfolios, usePositions } from '../hooks/usePortfolio'
import type { Portfolio, Position } from '../types'
import { CapitalConfig } from './CapitalConfig'

// Display formatters. The authoritative precise values are the API's Decimal
// strings; these are display-only (nothing downstream consumes them).
function fmtMoney(value: string | number): string {
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

function fmtQty(value: string): string {
  return Number.parseFloat(value).toLocaleString(undefined, { maximumFractionDigits: 8 })
}

function fmtPnl(value: string | number): string {
  const n = Number(value)
  const formatted = n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })
  return n > 0 ? `+${formatted}` : formatted
}

export function PortfolioShell() {
  const portfoliosQuery = usePortfolios()
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const portfolios = portfoliosQuery.data ?? []
  const activeId = selectedId ?? portfolios[0]?.id ?? ''
  const activePortfolio = portfolios.find((p) => p.id === activeId) ?? null

  return (
    <div className="space-y-8">
      <PageHeader
        icon={<Wallet size={18} />}
        title="Portfolio"
        subtitle="Positions, P&L and configured capital — Phase 3 recorded state."
        actions={
          activePortfolio && (
            <Badge variant="neutral" className="gap-1.5">
              {activePortfolio.portfolio_type} · {activePortfolio.base_currency}
            </Badge>
          )
        }
      />

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[16rem_1fr]">
        {/* Portfolio switcher — a plain list, not a boxed card */}
        <Section title="Portfolios" actions={portfoliosQuery.isSuccess ? <Badge variant="neutral">{portfolios.length}</Badge> : null}>
          {portfoliosQuery.isLoading && <div className="skeleton h-24 w-full" />}
          {portfoliosQuery.isError && (
            <ErrorState description="Could not load portfolios." onRetry={() => portfoliosQuery.refetch()} />
          )}
          {portfoliosQuery.isSuccess && portfolios.length === 0 && (
            <EmptyState icon={<Wallet size={20} />} title="No portfolios" description="No active portfolios exist yet." />
          )}
          <div className="space-y-1">
            {portfolios.map((portfolio) => {
              const selected = portfolio.id === activeId
              return (
                <button
                  key={portfolio.id}
                  onClick={() => setSelectedId(portfolio.id)}
                  aria-current={selected ? 'true' : undefined}
                  className={cn(
                    'flex w-full flex-col gap-1 rounded-lg border px-3 py-2.5 text-left transition-colors duration-150',
                    selected
                      ? 'border-info/40 bg-info-soft text-info'
                      : 'border-transparent text-fg-muted hover:bg-surface-hover hover:text-fg',
                  )}
                >
                  <span className="truncate text-sm font-medium">{portfolio.name}</span>
                  <span className="text-[11px] uppercase tracking-wide text-fg-subtle">
                    {portfolio.portfolio_type} · {portfolio.base_currency}
                  </span>
                </button>
              )
            })}
          </div>
        </Section>

        <div className="min-w-0 space-y-8">
          {activePortfolio ? (
            <PortfolioDetail portfolio={activePortfolio} />
          ) : (
            !portfoliosQuery.isLoading &&
            !portfoliosQuery.isError && (
              <EmptyState icon={<Wallet size={20} />} title="No portfolio selected" description="Select a portfolio to view its positions." />
            )
          )}
        </div>
      </div>
    </div>
  )
}

function PortfolioDetail({ portfolio }: { portfolio: Portfolio }) {
  const positionsQuery = usePositions(portfolio.id)
  const positions = positionsQuery.data ?? []
  const open = positions.filter((p) => !p.is_closed)

  const totalMarketValue = open.reduce((s, p) => s + Number.parseFloat(p.market_value), 0)
  const totalUnrealized = open.reduce((s, p) => s + Number.parseFloat(p.unrealized_pnl), 0)
  const totalRealizedToday = open.reduce((s, p) => s + Number.parseFloat(p.realized_pnl_today), 0)

  return (
    <>
      {/* KPI strip — fills the top of the workspace and anchors the page */}
      {positionsQuery.isLoading ? (
        <SkeletonStats count={4} />
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard label="Market value" value={fmtMoney(totalMarketValue)} hint={`${portfolio.base_currency}`} />
          <StatCard
            label="Unrealized P&L"
            value={fmtPnl(totalUnrealized)}
            tone={totalUnrealized >= 0 ? 'profit' : 'risk'}
          />
          <StatCard
            label="Realized today"
            value={fmtPnl(totalRealizedToday)}
            tone={totalRealizedToday >= 0 ? 'profit' : 'risk'}
          />
          <StatCard label="Open positions" value={open.length} hint={`${positions.length} total`} />
        </div>
      )}

      {/* Capital configuration (honest F-19 labeling) */}
      <CapitalConfig portfolio={portfolio} />

      <Section
        title="Positions"
        actions={positionsQuery.isSuccess ? <Badge variant="neutral">{positions.length}</Badge> : null}
      >
        {positionsQuery.isLoading && <SkeletonTable rows={4} cols={6} />}
        {positionsQuery.isError && (
          <ErrorState description="Could not load positions." onRetry={() => positionsQuery.refetch()} />
        )}
        {positionsQuery.isSuccess && positions.length === 0 && (
          <EmptyState icon={<Wallet size={20} />} title="No positions" description="This portfolio holds no positions." />
        )}
        {positionsQuery.isSuccess && positions.length > 0 && (
          <div className="overflow-hidden rounded-xl border border-border bg-surface-raised shadow-sm">
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
          </div>
        )}
      </Section>
    </>
  )
}

function PositionRow({ position }: { position: Position }) {
  const symbol = position.symbol ?? position.asset_id
  return (
    <TableRow>
      <TableCell>
        <div className="flex items-center gap-2.5">
          <CryptoIcon symbol={symbol} size={22} />
          <div className="min-w-0">
            <div className="font-medium text-fg">{symbol}</div>
            {position.exchange && (
              <div className="text-[11px] uppercase tracking-wide text-fg-subtle">{position.exchange}</div>
            )}
          </div>
        </div>
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
