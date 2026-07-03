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

Findings surfaced during backend implementation (originally Phase 1, Doc
11 Market Data Ingestion, Steps 1.2–1.4; extended in Phase 2, Doc 14
Trading Infrastructure — F-10 Step 2.2 signals idempotency, F-9 Step 2.3
strategy versioning; extended in Phase 3 planning and implementation —
F-11, an accepted divergence record, not an open gap; F-12, a real
structural debt (pipeline ordering); F-13, a schema/lineage gap RESOLVED
same-step; F-14, a structural clarification distinguishing the §10.7.5
pre-trade-check artifact from the §11.5.13 portfolio risk-assessment
artifact; F-15, the Step 3.4 real-Pre-Trade-Risk scope record) that are
tracked defects/open gaps requiring resolution before
a specific future phase/workflow begins — unlike Phase 4/5 above, these
are NOT accepted design decisions. F-11 and F-13 are the exceptions: F-11
documents an already-resolved, deliberate divergence (kept for visibility
alongside the related F-2/F-3/F-4 entries it distinguishes itself from);
F-13 documents a gap that was found and fixed within the same step
(Step 3.3), kept as a resolved record rather than deleted so the prior
risk and its fix remain visible. Recorded here so each finding surfaces
again naturally (e.g. when a blocked repository is about to be
implemented) rather than depending on anyone's memory.

