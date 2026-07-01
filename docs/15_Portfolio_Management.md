# Document 15 — Portfolio Management Architecture

## Part 11 — Portfolio Management Architecture

---

# 11.1 Portfolio Management Platform Architecture

## 11.1.1 Purpose

The Portfolio Management Platform Architecture defines the canonical architecture for Quant Hub's enterprise portfolio and risk management platform.

The portfolio platform shall govern the complete portfolio lifecycle: portfolio construction from trading signals and positions, position sizing, capital allocation across strategies, enterprise risk measurement and management, portfolio rebalancing, performance attribution, portfolio governance, and portfolio observability.

The portfolio platform shall be the final downstream consumer in the Quant Hub platform stack. It shall consume trade positions and profit and loss (P&L) from Document 14 Trading Infrastructure, promoted research findings from Document 13 Research Engineering, model predictions from Document 12 ML Engineering, and market data from Document 11 Data Engineering. It shall produce portfolio-level decisions — capital allocation, position sizing parameters, rebalancing instructions, risk limits, and performance attribution — that govern how capital is deployed and risk is managed.

The portfolio platform shall be strategy-agnostic per P-1. Portfolio construction methodology, position sizing rules, risk models, and capital allocation strategies shall be external configurations within a governed portfolio framework. The platform shall provide the governance, infrastructure, and observability for portfolio management without embedding assumptions about specific portfolio theories or risk models.

---

## 11.1.2 Scope

The Portfolio Management Platform Architecture applies to all portfolio management and risk management within the Quant Hub platform.

Coverage includes:

- Portfolio Construction Architecture
- Position Sizing Architecture
- Capital Allocation Architecture
- Risk Management Architecture
- Portfolio Rebalancing Architecture
- Portfolio Performance Attribution Architecture
- Portfolio Governance Architecture
- Portfolio Security Architecture
- Portfolio Observability Architecture
- Portfolio Infrastructure

The following topics are intentionally excluded:

- Data storage, data quality, data governance, data security — Frozen per Document 11 (D-7.1 through D-7.13)
- Feature engineering, feature storage — Frozen per Document 12 (Section 8.2)
- Model training, validation, registry, serving — Frozen per Document 12 (Sections 8.4–8.7)
- Hypothesis management, research experiments — Frozen per Document 13 (Sections 9.3, 9.4)
- Research-to-production promotion — Frozen per Document 13 (Section 9.13)
- Strategy development, backtesting, walk-forward — Frozen per Document 14 (Sections 10.2–10.4)
- Paper trading, live trading, order management — Frozen per Document 14 (Sections 10.5–10.7)
- Execution management, trade lifecycle — Frozen per Document 14 (Sections 10.8–10.9)
- Frontend portfolio UI — Owned by Documents 06, 08

---

## 11.1.3 Design Goals

The portfolio platform architecture shall satisfy the following design goals:

- Portfolio Construction Separation — Portfolio construction methodology shall remain separate from execution infrastructure per P-9 and Port-1, ensuring trading infrastructure (Document 14) remains independent of portfolio methodology
- Risk-Managed Capital Deployment — Capital shall only be deployed through governed risk frameworks per Port-2; position sizes shall be constrained by risk budgets, not just conviction
- Deterministic Portfolio State — Portfolio state, risk metrics, and performance attribution shall be deterministic per P-13
- Continuous Risk Monitoring — Risk shall be continuously monitored per P-7; risk breaches shall trigger immediate escalation
- Strategy Risk Separation — Risk management shall operate at the portfolio level with authority to constrain individual strategies
- Complete Portfolio Auditability — Every portfolio decision shall produce immutable audit records per P-5
- Strategy Independence — Portfolio platform shall serve all strategies uniformly per P-1

---

## 11.1.4 Architectural Principles

The portfolio platform shall be governed by six architectural principles extending platform invariants.

### Portfolio Construction Separation

Portfolio construction methodology — how portfolio weights are derived — shall remain separate from portfolio execution infrastructure — how weights are communicated to Document 14 Trading Infrastructure. This extends P-9 (Separation of Concerns).

### Risk-Managed Capital Deployment

Capital shall only be deployed through governed risk frameworks. Position sizes shall be constrained by risk budgets, not just conviction. Risk limits shall gate capital deployment per P-17 (Enterprise Governance).

### Deterministic Portfolio State

Portfolio state, risk metrics, and performance attribution shall be deterministic per P-13. Identical positions, market data, and risk model parameters shall produce identical risk metrics and attribution.

### Continuous Risk Monitoring

Risk shall be continuously monitored, not periodically assessed per P-7. Risk breaches shall trigger immediate escalation. Risk monitoring shall never silently degrade.

### Strategy Risk Separation

Risk management shall operate at the portfolio level with authority to constrain individual strategies. No strategy shall self-regulate its own risk limits without portfolio-level oversight. This principle prevents strategies from expanding risk without governance.

### Complete Portfolio Auditability

Every portfolio decision — capital allocation change, rebalancing action, risk limit modification, construction methodology change — shall produce immutable audit records per P-5.

---

## 11.1.5 Portfolio Platform Overview

The portfolio platform shall provide end-to-end governed portfolio and risk management.

The portfolio platform shall consume:

- Trade Positions and P&L — From Document 14 Trading Infrastructure (Sections 10.6, 10.7, 10.9)
- Promoted Research — Portfolio construction and risk methodology research from Document 13 (Section 9.13)
- Model Predictions — From Document 12 Model Serving (Section 8.7) for risk models and factor models
- Market Data — From Document 11 for risk computation, performance attribution, and rebalancing triggers
- Reference Data — From Document 11 for instrument classifications, sectors, and factor definitions

The portfolio platform shall produce:

- Portfolio Construction — Portfolio weights and allocation targets for each strategy
- Position Sizing Parameters — Position sizing parameters communicated to Document 14 order generation
- Capital Allocations — Capital allocated per strategy with risk budgets
- Risk Metrics — Portfolio-level risk: Value at Risk (VaR), Conditional VaR (CVaR), volatility, factor exposures, stress test results
- Rebalancing Instructions — Rebalancing trades to maintain target allocations
- Performance Attribution — Return attribution to factors, strategies, and decisions

The portfolio flow shall progress through governed phases:

- Construction — Portfolio weights derived from strategy signals and positions
- Position Sizing — Conviction converted to position sizes under risk constraints
- Capital Allocation — Capital deployed across strategies with risk budgets
- Risk Management — Continuous risk measurement, monitoring, and control
- Rebalancing — Systematic rebalancing to maintain targets
- Attribution — Performance decomposed into factors, strategies, and decisions

---

## 11.1.6 Platform Services

The portfolio platform shall be composed of governed portfolio services.

Portfolio platform services include:

- Portfolio Construction Service — Portfolio construction from strategy positions with governed methodology and constraints
- Position Sizing Service — Conviction-to-position-size conversion under risk constraints
- Capital Allocation Service — Multi-strategy capital allocation with risk budgeting
- Risk Management Service — Risk measurement, modeling, stress testing, and monitoring
- Rebalancing Service — Systematic portfolio rebalancing with cost and tax awareness
- Attribution Service — Performance attribution to factors, strategies, and decisions
- Portfolio Governance Service — Portfolio-level governance, risk limits, and oversight

Services shall communicate through standardized event contracts per P-4.

---

## 11.1.7 Integration Architecture

The portfolio platform shall integrate with upstream platforms through governed interfaces.

Integration with Document 11 Data Platform shall include market data consumption for risk computation and attribution, reference data for instrument classifications and factor definitions, metadata registration per D-7.7.2, lineage recording per D-5 for portfolio decisions, and governance per D-7.11.

Integration with Document 12 ML Platform shall include model prediction consumption for risk models and factor models, feature consumption for factor-based analysis, and model version tracking.

Integration with Document 13 Research Platform shall include promoted research findings for portfolio construction methodology and risk methodology, and research lineage tracking.

Integration with Document 14 Trading Infrastructure shall include position and P&L consumption, position sizing parameter output to order generation (Section 10.6.5), capital allocation communication to live trading configuration, and risk limit communication to trading circuit breakers.

All integrations shall be contract-governed per D-8.

---

## 11.1.8 Portfolio Event Model

Every portfolio action shall produce standardized events through the Event Platform per P-4.

Portfolio event types include:

- Construction Events — Portfolio Constructed, Portfolio Weights Updated
- Sizing Events — Position Sizing Parameters Updated
- Allocation Events — Capital Allocated, Allocation Changed, Risk Budget Updated
- Risk Events — Risk Metrics Computed, Risk Limit Breached, Risk Limit Warning, Stress Test Completed
- Rebalancing Events — Rebalance Triggered, Rebalance Executed, Rebalance Completed
- Attribution Events — Attribution Computed, Attribution Published
- Governance Events — Methodology Approved, Risk Limit Modified, Allocation Approved

Every event shall include event identifier, timestamp, source service, correlation identifiers, and immutable payload per P-2.

---

## 11.1.9 Platform Security Context

Portfolio operations shall be secured through enterprise security controls extending Document 11 Section 7.12, Document 13 Section 9.14, and Document 14 Section 10.11.

Security requirements include authentication per D-9, authorization by role and portfolio scope, encryption at rest per D-7.12.5, and audit logging per P-5.

Detailed portfolio security architecture is defined in Section 11.9.

---

## 11.1.10 Platform Observability Context

Portfolio operations shall be observable through enterprise observability extending Document 11 Section 7.13, Document 13 Section 9.15, and Document 14 Section 10.12.

Observability requirements include real-time risk dashboards, exposure monitoring, portfolio alerts for risk breaches, and portfolio SLOs. Detailed portfolio observability architecture is defined in Section 11.10.

---

## 11.1.11 Platform Governance Context

Portfolio operations shall be governed through enterprise governance extending Document 11 Section 7.11, Document 13 Section 9.11, and Document 14 Section 10.10.

Governance requirements include construction methodology approval, capital allocation governance, risk limit governance, and portfolio audit trail per P-5. Detailed portfolio governance architecture is defined in Section 11.8.

---

## 11.1.12 Performance Requirements

The portfolio platform shall satisfy defined performance requirements.

Performance domains include risk computation latency (bounded time for VaR, CVaR, and factor exposure computation), optimization processing time for portfolio construction and rebalancing, attribution computation throughput, and real-time risk monitoring responsiveness.

Risk metric computation SLAs:

| Metric | Method | Target | Notes |
|--------|--------|--------|-------|
| Parametric VaR (1-day, 99%) | Covariance matrix | <= 5 seconds | Single portfolio, 500 positions |
| Historical VaR (1-day, 99%) | 500-day window | <= 30 seconds | Single portfolio |
| Monte Carlo VaR (1-day, 99%) | 10,000 paths | <= 120 seconds | GPU-accelerated |
| CVaR (Expected Shortfall) | Same as parent VaR | <= 1.5x parent VaR time | Single portfolio |
| Factor Decomposition | Risk model factors | <= 15 seconds | Full factor attribution |
| Full Stress Test Suite | All configured scenarios | <= 5 minutes | 50 scenarios typical |
| Intraday Risk Update | All metrics | <= 10 seconds | On material position change |

Risk metrics shall be computed on every material position change and on a scheduled interval (minimum: every 5 minutes for intraday risk, every 15 minutes for factor decomposition). Computation time exceeding 2x target shall trigger Warning alert.

---

## 11.1.13 Scalability Strategy

The portfolio platform shall scale to support strategy count growth, instrument universe growth, risk factor count growth, and portfolio count growth. Scaling shall preserve risk computation determinism per P-13.

---

## 11.1.14 High Availability

The portfolio platform shall operate with high availability. Risk monitoring shall be resilient to component failure. Risk computation services shall have redundancy. Portfolio state shall be persistent for recovery.

Portfolio infrastructure high availability topology:

| Component | Availability Target | Deployment Topology | Failure Response |
|-----------|-------------------|-------------------|-----------------|
| Risk Monitoring | 99.99% | Active-Active across 2 AZs | Automatic failover — no interruption |
| Risk Computation | 99.95% | Active-Active compute pool | Failed node replaced by pool |
| Portfolio State Store | 99.99% | Multi-AZ with synchronous replication | Automatic failover to replica |
| Rebalancing Engine | 99.9% | Active-Passive with auto-promotion | <= 15 minute failover |
| Attribution Engine | 99.5% | Warm standby | <= 1 hour — batch-oriented, can tolerate delay |
| Governance Services | 99.95% | Active-Active across 2 AZs | Automatic failover |
| API / Dashboard | 99.9% | Load-balanced across 2 AZs | Healthy instances serve traffic |

Network isolation: Portfolio infrastructure traffic shall be isolated from trading infrastructure traffic per Section 11.11.5. Graceful degradation: If attribution and reporting are unavailable, risk monitoring and position management shall continue operating at full capacity.

---

## 11.1.15 Disaster Recovery

DR for the portfolio platform shall enable portfolio operations resumption following failure. Recovery shall include portfolio state, risk history, attribution history, capital allocation records, and governance records. DR shall follow Document 11 DR architecture per D-7.5.

Portfolio platform RTO/RPO targets:

| Service Tier | RTO | RPO | Failover |
|-------------|-----|-----|----------|
| Core Risk Monitoring | <= 1 minute | Real-time (synchronous replication) | Active-Active automatic failover |
| Risk Computation | <= 5 minutes | <= 1 minute | Active-Passive with automatic promotion |
| Portfolio State (positions, P&L) | <= 5 minutes | <= 1 minute | Active-Passive with synchronous replication |
| Rebalancing Engine | <= 15 minutes | <= 5 minutes | Warm standby, manual activate |
| Attribution Engine | <= 1 hour | <= 1 hour (batch-oriented) | Cold standby |
| Governance Records | <= 15 minutes | 0 (immutable records, append-only) | Active-Active |
| Reporting Services | <= 4 hours | <= 24 hours | Cold standby |

These RTO/RPO targets operationalize the Document 11 D-7.5 service tier model. DR exercises shall validate these targets quarterly per Document 11 Section 7.5.16.

---

## 11.1.16 Backup Strategy

Portfolio backup shall include portfolio configurations, construction methodology configurations, risk model configurations, capital allocation records, risk history, attribution history, rebalancing history, and governance records. Backup shall follow Document 11 backup architecture per D-7.5.

---

## 11.1.17 Capacity Planning

Portfolio platform capacity shall be planned for strategy growth, instrument universe expansion, risk factor count growth, and rebalancing frequency growth. Capacity planning shall maintain risk computation performance.

---

## 11.1.18 Operational Monitoring

Portfolio platform operations shall be continuously monitored including portfolio construction service health, risk computation service health, data feed health, and integration health. Detailed monitoring is defined in Section 11.10.

---

## 11.1.19 Alert Management

Portfolio alerts shall include risk breach alerts, concentration warnings, drawdown alerts, VaR limit warnings, and integration failure alerts. Alerts shall be severity-classified and routed per enterprise alerting standards. Detailed alerting is defined in Section 11.10.

