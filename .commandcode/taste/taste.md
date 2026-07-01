# Taste (Continuously Learned by [CommandCode][cmd])

[cmd]: https://commandcode.ai/

# language
- All handbook content, markdown, comments, status updates, completion summaries, and responses shall be written exclusively in professional English. No Chinese or any other language. Confidence: 0.85

# workflow
- Before writing any handbook document content, design and freeze a complete implementation-grade outline. Wait for explicit approval after producing the outline. Confidence: 0.65
- When freezing any document or outline, update HANDBOOK_INDEX.md, FROZEN_DECISIONS.md, and SESSION_MEMORY.md to reflect the new frozen status. Confidence: 0.65
- After writing handbook document sections, review for architectural consistency, duplicate concepts, terminology drift, overlap with frozen documents, missing enterprise-grade concepts, weak engineering reasoning, and incomplete cross-references before continuing to the next sections. Confidence: 0.70
- For handbook audits: Phase 2 is strictly terminology-only (names, spelling, abbreviations, vocabulary, SHALL-language). Architectural changes to ownership, lifecycle definitions, governance rules, responsibilities, interfaces, or canonical behavior are deferred to Phase 3 — Cross-Document Architecture Audit. Phase 4 — Enterprise Engineering Quality Audit covers operational readiness, scalability, performance, resiliency, security, observability, disaster recovery, compliance, testing requirements, deployment readiness, cloud readiness, maintainability, operational procedures, monitoring, alerting, capacity planning, failure handling, and long-term extensibility. Confidence: 0.70

