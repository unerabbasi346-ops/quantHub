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

import { useMemo, useState } from 'react'
import { TrendingDown, TrendingUp, Wallet } from 'lucide-react'
import {
  Badge,
  DonutChart,
  EmptyState,
  ErrorState,
  InstitutionalTable,
  type InstitutionalColumnDef,
  PageHeader,
  Panel,
  Section,
  SkeletonStats,
  SkeletonTable,
  StatCard,
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
    <div className="space-y-14">
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
                      ? 'border-accent/40 bg-accent-soft text-accent'
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

        <div className="min-w-0 space-y-14">
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

  // Allocation slices from real open-position market values (abs, so a short
  // still shows its capital footprint). Excludes zero/near-zero rows.
  const allocation = open
    .map((p) => ({ name: p.symbol ?? p.asset_id, value: Math.abs(Number.parseFloat(p.market_value)) }))
    .filter((d) => d.value > 0)
    .sort((a, b) => b.value - a.value)

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

      {/* Asset allocation — computed from REAL open-position market values.
          Honest: shows only actual holdings; an unpriced/empty book renders an
          empty state rather than a fabricated split. */}
      {!positionsQuery.isLoading && (
        <Section
          title="Asset allocation"
          description="Share of capital by open-position market value."
          actions={<Badge variant="neutral">{open.length} open</Badge>}
        >
          {allocation.length > 0 ? (
            <Panel className="p-4">
              <DonutChart
                data={allocation}
                height={280}
                centerLabel="market value"
                centerValue={fmtMoney(totalMarketValue)}
                valueFormat={(v) => fmtMoney(v)}
              />
            </Panel>
          ) : (
            <EmptyState
              icon={<Wallet size={20} />}
              title="No open positions to allocate"
              description="Allocation appears once this portfolio holds positions with a market value."
            />
          )}
        </Section>
      )}

      {/* Capital configuration (honest F-19 labeling) — integrates the REAL
          open-position market value as a utilization figure, not a standalone card. */}
      <CapitalConfig portfolio={portfolio} openMarketValue={totalMarketValue} />

      {/* Contributors — real per-position P&L ranking, ties the allocation
          donut and the positions table together (Doc 07 §Top/Bottom
          Contributors), honestly scoped to whatever positions actually exist. */}
      {!positionsQuery.isLoading && open.length > 0 && <Contributors positions={open} />}

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
          <Panel className="overflow-hidden">
            <PositionTable positions={positions} />
          </Panel>
        )}
      </Section>
    </>
  )
}

function ContributorRow({ position }: { position: Position }) {
  const symbol = position.symbol ?? position.asset_id
  const pnl = Number.parseFloat(position.unrealized_pnl)
  return (
    <div className="flex items-center gap-3 py-2">
      <CryptoIcon symbol={symbol} size={22} />
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-medium text-fg">{symbol}</div>
        <div className="text-[11px] text-fg-subtle">{fmtMoney(position.market_value)} mkt value</div>
      </div>
      <Badge variant={pnlBadgeVariant(pnl)}>{fmtPnl(pnl)}</Badge>
    </div>
  )
}

function Contributors({ positions }: { positions: Position[] }) {
  const ranked = [...positions].sort((a, b) => Number.parseFloat(b.unrealized_pnl) - Number.parseFloat(a.unrealized_pnl))
  const winners = ranked.filter((p) => Number.parseFloat(p.unrealized_pnl) > 0).slice(0, 5)
  const losers = ranked
    .filter((p) => Number.parseFloat(p.unrealized_pnl) < 0)
    .slice(-5)
    .reverse()

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <Section title="Top contributors" description="Open positions with the largest unrealized gain.">
        <Panel className="divide-y divide-border/70 px-4">
          {winners.length > 0 ? (
            winners.map((p) => <ContributorRow key={p.id} position={p} />)
          ) : (
            <div className="flex items-center gap-2 py-6 text-sm text-fg-muted">
              <TrendingUp size={16} className="text-fg-subtle" /> No position is currently profitable.
            </div>
          )}
        </Panel>
      </Section>
      <Section title="Bottom contributors" description="Open positions with the largest unrealized loss.">
        <Panel className="divide-y divide-border/70 px-4">
          {losers.length > 0 ? (
            losers.map((p) => <ContributorRow key={p.id} position={p} />)
          ) : (
            <div className="flex items-center gap-2 py-6 text-sm text-fg-muted">
              <TrendingDown size={16} className="text-fg-subtle" /> No position is currently underwater.
            </div>
          )}
        </Panel>
      </Section>
    </div>
  )
}

function PositionTable({ positions }: { positions: Position[] }) {
  const columns = useMemo<InstitutionalColumnDef<Position>[]>(
    () => [
      {
        id: 'asset',
        header: 'Asset',
        accessorFn: (p) => p.symbol ?? p.asset_id,
        cell: ({ row }) => {
          const p = row.original
          const symbol = p.symbol ?? p.asset_id
          return (
            <div className="flex items-center gap-2.5">
              <CryptoIcon symbol={symbol} size={22} />
              <div className="min-w-0">
                <div className="font-medium text-fg">{symbol}</div>
                {p.exchange && <div className="text-[11px] uppercase tracking-wide text-fg-subtle">{p.exchange}</div>}
              </div>
            </div>
          )
        },
      },
      {
        id: 'quantity',
        header: 'Quantity',
        accessorFn: (p) => Number.parseFloat(p.quantity),
        cell: ({ row }) => fmtQty(row.original.quantity),
        meta: { numeric: true },
      },
      {
        id: 'average_entry_price',
        header: 'Avg Entry',
        accessorFn: (p) => Number.parseFloat(p.average_entry_price),
        cell: ({ row }) => fmtMoney(row.original.average_entry_price),
        meta: { numeric: true, hideBelow: 'tablet' },
      },
      {
        id: 'market_value',
        header: 'Market Value',
        accessorFn: (p) => Number.parseFloat(p.market_value),
        cell: ({ row }) => fmtMoney(row.original.market_value),
        meta: { numeric: true },
      },
      {
        id: 'unrealized_pnl',
        header: 'Unrealized P&L',
        accessorFn: (p) => Number.parseFloat(p.unrealized_pnl),
        cell: ({ row }) => (
          <Badge variant={pnlBadgeVariant(Number.parseFloat(row.original.unrealized_pnl))}>
            {fmtPnl(row.original.unrealized_pnl)}
          </Badge>
        ),
        meta: { numeric: true },
      },
      {
        id: 'realized_pnl_today',
        header: 'Realized P&L (today)',
        accessorFn: (p) => Number.parseFloat(p.realized_pnl_today),
        cell: ({ row }) => (
          <Badge variant={pnlBadgeVariant(Number.parseFloat(row.original.realized_pnl_today))}>
            {fmtPnl(row.original.realized_pnl_today)}
          </Badge>
        ),
        meta: { numeric: true, hideBelow: 'laptop' },
      },
    ],
    [],
  )

  return (
    <InstitutionalTable
      data={positions}
      columns={columns}
      getRowId={(p) => p.id}
      searchPlaceholder="Search positions…"
      exportFilename="portfolio-positions"
    />
  )
}
