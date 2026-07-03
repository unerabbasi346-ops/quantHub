// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0) §Component Standards
// Per Doc 00 §14.11
//
// Minimal className combiner — no new dependency (clsx/tailwind-merge) added
// for this alone; Doc 08 doesn't call for one, and the design-system
// components below fully control their own class lists, so conflict
// resolution (tailwind-merge's job) is not yet needed. Revisit if a
// consumer needs to override a component's Tailwind classes directly.
export type ClassValue = string | false | null | undefined

export function cn(...values: ClassValue[]): string {
  return values.filter(Boolean).join(' ')
}
