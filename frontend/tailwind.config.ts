// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0) §Visual Language
//                          Doc 08 — Frontend Architecture (QH-008 v1.0)
// Technology: Tailwind CSS — Doc 08 §Technology
// Content paths cover App Router, feature modules, and shared components — Doc 08 §Architecture
// Per Doc 00 §14.11
import type { Config } from 'tailwindcss'

// Doc 06 §Visual Language semantic tokens, backed by the CSS custom
// properties defined in app/globals.css (dark-first default, light-mode
// override via [data-theme='light']). `<alpha-value>` lets Tailwind's
// opacity utilities (bg-surface/60, text-risk/80, ...) work on these.
function themeColor(varName: string): string {
  return `hsl(var(${varName}) / <alpha-value>)`
}

const config: Config = {
  content: [
    './src/app/**/*.{ts,tsx}',
    './src/components/**/*.{ts,tsx}',
    './src/features/**/*.{ts,tsx}',
  ],
  darkMode: ['selector', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        bg: themeColor('--color-bg'),
        surface: themeColor('--color-surface'),
        'surface-hover': themeColor('--color-surface-hover'),
        border: themeColor('--color-border'),
        fg: themeColor('--color-fg'),
        'fg-muted': themeColor('--color-fg-muted'),
        // Doc 06 §Visual Language: "green=profit, red=risk, blue=information,
        // amber=warning" — the platform's four semantic hues. `risk` also
        // covers P&L loss (see globals.css judgment-call comment) rather
        // than a separate, undefined "loss" hue.
        profit: {
          DEFAULT: themeColor('--color-profit'),
          soft: themeColor('--color-profit-soft'),
        },
        risk: {
          DEFAULT: themeColor('--color-risk'),
          soft: themeColor('--color-risk-soft'),
        },
        info: {
          DEFAULT: themeColor('--color-info'),
          soft: themeColor('--color-info-soft'),
        },
        warning: {
          DEFAULT: themeColor('--color-warning'),
          soft: themeColor('--color-warning-soft'),
        },
      },
      borderColor: {
        DEFAULT: themeColor('--color-border'),
      },
    },
  },
  plugins: [],
}

export default config
