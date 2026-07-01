// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0)
// Routing: public pages isolated from application modules — Doc 08 §Routing
// Application Structure: Authentication layer — Doc 08 §Application Structure
// Per Doc 00 §14.11
export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50">
      {children}
    </main>
  )
}
