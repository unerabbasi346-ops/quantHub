# Architectural Invariants

**STATUS: AUTHORITATIVE — 2026-06-30**

This document records every architectural invariant that governs the Quant Hub Engineering Handbook. Invariants are non-negotiable principles that no document, specification, or implementation may violate. Every future document author shall load this file before writing and shall ensure all content complies with every invariant listed herein.

Invariants are organized into three tiers: Platform (applies universally), Data (frozen per Document 11), and ML (frozen per Document 12 outline). ML invariants are specializations of Platform invariants for the ML domain and shall not be read as independent overrides.

---

## Platform Invariants

These invariants apply to every platform component, document, and architectural domain. They originate from Document 00 (Project Constitution), Document 02 (System Architecture), and cross-cutting principles validated across Documents 11 and 12.

---

### P-1: Strategy Independence

**Origin:** Document 00, Document 11 I-3, Document 12 outline

No platform component, architecture, pipeline, data model, metadata schema, validation rule, governance policy, or service definition shall assume the existence of any specific trading strategy. The platform shall serve all strategies identically without strategy-specific customization in infrastructure, data handling, or platform logic.

Strategy-specific configurations, feature definitions, hyperparameters, signal definitions, and portfolio weights are external to platform architecture. They shall be defined and governed as strategy-level configurations that reference but do not alter platform architecture.

References to named strategies (including Lancaster) are permitted only in negation: "shall not assume Lancaster" or "independent of any individual strategy." No requirement, architecture, or specification may be expressed in terms of a specific strategy's needs.

---

### P-2: Immutability After Publication

**Origin:** Document 00 (Immutable History), Document 11 I-1, Document 12 outline

Every governed artifact, once published, shall be immutable. Corrections shall create new versions rather than modifying published records. Immutability applies to all of the following:

- Datasets and data products
- Metadata records
- Lineage records
- Quality reports and validation evidence
- Governance decisions and policies
- Audit records
- Backup copies and archives
- Data contracts
- Model artifacts (per Document 12)
- Experiment records (per Document 12)
- Observability evidence

Version identifiers shall be globally unique within their domain. Historical records shall remain permanently available for audit, reproducibility, and governance purposes.

---

### P-3: Technology Independence

**Origin:** Document 00, Document 11 I-2, Document 12 outline

Architecture shall remain independent of specific technology implementations. All of the following domains shall be technology-independent:

- Storage engines, file formats, and object storage
- Processing frameworks and query engines
- Cloud providers and infrastructure platforms
- Container runtimes and orchestration systems
- Graphics Processing Unit (GPU) vendors and compute accelerators
- Serialization formats and wire protocols
- Database systems and catalog implementations
- Monitoring, logging, and observability tools

Technology independence enables vendor migration without architectural redesign. No requirement, specification, or interface shall embed assumptions about specific technology products.

---

### P-4: Event-Driven Communication

**Origin:** Document 00, Document 02, Document 11 F-4

Inter-service communication shall use standardized event contracts. The Event Platform is the primary integration mechanism across Quant Hub. Synchronous API interactions shall be explicitly justified when used.

Every major platform capability shall communicate using events: Data Engineering, Feature Engineering, Machine Learning, Strategy Development, Backtesting, Walk-Forward Analysis, Paper Trading, Live Trading, Portfolio Management, Risk Management, Monitoring, and Analytics.

Event contracts shall be versioned, governed, and immutable after publication.

---

### P-5: Complete Auditability

**Origin:** Document 00, Document 11 I-6

Every governed action shall produce immutable audit evidence. Audit trails shall support complete reconstruction of platform history. Audit records shall include actor identity, action description, resource identifier, timestamp, previous state, new state, policy reference, and outcome.

Audit records shall be retained according to enterprise retention policies. Audit records shall remain available for regulatory, compliance, and investigative purposes.

---

### P-6: Automated Enforcement

**Origin:** Document 11 I-4

Manual enforcement of policies, quality rules, contracts, governance decisions, and security controls shall be minimized. Automation shall be the default enforcement mechanism across all architectural domains.

Enforcement shall never silently degrade. Every enforcement action shall produce explicit, auditable evidence of the decision and its rationale.

---

### P-7: Continuous Verification

**Origin:** Document 11 I-5

Validation, compliance monitoring, quality assessment, backup integrity, security posture, and model performance shall be verified continuously rather than periodically. Proactive detection shall take precedence over reactive response.

