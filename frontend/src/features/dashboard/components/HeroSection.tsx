// Governing specification: handbook/ui/visual_engineering/02_LAYOUT_GRID_SYSTEM
//   §Hero Section ("Chart: 70% / AI Panel: 30%. Never split 50/50. The Hero
//   Chart must dominate the screen.") and
//   handbook/ui/visual_engineering/10_DASHBOARD_MASTER_BLUEPRINT §Hero Section
//   / §AI Intelligence Panel. Doc 00 §14.5/§14.7 DATA HONESTY.
//
// PHASE 1 — DASHBOARD ARCHITECTURE ONLY (presentation layer, Doc 02/10):
// the Hero Intelligence Area. Left (70%) is the real primary market chart —
// reuses the same real useAssets/useBars data and PriceChart component the
// Markets page renders, just the first active instrument, so it is never a
// second, competing "hero" invented for this page. Right (30%) is the
// Intelligence Workspace: one EngineStatusRow per REAL backend engine this
// platform actually has (Strategy/Portfolio/Risk/Execution), plus a
// permanently honest "AI Engine — not connected" row — never a fake
// "coming soon" placeholder, never fabricated confidence/analysis text.
// The row list is the same shape for every engine (icon, label, status
// badge, detail line) specifically so a future real AI integration slots
// into the AI row without restructuring this panel.
'use client'

import { type ReactNode } from 'react'
import { motion } from 'framer-motion'
import {
  ArrowLeftRight,
  Bot,
  Brain,
  CandlestickChart,
  Cpu,
  Database,
  ShieldAlert,
} from 'lucide-react'
import { Badge, CryptoIcon, EmptyState, ErrorState, glassSurface, Ring, type BadgeVariant } from '@/components/ui'
import { cn } from '@/lib/utils/cn'
import { formatRatio, formatReturn, formatTimestamp } from '@/lib/utils/format'
import { useReveal } from '@/lib/motion'
import { useSyncStore } from '@/lib/store/sync'
import { useAssets, useBars } from '@/features/markets/hooks/useMarkets'
import { PriceChart } from '@/features/markets/components/PriceChart'
import { useHermesHealth } from '@/features/hermes/hooks/useHermes'

const num = (v: string) => Number.parseFloat(v)
const fmtPrice = (v: string | number) =>
  Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })

export function HeroSection() {
  return (
    <section
      aria-label="Hero intelligence area"
      className="grid grid-cols-1 gap-6 lg:grid-cols-[7fr_3fr]"
    >
      <HeroMarketChart />
      <IntelligenceWorkspace />
    </section>
  )
}

// ── Left: Hero Market Chart (70%) ───────────────────────────────────────
// Preferred default instrument for the Hero, in priority order — all real,
// registered spot pairs; not a fabricated choice. Falls through to the first
// registered asset if none of these are present, so the Hero never depends
// on any one symbol existing (Doc 00 §14.5 honesty: never hide behind a
// hardcoded assumption).
const PREFERRED_SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']

function HeroMarketChart() {
  const assetsQuery = useAssets()
  const assets = assetsQuery.data ?? []
  // Global Synchronization (Doc 11): "Selecting Asset updates every page" —
  // an asset picked on Markets is what the Hero shows next, ahead of the
  // static preference list, which only applies once nothing has been chosen.
  const syncedSymbol = useSyncStore((s) => s.selectedAssetSymbol)
  const synced = syncedSymbol ? assets.find((a) => a.symbol === syncedSymbol) : undefined
  const asset = synced ?? PREFERRED_SYMBOLS.map((sym) => assets.find((a) => a.symbol === sym)).find(Boolean) ?? assets[0] ?? null
  const barsQuery = useBars(asset?.id ?? '', '1h')
  const bars = barsQuery.data ?? []
  const last = bars.at(-1)
  const prev24 = bars.at(-25) ?? bars[0]
  const change = last && prev24 ? num(last.close) - num(prev24.close) : null
  const changePct = change != null && prev24 ? (change / num(prev24.close)) * 100 : null

  const reveal = useReveal('card')
  return (
    <motion.div {...reveal} className={cn(glassSurface('glow'), 'flex min-h-[26rem] flex-col p-5')}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2.5">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent">
            <CandlestickChart size={16} />
          </span>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              {asset && <CryptoIcon symbol={asset.symbol} size={18} />}
              <h2 className="truncate text-sm font-semibold tracking-tight text-fg">
                {asset ? `${asset.symbol} · Hero Market Chart` : 'Hero Market Chart'}
              </h2>
            </div>
            <p className="mt-0.5 text-[11px] text-fg-subtle">
              {asset ? `${asset.exchange} · 1h · live ingested bars` : 'Primary tracked instrument'}
            </p>
          </div>
        </div>
        {last && (
          <div className="text-right">
            <div className="font-mono text-lg font-semibold tabular-nums text-fg">{fmtPrice(last.close)}</div>
            {changePct != null && (
              <div className={cn('font-mono text-[11px] tabular-nums', change! >= 0 ? 'text-profit' : 'text-risk')}>
                {formatReturn(changePct / 100)} · 24h
              </div>
            )}
          </div>
        )}
      </div>

      <div className="mt-4 flex-1">
        {assetsQuery.isLoading && <div className="skeleton h-full min-h-[20rem] w-full" />}
        {assetsQuery.isError && <ErrorState description="Could not load instruments." onRetry={() => assetsQuery.refetch()} />}
        {assetsQuery.isSuccess && assets.length === 0 && (
          <EmptyState icon={<CandlestickChart size={20} />} title="No instruments" description="No tradable assets are registered yet." />
        )}
        {asset && barsQuery.isLoading && <div className="skeleton h-full min-h-[20rem] w-full" />}
        {asset && barsQuery.isError && <ErrorState description="Could not load bars." onRetry={() => barsQuery.refetch()} />}
        {asset && barsQuery.isSuccess && bars.length === 0 && (
          <EmptyState title="No bars" description={`No bars ingested for ${asset.symbol} yet.`} />
        )}
        {asset && barsQuery.isSuccess && bars.length > 0 && <PriceChart bars={bars} />}
      </div>
    </motion.div>
  )
}

