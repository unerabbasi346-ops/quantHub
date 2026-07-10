// Governing specification: Doc 06 §Interaction Standards. Public surface of the
//   QuantHub motion system ("digital materialization"). Components import from
//   '@/lib/motion' — the internal file split (config / variants / reveal) stays
//   an implementation detail.
// Per Doc 00 §14.11
export { useReveal, type RevealResult } from './reveal'
export { revealVariants, type RevealCustom } from './variants'
export { Materialize } from './Materialize'
export { AnimatedNumber } from './AnimatedNumber'
export {
  EASE_OUT,
  DURATION,
  CASCADE,
  KIND,
  GLOW_FROM,
  GLOW_TO,
  hiddenFilter,
  visibleFilter,
  type RevealKind,
  type RevealKindConfig,
} from './config'