---

## 11.1.20 Logging Architecture

Portfolio logs shall capture construction decisions, sizing decisions, allocation decisions, risk computations, rebalancing actions, attribution computations, and governance decisions. Logs shall be immutable after recording per P-2.

---

## 11.1.21 Operational Runbooks

Portfolio platform operations shall maintain runbooks for risk breach response, capital reallocation procedures, rebalancing override procedures, methodology change procedures, and DR failover.

---

## 11.1.22 Testing Requirements

Portfolio platform testing shall include functional testing of all services, integration testing with Documents 11, 12, 13, and 14, determinism testing (identical configuration producing identical risk metrics), risk limit breach testing, and DR testing.

---

## 11.1.23 Deployment Architecture

Portfolio services shall be deployed with isolation from trading execution paths while maintaining low-latency communication for position sizing parameter updates and risk limit enforcement.

---

## 11.1.24 Configuration Management

Portfolio configuration shall be managed as governed assets per P-17 including construction methodology configurations, risk model configurations, risk limit configurations, and rebalancing configurations. Changes shall be governed with audit trail per P-5.

---

## 11.1.25 Risks

The Portfolio Management Platform Architecture shall continuously assess risks including:

- Methodology-Execution Disconnect — Portfolio construction methodology producing weights incompatible with trading execution
- Risk Model Failure — Risk models failing to capture actual portfolio risk
- Attribution Error — Incorrect performance attribution misleading stakeholders
- Governance Bypass — Risk limits circumvented by individual strategies
- State Inconsistency — Portfolio state diverging from trading positions

Every identified risk shall include risk classification, impact assessment, likelihood assessment, detection method, mitigation strategy, recovery procedure, and ownership.

---

## 11.1.26 Acceptance Criteria

The Portfolio Management Platform Architecture shall be considered complete when the platform demonstrates:

- End-to-end portfolio management from construction through attribution
- Portfolio construction separation from trading execution per P-9
- Risk-managed capital deployment with risk budget constraints
- Deterministic risk metrics and attribution per P-13
- Continuous risk monitoring with immediate escalation on breaches
- Portfolio-level risk authority over individual strategies
- Complete audit trail for all portfolio decisions per P-5
- Strategy-agnostic platform — no embedded portfolio theory assumptions per P-1

---

## 11.1.27 Cross References

This section shall be read together with Section 11.2 (Portfolio Construction), Section 11.3 (Position Sizing), Section 11.4 (Capital Allocation), Section 11.5 (Risk Management), Section 11.8 (Governance), Document 11 (per D-7.1, D-7.5, D-7.7, D-7.11, D-7.12, D-7.13), Document 12 (per Sections 8.2, 8.7), Document 13 (per Sections 9.13, 9.14, 9.15), Document 14 (per Sections 10.6, 10.10, 10.11, 10.12), and handbook/ARCHITECTURAL_INVARIANTS.md (per P-1, P-2, P-4, P-5, P-7, P-9, P-13, P-17).

---

# End of Section

---

# 11.2 Portfolio Construction Architecture

## 11.2.1 Purpose

The Portfolio Construction Architecture defines the governed framework for constructing portfolios from trading strategy signals and positions.

Portfolio construction shall aggregate individual strategy positions into coherent portfolios with defined objectives and constraints. It shall be the bridge between strategy-level trading decisions (Document 14) and portfolio-level capital deployment. Construction methodology shall be external to the platform per P-1 — the platform shall govern the methodology framework without prescribing specific optimization approaches.

Portfolio construction shall implement the Portfolio Construction Separation principle — construction methodology shall remain separate from execution infrastructure per P-9 and Port-1.

---

## 11.2.2 Scope

The Portfolio Construction Architecture applies to every portfolio within the Quant Hub platform.

Coverage includes:

- Portfolio Model
- Portfolio Construction Methodology Framework
- Constraint Modeling
- Multi-Strategy Aggregation
- Portfolio Optimization
- Portfolio Construction Governance

The following topics are intentionally excluded:

- Strategy-level trading decisions — Frozen per Document 14
- Position sizing from conviction — Owned by Section 11.3 (construction produces target weights; sizing converts to positions)
- Capital allocation across strategies — Owned by Section 11.4
- Specific optimization algorithms — External to platform per P-1

---

## 11.2.3 Portfolio Model

Every portfolio shall be defined through a canonical specification.

Portfolio specification shall include:

- Portfolio Identifier — Globally unique portfolio identifier
- Portfolio Name — Human-readable portfolio name
- Constituent Strategies — Strategy references (Document 14) included in the portfolio
- Construction Methodology — Portfolio construction methodology (external configuration per P-1): mean-variance optimization, risk parity, equal risk contribution, factor-based, Black-Litterman, or custom approaches
- Objective Function — Portfolio optimization objective: maximize Sharpe ratio, minimize risk, maximize return subject to risk constraint, target risk level
- Constraints — Portfolio constraints per Section 11.2.5
- Benchmark — Benchmark for performance comparison and tracking error measurement
- Rebalancing Schedule — Rebalancing frequency per Section 11.6
- Owner — Portfolio owner identity
- Status — Current lifecycle state

Portfolios shall be registered in the Document 11 Metadata Registry per D-7.7.2.

---

## 11.2.4 Portfolio Construction Methodology

Portfolio construction methodology shall be governed through the platform without the platform prescribing specific methodologies per P-1.

The methodology framework shall support:

- Mean-Variance Optimization — Expected returns, covariance matrix estimation, efficient frontier computation
- Risk Parity — Equal risk contribution from each constituent; risk budget allocation per constituent
- Factor-Based Construction — Portfolio weights derived from factor exposures; factor timing and factor allocation
- Black-Litterman — Prior equilibrium returns combined with investor views
- Custom Methodologies — Proprietary or research-derived construction approaches

The platform shall govern:

- Methodology Registration — Every construction methodology registered and versioned
- Input Requirements — Required inputs defined and validated (expected returns, covariance, constraints)
- Output Specification — Standardized output: target weights per strategy and per instrument
- Methodology Validation — Methodology validated before production use
- Methodology Versioning — Methodology changes create new versions per P-2

---

## 11.2.5 Constraint Modeling

Portfolio construction shall operate under governed constraints.

Constraint categories include:

- Risk Constraints — Portfolio volatility limit, VaR limit, CVaR limit, maximum drawdown limit, factor exposure limits
- Position Constraints — Minimum and maximum weight per instrument, per sector, per strategy; maximum active weight vs benchmark
- Turnover Constraints — Maximum one-way or two-way turnover per rebalancing period
- Liquidity Constraints — Maximum position as percentage of average daily volume; minimum liquidity thresholds
- Regulatory Constraints — Concentration limits, leverage limits, short-selling restrictions
- Custom Constraints — Portfolio-specific constraints defined through governed configuration

Constraints shall be defined, versioned, and governed. Constraint violations during construction shall produce alerts and may prevent construction completion.

---

## 11.2.6 Multi-Strategy Aggregation

Portfolio construction shall aggregate multiple strategy positions into a single portfolio.

Aggregation shall include:

- Strategy Weighting — Weight assigned to each constituent strategy within the portfolio
- Cross-Strategy Correlation — Correlation between strategy returns considered in portfolio risk estimation
- Diversification Assessment — Portfolio diversification across strategies, sectors, and factors
- Aggregation Governance — Aggregation methodology governed and versioned
- Aggregation Transparency — Contribution of each strategy to overall portfolio weights, risk, and expected return visible

Multi-strategy aggregation shall not embed assumptions about strategy interactions per P-1. Correlation estimates and diversification metrics shall be computed from governed data.

---

## 11.2.7 Portfolio Optimization

Portfolio construction may include governed optimization where the methodology requires it.

Optimization shall include:

- Optimization Scope — Optimization applied at strategy weight level, instrument weight level, or both, per methodology configuration
- Optimization Governance — Optimization algorithm, parameters, and convergence criteria governed

Optimization solver timeout and fallback:

| Scenario | Max Solver Time | Fallback |
|----------|----------------|----------|
| Standard rebalance (<= 500 positions) | 60 seconds | Previous weights held if timeout |
| Large rebalance (500-2000 positions) | 120 seconds | Previous weights held if timeout |
| Intraday tactical adjustment | 30 seconds | Current weights held, full rebalance deferred |
| Constraint Infeasibility | N/A (infeasibility detected) | Relax constraints in order: turnover → concentration → sector → position limits. Re-solve. If still infeasible: equal-risk-contribution fallback |
| Solver Instability (weight oscillation > 5%) | 90 seconds | Previous stable weights held + alert for manual review |

Solver non-convergence or infeasibility shall be recorded with: input parameters, constraints attempted, relaxation sequence applied, fallback applied. These records shall be immutable per P-5 and reviewed during post-rebalance governance.
- Optimization Recording — Optimization inputs, outputs, and diagnostics recorded for audit
- Optimization Validation — Optimized portfolio validated against constraints
- Robustness — Sensitivity analysis to input parameter variation

Optimization is optional — some construction methodologies may not require numerical optimization.

---

## 11.2.8 Benchmark Tracking

Portfolios may be constructed relative to benchmarks.

Benchmark tracking shall include:

- Benchmark Definition — Benchmark composition, weights, and rebalancing rules
- Tracking Error Management — Tracking error budget defined and governed
- Active Weights — Active weights (portfolio weight minus benchmark weight) computed and constrained
- Benchmark Comparison — Portfolio performance compared against benchmark for attribution per Section 11.7

Benchmark definitions shall be governed as reference data.

---

## 11.2.9 Portfolio Construction Governance

Portfolio construction shall be governed through portfolio governance per Section 11.8.

Governance shall include:

- Methodology Approval — Construction methodology approved before production use
- Methodology Change Governance — Methodology changes governed with impact assessment
- Constraint Governance — Constraints approved and reviewed periodically
- Construction Audit Trail — Every construction event shall produce immutable records per P-5
- Construction Review — Portfolio construction results reviewed for reasonableness

---

## 11.2.10 Portfolio Construction Artifacts

Every portfolio construction shall produce governed artifacts.

Artifacts shall include: constructed portfolio weights, constraint compliance report, risk decomposition, construction methodology snapshot, input data references (Document 11), and construction timestamp.

Artifacts shall be governed per Document 13 Section 9.10. Artifacts shall be immutable after publication per P-2.

---

## 11.2.11 Portfolio Construction Reproducibility

Portfolio construction shall be reproducible per P-13. Identical strategy positions, methodology configuration, constraints, and market data shall produce identical portfolio weights.

Reproducibility shall require all inputs recorded, methodology version recorded, and data versions recorded per Document 11.

---

## 11.2.12 Portfolio Construction Integration

Portfolio construction shall integrate with Position Sizing (Section 11.3 — portfolio weights feed into position sizing), Capital Allocation (Section 11.4 — allocation constrains construction), Risk Management (Section 11.5 — risk constraints from risk management), and Document 14 (strategy positions consumed, portfolio weights communicated for execution).

---

## 11.2.13 Portfolio Construction Performance and Scalability

Construction services shall satisfy performance objectives for optimization computation and constraint validation. Services shall scale with portfolio count and constituent strategy count. Scaling shall preserve determinism per P-13.

---

## 11.2.14 Risks

The Portfolio Construction Architecture shall continuously assess risks including:

- Optimization Instability — Small input changes producing large weight changes
- Constraint Infeasibility — Constraints producing no feasible solution
- Methodology Error — Construction methodology producing unintended or unreasonable portfolios
- Correlation Breakdown — Cross-strategy correlations estimated during normal markets failing in stress
- Benchmark Mismatch — Portfolio benchmark not reflecting actual investment universe

Every identified risk shall include risk classification, impact assessment, likelihood assessment, detection method, mitigation strategy, recovery procedure, and ownership.

---

## 11.2.15 Acceptance Criteria

The Portfolio Construction Architecture shall be considered complete when the platform demonstrates:

- Governed portfolio model with methodology, objectives, and constraints
- Methodology framework supporting diverse construction approaches without embedding assumptions per P-1
- Multi-strategy aggregation with diversification assessment
- Constraint-governed construction with constraint compliance verification
- Portfolio construction reproducibility per P-13
- Integration with position sizing, capital allocation, and risk management
- Complete audit trail for all construction decisions per P-5

---

## 11.2.16 Cross References

This section shall be read together with Section 11.1 (Portfolio Platform), Section 11.3 (Position Sizing), Section 11.4 (Capital Allocation), Section 11.5 (Risk Management), Document 11 (per D-7.7), Document 13 (per Section 9.10), Document 14 (per Sections 10.2, 10.6), and handbook/ARCHITECTURAL_INVARIANTS.md (per P-1, P-2, P-5, P-9, P-13, P-17).

---

# End of Section

---

# 11.3 Position Sizing Architecture

## 11.3.1 Purpose

The Position Sizing Architecture defines the methodological framework for converting strategy conviction (signal strength) into position sizes subject to risk constraints and capital allocation.

Position sizing shall bridge portfolio construction (Section 11.2) and trade execution (Document 14). Portfolio construction produces target weights or exposures; position sizing converts these into actionable position sizes that respect risk budgets, liquidity constraints, and capital allocation limits.

Position sizing methodology shall be external to platform per P-1. The platform shall govern the sizing framework without prescribing specific sizing approaches. Position sizing shall implement Risk-Managed Capital Deployment — position sizes shall be constrained by risk budgets, not just conviction.

---

## 11.3.2 Scope

The Position Sizing Architecture applies to all position sizing within the Quant Hub platform.

Coverage includes:

- Position Sizing Model
- Risk-Based Sizing
- Sizing Constraints
- Sizing Integration
- Sizing Governance

The following topics are intentionally excluded:

- Portfolio construction and weight derivation — Owned by Section 11.2
- Order generation from sized positions — Owned by Document 14 (Section 10.6.5)
- Specific sizing algorithms — External to platform per P-1
- Strategy-specific sizing logic — External per P-1

---

## 11.3.3 Position Sizing Model

Position sizing shall be defined through a governed specification.

Position sizing specification shall include:

- Sizing Methodology — Sizing methodology identifier: volatility targeting, Kelly criterion, risk parity, equal weight, or custom
- Input Parameters — Signal strength, volatility forecast, correlation matrix, risk budget allocation, capital allocation
- Output — Target position size per instrument
- Constraints — Position constraints per Section 11.3.5
- Methodology Version — Sizing methodology version per P-2

Position sizing parameters shall be communicated to Document 14 Order Generation (Section 10.6.5) for execution.

---

## 11.3.4 Risk-Based Sizing

Position sizing shall be governed by risk budgets.

Risk-based sizing shall include:

