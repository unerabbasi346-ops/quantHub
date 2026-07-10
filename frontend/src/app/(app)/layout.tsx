// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout: "Persistent sidebar, top command bar, central workspace,
//   optional contextual panel, responsive grid, modular widgets."
// Doc 08 — Frontend Architecture (QH-008 v1.0)
// Application Structure: Dashboard Shell — Doc 08 §Application Structure
// Routing: authenticated routes protected — Doc 08 §Routing
//   NOTE (S-6): real authentication is deferred (single-user local
//   platform, G-AUTH-1) — this route group is not actually gated yet;
//   it is the shell real auth would attach to when built.
// Architecture: stateless shell layout; feature modules render in {children} — Doc 08 §Architecture
// Per Doc 00 §14.11
import { TopBar } from '@/components/ui/TopBar'

export default function AppLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    // NAVIGATION RESTRUCTURE (owner request): the left vertical sidebar is
    // removed; navigation now lives in the horizontal TopBar. The shell is a
    // simple vertical stack — command bar on top, central workspace below
    // (Doc 06 §Layout "top command bar, central workspace").
    <div className="flex h-screen flex-col overflow-hidden bg-bg">
      <TopBar />
      {/* Central workspace — the optional contextual panel (ContextPanel) is
          composed by individual feature pages, not force-mounted here. */}
      <main className="flex-1 overflow-auto px-6 py-6 lg:px-8">
        <div className="mx-auto w-full max-w-[1600px]">{children}</div>
      </main>
    </div>
  )
}
