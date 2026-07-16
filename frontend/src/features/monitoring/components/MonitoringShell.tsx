// Governing specification: Doc 08 §Architecture: feature-specific component
//   inside feature directory. Doc 00 §14.5/§14.7 DATA HONESTY — every figure
//   below is Hermes's own real, server-computed status (backend/src/quant_hub/
//   hermes/); nothing here is fabricated or a "coming soon" placeholder.
//
// REPLACES the previous ComingSoon deferral (S-6: "no backend audit/
// notification/metrics pipeline exists yet") now that Hermes IS that
// pipeline — read-only, polled every 60s. Five sections, task-specified
// order: (1) System Health Strip, (2) Data Pipeline (ingestion + funding
// freshness), (3) Strategy Lifecycle, (4) ML Operations, (5) System Timeline.
'use client'

import { useMemo } from 'react'
import { Activity, Brain, Cpu, Database, GitCommit, Radio, Server, Signal as SignalIcon } from 'lucide-react'
import {
  Badge,
  type BadgeVariant,
  EmptyState,
  ErrorState,
  InstitutionalTable,
  type InstitutionalColumnDef,
  PageHeader,
  Panel,
  Section,
} from '@/components/ui'
import { formatCount, formatRatio, formatTimestamp } from '@/lib/utils/format'
import { useHermesStatus } from '@/features/hermes/hooks/useHermes'
import type {
  AssetFreshness,
  FreshnessStatus,
  FundingFreshness,
  HermesServiceStatus,
  MLModelStatus,
  StrategyLifecycle,
  TrainingJob,
} from '@/features/hermes/types'
import { HealthGauge } from './charts'

function freshnessVariant(status: FreshnessStatus): BadgeVariant {
  switch (status) {
    case 'FRESH': return 'profit'
    case 'STALE': return 'warning'
    case 'DEAD': return 'risk'
  }
}

function serviceVariant(status: HermesServiceStatus['status']): BadgeVariant {
  switch (status) {
    case 'UP': return 'profit'
    case 'DOWN': return 'risk'
    case 'NOT_CONFIGURED': return 'neutral'
  }
}

// Staleness is reported in seconds (raw, per hermes_router.py's numeric
// convention) — a compact "Xm/Xh/Xd" duration reads far better in a table
// cell than a formatted timestamp would for a relative gap measurement.
function fmtDuration(seconds: number | null): string {
  if (seconds == null) return '—'
  if (seconds < 60) return `${Math.floor(seconds)}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`
  return `${Math.floor(seconds / 86400)}d`
}

export function MonitoringShell() {
  const query = useHermesStatus()
  const status = query.data ?? null

  return (
    <div className="space-y-8">
      <PageHeader
        icon={<Activity size={18} />}
        title="Monitoring"
        subtitle="Hermes — real-time system observability, coordinates and monitors only."
      />

      {query.isLoading && <div className="skeleton h-40 w-full" />}
      {query.isError && <ErrorState description="Could not load Hermes status." onRetry={() => query.refetch()} />}

      {status && (
        <>
          <HealthStrip status={status} />
          <DataPipelineSection assets={status.assets} funding={status.funding} />
          <StrategyLifecycleSection strategies={status.strategies} />
          <MLOpsSection models={status.models} jobs={status.training_jobs} />
          <SystemTimeline status={status} />
        </>
      )}
    </div>
  )
}

// ── Section 1: System Health Strip ──────────────────────────────────────
function HealthStrip({ status }: { status: NonNullable<ReturnType<typeof useHermesStatus>['data']> }) {
  const backend = status.services.find((s) => s.name === 'backend') ?? null
  const database = status.services.find((s) => s.name === 'database') ?? null
  const redis = status.services.find((s) => s.name === 'redis') ?? null

  return (
    <Section icon={<Server size={16} />} title="System health" description="Backend, database, and cache connectivity — polled every 60s.">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[2fr_1fr]">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <ServiceTile label="Backend API" service={backend} />
          <ServiceTile label="Database" service={database} />
          <ServiceTile label="Redis" service={redis} />
        </div>
        <Panel className="flex items-center justify-center p-4">
          <HealthGauge score={status.health_score} height={180} />
        </Panel>
      </div>
    </Section>
  )
}