- Volatility Targeting — Position size inversely proportional to volatility. Higher volatility instruments receive smaller positions for equivalent risk contribution. Target volatility defined per strategy and portfolio.
- Risk Budget Allocation — Each strategy allocated a risk budget. Position sizes constrained so that aggregate strategy risk does not exceed budget.
- Maximum Position — Maximum position as percentage of portfolio value. Limits per instrument, sector, and strategy.

Position sizing default constraints:

| Constraint | Default Value | Scope | Override Authority |
|------------|-------------|-------|-------------------|
| Single Instrument Max | 5% of AUM | Per strategy | Risk Manager |
| Single Sector Max | 25% of AUM | Per strategy | Risk Manager |
| Single Strategy Max | 40% of total portfolio AUM | Portfolio | Governance Officer |
| Liquidity Constraint | Position <= 10% of 20-day ADV | Per instrument | Risk Manager |
| Minimum Liquidity Threshold | Instrument ADV >= $1,000,000 | Per instrument | Risk Manager (research exemption possible) |
| Position Build/Exit Horizon | Position exit in <= 5 trading days at 20% ADV participation | Per position | Risk Manager |
| Concentration (HHI) | Portfolio HHI <= 0.10 (equivalent to 10 equal-weighted positions) | Portfolio | Governance Officer |
| Max Leverage | 2x AUM for strategies with leverage authorization | Per strategy | CRO |

These defaults represent platform safety bounds — strategies may configure tighter limits but shall not exceed these maximums per P-1 and Port-2. Limits shall be reviewed quarterly and adjusted based on market conditions and strategy performance.
- Correlation-Aware Sizing — Position sizes adjusted for cross-instrument correlations to control portfolio-level risk.

Risk-based sizing shall implement the Risk-Managed Capital Deployment principle — conviction shall not override risk constraints.

---

## 11.3.5 Sizing Constraints

Position sizing shall operate under governed constraints.

Constraint categories include:

- Position Limits — Maximum position per instrument (absolute value and percentage of portfolio), maximum position per sector, maximum position per strategy
- Liquidity Constraints — Maximum position as percentage of average daily volume, minimum liquidity threshold, position build/exit time horizon consideration
- Concentration Limits — Maximum concentration in single instrument, sector, factor, or country
- Leverage Limits — Maximum gross leverage, maximum net leverage
- Risk Contribution Limits — Maximum risk contribution from single position or strategy
- Drawdown-Based Adjustment — Position sizes may be reduced as drawdown increases

Constraints shall be defined, versioned, and governed.

---

## 11.3.6 Kelly-Based Sizing

The platform shall support Kelly criterion and fractional Kelly sizing where methodology specifies.

Kelly-based sizing shall include:

- Kelly Fraction Computation — Optimal fraction based on win rate and win/loss ratio
- Fractional Kelly — Conservative sizing using fraction of full Kelly
- Kelly Constraints — Kelly sizing constrained by risk limits, liquidity, and diversification
- Kelly Governance — Kelly parameters governed and reviewed

Kelly methodology shall be external configuration. The platform shall not assume Kelly as the default sizing approach.

---

## 11.3.7 Position Sizing Integration

Position sizing shall integrate with Portfolio Construction (Section 11.2 — construction outputs feed sizing inputs), Capital Allocation (Section 11.4 — allocation constrains sizing), Risk Management (Section 11.5 — risk limits constrain sizing), and Document 14 Order Generation (Section 10.6.5 — sizing parameters consumed for order generation).

---

## 11.3.8 Position Sizing Governance

Position sizing shall be governed through portfolio governance per Section 11.8.

Governance shall include: methodology approval, parameter governance, constraint governance, sizing parameter change governance, and audit trail per P-5 for all sizing parameter changes.

---

## 11.3.9 Position Sizing Artifacts

Position sizing shall produce governed artifacts including sizing parameters per strategy, risk budget utilization, constraint compliance report, and sizing methodology snapshot. Artifacts shall be immutable after publication per P-2.

---

## 11.3.10 Position Sizing Reproducibility

Position sizing shall be deterministic per P-13. Identical inputs, methodology, and constraints shall produce identical position sizes. Reproducibility shall require all inputs and methodology version recorded.

---

## 11.3.11 Position Sizing Performance

Position sizing shall satisfy performance objectives for sizing computation latency. Sizing shall operate within bounded time to avoid delaying order generation per Document 14 latency SLOs (T-7).

---

## 11.3.12 Risks

The Position Sizing Architecture shall continuously assess risks including:

- Over-Concentration — Position sizes producing excessive concentration in single instrument or sector
- Liquidity Overestimation — Position sizes exceeding market liquidity
- Risk Budget Exhaustion — Aggregate positions exhausting risk budget before all signals allocated
- Volatility Regime Shift — Sizing based on historical volatility inappropriate for current regime
- Methodology Drift — Actual sizing diverging from governed methodology

Every identified risk shall include risk classification, impact assessment, likelihood assessment, detection method, mitigation strategy, recovery procedure, and ownership.

---

## 11.3.13 Acceptance Criteria

The Position Sizing Architecture shall be considered complete when the platform demonstrates:

- Governed position sizing model with methodology, inputs, and constraints
- Risk-based sizing implementing risk-managed capital deployment
- Constraint enforcement preventing position limits, liquidity limits, and concentration
- Integration with portfolio construction and order generation
- Deterministic sizing per P-13
- Complete audit trail for sizing parameter changes per P-5
- No embedded sizing methodology assumptions per P-1

---

## 11.3.14 Cross References

This section shall be read together with Section 11.1 (Portfolio Platform), Section 11.2 (Portfolio Construction), Section 11.4 (Capital Allocation), Section 11.5 (Risk Management), Document 14 (per Section 10.6.5), and handbook/ARCHITECTURAL_INVARIANTS.md (per P-1, P-2, P-5, P-13, P-17).

---

# End of Section

---

# 11.4 Capital Allocation Architecture

## 11.4.1 Purpose

The Capital Allocation Architecture defines the framework for deploying capital across trading strategies.

Capital allocation shall govern how total portfolio capital is distributed among constituent strategies. Allocation shall balance risk-adjusted return expectations with risk budget constraints, portfolio diversification requirements, and drawdown management.

Capital allocation shall implement Risk-Managed Capital Deployment — capital shall only be deployed through governed risk frameworks. Allocation shall operate at the portfolio level with authority over individual strategies per Strategy Risk Separation.

Capital allocation methodology shall be external to platform per P-1. The platform shall govern the allocation framework without prescribing specific allocation strategies.

---

## 11.4.2 Scope

The Capital Allocation Architecture applies to all capital allocation within the Quant Hub portfolio platform.

Coverage includes:

- Capital Allocation Model
- Risk Budgeting
- Allocation Optimization
- Drawdown-Based Allocation Adjustment
- Allocation Governance

The following topics are intentionally excluded:

- Portfolio construction methodology — Owned by Section 11.2
- Position sizing — Owned by Section 11.3
- Specific allocation strategies — External per P-1
- Trading execution — Owned by Document 14

---

## 11.4.3 Capital Allocation Model

Capital allocation shall be defined through a governed specification.

Capital allocation specification shall include:

- Total Capital — Total portfolio capital available for deployment
- Allocation Methodology — Methodology identifier: equal weight, risk parity, mean-variance, Kelly-based, or custom
- Allocation Per Strategy — Capital amount allocated to each constituent strategy
- Risk Budget Per Strategy — Risk budget allocated to each strategy constraining position sizing
- Reallocation Triggers — Conditions triggering capital reallocation: performance threshold, risk budget exhaustion, drawdown threshold, time-based
- Allocation Constraints — Minimum and maximum allocation per strategy, maximum allocation change per reallocation
- Allocation Status — Current allocation state

Allocation records shall be immutable after publication per P-2.

---

## 11.4.4 Risk Budgeting

Risk budgeting shall be the primary constraint on capital allocation.

Risk budgeting shall include:

- Risk Budget Definition — Total portfolio risk budget decomposed into strategy-level risk budgets
- Risk Budget Allocation — Risk budget per strategy may reflect strategy Sharpe ratio, diversification benefit, or other methodology (external per P-1)
- Risk Budget Utilization — Risk budget utilization monitored per strategy. Under-utilization may permit increased allocation; over-utilization constrains allocation.
- Risk Budget Adjustment — Risk budgets adjusted based on strategy performance, regime changes, or governance decisions
- Risk Budget Governance — Risk budget changes governed with approval per Section 11.8

Risk budgets shall constrain both capital allocation and position sizing per Section 11.3.

---

## 11.4.5 Allocation Optimization

Capital allocation may involve governed optimization where methodology requires.

Optimization shall include: objective function (maximize risk-adjusted return, maximize diversification), constraints (risk budget, minimum/maximum allocation, turnover), optimization recording for audit, and sensitivity analysis for robustness. Optimization methodology shall be external per P-1.

---

## 11.4.6 Allocation Rebalancing

Capital allocation may be rebalanced periodically or on triggers.

Rebalancing shall include:

- Trigger-Based Rebalancing — Allocation rebalanced when strategy performance, risk, or correlation deviates from expectations beyond defined thresholds
- Calendar-Based Rebalancing — Allocation rebalanced on defined schedule
- Rebalancing Execution — New allocations communicated to Document 14 for execution. Capital flows managed to minimize transaction costs.
- Rebalancing Governance — Rebalancing decisions governed with approval for material allocation changes

---

## 11.4.7 Drawdown-Based Allocation Adjustment

Capital allocation may be adjusted based on strategy drawdown.

Adjustment shall include:

- Drawdown Thresholds — Defined drawdown levels triggering allocation review or reduction
- Allocation Reduction — Allocation may be reduced or suspended for strategies exceeding drawdown thresholds
- Recovery Conditions — Conditions for restoring allocation after drawdown recovery
- Adjustment Governance — Drawdown-based adjustments governed with documented rationale

---

## 11.4.8 Allocation Governance

Capital allocation shall be governed through portfolio governance per Section 11.8.

Governance shall include: allocation approval, allocation change governance, rebalancing governance, risk budget governance, and complete audit trail per P-5 for all allocation decisions.

---

## 11.4.9 Allocation Artifacts

Capital allocation shall produce governed artifacts including current allocation state, allocation history, risk budget allocation, rebalancing history, and allocation rationale.

Artifacts shall be immutable after publication per P-2.

---

## 11.4.10 Allocation Integration

Capital allocation shall integrate with Portfolio Construction (Section 11.2 — allocation constrains construction), Position Sizing (Section 11.3 — allocation feeds risk budgets to sizing), Risk Management (Section 11.5 — risk metrics inform allocation), and Document 14 Live Trading and Governance (Sections 10.6, 10.10 — allocation communicated to trading).

---

## 11.4.11 Risks

The Capital Allocation Architecture shall continuously assess risks including:

- Overallocation — Capital allocated exceeding available capital or risk budget
- Concentration — Excessive capital concentration in single strategy or correlated strategies
- Drawdown Cascade — Unchecked strategy drawdown consuming portfolio capital
- Allocation Drift — Actual allocation diverging from target without rebalancing
- Risk Budget Inconsistency — Risk budgets inconsistent with capital allocation

Every identified risk shall include risk classification, impact assessment, likelihood assessment, detection method, mitigation strategy, recovery procedure, and ownership.

---

## 11.4.12 Acceptance Criteria

The Capital Allocation Architecture shall be considered complete when the platform demonstrates:

- Governed capital allocation model with methodology and constraints
- Risk budgeting as primary constraint on capital deployment
- Allocation rebalancing on triggers and schedule
- Drawdown-based allocation adjustment
- Portfolio-level authority over strategy capital per Strategy Risk Separation
- Complete audit trail for all allocation decisions per P-5
- No embedded allocation strategy assumptions per P-1

---

## 11.4.13 Cross References

This section shall be read together with Section 11.1 (Portfolio Platform), Section 11.2 (Portfolio Construction), Section 11.3 (Position Sizing), Section 11.5 (Risk Management), Section 11.8 (Governance), Document 14 (per Sections 10.6, 10.10), and handbook/ARCHITECTURAL_INVARIANTS.md (per P-1, P-2, P-5, P-17).

---

# End of Section

---

# 11.5 Risk Management Architecture

## 11.5.1 Purpose

The Risk Management Architecture defines the enterprise risk management framework for measuring, monitoring, and controlling portfolio risk.

Risk management shall implement Port-4 (Continuous Risk Monitoring) — risk shall be continuously measured and monitored, not periodically assessed. Risk management shall operate at the portfolio level with authority to constrain individual strategies per Port-5 (Strategy Risk Separation).

Risk management shall consume positions and P&L from Document 14 Trading Infrastructure, market data from Document 11 Data Engineering, model predictions from Document 12 Model Serving, and promoted research from Document 13 Research Engineering. It shall produce risk metrics, risk limit assessments, stress test results, and risk alerts.

Risk models and methodologies shall be external configurations per P-1. The platform shall govern the risk management framework without prescribing specific risk models.

---

## 11.5.2 Scope

The Risk Management Architecture applies to all risk management within the Quant Hub portfolio platform.

Coverage includes:

- Risk Measurement
- Risk Modeling
- Factor Risk Decomposition
- Stress Testing
- Scenario Analysis
- Risk Reporting
- Risk Governance

The following topics are intentionally excluded:

- Strategy-level risk controls — Owned by Document 14 (Section 10.10.6)
- Trading circuit breakers — Owned by Document 14 (Section 10.6.7)
- Position-level limit enforcement — Owned by Document 14 (Section 10.6.6)
- Specific risk models — External configurations per P-1

---

## 11.5.3 Risk Measurement

The platform shall compute standardized risk metrics continuously.

Risk metrics shall include:

- Value at Risk (VaR) — Maximum expected loss over a defined time horizon at a defined confidence level. Parametric VaR (variance-covariance), historical simulation VaR, and Monte Carlo VaR supported per methodology configuration.
- Conditional VaR (CVaR / Expected Shortfall) — Expected loss conditional on exceeding VaR threshold. CVaR complements VaR by capturing tail risk magnitude.
- Volatility — Annualized portfolio volatility. Realized volatility and forecast volatility. Volatility contribution by position and strategy.
- Maximum Drawdown — Maximum peak-to-trough decline. Current drawdown, historical maximum drawdown, drawdown duration. Drawdown by strategy and portfolio.
- Beta Exposure — Portfolio beta to defined benchmarks. Market beta, sector beta, factor beta.
- Factor Exposures — Exposure to defined risk factors: market, size, value, momentum, quality, volatility, sector, and custom factors.
- Concentration Metrics — Concentration by instrument, sector, factor, and strategy. Herfindahl-Hirschman Index and other concentration measures.
- Leverage — Gross leverage, net leverage. Leverage by strategy.
- Correlation — Intra-portfolio correlation, correlation to benchmarks, cross-strategy correlation.
- Liquidity Metrics — Portfolio liquidity profile: days to liquidate, percentage of ADV, liquidity concentration.

Risk metrics shall be computed on every material position change and on defined intervals. Risk computation shall be deterministic per Port-3 — identical positions, market data, and risk model parameters shall produce identical metrics.

