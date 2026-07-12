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
      // Doc 02 §Responsive Breakpoints: Tablet 768-1023, Laptop 1024-1399,
      // Desktop 1400+. Named alongside (not replacing) Tailwind's stock
      // sm/md/lg/xl/2xl scale so existing classes keep working.
      screens: {
        tablet: '768px',
        laptop: '1024px',
        desktop: '1400px',
      },
      fontFamily: {
        sans: ['var(--font-sans)'],
        mono: ['var(--font-mono)'],
      },
      colors: {
        bg: themeColor('--color-bg'),
        surface: themeColor('--color-surface'),
        'surface-raised': themeColor('--color-surface-raised'),
        'surface-hover': themeColor('--color-surface-hover'),
        border: themeColor('--color-border'),
        'border-strong': themeColor('--color-border-strong'),
        fg: themeColor('--color-fg'),
        'fg-muted': themeColor('--color-fg-muted'),
        'fg-subtle': themeColor('--color-fg-subtle'),
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
        // Brand accent (violet/indigo) — deliberately NOT one of the four
        // semantic hues (see globals.css). Used only for brand chrome: logo,
        // active nav, primary CTA, focus ring. Never data-driven.
        accent: {
          DEFAULT: themeColor('--color-accent'),
          soft: themeColor('--color-accent-soft'),
          fg: themeColor('--color-accent-fg'),
        },
      },
      borderColor: {
        DEFAULT: themeColor('--color-border'),
      },
      boxShadow: {
        // Elevation ramp (globals.css --shadow-*) — the visual-hierarchy
        // system: raised/primary content casts a real shadow, secondary
        // content stays flat with a hairline border.
        sm: 'var(--shadow-sm)',
        md: 'var(--shadow-md)',
        lg: 'var(--shadow-lg)',
        // Violet brand halo for the glowing card treatment (owner visual
        // language) — a soft blurred accent glow, not a hard border. `-hover`
        // intensifies for interactive cards. See globals.css --shadow-glow*.
        glow: 'var(--shadow-glow)',
        'glow-hover': 'var(--shadow-glow-hover)',
      },
      keyframes: {
        'fade-in': { from: { opacity: '0' }, to: { opacity: '1' } },
        'fade-in-up': {
          from: { opacity: '0', transform: 'translateY(6px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        'fade-in': 'fade-in 180ms ease-out both',
        'fade-in-up': 'fade-in-up 220ms cubic-bezier(0.22,1,0.36,1) both',
      },
    },
  },
  plugins: [],
}

export default config
