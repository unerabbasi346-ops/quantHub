# Writing Standard

## Tone

Professional, precise, engineering-focused. Present tense. Active voice. Avoid marketing language, hyperbole, or emotional appeals. Write for an audience of senior engineers and architects.

## Voice

Third person for architecture descriptions: "The platform provides..." not "We provide..." or "You should..."

Second person "you" is prohibited in handbook architecture documents.

## Heading Hierarchy

`#` for document titles. `##` for sections (e.g., "## 7.1 Enterprise Data Lake Architecture"). `###` for subsections. `####` for sub-subsections. Every heading shall use title case.

## Lists

Bullet lists (`-`) for enumeration of items. Numbered lists (`1.`) only for sequential steps or ordered priorities. Tables for structured comparisons. Lists shall use parallel grammatical structure.

## Terminology Usage

Use only canonical terms as defined in `handbook/TERMINOLOGY.md`. Same term for same concept everywhere — no aliases, no synonyms, no competing names.

First use of any abbreviation in each document shall include its expansion in parentheses: "profit and loss (P&L)". Subsequent uses may use the abbreviation alone.

Cross-document references shall use the canonical document name: "Document 11 — Data Engineering & Data Pipeline Architecture" for first reference, "Document 11" for subsequent references in the same section.

Invariant identifiers shall use the canonical forms: P-1 through P-18, D-1 through D-10, M-1 through M-8, R-1 through R-7, T-1 through T-7, Port-1 through Port-6.

No document shall introduce new terminology without an entry in TERMINOLOGY.md.

## Requirement Statements

The following modal verbs define normative requirements in handbook architecture documents:

- **shall** — Mandatory requirement. Non-compliance is a violation of the specification.
- **should** — Recommendation. Departure requires documented justification.
- **may** — Optional permission. Implementation choice. No compliance implication.

All modal verbs shall be lowercase (house style). The term "must" is prohibited in handbook architecture documents — use "shall" instead.

Every requirement shall use exactly one modal verb. Requirements shall not use "will" or present-tense declaratives as substitutes for "shall".

## Engineering Language

Architecture descriptions use present tense declarative: "The Lakehouse provides ACID-compliant transaction semantics." Future tense "will" shall be used only for planned capabilities not yet specified.

Quantitative requirements shall use precise values, not vague comparatives: "99.95% availability" not "high availability."

## Formatting Rules

Markdown format throughout. Code blocks (triple backticks) for schemas, configurations, and interface definitions. Tables for comparisons, matrices, and structured reference data. **Bold** for emphasis of key terms on first definition. Inline `code` for identifiers, paths, and technical terms used as identifiers.

## Section Structure

Every architecture section shall follow this structure:
1. Purpose statement
2. Architectural requirements (using "shall")
3. Cross-references to upstream/downstream documents
4. End of Section marker: `# End of Section N.M — Section Name`

## Cross References

Document references: `Document N — Canonical Name`  
Section references: `Document N Section X.Y` or `Section X.Y` (within same document)  
Invariant references: `P-1`, `D-3`, `M-5`, `R-2`, `T-4`, `Port-2`  
Decision references: `F-1`, `D-7.9.1 Quality by Design`

The verbal form "per" is standard for inline references: "per P-13", "per D-7.9.5".

No document shall reference a downstream document as "(future)". Completed documents shall be referenced by canonical name without qualifier.

## Consistency Rules

Same term for same concept in every document. No redefinition of frozen architectures. No introduction of synonyms or aliases.

Section numbers, invariant identifiers, decision identifiers, and document numbers shall be globally unique and consistently used.

All cross-references shall be resolvable to the referenced content. References to non-existent sections or documents are prohibited.

Corrections to frozen documents shall follow the amendment process: new version with explicit change record, not silent modification.