---

## 11.5.4 Risk Models

Risk measurement shall be supported by governed risk models. Risk model methodology shall be external configuration per P-1.

The platform shall support:

- Covariance-Based Models — Risk estimated from historical return covariance matrix. Estimation methodology, lookback period, and decay factor configurable.
- Factor-Based Models — Risk decomposed into systematic factor risk and idiosyncratic risk. Factor definitions, factor covariance, and factor exposures configurable.
- Historical Simulation — Non-parametric VaR from historical return distribution. Historical period configurable.
- Monte Carlo Simulation — Risk estimated from simulated return paths. Simulation parameters, distributions, and path count configurable.
- Custom Models — Proprietary risk models integrated through governed interfaces.

Risk model governance shall include:

- Model Registration — Every risk model registered with methodology documentation
- Model Validation — Risk models validated before production use. Backtesting: VaR exceedance analysis comparing predicted vs actual losses. Validation results recorded as governed evidence.
- Model Versioning — Risk model changes create new versions per P-2
- Model Monitoring — Risk model performance continuously monitored. Model degradation triggers review.

---

## 11.5.5 Factor Risk Decomposition

Portfolio risk shall be decomposed into factor contributions.

Factor decomposition shall include:

- Factor Definitions — Risk factors defined and governed: market beta, size, value, momentum, quality, low volatility, sector, country, currency, and custom factors
- Factor Exposure Computation — Portfolio exposure to each factor computed from position data and factor loadings
- Factor Covariance — Factor covariance matrix estimated and governed
- Systematic vs Idiosyncratic — Portfolio risk decomposed into systematic (factor-driven) and idiosyncratic (strategy-specific) components
- Marginal Contribution to Risk — Each factor's marginal contribution to total portfolio risk
- Factor Exposure Limits — Factor exposure limits defined and monitored

Factor decomposition shall enable risk understanding beyond aggregate risk measures.

---

## 11.5.6 Stress Testing

Portfolio risk shall be assessed through governed stress testing.

Stress testing shall include:

- Historical Scenarios — Portfolio performance under historical stress events: 2008 financial crisis, 2020 COVID crash, 2010 flash crash, 2015 Swiss franc event, and other defined scenarios
- Hypothetical Scenarios — Portfolio performance under defined hypothetical stress scenarios: equity market crash (-20%, -30%, -50%), interest rate shocks (+100bp, +200bp, +300bp), volatility spikes, credit spread widening, currency shocks, commodity price shocks
- Reverse Stress Testing — Identifying scenarios that would cause portfolio failure (exceeding maximum acceptable loss). Understanding which scenarios break the portfolio.
- Sensitivity Analysis — Portfolio sensitivity to individual risk factor changes: delta, gamma, vega for options; duration and convexity for fixed income; beta sensitivity to market moves
- Correlation Stress — Impact of correlation breakdown: correlations moving to 1 during stress (diversification failure)
- Multi-Factor Stress — Combined stress scenarios: equity crash + volatility spike + correlation breakdown

Stress test results shall be recorded as governed evidence. Stress test scenarios shall be governed and reviewed periodically.

---

## 11.5.7 Risk Limit Framework

Risk management shall operate within governed risk limits extending Document 14 Section 10.10.6.

Portfolio-level risk limits shall include:

- VaR Limit — Maximum portfolio VaR at defined confidence level and horizon
- CVaR Limit — Maximum portfolio CVaR
- Volatility Limit — Maximum portfolio volatility target
- Drawdown Limit — Maximum acceptable drawdown before mandatory risk reduction
- Factor Exposure Limits — Maximum exposure per factor
- Concentration Limits — Maximum concentration per instrument, sector, country
- Leverage Limits — Maximum gross and net leverage
- Liquidity Limits — Minimum portfolio liquidity requirements
- Stress Loss Limits — Maximum loss under defined stress scenarios

Risk limits shall be governed: limits set based on risk assessment, approved by risk governance authority, monitored continuously per Port-4, and breaches escalated immediately.

Portfolio-level limits shall supersede strategy-level limits per Port-5 — if a strategy-level limit permits an action that would breach a portfolio-level limit, the portfolio-level limit shall prevail.

---

## 11.5.8 Risk Monitoring

Risk shall be continuously monitored per Port-4.

Monitoring shall include:

- Real-Time Risk Metrics — VaR, CVaR, volatility, exposures, concentrations updated on every material position change
- Limit Utilization Monitoring — Current risk metrics compared against limits. Warning at defined thresholds (e.g., 80% of limit). Breach at 100%.
- Risk Trend Monitoring — Risk metric trends over time. Risk acceleration detection.
- Correlation Monitoring — Intra-portfolio and cross-strategy correlation trends. Correlation breakdown detection.
- Risk Regime Detection — Detection of changing risk regimes: low volatility to high volatility transitions
- Risk Alerts — Immediate alerts on limit breaches, limit warnings, unusual risk changes, and risk regime shifts

Risk monitoring dashboards shall provide real-time visibility per Section 11.10.

---

## 11.5.9 Risk Reporting

The platform shall generate risk reports.

Reports shall include:

- Daily Risk Report — Current risk metrics, limit utilization, risk changes from previous day
- Risk Attribution Report — Risk decomposed by strategy, factor, and position
- Stress Test Report — Stress test results summary with scenario analysis
- VaR Backtesting Report — VaR exceedance analysis comparing predicted vs actual losses
- Risk Trend Report — Risk metric trends over defined periods
- Exception Report — Risk limit breaches and near-breaches with context

Reports shall be governed artifacts. Reports shall be generated on schedule and on demand.

---

## 11.5.10 Risk Governance

Risk management shall be governed through portfolio governance per Section 11.8.

Governance shall include:

- Risk Model Governance — Model registration, validation, versioning, and monitoring
- Risk Limit Governance — Limit setting, modification, and breach escalation
- Stress Test Governance — Scenario definition, review, and update
- Risk Methodology Governance — Risk measurement methodology governance
- Risk Reporting Governance — Report content, frequency, and distribution
- Risk Audit Trail — All risk governance actions recorded per P-5

Risk governance shall maintain separation from trading governance — risk management shall have independent authority per Port-5.

---

## 11.5.11 Risk Integration

Risk management shall integrate with Capital Allocation (Section 11.4 — risk metrics inform allocation), Position Sizing (Section 11.3 — risk budgets constrain sizing), Document 14 Trading Circuit Breakers (Section 10.6.7 — portfolio risk breaches may trigger trading halt), and Document 14 Trading Governance (Section 10.10 — risk limits communicated to trading).

---

## 11.5.12 Risk Model Validation

Risk models shall be validated before production use and periodically thereafter.

Validation shall include:

- VaR Backtesting — Comparing VaR predictions against actual P&L. Kupiec test, Christoffersen test for VaR accuracy. Recording exceedance frequency and magnitude.
- Stress Test Validation — Comparing stress test predictions against actual stress event outcomes where available
- Model Stability — Parameter stability over time. Sensitivity to estimation methodology changes.
- Model Comparison — Comparing multiple risk models for consistency and robustness
- Validation Governance — Validation results reviewed. Models failing validation shall not be used for limit enforcement.

Validation evidence shall be governed and immutable after publication per P-2.

---

## 11.5.13 Risk Artifacts

Risk management shall produce governed artifacts including risk metrics history, risk limit history, stress test results, VaR backtesting results, risk model configurations, and risk reports.

Artifacts shall be governed per Document 13 Section 9.10. Artifacts shall be immutable after publication per P-2.

---

## 11.5.14 Risk Performance and Scalability

Risk computation shall satisfy performance objectives: VaR computation latency, stress test completion time, factor decomposition latency, and concurrent strategy and portfolio support. Services shall scale with position count, factor count, and scenario count. Scaling shall preserve risk computation determinism per Port-3.

---

## 11.5.15 Risk High Availability and Disaster Recovery

Risk monitoring shall be highly available. Risk computation services shall have redundancy. DR shall preserve risk history, stress test results, risk limit history, and risk model configurations.

---

## 11.5.16 Risks

The Risk Management Architecture shall continuously assess risks including:

- Model Risk — Risk models failing to capture actual portfolio risk
- VaR Exceedance Clustering — VaR breaches occurring more frequently than confidence level predicts
- Correlation Breakdown — Diversification assumptions failing during stress
- Regime Blindness — Risk models based on low-volatility regimes failing during high-volatility transitions
- Limit Gaming — Strategies structuring positions to appear within limits while maintaining hidden risk
- Stress Scenario Obsolescence — Stress scenarios not reflecting current market conditions

Every identified risk shall include risk classification, impact assessment, likelihood assessment, detection method, mitigation strategy, recovery procedure, and ownership.

---

## 11.5.17 Acceptance Criteria

The Risk Management Architecture shall be considered complete when the platform demonstrates:

- Continuous risk measurement covering VaR, CVaR, volatility, drawdown, exposures, and concentrations per Port-4
- Governed risk model framework supporting multiple model types without model-specific assumptions per P-1
- Factor risk decomposition enabling systematic vs idiosyncratic risk understanding
- Governed stress testing including historical, hypothetical, and reverse stress testing
- Portfolio-level risk limits with breach escalation superseding strategy limits per Port-5
- Risk model validation with VaR backtesting and model performance monitoring
- Deterministic risk metrics per Port-3
- Complete risk audit trail per P-5

---

## 11.5.18 Cross References

This section shall be read together with Section 11.1 (Portfolio Platform), Section 11.4 (Capital Allocation), Section 11.3 (Position Sizing), Section 11.8 (Governance), Document 11 (per D-7.1, D-7.7, D-7.12), Document 12 (per Sections 8.2, 8.7), Document 14 (per Sections 10.6.7, 10.10.6), and handbook/ARCHITECTURAL_INVARIANTS.md (per P-1, P-2, P-5, P-7, P-13, P-17, Port-3, Port-4, Port-5).

---

# End of Section

---

# 11.6 Portfolio Rebalancing Architecture

## 11.6.1 Purpose

The Portfolio Rebalancing Architecture defines the framework for systematic portfolio rebalancing to maintain target allocations and risk profiles.

Rebalancing shall ensure that actual portfolio weights remain aligned with target weights from portfolio construction (Section 11.2). Without rebalancing, portfolios drift — winning positions grow overweight, losing positions shrink underweight, and risk profiles diverge from targets.

Rebalancing shall balance the benefits of maintaining target allocations against the costs of trading. Cost-aware rebalancing shall minimize unnecessary turnover. Tax-aware rebalancing shall consider tax implications.

Rebalancing methodology shall be external to platform per P-1. The platform shall govern the rebalancing framework.

---

## 11.6.2 Scope

The Portfolio Rebalancing Architecture applies to all portfolio rebalancing within the Quant Hub platform.

Coverage includes:

- Rebalancing Triggers
- Rebalancing Methodology
- Cost-Aware Rebalancing
- Rebalancing Execution
- Rebalancing Governance

The following topics are intentionally excluded:

- Portfolio construction — Owned by Section 11.2
- Trade execution — Owned by Document 14
- Specific rebalancing algorithms — External per P-1

---

## 11.6.3 Rebalancing Triggers

Rebalancing shall be triggered by defined conditions.

Trigger types include:

- Calendar-Based — Rebalancing at defined intervals: daily, weekly, monthly, quarterly. Schedule governed per portfolio configuration.
- Threshold-Based — Rebalancing when allocation drift exceeds defined tolerance. Weight drift (actual weight minus target weight) exceeding threshold. Risk drift (actual risk contribution minus target risk contribution) exceeding threshold.
- Risk-Based — Rebalancing when portfolio risk exceeds target by defined margin. VaR or volatility exceeding target triggers rebalancing toward lower risk allocation.
- Event-Based — Rebalancing on defined events: significant cash flow (deposit or withdrawal), corporate action affecting major position, benchmark rebalancing, risk limit modification
- Conditional — Rebalancing only when expected benefit (risk reduction, return improvement) exceeds expected cost (transaction costs, taxes)

Multiple triggers may be combined. Trigger parameters shall be governed.

---

## 11.6.4 Rebalancing Methodology

Rebalancing methodology shall be governed external configuration per P-1.

Methodology types include:

- To Target Weights — Rebalance entirely to target weights. Simple but may generate high turnover.
- To Tolerance Bands — Rebalance only weights outside defined tolerance bands. Weights within bands left unchanged. Reduces unnecessary turnover.
- To Target Risk — Rebalance to target risk contributions rather than target weights. More sophisticated — adjusts for changes in volatility and correlation.
- Partial Rebalancing — Rebalance a fraction toward targets. Fraction configurable. Gradual approach reducing market impact.
- Optimization-Based — Rebalance through optimization minimizing turnover subject to tracking error constraint. May incorporate transaction cost models.

Methodology selection and parameters shall be governed per portfolio configuration.

---

## 11.6.5 Cost-Aware Rebalancing

Rebalancing shall consider transaction costs.

Cost-aware rebalancing shall include:

- Transaction Cost Estimation — Estimated commission, spread, and market impact of rebalancing trades
- Cost-Benefit Analysis — Expected risk/return benefit of rebalancing compared against estimated transaction costs. Rebalancing deferred if costs exceed benefits.
- Turnover Minimization — Methodology and tolerance bands configured to minimize unnecessary turnover
- Liquidity Consideration — Rebalancing sized to respect market liquidity. Large rebalances may be executed over multiple periods.
- Cost Tracking — Actual rebalancing costs tracked and compared against estimates for methodology improvement

Cost-aware rebalancing shall not prevent necessary risk-reducing rebalances.

---

## 11.6.6 Tax-Aware Rebalancing

Where applicable, rebalancing shall consider tax implications.

Tax-aware rebalancing shall include:

- Tax Lot Selection — Specific lot identification to minimize tax impact: highest cost basis lots sold first, short-term gains deferred where possible, loss harvesting integrated with rebalancing
- Holding Period Consideration — Preference for selling positions held beyond short-term threshold
- Tax Cost Estimation — Estimated tax cost of rebalancing trades incorporated into cost-benefit analysis
- Wash Sale Avoidance — Rebalancing respecting wash sale rules

Tax-aware rebalancing shall be optional — enabled per portfolio configuration.

---

## 11.6.7 Rebalancing Execution

Rebalancing shall produce trades executed through Document 14 Trading Infrastructure.

Execution shall include:

- Trade Generation — Rebalancing differences translated into specific trades: instruments, quantities, sides
- Trade Validation — Rebalancing trades validated against constraints and limits
- Order Submission — Trades submitted through Document 14 Order Management (Section 10.7)
- Execution Monitoring — Rebalancing execution monitored for completion and execution quality
- Partial Execution Handling — Procedures for incompletely executed rebalances

Rebalancing trades shall be clearly identified as rebalancing trades in order metadata.

---

## 11.6.8 Cash Flow Handling

Portfolio cash flows shall be integrated with rebalancing.

