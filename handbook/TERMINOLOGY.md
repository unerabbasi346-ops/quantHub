# Terminology

## Quant Hub

The trading strategy research and execution platform. All architecture documents define the Quant Hub platform. The canonical name is "Quant Hub" (with space), never "QuantHub."

---

## Strategy

A governed trading strategy that consumes platform data, features, models, and infrastructure to generate trading signals and portfolio allocations. Strategies are external to platform architecture per P-1. Strategy-specific configurations, feature definitions, hyperparameters, signal definitions, and portfolio weights are defined as strategy-level configurations that reference but do not alter platform architecture.

---

## Dataset

A governed collection of related data with a globally unique identifier, version, and complete metadata per Document 11. Every dataset possesses lineage, quality certification, and lifecycle state. Datasets reside in the Bronze, Silver, or Gold Zone of the Enterprise Data Lake per D-1.

---

## Data Product

A governed, published dataset in the Gold Zone, certified for consumption by downstream consumers including feature engineering pipelines, ML training processes, research workspaces, and trading infrastructure. Data Products are published through defined contracts per D-8 and are immutable after publication per D-7.4.2.

---

## Feature Store

The governed storage zone within the Enterprise Data Lake (Document 11) where computed features are persisted as governed data assets. Feature engineering architecture — how features are computed, validated, and registered — is owned by Document 12 Section 8.2. Feature storage — where computed features reside — is owned by Document 11 per D-7.1.2.

---

## Metadata Registry

The single authoritative source of platform metadata per D-3. The Enterprise Metadata Registry governs dataset identity, ownership, lifecycle, governance, operational metadata, and relationship information. No subsystem shall maintain independent authoritative metadata outside the Registry. Formerly referred to as "Metadata Catalog" — "Metadata Registry" is the canonical term.

---

## Data Contract

A formal, versioned interface definition between data producers and consumers per D-8. Every contract includes schema definition, semantic definition, quality requirements, availability requirements, performance requirements, security requirements, lifecycle requirements, governance requirements, ownership information, and version information. Published contract versions are immutable.

---

## Research Workspace

An isolated, reproducible computational environment for research activities per Document 13 and R-5. Workspaces are provisioned through containerized environments with pinned dependencies. Workspace isolation is enforced at compute, network, and data levels. Research Workspace Architecture is defined in Document 13 Section 9.2.

---

## Risk Engine

The runtime component that computes portfolio-level risk metrics including VaR, CVaR, volatility, factor exposures, and stress test results. The Risk Engine consumes position data from Document 14 Trading Infrastructure and provides risk assessments to Document 15 Portfolio Management. Risk Management Architecture is defined in Document 15 Section 11.5.

**Distinction — Runtime Component vs. Architectural Domain:** The "Risk Engine" is a runtime computational service that consumes position data and produces risk metrics per Port-4. "Risk Management Architecture" (Document 15, Section 11.5) is the architectural domain governing risk measurement methodology, risk limits, risk governance, and the integration of risk assessment into portfolio management. Cross-document references shall use "Risk Management" (Document 15) when discussing architectural governance and "Risk Engine" when discussing runtime risk computation.

---

## Portfolio Engine

The runtime component that executes portfolio construction, position sizing, capital allocation, and rebalancing per Document 15. The Portfolio Engine consumes trading signals from Document 14, risk assessments from the Risk Engine, and market data from Document 11. Portfolio Management Platform Architecture is defined in Document 15.

**Distinction — Runtime Component vs. Architectural Domain:** The "Portfolio Engine" is a runtime computational service that executes portfolio construction, position sizing, and rebalancing per Port-1. "Portfolio Management Platform Architecture" (Document 15) is the architectural domain governing the complete portfolio lifecycle. Cross-document references shall use "Portfolio Management" (Document 15) when discussing architectural governance and "Portfolio Engine" when discussing runtime portfolio computation.

---

## Lakehouse

The analytical computational layer built upon the Enterprise Data Lake per Document 11 Section 7.2. The Lakehouse provides ACID-compliant transaction semantics through Multi-Version Concurrency Control (MVCC), governed snapshot management with time-travel queries, and processing isolation between batch, streaming, and incremental workloads. The canonical term is "Lakehouse" or "Enterprise Lakehouse" — "Data Lakehouse" is deprecated.

