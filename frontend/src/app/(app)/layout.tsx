// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0)
// Application Structure: Dashboard Shell — Doc 08 §Application Structure
// Routing: authenticated routes protected — Doc 08 §Routing
// Architecture: stateless shell layout; feature modules render in {children} — Doc 08 §Architecture
// Per Doc 00 §14.11
import { SidebarNav } from '@/components/ui/SidebarNav'

export default function AppLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex min-h-screen">
      {/* Doc 08 §Application Structure: Dashboard Shell → Feature Modules */}
      <SidebarNav />
      <main className="flex-1 overflow-auto p-6">{children}</main>
    </div>
  )
}
