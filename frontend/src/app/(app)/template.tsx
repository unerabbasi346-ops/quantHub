// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Interaction Standards: motion on navigation. A Next App Router `template`
//   re-mounts on every route change (unlike `layout`), so it is the natural
//   home for the page-level enter animation — and it re-plays the whole
//   materialization sequence on each navigation.
//
// UNIVERSAL MATERIALIZATION LAYER: this root wraps 100% of every page's content
//   in a single blur→sharp + opacity wash. It is what guarantees the
//   "everything emerges from haze" language reaches even raw markup that isn't a
//   design-system component (loose text, a bespoke widget). Design-system
//   components (Card, Section, Stat, charts…) then layer their own positional
//   cascade + glow ON TOP of this wash — no per-page animation code required.
//   prefers-reduced-motion collapses it to the finished state instantly.
// Per Doc 00 §14.11
'use client'

import { motion } from 'framer-motion'
import { useReveal } from '@/lib/motion'

export default function AppTemplate({ children }: { children: React.ReactNode }) {
  const reveal = useReveal('page')
  return <motion.div {...reveal}>{children}</motion.div>
}