Verification failures shall generate actionable alerts with sufficient context for diagnosis. Verification results shall be immutable and auditable.

---

### P-8: No Bypass Architecture

**Origin:** Document 11 I-7

No governed component, service, interface, or operational path shall operate outside its designated governance, security, quality, or operational framework. Every governed path shall enforce its applicable policies without exception.

Silently degraded enforcement is prohibited. Every violation shall produce explicit, auditable evidence and trigger governance review.

---

### P-9: Separation of Concerns

**Origin:** Document 00 (Architecture Principles)

Platform components shall have clearly defined, non-overlapping responsibilities. Every component shall own exactly one architectural domain. Cross-domain integration shall occur through published, governed interfaces rather than internal dependencies.

Components shall not embed logic belonging to other components. This principle applies within documents (sections shall not redefine architectures owned by other sections) and within the platform (services shall not duplicate responsibilities of other services).

---

### P-10: Modular Design

**Origin:** Document 00 (Architecture Principles)

The platform shall be composed of independent, replaceable modules. Every module shall expose a governed interface and shall be independently testable, deployable, and scalable.

Module boundaries shall align with architectural domain boundaries defined in the handbook. Modules shall not share internal state. Module implementation shall be replaceable without affecting consumers.

---

### P-11: Loose Coupling and High Cohesion

**Origin:** Document 00 (Architecture Principles)

Modules shall be loosely coupled: changes to one module shall not require changes to others. Modules shall be highly cohesive: all functionality within a module shall serve a single, well-defined purpose.

Cross-module dependencies shall be explicit, governed, and documented. Hidden or undocumented dependencies are prohibited.

---

### P-12: Horizontal Scalability

**Origin:** Document 00 (Architecture Principles)

Every platform service shall support horizontal scaling. No service shall depend on vertical scaling (single-instance capacity increases) as its primary scalability mechanism.

Scaling decisions shall be data-driven based on operational metrics. Capacity planning shall ensure infrastructure expansion occurs before operational service objectives are impacted.

---

### P-13: Deterministic Processing

**Origin:** Document 00 (Architecture Principles)

Every data transformation, pipeline execution, validation rule, quality assessment, model training run, and inference operation shall be deterministic. Given identical inputs, configuration, and environment, the same operation shall produce identical outputs.

Determinism shall not depend on execution order, timing, or external mutable state. Randomness shall be explicitly seeded and recorded.

---

### P-14: Security by Design

**Origin:** Document 00, Document 11 D-7.12.1

Security shall be incorporated during architecture design rather than added after implementation. Every platform component shall be designed with security controls from inception.

The platform shall implement defense in depth, zero trust architecture, and least privilege. Security failure shall default to deny. Encryption shall protect data at rest and in transit.

---

### P-15: Observability by Design

**Origin:** Document 00, Document 11 D-7.13.1

Every platform component shall emit observability data (metrics, logs, traces) from inception. Observability shall not be retrofitted after implementation.

Observability data shall follow standardized models across all components and shall be correlated through common identifiers. Observability service failure shall not affect monitored platform services.

---

### P-16: Fail-Safe Architecture

**Origin:** Document 00 (Architecture Principles)

Platform services shall fail safely. Service failure shall not cause data corruption, silent data loss, or violation of governance guarantees.

Failure modes shall be explicitly documented. Recovery procedures shall be tested. No individual infrastructure component shall constitute a single point of failure.

---

### P-17: Enterprise Governance

**Origin:** Document 00, Document 11 D-7.11.1

Every platform asset, policy, process, and role shall be governed. Governance shall be by default: assets shall be explicitly exempted rather than requiring explicit inclusion.

Governance shall provide centralized oversight, policy enforcement, compliance management, and accountability. Governance decisions shall produce immutable audit records.

---

### P-18: Cloud-Neutral Architecture

**Origin:** Document 11 F-5

The architecture shall be vendor-independent and cloud-neutral. No component shall embed assumptions about specific cloud providers, deployment environments, or infrastructure vendors.

This invariant extends P-3 (Technology Independence) to deployment and infrastructure decisions.

---

---

## Data Platform Invariants

These invariants apply specifically to the data platform domain and are frozen per Document 11. Data invariants are specializations of Platform invariants for data-specific concerns.

---

### D-1: Bronze-Silver-Gold Medallion Architecture

**Origin:** Document 11 F-1

The data platform shall use three storage layers: Bronze (raw source data, immutable after receipt), Silver (validated, normalized, schema-compliant), and Gold (business-ready, optimized for analytics and model consumption).

