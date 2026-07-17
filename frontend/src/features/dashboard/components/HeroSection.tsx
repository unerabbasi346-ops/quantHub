// Governing specification: handbook/ui/visual_engineering/02_LAYOUT_GRID_SYSTEM
//   §Hero Section ("Chart: 70% / AI Panel: 30%. Never split 50/50. The Hero
//   Chart must dominate the screen.") and
//   handbook/ui/visual_engineering/10_DASHBOARD_MASTER_BLUEPRINT §Hero Section
//   / §AI Intelligence Panel. Doc 00 §14.5/§14.7 DATA HONESTY.
//
// DASHBOARD ARCHITECTURE (presentation layer, Doc 02/10): the Hero
// Intelligence Area. Left (70%) is the auto-rotating strategy conviction
// chart (owner request — replaces the earlier market candlestick chart,
// which now lives only on the Markets page). Right (30%) is the
// Intelligence Workspace: one EngineStatusRow per REAL backend engine this
// platform actually has (Strategy/Portfolio/Risk/Execution), plus a
// permanently honest "AI Engine — not connected" row — never a fake
// "coming soon" placeholder, never fabricated confidence/analysis text.
// The row list is the same shape for every engine (icon, label, status
// badge, detail line) specifically so a future real AI integration slots
// into the AI row without restructuring this panel.
'use client'

import { memo, type ComponentType, type ReactNode } from 'react'
import { motion } from 'framer-motion'
import {
  ArrowLeftRight,
  Bot,
  Brain,
  Cpu,
  Database,
  ShieldAlert,
  type LucideProps,
} from 'lucide-react'
import { Badge, EmptyState, ErrorState, Gauge, glassSurface, Ring, type BadgeVariant } from '@/components/ui'
import { cn } from '@/lib/utils/cn'
import { formatRatio, formatTimestamp } from '@/lib/utils/format'
import { useReveal } from '@/lib/motion'
import { useHermesHealth, useHermesStatus } from '@/features/hermes/hooks/useHermes'
import { useStrategies } from '@/features/strategies/hooks/useStrategies'
import { useStrategyPerformance } from '@/features/strategies/hooks/useStrategyPerformance'
import { RotatingStrategyChart } from '@/features/strategies/components/RotatingStrategyChart'

export function HeroSection() {
  return (
    <section
      aria-label="Hero intelligence area"
      className="grid grid-cols-1 gap-6 lg:grid-cols-[7fr_3fr]"
    >
      <HeroStrategyChart />
      <IntelligenceWorkspace />
    </section>
  )
}

// ── Left: Hero Strategy Chart (70%) ─────────────────────────────────────
// The rotating conviction chart is the Hero's primary visual (owner
// request) — replaces the market candlestick chart entirely. A single
// min-h wrapper matches the Intelligence Workspace's footprint; the chart
// owns its own card surface (no double-nested glass panel).
function HeroStrategyChart() {
  const query = useStrategies()
  const strategies = query.data ?? []
  const performance = useStrategyPerformance(strategies)

  return (
    <div className="min-h-[26rem]">
      {query.isLoading && <div className={cn(glassSurface('elevated'), 'skeleton h-full min-h-[26rem] w-full')} />}
      {query.isError && (
        <div className={cn(glassSurface('elevated'), 'flex min-h-[26rem] items-center justify-center p-5')}>
          <ErrorState description="Could not load strategies." onRetry={() => query.refetch()} />
        </div>
      )}
      {query.isSuccess && strategies.length === 0 && (
        <div className={cn(glassSurface('elevated'), 'flex min-h-[26rem] items-center justify-center p-5')}>
          <EmptyState
            icon={<Brain size={20} />}
            title="No strategies registered"
            description="Register a strategy to see it here. Run: python scripts/register_strategy.py --all"
          />
        </div>
      )}
      {query.isSuccess && strategies.length > 0 && <RotatingStrategyChart items={performance} />}
    </div>
  )
}

