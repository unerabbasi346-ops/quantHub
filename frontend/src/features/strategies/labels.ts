// Governing specification: Doc 14 §10.2 Strategy Governance; P-1 (Strategy
//   Independence). Doc 00 §14.5/§14.7 — flagged judgment call, not silent.
// Per Doc 00 §14.11
//
// REFERENCE/TESTING LABELING (owner request, point 10): MovingAverageCrossover
// is kept for dev/testing/UI validation and must be clearly labelled as a
// reference/testing strategy — never presented as a real trading strategy.
//
// JUDGMENT CALL (flagged): membership is an EXPLICIT allow-list, not a name
// prefix. Both current strategies are named `reference-*` and both are, by
// their own docstrings, reference plugins that make no economic claim — but the
// owner's framing treats the funding-basis strategy as the load-bearing
// perpetual work and singled out ONLY the MA crossover as testing-only. So the
// set contains just `reference-ma-crossover`. If the funding strategy should
// also read as reference-only, add its name here (one line) — deliberately left
// out so the label reflects the owner's stated intent, not a guess.
const REFERENCE_STRATEGY_NAMES = new Set<string>(['reference-ma-crossover'])

export function isReferenceStrategy(name: string): boolean {
  return REFERENCE_STRATEGY_NAMES.has(name)
}

// Exact wording (owner asked for the proposed label to be surfaced, not chosen
// silently). Short badge + explicit tooltip; a card caption uses CAPTION.
export const REFERENCE_BADGE = 'Reference'
export const REFERENCE_CAPTION = 'Testing · reference plugin'
export const REFERENCE_TOOLTIP =
  'Reference / testing strategy — used to validate the platform, not a real trading strategy. Not for live capital.'
