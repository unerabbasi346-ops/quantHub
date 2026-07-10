// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0) §Visual Language
//                          Doc 08 — Frontend Architecture (QH-008 v1.0)
// Application Structure: Root Layout — Doc 08 §Application Structure
// State management providers wired here — Doc 08 §State Management
// Per Doc 00 §14.11
import type { Metadata } from 'next'
import './globals.css'
import { Providers } from '@/lib/query/client'

export const metadata: Metadata = {
  title: 'Quant Hub',
  description: 'Institutional-grade trading and research platform',
}

// Doc 06 §Visual Language "dark-first theme, optional light mode": this
// runs before hydration/paint to set the real `data-theme` attribute from
// the persisted choice (falling back to dark), so there is no
// flash-of-wrong-theme on reload. useUIStore's `theme: 'dark'` initial
// value (lib/store/ui.ts) is only for SSR/hydration consistency — this
// script is what actually determines the first paint.
const THEME_INIT_SCRIPT = `
(function () {
  try {
    var stored = window.localStorage.getItem('quant-hub-theme');
    var theme = stored === 'light' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', theme);
  } catch (e) {
    document.documentElement.setAttribute('data-theme', 'dark');
  }
})();
`

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" data-theme="dark" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body>
        {/* Doc 08 §State Management: TanStack Query + Zustand providers */}
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
