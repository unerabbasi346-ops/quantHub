# Quant Hub Engineering Handbook — Known Limitations

**Version 1.0 — Certified**  
**Date:** 2026-06-30  
**Status:** All limitations documented as intentional design decisions. None block certification.

---

## Phase 3 — Intentional Architectural Variations (Accepted)

| ID | Variation | Justification |
|----|-----------|---------------|
| V-1 | Metadata lifecycle (6 states) vs Data lifecycle D-6 (8 states) | Distinct entities — metadata governance vs data lifecycle. Accepted per separate architectural domain ownership. |
| V-2 | Document 05 (Engineering Standards) modal verb convention | Exists as .docx binary, not auditable markdown. Accepted pending potential future conversion. |
| V-3 | Pre-Part 7 vs Part 7 cross-reference conventions | Different architectural abstraction levels in Document 11. Internally consistent within their structural context. Accepted. |

---

## Phase 4 — Design Limitations (Accepted, No Fixes)

| ID | Limitation | Rationale |
|----|-----------|-----------|
| L-1 | Order gateway throughput not qualified per venue | Venue-specific limits are strategy configurations per P-1; platform specifies the capability floor |
| L-2 | Network zone model is logical, not physical | Physical topology varies by deployment per P-18 |
| L-3 | GPU scaling thresholds are platform defaults | Research GPU policies are Doc 13 scope; platform defaults apply to production ML workloads |
| L-4 | Solver timeout fallback specified as "previous weights" | Architecture guidance, not implementation mandate. Strategies may use more sophisticated fallback models |
| L-5 | Circuit breaker dollar amounts not specified | Dollar amounts are portfolio/strategy-specific per Port-2. Platform specifies percentage thresholds as safety bounds |
| L-6 | Knowledge graph absent | Not in current architecture scope. Current model (taxonomy + full-text search) is the specified architecture |
| L-7 | What-if simulation capability absent | Not in current scope. Pre-trade analysis handled through Portfolio Construction (Doc 15 §11.2) and Stress Testing (§11.5.6) |
| L-8 | Risk model hot-swap capability | Currently specified as versioned model comparison (registration + validation). Hot-swap deferred to implementation phase |
| L-9 | Formal threat model not referenced (STRIDE, MITRE) | Deferred to implementation phase. Security architecture specifies defense-in-depth/zero trust at architecture level |
| L-10 | No continuous production chaos engineering | Full production chaos engineering requires mature observability and automated rollback. Annual Production Game Day is the architecture-specified starting point |

---

## Phase 5 — Known Specification Gaps (Deferred to Implementation)

| ID | Gap | Impact | Resolution |
|----|-----|--------|------------|
| G-1 | Exact FIX message type mappings for canonical order model | Broker adapters | Resolved per broker during exchange certification. Canonical order model provides target; FIX mapping is broker-specific |
| G-2 | Complete event schemas for all 60+ event types | Event catalog | Implementation phase generates schemas using Event Contract Completeness Requirements and canonical type system |
| G-3 | Complete API schemas for all Document 10 endpoints | Cross-document | Implementation phase generates schemas using API Contract Completeness Requirements |
| G-4 | GPU type abstraction mapping (valid `gpu_type` values) | Training/Workspace | Defined per infrastructure deployment; platform validates against available pool |
| G-5 | IdP product-specific group claim format mapping | SSO | Configured per organization's IdP; Document 13 provides mapping configuration format |
| G-6 | Exchange-specific tick normalization rules per venue | Market data | Implemented per exchange adapter; Document 14 provides canonical target format |
| G-7 | Custom constraint plugin interface | Portfolio construction | Strategy-specific per P-1; platform provides Constraint type structure; custom logic is external |
| G-8 | "Decision attribution" methodology | Performance attribution | Methodology is portfolio-specific per P-1; platform provides Brinson and Factor attribution |
| G-9 | Factor return computation source | Attribution | External per P-1; platform consumes factor returns as input; computation is strategy/governance scope |
| G-10 | Strategy-specific parameters (signals, models, rules) | All domains | External configurations per P-1. Platform provides contract shapes; strategy logic is outside platform scope |

---

## Phase 6 — Accepted Orphan Definitions

| ID | Term | Reason |
|----|------|--------|
| O-1 | Risk Engine | Anticipatory definition for when runtime component name needs separate identification from "Risk Management Architecture" (Doc 15 §11.5) |
| O-2 | Portfolio Engine | Anticipatory definition for when runtime component name needs separate identification from "Portfolio Management Platform Architecture" (Doc 15) |
| O-3 | IaC (Infrastructure as Code) | Defined for completeness; full phrase "Infrastructure as Code" used where needed |

---

## Implementation Decisions Deferred

| Decision Category | Guidance | Constraint |
|-------------------|----------|------------|
| Programming language | Not specified | Must support canonical type system mappings, mature data/ML ecosystem |
| Serialization format | Not specified | Must satisfy 6 governance criteria (schema evolution, code gen, binary efficiency, validation, ecosystem compatibility, governance) |
| Message broker | Not specified | Must support topics, partitions, consumer groups, ordering, exactly-once option |
| Storage backends | Not specified | Must support ACID/MVCC/time-travel for Lakehouse, sync replication for position state |
| Container orchestration | Not specified | Must support deployment topologies from Documents 12, 14, 15 |
| Identity provider | Not specified | Must support OIDC 1.0, SAML 2.0, JWKS, SCIM 2.0 |
| Observability stack | Not specified | Must support Prometheus-compatible metrics, structured logging, OpenTelemetry tracing |
| CI/CD platform | Not specified | Must support 9-stage pipeline architecture |
| FIX engine/protocol | Not specified | Must support target exchange protocols; broker adapter abstracts specific versions |
| GPU vendor/infrastructure | Not specified | Must support vendor lock-in prevention requirements per Document 12 |

---

## Handbook Scope Boundaries (Not Covered)

| Domain | Reason |
|--------|--------|
| Documents 00-10 (Project Constitution through API Specification) | Exist as .docx binary files; not auditable in this process |
| Frontend UI/UX | Owned by Documents 06, 08 |
| Database implementation details | Owned by Document 09 |
| Embedding of 3rd party software versions | Prohibited per P-3 Technology Independence |
| Specific cloud provider configurations | Prohibited per P-18 Cloud-Neutral Architecture |
| Strategy-specific logic, signals, models, parameters | Prohibited per P-1 Strategy Independence |

---

## Amendment Process

Amendments to Version 1.0 SHALL follow the governance process defined in FROZEN_DECISIONS.md. All amendments SHALL:
1. Be proposed with documented rationale and impact analysis
2. Reference specific invariant(s), frozen decision(s), or section(s) being amended
3. Receive governance council approval
4. Be recorded in a new document version with complete change log
5. Preserve all existing invariants — amendments SHALL NOT weaken or contradict frozen architectural principles
