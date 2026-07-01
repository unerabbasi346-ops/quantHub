# Document 15 — Portfolio Management Architecture

## Outline — FROZEN

**STATUS: FROZEN — 2026-06-30**

This outline is the approved implementation plan for Document 15. Content generation shall follow this structure exactly. Section identifiers, subsection counts, scope boundaries, exclusions, and shared interfaces defined herein shall not be altered without governance approval and an updated outline version. No section, subsection, domain, or architectural concept that overlaps with frozen Document 11, Document 12, Document 13, or Document 14 architectures shall be introduced during content generation.

---

## Purpose

Define the canonical architecture for Quant Hub's portfolio management and risk management platform. The portfolio platform governs the complete portfolio lifecycle: portfolio construction from trading signals and positions, position sizing, capital allocation across strategies, risk measurement and management, portfolio rebalancing, performance attribution, portfolio governance, and portfolio observability.

The portfolio platform consumes trade positions and P&L from Document 14 Trading Infrastructure, promoted research findings from Document 13 Research Engineering, model predictions from Document 12 ML Engineering, and market data from Document 11 Data Engineering. It is the final downstream consumer in the Quant Hub platform stack, governing the critical transition from individual trade decisions to portfolio-level capital deployment and risk oversight.

The portfolio platform shall be strategy-agnostic per P-1. Portfolio construction methodology, position sizing rules, risk models, and capital allocation strategies shall be external configurations within a governed portfolio framework. The platform shall not embed assumptions about specific portfolio theories, risk models, or allocation strategies.

---

## Scope Boundaries

### In Scope (Document 15 owns these domains)

- Portfolio Management Platform Architecture — overall portfolio platform design and integration
- Portfolio Construction Architecture — governed portfolio construction from strategy signals and positions
- Position Sizing Architecture — methodological framework for converting conviction to position size
- Capital Allocation Architecture — multi-strategy capital deployment and allocation management
- Risk Management Architecture — enterprise risk measurement, risk modeling, stress testing
- Portfolio Rebalancing Architecture — systematic portfolio rebalancing with cost and tax awareness
- Portfolio Performance Attribution Architecture — return attribution to factors, strategies, and decisions
- Portfolio Governance Architecture — portfolio-level governance, risk limits, and oversight
- Portfolio Security Architecture — portfolio data protection and access control
- Portfolio Observability Architecture — risk dashboards, exposure monitoring, portfolio alerts
- Portfolio Infrastructure — compute and operational infrastructure for portfolio operations

### Out of Scope (Owned by frozen documents)

| Topic | Frozen Document | Reference |
|-------|----------------|-----------|
| Data storage, data quality, data governance, data security | Document 11 | D-7.1 through D-7.13 |
| Feature engineering and feature storage | Document 12 | Section 8.2 |
| Model training, model validation, model registry, model serving | Document 12 | Sections 8.4–8.7 |
| Hypothesis management, research experiments, statistical analysis | Document 13 | Sections 9.3, 9.4, 9.6 |
| Research-to-production promotion | Document 13 | Section 9.13 |
| Strategy development, backtesting, walk-forward | Document 14 | Sections 10.2–10.4 |
| Paper trading, live trading, order management | Document 14 | Sections 10.5–10.7 |
| Execution management, trade lifecycle | Document 14 | Sections 10.8–10.9 |
| Trading governance, trading security | Document 14 | Sections 10.10–10.11 |
| Frontend portfolio UI | Documents 06, 08 | N/A |
| Database architecture | Document 09 | N/A |
| API specification | Document 10 | N/A |

### Shared Interfaces (Document 15 collaborates at these boundaries)

| Interface | Frozen Document Role | Document 15 Role |
|-----------|---------------------|-------------------|
| Data Platform | Market data, reference data, metadata, lineage (Document 11) | Portfolio consumes market data for risk computation, performance attribution, and rebalancing triggers |
| Feature Store | Governed features (Document 12 Feature Engineering Architecture, Section 8.2) | Portfolio consumes features for factor-based risk models and attribution |
| Model Serving | Production model inference (Document 12 Section 8.7) | Portfolio consumes model predictions for portfolio construction and risk models |
| Research Platform | Promoted research findings (Document 13 Section 9.13) | Portfolio consumes portfolio construction research and risk methodology research |
| Trading Infrastructure | Trade positions, P&L, execution records (Document 14) | Portfolio consumes positions and P&L for portfolio-level aggregation, risk computation, and rebalancing decisions |
| Metadata Registry | Single authoritative metadata source (D-7.7.2) | Portfolio artifacts registered in metadata registry |
| Lineage | Data lineage infrastructure (D-5) | Portfolio lineage from strategy allocation through position sizing to portfolio state |
| Governance | Policy enforcement, audit (D-7.11) | Portfolio governance extends enterprise governance with portfolio-level controls |
| Observability | Metrics, logging, alerting (D-7.13) | Portfolio-level risk metrics, exposure dashboards, and risk alerts |

