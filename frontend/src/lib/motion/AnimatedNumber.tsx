// Governing specification: Doc 06 §Data Visualization. Numbers don't just fade
//   in — per the owner brief they materialize from the violet bloom, SHARPEN
//   first, and THEN count up to their final value. This primitive owns both
//   halves: it is a `number`-leaf that self-reveals (blur→sharp via useReveal)
//   AND, once sharpened, animates 0 → value. It parses a pre-formatted figure
//   (e.g. "$1,234.56", "+2.3%", "1,024 USDT"), holds the final value for SSR /
//   reduced-motion, and preserves the exact prefix, sign, decimal places,
//   grouping and suffix of the original string while counting.
// Per Doc 00 §14.11
'use client'

import { useEffect, useLayoutEffect, useState } from 'react'
import { animate, motion, useReducedMotion } from 'framer-motion'
import { CASCADE, DURATION, EASE_OUT } from './config'
import { useReveal } from './reveal'

// useLayoutEffect warns on the server; fall back to useEffect there.
const useIsoLayoutEffect = typeof window !== 'undefined' ? useLayoutEffect : useEffect

// prefix (non-digits) · optional sign · digits (with grouping/decimals) · suffix
const NUMERIC_RE = /^(\D*?)([+-]?)([\d,]*\.?\d+)(.*)$/

interface Parsed {
  prefix: string
  sign: '+' | '-' | ''
  target: number
  decimals: number
  grouped: boolean
  suffix: string
}

function parse(value: string): Parsed | null {
  const m = value.match(NUMERIC_RE)
  if (!m) return null
  const [, prefix, sign, digits, suffix] = m
  const target = parseFloat(digits.replace(/,/g, ''))
  if (!Number.isFinite(target)) return null
  const dot = digits.indexOf('.')
  const decimals = dot === -1 ? 0 : digits.length - dot - 1
  return {
    prefix,
    sign: sign === '+' ? '+' : sign === '-' ? '-' : '',
    target,
    decimals,
    grouped: digits.includes(','),
    suffix,
  }
}

interface AnimatedNumberProps {
  /** The already-formatted final figure, exactly as it should read when done. */
  value: string
  className?: string
}

export function AnimatedNumber({ value, className }: AnimatedNumberProps) {
  const reduce = useReducedMotion()
  const parsed = parse(value)
  // The `number` leaf reveal (blur→sharp + glow). Its ref also serves the
  // count's positional timing, so we measure the element exactly once.
  const reveal = useReveal('number')
  const ref = reveal.ref
  // Initialise to the FINAL text so SSR, no-JS and reduced-motion all render the
  // real value — never a blank or a frozen zero.
  const [display, setDisplay] = useState<string>(value)

  const format = parsed
    ? (n: number) => {
        const body = Math.abs(n).toLocaleString('en-US', {
          minimumFractionDigits: parsed.decimals,
          maximumFractionDigits: parsed.decimals,
          useGrouping: parsed.grouped,
        })
        const sign = parsed.sign || (n < 0 ? '-' : '')
        return `${parsed.prefix}${sign}${body}${parsed.suffix}`
      }
    : null

  useIsoLayoutEffect(() => {
    if (reduce || !parsed || !format) return
    // Reset to zero before paint so the count is never seen jumping down.
    setDisplay(format(0))
  }, [reduce, value])

  useIsoLayoutEffect(() => {
    if (reduce || !parsed || !format) return
    // Start the count AFTER the digits have sharpened: position-cascade delay
    // (matching useReveal) + the text materialization duration.
    const top = ref.current ? ref.current.getBoundingClientRect().top : 0
    const startDelay =
      Math.min(CASCADE.max, Math.max(0, top) * CASCADE.pxToS) + DURATION.text
    const controls = animate(0, parsed.target, {
      duration: DURATION.number,
      delay: startDelay,
      ease: EASE_OUT,
      onUpdate: (v) => setDisplay(format(v)),
    })
    return () => controls.stop()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, reduce])

  return (
    <motion.span {...reveal} className={className}>
      {display}
    </motion.span>
  )
}
