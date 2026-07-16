// Doc 08 §Application Structure: Feature Module — Monitoring
// Perf pass: dynamically imported — see risk/page.tsx for the rationale.
import dynamic from 'next/dynamic'
import { PageSkeleton } from '@/components/ui/PageSkeleton'

const MonitoringShell = dynamic(
  () => import('@/features/monitoring/components/MonitoringShell').then((m) => m.MonitoringShell),
  { loading: () => <PageSkeleton /> },
)

export default function MonitoringPage() { return <MonitoringShell /> }
