// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Interaction Standards: motion is a first-class part of the system, not a
//   per-page afterthought. This file is the single source of truth for the
//   "digital materialization" language — every timing, easing, blur radius and
//   translate distance lives here so the whole app moves as one instrument.
// Per Doc 00 §14.11
//
// THE LANGUAGE (owner brief): nothing pops. Every element travels
//   invisible → soft glowing haze → semi-recognisable shape → sharp component
// inside a fraction of a second. The perceived motion comes almost entirely
// from BLUR reduction + opacity + a transient glow that dissipates as the
// element "stabilises"; physical translation is deliberately tiny (≤12px) so
// the interface feels like an OS resolving itself into focus, not sliding in.
//
// GPU-only: everything here animates `opacity`, `transform` (y) and `filter`
// (blur + drop-shadow) — all compositor-friendly. No width/height/top/left.

/**
 * Ease-out with an exponential tail (no overshoot / bounce). Fast start that
 * decelerates into a soft settle — the "coming into focus" feel. Used for
 * every materialization; SVG path draws share it so lines and shells agree.
 */
export const EASE_OUT: [number, number, number, number] = [0.16, 1, 0.3, 1]

/** Durations (seconds). Kept sub-second so a full page resolves in ~1s. */
export const DURATION = {
  page: 0.45,
  container: 0.5,
  card: 0.5,
  item: 0.42,
  text: 0.4,
  number: 0.55, // count-up after the digits have sharpened
  chart: 0.95, // progressive line draw — the hero of the chart sequence
  spark: 0.7,
} as const

/**
 * Position-based cascade. Each self-revealing component measures its own
 * vertical position on mount and converts it to a start delay, so the page
 * resolves top-to-bottom automatically — no global counter, no per-page code,
 * robust to render order. Capped so the bottom of a long page never lags too
 * far behind the top.
 */
export const CASCADE = {
  pxToS: 0.00035, // seconds of delay per px of viewport offset
  max: 0.42, // hard ceiling on the positional part of the delay
} as const

/**
 * Per-kind materialization recipe. `base` is an additive delay that encodes the
 * motion HIERARCHY (page → container → card shell → header → title → content →
 * item → number): larger structures start first, their contents lag a beat, so
 * a card shell always forms before the numbers inside it. `useGlow` is reserved
 * for small text-like elements where a drop-shadow bloom is cheap and reads as
 * "illuminated smoke"; large surfaces use blur only (a full-viewport drop-shadow
 * would be far too expensive per frame).
 */
export interface RevealKindConfig {
  y: number
  blur: number
  duration: number
  base: number
  useFilter: boolean
  useGlow: boolean
}

export type RevealKind =
  | 'page'
  | 'container'
  | 'card'
  | 'cardHeader'
  | 'cardContent'
  | 'title'
  | 'header'
  | 'section'
  | 'item'
  | 'text'
  | 'number'
  | 'row'

// ANTI-STACKING RULE: `filter: blur()` is expensive and, when nested, blurs the
// same pixel multiple times (page → section → card → content → number) into
// mud. So blur lives at exactly TWO tiers: the PAGE wash (one shared ancestor
// blur over everything) and LEAF text/number/chip elements (title, text,
// number, item) which contain nothing else that blurs. Structural containers
// (container, card, header, section, content, row) materialize with a crisp
// opacity + slide only — their haze is supplied by the page wash above them.
// Net result: any pixel is blurred by at most 2 layers. `base` still encodes
// the full hierarchy so shells lead their contents.
export const KIND: Record<RevealKind, RevealKindConfig> = {
  //           y   blur  dur   base   filter  glow
  page: /*  */ { y: 8, blur: 4, duration: DURATION.page, base: 0, useFilter: true, useGlow: false },
  container: /**/ { y: 12, blur: 0, duration: DURATION.container, base: 0.04, useFilter: false, useGlow: false },
  card: /*  */ { y: 10, blur: 0, duration: DURATION.card, base: 0.03, useFilter: false, useGlow: false },
  // Card sub-parts fade only (no translate of their own) so they don't compound
  // with the shell's slide that's still settling above them — the shell moves,
  // the contents simply resolve into it a beat later.
  cardHeader: /**/ { y: 0, blur: 0, duration: DURATION.item, base: 0.14, useFilter: false, useGlow: false },
  cardContent: /**/ { y: 0, blur: 0, duration: DURATION.item, base: 0.2, useFilter: false, useGlow: false },
  title: /* */ { y: 6, blur: 8, duration: DURATION.text, base: 0.12, useFilter: true, useGlow: true },
  header: /**/ { y: 8, blur: 0, duration: DURATION.text, base: 0.02, useFilter: false, useGlow: false },
  section: /**/ { y: 10, blur: 0, duration: DURATION.container, base: 0.04, useFilter: false, useGlow: false },
  item: /*  */ { y: 8, blur: 6, duration: DURATION.item, base: 0.06, useFilter: true, useGlow: true },
  text: /*  */ { y: 6, blur: 8, duration: DURATION.text, base: 0.06, useFilter: true, useGlow: true },
  number: /**/ { y: 6, blur: 7, duration: DURATION.text, base: 0.08, useFilter: true, useGlow: true },
  // Rows also skip `filter`: it can detach a <tr> from the table box model. The
  // page wash covers their haze; here we stagger a crisp opacity + slide so rows
  // "populate one after another".
  row: /*   */ { y: 6, blur: 0, duration: 0.34, base: 0.02, useFilter: false, useGlow: false },
}

/**
 * The transient violet bloom (brand accent, not a semantic hue) an element is
 * lit by while it forms, and the fully-dissipated end state. Both keyframes
 * carry the same `drop-shadow(...)` function so framer can interpolate the
 * radius and alpha to zero — the "energy stabilising" fade.
 */
export const GLOW_FROM = 'drop-shadow(0 0 10px rgba(179, 158, 255, 0.45))'
export const GLOW_TO = 'drop-shadow(0 0 0px rgba(179, 158, 255, 0))'

/** Compose the `filter` keyframes for a given kind config. */
export function hiddenFilter(cfg: Pick<RevealKindConfig, 'blur' | 'useGlow'>): string {
  return cfg.useGlow ? `blur(${cfg.blur}px) ${GLOW_FROM}` : `blur(${cfg.blur}px)`
}
export function visibleFilter(cfg: Pick<RevealKindConfig, 'useGlow'>): string {
  return cfg.useGlow ? `blur(0px) ${GLOW_TO}` : 'blur(0px)'
}
