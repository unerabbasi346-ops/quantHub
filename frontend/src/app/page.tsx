// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0)
// Routing: public root redirects into the authenticated app shell — Doc 08 §Routing
// Per Doc 00 §14.11
import { redirect } from 'next/navigation'

export default function RootPage() {
  redirect('/dashboard')
}