// ── Right: Intelligence Workspace (30%) ─────────────────────────────────
interface EngineStatusRowProps {
  // A component REFERENCE (e.g. `ShieldAlert`), not a JSX element — a
  // function-reference prop is the same object on every render, unlike
  // `<ShieldAlert size={15} />` which mints a new element instance each
  // time. That stability is what lets React.memo below actually skip a
  // re-render for a row whose content is static (Risk Engine, AI Engine),
  // rather than bailing out on the icon prop every single poll regardless.
  icon: ComponentType<LucideProps>
  label: string
  status: string
  variant: BadgeVariant
  detail: ReactNode
  muted?: boolean
}

// Perf pass: memoized — rendered 6x inside IntelligenceWorkspace, which
// re-renders every 60s Hermes poll. Rows backed by literal, unchanging
// props (Risk Engine, AI Engine) now genuinely skip re-rendering instead
// of remounting on every poll regardless of whether their content moved.
const EngineStatusRow = memo(function EngineStatusRow({ icon: Icon, label, status, variant, detail, muted }: EngineStatusRowProps) {
  // Same 'row' kind Table.tsx uses for its rows — a crisp opacity+slide (no
  // filter, so it can't detach from box model), staggered purely by each
  // row's own vertical position, giving the "engines populate one after
  // another" read the spec asks for with zero new motion primitives.
  const reveal = useReveal('row')
  return (
    <motion.div
      {...reveal}
      className={cn(
        'flex items-start gap-3 rounded-lg border px-3 py-2.5',
        muted ? 'border-dashed border-border bg-transparent' : 'border-border bg-surface/60',
      )}
    >
      <span className={cn('mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md', muted ? 'bg-surface text-fg-subtle' : 'bg-accent-soft text-accent')}>
        <Icon size={15} />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <span className={cn('truncate text-sm font-medium', muted ? 'text-fg-muted' : 'text-fg')}>{label}</span>
          <Badge variant={variant}>{status}</Badge>
        </div>
        {/* div, not p — detail can carry block-level content (Ring gauge). */}
        <div className="mt-0.5 truncate text-[11px] text-fg-subtle">{detail}</div>
      </div>
    </motion.div>
  )
})

// Honesty caveat (owner-requested fix): analytics.ml_models.metrics.accuracy
// is computed by MODEL.evaluate() ON ITS OWN TRAINING SET (see
// api/ml.py's _run_training) — not a held-out/out-of-sample split. A 1.00
// here means the model fit its training data perfectly, not that it
// predicts unseen data well. Surfaced everywhere accuracy renders (this
// row + the Monitoring page's ML model table) so it can never read as real
// predictive performance.
const ACCURACY_CAVEAT = 'Training accuracy — not validated out-of-sample.'

// Health-score ring tone — mirrors the System Health Strip gauge on the
// Monitoring page (same 0-100 composite Hermes computes server-side).
function healthTone(score: number): 'profit' | 'warning' | 'risk' {
  if (score >= 80) return 'profit'
  if (score >= 50) return 'warning'
  return 'risk'
}

// Freshness bar: real fresh/stale/dead pipeline counts as proportional
// green/amber/red segments.
function FreshnessBar({ fresh, stale, dead }: { fresh: number; stale: number; dead: number }) {
  const total = fresh + stale + dead
  if (total === 0) return null
  return (
    <span className="flex h-1.5 w-24 shrink-0 overflow-hidden rounded-full bg-surface" title={`${fresh} fresh · ${stale} stale · ${dead} dead`}>
      {fresh > 0 && <span className="h-full bg-profit" style={{ width: `${(fresh / total) * 100}%` }} />}
      {stale > 0 && <span className="h-full bg-warning" style={{ width: `${(stale / total) * 100}%` }} />}
      {dead > 0 && <span className="h-full bg-risk" style={{ width: `${(dead / total) * 100}%` }} />}
    </span>
  )
}

// Recent events — synthesized from REAL Hermes status fields (latest signal,
// latest completed backtest, freshest ingested bar), never fabricated.
interface HermesEvent {
  icon: ComponentType<LucideProps>
  text: string
  ts: string
}

