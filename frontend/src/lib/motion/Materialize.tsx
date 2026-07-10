// Governing specification: Doc 06 §Interaction Standards. A drop-in wrapper for
//   any bespoke markup a future page introduces that ISN'T already a
//   design-system component — wrap it and it materializes like everything else.
//   Most pages never need this (they compose Card/Section/Stat/… which already
//   self-reveal); it exists so the escape hatch is still zero-config.
// Per Doc 00 §14.11
'use client'

import { motion, type HTMLMotionProps } from 'framer-motion'
import { useReveal } from './reveal'
import type { RevealKind } from './config'

interface MaterializeProps extends HTMLMotionProps<'div'> {
  /** Which recipe in the hierarchy this block should use. Default: 'item'. */
  kind?: RevealKind
}

export function Materialize({ kind = 'item', ...props }: MaterializeProps) {
  const reveal = useReveal(kind)
  return <motion.div {...reveal} {...props} />
}