function ServiceTile({ label, service }: { label: string; service: HermesServiceStatus | null }) {
  return (
    <Panel className="p-4">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[11px] font-medium uppercase tracking-wider text-fg-subtle">{label}</span>
        {service && <Badge variant={serviceVariant(service.status)}>{service.status === 'NOT_CONFIGURED' ? 'Not configured' : service.status}</Badge>}
      </div>
      <div className="mt-2 font-mono text-metric-sm font-semibold tabular-nums text-fg">
        {service?.latency_ms != null ? `${service.latency_ms.toFixed(1)} ms` : '—'}
      </div>
      <div className="mt-0.5 text-[11px] text-fg-subtle">{service?.detail ?? '—'}</div>
    </Panel>
  )
}

// ── Section 2: Data Pipeline ─────────────────────────────────────────────
function DataPipelineSection({ assets, funding }: { assets: AssetFreshness[]; funding: FundingFreshness[] }) {
  const assetColumns = useMemo<InstitutionalColumnDef<AssetFreshness>[]>(
    () => [
      { accessorKey: 'symbol', header: 'Asset', cell: ({ getValue }) => <span className="font-mono text-fg">{getValue<string>()}</span> },
      { accessorKey: 'instrument_type', header: 'Type', cell: ({ getValue }) => <Badge variant="neutral">{getValue<string>()}</Badge> },
      {
        id: 'last_bar_ts',
        header: 'Last Bar',
        accessorFn: (a) => (a.last_bar_ts ? new Date(a.last_bar_ts).getTime() : -Infinity),
        cell: ({ row }) => <span className="whitespace-nowrap text-fg-muted">{row.original.last_bar_ts ? formatTimestamp(row.original.last_bar_ts) : '—'}</span>,
      },
      {
        id: 'bar_count',
        header: 'Count',
        accessorFn: (a) => a.bar_count,
        cell: ({ row }) => formatCount(row.original.bar_count),
        meta: { numeric: true },
      },
      {
        id: 'staleness',
        header: 'Staleness',
        accessorFn: (a) => a.staleness_seconds ?? Infinity,
        cell: ({ row }) => fmtDuration(row.original.staleness_seconds),
        meta: { numeric: true },
      },
      {
        accessorKey: 'status',
        header: 'Status',
        cell: ({ getValue }) => <Badge variant={freshnessVariant(getValue<FreshnessStatus>())}>{getValue<FreshnessStatus>()}</Badge>,
      },
    ],
    [],
  )

  const fundingColumns = useMemo<InstitutionalColumnDef<FundingFreshness>[]>(
    () => [
      { accessorKey: 'symbol', header: 'Asset', cell: ({ getValue }) => <span className="font-mono text-fg">{getValue<string>()}</span> },
      {
        id: 'last_funding_ts',
        header: 'Last Funding',
        accessorFn: (f) => (f.last_funding_ts ? new Date(f.last_funding_ts).getTime() : -Infinity),
        cell: ({ row }) => <span className="whitespace-nowrap text-fg-muted">{row.original.last_funding_ts ? formatTimestamp(row.original.last_funding_ts) : '—'}</span>,
      },
      {
        id: 'staleness',
        header: 'Staleness',
        accessorFn: (f) => f.staleness_seconds ?? Infinity,
        cell: ({ row }) => fmtDuration(row.original.staleness_seconds),
        meta: { numeric: true },
      },
      {
        accessorKey: 'status',
        header: 'Status',
        cell: ({ getValue }) => <Badge variant={freshnessVariant(getValue<FreshnessStatus>())}>{getValue<FreshnessStatus>()}</Badge>,
      },
    ],
    [],
  )

  return (
    <Section icon={<Database size={16} />} title="Data pipeline" description="Ingestion freshness — green <1h, amber 1-24h, red >24h.">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Panel className="overflow-hidden">
          {assets.length === 0 ? (
            <EmptyState title="No assets" description="No active instruments are registered." />
          ) : (
            <InstitutionalTable data={assets} columns={assetColumns} getRowId={(a) => a.asset_id} searchPlaceholder="Search assets…" exportFilename="ingestion-freshness" />
          )}
        </Panel>
        <Panel className="overflow-hidden">
          {funding.length === 0 ? (
            <EmptyState title="No perpetual instruments" description="Funding-rate freshness only applies to PERPETUAL instruments." />
          ) : (
            <InstitutionalTable data={funding} columns={fundingColumns} getRowId={(f) => f.asset_id} searchPlaceholder="Search…" exportFilename="funding-freshness" />
          )}
        </Panel>
      </div>
    </Section>
  )
}

