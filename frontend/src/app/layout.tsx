// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0) §Visual Language
//                          Doc 08 — Frontend Architecture (QH-008 v1.0)
// Application Structure: Root Layout — Doc 08 §Application Structure
// State management providers wired here — Doc 08 §State Management
// Per Doc 00 §14.11
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Providers } from '@/lib/query/client'

// handbook/ui/visual_engineering/07_TYPOGRAPHY_SYSTEM §Font Family: "Primary
// — Inter ... The entire platform must use one primary font family."
// next/font self-hosts the font file at build time (downloaded once during
// `next build`, served from this app's own origin thereafter) — Inter by
// name, with no runtime request to Google's CDN, so it satisfies both the
// spec's font choice and globals.css's pre-existing "no network font fetch"
// constraint. The resulting CSS variable feeds --font-sans below instead of
// replacing it outright, so `var(--font-sans)` stays the one place every
// component already reads from.
const inter = Inter({ subsets: ['latin'], variable: '--font-inter', display: 'swap' })

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
    <html lang="en" data-theme="dark" suppressHydrationWarning className={inter.variable}>
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
