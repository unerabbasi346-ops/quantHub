// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout: sidebar + workspace; §Components: cards, tables, badges;
//   §Visual Language: semantic colors; §Interaction Standards: state handling.
// Doc 08 — Frontend Architecture (QH-008 v1.0)
//   §Architecture: feature module composes the shared design system + hooks;
//   §State Management: TanStack Query.
// Doc 14 §10.2 Strategy Governance, §10.6.4 Signal Recording, §10.3 Backtesting.
// Doc 15 §11.1.5 — the signal `value` is the signed conviction sizing consumes.
// Per Doc 00 §14.11
//
// JUDGMENT CALLS (Doc 00 §14.5/§14.7 — flagged):
//  1. HONEST F-9 VERSIONING REPRESENTATION (the one to get right). The registry
//     shows each strategy's `version` as its CURRENT registered value ONLY.
//     There is deliberately NO version-history list, NO "previous versions"
//     control, NO rollback affordance — because none exists (F-9: re-registering
//     overwrites the version row in place; the schema retains no history). A
//     persistent caption states this outright so the single version shown is
//     never mistaken for "the latest of a retained series". Glossing over it —
//     e.g. a version column that looks like it could be clicked for history —
//     would imply a capability the platform does not have.
//  2. STATUS COLORS map onto Doc 06's existing hues (no new colors): a backtest
//     COMPLETED reuses profit-green as a "successful terminal run" success
//     color and a strategy ACTIVE reuses info-blue, the same beyond-literal
//     reuse Badge.tsx documents. total_return is signed → pnlBadgeVariant.
//  3. total_return is a RETURN FRACTION; shown as a percentage (×100) for
//     readability, with the determinism hash shown truncated (full on hover).
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
  type BadgeVariant,
} from '@/components/ui'
import { cn } from '@/lib/utils/cn'
import { useBacktests, useSignals, useStrategies } from '../hooks/useStrategies'
import type { Backtest, Signal, Strategy } from '../types'

// ── display formatters (display-only; API strings are the source of truth) ──
function fmtReturnPct(value: string | null): string {
  if (value === null) return '—'
  return `${(Number.parseFloat(value) * 100).toFixed(4)}%`
}

function fmtMoney(value: string | null): string {
  if (value === null) return '—'
  return Number.parseFloat(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

function fmtSignal(value: string): string {
  const n = Number.parseFloat(value)
  const formatted = n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 8 })
  return n > 0 ? `+${formatted}` : formatted
}

