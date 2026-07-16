// Doc 08 §Application Structure: Feature Module — Risk
// Perf pass: dynamically imported (not eagerly bundled with the shell) —
// only Dashboard/Markets/Strategies load eagerly; Risk/Execution/Research/
// Monitoring are secondary workflows, not the landing path.
import dynamic from 'next/dynamic'
import { PageSkeleton } from '@/components/ui/PageSkeleton'

const RiskShell = dynamic(
  () => import('@/features/risk/components/RiskShell').then((m) => m.RiskShell),
  { loading: () => <PageSkeleton /> },
)

export default function RiskPage() { return <RiskShell /> }
