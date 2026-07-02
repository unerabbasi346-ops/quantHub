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

## Phase 7 — Implementation-Phase Findings (Tracked, Blocking)

Findings surfaced during Phase 1 backend implementation (Doc 11 Market
Data Ingestion, Steps 1.2–1.4) that are tracked defects requiring
resolution before a specific future phase begins — unlike Phase 4/5
above, these are NOT accepted design decisions. Recorded here so each
finding surfaces again naturally (e.g. when a blocked repository is about
to be implemented) rather than depending on anyone's memory.

| ID | Field(s) | Table | Issue | Must resolve before | Resolution pattern | Reference |
|----|----------|-------|-------|----------------------|---------------------|-----------|
| F-1 | `bid_size`, `ask_size`, `last_size`, `volume` | `market_data.ticks` | `INTEGER`/`BIGINT` cannot represent fractional trade/order sizes (e.g. crypto sizes below 1 unit) — same class of bug as the confirmed `ohlcv_bars.volume` truncation fixed in migration `fcec1b5ac8a0` | Any order/execution/position repository implementation (Phase 2) | `INTEGER`/`BIGINT` → `NUMERIC`, following the `ohlcv_bars.volume` fix (migration `fcec1b5ac8a0`, Step 1.4) | Step 1.4 live-execution finding (2026-07-02); Doc 09 §Entity Standards; Doc 11 §1, §2 |
| F-2 | `quantity`, `filled_quantity` | `core.orders` | `INTEGER` cannot represent fractional order quantities (e.g. crypto orders below 1 unit) | Order repository implementation (Phase 2) | Same as F-1 | Same as F-1 |
| F-3 | `quantity` | `core.executions` | `INTEGER` cannot represent fractional execution quantities | Execution repository implementation (Phase 2) | Same as F-1 | Same as F-1 |
| F-4 | `quantity` | `core.positions` | `INTEGER` cannot represent fractional position quantities | Position repository implementation (Phase 2) | Same as F-1 | Same as F-1 |

**Status as of 2026-07-02:** No active data corruption from F-1–F-4 today
— no order/execution/position repository exists yet, so nothing writes
to these columns. `ohlcv_bars.volume` (the fifth instance of this
pattern) was live and actively truncating data; it has been fixed and
verified (Step 1.4, migration `fcec1b5ac8a0`). F-1 through F-4 remain
open and must be resolved before Phase 2 begins.

---

## Phase 8 — Implementation Scope Decisions (Recorded, Not to Be Re-litigated by Silence)

Explicit scope decisions made during implementation about how much of a
governing document to build now vs. defer. Distinct from Phase 7 above:
those are tracked defects; these are deliberate boundaries, recorded so
a future session without this conversation's context doesn't silently
re-expand scope or re-derive a different boundary from Doc 11's text.

| ID | Decision | Rationale | Reference |
|----|----------|-----------|-----------|
| S-1 | Doc 11 (Data Engineering) Phase 1 implementation scope = **Part 2 (§1–§9, "Market Data Connectors" through "Performance & Operations") only.** Parts 3–7 — ETL/ELT orchestration engine, streaming architecture, the versioned dataset catalog/publication lifecycle (Part 4), deep data governance/security/compliance/DR (Part 4), distributed execution/worker clusters (Part 5), the full Data Quality/Validation/Lineage/Catalog framework (Part 6), and the Enterprise Lakehouse/storage-engine architecture (Part 7) — are explicitly OUT of scope for Phase 1 and any near-term phase. | These parts describe enterprise-scale platform infrastructure (comparable to standing up an Airflow-style orchestrator, Kafka, a data catalog, and a Delta Lake/Iceberg-style Lakehouse from scratch) not needed at the platform's current stage. Doc 11 never declares phase boundaries itself, so without this record the boundary could be silently re-litigated or expanded by a future session reading only the raw document. | Step 1.4→1.5 planning inventory (2026-07-02); Doc 11 Parts 2–7 |
| S-2 | Within the in-scope Part 2, four items are implemented as scoped-down versions, not Part 2's/Part 6's full enterprise specification: **§5 Data Validation Engine** = basic schema/range/completeness checks, not a full validation framework; **§6 Data Quality Scoring** = simple computed flags, not the formal 5-metric scoring system; **§8 Error Recovery** = retry with backoff + logging, not a full dead-letter-queue/operator-notification system; **§2 "Publish" pipeline stage** = a minimal "mark as ingestion-complete" step scoped to market data, not Part 4's full versioned dataset-lifecycle/catalog machinery. | Same rationale as S-1, applied within Part 2 itself — its section text (and Part 6's/Part 4's much deeper specifications of the same concepts) describe more machinery than a solo-developer platform's near-term needs justify. | Step 1.5+ planning (2026-07-02); Doc 11 §2, §5, §6, §8; Doc 11 Part 4 §1–2, Part 6 |

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