Cash flow handling shall include:

- Contribution Handling — New capital deployed according to target allocation. May trigger rebalancing if contribution is significant.
- Withdrawal Handling — Capital withdrawn proportionally from positions or according to defined methodology
- Dividend Reinvestment — Dividends reinvested per portfolio configuration. May accumulate as cash until rebalancing threshold.
- Cash Buffer — Portfolio may maintain cash buffer to reduce rebalancing frequency. Buffer size governed.

Cash flow events shall be recorded as portfolio events per Section 11.1.8.

---

## 11.6.9 Rebalancing Governance

Rebalancing shall be governed through portfolio governance per Section 11.8.

Governance shall include:

- Methodology Governance — Rebalancing methodology approved and versioned
- Trigger Governance — Trigger parameters approved and reviewed
- Execution Governance — Rebalancing trades subject to appropriate governance. Material rebalancing may require approval.
- Audit Trail — Every rebalancing decision and trade shall produce immutable records per P-5

---

## 11.6.10 Rebalancing Artifacts

Every rebalancing event shall produce governed artifacts including drift report (current vs target), rebalancing trade list, cost estimates and actual costs, execution quality report, and rebalancing rationale.

Artifacts shall be governed per Document 13 Section 9.10.

---

## 11.6.11 Rebalancing Integration

Rebalancing shall integrate with Portfolio Construction (Section 11.2 — target weights), Risk Management (Section 11.5 — risk triggers), Capital Allocation (Section 11.4 — allocation changes trigger rebalancing), and Document 14 Order Management (Section 10.7 — rebalancing trade execution).

---

## 11.6.12 Rebalancing Performance and Scalability

Rebalancing computation shall satisfy performance objectives for drift computation and trade generation. Services shall scale with portfolio count and position count. Computation shall be deterministic per Port-3.

---

## 11.6.13 Risks

The Portfolio Rebalancing Architecture shall continuously assess risks including:

- Excessive Turnover — Rebalancing generating excessive trading costs eroding portfolio returns
- Drift Accumulation — Infrequent rebalancing allowing significant risk drift from targets
- Market Impact — Large rebalancing trades moving market prices
- Tax Inefficiency — Rebalancing generating unnecessary tax liabilities
- Partial Execution — Rebalancing trades only partially executed creating residual drift
- Trigger Proliferation — Complex trigger combinations causing unexpected rebalancing behavior

Every identified risk shall include risk classification, impact assessment, likelihood assessment, detection method, mitigation strategy, recovery procedure, and ownership.

---

## 11.6.14 Acceptance Criteria

The Portfolio Rebalancing Architecture shall be considered complete when the platform demonstrates:

- Governed rebalancing triggers including calendar, threshold, risk, and event-based
- Multiple rebalancing methodologies with cost-aware optimization
- Cost-benefit analysis preventing unnecessary rebalancing
- Tax-aware rebalancing with lot selection and holding period optimization
- Integration with Document 14 for rebalancing trade execution
- Complete rebalancing audit trail per P-5
- No embedded rebalancing methodology assumptions per P-1

---

## 11.6.15 Cross References

This section shall be read together with Section 11.1 (Portfolio Platform), Section 11.2 (Portfolio Construction), Section 11.5 (Risk Management), Section 11.8 (Governance), Document 13 (per Section 9.10), Document 14 (per Section 10.7), and handbook/ARCHITECTURAL_INVARIANTS.md (per P-1, P-2, P-5, P-13, Port-3).

---

# End of Section

---

# 11.7 Portfolio Performance Attribution Architecture

## 11.7.1 Purpose

The Portfolio Performance Attribution Architecture defines the framework for attributing portfolio returns to strategies, factors, and decisions.

Performance attribution shall decompose portfolio returns into their sources — enabling understanding of what drives performance, what detracts from performance, and whether returns come from skill (alpha) or exposure (beta). Attribution shall inform capital allocation decisions, strategy assessment, and governance oversight.

Attribution shall be deterministic per Port-3 — identical positions, market data, and methodology shall produce identical attribution results.

Attribution methodology shall be external to platform per P-1.

---

## 11.7.2 Scope

The Portfolio Performance Attribution Architecture applies to all performance attribution within the Quant Hub platform.

Coverage includes:

- Return Attribution
- Factor Attribution
- Strategy Attribution
- Decision Attribution
- Attribution Reporting

The following topics are intentionally excluded:

- P&L computation — Owned by Document 14 (Section 10.9.5)
- Trade-level P&L attribution — Owned by Document 14
- Specific attribution methodologies — External per P-1

---

## 11.7.3 Return Attribution Models

The platform shall support multiple attribution models governed as external configurations.

Attribution models include:

- Brinson Attribution — Decomposes return into allocation effect (overweight/underweight vs benchmark), selection effect (security selection within sector), and interaction effect. Supports arithmetic and geometric multi-period compounding.
- Factor-Based Attribution — Decomposes return into factor contributions: market return, factor tilts (size, value, momentum, quality, low volatility, sector, country), and pure alpha (residual unexplained by factors).
- Strategy Attribution — Decomposes return into per-strategy contributions. Each strategy's P&L aggregated to portfolio contribution.
- Decision Attribution — Decomposes return into specific decisions: capital allocation decisions, construction methodology decisions, rebalancing decisions. Higher-level attribution enabling governance assessment of decision quality.
- Transaction Cost Attribution — Separately attributes transaction costs: commissions, spreads, market impact, slippage

Attribution model selection and configuration shall be governed per portfolio.

---

## 11.7.4 Brinson Attribution

The platform shall support Brinson attribution where specified.

Brinson attribution shall include:

- Allocation Effect — Return contribution from overweighting/underweighting sectors relative to benchmark
- Selection Effect — Return contribution from security selection within sectors
- Interaction Effect — Cross-product of allocation and selection effects
- Arithmetic Attribution — Single-period return decomposition
- Geometric Attribution — Multi-period compounding preserving additive property
- Benchmark Comparison — Attribution relative to defined benchmark

---

## 11.7.5 Factor Attribution

The platform shall support factor-based return decomposition.

Factor attribution shall include:

- Market Return — Return attributable to broad market exposure (beta)
- Style Factor Returns — Return from exposure to size, value, momentum, quality, low volatility factors
- Sector Returns — Return from sector allocation relative to market
- Country Returns — Return from country allocation (for multi-country portfolios)
- Currency Returns — Return from currency exposure
- Residual / Alpha — Return unexplained by systematic factors. This is the pure strategy alpha — the return source that attribution seeks to identify and validate.
- Factor Timing — Return from changes in factor exposures over time

Factor definitions and factor returns shall be governed. Factor attribution shall integrate with factor risk decomposition per Section 11.5.5.

---

## 11.7.6 Strategy Attribution

Portfolio returns shall be attributed to constituent strategies.

Strategy attribution shall include:

- Per-Strategy Contribution — Each strategy's P&L contribution to portfolio return
- Strategy Weight Effect — Return contribution from strategy weighting decisions
- Strategy Interaction — Cross-strategy effects from correlation and diversification
- Strategy Benchmarking — Each strategy's return compared against its individual benchmark

Strategy attribution shall inform capital allocation decisions — strategies delivering alpha receive increased allocation; strategies underperforming receive review.

---

## 11.7.7 Decision Attribution

Returns shall be attributed to specific governance decisions.

Decision attribution shall include:

- Allocation Decisions — Return impact of capital allocation changes between strategies
- Construction Decisions — Return impact of portfolio construction methodology changes
- Rebalancing Decisions — Return impact of rebalancing actions
- Risk Decisions — Return impact of risk limit changes
- Benchmark-Relative — All decisions assessed relative to what a passive benchmark allocation would have returned

Decision attribution shall support governance oversight — enabling assessment of whether governance decisions add or subtract value.

---

## 11.7.8 Attribution Governance

Attribution shall be governed through portfolio governance per Section 11.8.

Governance shall include:

- Model Governance — Attribution model selection, configuration, and versioning
- Methodology Governance — Attribution methodology documented and governed
- Factor Governance — Factor definitions and factor returns governed
- Attribution Audit — Attribution results shall produce immutable records per P-5
- Attribution Review — Attribution results reviewed periodically for insight and decision support

---

## 11.7.9 Attribution Artifacts

Attribution shall produce governed artifacts including attribution reports, factor contribution breakdowns, strategy contribution summaries, and attribution methodology snapshots.

Artifacts shall be governed per Document 13 Section 9.10. Artifacts shall be immutable after publication per P-2.

---

## 11.7.10 Attribution Reproducibility

Attribution results shall be deterministic per Port-3. Identical positions, market data, factor data, and attribution methodology shall produce identical attribution results.

Reproducibility shall require all inputs recorded, methodology version recorded, and data versions recorded.

---

## 11.7.11 Attribution Integration

Attribution shall integrate with Document 14 Trade Lifecycle (Section 10.9 — P&L data), Portfolio Construction (Section 11.2 — target weights for decision attribution), Capital Allocation (Section 11.4 — allocation changes for decision attribution), and Risk Management (Section 11.5 — factor data for factor attribution).

---

## 11.7.12 Attribution Performance and Scalability

Attribution computation shall satisfy performance objectives for single-period and multi-period attribution. Services shall scale with position count, factor count, and attribution period length. Computation shall preserve determinism per Port-3.

End-of-day batch window specification:

| Job | Trigger | Target Completion | Dependency |
|-----|---------|------------------|------------|
| Market Data Finalization (Document 11) | Market Close 16:00 EST | 16:15 | None |
| Portfolio State Snapshot | Market Data Finalized | 16:20 | Market data ready |
| Risk Metrics (EOD VaR, CVaR) | Portfolio Snapshot | 16:45 | Portfolio snapshot |
| Attribution Computation (single-period) | Portfolio Snapshot + Benchmark Data | 17:15 | Risk metrics + benchmark |
| Attribution Computation (multi-period) | Single-Period Attribution | 18:00 | Single-period complete |
| Regulatory Report Generation | Attribution Complete | 19:00 | Attribution data |
| Compliance Scans (post-trade) | Portfolio Snapshot | 17:00 | Portfolio snapshot |
| Risk Report Generation | Risk Metrics | 17:15 | Risk metrics |
| Performance Report Generation | Attribution Complete | 18:30 | Attribution data |
| Data Archival (Document 11) | All Jobs Complete | 21:00 | All EOD jobs |

Batch window SLA: All EOD jobs complete by 20:00 EST. Jobs exceeding target shall trigger Warning alert. Jobs exceeding 2x target shall trigger Error alert. Late-arriving market data shall be handled with a 30-minute grace window — jobs shall wait for data rather than proceed with incomplete data.

---

## 11.7.13 Risks

The Portfolio Performance Attribution Architecture shall continuously assess risks including:

- Attribution Error — Incorrect attribution misinforming capital allocation and governance decisions
- Factor Misspecification — Incorrect or omitted factors distorting alpha estimation
- Multi-Period Compounding Error — Arithmetic attribution not correctly compounding over multiple periods
- Benchmark Mismatch — Attribution benchmark not reflecting actual investment universe
- Residual Misinterpretation — Residual attributed as alpha when it represents missing factors
- Survivorship Bias — Attribution analysis excluding failed strategies or delisted instruments

Every identified risk shall include risk classification, impact assessment, likelihood assessment, detection method, mitigation strategy, recovery procedure, and ownership.

---

## 11.7.14 Acceptance Criteria

The Portfolio Performance Attribution Architecture shall be considered complete when the platform demonstrates:

- Multiple attribution models supported without embedding methodology assumptions per P-1
- Brinson attribution decomposing return into allocation, selection, and interaction effects
- Factor attribution decomposing return into systematic factor contributions and residual alpha
- Strategy attribution enabling per-strategy performance assessment
- Decision attribution linking returns to governance decisions
- Deterministic attribution per Port-3
- Complete attribution audit trail per P-5
- Integration with risk management factor decomposition

---

## 11.7.15 Cross References

This section shall be read together with Section 11.1 (Portfolio Platform), Section 11.2 (Portfolio Construction), Section 11.4 (Capital Allocation), Section 11.5 (Risk Management), Section 11.8 (Governance), Document 13 (per Section 9.10), Document 14 (per Section 10.9.5), and handbook/ARCHITECTURAL_INVARIANTS.md (per P-1, P-2, P-5, P-13, Port-3).

---

# End of Section

---

# 11.8 Portfolio Governance Architecture

## 11.8.1 Purpose

The Portfolio Governance Architecture defines the portfolio-level governance framework extending Document 11 Section 7.11 Data Governance, Document 13 Section 9.11 Research Governance, and Document 14 Section 10.10 Trading Governance.

Portfolio governance shall provide the oversight framework for all portfolio management activities — construction methodology, position sizing, capital allocation, risk management, rebalancing, and attribution. It shall implement Port-5 (Strategy Risk Separation) — risk management authority shall operate at the portfolio level above individual strategies.

Portfolio governance shall be the highest governance tier in the Quant Hub platform stack. It shall exercise authority over capital deployment and risk management across all strategies.

---

## 11.8.2 Scope

The Portfolio Governance Architecture applies to all portfolio governance within the Quant Hub platform.

Coverage includes:

- Portfolio Construction Governance
- Capital Allocation Governance
- Risk Governance
- Rebalancing Governance
- Attribution Governance
- Portfolio Audit
- Portfolio Oversight

The following topics are intentionally excluded:

- Data governance — Frozen per Document 11 (D-7.11)
- Research governance — Frozen per Document 13 (Section 9.11)
- Trading governance — Frozen per Document 14 (Section 10.10)

---

## 11.8.3 Portfolio Governance Principles

Portfolio governance shall be founded on platform and portfolio invariants.

Governance principles include:

- Portfolio-Level Authority — Portfolio governance shall have authority over all strategies. No strategy shall self-regulate without oversight per Port-5.
- Risk-First Governance — Risk considerations shall take precedence over return considerations. Capital shall not be deployed without risk governance approval per Port-2.
- Evidence-Based Decisions — All governance decisions shall be based on documented evidence: risk metrics, attribution results, stress test results, and backtest evidence
- Immutable Decisions — Governance decisions shall produce immutable records per Port-6
- Separation of Duties — Portfolio construction, risk management, capital allocation, and audit shall be separated per D-10

---

## 11.8.4 Portfolio Construction Governance

Portfolio construction shall be governed through defined approval processes.

Governance shall include:

- Methodology Approval — Construction methodology shall be approved by portfolio governance before production use. Approval shall review: methodology documentation, assumptions, constraints, expected behavior, and risk implications.
- Methodology Change Governance — Methodology changes shall be governed. Material changes require re-approval. Changes shall include impact assessment on portfolio risk profile.
- Constraint Governance — Portfolio constraints shall be approved. Constraint changes require governance approval.
- Construction Review — Periodic review of construction methodology for continued appropriateness.

---

## 11.8.5 Capital Allocation Governance