Downstream layers shall never modify upstream data. Every dataset shall possess a globally unique identifier and version.

---

### D-2: Single Authoritative Data Repository

**Origin:** Document 11 D-7.1.1

The Enterprise Data Lake shall be the single authoritative repository for all persistent enterprise data assets within Quant Hub. No production dataset shall exist outside the scope of the data lake.

---

### D-3: Single Authoritative Metadata Registry

**Origin:** Document 11 D-7.7.2

The Enterprise Metadata Registry shall be the single authoritative source of platform metadata. No subsystem shall maintain independent authoritative metadata outside the Registry.

---

### D-4: Metadata Before Storage

**Origin:** Document 11 D-7.7.3

No dataset shall enter governed storage without first being registered in the Enterprise Catalog. Metadata registration shall precede physical storage operations.

---

### D-5: Complete Data Lineage

**Origin:** Document 11 D-7.8.1, D-7.8.4

Every governed data asset shall possess complete end-to-end lineage at multiple granularities: Dataset, Table, File, Partition, Column, Feature, Model, Pipeline, and Strategy levels. Lineage relationships shall be deterministic.

---

### D-6: Data Lifecycle Governance (8-State Model)

**Origin:** Document 11 D-7.4.1

Every governed dataset shall progress through defined lifecycle states: Draft, Validating, Published, Active, Archived, Legal Hold, Retired, Destroyed. State transitions shall be deterministic, governed, and fully auditable.

---

### D-7: Ten-Dimension Data Quality Model

**Origin:** Document 11 D-7.9.5

Every governed dataset shall be evaluated across standardized quality dimensions: Accuracy, Completeness, Consistency, Timeliness, Validity, Integrity, Uniqueness, Availability, Traceability, and Compliance.

---

### D-8: Contract-First Data Interfaces

**Origin:** Document 11 D-7.10.1

Every data interface shall be defined through a formal contract before implementation begins. Contracts shall serve as the single source of truth for interface expectations. Published contract versions shall be immutable.

---

### D-9: Zero-Trust Data Security

**Origin:** Document 11 D-7.12.3

No component, service, or identity shall be inherently trusted for data access. Every access request shall be explicitly authenticated and authorized. Security service failure shall default to deny.

---

### D-10: Separation of Duties in Data Governance

**Origin:** Document 11 D-7.11.3

Policy definition, policy enforcement, and policy audit shall be separated in data governance. No individual role shall possess unrestricted governance authority over data assets.

---

---

## ML Platform Invariants

These invariants apply specifically to the ML platform domain per the Document 12 frozen outline. ML invariants are specializations of Platform invariants for ML-specific concerns and shall not contradict their parent invariants.

---

### M-1: ML Reproducibility

**Origin:** Document 12 outline, extends P-13 (Deterministic Processing)

Every ML experiment, training run, model artifact, and prediction shall be reproducible given identical code, data, configuration, and environment. Reproducibility shall not depend on mutable external state.

Required captures for reproducibility: code version (git hash), dataset versions (Document 11 identifiers), dependencies, environment specification, random seeds, and hyperparameters.

---

### M-2: Feature-Contract Separation

**Origin:** Document 12 outline, extends P-9 (Separation of Concerns)

Feature engineering logic (how features are computed) shall remain separate from feature storage (where computed features are persisted in the Document 11 Feature Store). Feature definitions shall be governed through contracts independent of their physical storage.

---

### M-3: Model Lifecycle Governance

**Origin:** Document 12 outline, extends P-17 (Enterprise Governance)

Every ML model shall progress through governed lifecycle states with explicit transitions, approval gates, and immutable certification evidence. Model lifecycle states: Draft, Training, Validation, Staging, Production, Archived, Retired, Destroyed. No ungoverned model shall enter production.

---

### M-4: Data-Model Decoupling

**Origin:** Document 12 outline, extends P-3 (Technology Independence)

Model architecture, training logic, and inference code shall remain independent of specific dataset implementations. Models shall consume data through standardized Document 11 contracts rather than direct storage access.

---

### M-5: Continuous Model Validation

**Origin:** Document 12 outline, extends P-7 (Continuous Verification)

Model performance, drift, and stability shall be continuously monitored post-deployment. Validation shall not be limited to pre-deployment evaluation. Drift detection shall trigger automated alerts and may trigger automated retraining.

---

### M-6: ML Infrastructure Abstraction

