// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0)
// Technology: Tailwind CSS — Doc 08 §Technology
// Content paths cover App Router, feature modules, and shared components — Doc 08 §Architecture
// Per Doc 00 §14.11
import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/app/**/*.{ts,tsx}',
    './src/components/**/*.{ts,tsx}',
    './src/features/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}

export default config
