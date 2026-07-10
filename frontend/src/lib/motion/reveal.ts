// Governing specification: Doc 06 §Interaction Standards. useReveal is the ONE
//   hook every design-system component calls to inherit the materialization
//   language. It self-triggers on mount, measures the element's vertical
//   position to derive a top-to-bottom cascade delay, and returns props to
//   spread straight onto a `motion.*` element. Because each component triggers
//   itself, nothing depends on render order or a parent orchestrator — a brand
//   new page inherits the whole sequence with zero animation code.
// Motion respects prefers-reduced-motion: reduced users get the finished state
//   instantly (initial=false), no blur, no translate, no delay.
// Per Doc 00 §14.11
'use client'

import { useLayoutEffect, useEffect, useRef, useState } from 'react'
import { useReducedMotion, type Variants } from 'framer-motion'
import { CASCADE, KIND, type RevealKind } from './config'
import { revealVariants, type RevealCustom } from './variants'

// useLayoutEffect on the server warns; fall back to useEffect there. These are
// client components but Next still renders them once on the server.
const useIsoLayoutEffect = typeof window !== 'undefined' ? useLayoutEffect : useEffect

export interface RevealResult {
  // `any` so the same hook result can be spread onto motion.div / .tr / .h3 /
  // .span / .svg without per-element ref-variance friction.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ref: React.MutableRefObject<any>
  initial: 'hidden' | false
  animate?: 'visible' | 'hidden'
  variants?: Variants
  custom?: RevealCustom
  onAnimationComplete?: () => void
}

function buildCustom(kind: RevealKind, delay: number): RevealCustom {
  const cfg = KIND[kind]
  return {
    y: cfg.y,
    blur: cfg.blur,
    duration: cfg.duration,
    delay,
    useFilter: cfg.useFilter,
    useGlow: cfg.useGlow,
  }
}

/**
 * Wire a `motion.*` element into the materialization system.
 *
 * @example
 *   const reveal = useReveal('card')
 *   return <motion.div {...reveal} className="rounded-xl …" />
 */
export function useReveal(kind: RevealKind = 'item'): RevealResult {
  const reduce = useReducedMotion()
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const ref = useRef<any>(null)
  const [animate, setAnimate] = useState<'hidden' | 'visible'>('hidden')
  const [custom, setCustom] = useState<RevealCustom>(() => buildCustom(kind, 0))

  useIsoLayoutEffect(() => {
    if (reduce) return
    const cfg = KIND[kind]
    const top = ref.current ? ref.current.getBoundingClientRect().top : 0
    const positional = Math.min(CASCADE.max, Math.max(0, top) * CASCADE.pxToS)
    // Compute the cascade delay before the browser paints, then release the
    // element to "visible" — so the first painted frame is already the intended
    // haze, never a flash of the finished component.
    setCustom(buildCustom(kind, cfg.base + positional))
    setAnimate('visible')
  }, [reduce, kind])

  if (reduce) {
    return { ref, initial: false }
  }

  const cfg = KIND[kind]
  return {
    ref,
    initial: 'hidden',
    animate,
    variants: revealVariants,
    custom,
    // Once formed, strip the inline `filter` entirely. A lingering `filter`
    // (even `blur(0px)`) keeps a stacking context / containing block alive that
    // can trap `position: fixed` descendants; clearing it restores normal flow.
    onAnimationComplete: cfg.useFilter
      ? () => {
          if (ref.current) ref.current.style.filter = ''
        }
      : undefined,
  }
}