// ── Section 3: Strategy Lifecycle ───────────────────────────────────────
function StrategyLifecycleSection({ strategies }: { strategies: StrategyLifecycle[] }) {
  const columns = useMemo<InstitutionalColumnDef<StrategyLifecycle>[]>(
    () => [
      { accessorKey: 'name', header: 'Strategy', cell: ({ getValue }) => <span className="font-medium text-fg">{getValue<string>()}</span> },
      {
        accessorKey: 'status',
        header: 'Status',
        cell: ({ getValue }) => <Badge variant={getValue<string>() === 'ACTIVE' ? 'profit' : 'neutral'}>{getValue<string>()}</Badge>,
      },
      {
        id: 'last_signal_ts',
        header: 'Last Signal',
        accessorFn: (s) => (s.last_signal_ts ? new Date(s.last_signal_ts).getTime() : -Infinity),
        cell: ({ row }) => <span className="whitespace-nowrap text-fg-muted">{row.original.last_signal_ts ? formatTimestamp(row.original.last_signal_ts) : '—'}</span>,
      },
      {
        id: 'signals_24h',
        header: 'Signals 24h',
        accessorFn: (s) => s.signals_24h,
        cell: ({ row }) => formatCount(row.original.signals_24h),
        meta: { numeric: true },
      },
      {
        id: 'valid_rate_24h',
        header: 'Valid Rate 24h',
        accessorFn: (s) => s.valid_rate_24h ?? -1,
        cell: ({ row }) => (row.original.valid_rate_24h != null ? formatRatio(row.original.valid_rate_24h) : '—'),
        meta: { numeric: true },
      },
      {
        accessorKey: 'latest_backtest_status',
        header: 'Backtest Status',
        cell: ({ getValue }) => {
          const value = getValue<string | null>()
          return value ? <Badge variant={value === 'COMPLETED' ? 'profit' : value === 'FAILED' ? 'risk' : 'info'}>{value}</Badge> : <span className="text-fg-muted">—</span>
        },
      },
    ],
    [],
  )

  return (
    <Section icon={<Brain size={16} />} title="Strategy lifecycle" description="Registration status, signal frequency, and latest backtest per strategy.">
      <Panel className="overflow-hidden">
        {strategies.length === 0 ? (
          <EmptyState title="No strategies" description="No strategies are registered yet." />
        ) : (
          <InstitutionalTable data={strategies} columns={columns} getRowId={(s) => s.strategy_id} searchPlaceholder="Search strategies…" exportFilename="strategy-lifecycle" />
        )}
      </Panel>
    </Section>
  )
}

// Honesty caveat (owner-requested fix, mirrors HeroSection.tsx's
// ACCURACY_CAVEAT): analytics.ml_models.metrics.accuracy is MODEL.evaluate()
// scored on its OWN training set (api/ml.py's _run_training) — not a held-
// out/out-of-sample split. Never let a 1.00 here read as real predictive
// performance.
const ACCURACY_CAVEAT = 'Training accuracy — not validated out-of-sample.'