---

## Architectural Principles (Document 15-specific)

These principles extend platform invariants with portfolio-domain specifics. They shall not contradict frozen invariants.

### Portfolio Construction Separation
Portfolio construction methodology (how portfolio weights are derived) shall remain separate from portfolio execution infrastructure (how weights are communicated to trading). This extends P-9 (Separation of Concerns) and ensures strategy infrastructure (Document 14) remains independent of portfolio methodology.

### Risk-Managed Capital Deployment
Capital shall only be deployed through governed risk frameworks. Position sizes shall be constrained by risk budgets, not just conviction. This extends P-17 (Enterprise Governance).

### Deterministic Portfolio State
Portfolio state, risk metrics, and performance attribution shall be deterministic per P-13. Identical positions, market data, and risk model parameters shall produce identical risk metrics and attribution.

### Continuous Risk Monitoring
Risk shall be continuously monitored, not periodically assessed per P-7. Risk breaches shall trigger immediate escalation. Risk monitoring shall never silently degrade.

### Strategy Risk Separation
Risk management shall operate at the portfolio level with authority to constrain individual strategies. No strategy shall self-regulate its own risk limits without portfolio-level oversight.

### Complete Portfolio Auditability
Every portfolio decision — capital allocation change, rebalancing action, risk limit modification — shall produce immutable audit records per P-5.

---

## Part 11 — Portfolio Management Architecture

Document 15 is organized as Part 11 of the Engineering Handbook, continuing the numbering convention from prior documents. Each section uses `## 11.X.Y` heading format. The document file is `docs/15_Portfolio_Management.md`. Every section ends with Risks, Acceptance Criteria, and Cross References.

---

### 11.1 Portfolio Management Platform Architecture — 24 subsections

**11.1.1 Purpose** — Declare the portfolio platform as the canonical architecture for enterprise portfolio and risk management. Position as the final downstream consumer consuming from Documents 11, 12, 13, and 14. Strategy-agnostic per P-1.

**11.1.2 Scope** — Enumerate covered domains. Enumerate excluded domains with frozen references.

**11.1.3 Design Goals** — Portfolio construction separation, risk-managed capital deployment, deterministic portfolio state, continuous risk monitoring, strategy risk separation, complete auditability.

**11.1.4 Architectural Principles** — The 6 principles defined above.

**11.1.5 Platform Overview** — High-level architecture showing consumption from Document 14 (positions, P&L), Document 13 (promoted research), Document 12 (model predictions), Document 11 (market data), and portfolio flow: Construction → Position Sizing → Capital Allocation → Risk Management → Rebalancing → Attribution → Governance.

**11.1.6 Platform Services** — Portfolio Construction Service, Position Sizing Service, Capital Allocation Service, Risk Management Service, Rebalancing Service, Attribution Service, Portfolio Governance Service.

**11.1.7 Integration Architecture** — Integration with upstream platforms and downstream consumers. Contract-governed interfaces per D-8.

**11.1.8 Portfolio Event Model** — Portfolio events: Portfolio Constructed, Positions Sized, Capital Allocated, Risk Limit Breached, Rebalance Triggered, Rebalance Executed, Attribution Computed.

**11.1.9–11.1.24** — Security context, observability context, governance context, performance, scalability, HA, DR, backup, capacity planning, monitoring, alerting, logging, runbooks, testing, deployment, risks, acceptance criteria, cross references.

---

### 11.2 Portfolio Construction Architecture — 16 subsections

**11.2.1 Purpose** — Define the governed framework for constructing portfolios from strategy signals and positions. Portfolio construction shall aggregate individual strategy positions into coherent portfolios with defined objectives and constraints.

