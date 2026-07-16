// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0)
// Technology: Next.js App Router — Doc 08 §Technology
// Performance: strict mode, bundle optimisation — Doc 08 §Performance
// Security: never expose secrets in client — Doc 08 §Security
// Per Doc 00 §14.11
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Strips console.* calls from production client bundles (kept in dev).
  // swcMinify is deliberately NOT set here — it was a real Next.js config
  // option through v12, but Next 13+ (this app runs 15) made SWC
  // minification the unconditional default and removed the flag from
  // NextConfig's type entirely; setting it would be dead config, not a fix.
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production',
  },
  // Doc 08 §Performance: optimise imports for large libraries — per-icon/
  // per-module imports instead of pulling each package's full barrel file
  // into every route that touches it. echarts-for-react dropped from the
  // requested list — not a dependency of this app (Chart.tsx wraps raw
  // `echarts` directly), so listing it here would be dead config.
  experimental: {
    optimizePackageImports: [
      'echarts',
      'framer-motion',
      'lucide-react',
      '@tanstack/react-table',
      '@tanstack/react-virtual',
    ],
  },
  // Only read when the dev server runs with `next dev --turbopack` — the
  // package.json `dev` script now does (below). NOT under `experimental`:
  // Next 15.5 promoted Turbopack config to a top-level key and logs a
  // deprecation warning for `experimental.turbo` (verified live). An empty
  // `rules` is a valid, harmless placeholder: no custom loader rules
  // needed today, but this is where a future one (e.g. an SVG loader)
  // would go without restructuring the config.
  turbopack: {
    rules: {},
  },
}

export default nextConfig
