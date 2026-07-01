// Doc 08 §Architecture: feature-specific component inside feature directory
// Doc 08 §Component Standards: stateless shell — no real widgets in Step 0.5
export function DashboardShell() {
  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>
      <p className="mt-1 text-sm text-gray-500">
        Overview widgets — implemented in Doc 06 phase.
      </p>
    </div>
  )
}
