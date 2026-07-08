// Doc 08 §Architecture: feature-specific component inside feature directory
// Doc 06 §Interaction Standards: intentional "planned" state. Research
// (Phase 3B — ML/Research Engineering, Docs 12–13) is deferred indefinitely
// per S-7: no ML model, researcher, or multi-strategy feature-sharing need
// exists to justify the Feature Store / experiment tracking machinery yet.
'use client'

import { FlaskConical } from 'lucide-react'
import { ComingSoon } from '@/components/ui'

export function ResearchShell() {
  return (
    <ComingSoon
      icon={<FlaskConical size={30} strokeWidth={1.75} />}
      title="Research"
      description="Feature engineering, experiment tracking, and model registry (Phase 3B) will appear here when a real ML/research workflow exists to populate them."
      note="Deferred indefinitely per S-7 · resumes on a real ML/feature-sharing trigger"
      planned={['Feature store & lineage', 'Experiment tracking', 'Model registry & promotion']}
    />
  )
}
