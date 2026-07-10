// Doc 08 §Application Structure: Feature Module — Strategy detail (dynamic route).
// Owner request (point 6/7): a dedicated per-strategy page at /strategies/[id],
// distinct from the flat /strategies list. Next 15 passes `params` as a Promise.
import { StrategyDetailShell } from '@/features/strategies/components/StrategyDetailShell'

export default async function StrategyDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return <StrategyDetailShell id={id} />
}