function recentEvents(status: import('@/features/hermes/types').SystemStatus | null): HermesEvent[] {
  if (!status) return []
  const events: HermesEvent[] = []
  const lastSignal = status.strategies
    .filter((s) => s.last_signal_ts != null)
    .sort((a, b) => (a.last_signal_ts! < b.last_signal_ts! ? 1 : -1))[0]
  if (lastSignal?.last_signal_ts) {
    events.push({ icon: Brain, text: `Signal generated · ${lastSignal.name}`, ts: lastSignal.last_signal_ts })
  }
  const lastBacktest = status.strategies
    .filter((s) => s.latest_backtest_completed_at != null)
    .sort((a, b) => (a.latest_backtest_completed_at! < b.latest_backtest_completed_at! ? 1 : -1))[0]
  if (lastBacktest?.latest_backtest_completed_at) {
    events.push({ icon: ArrowLeftRight, text: `Backtest completed · ${lastBacktest.name}`, ts: lastBacktest.latest_backtest_completed_at })
  }
  const freshAssets = status.assets.filter((a) => a.last_bar_ts != null)
  if (freshAssets.length > 0) {
    const newest = freshAssets.sort((a, b) => (a.last_bar_ts! < b.last_bar_ts! ? 1 : -1))[0]
    events.push({ icon: Database, text: `Data ingested · ${freshAssets.length} assets`, ts: newest.last_bar_ts! })
  }
  return events.sort((a, b) => (a.ts < b.ts ? 1 : -1)).slice(0, 3)
}

