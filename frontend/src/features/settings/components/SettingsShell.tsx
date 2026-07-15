// Doc 08 §Architecture: feature-specific component inside feature directory
// Doc 06 §Interaction Standards: intentional "planned" state (not a bare
// sentence in a void). Settings is deferred per S-6 (single-user local
// platform — no real auth/user prefs to configure yet, G-AUTH-1).
'use client'

import { Settings } from 'lucide-react'
import { ComingSoon } from '@/components/ui'

export function SettingsShell() {
  return (
    <ComingSoon
      icon={<Settings size={30} strokeWidth={1.75} />}
      title="Settings"
      description="Workspace and account preferences will live here once the platform grows beyond a single local operator."
      note="Arrives once the platform grows beyond a single local operator"
      planned={['Theme & display density', 'Default portfolio & base currency', 'API keys & data sources']}
    />
  )
}
