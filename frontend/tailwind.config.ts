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
      // Doc 07 §Typography Hierarchy — the platform-wide type scale. Extends
      // (does not replace) Tailwind's stock text-* sizes, each entry named
      // for its Doc 07 role rather than a raw pixel value so a page reads
      // `text-page-title` / `text-metric` and the scale stays centralized
      // here as the single source of truth. Weight and letter-spacing stay
      // separate utility classes (font-semibold, tracking-tight, ...) at
      // each call site — same convention already used throughout the
      // codebase — rather than baked into the tuple, so this doesn't depend
      // on every consumer picking up a font-weight-in-fontSize feature.
      fontSize: {
        display: ['44px', { lineHeight: '1.1' }], // Doc 07 Display Title 40-48px
        'page-title': ['32px', { lineHeight: '1.2' }], // Doc 07 Page Title 28-36px
        'section-title': ['24px', { lineHeight: '1.2' }], // Doc 07 Section Title 22-26px
        'card-title': ['19px', { lineHeight: '1.2' }], // Doc 07 Card Title 18-20px
        metric: ['36px', { lineHeight: '1.1' }], // Doc 07 Primary Metric 32-40px
        'metric-sm': ['22px', { lineHeight: '1.2' }], // Doc 07 Secondary Metric 20-24px
        body: ['15px', { lineHeight: '1.5' }], // Doc 07 Body Text 14-16px
        caption: ['12.5px', { lineHeight: '1.4' }], // Doc 07 Caption 12-13px
        table: ['13.5px', { lineHeight: '1.4' }], // Doc 07 Table Text 13-14px
        btn: ['14.5px', { lineHeight: '1.2' }], // Doc 07 Button Text 14-15px
        nav: ['14px', { lineHeight: '1.2' }], // Doc 07 Navigation 14px
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