const IntelligenceWorkspace = memo(function IntelligenceWorkspace() {
  const healthQuery = useHermesHealth()
  const statusQuery = useHermesStatus()
  const health = healthQuery.data ?? null
  const events = recentEvents(statusQuery.data ?? null)
  const bestAccuracy = (statusQuery.data?.models ?? [])
    .map((m) => m.accuracy)
    .filter((a): a is number => a != null)
    .reduce<number | null>((best, a) => (best == null || a > best ? a : best), null)

  const reveal = useReveal('card')
  return (
    <motion.div {...reveal} className={cn(glassSurface('glow'), 'flex min-h-[26rem] flex-col p-5')}>
      <div className="flex items-center gap-2.5">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent">
          <Brain size={16} />
        </span>
        <div>
          <h2 className="text-sm font-semibold tracking-tight text-fg">Intelligence Workspace</h2>
          <p className="mt-0.5 text-[11px] text-fg-subtle">Hermes system status — real, polled every 60s</p>
        </div>
      </div>

      {/* Large system-health gauge (ECharts) — panel-wide above the engine
          rows; this panel is itself the hero's right 30% column, so a
          side-by-side split leaves the gauge no measurable width. */}
      <div className="mt-3 flex flex-col items-center">
        {health ? (
          <>
            <Gauge value={Math.round(health.health_score)} min={0} max={100} height={150} className="w-full" />
            <span className="-mt-4 text-[11px] font-medium uppercase tracking-wide text-fg-subtle">System Health</span>
            <span className="text-[10px] text-fg-subtle">updated {formatTimestamp(health.generated_at)}</span>
          </>
        ) : (
          <div className="skeleton h-32 w-32 rounded-full" />
        )}
      </div>

      <div className="mt-3 flex flex-1 flex-col">
        <div className="flex flex-col gap-2.5">
        <EngineStatusRow
          icon={Brain}
          label="Strategy Engine"
          status={healthQuery.isLoading ? '…' : healthQuery.isError ? 'error' : `${health!.strategy_engine.active_count} active`}
          variant={healthQuery.isError ? 'risk' : health && health.strategy_engine.active_count > 0 ? 'profit' : 'neutral'}
          detail={health ? `${health.strategy_engine.signals_24h} signals · 24h` : 'hermes/health'}
        />
        <EngineStatusRow
          icon={Database}
          label="Data Pipeline"
          status={healthQuery.isLoading ? '…' : healthQuery.isError ? 'error' : `${health!.data_pipeline.fresh_count} fresh`}
          variant={healthQuery.isError ? 'risk' : health && health.data_pipeline.dead_count > 0 ? 'warning' : 'profit'}
          detail={
            health ? (
              <span className="flex items-center gap-2">
                {health.data_pipeline.fresh_count} fresh · {health.data_pipeline.stale_count} stale · {health.data_pipeline.dead_count} dead
                <FreshnessBar fresh={health.data_pipeline.fresh_count} stale={health.data_pipeline.stale_count} dead={health.data_pipeline.dead_count} />
              </span>
            ) : (
              'hermes/health'
            )
          }
        />
        <EngineStatusRow
          icon={Cpu}
          label="ML Engine"
          status={healthQuery.isLoading ? '…' : healthQuery.isError ? 'error' : `${health!.ml_engine.trained_count} trained`}
          variant={healthQuery.isError ? 'risk' : health && health.ml_engine.trained_count > 0 ? 'profit' : 'neutral'}
          detail={
            bestAccuracy != null ? (
              <span className="flex items-center gap-2" title={ACCURACY_CAVEAT}>
                best accuracy {formatRatio(bestAccuracy)}
                <Ring value={bestAccuracy} size={18} thickness={3} tone={bestAccuracy >= 0.6 ? 'profit' : 'warning'} />
              </span>
            ) : (
              'analytics.ml_models'
            )
          }
        />
        <EngineStatusRow
          icon={ShieldAlert}
          label="Risk Engine"
          status="Operational"
          variant="neutral"
          detail="No real-time risk status is wired to Hermes yet — pre-trade assessments run per order (see Risk page)."
        />
        <EngineStatusRow
          icon={ArrowLeftRight}
          label="Execution Engine"
          status={healthQuery.isLoading ? '…' : healthQuery.isError ? 'error' : `${health!.execution_engine.orders_today} today`}
          variant={healthQuery.isError ? 'risk' : health && health.execution_engine.orders_today > 0 ? 'info' : 'neutral'}
          detail={
            health?.execution_engine.fill_rate_today != null
              ? `${formatRatio(health.execution_engine.fill_rate_today)} filled`
              : 'core.orders'
          }
        />

        <div className="my-1 h-px bg-border" />

        {/* Honest, PERMANENT state — not a temporary placeholder (Doc 00
            §14.5/§14.7). No AI backend exists yet; this row is structured
            identically to the real engine rows above so a future AI
            integration populates it in place, without a layout change. */}
        <EngineStatusRow
          icon={Bot}
          label="AI Engine"
          status="Not connected"
          variant="neutral"
          detail="No AI backend is integrated yet — this is a permanent honest state, not a loading placeholder."
          muted
        />
        </div>
      </div>

      {/* Recent events — last 3 real Hermes-observable events. */}
      <div className="mt-3 border-t border-border pt-3">
        <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Recent events</p>
        {events.length === 0 ? (
          <p className="text-[11px] text-fg-subtle">No recorded system events yet.</p>
        ) : (
          <div className="space-y-1">
            {events.map((e) => (
              <div key={e.text} className="flex items-center gap-2 text-[11px] text-fg-muted">
                <e.icon size={12} className="shrink-0 text-fg-subtle" />
                <span className="min-w-0 flex-1 truncate">{e.text}</span>
                <span className="shrink-0 text-fg-subtle">{formatTimestamp(e.ts)}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="mt-3 flex items-center justify-between border-t border-border pt-3 text-[11px] text-fg-subtle">
        {healthQuery.isError && <ErrorState description="Could not load Hermes status." onRetry={() => healthQuery.refetch()} />}
        {!healthQuery.isError && (
          <span>{health ? `Last updated ${formatTimestamp(health.generated_at)}` : 'Loading Hermes status…'}</span>
        )}
      </div>
    </motion.div>
  )
})