Capital allocation shall be governed through risk-budgeted processes.

Governance shall include:

- Allocation Approval — Initial capital allocation shall be approved with documented rationale and risk assessment
- Allocation Change Governance — Material allocation changes require approval. Changes shall include impact assessment on portfolio risk and diversification.
- Risk Budget Governance — Risk budgets allocated per strategy. Budget changes require approval per Section 11.4.4.
- Allocation Review — Periodic review of capital allocation for continued appropriateness
- Drawdown Governance — Portfolio-level drawdown thresholds. Exceeding thresholds triggers governed review and potential capital reduction per Section 11.4.7.

---

## 11.8.6 Portfolio Risk Governance

Risk governance shall operate at the portfolio level with authority over strategies per Port-5.

Governance shall include:

- Risk Limit Governance — Portfolio-level risk limits set and approved per Section 11.5.7. Limits reviewed periodically.
- Risk Limit Breach Escalation — Breach of portfolio risk limits escalates immediately. Response shall include: immediate notification, investigation of cause, risk reduction actions (may include strategy capital reduction, position liquidation, trading halt via Document 14 circuit breaker), and documented resolution.

Risk breach escalation procedure:

| Breach Severity | Response Time | Escalation Path | Actions |
|----------------|--------------|-----------------|---------|
| Minor (< 20% over limit) | Acknowledge <= 15 min, Resolve <= 4 hours | Risk Manager → Portfolio Manager | Investigation, documented resolution |
| Moderate (20-50% over limit) | Acknowledge <= 5 min, Contain <= 30 min | Risk Manager → PM → CRO | Strategy capital reduction consideration |
| Severe (50-100% over limit) | Acknowledge <= 2 min, Contain <= 15 min | Risk Manager → PM → CRO → CEO | Mandatory position reduction, strategy pause consideration |
| Critical (> 100% over limit) | Acknowledge <= 1 min, Contain <= 5 min | All above + Board notification | Immediate trading halt via Document 14 circuit breaker (T-6) |

Escalation shall be automated through the alerting infrastructure per Document 11 Section 7.13.12. Every escalation step shall produce immutable audit records. Escalation contacts shall be maintained in a governed on-call rotation schedule. Quarterly drill exercises shall validate escalation paths.
- Risk Model Governance — Risk models approved, validated, and periodically reviewed per Section 11.5.4
- Stress Testing Governance — Stress test scenarios defined and results reviewed
- Risk Governance Independence — Risk governance shall have independent authority. Risk decisions shall not be overridden by portfolio construction or capital allocation governance.

---

## 11.8.7 Rebalancing Governance

Rebalancing shall be governed to ensure alignment with portfolio objectives.

Governance shall include:

- Methodology Governance — Rebalancing methodology and trigger parameters approved
- Execution Governance — Material rebalancing events reviewed. Large rebalancing trades may require approval.
- Drift Monitoring — Portfolio drift monitored. Excessive drift triggering review of rebalancing parameters.
- Rebalancing Review — Periodic review of rebalancing effectiveness

---

## 11.8.8 Attribution Governance

Performance attribution shall be governed for decision accountability.

Governance shall include:

- Methodology Governance — Attribution methodology approved and documented
- Attribution Review — Periodic review of attribution results. Attribution results shall inform capital allocation and methodology decisions.
- Factor Governance — Factor definitions used in attribution governed

---

## 11.8.9 Portfolio Audit

Every portfolio governance action shall produce immutable audit records per Port-6.

Audit domains shall include:

- Construction Methodology Audit — Methodology approvals, changes, and reviews
- Capital Allocation Audit — Allocation approvals, changes, and reviews
- Risk Audit — Risk limit approvals, changes, breaches, and responses
- Rebalancing Audit — Rebalancing events and approvals
- Governance Audit — Governance meeting records, decisions, and rationales
- Exception Audit — Governance exceptions with justification, approval, and time bounds

Audit records shall be tamper-proof, queryable, and retained per Document 11 retention policies.

---

## 11.8.10 Portfolio Exception Management

Governance exceptions shall follow governed processes.

Exception management shall include:

- Exception Justification — Business rationale for operating outside normal governance parameters
- Exception Risk Assessment — Risk implications of exception
- Exception Approval — Approval by designated governance authority
- Exception Time Bound — Defined expiration
- Exception Review — Periodic review of active exceptions
- Exception Audit — All exceptions recorded per P-5

Exceptions shall never persist indefinitely. Exceptions shall not bypass risk limits per Port-2.

---

## 11.8.11 Portfolio Governance Dashboards

Portfolio governance shall provide dashboards per Section 11.10.

Dashboards shall include:

- Portfolio Overview — Current allocation, risk metrics, P&L summary
- Risk Dashboard — Risk metrics, limit utilization, stress test results
- Governance Pipeline — Pending approvals, recent decisions
- Audit Summary — Recent governance actions, exceptions
- Performance Dashboard — Attribution results, strategy performance

---

## 11.8.12 Portfolio Governance Integration

Portfolio governance shall integrate with Document 11 governance per D-7.11, Document 13 research governance per Section 9.11, and Document 14 trading governance per Section 10.10. Integration shall extend without redefining frozen governance infrastructure per P-10.

Portfolio governance shall exercise authority over trading governance — portfolio risk limits shall supersede strategy risk limits per Port-5.

---

## 11.8.13 Portfolio Governance Security

Governance shall be secured through authentication per D-9, authorization for governance actions, integrity protection for governance records, and comprehensive audit logging per P-5. Governance configuration changes shall themselves be governed.

---

## 11.8.14 Portfolio Governance Performance

Governance services shall satisfy performance objectives: approval processing latency (shall not delay time-sensitive capital allocation or risk decisions), audit record processing, and dashboard query response.

---

## 11.8.15 Risks

The Portfolio Governance Architecture shall continuously assess risks including:

- Governance Override — Trading or portfolio construction governance overriding risk governance decisions
- Approval Bottleneck — Governance review delaying time-sensitive allocation or risk decisions
- Risk Governance Capture — Risk governance becoming subservient to return objectives
- Audit Gap — Portfolio governance decisions not captured in audit trail
- Exception Proliferation — Governance exceptions accumulating without proper review
- Information Asymmetry — Governance decisions made without complete risk and attribution information

Every identified risk shall include risk classification, impact assessment, likelihood assessment, detection method, mitigation strategy, recovery procedure, and ownership.

---

## 11.8.16 Acceptance Criteria

The Portfolio Governance Architecture shall be considered complete when the platform demonstrates:

- Portfolio-level governance authority over all strategies per Port-5
- Construction methodology governance with approval and periodic review
- Capital allocation governance with risk-budgeted approval processes
- Independent risk governance with breach escalation and trading circuit breaker authority
- Complete portfolio audit trail for all governance decisions per Port-6
- Governance dashboards providing portfolio oversight and transparency
- Integration with Document 11, 13, and 14 governance without redefinition per P-10
- No strategy self-regulation without portfolio-level oversight per Port-5

---

## 11.8.17 Cross References

This section shall be read together with Section 11.1 (Portfolio Platform), Section 11.2 (Portfolio Construction), Section 11.4 (Capital Allocation), Section 11.5 (Risk Management), Section 11.10 (Observability), Document 11 (per D-7.11), Document 13 (per Section 9.11), Document 14 (per Section 10.10), and handbook/ARCHITECTURAL_INVARIANTS.md (per P-1, P-2, P-5, P-10, P-17, Port-2, Port-5, Port-6).

---

# End of Section

---

# 11.9 Portfolio Security Architecture

## 11.9.1 Purpose

The Portfolio Security Architecture defines the portfolio-specific security framework extending Document 11 Section 7.12 Data Security, Document 13 Section 9.14 Research Security, and Document 14 Section 10.11 Trading Security.

Portfolio security shall protect the confidentiality, integrity, and availability of portfolio operations — capital allocation decisions, risk exposures, portfolio construction methodology, performance attribution, and portfolio intellectual property. Security controls shall extend enterprise security without redefining it per P-10.

Portfolio security shall protect the most sensitive information in the Quant Hub platform — how capital is deployed, what risks are taken, and what returns are generated. Breach of portfolio data shall be treated as a critical security incident.

---

## 11.9.2 Scope

The Portfolio Security Architecture applies to all portfolio operations within the Quant Hub platform.

Coverage includes:

- Portfolio Authentication
- Portfolio Authorization
- Portfolio Data Encryption
- Portfolio Access Control
- Security Monitoring
- Security Incident Response

The following topics are intentionally excluded:

- Data security — Frozen per Document 11 (D-7.12)
- Identity management — Frozen per Document 9
- Trading security — Frozen per Document 14 (Section 10.11)
- Research security — Frozen per Document 13 (Section 9.14)

---

## 11.9.3 Portfolio Authentication

All portfolio operations shall require authenticated identity extending Document 9.

Authentication shall include:

- Human Authentication — Multi-factor authentication required for sensitive portfolio operations: capital allocation changes, risk limit modifications, construction methodology changes, governance approvals
- Service Account Authentication — Service accounts for automated portfolio operations (risk computation, rebalancing, attribution) with governed credential management scoped to specific portfolio functions
- Session Management — Portfolio sessions with appropriate timeouts. Sensitive operations may require re-authentication.
- Authentication Audit — All authentication events logged per P-5

---

## 11.9.4 Portfolio Authorization

Portfolio access shall be governed through authorization controls extending Document 14 Section 10.11.4.

Authorization shall include:

- Role-Based Access — Portfolio roles: Portfolio Manager, Risk Manager, Portfolio Analyst, Portfolio Governance Officer, Portfolio Administrator
- Portfolio-Scoped Authorization — Access scoped to specific portfolios. A portfolio manager for one portfolio shall not access another.
- Operation-Scoped Authorization — Authorization by operation: view performance, view risk, modify construction, modify allocation, modify risk limits, approve governance decisions
- Segregation of Duties — Portfolio construction, risk management, and capital allocation authorization shall be separated. No individual shall have authority over all three domains.
- Authorization Audit — All authorization grants, modifications, and revocations logged per P-5

Authorization shall follow least privilege — identities shall possess only the permissions necessary for their authorized functions.

---

## 11.9.5 Capital Allocation Security

Capital allocation operations shall receive enhanced security protection.

Security controls shall include:

- Multi-Person Authorization — Material capital allocation changes shall require authorization from both portfolio management and risk governance
- Allocation Change Audit — Every allocation change recorded with complete context: previous allocation, new allocation, rationale, approving authorities
- Allocation Limits — System-enforced limits on allocation change magnitude without additional authorization
- Emergency Override — Emergency capital reduction procedures with post-action governance review

---

## 11.9.6 Portfolio Data Encryption

All portfolio data shall be encrypted per D-7.12.5.

Encryption shall cover:

- At Rest — Portfolio configurations, construction methodology, capital allocation records, risk model configurations, risk metrics history, attribution results, governance records, and audit trails
- In Transit — All communications between portfolio services, communication with Document 14 Trading Infrastructure, communication with enterprise services

Key management shall follow Document 11 encryption infrastructure.

---

## 11.9.7 Portfolio Access Control

Portfolio data access shall be governed through access controls.

Access controls shall include:

- Portfolio-Level Isolation — Access to one portfolio's data shall not grant access to another portfolio's data
- Time-Bound Access — Temporary access grants with automatic expiration for specific reviews or audits
- Access Review — Periodic review of active access grants
- Access Audit — All portfolio data access logged per P-5

---

## 11.9.8 Security Monitoring

Portfolio security shall be continuously monitored per P-15.

Monitoring shall include:

- Authentication Monitoring — Failed authentication attempts, unusual access patterns
- Authorization Monitoring — Authorization violations, privilege escalation attempts
- Data Access Monitoring — Unusual portfolio data access patterns, large data exports
- Configuration Monitoring — Security configuration changes
- Allocation Change Monitoring — Capital allocation changes flagged for security review

Security events shall generate alerts through Section 11.10.

---

## 11.9.9 Security Testing

Portfolio security controls shall satisfy testing requirements.

Testing shall include:

- Penetration Testing — Portfolio platform penetration testing
- Access Control Testing — Verification that authorization controls correctly restrict access
- Encryption Verification — Verification that encryption is correctly applied
- Segregation of Duties Testing — Verification that separated roles cannot perform unauthorized cross-domain actions
- Security Regression Testing — Security testing on significant platform changes

Testing shall be conducted periodically and on significant changes.

---

## 11.9.10 Security Incident Response

Portfolio security incidents shall be managed through governed incident response per Document 14 Section 10.11.10.

Incident response shall include detection, classification (Critical for capital allocation or risk data breach), containment, investigation, remediation, evidence preservation per P-5, and post-incident review.

---

## 11.9.11 Security Performance

Security controls shall satisfy performance objectives. Authentication latency, authorization check latency, and encryption overhead shall not materially degrade portfolio operations or risk computation performance.

---

## 11.9.12 Risks

The Portfolio Security Architecture shall continuously assess risks including:

- Capital Allocation Tampering — Unauthorized modification of capital allocation
- Risk Data Breach — Portfolio risk exposures exfiltrated
- Methodology Theft — Proprietary portfolio construction methodology stolen
- Segregation Failure — Individual obtaining authority across construction, risk, and allocation domains
- Audit Tampering — Portfolio audit records modified or deleted

Every identified risk shall include risk classification, impact assessment, likelihood assessment, detection method, mitigation strategy, recovery procedure, and ownership.

---

## 11.9.13 Acceptance Criteria

The Portfolio Security Architecture shall be considered complete when the platform demonstrates:

- Multi-factor authentication for sensitive portfolio operations extending Document 9
- Role-based, portfolio-scoped, and operation-scoped authorization
- Segregation of duties between portfolio construction, risk management, and capital allocation
- Enhanced security for capital allocation operations
- Portfolio data encryption at rest and in transit per D-7.12.5
- Security monitoring with anomaly detection and alerting
- No redefinition of frozen enterprise security infrastructure per P-10

---

## 11.9.14 Cross References

This section shall be read together with Section 11.1 (Portfolio Platform), Section 11.8 (Governance), Section 11.10 (Observability), Document 9 (Identity and Access Management), Document 11 (per D-7.12), Document 13 (per Section 9.14), Document 14 (per Section 10.11), and handbook/ARCHITECTURAL_INVARIANTS.md (per P-1, P-2, P-5, P-10, P-15).

---

# End of Section

---

# 11.10 Portfolio Observability Architecture

## 11.10.1 Purpose

The Portfolio Observability Architecture defines the portfolio-specific observability framework extending Document 11 Section 7.13 Data Observability, Document 13 Section 9.15 Research Observability, and Document 14 Section 10.12 Trading Observability.

Portfolio observability shall provide continuous visibility into portfolio risk, exposures, performance attribution, capital allocation, and governance status. Observability shall support risk management, governance oversight, and investment decision-making.

