// Governing specification: Doc 06 §Interaction Standards. The framer-motion
//   variant that every self-revealing component shares. It is DYNAMIC: the
//   concrete recipe (translate distance, blur radius, glow, duration, delay)
//   arrives per-instance through framer's `custom` prop, resolved by useReveal.
//   One variant object, reused everywhere → one coherent motion language.
// Per Doc 00 §14.11
import type { Variants } from 'framer-motion'
import { EASE_OUT, hiddenFilter, visibleFilter } from './config'

/** The per-instance recipe carried on framer's `custom` prop. */
export interface RevealCustom {
  y: number
  blur: number
  duration: number
  delay: number
  useFilter: boolean
  useGlow: boolean
}

/**
 * hidden → the element as unformed haze (transparent, nudged down, blurred and
 * lit by the bloom). visible → the finished component (opaque, in place, sharp,
 * glow gone). Because `filter` is only present when `useFilter` is set, kinds
 * that opt out (table rows) animate a pure opacity+slide with no filter cost.
 */
export const revealVariants: Variants = {
  hidden: (c: RevealCustom) => ({
    opacity: 0,
    y: c.y,
    ...(c.useFilter ? { filter: hiddenFilter({ blur: c.blur, useGlow: c.useGlow }) } : {}),
  }),
  visible: (c: RevealCustom) => ({
    opacity: 1,
    y: 0,
    ...(c.useFilter ? { filter: visibleFilter({ useGlow: c.useGlow }) } : {}),
    transition: { duration: c.duration, ease: EASE_OUT, delay: c.delay },
  }),
}
