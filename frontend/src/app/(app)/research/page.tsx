// Doc 08 §Application Structure: Feature Module — Research
// Perf pass: dynamically imported — see risk/page.tsx for the rationale.
import dynamic from 'next/dynamic'
import { PageSkeleton } from '@/components/ui/PageSkeleton'

const ResearchShell = dynamic(
  () => import('@/features/research/components/ResearchShell').then((m) => m.ResearchShell),
  { loading: () => <PageSkeleton /> },
)

export default function ResearchPage() { return <ResearchShell /> }