**Origin:** Document 12 outline, extends P-3 (Technology Independence)

Training and inference shall operate on abstracted compute resources. ML code shall not embed assumptions about GPU vendors, container runtimes, cluster topology, or cloud providers.

---

### M-7: Single Authoritative Model Registry

**Origin:** Document 12 outline, extends D-3 (Single Authoritative Metadata Registry)

The Model Registry shall be the single authoritative source for model identity, versioning, lineage, artifacts, deployment state, and lifecycle governance. The Model Registry shall be distinct from but integrated with the Document 11 Dataset Registry and Metadata Registry.

---

### M-8: Model Risk Classification

**Origin:** Document 12 outline, extends P-17 (Enterprise Governance)

Every production model shall be classified by risk tier: Low (advisory models), Medium (signal generation), High (portfolio construction), Critical (autonomous trading). Risk tier shall determine validation rigor, approval authority, and monitoring frequency.

---

---

## Research Platform Invariants

These invariants apply specifically to the research platform domain per the Document 13 frozen architecture. Research invariants are specializations of Platform invariants for research-specific concerns and shall not contradict their parent invariants.

---

### R-1: Research Reproducibility by Design

**Origin:** Document 13, extends P-13 (Deterministic Processing)

Every published research finding, analysis result, and statistical conclusion shall be reproducible given identical code, data, environment, parameters, and random seeds. Reproducibility shall not depend on mutable external state.

Required captures for reproducibility: code version (git hash), data versions (Document 11 identifiers), feature versions (Document 12 Feature Engineering Architecture), model versions (Document 12 Model Registry), environment specification, all parameters, and all random seeds.

Reproducibility shall be verified before publication through automated re-execution producing identical or statistically equivalent results.

---

### R-2: Hypothesis-Experiment Separation

**Origin:** Document 13, extends P-9 (Separation of Concerns)

Research hypotheses (what is being tested) shall remain separate from research experiments (how testing is executed). Hypothesis definitions shall be governed independently of experiment implementations. One hypothesis may be tested by multiple experiments; one experiment may test multiple hypotheses.

Hypothesis registration shall occur before confirmatory analysis begins. Registration shall create an immutable record preventing HARKing (Hypothesizing After Results are Known).

---

### R-3: Governed Research-to-Production Promotion

**Origin:** Document 13, extends P-17 (Enterprise Governance) and P-8 (No Bypass Architecture)

No research finding shall enter production (strategy, model, or portfolio construction) without passing formal governance gates. Every promotion shall require: hypothesis validation, reproducibility verification, peer review approval, governance approval, and risk assessment.

Promotion decisions shall be evidence-based with immutable audit records per P-5. Rollback procedures shall exist for failed promotions.

---

### R-4: Knowledge as Enterprise Asset

**Origin:** Document 13, extends P-17 (Enterprise Governance)

Research knowledge — hypotheses, findings, analyses, methodologies, insights, and reports — shall be treated as governed enterprise assets per P-17. Knowledge shall be captured at the point of creation, organized through governed taxonomies, discoverable through search and browse, and preserved for the lifecycle of the platform.

Published knowledge artifacts shall be immutable per P-2. Knowledge shall not be destroyed before archival obligations are satisfied.

---

### R-5: Independent Research Workspaces

**Origin:** Document 13, extends P-3 (Technology Independence)

Research workspaces shall be isolated, reproducible computational environments. Workspace configuration shall not embed assumptions about specific tools, libraries, or infrastructure per P-3. Workspaces shall be provisioned through containerized environments with pinned dependencies.

Workspace isolation shall be enforced at compute, network, and data levels. No cross-workspace data leakage shall be permitted. Workspace configuration shall be versioned and reproducible.

---

### R-6: Strategy Independence (Research Domain)

**Origin:** Document 13, extends P-1 (Strategy Independence)

Research hypotheses, analysis methodologies, knowledge artifacts, and research infrastructure shall remain independent of any specific trading strategy. The research platform shall serve all strategies without strategy-specific customization.

No research workspace, hypothesis template, validation rule, or knowledge capture mechanism shall assume the existence of any specific trading strategy. Research domains (Signal, Risk, Portfolio, Execution, Market Microstructure, Macro) are organizational taxonomies, not strategy-specific constructs.

---

### R-7: Multiple Testing Awareness

**Origin:** Document 13, extends P-7 (Continuous Verification)

