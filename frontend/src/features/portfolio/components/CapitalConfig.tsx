// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Interaction Standards: clear primary action + success/error states.
// Doc 08 §Architecture: feature component composing the design system + a
//   mutation hook (the second real write flow in the dashboard).
// Per Doc 00 §14.11
//
// HONEST F-19 LABELING (the crux — flagged, Doc 00 §14.5/§14.7): this control
// sets an operator-configured capital figure that has NO backing NAV/cash
// ledger and does NOT feed leverage or any risk determination. The copy says
// so plainly so the number is never mistaken for real equity. F-19 stays open.
'use client'

import { useState } from 'react'
import { CircleDollarSign, Info } from 'lucide-react'
import { Badge, Button, Panel, Ring, Section } from '@/components/ui'
import { formatCapital } from '@/lib/utils/format'
import { useSetCapital } from '../hooks/usePortfolio'
import type { Portfolio } from '../types'

function fmtMoney(value: string | number): string {
  return formatCapital(Number(value))
}

// Capital Utilization — integrates the operator-set capital figure with REAL
// open-position market value (Doc 07 §Capital Efficiency, honestly scoped:
// only utilization/idle-capital are derivable from what the platform tracks
// today, not the full "Capital Rotation / Margin Usage" widget set).
function Utilization({ configuredCapital, openMarketValue }: { configuredCapital: string; openMarketValue: number }) {
  const capital = Number.parseFloat(configuredCapital)
  if (!(capital > 0)) return null
  const utilization = Math.min(openMarketValue / capital, 1)
  const idle = Math.max(capital - openMarketValue, 0)
  return (
    <div className="flex items-center gap-4 border-t border-border pt-4">
      <Ring value={utilization} size={64} thickness={7} tone={utilization > 0.9 ? 'warning' : 'info'} centerLabel={`${Math.round(utilization * 100)}%`} />
      <div className="min-w-0">
        <div className="text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Capital utilization</div>
        <div className="text-sm text-fg-muted">
          {fmtMoney(openMarketValue)} deployed of {fmtMoney(capital)} configured
        </div>
        <div className="text-[11px] text-fg-subtle">{fmtMoney(idle)} idle</div>
      </div>
    </div>
  )
}

export function CapitalConfig({ portfolio, openMarketValue = 0 }: { portfolio: Portfolio; openMarketValue?: number }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const mutation = useSetCapital(portfolio.id)

  const current = portfolio.configured_capital

  function submit() {
    const trimmed = draft.trim()
    if (!trimmed || Number(trimmed) <= 0) return
    mutation.mutate(trimmed, {
      onSuccess: () => {
        setEditing(false)
        setDraft('')
      },
    })
  }

  return (
    <Section
      title="Configured capital"
      actions={
        !editing && (
          <Button
            size="sm"
            variant="secondary"
            onClick={() => {
              setDraft(current ?? '')
              setEditing(true)
            }}
          >
            <CircleDollarSign size={15} />
            {current ? 'Edit capital' : 'Set capital'}
          </Button>
        )
      }
    >
      <Panel className="p-5">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="text-[11px] font-medium uppercase tracking-wider text-fg-subtle">
              Operator-set capital
            </div>
            <div className="mt-1 font-mono text-metric font-bold tabular-nums text-fg">
              {current ? (
                <>
                  {fmtMoney(current)}{' '}
                  <span className="text-base font-normal text-fg-muted">{portfolio.base_currency}</span>
                </>
              ) : (
                <span className="text-lg font-normal text-fg-subtle">Not configured</span>
              )}
            </div>
          </div>

          {editing && (
            <div className="flex items-center gap-2">
              <div className="relative">
                <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-fg-subtle">
                  {portfolio.base_currency}
                </span>
                <input
                  autoFocus
                  type="number"
                  inputMode="decimal"
                  min="0"
                  step="1000"
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') submit()
                    if (e.key === 'Escape') setEditing(false)
                  }}
                  placeholder="100000"
                  aria-label="Capital amount"
                  className="h-9 w-40 rounded-lg border border-border bg-surface pl-12 pr-3 font-mono text-sm text-fg tabular-nums focus:border-accent focus:outline-none"
                />
              </div>
              <Button size="sm" variant="primary" onClick={submit} disabled={mutation.isPending}>
                {mutation.isPending ? 'Saving…' : 'Save'}
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setEditing(false)} disabled={mutation.isPending}>
                Cancel
              </Button>
            </div>
          )}
        </div>

        {mutation.isError && (
          <p className="mt-3 text-sm text-risk">Could not save capital. Please try again.</p>
        )}

        {current && <Utilization configuredCapital={current} openMarketValue={openMarketValue} />}

        {/* Honest capital-config disclosure — always visible, never buried */}
        <div className="mt-4 flex items-start gap-2 rounded-lg border border-warning/25 bg-warning-soft/40 px-3 py-2.5">
          <Info size={15} className="mt-0.5 shrink-0 text-warning" />
          <p className="text-xs leading-relaxed text-fg-muted">
            <Badge variant="warning" className="mr-1.5 align-middle">Config only</Badge>
            This is a configuration value only. It has <strong className="font-semibold text-fg">no backing NAV/cash ledger</strong> and does
            not feed leverage or any risk-limit calculation — those still take equity as an explicit input. A real capital ledger remains deferred.
          </p>
        </div>
      </Panel>
    </Section>
  )
}