**11.2.2 Scope** — Portfolio construction models, constraint modeling, objective functions, multi-strategy aggregation, portfolio optimization.

**11.2.3 Portfolio Model** — Canonical portfolio specification: identifier, name, constituent strategies (Document 14 references), construction methodology, objective function, constraints (risk, turnover, regulatory, liquidity), benchmark, owner, status.

**11.2.4 Portfolio Construction Methodology** — Methodology is external to platform per P-1: mean-variance optimization, risk parity, equal risk contribution, factor-based, Black-Litterman, or custom approaches. Platform provides methodology governance framework.

**11.2.5 Constraint Modeling** — Portfolio constraints: risk constraints (volatility, VaR, CVaR), position constraints (min/max per instrument, per sector, per strategy), turnover constraints, liquidity constraints, regulatory constraints.

**11.2.6 Multi-Strategy Aggregation** — Aggregating multiple strategy positions into single portfolio. Strategy weighting. Cross-strategy correlation consideration. Aggregation governance.

**11.2.7–11.2.16** — Portfolio optimization, benchmark tracking, portfolio construction governance, construction artifacts, construction reproducibility per P-13, integration with position sizing and capital allocation, risks, acceptance criteria, cross references.

---

### 11.3 Position Sizing Architecture — 14 subsections

**11.3.1 Purpose** — Define the methodological framework for converting strategy conviction (signal strength) into position sizes subject to risk constraints and capital allocation.

**11.3.2 Scope** — Position sizing models, risk-based sizing, Kelly criterion and variants, sizing constraints, sizing governance.

**11.3.3 Position Sizing Model** — Canonical sizing specification: sizing methodology (external per P-1), input parameters (signal strength, volatility forecast, correlation matrix, risk budget), output (target position size), constraints.

**11.3.4 Risk-Based Sizing** — Position size as function of risk budget allocation. Volatility targeting. Risk parity at position level. Maximum position as percentage of portfolio.

**11.3.5–11.3.14** — Kelly-based sizing, sizing constraints (max position, max sector, liquidity constraints), sizing governance, sizing integration with order generation (Document 14), sizing artifacts, risks, acceptance criteria, cross references.

---

### 11.4 Capital Allocation Architecture — 12 subsections

**11.4.1 Purpose** — Define the framework for allocating capital across trading strategies. Capital allocation shall balance risk-adjusted return expectations with risk budget constraints.

**11.4.2 Scope** — Capital allocation models, risk budgeting, allocation governance, allocation rebalancing.

**11.4.3 Capital Allocation Model** — Canonical allocation specification: total capital, allocation methodology (external per P-1), allocation per strategy, risk budget per strategy, reallocation triggers.

**11.4.4 Risk Budgeting** — Risk budget as primary constraint on capital allocation. Risk budget decomposition across strategies. Risk budget utilization monitoring.

**11.4.5–11.4.12** — Allocation optimization, allocation governance, drawdown-based allocation adjustment, allocation integration with position sizing, allocation artifacts, risks, acceptance criteria, cross references.

---

### 11.5 Risk Management Architecture — 18 subsections

**11.5.1 Purpose** — Define the enterprise risk management framework for measuring, monitoring, and controlling portfolio risk.

**11.5.2 Scope** — Risk measurement, risk modeling, stress testing, scenario analysis, risk reporting, risk governance.

**11.5.3 Risk Measurement** — Risk metrics: Value at Risk (VaR), Conditional VaR (CVaR/Expected Shortfall), volatility, maximum drawdown, beta exposure, factor exposures, concentration metrics, leverage ratios.

**11.5.4 Risk Models** — Risk model framework: covariance-based risk models, factor-based risk models, historical simulation, Monte Carlo simulation. Models are external configurations per P-1.

**11.5.5 Factor Risk Decomposition** — Decompose portfolio risk into factor exposures: market beta, size, value, momentum, quality, volatility, sector, and custom factors.

**11.5.6 Stress Testing** — Historical scenario replay, hypothetical stress scenarios, reverse stress testing, sensitivity analysis across risk factors.

**11.5.7–11.5.18** — VaR computation methodology, risk limit framework (portfolio-level limits extending Document 14 risk limits), real-time risk monitoring, risk reporting, risk governance, risk model validation, risk architecture integration with trading circuit breakers (Document 14), risks, acceptance criteria, cross references.