The research platform shall provide statistical infrastructure for multiple testing correction (Bonferroni, Holm-Bonferroni, Benjamini-Hochberg), p-hacking prevention (pre-registration, analysis plan comparison), and false discovery rate control.

Multiple testing correction shall be required when multiple hypotheses are tested on shared or overlapping data. Correction method shall be pre-registered. Both raw and corrected significance measures shall be reported.

---

---

## Trading Platform Invariants

These invariants apply specifically to the trading platform domain per the Document 14 frozen outline. Trading invariants are specializations of Platform invariants for trading-specific concerns and shall not contradict their parent invariants.

---

### T-1: Deterministic Backtesting

**Origin:** Document 14 outline, extends P-13 (Deterministic Processing)

Backtesting shall produce deterministic results. Given identical strategy configuration, market data, execution assumptions, and random seeds, every backtest execution shall produce identical results. All sources of non-determinism shall be explicitly seeded and recorded.

Backtest reproducibility shall require: strategy version, data versions (Document 11 identifiers), all configuration parameters, all random seeds, code version, and execution environment. Automated replay verification shall confirm determinism.

---

### T-2: Strategy-Infrastructure Separation

**Origin:** Document 14 outline, extends P-9 (Separation of Concerns)

Trading strategy logic shall remain separate from trading infrastructure. Infrastructure shall provide trading services — order management, execution routing, position tracking — without embedding strategy-specific assumptions per P-1.

Strategies shall be external configurations that reference platform services through governed interfaces. No strategy-specific signal logic, portfolio construction rule, or execution preference shall be embedded within trading infrastructure.

---

### T-3: Paper-Live Parity

**Origin:** Document 14 outline, extends P-13 (Deterministic Processing)

Paper trading and live trading shall share the same infrastructure, execution path, data feeds, signal generation pipeline, order management, and monitoring. The sole difference between paper and live trading shall be whether actual capital and orders are involved.

Paper trading shall accurately predict live trading behavior. Any divergence between paper and live performance indicates an infrastructure or execution modeling deficiency that shall be investigated.

---

### T-4: Governed Strategy Promotion

**Origin:** Document 14 outline, extends P-17 (Enterprise Governance) and P-8 (No Bypass Architecture)

No trading strategy shall enter live trading without passing governed promotion gates. Promotion shall require: backtest validation, walk-forward verification, paper trading validation, risk approval, and governance council approval.

Each promotion gate shall require defined evidence, approval authority, and immutable approval records per P-5. Promotion failure shall produce documented rationale. Rollback procedures shall exist for promoted strategies.

---

### T-5: Complete Trade Auditability

**Origin:** Document 14 outline, extends P-5 (Full Auditability)

Every trading action — signal generation, order creation, order modification, execution, fill, position change, profit and loss (P&L) event, and circuit breaker activation — shall produce immutable audit records per P-5. Complete trade reconstruction shall be possible from audit trails.

Audit records shall be tamper-proof and retained according to enterprise retention policies. Trade audit trails shall support regulatory compliance, dispute resolution, and operational investigation.

---

### T-6: Trading Circuit Breakers

**Origin:** Document 14 outline, extends P-8 (No Bypass Architecture)

Trading infrastructure shall implement governed circuit breakers that halt trading on defined thresholds: P&L-based (max drawdown, daily loss limit), risk-based (max position, max exposure, max VaR), operational (data feed loss, execution failure, latency exceeding threshold), and governance (manual halt, scheduled pause).

Circuit breakers shall default to halting trading — they shall never silently degrade. Breaker activation shall produce immutable records per P-5. Breaker release shall require governance authorization.

---

### T-7: Real-Time Determinism

**Origin:** Document 14 outline, extends P-13 (Deterministic Processing)

Trading infrastructure shall process signals and orders with bounded latency. Signal-to-order latency, order-to-exchange latency, and fill-to-position latency shall be measured, governed through Service Level Objectives (SLOs), and continuously monitored per P-15.

Latency SLOs shall be defined for all trading-critical paths. SLO violations shall trigger operational alerts and may trigger circuit breaker activation for sustained violations.

---

---

## Portfolio Platform Invariants

These invariants apply specifically to the portfolio management domain per the Document 15 frozen outline. Portfolio invariants are specializations of Platform invariants for portfolio-specific concerns and shall not contradict their parent invariants.

---

### Port-1: Portfolio Construction Separation

**Origin:** Document 15 outline, extends P-9 (Separation of Concerns)

