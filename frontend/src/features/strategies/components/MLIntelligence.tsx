// Governing specification: Doc 00 §14.5/§14.7 DATA HONESTY — every figure
//   below reads a real field off Signal (api/v1/strategies.py's SignalOut
//   ml_* fields) or Hermes's model registry (/api/hermes/ml); nothing here
//   is fabricated. ml_tp_suggestion/ml_sl_suggestion/ml_breakeven are
//   labeled "ML-suggested" throughout — they are sizing/level SUGGESTIONS,
//   never executed order levels.
//
// ARCHITECTURE NOTE (flagged deviation): the task asked for this to land as
// a tab "alongside the existing Overview/Performance/Signals/Backtest
// tabs" on the Strategy detail page — but that page (StrategyDetailShell)
// has never been tab-based; it's one continuous scroll of Sections (see
// its own module docstring: "six sections"). Retrofitting the whole page
// into a tab system was out of scope for this fix, so this renders as a
// new, prominent standalone Section instead — same visual weight the task
// asked for, without an unrelated page-architecture rewrite.
'use client'

import { Fragment } from 'react'
import Link from 'next/link'
import { Brain, Cpu, TrendingDown, TrendingUp, Zap } from 'lucide-react'
import { Badge, Card, EmptyState, Panel, Section, type BadgeVariant } from '@/components/ui'
import { cn } from '@/lib/utils/cn'
import { formatCapital, formatRatio, formatSignalStrength, formatTimestamp } from '@/lib/utils/format'
import { useHermesMl } from '@/features/hermes/hooks/useHermes'
import type { MLModelStatus } from '@/features/hermes/types'
import { mlConfidencePoints } from '../analytics'
import type { Signal } from '../types'
import { MLConfidenceScatterChart } from './charts'

// Mirrors HeroSection.tsx/MonitoringShell.tsx's ACCURACY_CAVEAT — the model
// registry's `accuracy` is scored on the model's OWN training set
// (api/ml.py's _run_training), not a held-out split.
const ACCURACY_CAVEAT = 'Training accuracy — not validated out-of-sample.'

function num(v: string | null): number | null {
  return v == null ? null : Number.parseFloat(v)
}

function confidenceTone(pct: number): 'profit' | 'warning' | 'risk' {
  if (pct >= 70) return 'profit'
  if (pct >= 50) return 'warning'
  return 'risk'
}

function ConfidenceBar({ label, fraction }: { label: string; fraction: number }) {
  const pct = fraction * 100
  const tone = confidenceTone(pct)
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-fg-subtle">{label}</span>
        <span className={cn('font-mono font-semibold tabular-nums', tone === 'profit' ? 'text-profit' : tone === 'warning' ? 'text-warning' : 'text-risk')}>
          {pct.toFixed(0)}%
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface">
        <div
          className={cn('h-full rounded-full', tone === 'profit' ? 'bg-profit' : tone === 'warning' ? 'bg-warning' : 'bg-risk')}
          style={{ width: `${Math.min(100, Math.max(0, pct))}%` }}
        />
      </div>
    </div>
  )
}

// Risk/Reward, computed exactly from real ml_tp_suggestion/ml_sl_suggestion/
// ml_breakeven — never fabricated when any of the three is missing or the
// implied denominator is non-positive (a degenerate suggestion window).
function riskReward(direction: string, entry: number | null, tp: number | null, sl: number | null): number | null {
  if (entry == null || tp == null || sl == null) return null
  const isLong = direction.toUpperCase() === 'LONG'
  const reward = isLong ? tp - entry : entry - tp
  const risk = isLong ? entry - sl : sl - entry
  if (risk <= 0) return null
  return reward / risk
}

// Quality badge (FIX 9): TRADE green / REVIEW amber / SKIP gray — read
// straight off SignalOut's real quality_recommendation.
function qualityVariant(rec: string | null): BadgeVariant {
  if (rec === 'TRADE') return 'profit'
  if (rec === 'REVIEW') return 'warning'
  return 'neutral'
}