---

### 11.6 Portfolio Rebalancing Architecture — 14 subsections

**11.6.1 Purpose** — Define the framework for systematic portfolio rebalancing to maintain target allocations and risk profiles.

**11.6.2 Scope** — Rebalancing triggers, rebalancing methodology, cost-aware rebalancing, tax-aware rebalancing, rebalancing execution, rebalancing governance.

**11.6.3 Rebalancing Triggers** — Calendar-based rebalancing (periodic schedule), threshold-based rebalancing (allocation drift exceeding tolerance), risk-based rebalancing (risk exposure drift), event-based rebalancing (corporate actions, cash flows).

**11.6.4 Rebalancing Methodology** — Rebalancing to target weights, rebalancing to target risk, partial rebalancing vs full rebalancing. Methodology external per P-1.

**11.6.5–11.6.14** — Cost-aware rebalancing (transaction costs, market impact), tax-aware rebalancing, rebalancing execution through Document 14 order management, rebalancing governance, rebalancing artifacts, risks, acceptance criteria, cross references.

---

### 11.7 Portfolio Performance Attribution Architecture — 14 subsections

**11.7.1 Purpose** — Define the framework for attributing portfolio returns to strategies, factors, and decisions.

**11.7.2 Scope** — Return attribution, factor attribution, strategy attribution, decision attribution, attribution reporting.

**11.7.3 Return Attribution** — Brinson attribution (allocation effect, selection effect, interaction effect). Multi-period attribution compounding. Arithmetic vs geometric attribution.

**11.7.4 Factor Attribution** — Factor-based return decomposition: alpha, market beta, size, value, momentum, quality, volatility, sector, and custom factors.

**11.7.5–11.7.14** — Strategy attribution (per-strategy contribution to portfolio return), decision attribution (attribution to specific allocation or rebalancing decisions), attribution governance, attribution artifacts, attribution reproducibility per P-13, risks, acceptance criteria, cross references.

---

### 11.8 Portfolio Governance Architecture — 16 subsections

**11.8.1 Purpose** — Define portfolio-level governance extending Document 7.11, Document 13 research governance, and Document 14 trading governance. Portfolio governance provides the oversight framework for capital deployment and risk management.

**11.8.2 Scope** — Portfolio construction approval, capital allocation governance, risk limit governance, rebalancing governance, portfolio oversight.

**11.8.3 Portfolio Construction Approval** — Construction methodology approval, constraint approval, multi-strategy aggregation approval.

**11.8.4 Capital Allocation Governance** — Allocation approval, allocation change governance, drawdown-based reallocation governance.

**11.8.5 Portfolio Risk Governance** — Portfolio risk limit setting, risk limit modification, risk breach escalation, risk governance integration with trading circuit breakers.

**11.8.6–11.8.16** — Rebalancing governance, portfolio audit trail per P-5, governance dashboards, governance integration, exception management, risks, acceptance criteria, cross references.

---

### 11.9 Portfolio Security Architecture — 12 subsections

**11.9.1 Purpose** — Define portfolio-specific security extending Document 7.12, Document 13 research security, and Document 14 trading security. Portfolio security protects capital allocation decisions, risk exposures, and portfolio intellectual property.

**11.9.2 Scope** — Portfolio authentication, authorization, data encryption, access control, security monitoring.

**11.9.3–11.9.12** — Portfolio authorization (role-based access to portfolio construction, risk management, capital allocation), portfolio data encryption, security monitoring, security testing, risks, acceptance criteria, cross references.

---

### 11.10 Portfolio Observability Architecture — 14 subsections

**11.10.1 Purpose** — Define portfolio-specific observability extending Document 7.13, Document 13 research observability, and Document 14 trading observability. Portfolio observability provides risk dashboards, exposure monitoring, and portfolio alerts.

**11.10.2 Scope** — Risk dashboards, exposure monitoring, portfolio alerts, attribution dashboards, portfolio SLOs.

**11.10.3 Risk Dashboards** — Real-time risk dashboards: VaR, CVaR, volatility, factor exposures, stress test results, concentration metrics.

**11.10.4 Exposure Monitoring** — Real-time exposure: gross, net, delta, by asset class, by sector, by factor, by strategy.

**11.10.5–11.10.14** — Portfolio alerts (risk breaches, concentration warnings, drawdown alerts), attribution dashboards, portfolio SLOs, integration, risks, acceptance criteria, cross references.

