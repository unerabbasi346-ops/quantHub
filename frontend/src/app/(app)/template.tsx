// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Interaction Standards: motion on navigation. A Next App Router
//   `template` re-mounts on every route change (unlike `layout`), so it is
//   the natural home for a per-page enter transition (owner request: page
//   transition on route change). framer-motion drives a subtle fade+rise,
//   ≤200ms, auto-disabled under prefers-reduced-motion.
// Per Doc 00 §14.11
'use client'

import { motion, useReducedMotion } from 'framer-motion'

export default function AppTemplate({ children }: { children: React.ReactNode }) {
  const reduce = useReducedMotion()
  return (
    <motion.div
      initial={reduce ? false : { opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduce ? 0 : 0.2, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  )
}