---

---

## Abbreviations

The following abbreviations are defined for use across all handbook documents. Each document shall expand the abbreviation in parentheses on first use, then may use the abbreviation alone for subsequent references.

---

### ACID

Atomicity, Consistency, Isolation, Durability. Transaction guarantees provided by the Enterprise Lakehouse per Document 11 Section 7.2.

---

### API

Application Programming Interface. A defined interface for programmatic interaction between platform components.

---

### Black-Litterman

A portfolio construction methodology developed by Fischer Black and Robert Litterman that combines prior market equilibrium returns (derived from a CAPM-based reverse optimization) with investor views (expressed as absolute or relative return expectations with confidence levels) to produce a posterior expected return vector. The methodology addresses the instability of mean-variance optimization by providing stable, intuitive portfolio weights. Referenced in Document 15 Section 11.2.4.

---

### Brinson Attribution

A performance attribution methodology (named for Gary Brinson) that decomposes portfolio excess return into three additive effects: **Allocation Effect** (return from overweighting/underweighting sectors relative to the benchmark), **Selection Effect** (return from selecting individual securities within a sector that outperform the sector benchmark), and **Interaction Effect** (cross-product of allocation and selection decisions). Referenced in Document 15 Section 11.7.

---

### CVaR

Conditional Value at Risk (also known as Expected Shortfall). The expected loss given that the loss exceeds the VaR threshold. Used in portfolio risk management per Document 15.

---

### CUDA

Compute Unified Device Architecture. NVIDIA's parallel computing platform and application programming interface (API) that allows software to use NVIDIA GPUs for general-purpose processing. The Quant Hub ML platform prohibits direct use of CUDA-specific libraries in model code per GPU vendor lock-in prevention requirements (Document 12 Section 8.1.3). ML code shall use framework-level APIs (PyTorch, JAX) that abstract GPU vendor specifics.

---

### DAG

Directed Acyclic Graph. The computation graph representation used for pipeline orchestration, workflow scheduling, and dependency management across the Quant Hub platform.

---

### DR

Disaster Recovery. The governed process for recovering platform operations following a catastrophic failure per Document 11 Section 7.5.

---

### EDA

Exploratory Data Analysis. The systematic investigation of dataset characteristics, distributions, relationships, and quality prior to formal modeling per Document 13.

---

### ELT

Extract, Load, Transform. A data processing pattern where data is extracted from sources, loaded into the platform, and transformed within the platform environment per Document 11 Part 3.

---

### ETL

Extract, Transform, Load. A data processing pattern where data is extracted from sources, transformed externally, and loaded into the platform per Document 11 Part 3.

---

### GPU

Graphics Processing Unit. A compute accelerator used for ML training and inference workloads. Platform architecture shall remain independent of specific GPU vendors per P-3 and M-6.

---

### HHI

Herfindahl-Hirschman Index. A measure of market concentration computed as the sum of squared market shares. In portfolio management, HHI measures portfolio concentration at the instrument or strategy level. Higher values indicate greater concentration risk. Used in Document 15 Section 11.3.4 (risk-based position sizing) and Section 11.5.3 (risk measurement).

---

### HA

High Availability. The architectural property ensuring platform services remain operational with minimal downtime. HA is measured through Service Level Objectives (SLOs) per Document 11 Section 7.13.

---

### IaC

Infrastructure as Code. The practice of defining and managing infrastructure through machine-readable definition files rather than manual configuration per Document 11.

---

### IAM

Identity and Access Management. The architectural domain governing authentication, authorization, and identity lifecycle across the Quant Hub platform per Document 11 Section 7.12.

---

### Implementation Shortfall

An execution algorithm and transaction cost measurement methodology introduced by Perold (1988). Implementation shortfall measures the difference between the theoretical portfolio return if all trades executed at the decision price and the actual return achieved after execution costs. It decomposes into: delay cost, price impact, opportunity cost, and fixed costs. Referenced in Document 14 Section 10.8 (execution management algorithms).

---

### Kelly Criterion / Fractional Kelly

