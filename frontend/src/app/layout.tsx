// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0)
// Application Structure: Root Layout — Doc 08 §Application Structure
// State management providers wired here — Doc 08 §State Management
// Per Doc 00 §14.11
import type { Metadata } from 'next'
import './globals.css'
import { Providers } from '@/lib/query/client'

export const metadata: Metadata = {
  title: 'Quant Hub',
  description: 'Institutional-grade trading and research platform — Doc 08',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        {/* Doc 08 §State Management: TanStack Query + Zustand providers */}
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