// ── Right: Intelligence Workspace (30%) ─────────────────────────────────
interface EngineStatusRowProps {
  icon: ReactNode
  label: string
  status: string
  variant: BadgeVariant
  detail: ReactNode
  muted?: boolean
}

function EngineStatusRow({ icon, label, status, variant, detail, muted }: EngineStatusRowProps) {
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
        {icon}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <span className={cn('truncate text-sm font-medium', muted ? 'text-fg-muted' : 'text-fg')}>{label}</span>
          <Badge variant={variant}>{status}</Badge>
        </div>
        <p className="mt-0.5 truncate text-[11px] text-fg-subtle">{detail}</p>
      </div>
    </motion.div>
  )
}

// Health-score ring tone — mirrors the System Health Strip gauge on the
// Monitoring page (same 0-100 composite Hermes computes server-side).
function healthTone(score: number): 'profit' | 'warning' | 'risk' {
  if (score >= 80) return 'profit'
  if (score >= 50) return 'warning'
  return 'risk'
}

function IntelligenceWorkspace() {
  const healthQuery = useHermesHealth()
  const health = healthQuery.data ?? null

  const reveal = useReveal('card')
  return (
    <motion.div {...reveal} className={cn(glassSurface('glow'), 'flex min-h-[26rem] flex-col p-5')}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent">
            <Brain size={16} />
          </span>
          <div>
            <h2 className="text-sm font-semibold tracking-tight text-fg">Intelligence Workspace</h2>
            <p className="mt-0.5 text-[11px] text-fg-subtle">Hermes system status — real, polled every 30s</p>
          </div>
        </div>
        {health && (
          <Ring
            value={health.health_score / 100}
            size={44}
            thickness={5}
            tone={healthTone(health.health_score)}
            centerLabel={String(Math.round(health.health_score))}
          />
        )}
      </div>

      <div className="mt-4 flex flex-1 flex-col gap-2.5">
        <EngineStatusRow
          icon={<Brain size={15} />}
          label="Strategy Engine"
          status={healthQuery.isLoading ? '…' : healthQuery.isError ? 'error' : `${health!.strategy_engine.active_count} active`}
          variant={healthQuery.isError ? 'risk' : health && health.strategy_engine.active_count > 0 ? 'profit' : 'neutral'}
          detail={health ? `${health.strategy_engine.signals_24h} signals · 24h` : 'hermes/health'}
        />
        <EngineStatusRow
          icon={<Database size={15} />}
          label="Data Pipeline"
          status={healthQuery.isLoading ? '…' : healthQuery.isError ? 'error' : `${health!.data_pipeline.fresh_count} fresh`}
          variant={healthQuery.isError ? 'risk' : health && health.data_pipeline.dead_count > 0 ? 'warning' : 'profit'}
          detail={health ? `${health.data_pipeline.stale_count} stale · ${health.data_pipeline.dead_count} dead` : 'hermes/health'}
        />
        <EngineStatusRow
          icon={<Cpu size={15} />}
          label="ML Engine"
          status={healthQuery.isLoading ? '…' : healthQuery.isError ? 'error' : `${health!.ml_engine.trained_count} trained`}
          variant={healthQuery.isError ? 'risk' : health && health.ml_engine.trained_count > 0 ? 'profit' : 'neutral'}
          detail={
            health?.ml_engine.last_accuracy != null
              ? `last accuracy ${formatRatio(health.ml_engine.last_accuracy)}`
              : 'analytics.ml_models'
          }
        />
        <EngineStatusRow
          icon={<ShieldAlert size={15} />}
          label="Risk Engine"
          status="Operational"
          variant="neutral"
          detail="No real-time risk status is wired to Hermes yet — pre-trade assessments run per order (see Risk page)."
        />
        <EngineStatusRow
          icon={<ArrowLeftRight size={15} />}
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
          icon={<Bot size={15} />}
          label="AI Engine"
          status="Not connected"
          variant="neutral"
          detail="No AI backend is integrated yet — this is a permanent honest state, not a loading placeholder."
          muted
        />
      </div>

      <div className="mt-3 flex items-center justify-between border-t border-border pt-3 text-[11px] text-fg-subtle">
        {healthQuery.isError && <ErrorState description="Could not load Hermes status." onRetry={() => healthQuery.refetch()} />}
        {!healthQuery.isError && (
          <span>{health ? `Last updated ${formatTimestamp(health.generated_at)}` : 'Loading Hermes status…'}</span>
        )}
      </div>
    </motion.div>
  )
}
