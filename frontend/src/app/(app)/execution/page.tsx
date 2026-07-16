// Doc 08 §Application Structure: Feature Module — Execution
// Perf pass: dynamically imported — see risk/page.tsx for the rationale.
import dynamic from 'next/dynamic'
import { PageSkeleton } from '@/components/ui/PageSkeleton'

const ExecutionShell = dynamic(
  () => import('@/features/execution/components/ExecutionShell').then((m) => m.ExecutionShell),
  { loading: () => <PageSkeleton /> },
)

export default function ExecutionPage() { return <ExecutionShell /> }