A position sizing methodology derived from information theory (Kelly, 1956). The Kelly criterion determines the optimal fraction of capital to allocate to a bet that maximizes long-term growth rate. In portfolio management, the full Kelly bet size is `f* = (p*b - q) / b` where p = probability of winning, q = probability of losing, b = net fractional odds. Fractional Kelly (a reduced fraction of the full Kelly bet) is commonly used to reduce volatility and estimation error sensitivity. Referenced in Document 15 Section 11.3.6.

---

### LIME

Local Interpretable Model-agnostic Explanations. A technique for explaining individual predictions of ML models by approximating the model locally with an interpretable surrogate per Document 12 Section 8.5.

---

### ML

Machine Learning. The architectural domain covering model training, validation, serving, and governance per Document 12. Not to be confused with the invariant prefix M- (M-1 through M-8).

---

### MVCC

Multi-Version Concurrency Control. The concurrency mechanism enabling simultaneous reads and writes without blocking in the Enterprise Lakehouse per Document 11 Section 7.2.

---

### ONNX

Open Neural Network Exchange. An open standard format for representing machine learning models that enables interoperability between ML frameworks (PyTorch, TensorFlow, scikit-learn, etc.). The Quant Hub ML platform requires production models to be exportable to ONNX format as part of GPU vendor lock-in prevention (Document 12 Section 8.1.3). ONNX compatibility ensures models can be deployed across different inference runtimes without framework-specific dependencies.

---

### P&L

Profit and Loss. The financial outcome of trading activity calculated from position changes, executed trades, and market movements. P&L data flows from Document 14 Trading Infrastructure to Document 15 Portfolio Management.

---

### PII

Personally Identifiable Information. Data that can identify an individual. PII handling is governed by Document 11 Section 7.12 and Document 12 Section 8.11.

---

### PTP / Precision Time Protocol

IEEE 1588-2019 standard for clock synchronization across networked systems, providing microsecond-precision time synchronization. In the Quant Hub trading platform (Document 14), PTP-synchronized clocks are required for: market data timestamp normalization (±100us from master, ±50us exchange skew), latency measurements (signal-to-order, order-to-exchange), and audit trail ordering. PTP grandmaster clocks with GPS holdover provide the primary time source, with NTP fallback (±1ms).

---

### RPO

Recovery Point Objective. The maximum acceptable data loss measured in time. RPO defines the point in time to which data must be recoverable after a disaster per Document 11 Section 7.5.

---

### RTO

Recovery Time Objective. The maximum acceptable time to restore service after a disruption. RTO defines the target duration from disaster declaration to operational recovery per Document 11 Section 7.5.

---

### SHAP

SHapley Additive exPlanations. A game-theoretic approach to explaining ML model predictions by computing feature contribution values per Document 12 Section 8.5.

---

### Sharpe Ratio

A risk-adjusted return measure developed by William Sharpe (1966), computed as `(Portfolio Return − Risk-Free Rate) / Standard Deviation of Portfolio Return`. The Sharpe ratio is the primary performance metric used in trading platform validation: backtesting (Document 14 Section 10.2), walk-forward analysis (§10.4), paper trading (§10.5), and live trading performance monitoring. Higher values indicate better risk-adjusted returns.

---

### SLA

Service Level Agreement. A formal commitment defining the expected service characteristics agreed between provider and consumer. SLAs are derived from documented SLOs and include remediation for violations.

---

### SLI

Service Level Indicator. A quantitative measure of a service characteristic. SLIs are the raw measurements used to compute SLO compliance per Document 11 Section 7.13.

---

### SLO

Service Level Objective. A target value or range for an SLI over a measurement window. SLOs define the acceptable operational threshold for platform services per Document 11 Section 7.13.

---

### VaR

Value at Risk. A statistical measure of the maximum potential loss over a defined time horizon at a given confidence level. Used in portfolio risk management per Document 15 Section 11.5.

---

### VWAP / TWAP

Volume-Weighted Average Price / Time-Weighted Average Price. Execution algorithms that slice orders over time to achieve average pricing. VWAP targets the volume-weighted average price by distributing order quantity proportionally to historical volume profiles. TWAP targets the time-weighted average price by distributing order quantity evenly over time intervals. Both minimize market impact by avoiding large discrete trades. Referenced in Document 14 Section 10.8 (execution algorithm selection).