function fmtTime(ts: string): string {
  return new Date(ts).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function strategyStatusVariant(status: string): BadgeVariant {
  switch (status.toUpperCase()) {
    case 'ACTIVE':
    case 'LIVE':
      return 'info'
    case 'PAPER':
      return 'warning'
    default:
      return 'neutral' // INACTIVE / ARCHIVED / unknown
  }
}

function backtestStatusVariant(status: string): BadgeVariant {
  switch (status.toUpperCase()) {
    case 'COMPLETED':
      return 'profit'
    case 'RUNNING':
      return 'info'
    case 'FAILED':
      return 'risk'
    default:
      return 'neutral'
  }
}

export function StrategiesShell() {
  const strategiesQuery = useStrategies()
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const strategies = strategiesQuery.data ?? []
  const activeId = selectedId ?? strategies[0]?.id ?? ''
  const activeStrategy = strategies.find((s) => s.id === activeId) ?? null

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-fg">Strategies</h1>
        <p className="mt-1 text-sm text-fg-muted">
          Strategy registry, signal feed &amp; backtest results — Phase 2/3 data.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[20rem_1fr]">
        <StrategyRegistry
          query={strategiesQuery}
          strategies={strategies}
          activeId={activeId}
          onSelect={setSelectedId}
        />
        <div className="min-w-0 space-y-6">
          {activeStrategy ? (
            <>
              <Backtests strategy={activeStrategy} />
              <Signals strategy={activeStrategy} />
            </>
          ) : (
            !strategiesQuery.isLoading &&
            !strategiesQuery.isError && (
              <Card>
                <CardContent>
                  <EmptyState
                    title="No strategy selected"
                    description="Select a strategy to view its backtests and signals."
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

function StrategyRegistry({
  query,
  strategies,
  activeId,
  onSelect,
}: {
  query: ReturnType<typeof useStrategies>
  strategies: Strategy[]
  activeId: string
  onSelect: (id: string) => void
}) {
  return (
    <Card className="h-fit">
      <CardHeader>
        <CardTitle>Registry</CardTitle>
        {query.isSuccess && <Badge variant="neutral">{strategies.length}</Badge>}
      </CardHeader>
      <CardContent className="p-2">
        {query.isLoading && <LoadingState label="Loading strategies…" />}
        {query.isError && (
          <ErrorState description="Could not load strategies." onRetry={() => query.refetch()} />
        )}
        {query.isSuccess && strategies.length === 0 && (
          <EmptyState title="No strategies" description="No strategies are registered yet." />
        )}
        {query.isSuccess &&
          strategies.map((strategy) => {
            const selected = strategy.id === activeId
            return (
              <button
                key={strategy.id}
                onClick={() => onSelect(strategy.id)}
                aria-current={selected ? 'true' : undefined}
                className={cn(
                  'flex w-full items-center justify-between gap-2 rounded-md px-3 py-2 text-left transition-colors',
                  selected
                    ? 'bg-info-soft text-info'
                    : 'text-fg-muted hover:bg-surface-hover hover:text-fg',
                )}
              >
                <span className="flex min-w-0 flex-col gap-1">
                  <span className="truncate text-sm font-medium">{strategy.name}</span>
                  <span className="text-xs text-fg-muted">v{strategy.version}</span>
                </span>
                <Badge variant={strategyStatusVariant(strategy.status)}>{strategy.status}</Badge>
              </button>
            )
          })}
      </CardContent>
      {/* Judgment call #1: state the F-9 versioning limitation outright rather
          than implying a version history that the schema does not retain. */}
      {query.isSuccess && strategies.length > 0 && (
        <div className="border-t border-border px-4 py-3 text-xs leading-relaxed text-fg-muted">
          Version shown is the current registration only. Prior versions are not
          retained — re-registering a strategy overwrites its version in place
          (no history or rollback). <span className="opacity-70">(F-9)</span>
        </div>
      )}
    </Card>
  )
}

function Backtests({ strategy }: { strategy: Strategy }) {
  const backtestsQuery = useBacktests(strategy.id)
  const backtests = backtestsQuery.data ?? []

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          Backtests
          <span className="ml-2 font-normal text-fg-muted">{strategy.name}</span>
        </CardTitle>
        {backtestsQuery.isSuccess && <Badge variant="neutral">{backtests.length}</Badge>}
      </CardHeader>
      <CardContent>
        {backtestsQuery.isLoading && <LoadingState label="Loading backtests…" />}
        {backtestsQuery.isError && (
          <ErrorState
            description="Could not load backtests."
            onRetry={() => backtestsQuery.refetch()}
          />
        )}
        {backtestsQuery.isSuccess && backtests.length === 0 && (
          <EmptyState title="No backtests" description="This strategy has no backtest runs." />
        )}
        {backtestsQuery.isSuccess && backtests.length > 0 && (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Run</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Fills</TableHead>
                <TableHead>Total Return</TableHead>
                <TableHead>Realized P&amp;L</TableHead>
                <TableHead>Final Capital</TableHead>
                <TableHead>Determinism Hash</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {backtests.map((backtest) => (
                <BacktestRow key={backtest.id} backtest={backtest} />
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  )
}

function BacktestRow({ backtest }: { backtest: Backtest }) {
  const fills = backtest.results?.orders_filled ?? backtest.trade_count
  const realized = backtest.results?.realized_pnl ?? null
  return (
    <TableRow>
      <TableCell>
        <span className="font-medium text-fg">{backtest.name}</span>
      </TableCell>
      <TableCell>
        <Badge variant={backtestStatusVariant(backtest.status)}>{backtest.status}</Badge>
      </TableCell>
      <TableCell numeric>{fills ?? '—'}</TableCell>
      <TableCell numeric>
        {backtest.total_return === null ? (
          '—'
        ) : (
          <Badge variant={pnlBadgeVariant(Number.parseFloat(backtest.total_return))}>
            {fmtReturnPct(backtest.total_return)}
          </Badge>
        )}
      </TableCell>
      <TableCell numeric>
        {realized === null ? (
          '—'
        ) : (
          <Badge variant={pnlBadgeVariant(Number.parseFloat(realized))}>{fmtMoney(realized)}</Badge>
        )}
      </TableCell>
      <TableCell numeric>{fmtMoney(backtest.final_capital)}</TableCell>
      <TableCell>
        {backtest.reproducibility_hash ? (
          <span
            className="font-mono text-xs text-fg-muted"
            title={backtest.reproducibility_hash}
          >
            {backtest.reproducibility_hash.slice(0, 12)}…
          </span>
        ) : (
          <span className="text-fg-muted">—</span>
        )}
      </TableCell>
    </TableRow>
  )
}

function Signals({ strategy }: { strategy: Strategy }) {
  const signalsQuery = useSignals(strategy.id)
  const signals = signalsQuery.data ?? []

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          Signals
          <span className="ml-2 font-normal text-fg-muted">most recent</span>
        </CardTitle>
        {signalsQuery.isSuccess && <Badge variant="neutral">{signals.length}</Badge>}
      </CardHeader>
      <CardContent>
        {signalsQuery.isLoading && <LoadingState label="Loading signals…" />}
        {signalsQuery.isError && (
          <ErrorState description="Could not load signals." onRetry={() => signalsQuery.refetch()} />
        )}
        {signalsQuery.isSuccess && signals.length === 0 && (
          <EmptyState title="No signals" description="This strategy has emitted no signals." />
        )}
        {signalsQuery.isSuccess && signals.length > 0 && (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time</TableHead>
                <TableHead>Value (conviction)</TableHead>
                <TableHead>Validation</TableHead>
                <TableHead>Detail</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {signals.map((signal) => (
                <SignalRow key={signal.id} signal={signal} />
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  )
}

function SignalRow({ signal }: { signal: Signal }) {
  const metaEntries = Object.entries(signal.metadata)
  return (
    <TableRow>
      <TableCell className="whitespace-nowrap text-fg-muted">{fmtTime(signal.ts)}</TableCell>
      <TableCell numeric>
        <Badge variant={pnlBadgeVariant(Number.parseFloat(signal.value))}>
          {fmtSignal(signal.value)}
        </Badge>
      </TableCell>
      <TableCell>
        <Badge variant={signal.validation_status === 'VALID' ? 'profit' : 'warning'}>
          {signal.validation_status}
        </Badge>
      </TableCell>
      {/* metadata is opaque per P-1 — shown verbatim, never interpreted. */}
      <TableCell className="font-mono text-xs text-fg-muted">
        {metaEntries.length === 0
          ? '—'
          : metaEntries.map(([k, v]) => `${k}=${v}`).join('  ')}
      </TableCell>
    </TableRow>
  )
}
