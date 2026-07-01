// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0)
// Technology: Next.js App Router — Doc 08 §Technology
// Performance: strict mode, bundle optimisation — Doc 08 §Performance
// Security: never expose secrets in client — Doc 08 §Security
// Per Doc 00 §14.11
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Doc 08 §Performance: optimise imports for large libraries where applicable
  experimental: {},
}

export default nextConfig