Observability shall implement P-15 (Monitoring and Alerting) for the portfolio domain. Portfolio alerts shall notify on risk breaches, concentration warnings, attribution anomalies, and governance events.

---

## 11.10.2 Scope

The Portfolio Observability Architecture applies to all portfolio-related observability within the Quant Hub platform.

Coverage includes:

- Risk Dashboards
- Exposure Monitoring
- Attribution Dashboards
- Portfolio Alerts
- Portfolio SLOs

The following topics are intentionally excluded:

- Data observability — Frozen per Document 11 (D-7.13)
- Trading observability — Frozen per Document 14 (Section 10.12)
- Research observability — Frozen per Document 13 (Section 9.15)

---

## 11.10.3 Portfolio Metrics

The platform shall maintain standardized portfolio metrics extending enterprise observability.

Metric categories include:

- Risk Metrics — VaR, CVaR, volatility, maximum drawdown, factor exposures, concentration (instrument, sector, factor, strategy), leverage (gross, net), liquidity profile, stress test losses
- Performance Metrics — Portfolio return (total, attribution, benchmark-relative), strategy contributions, factor contributions, risk-adjusted return (Sharpe, Sortino, information ratio)
- Allocation Metrics — Capital allocation (per strategy, current vs target), risk budget utilization, allocation drift
- Governance Metrics — Pending approvals, recent decisions, exception count, audit events

Metrics shall be collected continuously per D-7.13.1 and reported through dashboards.

---

## 11.10.4 Risk Dashboards

The platform shall provide real-time risk dashboards.

Risk dashboards shall include:

- Risk Overview — Current VaR, CVaR, volatility with trend indicators and limit utilization percentage
- Factor Exposure Dashboard — Current factor exposures with limits. Factor exposure changes highlighted.
- Concentration Dashboard — Concentration by instrument, sector, and strategy. Concentration warnings at defined thresholds.
- Stress Test Dashboard — Stress test results across defined scenarios. Maximum stress loss. Scenario comparison.
- Risk Trend Dashboard — Risk metrics over time. Risk regime indicators. Risk acceleration detection.
- Limit Utilization Dashboard — All risk limits with current utilization. Warning zone (80%+). Breach zone (100%+).

Dashboards shall support real-time and historical views, role-based access, and configurable thresholds.

---

## 11.10.5 Exposure Monitoring

Portfolio exposures shall be continuously monitored.

Exposure monitoring shall include:

- Gross Exposure — Sum of absolute position values as percentage of portfolio
- Net Exposure — Long minus short exposure
- Delta Exposure — Option-adjusted exposure
- Sector Exposure — Exposure by sector with limits
- Factor Exposure — Exposure by factor with limits per Section 11.5.5
- Strategy Exposure — Exposure per strategy with allocation comparison
- Counterparty Exposure — Exposure to counterparties for OTC instruments
- Currency Exposure — Exposure by currency

Exposure breaches shall trigger immediate alerts.

---

## 11.10.6 Attribution Dashboards

The platform shall provide performance attribution dashboards.

Attribution dashboards shall include:

- Return Attribution Overview — Total return decomposed into allocation, selection, interaction, factor, and residual components
- Factor Contribution — Each factor's contribution to portfolio return
- Strategy Contribution — Each strategy's contribution to portfolio return with benchmark comparison
- Decision Attribution — Return impact of allocation, construction, and rebalancing decisions
- Attribution History — Attribution results over time enabling trend analysis

Attribution dashboards shall support drill-down from portfolio level to strategy level to position level.

---

## 11.10.7 Allocation Dashboards

Capital allocation shall be visible through allocation dashboards.

Allocation dashboards shall include:

- Current Allocation — Capital allocated per strategy with comparison to target allocation and risk budget
- Allocation History — Allocation changes over time with rationale
- Risk Budget Utilization — Risk budget consumed per strategy
- Allocation Drift — Current allocation deviation from target
- Drawdown Overlay — Strategy drawdown overlaid on allocation for drawdown-based adjustment assessment

---

## 11.10.8 Portfolio Alerts

Portfolio alerts shall extend enterprise alerting per D-7.13.6 and Document 14 Section 10.12.7.

Alert categories include:

- Risk Alerts — VaR limit breached, CVaR limit breached, volatility limit breached, drawdown threshold exceeded, factor exposure limit breached, concentration limit breached, leverage limit breached, stress test loss exceeding limit
- Performance Alerts — Significant underperformance vs benchmark, attribution anomaly, factor contribution anomaly
- Allocation Alerts — Allocation drift exceeding threshold, risk budget exhaustion, strategy drawdown triggering allocation review
- Governance Alerts — Pending approval exceeding threshold, governance exception expiring, audit event requiring review
- System Alerts — Risk computation failure, data feed interruption, integration failure

Alerts shall include severity classification, notification routing, alert correlation, and alert history for trend analysis.

---

## 11.10.9 Portfolio SLOs

Portfolio services shall have defined SLOs per D-7.13.5.

Portfolio SLOs shall include:

- Risk Computation SLO — Risk metrics computed within bounded time after position update
- Stress Test SLO — Stress tests completed within bounded time
- Attribution Computation SLO — Attribution results available within bounded time after period close
- Dashboard SLO — Portfolio dashboard data freshness
- Service Availability SLO — Portfolio service uptime requirement

SLOs shall be continuously measured. SLO violations shall trigger operational alerts.

---

## 11.10.10 Portfolio Logging

Portfolio events shall be logged for observability and audit.

Logging shall include: construction events, sizing events, allocation events, risk computation events, rebalancing events, attribution events, governance events, and security events. Logs shall be immutable after recording per P-2.

---

## 11.10.11 Observability Integration

Portfolio observability shall integrate with enterprise observability infrastructure per D-7.13, Document 12 ML observability (Section 8.9), Document 13 research observability (Section 9.15), Document 14 trading observability (Section 10.12), and enterprise dashboard federation. Integration shall avoid duplication per P-10.

---

## 11.10.12 Observability Governance

Portfolio observability shall be governed through enterprise governance processes. Governance shall include metric definition governance, SLO governance, alert rule governance, dashboard governance, and observability audit trail per P-5.

---

## 11.10.13 Observability Security

Observability data shall be secured through access control, encryption, integrity protection, and audit logging. Dashboards shall not expose sensitive portfolio data beyond authorized roles. Observability access shall respect portfolio security boundaries per Section 11.9.

---

## 11.10.14 Observability Performance and Scalability

Observability shall satisfy performance objectives for metric collection latency, dashboard query response, and alert evaluation latency. Infrastructure shall scale with portfolio count growth, metric volume growth, and dashboard concurrent access.

---

## 11.10.15 Risks

The Portfolio Observability Architecture shall continuously assess risks including:

- Risk Misreporting — Incorrect risk metrics displayed affecting governance decisions
- Alert Fatigue — Excessive portfolio alerts causing critical alerts to be ignored
- Dashboard Blindness — Critical portfolio metrics not visible on dashboards
- Data Freshness Gap — Dashboards displaying stale risk or attribution data
- Attribution Error Visualization — Incorrect attribution leading to misinformed allocation decisions

Every identified risk shall include risk classification, impact assessment, likelihood assessment, detection method, mitigation strategy, recovery procedure, and ownership.

---

## 11.10.16 Acceptance Criteria

The Portfolio Observability Architecture shall be considered complete when the platform demonstrates:

- Real-time risk dashboards covering VaR, factor exposures, concentrations, and stress tests
- Exposure monitoring with immediate breach alerts
- Attribution dashboards enabling factor, strategy, and decision-level analysis
- Capital allocation dashboards with risk budget utilization tracking
- Comprehensive portfolio alerting with severity classification
- Defined SLOs for risk computation, stress testing, and attribution
- Integration with enterprise observability without duplication per P-10

---

## 11.10.17 Cross References

This section shall be read together with Section 11.1 (Portfolio Platform), Section 11.5 (Risk Management), Section 11.7 (Attribution), Section 11.8 (Governance), Section 11.9 (Security), Document 11 (per D-7.13), Document 13 (per Section 9.15), Document 14 (per Section 10.12), and handbook/ARCHITECTURAL_INVARIANTS.md (per P-1, P-5, P-10, P-15).

---

# End of Section

---

# 11.11 Portfolio Infrastructure

## 11.11.1 Purpose

The Portfolio Infrastructure section defines the compute, network, and operational infrastructure supporting the Quant Hub portfolio management platform. It extends platform infrastructure without redefining it per P-10.

Portfolio infrastructure shall provide the computational foundation for portfolio construction, position sizing, capital allocation, risk measurement, rebalancing, and performance attribution. Infrastructure shall be abstracted from portfolio services per P-3.

Infrastructure shall be strategy-agnostic per P-1. No infrastructure component shall embed assumptions about specific portfolio construction methodologies, risk models, or allocation strategies.

---

## 11.11.2 Scope

The Portfolio Infrastructure section applies to all infrastructure supporting the Quant Hub portfolio platform.

Coverage includes:

- Portfolio Compute
- Portfolio Storage
- Portfolio Networking
- Infrastructure Abstraction
- Operational Resilience
- Cost Optimization

The following topics are intentionally excluded:

- Enterprise infrastructure — Owned by Documents 02, 03, 07
- Data storage infrastructure — Frozen per Document 11 (D-7.1)
- Trading infrastructure — Frozen per Document 14 (Section 10.13)
- Research infrastructure — Frozen per Document 13 (Section 9.16)

---

## 11.11.3 Portfolio Compute

Portfolio platform compute resources shall be provisioned for portfolio workloads.

Compute management shall include:

- Risk Computation Compute — Compute for continuous risk measurement: VaR, CVaR, factor decomposition, stress testing. Optimized for parallel computation where applicable — risk metrics for multiple portfolios, factors, and scenarios computed concurrently.
- Optimization Compute — Compute for portfolio construction and rebalancing optimization. Higher-memory for large covariance matrices. Performance balanced against optimization frequency.
- Attribution Compute — Compute for performance attribution: Brinson, factor-based, multi-period. Batch-oriented with defined completion windows.
- Compute Isolation — Portfolio compute isolated from trading compute to prevent portfolio workloads from affecting trading latency per Document 14 T-7.
- Compute Abstraction — Compute resources abstracted per P-3. Portfolio services shall not embed compute-specific assumptions.

---

## 11.11.4 Portfolio Storage

Portfolio data shall be stored through Document 11 storage infrastructure per D-7.1.

Storage shall include:

- Portfolio State Storage — Current portfolio weights, allocations, positions. High-durability persistent storage.
- Risk History Storage — Historical risk metrics for trend analysis and backtesting. Time-series optimized.
- Attribution History Storage — Historical attribution results. Time-series with factor and strategy dimensions.
- Governance Storage — Governance decisions, approvals, and audit trails. Immutable storage per P-2.
- Configuration Storage — Portfolio construction methodology, risk model, and allocation methodology configurations. Version history maintained.
- Cost-Optimized Tiering — Historical data tiered through Document 11 storage tiers per D-7.6.4: active data on optimized storage, historical data on cost-optimized storage.

---

## 11.11.5 Portfolio Networking

Portfolio platform networking shall provide governed connectivity.

Networking shall include:

- Upstream Connectivity — Network connectivity to Document 11 for market data and reference data, Document 12 for model predictions, Document 14 for position and P&L data
- Internal Connectivity — Secure inter-service communication between portfolio services
- Downstream Connectivity — Communication of portfolio weights, sizing parameters, and risk limits to Document 14 trading infrastructure
- Network Isolation — Portfolio traffic isolated from trading traffic to prevent interference
- Network Monitoring — Continuous network latency, throughput, and error monitoring

---

## 11.11.6 Infrastructure Abstraction

Portfolio infrastructure shall be abstracted from portfolio services per P-3.

Abstraction shall ensure:

- Compute Abstraction — Services interact with governed compute interfaces, not specific hardware or providers
- Storage Abstraction — Services interact with Document 11 storage interfaces per D-7.1, not specific storage implementations
- Network Abstraction — Services interact with governed network interfaces, not specific network topologies
- Data Abstraction — Services consume data through governed contracts per D-8, not direct data access

Abstraction shall enable infrastructure migration without affecting portfolio services.

---

## 11.11.7 Operational Resilience

Portfolio infrastructure shall maintain operational resilience.

Resilience shall include:

- Component Redundancy — Critical risk monitoring components deployed with redundancy
- State Recovery — Portfolio state recoverable from persistent storage and audit trails
- Graceful Degradation — Attribution and historical analysis may degrade while risk monitoring remains operational
- Resilience Testing — Failover and recovery scenarios tested periodically

Portfolio operations are less latency-critical than trading — brief interruption of attribution computation is acceptable; interruption of risk monitoring is not.

---

## 11.11.8 Disaster Recovery

Portfolio DR shall enable portfolio operations resumption following significant failure.

DR shall include: secondary infrastructure for DR activation, documented DR procedures, periodic DR testing, portfolio state recoverability, risk history recoverability, and governance record recoverability. DR shall follow Document 11 DR architecture per D-7.5.

---

## 11.11.9 Infrastructure Scalability

Portfolio infrastructure shall scale with portfolio platform growth including portfolio count growth, strategy count growth, factor count growth, instrument universe growth, and attribution history growth. Scaling shall preserve risk computation determinism per Port-3.

---

## 11.11.10 Cost Optimization

Portfolio infrastructure shall be governed for cost efficiency.

Cost optimization shall include: risk computation right-sized to portfolio requirements, optimization compute matched to optimization frequency and complexity, historical data tiered per D-7.6.4, cost attribution by portfolio and function, and governance reporting for cost oversight. Cost optimization shall not compromise risk monitoring availability.

---

## 11.11.11 Infrastructure Operations

Portfolio infrastructure shall be operated through governed operations practices including provisioning automation, maintenance windows communicated and governed, upgrades managed without disrupting risk monitoring, continuous infrastructure health monitoring, and operational runbooks for failure scenarios.

---

## 11.11.12 Infrastructure Testing

Portfolio infrastructure testing shall include risk computation throughput testing, optimization solver testing, failover and DR testing, network resilience testing, and capacity testing. Testing shall not disrupt live risk monitoring.

---

## 11.11.13 Risks

The Portfolio Infrastructure section shall continuously assess risks including:

- Resource Contention — Portfolio optimization competing with risk computation for compute resources
- Storage Growth — Uncontrolled risk and attribution history growth
- Network Latency — Portfolio-to-trading communication latency delaying position sizing parameter updates
- Single Point of Failure — Critical risk monitoring infrastructure without redundancy
- Abstraction Leak — Infrastructure details leaking through abstraction to portfolio services

Every identified risk shall include risk classification, impact assessment, likelihood assessment, detection method, mitigation strategy, recovery procedure, and ownership.

---

## 11.11.14 Acceptance Criteria

The Portfolio Infrastructure section shall be considered complete when the platform demonstrates:

- Compute resources provisioned for risk computation, optimization, and attribution workloads
- Portfolio data stored through Document 11 storage infrastructure per D-7.1
- Network connectivity to Documents 11, 12, and 14 with governed isolation
- Infrastructure abstraction enabling migration without service changes per P-3
- Operational resilience prioritizing risk monitoring continuity
- DR with portfolio state and risk history recoverability
- No vendor-specific or strategy-specific infrastructure assumptions per P-1, P-3

---

## 11.11.15 Cross References

This section shall be read together with Section 11.1 (Portfolio Platform), Section 11.5 (Risk Management), Section 11.9 (Security), Document 11 (per D-7.1, D-7.5, D-7.6, D-7.12), Documents 02, 03, 07 (enterprise infrastructure), Document 14 (per Section 10.13), and handbook/ARCHITECTURAL_INVARIANTS.md (per P-1, P-2, P-3, P-10, P-15, Port-3).

---

# End of Section

---

# 

---

## Implementation Specification Requirements

This section defines portfolio-specific implementation requirements that extend the canonical type system and specification requirements defined in Document 11. The Document 11 canonical type system SHALL be used for all fields. All requirements apply per Document 11 Implementation Specification Requirements section.

### Portfolio-Specific Canonical Types

| Type | Definition | Example |
|------|-----------|---------|
| `portfolio_id` | UUID v7 | `"550e8400-e29b-41d4-a716-446655440020"` |
| `strategy_id` | Strategy reference string(max 64) per P-1 | `"momentum_v3"` |
| `instrument_id` | Canonical instrument symbol per Document 11 | `"AAPL"`, `"ESM26"` |
| `weight` | Fixed-point decimal with 6 decimal places, expressed as fraction (0.0 to 1.0) | `"0.037500"` |
| `notional` | `decimal(20,4)` — monetary amount in base currency | `"1500000.0000"` |
| `currency_code` | ISO 4217 3-letter currency code | `"USD"`, `"EUR"`, `"JPY"` |
| `attribution_result` | Structured decomposition of return into component contributions | See Attribution Output Format below |

---

## Portfolio Construction API Contract

### Constraint Specification Format

Every portfolio constraint SHALL be expressed using this typed structure:

| Field | Type | Description |
|-------|------|-------------|
| `constraint_id` | `string(64)` | Unique constraint identifier |
| `constraint_type` | `enum{"RISK_LIMIT","POSITION_LIMIT","TURNOVER_LIMIT","LIQUIDITY_LIMIT","REGULATORY","CUSTOM"}` | Constraint category |
| `parameters` | `dict[string, any]` | Type-specific parameters |
| `priority` | `integer` | Relaxation priority (1 = highest, relaxed last during infeasibility) |
| `relaxable` | `boolean` | Whether this constraint may be relaxed during solver infeasibility |
| `hard` | `boolean` | Hard constraints SHALL NOT be relaxed under any circumstance |

Example constraint: `{constraint_type: "POSITION_LIMIT", parameters: {"max_weight": 0.05, "scope": "SINGLE_INSTRUMENT"}, priority: 3, relaxable: true, hard: false}`

### Optimizer Input

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `portfolio_id` | `portfolio_id` | Yes | Target portfolio |
| `target_date` | `timestamp` | Yes | Effective date for the optimization |
| `methodology` | `enum{"MEAN_VARIANCE","RISK_PARITY","BLACK_LITTERMAN","MINIMUM_VARIANCE","MAX_DIVERSIFICATION","CUSTOM"}` | Yes | Optimization methodology |
| `expected_returns` | `list[{instrument_id, value: float}]` | Depends on methodology | Expected return estimates; required for mean-variance, Black-Litterman |
| `covariance_matrix_uri` | `uri` | Yes | D-8 contract reference to covariance matrix |
| `constraints` | `list[Constraint]` | Yes | All applicable constraints |
| `current_positions` | `list[{instrument_id, quantity: integer, current_price: decimal_price}]` | No | Current positions for turnover-aware optimization |
| `benchmark_weights` | `list[{instrument_id, weight}]` | No | Benchmark for tracking-error-constrained optimization |

### Optimizer Output

| Field | Type | Description |
|-------|------|-------------|
| `optimization_id` | `uuid` | Unique optimization run identifier |
| `status` | `enum{"OPTIMAL","FEASIBLE","INFEASIBLE","TIMED_OUT","ERROR"}` | Solver status |
| `target_weights` | `list[{instrument_id, strategy_id, weight: decimal(8,6), notional: notional}]` | Optimal weights |
| `shadow_costs` | `optional[list[{constraint_id, value: float}]]` | Shadow cost of each binding constraint |
| `risk_decomposition` | `optional[list[{factor, contribution: float, pct_of_total: float}]]` | Risk decomposition if methodology supports it |
| `computation_time_ms` | `integer` | Solver execution time |

---

## Rebalancing Workflow Sequence

The complete end-to-end rebalancing workflow SHALL execute as follows. Each step identifies the responsible service and the inter-service contract used.

| Step | Service | Action | Contract |
|------|---------|--------|----------|
| 1. Trigger | Rebalancing Service | Drift trigger fires (calendar schedule OR drift threshold exceeded per Section 11.6.3) | Internal |
| 2. Drift Detection | Rebalancing Service | Compute current-vs-target drift for all positions using latest Document 14 Position Update contract | Document 11 Position Update contract |
| 3. Materiality Gate | Rebalancing Service | If aggregate drift < 2% of portfolio AUM, exit (no rebalance). Threshold is configurable per portfolio (default: 2%) | Internal |
| 4. Target Computation | Portfolio Construction Service | Run optimization with current positions, covariance matrix, updated constraints. Produce target weights | Portfolio Construction API (above) |
| 5. Risk What-If | Risk Management Service | Simulate proposed target portfolio; compute VaR, CVaR, exposures, stress test results. Verify within all limits | Risk Computation API (below) |
| 6. Position Sizing | Position Sizing Service | Convert target weights to specific position sizes accounting for lot sizes, liquidity, and execution constraints | Position Sizing (Document 15 Section 11.3) |
| 7. Cost Estimation | Rebalancing Service | Estimate transaction costs (commission, spread, market impact) for the trade list | Cost model (Document 15 Section 11.6.5) |
| 8. Cost-Benefit Gate | Rebalancing Service | If estimated costs > estimated risk reduction benefit, defer rebalance. Benefit = reduction in portfolio VaR attributable to the rebalance | Internal |
| 9. Governance Gate | Portfolio Governance Service | If trades affect > 5% of portfolio AUM, require explicit governance approval per Section 11.6.9 | Governance API (Document 15 Section 11.9) |
| 10. Trade Generation | Rebalancing Service | Generate trade list: for each position, delta = target - current | Internal |
| 11. Order Submission | Rebalancing Service | Submit trades as orders to Document 14 Order Management | Document 11 Order Lifecycle Event contract |
| 12. Monitoring | Rebalancing Service | Monitor fill confirmations; if partial fill, recalculate residual drift and decide whether to resubmit | Document 14 order events |

### Material Threshold Definitions

| Threshold | Definition | Default |
|-----------|------------|---------|
| Drift materiality | Aggregate absolute deviation from target weights | 2% of AUM |
| Governance gate | Total notional value of proposed trades | 5% of AUM |
| Cost-benefit minimum | Required risk reduction per unit of transaction cost | 2:1 benefit-to-cost ratio |
| Partial fill threshold | Minimum fill percentage to accept without resubmitting | 90% of requested quantity |

---

## Risk Computation API Contract

### Request

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `portfolio_id` | `portfolio_id` | Yes | Target portfolio |
| `metric_types` | `list[enum{"PARAMETRIC_VAR","HISTORICAL_VAR","MONTE_CARLO_VAR","CVAR","FACTOR_EXPOSURE","LIQUIDITY","STRESS_TEST","DRAWDOWN","CONCENTRATION","FULL_SUITE"}]` | Yes | Requested metrics |
| `as_of` | `timestamp` | No | Computation timestamp (default: now) |
| `hypothetical_positions` | `optional[list[{instrument_id, quantity}]]` | No | If provided, compute risk for hypothetical portfolio (what-if mode) instead of current positions. Used by pre-trade risk checks and rebalancing step 5 |
| `parameters` | `dict[string, any]` | No | Metric-specific parameters (confidence level, horizon, path count) |

### Response

| Field | Type | Description |
|-------|------|-------------|
| `computation_id` | `uuid` | Unique computation identifier |
| `as_of` | `timestamp` | Actual computation timestamp |
| `metrics` | `list[{type: string(32), value: float, unit: string(16), limit_utilization_pct: optional[float], model_version: string(16), computation_time_ms: integer}]` | Individual metric results. Limit utilization is the percentage of the applicable risk limit consumed |
| `aggregated` | `{total_var: float, total_cvar: float, total_exposure: float, var_utilization_pct: float}` | Portfolio-level aggregates in base currency |

### Metric Parameter Defaults

| Metric | Parameter | Default |
|--------|-----------|---------|
| Parametric VaR | confidence_level | 0.99 |
| Parametric VaR | horizon | 1 (day) |
| Historical VaR | window_days | 500 |
| Historical VaR | confidence_level | 0.99 |
| Monte Carlo VaR | path_count | 10000 |
| Monte Carlo VaR | confidence_level | 0.99 |
| Monte Carlo VaR | horizon_days | 1 |
| CVaR | tail_percentile | 0.01 (1% tail beyond VaR) |
| Stress Test | scenario_set | "STANDARD" (platform-defined standard scenarios) |

---

## Multi-Currency Specification

### Base Currency

Every portfolio SHALL declare a base currency in its configuration:

| Config Key | Type | Default | Description |
|-----------|------|---------|-------------|
| `portfolio.base_currency` | `currency_code` | `"USD"` | Portfolio base currency for all aggregations and reporting |

### FX Rate Sourcing

FX rates SHALL be sourced from Document 11 Gold layer FX datasets:

| Parameter | Specification |
|-----------|---------------|
| Data source | Document 11 Gold FX datasets (contract: `contract://market/fx/gold_fx_rates/v1`) |
| Refresh frequency | <= 5 minutes intraday; daily fix rate also available |
| Rate type | Mid-rate for valuation; bid/ask for liquidation P&L estimation |
| Failover | If primary FX feed unavailable, fallback to previous close rate within 30 seconds; flag as ESTIMATED |

### Conversion Timing

| Operation | Conversion Timing | Rate Used |
|-----------|------------------|-----------|
| Position valuation (market value) | At valuation computation time | Latest mid-rate |
| P&L computation | At P&L computation time | Transaction-date rate for realized P&L; latest rate for unrealized P&L |
| Risk computation | At risk computation time | Latest rate for all exposures |
| Attribution | At period close | Period-end rate for end-of-period exposures; weighted-average rate for intra-period flows |

### Cross-Currency Aggregation

All portfolio-level metrics SHALL be reported in base currency:

1. Non-base-currency positions converted at prevailing FX rate
2. P&L components tracked in BOTH local currency and base currency
3. Risk metrics (VaR, CVaR) include FX risk as a risk factor in the covariance matrix
4. Attribution decomposes currency effects separately from asset selection effects

### Currency-Hedged Positions

Positions with explicit currency hedging SHALL track:

| Field | Type | Description |
|-------|------|-------------|
| `hedge_ratio` | `float` | Percentage of currency exposure hedged (0.0 to 1.0) |
| `hedge_instrument` | `instrument_id` | Hedging instrument (e.g., FX forward, currency future) |
| `hedge_pnl` | `decimal(20,4)` | P&L attributable to the hedge |
| `unhedged_exposure` | `decimal(20,4)` | Remaining currency exposure in base currency |

---

## Attribution Output Format

### Brinson Attribution Result

| Field | Type | Description |
|-------|------|-------------|
| `attribution_id` | `uuid` | Unique attribution run identifier |
| `period_start` | `timestamp` | Start of attribution period |
| `period_end` | `timestamp` | End of attribution period |
| `methodology` | `string(32)` | `"BRINSON"` |
| `total_return` | `float` | Portfolio total return for period |
| `benchmark_return` | `float` | Benchmark total return for period |
| `excess_return` | `float` | Portfolio - benchmark return |
| `allocation_effect` | `float` | Return from sector/country allocation decisions |
| `selection_effect` | `float` | Return from security selection within sectors |
| `interaction_effect` | `float` | Cross-product of allocation and selection |
| `currency_effect` | `float` | Return from currency movements |
| `residual` | `float` | Unexplained return |
| `sector_details` | `list[{sector, portfolio_weight, benchmark_weight, allocation_effect, selection_effect, total_effect}]` | Per-sector decomposition |

### Factor Attribution Result

| Field | Type | Description |
|-------|------|-------------|
| `attribution_id` | `uuid` | Unique attribution run identifier |
| `methodology` | `string(32)` | `"FACTOR"` |
| `factor_returns_source` | `uri` | D-8 contract reference to factor return time series |
| `regression_methodology` | `string(32)` | `"TIME_SERIES_REGRESSION"` (portfolio returns on factor returns) |
| `alpha` | `float` | Regression intercept (skill return) |
| `r_squared` | `float` | Model fit |
| `factor_contributions` | `list[{factor_name, factor_return, factor_exposure, contribution, t_statistic}]` | Per-factor decomposition |
| `specific_return` | `float` | Return not explained by factors |

### Multi-Period Linking

Multi-period attribution SHALL use the GRAP (Groupe de Recherche en Attribution de Performance) geometric linking methodology to preserve additive property across periods. Single-period arithmetic results SHALL be geometrically linked per GRAP to produce multi-period attribution that sums to the compound excess return.

---

## Compliance Rule Engine Specification

The compliance rule engine SHALL provide pre-trade and post-trade compliance checking:

| Parameter | Specification |
|-----------|---------------|
| Pre-trade check latency | <= 50ms p95 (within Document 14 pre-trade risk budget) |
| Post-trade check latency | <= 5 minutes after trade confirmation |
| Rule storage | Version-controlled rule library |
| Rule priority | 1. Regulatory (highest), 2. Mandate, 3. Internal (lowest) |
| Breach response (pre-trade) | Block trade, record violation attempt |
| Breach response (post-trade) | Alert compliance officer, record violation, trigger remediation workflow |

### Supported Regulatory Frameworks

| Framework | Jurisdiction | Rule Examples |
|-----------|-------------|---------------|
| UCITS | EU | 5/10/40 diversification limits, eligible assets, concentration |
| 40 Act | US | Diversification (75-5-10), concentration, leverage limits |
| AIFMD | EU | Leverage limits, liquidity management, risk management |
| MiFID II | EU | Product governance, suitability, best execution |
| Custom | Per mandate | Investment guidelines, exclusion lists, ESG constraints |

### Rule Versioning

Compliance rules SHALL be versioned with semantic versioning. Rule changes SHALL pass through a governance approval workflow before activation. A rule change log SHALL maintain complete history of all rule modifications.

---

**End of Document 15 — Portfolio Management Architecture**
