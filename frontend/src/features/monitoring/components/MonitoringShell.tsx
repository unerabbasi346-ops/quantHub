// Doc 08 §Architecture: feature-specific component inside feature directory
// Doc 06 §Interaction Standards: intentional "planned" state. Monitoring is
// deferred per S-6 — no backend audit/notification/metrics pipeline exists
// yet to feed a real monitoring surface.
'use client'

import { Activity } from 'lucide-react'
import { ComingSoon } from '@/components/ui'

export function MonitoringShell() {
  return (
    <ComingSoon
      icon={<Activity size={30} strokeWidth={1.75} />}
      title="Monitoring"
      description="System health, latency, and audit-event streams will surface here once an observability pipeline is wired to the backend."
      note="Deferred per S-6 · no audit/metrics pipeline yet"
      planned={['Service health & uptime', 'Order/latency telemetry', 'Audit & risk-event feed']}
    />
  )
}