---

### 11.11 Portfolio Infrastructure — 12 subsections

**11.11.1 Purpose** — Define compute, network, and operational infrastructure for portfolio operations extending Document 14 trading infrastructure.

**11.11.2 Scope** — Portfolio compute, storage, networking, operational resilience, cost optimization.

**11.11.3–11.11.12** — Portfolio compute (risk computation, optimization, attribution — batch-oriented with defined latency), storage (portfolio state, risk history, attribution history), networking, infrastructure abstraction per P-3, operational resilience, scaling, risks, acceptance criteria, cross references.

---

## Cross-Document Dependencies

### Documents that Document 15 depends on

| Document | Title | Nature of Dependency |
|----------|-------|---------------------|
| 00 | Project Constitution | Architectural principles, strategy independence |
| 02 | System Architecture | Portfolio Engine as system component |
| 03 | Technology Stack | Technology independence constraints |
| 09 | Database Architecture | Database services |
| 10 | API Specification | API design standards |
| **11** | **Data Engineering** | Market data, reference data, metadata, lineage, governance, security, observability |
| **12** | **Machine Learning Engineering** | Model predictions, features for risk models and attribution |
| **13** | **Research Engineering** | Promoted portfolio construction research, risk methodology research |
| **14** | **Trading Infrastructure** | Trade positions, P&L, execution records for portfolio construction and attribution |

### Documents that depend on Document 15

None — Document 15 is the final downstream consumer in the Quant Hub platform stack.

---

## Explicit Exclusions

The following topics are not covered by Document 15 and shall not be introduced:

- **Specific portfolio construction methodologies** — External to platform per P-1. Platform governs methodology, doesn't prescribe it.
- **Specific risk models** — External configurations per P-1.
- **Specific capital allocation strategies** — External configurations per P-1.
- **Data storage, data quality, data governance, data security** — Frozen in Document 11.
- **Feature engineering, model training, model validation** — Frozen in Document 12.
- **Research hypotheses, experiments, statistical analysis** — Frozen in Document 13.
- **Strategy development, backtesting, live trading** — Frozen in Document 14.
- **Order management, execution management** — Frozen in Document 14.
- **Frontend portfolio UI** — Owned by Documents 06/08.
- **Cloud-specific deployment** — Violates F-5, P-18.

---

## Section Summary

| Section | Topic | Subsections |
|---------|-------|-------------|
| 11.1 | Portfolio Management Platform Architecture | 24 |
| 11.2 | Portfolio Construction Architecture | 16 |
| 11.3 | Position Sizing Architecture | 14 |
| 11.4 | Capital Allocation Architecture | 12 |
| 11.5 | Risk Management Architecture | 18 |
| 11.6 | Portfolio Rebalancing Architecture | 14 |
| 11.7 | Portfolio Performance Attribution Architecture | 14 |
| 11.8 | Portfolio Governance Architecture | 16 |
| 11.9 | Portfolio Security Architecture | 12 |
| 11.10 | Portfolio Observability Architecture | 14 |
| 11.11 | Portfolio Infrastructure | 12 |
| **Total** | | **166** |

---

## Numbering Convention

- Document 15 = Part 11 (Sections 11.1–11.11)
- Heading format: `## 11.X.Y` for subsections
- Document file: `docs/15_Portfolio_Management.md`
- Every section ends with Risks, Acceptance Criteria, Cross References
- Cross-references to Documents 11, 12, 13, and 14 use frozen decision or section identifiers
- Requirements use "shall" (not "must" or "should")

---

## Writing Standards

Document 15 shall follow all rules in handbook guidelines and comply with all invariants in handbook/ARCHITECTURAL_INVARIANTS.md (P-1 through P-18, D-1 through D-10, M-1 through M-8, R-1 through R-7, T-1 through T-7).

---

## Approval

| Role | Decision |
|------|----------|
| Document 15 Outline | APPROVED and FROZEN |
| Sections | 11.1 through 11.11, 166 total subsections |
| Date | 2026-06-30 |
| Scope boundaries | As defined — zero overlap with frozen Documents 11, 12, 13, and 14 |
| Amendment process | Governance approval required for section additions, removals, or scope changes |
| Content generation | Shall follow this outline without deviation |