Portfolio construction methodology — how portfolio weights are derived — shall remain separate from portfolio execution infrastructure — how weights are communicated to Document 14 Trading Infrastructure for order generation and execution.

Construction methodology changes shall not require trading infrastructure changes. Trading infrastructure shall consume portfolio weights through governed interfaces without embedding assumptions about how weights were derived. This principle extends the Strategy-Infrastructure Separation (T-2) into the portfolio domain.

---

### Port-2: Risk-Managed Capital Deployment

**Origin:** Document 15 outline, extends P-17 (Enterprise Governance)

Capital shall only be deployed through governed risk frameworks. Position sizes shall be constrained by risk budgets, not just conviction or signal strength. Risk limits shall gate capital deployment — no amount of conviction shall override portfolio-level risk constraints.

Risk budgets shall be allocated per strategy, monitored continuously per Port-4, and adjusted through governed processes. Capital allocation decisions shall reference risk budget utilization.

---

### Port-3: Deterministic Portfolio State

**Origin:** Document 15 outline, extends P-13 (Deterministic Processing)

Portfolio state, risk metrics, and performance attribution shall be deterministic. Given identical positions, market data, risk model parameters, and attribution methodology, every computation shall produce identical risk metrics and attribution results.

Risk model execution shall be seeded and reproducible. Attribution computations shall be recorded with complete inputs for verification and audit.

---

### Port-4: Continuous Risk Monitoring

**Origin:** Document 15 outline, extends P-7 (Continuous Verification)

Risk shall be continuously monitored, not periodically assessed. Risk metric computation shall execute on every material position change and on defined intervals. Risk breaches shall trigger immediate escalation through alerts and may trigger trading circuit breaker activation per T-6.

Risk monitoring shall never silently degrade. Monitoring service failure shall default to alerting and may trigger trading pause if risk cannot be assessed.

---

### Port-5: Strategy Risk Separation

**Origin:** Document 15 outline, extends P-17 (Enterprise Governance)

Risk management shall operate at the portfolio level with authority to constrain individual strategies. No strategy shall self-regulate its own risk limits without portfolio-level oversight. Portfolio risk management shall have authority to reduce or suspend strategy capital allocation based on risk assessment.

This principle prevents strategies from expanding risk exposure without governance. Strategy-level risk limits (Document 14 Section 10.10.6) shall be subordinate to portfolio-level risk limits.

---

### Port-6: Complete Portfolio Auditability

**Origin:** Document 15 outline, extends P-5 (Full Auditability)

Every portfolio decision — capital allocation change, risk limit modification, rebalancing action, construction methodology change, attribution publication — shall produce immutable audit records per P-5.

Portfolio audit records shall support reconstruction of portfolio state at any historical point. Audit trails shall be tamper-proof and retained per enterprise retention policies.

---

---

## Invariant Hierarchy and Conflict Resolution

Platform invariants (P-1 through P-18) are supreme. Domain invariants (D-1 through D-10, M-1 through M-8, R-1 through R-7, T-1 through T-7, Port-1 through Port-6) are specializations that extend Platform invariants for specific domains. Domain invariants shall not contradict their parent Platform invariants.

When invariants appear to conflict:
1. Platform invariants take precedence over domain invariants
2. Data invariants (Document 11) are frozen and may not be overridden by any domain invariants
3. Specific domain requirements that appear to conflict with invariants indicate either a misreading of the invariant or an improperly scoped requirement

---

## Usage Rules

Every document author shall:

1. Load this file before writing any new handbook content
2. Verify that every requirement, architecture, and specification complies with all applicable invariants
3. Reference invariants by their canonical identifiers (P-1, D-3, M-5, R-2, T-4, Port-2, etc.) in cross-references
4. Not introduce new invariants in individual documents — new invariants shall be proposed through governance review and recorded here
5. Not redefine, override, or weaken any invariant in subordinate documents

---

## Approval

| Role | Decision |
|------|----------|
| Platform Invariants (P-1 through P-18) | FROZEN — approved across Documents 00, 02, and 11 |
| Data Invariants (D-1 through D-10) | FROZEN per Document 11 |
| ML Invariants (M-1 through M-8) | FROZEN per Document 12 |
| Research Invariants (R-1 through R-7) | FROZEN per Document 13 |
| Trading Invariants (T-1 through T-7) | FROZEN per Document 14 |
| Portfolio Invariants (Port-1 through Port-6) | FROZEN per Document 15 |
| Date | 2026-06-30 |
| Amendment process | Governance Council approval required |