// ── Section 4: ML Operations ─────────────────────────────────────────────
function MLOpsSection({ models, jobs }: { models: MLModelStatus[]; jobs: TrainingJob[] }) {
  const modelColumns = useMemo<InstitutionalColumnDef<MLModelStatus>[]>(
    () => [
      { accessorKey: 'name', header: 'Model', cell: ({ getValue }) => <span className="font-mono text-fg">{getValue<string>()}</span> },
      { accessorKey: 'model_type', header: 'Type', cell: ({ getValue }) => <span className="text-fg-muted">{getValue<string>()}</span> },
      {
        accessorKey: 'status',
        header: 'Status',
        cell: ({ getValue }) => <Badge variant={getValue<string>() === 'DEPLOYED' ? 'profit' : 'neutral'}>{getValue<string>()}</Badge>,
      },
      {
        id: 'accuracy',
        header: () => <span title={ACCURACY_CAVEAT}>Accuracy*</span>,
        accessorFn: (m) => m.accuracy ?? -1,
        cell: ({ row }) =>
          row.original.accuracy != null ? (
            <span title={ACCURACY_CAVEAT}>{formatRatio(row.original.accuracy)}</span>
          ) : (
            '—'
          ),
        meta: { numeric: true },
      },
      {
        id: 'created_at',
        header: 'Registered',
        accessorFn: (m) => new Date(m.created_at).getTime(),
        cell: ({ row }) => <span className="whitespace-nowrap text-fg-muted">{formatTimestamp(row.original.created_at)}</span>,
      },
    ],
    [],
  )

  return (
    <Section
      icon={<Cpu size={16} />}
      title="ML operations"
      description={`Model registry (analytics.ml_models) and in-flight training jobs. * ${ACCURACY_CAVEAT}`}
    >
      <div className="space-y-4">
        <Panel className="overflow-hidden">
          {models.length === 0 ? (
            <EmptyState title="No trained models" description="No models have been registered yet — this list populates once a training job completes." />
          ) : (
            <InstitutionalTable data={models} columns={modelColumns} getRowId={(m) => m.model_id} searchPlaceholder="Search models…" exportFilename="ml-model-registry" />
          )}
        </Panel>

        {jobs.length > 0 && (
          <Panel className="divide-y divide-border/60 overflow-hidden">
            {jobs.map((j) => (
              <div key={j.job_id} className="flex items-center justify-between gap-3 px-4 py-2.5 text-sm">
                <div className="min-w-0">
                  <span className="font-mono text-xs text-fg-subtle" title={j.job_id}>{j.job_id.slice(0, 8)}…</span>
                  <span className="ml-2 text-fg">{j.model_type}</span>
                </div>
                <Badge variant="info">{j.status}</Badge>
              </div>
            ))}
          </Panel>
        )}
      </div>
    </Section>
  )
}

// ── Section 5: System Timeline ───────────────────────────────────────────
// Composed client-side from /status's already-fetched data — Hermes's own
// endpoints are aggregate-shaped (latest-per-strategy, latest-per-asset),
// not a raw event log, so "last 10 signals/backtests/ingestion events" here
// means the 10 most recent entries across those three per-entity latest-
// activity timestamps, not 10 of each individually. Every timestamp is real
// (Doc 00 §14.5/§14.7) — nothing synthesized to pad the list.
type TimelineEvent = { id: string; kind: 'signal' | 'backtest' | 'ingestion'; label: string; ts: string }

function buildTimeline(status: NonNullable<ReturnType<typeof useHermesStatus>['data']>): TimelineEvent[] {
  const events: TimelineEvent[] = []
  for (const s of status.strategies) {
    if (s.last_signal_ts) events.push({ id: `sig-${s.strategy_id}`, kind: 'signal', label: `Signal · ${s.name}`, ts: s.last_signal_ts })
    if (s.latest_backtest_completed_at) {
      events.push({
        id: `bt-${s.strategy_id}`,
        kind: 'backtest',
        label: `Backtest ${s.latest_backtest_status?.toLowerCase() ?? 'completed'} · ${s.name}`,
        ts: s.latest_backtest_completed_at,
      })
    }
  }
  for (const a of status.assets) {
    if (a.last_bar_ts) events.push({ id: `bar-${a.asset_id}`, kind: 'ingestion', label: `Bar ingested · ${a.symbol}`, ts: a.last_bar_ts })
  }
  return events.sort((a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime()).slice(0, 10)
}

const TIMELINE_ICON: Record<TimelineEvent['kind'], typeof SignalIcon> = {
  signal: SignalIcon,
  backtest: GitCommit,
  ingestion: Radio,
}

function SystemTimeline({ status }: { status: NonNullable<ReturnType<typeof useHermesStatus>['data']> }) {
  const events = useMemo(() => buildTimeline(status), [status])

  return (
    <Section icon={<Activity size={16} />} title="System timeline" description="Most recent signal, backtest, and ingestion activity across every strategy/asset.">
      <Panel className="overflow-hidden">
        {events.length === 0 ? (
          <EmptyState title="No recent activity" description="Nothing to show yet — signals, backtests, and ingested bars will appear here as they happen." />
        ) : (
          <div className="divide-y divide-border/60">
            {events.map((e) => {
              const Icon = TIMELINE_ICON[e.kind]
              return (
                <div key={e.id} className="flex items-center gap-3 px-4 py-2.5">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-accent-soft text-accent">
                    <Icon size={14} />
                  </span>
                  <span className="min-w-0 flex-1 truncate text-sm text-fg">{e.label}</span>
                  <span className="shrink-0 text-[11px] text-fg-subtle">{formatTimestamp(e.ts)}</span>
                </div>
              )
            })}
          </div>
        )}
      </Panel>
    </Section>
  )
}