| ID | Field(s) | Table | Issue | Must resolve before | Resolution pattern | Reference |
|----|----------|-------|-------|----------------------|---------------------|-----------|
| F-1 | `bid_size`, `ask_size`, `last_size`, `volume` | `market_data.ticks` | `INTEGER`/`BIGINT` cannot represent fractional trade/order sizes (e.g. crypto sizes below 1 unit) — same class of bug as the confirmed `ohlcv_bars.volume` truncation fixed in migration `fcec1b5ac8a0` | Any order/execution/position repository implementation (Phase 2) | `INTEGER`/`BIGINT` → `NUMERIC`, following the `ohlcv_bars.volume` fix (migration `fcec1b5ac8a0`, Step 1.4) | Step 1.4 live-execution finding (2026-07-02); Doc 09 §Entity Standards; Doc 11 §1, §2 |
| F-2 | `quantity`, `filled_quantity` | `core.orders` | `INTEGER` cannot represent fractional order quantities (e.g. crypto orders below 1 unit) | Order repository implementation (Phase 2) | Same as F-1 | Same as F-1 |
| F-3 | `quantity` | `core.executions` | `INTEGER` cannot represent fractional execution quantities | Execution repository implementation (Phase 2) | Same as F-1 | Same as F-1 |
| F-4 | `quantity` | `core.positions` | `INTEGER` cannot represent fractional position quantities | Position repository implementation (Phase 2) | Same as F-1 | Same as F-1 |
| F-5 | `(asset_id, action_type, ex_date)` | `market_data.corporate_actions` | `UNIQUE(asset_id, action_type, ex_date)` (migration `97e88a746f25`) cannot distinguish two same-type actions with the same ex-date (e.g. a special dividend and a regular dividend both ex-dated the same day) — the second silently revises the first via `ON CONFLICT DO UPDATE` instead of being stored as a separate row | Before ingesting any corporate-actions source that can report same-day same-type multi-actions, or immediately if this case is observed in real data | Natural key needs an additional disambiguating column; Doc 11 §3 does not currently provide one (no per-action sequence/identifier field) | Migration `97e88a746f25` (Step 1.10); Doc 11 §3 |
| F-6 | `record_date`, `payment_date` | `market_data.corporate_actions` | Always `NULL` — yfinance's basic `Ticker.dividends`/`Ticker.splits` API only exposes `ex_date`, not the fuller corporate-action calendar. Both columns are nullable (Step 1.1 schema), so this is a gap, not a bug | When a consumer needs record/payment date specifically (e.g. settlement-date-aware calculations), not just ex-date | Requires a richer data source than yfinance's basic dividends/splits API (unnamed by Doc 11), or a yfinance calendar endpoint not yet investigated | `YFinanceConnector.fetch_corporate_actions` (Step 1.10); Doc 11 §3 |
| F-7 | Symbol Changes, Delistings, Mergers (event-type coverage) | `market_data.corporate_actions` (connector scope) | Doc 11 §3 names 6 supported event types; only Dividends and Splits/Reverse Splits are sourced (via yfinance). No implemented data source for Symbol Changes, Delistings, or Mergers | When Doc 11 names a vendor for these event types, or before any consumer needs them | Doc 11 does not name a corporate-actions vendor for any event type; yfinance's `Ticker` API has no clean endpoint for these three | `YFinanceConnector` (Step 1.10); Doc 11 §3 |
| F-8 | `adjustment_factor` | `market_data.ohlcv_bars` | Corporate-action facts (splits/dividends) are recorded in `market_data.corporate_actions`, but `ohlcv_bars.adjustment_factor` is never recomputed/updated from them — historical bars remain exactly as originally ingested (raw), unadjusted for later splits/dividends | Before any backtesting/analytics consumer requires split/dividend-adjusted historical price series | Correctly chaining multiple adjustments over a price series (multiple splits, ordering, precision) is a materially larger feature Doc 11 §3 does not detail | `CorporateActionsIngestionService` (Step 1.10); Doc 11 §3 Rules ("Adjustments are versioned. Original raw values remain preserved.") |
| F-9 | `name` (sole natural key), no version-history storage | `core.strategies` | Doc 14 §10.2.5 requires: "Every strategy modification shall create a new version per P-2... Published strategy versions shall be immutable... Historical strategy versions shall remain available for audit, comparison, and rollback." The Step 1.1 schema has `name UNIQUE` as the only natural key and no separate version-history table, so `SQLAlchemyStrategyRepository.upsert`'s resolve-or-register pattern (`ON CONFLICT (name) DO UPDATE`, Step 2.3) **overwrites** the prior version's row in place — the previous version's config/description is not preserved anywhere, violating §10.2.5's immutability/audit/rollback requirement | Before any real strategy iteration/versioning workflow begins, or before Phase 2 is considered fully complete, whichever comes first | Requires a schema change: e.g. a separate `core.strategy_versions` table recording each version immutably, or changing the natural key from `name` alone to `(name, version)` so distinct versions coexist as distinct rows | Step 2.3 finding (2026-07-03); `persistence/repositories/strategy_engine.py` `SQLAlchemyStrategyRepository.upsert` docstring; Doc 14 §10.2.5; P-2 |
| F-10 | No idempotency/uniqueness constraint on `(strategy_id, asset_id, ts)` | `core.signals` | Migration `7c7482e4e00a` (Step 2.2) deliberately created `core.signals` with no natural-key uniqueness constraint. Consequence: re-invoking the same strategy for the same instrument at the same signal timestamp records a **second distinct row**, not a de-duplicated one. Live-observed in the Step 2.4 / Phase 2 regression pass (2026-07-02–03): running the reference strategy twice against the same `ts=2026-07-02 19:00:00+00` produced two `core.signals` rows. Note this is **arguably correct** for a P-5 immutable event log (each invocation *is* a separate generation event) — the gap is only that there is no protection against *unintended* duplicates from retries/re-invocation, unlike the ingestion tables. Doc 11 §2's ingestion tables (bars/ticks) carry an explicit "idempotent ingestion" requirement (external retryable feed); Doc 14 §10.6.4 states **no** equivalent idempotency requirement for internally-computed signals | Before any signal-generation service runs on a schedule or with retry/redelivery in a way that could produce unintended duplicate signal events, or before Phase 2 is considered fully complete, whichever comes first | Add a uniqueness constraint (e.g. on `(strategy_id, asset_id, ts)`) or a de-duplication rule at the recording-service layer — deferred until a real signal-generation service exists whose retry/re-invocation behavior can be observed, mirroring how the ticks idempotency gap (migration `a428732d6bfe`) was resolved only after Step 1.2 surfaced it concretely | Migration `7c7482e4e00a` docstring (Step 2.2); Step 2.4 regression live-observation (2026-07-03); Doc 14 §10.6.4; P-5 |
| F-11 | `quantity`, `filled_quantity` | `core.orders`, `core.executions`, `core.positions` | **NOT a gap — an accepted, documented divergence, recorded here so it is never mistaken for an oversight.** Doc 14 §10.7.5's Pre-Trade Risk Check API contract types `quantity` as `integer`, and Doc 09's original Step 1.1 schema matches (`INTEGER`, the same columns tracked as F-2/F-3/F-4). The Step 3.0 migration widening these columns to `NUMERIC` is a **deliberate, flagged divergence** from the docs' own typing — not a silent gap-fill — chosen because fractional crypto order/execution/position quantities require it, the same reasoning already established and live-verified for `ohlcv_bars.volume` (migration `fcec1b5ac8a0`, Step 1.4). F-2/F-3/F-4 tracked *that* the columns were wrong; F-11 documents *that the fix intentionally disagrees with Doc 14/Doc 09's literal integer typing*, which is a distinct fact worth its own record | **None — resolution is the Step 3.0 migration itself.** This entry does not require further action; it exists so the divergence is cited, not silently re-discovered | Must be cited explicitly in every subsequent step that implements/touches `quantity` fields (order generation, execution handling, position updates) so the NUMERIC choice is never mistaken for an unflagged oversight | Phase 3 planning inventory (2026-07-03); Step 3.0 migration; Doc 14 §10.7.5 (Pre-Trade Risk Check API, `quantity: integer`); Doc 09 §Entity Standards (Step 1.1 schema); F-2, F-3, F-4; precedent: migration `fcec1b5ac8a0` (Step 1.4) |
| F-12 | Pipeline ordering: `PortfolioConstructor`/`PositionSizer` relationship | `domain/portfolio/sizing.py`, `domain/portfolio/construction.py` (no schema/table — a code-structural finding) | **Real structural debt, not a scope decision** (same severity class as F-9). Doc 15 specifies the pipeline order as Construction → weights → Sizing: §11.3.1 "Portfolio construction produces target weights or exposures; position sizing converts these into actionable position sizes"; §11.2.12 "Portfolio construction shall integrate with Position Sizing (Section 11.3 — portfolio weights feed into position sizing)." Step 3.1 (Position Sizing) and Step 3.2 (Portfolio Construction) were built in the **reverse order** (Sizing → Construction — `PortfolioConstructor.construct` consumes `PositionSizingDecision`, Step 3.1's output) per owner instruction error. This is only safe today because exactly one reference strategy exists (Step 2.4): with N=1 at strategy_weight=1, "aggregate one sized position into a weight" and "aggregate one weight, then size it" are computationally equivalent (an identity transform, live-verified in the Step 3.2 report 2026-07-03) — the inversion produces no wrong numbers YET, but the code's *relationship* between the two stages does not match Doc 15's architecture | Before any second real strategy is built (Step 2.4-style) that would exercise genuine multi-strategy aggregation, or before a real optimization-based Construction methodology (§11.2.4 — mean-variance, risk parity, Black-Litterman) is implemented, whichever comes first — at that point the identity-transform equivalence breaks and the ordering becomes materially wrong, not just architecturally inverted | Invert the relationship: Portfolio Construction must run first and produce target weights (consuming per-strategy conviction/weight inputs, not sized positions); Position Sizing must consume those weights and convert them into actionable position sizes, per §11.3.1's literal text. This likely requires re-deriving `SizingContext`'s inputs (currently includes a `Signal` directly; would need to accept a portfolio-level target weight instead) and reworking `PortfolioConstructor`'s input type away from `StrategyContribution.decision: PositionSizingDecision` | Step 3.2 report (2026-07-03), flagged at implementation time in `domain/portfolio/construction.py`'s module docstring ("FLAGGED PIPELINE-ORDERING DIVERGENCE"); promoted to this tracked register per explicit owner instruction; Doc 15 §11.3.1, §11.2.12 |
| F-13 | ~~No `signal_id` column; `correlation_id` reused as a lineage carrier~~ **RESOLVED** | `core.orders` | **RESOLVED same-step (Step 3.3), 2026-07-03.** Doc 14 §10.6.5 requires orders be "created with complete lineage to the originating signal," and §10.7.3's canonical Order Model lists a dedicated "Signal Reference — Lineage to the originating signal" field. The Step 1.1 schema shipped with **no `signal_id` column** on `core.orders`; the first Step 3.3 implementation stored `OrderIntent.signal_id` into the existing `correlation_id` column as a best-effort carrier, with no FK to `core.signals`. This was **confirmed as column-overloading, not just a missing-FK gap**: `correlation_id` has an established, distinct platform meaning — Doc 10 §8 "Logging & Observability" lists "Request ID" and "Correlation ID" as separate fields every API request records; Doc 10 §6's domain-event envelope (`OrderExecuted`, `RiskViolation`, etc.) carries `correlation_id` as a cross-event tracing field; Doc 14 §10.1.8 requires "every event shall include ... correlation identifiers for traceability"; `audit.audit_log.correlation_id` (Step 1.1 schema) matches this same request/event-tracing semantic; `RequestIDMiddleware` (`api/middleware.py`) generates a distinct per-HTTP-request `request_id` for exactly this purpose | **None — resolution complete.** Migration `d1f8b6c4a7e2` (Step 3.3) added `core.orders.signal_id UUID REFERENCES core.signals(id)`, nullable (a manually-placed or non-signal-originated order may have no signal), with index `orders_signal_id_idx`. `SQLAlchemyOrderRepository.create` now writes to `signal_id` directly; `correlation_id` is left NULL/untouched, genuinely free for its own request/event-tracing purpose. Live-verified (2026-07-03): a real recorded `core.signals` row's id was written as `core.orders.signal_id`, read back in a fresh session and confirmed to reference the real signal row; `correlation_id` confirmed `NULL`; a bogus (all-zero) `signal_id` was rejected by the FK constraint, confirming referential-integrity enforcement now holds. Fresh-database migrate-from-scratch (all 8 migrations, `c3a8f2b91e4d` → `d1f8b6c4a7e2`) and upgrade/downgrade/re-upgrade round-trip both verified clean | The column-overloading risk is closed; kept as a resolved record (same pattern as F-1..F-4) so the prior gap and its fix remain visible, not silently forgotten | Step 3.3 migration `d1f8b6c4a7e2`; `domain/execution/entities.py` `OrderIntent`/`RecordedOrder` docstrings (updated); `persistence/repositories/execution.py` `SQLAlchemyOrderRepository.create` docstring (updated); Doc 14 §10.6.5, §10.7.3; Doc 10 §6 (event envelope), §8 (Logging & Observability); Doc 14 §10.1.8; `api/middleware.py` `RequestIDMiddleware` |
| F-14 | `analytics.risk_assessments` (table naming); `RiskLimit.portfolio_id` (new field) | `analytics.risk_assessments`, `analytics.risk_limits`, domain `RiskLimit` / `RiskAssessment` | **Structural clarification, not a defect — recorded so two same-named-ish artifacts are never conflated.** Step 3.4 introduced `analytics.risk_assessments` (migration `b2e4c9d17a30`) to store the Doc 14 §10.7.5 **pre-trade check** record: one row per gate evaluation of one order (`authorized`, `rejection_reason`, `individual_checks`, `check_id`, `computation_latency_ns`). The domain already carries a **different** artifact — the Doc 15 §11.5.13 `RiskAssessment` entity + `RiskAssessmentRepository` (portfolio-level `metrics` + `limit_assessments` + `breaches`, a periodic snapshot). These share the word "assessment" but are distinct: per-order gate audit vs. periodic portfolio risk snapshot. Step 3.4 keeps them in separate tables/repositories (`SQLAlchemyPreTradeRiskRepository` -> `analytics.risk_assessments` vs. the still-stub `RiskAssessmentRepository`). Also: `RiskLimit` gained a `portfolio_id` field (the Step 0.6 skeleton omitted it; needed so `save_limit`/`get_active_limits` round-trip the owning portfolio) — a natural completion of a "portfolio-level" (§11.5.7) entity, not a redefinition | Step 3.6 (P&L + portfolio risk metrics), when the §11.5.13 portfolio `RiskAssessment` gets a real persistence home: decide then whether it reuses `analytics.risk_snapshots` (already metric-shaped, present since Step 1.1) or a new table — and do **not** overload `analytics.risk_assessments`, which is pre-trade-check-shaped | Keep the two concepts in separate tables/repositories (already done); §11.5.13 portfolio-assessment persistence deferred to Step 3.6 | Step 3.4 migration `b2e4c9d17a30`; `domain/risk/entities.py` (`PreTradeRisk*`, `RiskLimit.portfolio_id`); `persistence/repositories/risk.py`; Doc 14 §10.7.5; Doc 15 §11.5.7, §11.5.13 |
| F-15 | Pre-trade check coverage (code-structural; no single column) | `domain/risk/pretrade.py`, `application/risk/service.py` (`assess_pre_trade`) | **Step 3.4 scope record (S-5), not a defect.** The real pre-trade gate implements only the §10.7.5 **Risk Limit Check** — specifically the `position_size` and `gross_exposure` limits ("position limits, exposure limits" per §10.7.5) — and is deterministic, fail-closed, and audited. **Deferred:** (a) the other six §10.7.5 check categories — compliance/short-sale, price sanity/fat-finger, trading schedule, instrument state (halt/restricted), duplicate detection, quantity/lot-size validation — and **loss** limits; (b) any limit whose `metric_name` is outside `{position_size, gross_exposure}` is ignored by the pre-trade gate (var/leverage/drawdown limits belong to the §11.5.8 monitoring path via `check_limits`, not pre-trade); (c) the §10.7.5 latency SLO (≤500µs p99.9, §10.1.12) and its **timeout-triggered** default-deny are not enforced by a real timer — `computation_latency_ns` is measured and recorded, but the gate fails closed only on **exception**, not on a latency-budget overrun; (d) `PreTradeRiskRequest` is assembled by the **caller** from the order + gathered price / current-position / portfolio-value context — automatic context-gathering inside a live `ExecutionService` is not built (`ExecutionService` is still the Step 0.4 stub); (e) the gate records its decision in `analytics.risk_assessments` but does **not** transition `core.orders.status` CREATED→VALIDATED/REJECTED (§10.7.4) — the order-lifecycle state machine remains unbuilt (per Step 3.3's `OrderStatus` docstring) and is deferred to Step 3.5 | Each deferred item before the workflow that needs it: the CREATED→VALIDATED/REJECTED status transition + duplicate detection before **Step 3.5** (execution/lifecycle); compliance/schedule/instrument-state before any **live (non-paper) trading**; latency-SLO enforcement before the §10.1.12 p99.9 budget is a real operational requirement | Additive: extend `evaluate_pretrade` with further check functions and wire the order-status transition when the §10.7.4 state machine is built — each layers onto the framework established here | Step 3.4: `domain/risk/pretrade.py`, `application/risk/service.py` (`assess_pre_trade`); Doc 14 §10.7.5 + §Pre-Trade Risk Check API Contract; Doc 15 §11.5.7–§11.5.8; S-5 |

**Status as of 2026-07-03:** **F-2, F-3, and F-4 are now RESOLVED** —
Step 3.0 (migration `861eb5a06b23`) widened `core.orders.quantity`/
`filled_quantity`, `core.executions.quantity`, and `core.positions.quantity`
from `INTEGER` to `NUMERIC(28,8)`, live-verified (upgrade, column-type
inspection, downgrade, re-upgrade, and a full fresh-database migrate-from-
scratch all confirmed clean) before any order/execution/position write
code was implemented — satisfying S-4/S-5's prerequisite-step requirement.
No data corruption occurred for F-2/F-3/F-4: no order/execution/position
repository wrote to these columns before the fix landed, so this was a
preventive fix, not a remediation. **F-1 is now also RESOLVED** — Step
3.0 (migration `4253bf6672b9`) widened `market_data.ticks.bid_size`,
`ask_size`, `last_size`, and `volume` from `INTEGER`/`BIGINT` to
`NUMERIC(28,8)`. Unlike F-2/F-3/F-4, **F-1 was live active corruption**,
discovered while implementing this migration: `CCXTConnector.
fetch_latest_tick` (infrastructure/market_data/ccxt_connector.py)
contained `volume=int(ticker["baseVolume"])` — the identical bug class
to the confirmed `ohlcv_bars.volume` truncation (migration `fcec1b5ac8a0`,
Step 1.4), silently truncating every live tick's real fractional volume.
Fixed in the same step (connector now uses the existing `_to_decimal`
helper, matching `bid`/`ask`/`last`) and live-verified: a real BTC/USDT
tick fetched with `volume=Decimal('23939.89268')` persisted with an exact
match, versus the pre-fix behavior which would have stored `23939`.
`bid_size`/`ask_size`/`last_size` had no active writer (verified via code
search — no connector populates them today), so the domain-entity type
widening (`RawTick`/`Tick`: `int | None` → `Decimal | None`) for those
three is preventive, closing the gap before a future connector could
reintroduce the same bug. See **F-11** for the deliberate, flagged
divergence the F-2/F-3/F-4 fix represents from Doc 14 §10.7.5's literal
`integer` typing. F-5 through F-8
(Step 1.10, Corporate Actions Processing) are scope/coverage gaps rather
than active corruption — `corporate_actions` writes are correct for the
event types and fields it does implement (Dividends, Splits/Reverse
Splits, ex_date only), live-verified against real AAPL historical split
and dividend data. F-9 (Step 2.3, `core.strategies` versioning) is active
today: `SQLAlchemyStrategyRepository.upsert` is live and does overwrite
prior version rows on every re-registration — not corruption of a single
write, but data loss of prior version history on each re-registration.
F-10 (Step 2.2, `core.signals` no natural-key idempotency) is present but
not actively harmful today: it produces additional immutable signal-event
rows on re-invocation, which is arguably correct P-5 behavior rather than
corruption — it becomes a real concern only once a retrying/scheduled
signal-generation service could emit unintended duplicates. Both F-9 and
F-10 were surfaced/logged during Phase 2 (Steps 2.2–2.3) and confirmed in
the Phase 2 regression pass; F-10 was flagged in the Step 2.2 migration
docstring at the time and promoted to this tracked register during the
Phase 2 regression pass (2026-07-03).

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
| S-2 | Within the in-scope Part 2, three items are implemented as scoped-down versions, not Part 2's/Part 6's full enterprise specification: **§5 Data Validation Engine** = basic schema/range/completeness checks (Step 1.6), not a full validation framework; **§6 Data Quality Scoring** = simple computed flags (Step 1.7), not the formal 5-metric scoring system; **§8 Error Recovery** = retry with backoff + logging + per-row checkpoint isolation (Step 1.8), not a full dead-letter-queue/operator-notification system. **CORRECTED 2026-07-02 (Phase 1 regression pass):** this entry previously also listed "§2 'Publish' pipeline stage = a minimal mark-as-ingestion-complete step" as scoped-down-and-implemented — that was inaccurate. Publish was never implemented at any scope, minimal or otherwise; it remains entirely deferred alongside Enrich (see `application/market_data/service.py`'s "SCOPE NOTE (Step 1.2, still current)"). | Same rationale as S-1, applied within Part 2 itself — its section text (and Part 6's/Part 4's much deeper specifications of the same concepts) describe more machinery than a solo-developer platform's near-term needs justify. | Step 1.5+ planning (2026-07-02); Doc 11 §2, §5, §6, §8; Doc 11 Part 4 §1–2, Part 6 |
| S-3 | Doc 11 §7 "Maintain dataset version history" is judged satisfied at S-2 scope by: `updated_at` (`clock_timestamp()` on every write, Step 1.3) + an insert-vs-revised count logged per `upsert_bars()` batch via Postgres' `xmax = 0` idiom (Step 1.9). This does **not** capture *what* changed (no before/after delta, no queryable history table) — only *that* and *when* a bar was last written and whether that write was a fresh insert or a revision. A full versioned/immutable dataset system is Doc 11 Part 4 territory, out of scope per S-1. | A real delta-tracking audit table was considered and rejected as disproportionate: nothing in the current pipeline reads or needs historical deltas (no UI, no analytics, no correction-auditing consumer exists yet). Revisit — build a real audit trail (before/after values, not just insert/revised counts) — when an actual consumer needs to answer "what did this bar look like before it was revised," e.g. auditing vendor corrections or diagnosing an ingestion bug after the fact. | Step 1.9 (2026-07-02); Doc 11 §7 |
| S-4 | **Phase 2 scope = Steps 2.1–2.4 (Strategy Plugin Interface): (2.1) the abstract strategy contract, (2.2) Signal generation/validation/recording, (2.3) the strategy registry against `core.strategies`, (2.4) one reference strategy proving the contract is genuinely pluggable.** Order Generation (Doc 14 §10.6.5) and Portfolio Construction / Position Sizing (Doc 15 §11.1.5–§11.3) are explicitly **out of scope for Phase 2**. They require F-1/F-2 (`core.orders.quantity`/`filled_quantity` `INTEGER`→`NUMERIC`) resolution first — Step 2.5 (conditional, done immediately before any real order-writing code) — and constitute their own future phase-boundary decision. | The handbook's own pipeline (Doc 14 §10.6.4→§10.6.5, Doc 15 §11.1.5) puts the strategy plugin boundary at the **Signal**, not the Order: a strategy emits a Signal; position sizing and order construction are separate downstream governed services (Doc 15 Portfolio Construction, Doc 14 Order Generation), the former not yet built even as a stub. Steps 2.1–2.4 touch none of `core.orders`/`core.executions`/`core.positions`, so F-1–F-4 do **not** block Phase 2's start — but they become a hard prerequisite the moment any step writes real orders. Recorded so a future session doesn't silently expand Phase 2 into order execution and hit the F-1/F-2 corruption pattern unflagged. | Phase 2 planning inventory (2026-07-02); Doc 14 §10.6.4–§10.6.5; Doc 15 §11.1.5–§11.3; P-1, T-2, Port-1; F-1, F-2 |
| S-5 | **Phase 3 = Phase 3A only (Doc 14 + Doc 15 core trade-execution loop, scoped down): Step 3.0 (F-2/F-3/F-4 quantity-precision prerequisite migration), 3.1 Position Sizing, 3.2 Portfolio Construction (minimal), 3.3 Order Generation, 3.4 real Pre-Trade Risk, 3.5 simulated Execution, 3.6 P&L + portfolio risk metrics, 3.7 minimal Backtesting.** Phase 3B (Doc 12 Machine Learning Engineering, Doc 13 Research Engineering) is explicitly **deferred** — both are upstream provenance/governance layers, not required by the runtime trade loop (Phase 2's reference strategy already proved features can be computed inline from raw bars without a Feature Store or Model Serving; research promotion is a governance/lineage concern, not a runtime dependency of Signal→Order→Execution). Disproportionate enterprise-scale elements explicitly flagged and excluded from Phase 3A even within Doc 14/15's in-scope sections: broker/FIX connectivity and smart order routing (Doc 14 §10.8.3–10.8.5), colocation/FPGA/low-latency network infrastructure (Doc 14 §10.13), full paper/live trading operational infrastructure (Doc 14 §10.5/§10.6 in full — only Order Generation §10.6.5 and Circuit Breakers' basic shape are in scope), stress testing/scenario analysis/Monte Carlo/reverse stress testing (Doc 15 §11.5.6), factor risk decomposition (Doc 15 §11.5.5), capital-allocation optimization (Doc 15 §11.4), tax-aware rebalancing (Doc 15 §11.6), and Brinson/factor performance attribution (Doc 15 §11.7). | Same rationale as S-1: Docs 12–15 combined specify 939 subsections of enterprise-institutional platform architecture (distributed multi-GPU training, canary/blue-green model deployment, research workspace container orchestration, broker/FIX/venue routing, Monte Carlo stress testing, tax-aware rebalancing) disproportionate to a solo-developer platform's current stage. The dependency-chain trace done during Phase 3 planning showed the Signal→Order→Execution loop is self-contained and does not require Doc 12/13 at runtime, so Phase 3A can deliver a complete, valuable, real trading loop without first building ML/Research platforms. Recorded so a future session doesn't silently re-expand Phase 3 into Doc 12/13, or re-introduce the flagged Doc 14/15 enterprise elements while implementing Phase 3A's own in-scope sections. | Phase 3 planning inventory (2026-07-03); Doc 12 (280 subsections), Doc 13 (277 subsections), Doc 14 (216 subsections, scoped to §10.6.5, §10.7, thin §10.8, §10.9.4, thin §10.3), Doc 15 (166 subsections, scoped to §11.2, §11.3, §11.5.3/§11.5.7–8 only) |

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