// Mirrors backend Rule 1 (domain/backtesting/trade_rules.py): 2% of capital
// default, 3% when ml_confidence > 0.70 — derived from the same field the
// backend reads, not a second source of truth.
const sizePctLabel = (confidence: number | null) => (confidence != null && confidence > 0.7 ? '3% acct' : '2% acct')

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-2 text-[11px]">
      <span className="text-fg-subtle">{label}</span>
      <span className="font-mono tabular-nums text-fg">{value}</span>
    </div>
  )
}

function SignalCard({ signal, symbol }: { signal: Signal; symbol: string | null }) {
  const isLong = signal.direction.toUpperCase() === 'LONG'
  const value = Number.parseFloat(signal.value)
  const confidence = num(signal.ml_confidence)
  const probability = num(signal.ml_probability)
  const tp = num(signal.ml_tp_suggestion)
  const sl = num(signal.ml_sl_suggestion)
  const breakeven = num(signal.ml_breakeven)
  const rr = riskReward(signal.direction, breakeven, tp, sl)
  const hasMl = confidence != null
  const size = signal.implied_size_usdt != null ? Number.parseFloat(signal.implied_size_usdt) : null
  const quality = signal.quality_recommendation

  return (
    <Card
      elevation="elevated"
      className={cn('space-y-3 border-l-4 p-4', isLong ? 'border-l-profit' : 'border-l-risk')}
    >
      {/* Direction large, date right — immediately interpretable hierarchy. */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          {isLong ? <TrendingUp size={18} className="text-profit" /> : <TrendingDown size={18} className="text-risk" />}
          <span className={cn('text-lg font-bold tracking-tight', isLong ? 'text-profit' : 'text-risk')}>{signal.direction.toUpperCase()}</span>
        </div>
        <span className="mt-1 shrink-0 text-[11px] text-fg-subtle">{formatTimestamp(signal.ts)}</span>
      </div>
      {symbol && <div className="font-mono text-sm text-fg-muted">{symbol}</div>}

      <div className="space-y-1.5 border-t border-border pt-3">
        <DetailRow
          label="Alpha Score"
          value={<span className={value >= 0 ? 'text-profit' : 'text-risk'}>{formatSignalStrength(value)}</span>}
        />
        <DetailRow
          label="Implied size"
          value={size != null ? `${formatCapital(size)} (${sizePctLabel(confidence)})` : '—'}
        />
        <DetailRow
          label="ML analysis"
          value={hasMl ? `${(confidence! * 100).toFixed(0)}% confidence` : <span className="font-sans text-fg-subtle">Not available</span>}
        />
        <DetailRow label="Suggested TP" value={tp != null ? formatCapital(tp) : '—'} />
        <DetailRow label="Suggested SL" value={sl != null ? formatCapital(sl) : '—'} />
        <div className="flex items-center justify-between gap-2 text-[11px]">
          <span className="text-fg-subtle">Quality</span>
          {quality ? <Badge variant={qualityVariant(quality)}>{quality}</Badge> : <span className="font-mono text-fg">—</span>}
        </div>
      </div>

      {hasMl && (
        <div className="space-y-2.5 border-t border-border pt-3">
          <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-fg-subtle">
            <Zap size={11} /> ML detail
          </div>
          <ConfidenceBar label="ML confidence" fraction={confidence!} />
          {probability != null && <ConfidenceBar label="ML probability" fraction={probability} />}
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-fg-subtle">Direction agreement</span>
            <span className={cn('font-medium', signal.ml_direction_agreement ? 'text-profit' : 'text-risk')}>
              {signal.ml_direction_agreement == null ? '—' : signal.ml_direction_agreement ? '✓ Yes' : '✗ No'}
            </span>
          </div>
          {breakeven != null && <DetailRow label="Breakeven" value={formatCapital(breakeven)} />}
          <DetailRow label="Risk/Reward" value={rr != null ? `${rr.toFixed(1)}:1` : '—'} />
        </div>
      )}
    </Card>
  )
}

function modelStatusVariant(status: string): BadgeVariant {
  return status === 'DEPLOYED' ? 'profit' : 'neutral'
}

const pct1 = (v: number) => `${(v * 100).toFixed(2)}%`

function ModelPerformancePanel({ models, isLoading }: { models: MLModelStatus[]; isLoading: boolean }) {
  // Prefer a DEPLOYED XGBoost_MetaLabeler (the model type that actually
  // scores signals, per SignalOut's docstring); fall back to the most
  // recent model of any type/status so this panel still shows something
  // real if nothing is deployed yet.
  const model =
    models.find((m) => m.status === 'DEPLOYED' && m.model_type === 'XGBoost_MetaLabeler')
    ?? models.find((m) => m.model_type === 'XGBoost_MetaLabeler')
    ?? models[0]
    ?? null

  if (isLoading) return <div className="skeleton h-32 w-full" />

  if (!model) {
    return (
      <Panel className="flex items-center justify-between gap-3 p-5">
        <div>
          <div className="text-sm font-medium text-fg">No model trained yet</div>
          <p className="mt-1 text-xs text-fg-muted">Go to the Research page to train a model.</p>
        </div>
        <Link href="/research" className="shrink-0 rounded-lg border border-border bg-surface-raised/60 px-3 py-1.5 text-xs font-medium text-fg hover:border-border-strong">
          Research →
        </Link>
      </Panel>
    )
  }

  const deployed = model.status === 'DEPLOYED'
  const underperforms = model.accuracy != null && model.baseline != null && model.accuracy <= model.baseline

  return (
    <Panel className="space-y-3 p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Cpu size={15} className="text-fg-subtle" />
          <span className="font-mono text-sm text-fg">{model.model_type}</span>
          <Badge variant={deployed ? 'profit' : 'warning'}>{deployed ? 'DEPLOYED' : 'NOT DEPLOYED'}</Badge>
        </div>
        <span className="text-[11px] text-fg-subtle">trained {formatTimestamp(model.created_at)}</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-[11px] uppercase tracking-wide text-fg-subtle">Accuracy</span>
        <span className="font-mono text-sm font-semibold text-fg" title={ACCURACY_CAVEAT}>
          {model.accuracy != null ? formatRatio(model.accuracy) : '—'}
        </span>
        {model.baseline != null && (
          <span className="text-[11px] text-fg-subtle">vs majority baseline <span className="font-mono">{formatRatio(model.baseline)}</span></span>
        )}
      </div>
      {!deployed && (
        <p className="text-[11px] leading-relaxed text-fg-muted">
          {underperforms && model.accuracy != null && model.baseline != null
            ? `Not deployed: accuracy (${pct1(model.accuracy)}) is below the majority-class baseline (${pct1(model.baseline)}) — deploying it would score signals worse than always guessing the most common outcome.`
            : 'Not deployed — the deploy gate only promotes a model that beats its majority-class baseline.'}
        </p>
      )}
      <div className="flex items-center justify-between gap-3 border-t border-border pt-3">
        <span className="text-[11px] text-fg-subtle">Retrain with more data to try to beat the baseline.</span>
        <Link href="/research" className="shrink-0 rounded-lg border border-border bg-surface-raised/60 px-3 py-1.5 text-xs font-medium text-fg transition-colors hover:border-border-strong">
          Retrain on Research page →
        </Link>
      </div>
    </Panel>
  )
}

function RegimePanel({ models, isLoading }: { models: MLModelStatus[]; isLoading: boolean }) {
  const hmm = models.find((m) => m.model_type === 'HMM_RegimeDetector')

  if (isLoading) return <div className="skeleton h-28 w-full" />

  if (!hmm) {
    return (
      <div className="flex flex-col items-center gap-3">
        <EmptyState
          icon={<Brain size={20} />}
          title="No regime model"
          description="Train HMMRegimeDetector on the Research page to enable market regime detection."
        />
        <Link href="/research" className="rounded-lg border border-border bg-surface-raised/60 px-3 py-1.5 text-xs font-medium text-fg transition-colors hover:border-border-strong">
          Train on Research page →
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm text-fg">{hmm.model_type}</span>
          <Badge variant={modelStatusVariant(hmm.status)}>{hmm.status}</Badge>
        </div>
        <span className="text-[11px] text-fg-subtle">trained {formatTimestamp(hmm.created_at)}</span>
      </div>
      <p className="text-[11px] leading-relaxed text-fg-subtle">
        A regime model is registered, but no live regime-inference endpoint exists yet to classify the current bar or
        build a regime history — the platform doesn&apos;t persist per-bar regime predictions today. Shown honestly
        rather than a fabricated classification.
      </p>
    </div>
  )
}

export function MLIntelligenceSection({ signals, symbol }: { signals: Signal[]; symbol: string | null }) {
  const mlQuery = useHermesMl()
  const models = mlQuery.data?.models ?? []

  const recentSignals = [...signals].sort((a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime()).slice(0, 8)
  const confidencePoints = mlConfidencePoints(signals)

  // Real signal-period context (owner request): these are backtest-replay
  // signals, so state the actual period shown instead of implying live flow.
  const periodLabel = (() => {
    if (recentSignals.length === 0) return null
    const fmt = (ts: string) => new Date(ts).toLocaleDateString(undefined, { month: 'short', year: 'numeric' })
    const newest = fmt(recentSignals[0].ts)
    const oldest = fmt(recentSignals[recentSignals.length - 1].ts)
    return newest === oldest ? newest : `${oldest} – ${newest}`
  })()

  // Specific (not generic) explanation when the chart is empty because the
  // only trained model underperforms its baseline and so was never deployed.
  const metaModel = models.find((m) => m.model_type === 'XGBoost_MetaLabeler') ?? null
  const undeployedUnderperformer =
    metaModel && metaModel.status !== 'DEPLOYED' && metaModel.accuracy != null && metaModel.baseline != null

  return (
    <Section
      icon={<Zap size={16} />}
      title="ML Intelligence"
      description="Per-signal ML suggestions, current model performance, confidence over time, and regime detection — real values only."
    >
      <div className="space-y-6">
        {/* Section 1: signal cards */}
        <div>
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-fg-subtle">Recent signals</h3>
            {periodLabel && <Badge variant="neutral">Backtest signals — {periodLabel} period shown</Badge>}
          </div>
          {recentSignals.length === 0 ? (
            <Panel className="p-6">
              <EmptyState title="No signals" description="This strategy has emitted no signals yet." />
            </Panel>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {recentSignals.map((s) => (
                <Fragment key={s.id}>
                  <SignalCard signal={s} symbol={symbol} />
                </Fragment>
              ))}
            </div>
          )}
        </div>

        {/* Section 2: ML model performance */}
        <div>
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-fg-subtle">Model performance</h3>
          <ModelPerformancePanel models={models} isLoading={mlQuery.isLoading} />
        </div>

        {/* Section 3: confidence distribution over time */}
        <div>
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-fg-subtle">Signal confidence over time</h3>
          <Panel className="p-4">
            {confidencePoints.length === 0 && undeployedUnderperformer ? (
              <div className="flex h-[240px] flex-col items-center justify-center gap-1 px-6 text-center">
                <p className="text-sm text-fg-muted">
                  Confidence scores unavailable — the current model underperforms its baseline
                  ({(metaModel!.accuracy! * 100).toFixed(2)}% vs {(metaModel!.baseline! * 100).toFixed(2)}%) and was not deployed.
                </p>
                <p className="text-xs text-fg-subtle">Retrain with more data on the Research page.</p>
              </div>
            ) : (
              <MLConfidenceScatterChart points={confidencePoints} height={240} />
            )}
          </Panel>
        </div>

        {/* Section 4: market regime */}
        <div>
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-fg-subtle">Market regime</h3>
          <Panel className="p-5">
            <RegimePanel models={models} isLoading={mlQuery.isLoading} />
          </Panel>
        </div>
      </div>
    </Section>
  )
}
