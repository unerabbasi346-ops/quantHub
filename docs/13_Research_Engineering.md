Quant Hub Engineering Handbook
Document 13 — Research Engineering Architecture (Part 9)

**STATUS: COMPLETED & FROZEN — 2026-06-30**

This document is the canonical architecture specification for the Quant Hub research platform. It shall reference but not redefine frozen Document 11 (Data Engineering) and Document 12 (Machine Learning Engineering) architectures. It shall comply with all invariants in handbook/ARCHITECTURAL_INVARIANTS.md. It shall remain strategy-independent and technology-independent.

---

# 9.1 Research Platform Architecture

## 9.1.1 Purpose

The Research Platform Architecture defines the canonical framework for quantitative research lifecycle management within the Quant Hub platform.

The research platform governs the complete quantitative research lifecycle: hypothesis formulation, exploratory data analysis, research experiment organization, statistical validation, knowledge capture, collaboration, research governance, artifact management, and the governed promotion of validated research findings into downstream production platforms including ML Engineering (Document 12), Strategy Development and Backtesting (Document 14), and Portfolio Management including Risk Management (Document 15, Section 11.5).

The research platform sits between the data and ML platforms (Documents 11 and 12) and the production trading platforms (Documents 14 and 15), governing the critical transition from exploration to production. It shall ensure that only validated, reviewed, and governed research findings enter production systems.

The research platform is strategy-agnostic per P-1. It shall serve every quantitative strategy uniformly without embedding strategy-specific logic, domain assumptions, or signal priors within platform infrastructure. No research workspace, hypothesis template, validation rule, analysis methodology, or knowledge capture mechanism shall assume the existence of any specific trading strategy.

Quantitative research shall be treated as a first-class platform capability with governed infrastructure, reproducibility guarantees, and production promotion gates.

---

## 9.1.2 Scope

The Research Platform Architecture applies to every research activity, asset, workspace, and process within the Quant Hub platform.

Coverage includes:

- Research Workspace Architecture
- Hypothesis Management
- Research Experiment Organization
- Exploratory Data Analysis
- Statistical Analysis Framework
- Research Reproducibility
- Knowledge Management
- Research Collaboration
- Research Artifact Management
- Research Governance
- Research Lifecycle
- Research-to-Production Promotion
- Research Security
- Research Observability
- Research Infrastructure

The following topics are intentionally excluded because they are defined and frozen within other handbook documents:

| Topic | Frozen Document | Reference |
|-------|----------------|-----------|
| Data storage (Bronze/Silver/Gold) | Document 11 | D-7.1.1, F-1, D-1 |
| Data quality validation | Document 11 | D-7.9.5, D-7.9.6, D-7 |
| Data lineage infrastructure | Document 11 | D-7.8.1, D-7.8.4, D-5 |
| Data governance (stewardship, policy) | Document 11 | D-7.11.1, D-7.11.6, D-10 |
| Data security (encryption, IAM) | Document 11 | D-7.12.5, D-7.12.6, D-9 |
| Data lifecycle states | Document 11 | D-7.4.1, D-6 |
| Data contracts | Document 11 | D-7.10.1, D-7.10.5, D-8 |
| General platform observability | Document 11 | D-7.13.5, D-7.13.6 |
| Feature engineering | Document 12 | Section 8.2 |
| ML experiment tracking | Document 12 | Section 8.3 |
| Model training | Document 12 | Section 8.4 |
| Model validation | Document 12 | Section 8.5 |
| Model registry | Document 12 | Section 8.6 |
| Model serving | Document 12 | Section 8.7 |
| ML governance | Document 12 | Section 8.10 |
| ML lifecycle | Document 12 | Section 8.12 |
| API specification | Document 10 | N/A |
| Frontend/back-end architecture | Documents 07, 08 | N/A |
| Database architecture | Document 09 | N/A |
| Strategy development | Document 14 | N/A |
| Backtesting execution | Document 14 | N/A |
| Portfolio management | Document 15 | N/A |

No production research output shall bypass enterprise governance per P-8 and P-17.

---

## 9.1.3 Design Goals

The Research Platform Architecture shall satisfy the following objectives:

- Research Reproducibility — Every published research finding shall be reproducible given identical data, code, and environment. Reproducibility shall not depend on mutable external state. Extends P-13.
- Strategy Independence — The research platform shall serve all strategies identically per P-1.
- Governed Research-to-Production Promotion — No research finding shall enter production without passing formal governance gates per P-8 and P-17.
- Statistical Rigor — The platform shall provide statistical infrastructure preventing common analytical pitfalls including p-hacking, multiple testing issues, and selective reporting.
- Knowledge Preservation — Research knowledge shall be captured, organized, discoverable, and preserved as enterprise assets per P-17.
- Collaboration Enablement — The platform shall support governed multi-user research collaboration with role-based access and peer review.
- Enterprise Scalability — The platform shall scale horizontally to support growing research activity per P-12.

---

## 9.1.4 Architectural Principles

The Research Platform Architecture shall follow the following principles, which extend platform invariants P-1 through P-18 with research-specific semantics.

### Research Reproducibility by Design

Every published research finding, analysis result, and statistical conclusion shall be reproducible given identical data, code, and environment. Reproducibility shall not depend on mutable external state. This principle extends P-13 (Deterministic Processing).

### Hypothesis-Experiment Separation

Research hypotheses (what is being tested) shall remain separate from research experiments (how testing is executed). Hypothesis definitions shall be governed independently of experiment implementations. This principle extends P-9 (Separation of Concerns).

### Governed Research-to-Production Promotion

No research finding shall enter production (strategy, model, or portfolio construction) without passing formal governance gates. Research artifacts shall be validated, reviewed, and approved before production promotion. This principle extends P-17 (Enterprise Governance) and P-8 (No Bypass Architecture).

### Knowledge as Enterprise Asset

Research knowledge — hypotheses, findings, analyses, methodologies, and insights — shall be treated as governed enterprise assets. Knowledge shall be captured, organized, discoverable, and preserved. This principle extends P-17 (Enterprise Governance).

### Independent Research Workspaces

Research workspaces shall be isolated, reproducible computational environments. Workspace configuration shall not embed assumptions about specific tools, libraries, or infrastructure per P-3 (Technology Independence).

### Strategy Independence (Research Domain)

Research hypotheses, analysis methodologies, and knowledge artifacts shall remain independent of any specific trading strategy. Research platform infrastructure shall serve all strategies without strategy-specific customization. This principle extends P-1.

### Multiple Testing Awareness

The research platform shall provide statistical infrastructure for multiple testing correction, p-hacking prevention, and false discovery rate control. Research governance shall require appropriate statistical rigor per the research risk classification.

---

## 9.1.5 Research Platform Overview

The Research Platform Architecture defines a layered service model consuming governed data from Document 11, features and models from Document 12, and producing validated research findings for promotion to production platforms.

Logical research lifecycle:

```
Document 11 Data Platform (Gold Layer)
Document 12 ML Platform (Features, Models)
                    ↓
           Ideation & Hypothesis
                    ↓
         Exploratory Data Analysis
                    ↓
          Research Experimentation
                    ↓
          Statistical Validation
                    ↓
          Peer Review & Publication
                    ↓
         Promotion to Production:
    ML Engineering (Doc 12)    Strategy Development (Doc 14)
    Risk Management (Doc 15, Section 11.5)   Portfolio Management (Doc 15)
```

Every stage represents a governed research activity with defined contracts, reproducibility evidence, and integration with Document 11 infrastructure for storage, metadata, lineage, governance, security, and observability.

The research platform shall communicate through standardized event contracts per P-4. Every hypothesis registration, experiment completion, finding publication, and promotion decision shall be communicated as governed events.

Integration with frozen platforms shall occur through published, governed interfaces:

- Data Access — Research workspaces consume governed data through Document 11 contracts per D-8. Research datasets are temporary working copies scoped to research projects.
- Feature Store — Researchers discover and consume features from Document 12 Feature Engineering Architecture for hypothesis testing; may prototype new feature definitions.
- ML Platform — Researchers consume model predictions and metadata for analysis; research experiments are distinct from ML experiments (Section 8.3) while sharing reproducibility principles.
- Metadata — Research artifacts registered in Document 11 Metadata Registry per D-7.7.2 with research-specific metadata domains.
- Lineage — Research activities record lineage from input data through analysis to published findings per D-5.
- Governance — Research governance workflows integrate with Document 11 governance infrastructure per D-7.11.
- Security — Research security controls integrate with Document 11 Security Architecture per D-7.12.
- Observability — Research metrics flow through Document 11 Observability infrastructure per D-7.13.

---

## 9.1.6 Platform Services

The research platform shall be composed of the following governed services.

Service responsibilities include:

- Research Workspace Service — Provisioning, configuration, resource management, lifecycle of research computational environments
- Hypothesis Management Service — Hypothesis registration, tracking, validation, lifecycle, and search
- Research Experiment Service — Experiment definition, execution, versioning, lineage, and governance
- Exploratory Data Analysis Service — Governed EDA sessions, insight capture, visualization management
- Statistical Analysis Service — Standardized statistical testing, multiple testing correction, power analysis, reporting
- Reproducibility Service — Automated reproducibility verification, evidence management, tier certification
- Knowledge Management Service — Knowledge capture, taxonomy, discovery, lifecycle, and governance
- Collaboration Service — Workspace sharing, peer review, co-authoring, access management
- Artifact Management Service — Research artifact storage, versioning, discovery, lifecycle
- Research Governance Service — Approval workflows, review management, compliance, audit
- Promotion Service — Research-to-production promotion gates, evidence packaging, destination integration

Every service shall be independently deployable, scalable, and governed per P-10 (Modular Design) and P-11 (Loose Coupling).

Services shall communicate through standardized event contracts per P-4.

No service shall duplicate responsibilities owned by Document 11 or Document 12 services per P-9 (Separation of Concerns).

---

## 9.1.7 Integration Architecture

The research platform shall integrate with surrounding platforms through governed interfaces.

Integration domains include:

- Data Platform Integration — Research workspaces consume governed data through Document 11 contracts. Research datasets are temporary working copies scoped to projects. No direct storage access.
- ML Platform Integration — Researchers consume features and model predictions through Document 12 interfaces. Research experiments are distinct from ML experiments. Research-to-model promotion follows governed gates.
- Metadata Integration — Research artifacts registered in Document 11 Metadata Registry with research-specific domains.
- Lineage Integration — Research lineage events extend Document 11 lineage graph with research-specific node types.
- Governance Integration — Research governance workflows integrate with Document 11 governance infrastructure. Research approval gates are distinct from data and model approval gates.
- Security Integration — Research authentication and authorization through enterprise IAM. Workspace isolation extends Document 11 security controls.
- Observability Integration — Research metrics, logs, and traces flow through Document 11 observability pipeline.
- Event Platform Integration — Research events published through enterprise Event Platform per P-4.

Integration shall preserve governance boundaries per P-8. Security controls shall not be bypassed through integration paths per D-9.

Every integration shall be governed by a Data Contract per D-8.

---

## 9.1.8 Research Event Model

The research platform shall emit standardized events for every governed research operation.

Event types include:

- Hypothesis Registered
- Hypothesis Status Changed
- Experiment Started
- Experiment Completed
- Experiment Failed
- Finding Published
- Peer Review Requested
- Peer Review Completed
- Knowledge Artifact Created
- Knowledge Artifact Updated
- Promotion Requested
- Promotion Approved
- Promotion Rejected
- Promotion Rolled Back
- Workspace Provisioned
- Workspace Suspended
- Workspace Archived
- Collaboration Invitation Sent
- Collaboration Access Granted
- Governance Decision Recorded

Every event shall include event identifier, event type, timestamp, source service, correlation identifier, resource identifier, actor identity, event payload, and event version.

Events shall be immutable after publication per P-2. Event contracts shall be versioned and governed per D-8.

---

## 9.1.9 Platform Security Context

The research platform shall implement enterprise security controls extending Document 11 Section 7.12 Data Security Architecture.

Security posture includes:

- Authentication — Every research service access shall be authenticated per D-9. Multi-factor authentication shall be required for privileged operations.
- Authorization — Every authenticated request shall be authorized per D-7.12.4 least privilege principle. Research data access shall be governed by project-scoped authorization.
- Workspace Isolation — Research workspaces shall be isolated per user, project, and data classification. No cross-workspace data leakage.
- Encryption — Research artifacts and workspace data shall be encrypted at rest per D-7.12.5. All research service communication shall be encrypted in transit.
- Audit Logging — Every security-relevant research operation shall generate immutable audit records per P-5.
- IP Protection — Research intellectual property shall be protected through access controls, workspace isolation, and governed data export controls.

Detailed research-specific security controls are defined in Section 9.14 — Research Security Architecture.

---

## 9.1.10 Platform Observability Context

The research platform shall implement enterprise observability extending Document 11 Section 7.13 Data Observability Architecture.

Observability posture includes:

- Metrics — Every research service shall emit standardized metrics per P-15.
- Logging — Every research service shall emit structured logs with correlation identifiers per D-7.13.2.
- Tracing — Distributed tracing shall span research workflows from data access through analysis and publication.
- Health Checks — Every research service shall implement health checks per D-7.13.
- SLOs — Every critical research service shall have defined Service Level Objectives per D-7.13.5.
- Alerting — Research operational alerts shall integrate with enterprise alerting infrastructure per D-7.13.6.

Detailed research-specific observability is defined in Section 9.15 — Research Observability Architecture.

---

## 9.1.11 Platform Governance Context

The research platform shall implement enterprise governance extending Document 11 Section 7.11 Data Governance Architecture.

Governance posture includes:

- Governance by Default — Every research activity shall be governed per P-17.
- Policy as Code — Research governance policies shall be defined, versioned, and enforced as code per D-7.11.2.
- Separation of Duties — Research policy definition, enforcement, and audit shall be separated per D-10.
- Continuous Compliance — Research compliance shall be continuously verified per D-7.11.4.
- Immutable Evidence — Every research governance decision shall produce immutable audit records per D-7.11.5 and P-2.
- Stewardship — Every research project shall have a designated Research Steward extending D-7.11.6.

Detailed research-specific governance is defined in Section 9.11 — Research Governance Architecture.

---

## 9.1.12 Performance Requirements

The Research Platform shall satisfy defined operational performance objectives.

Performance considerations include:

- Workspace Provisioning Latency — Time from workspace request to ready-for-use state
- Hypothesis Registration Latency — Time to register and validate a new hypothesis
- Experiment Execution Support — Concurrent research experiment support
- Statistical Analysis Throughput — Analyses completed per time unit
- Knowledge Discovery Query Performance — Knowledge search and browse response time
- Promotion Processing Time — Time from promotion request to decision
- Collaboration Responsiveness — Real-time collaboration latency

Performance objectives shall be continuously monitored through enterprise metrics per P-15.

---

## 9.1.13 Scalability Strategy

The research platform shall scale horizontally to support research growth per P-12.

Scalability considerations include:

- Researcher Growth — Increasing number of active researchers
- Workspace Growth — Increasing concurrent active workspaces
- Hypothesis Volume Growth — Increasing registered hypotheses
- Experiment Volume Growth — Increasing research experiment count
- Knowledge Volume Growth — Increasing knowledge artifacts
- Collaboration Growth — Increasing concurrent collaborative sessions

Every research service shall support independent horizontal scaling per P-12.

---

## 9.1.14 High Availability

The research platform shall operate with high availability.

Availability shall cover:

- Research Workspace Services
- Hypothesis Management Services
- Experiment Services
- Statistical Analysis Services
- Knowledge Management Services
- Collaboration Services
- Promotion Services

No individual infrastructure component shall constitute a single point of failure per P-16.

Research workspace interruption shall support graceful state preservation and recovery.

---

## 9.1.15 Disaster Recovery

Disaster recovery architecture shall ensure continuity of research operations.

Recovery shall preserve:

- Hypothesis Records
- Experiment Records
- Knowledge Artifacts
- Research Artifacts
- Governance Records
- Collaboration Records
- Promotion Records
- Research Configuration

Recovery shall satisfy enterprise RTO and RPO objectives.

Research artifacts shall be recoverable from Document 11 backup and archive infrastructure per D-7.5 and D-7.6.

---

## 9.1.16 Backup Strategy

The research platform shall integrate with Document 11 backup architecture.

Backup coverage shall include:

- Hypothesis records
- Experiment records and metadata
- Research artifacts
- Knowledge artifacts
- Governance records and approvals
- Promotion evidence
- Research configuration
- Collaboration records

Backup shall comply with Document 11 backup governance per D-7.5.1.

Backup copies shall be immutable after successful creation per D-7.5.3.

---

## 9.1.17 Capacity Planning

Capacity planning shall evaluate:

- Researcher Growth
- Workspace Growth
- Hypothesis Volume Growth
- Experiment Volume Growth
- Knowledge Volume Growth
- Collaboration Session Growth
- Promotion Volume Growth
- Storage Requirements
- Compute Utilization

Infrastructure expansion shall occur before operational service objectives are impacted.

---

## 9.1.18 Operational Monitoring

Research platform services shall be continuously monitored per P-15.

Monitoring domains include:

- Service Health — Availability, response time, error rate for every research service
- Workspace Operations — Active workspaces, provisioning time, resource utilization
- Research Operations — Hypothesis registrations, experiment executions, publication volume
- Collaboration Operations — Active collaborative sessions, peer review throughput
- Knowledge Operations — Knowledge artifact creation rate, discovery query volume
- Promotion Operations — Promotion requests, approval rate, processing time
- Resource Utilization — CPU, memory, storage for research compute resources

Monitoring shall detect and alert on operational anomalies.

---

## 9.1.19 Alert Management

Research platform alerts shall integrate with enterprise alerting per D-7.13.6.

Alert categories include:

- Service Availability Alerts — Research service outage or degradation
- Workspace Failure Alerts — Workspace provisioning or recovery failure
- Experiment Failure Alerts — Research experiment execution failure
- Promotion Failure Alerts — Promotion gate rejection requiring attention
- Collaboration Degradation — Real-time collaboration performance degradation
- Resource Exhaustion Alerts — Compute, memory, or storage capacity limits
- Governance Alerts — Approval timeout, review overdue, certification expiry

Alerts shall include sufficient context for diagnosis.

---

## 9.1.20 Logging Architecture

Every research platform service shall emit structured logs per P-15.

Logging requirements include structured log format, correlation identifiers linking related operations across services, standard log levels, timestamp precision, source identification, retention per enterprise policies, and access controls per enterprise security policies.

Logs shall be immutable after creation per P-2.

---

## 9.1.21 Operational Runbooks

The research platform shall maintain operational runbooks.

Runbook coverage shall include:

- Service Startup Procedures
- Service Shutdown Procedures
- Workspace Recovery
- Experiment Recovery
- Promotion Rollback
- Collaboration Issue Resolution
- Incident Response
- Escalation Procedures

Runbooks shall be versioned, maintained as operational documentation, and accessible during incidents.

---

## 9.1.22 Testing Requirements

The Research Platform Architecture shall satisfy comprehensive testing requirements.

Testing categories include:

- Functional Testing — Every research service function verified against specification
- Integration Testing — Cross-service and cross-platform integration validated
- Performance Testing — Throughput, latency, and concurrency under load
- Scalability Testing — Horizontal scaling behavior under growth conditions
- Failure Testing — Graceful degradation and recovery under component failure
- Security Testing — Authentication, authorization, workspace isolation
- Reproducibility Testing — End-to-end research finding reproducibility verification
- Governance Testing — Policy enforcement, approval workflows, audit completeness

Testing shall verify compliance with all applicable invariants.

---

## 9.1.23 Deployment Architecture

Research platform services shall be deployed using standardized practices: containerized services, immutable deployments with versioning, automated rollback capability, environment parity across development/staging/production, externalized and versioned configuration, and managed credentials through enterprise secret management.

Deployment shall not embed assumptions about specific cloud providers or orchestration platforms per P-18.

---

## 9.1.24 Configuration Management

Research platform configuration shall be centrally managed and versioned with externalized configuration, version control for every change, explicit environment-specific overrides, immutable audit trail per P-5, validation before application, and automated rollback.

Research-specific configuration (workspace templates, hypothesis templates, statistical analysis configurations) shall be governed through their respective platform services with immutable version history.

---

## 9.1.25 Integration Testing

Cross-platform integration shall be validated through comprehensive integration testing.

Integration testing shall verify:

- Data Platform Integration — Research platform correctly consumes governed data from Document 11
- ML Platform Integration — Research platform correctly consumes features and models from Document 12
- Metadata Integration — Research artifacts correctly registered in Document 11 Metadata Registry
- Lineage Integration — Research lineage events correctly recorded in Document 11 lineage graph
- Governance Integration — Research governance decisions correctly recorded in Document 11 audit infrastructure
- Security Integration — Research authentication and authorization correctly enforced through enterprise IAM
- Observability Integration — Research metrics correctly flowing through Document 11 observability pipeline
- Event Integration — Research events correctly published through enterprise Event Platform

Integration testing shall verify that no integration path bypasses governance, security, or quality controls per P-8.

---

## 9.1.26 Platform Certification

The research platform shall be formally certified before production authorization.

Certification shall verify:

- Architecture Compliance — Every research service satisfies its documented specification
- Invariant Compliance — Every research service complies with applicable invariants
- Integration Validation — All cross-platform integrations function correctly
- Security Verification — Security controls including workspace isolation are effective
- Performance Validation — Performance objectives are satisfied
- Governance Readiness — Governance workflows, peer review, and promotion gates are operational
- Reproducibility Verification — Research reproducibility guarantees are validated
- Disaster Recovery Readiness — Recovery procedures are tested

Certification records shall be immutable per P-2.

---

## 9.1.27 Risks

The Research Platform Architecture shall continuously identify, evaluate, and mitigate architectural risks.

Primary architectural risks include:

- Reproducibility Failure — Inability to reproduce published research findings due to missing environment, data, or code version information
- Research Data Leakage — Cross-workspace data leakage violating data classification boundaries
- Promotion Bypass — Research findings entering production without governance approval
- Statistical Misconduct — P-hacking, selective reporting, or multiple testing abuse undetected by platform controls
- Knowledge Loss — Loss of research knowledge artifacts due to inadequate preservation
- Collaboration Conflict — Concurrent modification conflicts causing data loss in collaborative workspaces
- Workspace Resource Exhaustion — Compute resource contention degrading research productivity
- Integration Failure — Breakdown in research-to-data-platform or research-to-ML-platform integration

Each identified risk shall include risk identifier, risk classification, severity, probability, business impact, detection method, mitigation strategy, recovery procedure, responsible owner, and review frequency.

---

## 9.1.28 Acceptance Criteria

The Research Platform Architecture shall be considered complete when the platform demonstrates:

- Complete research service inventory with defined responsibilities per Section 9.1.6
- Integration with every Document 11 and Document 12 platform domain
- Standardized research event model
- Security controls extending Document 11 Section 7.12 with workspace isolation
- Observability extending Document 11 Section 7.13
- Governance extending Document 11 Section 7.11
- Performance objectives satisfied
- Horizontal scalability demonstrated
- High availability with no single point of failure
- Disaster recovery readiness
- Comprehensive testing coverage
- Platform certification completed
- Strategy independence verified — no strategy-specific logic in any platform component
- Technology independence verified — no vendor-specific assumptions
- Compliance with all applicable invariants
- No redefinition of frozen Document 11 or Document 12 architectures

Every acceptance criterion shall be objectively verifiable through architecture validation procedures.

---

## 9.1.29 Cross References

This section shall be read together with:

- Section 9.2 — Research Workspace Architecture
- Section 9.3 — Hypothesis Management Architecture
- Section 9.4 — Research Experiment Architecture
- Section 9.5 — Exploratory Data Analysis Architecture
- Section 9.6 — Statistical Analysis Framework
- Section 9.7 — Research Reproducibility Architecture
- Section 9.8 — Knowledge Management Architecture
- Section 9.9 — Research Collaboration Architecture
- Section 9.10 — Research Artifact Management
- Section 9.11 — Research Governance Architecture
- Section 9.12 — Research Lifecycle Architecture
- Section 9.13 — Research-to-Production Promotion Architecture
- Section 9.14 — Research Security Architecture
- Section 9.15 — Research Observability Architecture
- Section 9.16 — Research Infrastructure Architecture
- Document 11 — Data Engineering & Data Pipeline Architecture (per D-7.1 through D-7.13)
- Document 12 — Machine Learning Engineering Architecture (per Sections 8.1 through 8.12)
- Document 10 — API Specification
- Document 09 — Database Architecture
- Document 03 — Technology Stack
- Document 02 — System Architecture
- Document 00 — Project Constitution
- handbook/ARCHITECTURAL_INVARIANTS.md (per P-1 through P-18, D-1 through D-10, M-1 through M-8)

---

## 9.1.30 Integration Validation

The complete research platform shall undergo end-to-end integration validation.

Integration validation shall verify:

- End-to-End Research Pipeline — Hypothesis registration through experiment execution, validation, peer review, and promotion
- Data Platform Integration — Research workspaces correctly consume governed data from Document 11 Gold layer
- ML Platform Integration — Research correctly consumes features and models from Document 12
- Promotion Pipeline — Research findings correctly promoted to destination production platforms
- Governance Pipeline — Research approval workflow through audit record production
- Reproducibility Verification — Research findings verified as reproducible
- Cross-Platform Contract Compliance — Every integration contract verified
- Invariant Compliance — All applicable invariants verified end-to-end

Every integration validation result shall be immutable per P-2.

Validation failures shall prevent production authorization.

---

# End of Section

---

# 9.2 Research Workspace Architecture

## 9.2.1 Purpose

The Research Workspace Architecture defines the canonical framework for governed computational environments within the Quant Hub research platform.

Research workspaces shall provide isolated, reproducible, and governed environments for data exploration, statistical analysis, hypothesis testing, and research experimentation. Every workspace shall be a governed asset with defined lifecycle, resource allocation, data access boundaries, and reproducibility guarantees.

Workspaces shall not embed assumptions about specific tools, libraries, or infrastructure per P-3 (Technology Independence). Workspace configuration shall be fully specified and versioned for reproducibility.

Workspaces are distinct from ML training environments (Document 12 Section 8.4). Research workspaces are interactive, exploratory environments. ML training is batch pipeline execution. Both consume governed data through Document 11 contracts per D-8.

---

## 9.2.2 Scope

The Research Workspace Architecture applies to every research computational environment within the Quant Hub platform.

Coverage includes:

- Workspace Provisioning
- Workspace Configuration
- Computational Resource Allocation
- Workspace Lifecycle
- Workspace Isolation
- Workspace Collaboration
- Workspace Data Access
- Workspace Persistence and Backup

The following topics are intentionally excluded:

- Data storage infrastructure — Frozen per Document 11 (D-7.1)
- ML training environments — Owned by Document 12 (Section 8.4)
- General compute infrastructure — Owned by Section 9.16

---

## 9.2.3 Workspace Model

Every research workspace shall be defined through a canonical specification.

Workspace specification shall include:

- Workspace Identifier — Globally unique workspace identifier
- Workspace Name — Human-readable workspace name
- Owner — Workspace owner identity
- Project — Research project the workspace belongs to
- Computational Resources — Requested CPU, memory, GPU (if required), and storage
- Environment Specification — Container image, dependencies, runtime configuration, environment variables
- Data Access Grants — References to Document 11 data contracts authorizing data access within the workspace per D-8
- Mounted Artifacts — References to research artifacts, datasets, and knowledge artifacts available in the workspace
- Collaboration Configuration — Authorized collaborators and their roles per Section 9.9
- Lifecycle Configuration — Idle timeout, suspension behavior, archival policy
- Creation Timestamp — Workspace creation time
- Status — Current lifecycle state per Section 9.2.6

Workspace specifications shall be versioned and governed.

---

## 9.2.4 Workspace Environment Reproducibility

Every research workspace shall have a fully specified, reproducible environment.

Environment reproducibility shall include:

- Containerized Workspaces — Every workspace shall execute within a governed container image
- Dependency Pinning — All software dependencies shall be pinned to exact versions
- Environment Versioning — Environment specifications shall be versioned
- Environment Registry — Container images shall be registered in the platform container registry
- Environment Validation — Workspace environment shall be validated before activation
- Integration with Reproducibility — Workspace environment specification shall be captured as part of experiment reproducibility evidence per Section 9.7

Environment specifications shall not embed technology-specific assumptions per P-3.

---

## 9.2.5 Workspace Data Access

Research workspaces shall access data through governed Document 11 contracts per D-8.

Data access governance shall include:

- Contract-Governed Access — All data access within the workspace shall be through authorized contracts
- Temporary Working Copies — Research datasets within workspaces are temporary working copies scoped to the project
- No Direct Storage Access — Workspaces shall not access Document 11 storage directly; all access shall be through governed interfaces
- Access Revocation — Data access shall be revocable upon workspace suspension or project completion
- Data Classification Compliance — Workspace data access shall comply with data classification controls per D-7.12.6
- Access Audit — All data access from workspaces shall be logged for audit per P-5

Research data produced within workspaces shall be saved as governed research artifacts per Section 9.10 before workspace archival or destruction.

---

## 9.2.6 Workspace Lifecycle

Every workspace shall progress through governed lifecycle states.

Workspace lifecycle states include:

- Provisioned — Workspace has been created and configured. Resources are allocated. Environment is validated.
- Active — Workspace is actively in use. Resources are fully available.
- Idle — Workspace has not been actively used beyond the configured idle timeout. Resources may be partially released.
- Suspended — Workspace has been suspended. Computational state is preserved. Resources are released. Suspension may occur automatically after extended idle period or manually.
- Archived — Workspace has been archived. Workspace specification, environment, and artifacts are preserved for reproducibility. Archived workspaces may be restored.
- Destroyed — Workspace has been destroyed. Computational resources and temporary data are permanently removed. Workspace metadata is preserved for audit.

Lifecycle transitions shall be governed with appropriate authorization.

Automatic suspension of idle workspaces shall preserve workspace state for recovery.

Idle timeout and cleanup schedule:

| State | Timeout | Action | Recovery |
|-------|---------|--------|----------|
| Active → Idle Warning | 30 minutes no kernel activity | Notification to researcher | N/A |
| Idle Warning → Suspended | 2 hours no activity | Workspace suspended, state preserved, compute released | Resume <= 30 seconds |
| Suspended → Archived | 14 days suspended | Workspace archived, storage moved to Tier 2 | Restore <= 5 minutes |
| Archived → Destroyed | 90 days archived, no access | Workspace destroyed, storage reclaimed | Non-recoverable |

Researchers shall receive notification 24 hours before archival and 7 days before destruction. Project leads may configure shorter timeouts per project policy. Critical tagged workspaces shall be exempt from automatic archival — critical flag requires project lead approval and annual renewal.

---

## 9.2.7 Workspace Resource Management

Research workspaces shall be allocated computational resources through governed processes.

Resource management shall include:

- Resource Specification — CPU cores, memory gigabytes, GPU count/type, storage gigabytes
- Resource Quotas — Per-user, per-project, and per-team resource quotas ensuring fair allocation

Default resource quota tiers:

| Tier | Max CPU Cores | Max GPU | Max Memory (GB) | Max Workspace Storage (GB) | Max Concurrent Workspaces | Max Concurrent Experiments |
|------|-------------|---------|-----------------|---------------------------|--------------------------|---------------------------|
| Standard Researcher | 16 | 0 | 64 | 500 | 5 | 10 |
| Power Researcher | 64 | 2 | 256 | 2,000 | 10 | 25 |
| Research Team Lead | 128 | 4 | 512 | 5,000 | 15 | 50 |
| Project Aggregate | 256 | 8 | 1,024 | 10,000 | 30 | 100 |

Quota increase requests shall require project lead approval with resource justification. Quotas shall be enforced at workspace creation and experiment submission. Exceeding quota shall return a clear error with current utilization and quota limit.
- Resource Scheduling — Fair scheduling of shared compute resources across active workspaces
- Burst Capacity — Support for temporary resource increases for intensive analyses
- Resource Monitoring — Continuous monitoring of workspace resource utilization
- Cost Attribution — Resource consumption attributed to projects for cost tracking

Resource allocation shall not embed assumptions about specific hardware vendors or cloud providers per P-3 and P-18.

---

## 9.2.8 Workspace Isolation

Research workspaces shall be isolated to prevent cross-workspace data leakage and ensure security boundaries.

Isolation shall include:

- Compute Isolation — Workspaces shall not share memory or compute resources
- Data Isolation — Workspace data shall be isolated at the storage access level; no cross-workspace data access without explicit authorization
- Network Isolation — Workspace network traffic shall be isolated; cross-workspace communication requires explicit authorization
- Classification-Aware Isolation — Workspaces handling different data classification levels shall maintain appropriate isolation boundaries per D-7.12.6
- Project Isolation — Workspaces belonging to different research projects shall be isolated

Isolation violations shall generate security alerts per Section 9.14.

---

## 9.2.9 Workspace Collaboration Features

Research workspaces shall support governed collaboration per Section 9.9.

Collaboration features shall include:

- Workspace Sharing — Workspace owner may share workspace with authorized collaborators
- Role-Based Access — Collaborators assigned roles: Editor (full access), Reviewer (read-only), Viewer (limited access)
- Real-Time Collaboration — Support for concurrent editing and analysis within a shared workspace
- Change Tracking — All modifications tracked with attribution for collaboration audit
- Collaboration Invitations — Governed invitation workflow with time-bound access grants
- Access Revocation — Workspace owner or governance authority may revoke collaborator access

Collaboration shall not compromise workspace isolation boundaries.

---

## 9.2.10 Workspace Persistent Storage

Research workspaces shall be supported by persistent storage for research continuity.

Persistent storage shall include:

- Home Directory — Persistent per-user storage surviving workspace suspension
- Project Storage — Shared persistent storage for the research project
- Temporary Workspace Storage — Ephemeral storage released upon workspace destruction
- Storage Quotas — Per-user and per-project storage quotas
- Storage Tiering — Automatic transition of inactive workspace data to lower-cost storage tiers per Document 11 Section 7.6

Persistent storage shall be backed up per Section 9.2.11.

---

## 9.2.11 Workspace Backup

Workspace data shall be protected through integration with Document 11 backup architecture.

Backup coverage shall include:

- Workspace specifications and configurations
- Persistent workspace data
- Workspace environment specifications
- Collaboration records

Backup shall comply with Document 11 backup governance per D-7.5.1.

Backup copies shall be immutable after successful creation per D-7.5.3.

---

## 9.2.12 Workspace Security

Research workspaces shall implement security controls extending Document 11 Section 7.12.

Security controls shall include:

- Authentication — Workspace access shall require authenticated identity per D-9
- Authorization — Workspace operations shall be governed by access controls per D-7.12.4
- Data Access Governance — Workspace data access through contracts per Section 9.2.5
- Encryption — Workspace data encrypted at rest per D-7.12.5
- Audit Logging — Workspace lifecycle and access events logged per P-5
- Network Security — Workspace network traffic governed by enterprise network security policies

Detailed security controls are defined in Section 9.14.

---

## 9.2.13 Workspace Governance

Research workspaces shall be governed through enterprise governance processes.

Governance shall include:

- Workspace Provisioning Approval — Large-scale or high-resource workspaces shall require governance approval
- Data Access Governance — Data access grants shall be governed and periodically reviewed
- Collaboration Governance — Workspace sharing shall follow governed collaboration policies
- Lifecycle Governance — Workspace archival and destruction shall require appropriate authorization
- Audit Trail — Every workspace governance event shall produce immutable audit records per P-5

---

## 9.2.14 Workspace Performance

Workspace services shall satisfy defined performance objectives.

Performance considerations include:

- Provisioning Latency — Time from workspace request to ready state

Workspace startup time SLOs:

| Operation | Target (p95) | Target (p99) | Measurement |
|-----------|-------------|-------------|-------------|
| Cold Start (new workspace) | <= 120 seconds | <= 180 seconds | Workspace request to Jupyter kernel ready |
| Warm Start (suspended workspace) | <= 30 seconds | <= 60 seconds | Resume request to kernel responsive |
| Package Install (additional) | <= 60 seconds per 100 packages | <= 120 seconds | pip/conda install to import-ready |

Startup time shall be logged per workspace activation event. SLO violations shall be tracked for capacity planning.
- Activation Latency — Time from suspended state to active state
- Collaboration Latency — Real-time collaboration responsiveness
- Storage I/O Performance — Workspace storage read/write throughput
- Resource Scaling Latency — Time to increase or decrease allocated resources

Performance objectives shall be continuously monitored.

---

## 9.2.15 Workspace Scalability

Workspace services shall scale horizontally to support researcher growth.

Scalability considerations include:

- Concurrent Workspace Growth — Increasing number of simultaneously active workspaces
- Resource Demand Growth — Increasing per-workspace resource requirements
- Collaboration Growth — Increasing concurrent collaborative sessions
- Storage Growth — Increasing persistent workspace storage

Scaling shall preserve workspace isolation and governance guarantees.

---

## 9.2.16 Workspace High Availability

Workspace services shall operate with high availability.

Availability shall cover:

- Workspace Provisioning Services
- Workspace Lifecycle Services
- Workspace Storage Services

Workspace interruption shall support graceful state preservation and recovery from suspension. Active workspaces shall survive temporary service disruption.

No individual component shall constitute a single point of failure per P-16.

---

## 9.2.17 Workspace Disaster Recovery

Disaster recovery shall ensure continuity of workspace operations.

Recovery shall preserve:

- Workspace Specifications
- Persistent Workspace Data
- Environment Specifications
- Collaboration Records
- Workspace Configuration

Recovery shall satisfy enterprise RTO and RPO objectives.

---

## 9.2.18 Workspace Operational Monitoring

Workspace operations shall be continuously monitored per P-15.

Monitoring domains include:

- Active Workspaces — Count of workspaces by lifecycle state
- Provisioning Operations — Provisioning success rate, provisioning latency
- Resource Utilization — CPU, memory, GPU, storage utilization per workspace
- Idle Detection — Idle workspace count, idle duration distribution
- Collaboration Activity — Active collaborative sessions, collaborator count
- Storage Utilization — Workspace storage consumption trends

Monitoring shall detect and alert on operational anomalies.

---

## 9.2.19 Workspace Alerting

Workspace alerts shall integrate with enterprise alerting per D-7.13.6.

Alert categories include:

- Provisioning Failure — Workspace provisioning failure
- Resource Exhaustion — Workspace resource quotas approaching limits
- Prolonged Idle — Workspace idle beyond governance-defined threshold
- Isolation Violation — Potential cross-workspace data leakage detected
- Storage Capacity — Workspace storage approaching quota limits
- Collaboration Anomaly — Unusual collaboration access patterns

Alerts shall include sufficient context for diagnosis.

---

## 9.2.20 Workspace Testing

Workspace architecture shall satisfy comprehensive testing requirements.

Testing categories include:

- Functional Testing — Workspace provisioning, suspension, restoration, destruction
- Isolation Testing — Verification of cross-workspace isolation boundaries
- Collaboration Testing — Concurrent access, role enforcement, access revocation
- Performance Testing — Provisioning and activation latency under load
- Failure Testing — Graceful behavior under resource exhaustion and component failure
- Security Testing — Authentication, authorization, data access governance

---

## 9.2.21 Risks

The Research Workspace Architecture shall continuously assess architectural risks.

Risk categories include:

- Cross-Workspace Data Leakage — Data isolation failure between workspaces
- Resource Starvation — Excessive resource consumption by individual workspaces
- Environment Non-Reproducibility — Workspace environment specification insufficient for reproduction
- Data Loss on Destruction — Important research data lost during workspace destruction without archival
- Provisioning Failure — Inability to provision workspaces during peak demand
- Idle Resource Waste — Excessive resources consumed by idle workspaces

Every identified risk shall include risk classification, impact assessment, likelihood assessment, detection method, mitigation strategy, recovery procedure, and ownership.

---

## 9.2.22 Acceptance Criteria

The Research Workspace Architecture shall be considered complete when the platform demonstrates:

- Standardized workspace model with governed specification
- Reproducible workspace environments with containerization and dependency pinning
- Governed data access through Document 11 contracts
- Complete workspace lifecycle from Provisioned through Destroyed
- Workspace isolation preventing cross-workspace data leakage
- Governed collaboration with role-based access
- Integration with Document 11 storage, backup, and security infrastructure
- No technology-specific or strategy-specific assumptions per P-1, P-3

---

## 9.2.23 Cross References

This section shall be read together with:

- Section 9.1 — Research Platform Architecture
- Section 9.4 — Research Experiment Architecture
- Section 9.9 — Research Collaboration Architecture
- Section 9.10 — Research Artifact Management
- Section 9.14 — Research Security Architecture
- Section 9.16 — Research Infrastructure Architecture
- Document 11 — Data Engineering & Data Pipeline Architecture (per D-7.1, D-7.5, D-7.6, D-7.8, D-7.10, D-7.12)
- Document 12 — Machine Learning Engineering Architecture (per Section 8.4)
- handbook/ARCHITECTURAL_INVARIANTS.md (per P-1, P-2, P-3, P-5, P-8, P-9, P-15, P-16, P-17, P-18, D-8, D-9)

---

# End of Section

---

# 9.3 Hypothesis Management Architecture

## 9.3.1 Purpose

The Hypothesis Management Architecture defines the canonical framework for formulating, registering, tracking, validating, and governing quantitative research hypotheses within the Quant Hub platform.

Hypothesis management shall provide the structured foundation for research accountability. By requiring explicit hypothesis registration before confirmatory analysis begins, the platform shall prevent HARKing (Hypothesizing After Results are Known) and enable rigorous statistical governance per the Multiple Testing Awareness principle.

Every hypothesis shall be treated as a governed research asset with defined lifecycle, ownership, validation criteria, and immutable history per P-2. Hypothesis management shall not embed strategy-specific assumptions per P-1.

---

## 9.3.2 Scope

The Hypothesis Management Architecture applies to every quantitative research hypothesis within the Quant Hub platform.

Coverage includes:

- Hypothesis Formulation
- Hypothesis Registration
- Hypothesis Tracking
- Hypothesis Validation
- Hypothesis Lifecycle
- Hypothesis-to-Experiment Linkage
- Hypothesis Discovery
- Hypothesis Governance

The following topics are intentionally excluded:

- ML experiment hypotheses — Owned by Document 12 (Section 8.3); research hypotheses are distinct and may test non-ML phenomena
- Strategy-specific hypotheses — Strategy configurations are external to platform architecture per P-1
- General governance infrastructure — Frozen per Document 11 (D-7.11)

---

## 9.3.3 Hypothesis Model

Every hypothesis shall be defined through a canonical specification.

Hypothesis specification shall include:

- Hypothesis Identifier — Globally unique hypothesis identifier
- Statement — Precise, falsifiable statement of the hypothesis
- Null Hypothesis — Explicit null hypothesis being tested
- Alternative Hypothesis — Explicit alternative hypothesis
- Motivation — Research motivation and background for the hypothesis
- Success Criteria — Pre-registered criteria for hypothesis confirmation or rejection, including statistical thresholds and effect size expectations
- Statistical Methodology — Planned statistical test(s), significance level, multiple testing correction method, power analysis requirements
- Required Data — References to Document 11 datasets required for testing (by identifier, not specific versions)
- Assumptions — Documented assumptions underlying the hypothesis and statistical methodology
- Owner — Hypothesis owner identity
- Timestamps — Creation time, registration time, last update time
- Status — Current lifecycle state per Section 9.3.4
- Tags and Classification — Organizational taxonomy per Section 9.8

Hypothesis registration shall create an immutable record per P-2, preventing post-hoc modification.

---

## 9.3.4 Hypothesis Lifecycle

Every hypothesis shall progress through governed lifecycle states.

Hypothesis lifecycle states include:

- Draft — Hypothesis is being formulated. May be modified freely.
- Registered — Hypothesis has been formally registered. Statement, methodology, and success criteria are immutable per P-2. Registration shall occur before confirmatory analysis begins.
- Under Investigation — Active research is testing the hypothesis. Experiments are linked per Section 9.3.6.
- Validated — Hypothesis has been confirmed through governed research with statistical significance meeting pre-registered criteria.
- Rejected — Hypothesis has been disconfirmed through governed research.
- Inconclusive — Research did not produce sufficient evidence to confirm or reject. Insufficient data, statistical power, or contradictory results.
- Archived — Hypothesis is archived. Historical records preserved for knowledge management.

State transitions shall be governed with explicit rationale.

Registration is the critical governance gate — once Registered, hypothesis fundamentals shall not change. New hypotheses shall be registered for modified research questions.

---

## 9.3.5 Hypothesis Registration

Hypothesis registration is the foundational governance mechanism preventing HARKing and enabling statistical rigor.

Registration shall include:

- Pre-Registration Timing — Hypothesis shall be registered before confirmatory analysis begins on the data that will test it
- Immutable Registration — Registration creates an immutable record per P-2
- Registration Validation — Automated validation that the hypothesis specification is complete and well-formed
- Registration Metadata — Hypothesis registered in the Document 11 Metadata Registry per D-7.7.3
- Exploratory vs Confirmatory Flag — Explicit flag distinguishing hypothesis-generating (exploratory) from hypothesis-testing (confirmatory) analysis

Registration shall not prevent exploratory analysis on the same data; it shall prevent presenting exploratory findings as confirmatory.

---

## 9.3.6 Hypothesis-Experiment Linkage

Every research experiment shall declare which hypothesis it tests per the Hypothesis-Experiment Separation principle.

Linkage shall include:

- Many-to-Many Relationship — One hypothesis may be tested by multiple experiments; one experiment may test multiple hypotheses
- Explicit Declaration — Experiment shall explicitly declare hypothesis references in its specification per Section 9.4.3
- Linkage Immutability — Hypothesis-experiment linkages shall be immutable after experiment completion per P-2
- Linkage Lineage — Hypothesis-experiment relationships recorded in lineage per D-5
- Linkage Governance — Multiple experiments testing the same hypothesis shall be tracked for multiple testing adjustment

---

## 9.3.7 Hypothesis Validation Framework

Hypothesis validation shall provide the statistical and governance framework for hypothesis confirmation or rejection.

Validation shall include:

- Pre-Registered Criteria Enforcement — Validation shall compare results against pre-registered success criteria
- Statistical Significance Verification — Verification that statistical tests are appropriate and correctly applied
- Multiple Testing Adjustment — Adjustment for multiple experiments testing the same hypothesis or multiple hypotheses tested on shared data
- Effect Size Assessment — Effect size evaluation alongside statistical significance per the Statistical Analysis Framework (Section 9.6)
- Reproducibility Verification — Validation results shall be reproducible per Section 9.7
- Governance Review — Validation conclusions shall be subject to governance review per Section 9.11

Hypothesis validation shall produce immutable evidence per P-2.

---

## 9.3.8 Hypothesis Discovery

The platform shall provide hypothesis discovery services.

Discovery capabilities shall include:

- Hypothesis Search — Search by statement, hypothesis, tags, owner, status, or methodology
- Hypothesis Browse — Hierarchical browsing organized by research domain and taxonomy
- Hypothesis Lineage — Visualization of hypothesis relationships, experiments, and findings
- Hypothesis Metrics — Statistics on hypothesis registration rates, validation rates, and time-to-conclusion
- Related Hypotheses — Discovery of related or similar hypotheses to prevent duplication

Discovery shall integrate with the knowledge management platform per Section 9.8.

---

## 9.3.9 Hypothesis Lineage

Every hypothesis shall maintain lineage connecting it to related research artifacts.

Lineage shall include:

- Parent Hypothesis — When a hypothesis is derived from or refined from a previous hypothesis
- Input Datasets — Document 11 datasets required for testing
- Testing Experiments — Experiments that tested the hypothesis
- Resulting Findings — Knowledge artifacts produced from hypothesis validation
- Related Hypotheses — Thematically connected hypotheses in the same research domain

Hypothesis lineage shall integrate with Document 11 Lineage Architecture per D-5.

---

## 9.3.10 Hypothesis Governance

Hypothesis management shall be governed through enterprise governance processes.

Governance shall include:

- Registration Review — Registered hypotheses may be reviewed for methodological soundness
- Validation Governance — Hypothesis validation decisions shall require governance review for production-bound research
- Methodology Governance — Statistical methodologies shall comply with the Statistical Analysis Framework (Section 9.6)
- Ownership Governance — Every hypothesis shall have a designated owner
- Audit Trail — Hypothesis lifecycle events shall produce immutable audit records per P-5

---

## 9.3.11 Hypothesis Security

Hypothesis records shall be protected through enterprise security controls extending Document 11 Section 7.12.

Security controls shall include:

- Authentication — Hypothesis registration and modification shall require authenticated access per D-9
- Authorization — Hypothesis visibility shall be governed by project and classification access controls
- Immutability — Registered hypothesis fundamentals shall be immutable per P-2
- Audit Logging — Hypothesis lifecycle events shall generate audit records per P-5

---

## 9.3.12 Hypothesis Metrics

The platform shall maintain standardized hypothesis metrics.

Metric categories include:

- Registration Metrics — Hypotheses registered per time period, registration-to-first-experiment time
- Validation Metrics — Validation rate (confirmed, rejected, inconclusive distribution), time-to-conclusion
- Methodology Metrics — Statistical test usage distribution, multiple testing correction usage
- Quality Metrics — Reproducibility rate for hypothesis validation, pre-registration compliance rate

Metrics shall be available through research dashboards per Section 9.15.

---

## 9.3.13 Hypothesis Performance

Hypothesis management services shall satisfy defined performance objectives.

Performance considerations include hypothesis registration latency, query response time for hypothesis search, linkage resolution performance, and validation processing time.

Performance objectives shall be continuously monitored.

---

## 9.3.14 Hypothesis Scalability

Hypothesis services shall scale to support research growth including hypothesis volume, experiment linkage volume, and discovery query volume.

Scaling shall preserve hypothesis immutability and governance guarantees.

---

## 9.3.15 Hypothesis High Availability and Disaster Recovery

Hypothesis services shall operate with high availability covering registration, query, and validation services. Disaster recovery shall preserve hypothesis records, lifecycle history, experiment linkages, and governance records.

---

## 9.3.16 Hypothesis Testing

Hypothesis management architecture shall satisfy testing requirements including functional testing (registration, lifecycle, validation), integration testing (with experiment, governance, knowledge), security testing, and audit testing.

---

## 9.3.17 Risks

The Hypothesis Management Architecture shall continuously assess architectural risks.

Risk categories include:

- HARKing — Post-hoc hypothesis modification to match observed results, defeating statistical validity
- Registration Bypass — Confirmatory analysis conducted without hypothesis pre-registration
- Multiple Testing Abuse — Uncorrected multiple comparisons inflating false positive rates
- Methodology Drift — Analysis methodology diverging from pre-registered plan without documentation
- Incomplete Validation — Hypothesis validation based on insufficient or inappropriate statistical evidence
- Discovery Gap — Inability to discover existing related hypotheses leading to duplicated research

Every identified risk shall include risk classification, impact assessment, likelihood assessment, detection method, mitigation strategy, recovery procedure, and ownership.

---

## 9.3.18 Acceptance Criteria

The Hypothesis Management Architecture shall be considered complete when the platform demonstrates:

- Standardized hypothesis model with pre-registered success criteria
- Governed hypothesis lifecycle with immutable registration preventing HARKing
- Hypothesis-experiment linkage with many-to-many relationship support
- Hypothesis validation against pre-registered criteria with multiple testing adjustment
- Hypothesis discovery and lineage integrated with knowledge management
- Hypothesis governance with registration review and methodology compliance
- No strategy-specific hypothesis templates or assumptions per P-1

---

## 9.3.19 Cross References

This section shall be read together with:

- Section 9.1 — Research Platform Architecture
- Section 9.4 — Research Experiment Architecture
- Section 9.6 — Statistical Analysis Framework
- Section 9.7 — Research Reproducibility Architecture
- Section 9.8 — Knowledge Management Architecture
- Section 9.11 — Research Governance Architecture
- Document 11 — Data Engineering & Data Pipeline Architecture (per D-7.7, D-7.8, D-7.11, D-7.12)
- handbook/ARCHITECTURAL_INVARIANTS.md (per P-1, P-2, P-5, P-9, P-13, P-17)

---

# End of Section

---

# 9.4 Research Experiment Architecture

## 9.4.1 Purpose

The Research Experiment Architecture defines the canonical framework for organizing, executing, versioning, and governing quantitative research experiments within the Quant Hub platform.

Research experiments are the execution vehicles for testing hypotheses through data analysis, backtesting, simulation, or statistical modeling. Research experiments are distinct from ML experiments (Document 12 Section 8.3). ML experiments track model training runs with hyperparameters and metrics. Research experiments test hypotheses through analysis that may or may not involve ML — they may include statistical tests, econometric analysis, simulation studies, backtesting, or other quantitative methods.

Every research experiment shall be governed, versioned, and reproducible per the Research Reproducibility by Design principle. Research experiments shall not embed strategy-specific assumptions per P-1.

---

## 9.4.2 Scope

The Research Experiment Architecture applies to every research experiment within the Quant Hub platform.

Coverage includes:

- Experiment Definition
- Experiment Execution
- Experiment Versioning
- Experiment Lifecycle
- Experiment Lineage
- Experiment Reproducibility
- Experiment Governance
- Experiment Artifact Management

The following topics are intentionally excluded:

- ML experiment tracking — Owned by Document 12 (Section 8.3). Research experiments are distinct.
- Model training experiments — Owned by Document 12 (Section 8.4)
- Backtesting execution — Owned by Document 14
- Strategy development — Owned by Document 14

---

## 9.4.3 Research Experiment Model

Every research experiment shall be defined through a canonical specification.

Experiment specification shall include:

- Experiment Identifier — Globally unique experiment identifier
- Experiment Name — Human-readable experiment name
- Hypothesis References — References to hypotheses tested by this experiment per Section 9.3.6
- Methodology — Description of the analysis methodology, statistical approach, or simulation design
- Input Data References — Document 11 dataset identifiers used in the experiment per D-8
- Feature References — Feature identifiers from Document 12 Feature Engineering Architecture if applicable
- Model References — Model identifiers from Document 12 Model Registry if applicable
- Parameters — All configurable parameters controlling experiment behavior
- Metrics — All tracked metrics with definitions and computation methodology
- Results — Experiment results, statistical outputs, and conclusions
- Artifacts — References to all outputs: reports, visualizations, data products
- Code Version — Source code version at experiment execution
- Environment — Workspace environment specification per Section 9.2.4
- Random Seeds — All random seeds for deterministic reproducibility per P-13
- Owner — Experiment owner identity
- Status — Current lifecycle state per Section 9.4.4
- Timestamps — Creation, start, completion, and archival timestamps

Every completed experiment record shall be immutable per P-2.

---

## 9.4.4 Experiment Lifecycle

Every experiment shall progress through governed lifecycle states.

Experiment lifecycle states include:

- Draft — Experiment is being defined. May be modified freely.
- Running — Experiment is actively executing. Parameters are frozen. Metrics are being recorded.
- Completed — Experiment finished successfully. The experiment record is immutable per P-2. Reproducibility evidence shall be captured per Section 9.7.
- Failed — Experiment terminated with an error. The experiment record shall be preserved for diagnostic purposes. Partial results and artifacts shall remain accessible.
- Archived — Experiment has been archived per Document 11 archiving infrastructure (D-7.6). The experiment record remains discoverable and recoverable per D-7.6.2.

Lifecycle transitions shall be governed with explicit rationale.

Completed and Failed experiments shall be immutable. Modifications shall create new experiment versions with explicit parent-child lineage.

---

## 9.4.5 Experiment Reproducibility

Every completed experiment shall be reproducible per the Research Reproducibility by Design principle.

The platform shall guarantee reproducibility by capturing:

- Code Version — Source code version at experiment execution
- Data Version — Document 11 dataset versions referenced by identifier
- Feature Versions — Feature versions from Document 12 Feature Engineering Architecture
- Model Versions — Model versions from Document 12 Model Registry
- Environment — Complete workspace environment specification
- Parameters — All experiment parameters
- Random Seeds — All random seeds
- Methodology — Complete analysis methodology specification

Detailed reproducibility requirements are defined in Section 9.7.

---

## 9.4.6 Experiment Lineage

Every experiment shall maintain lineage connecting it to hypotheses, data, features, models, and related experiments.

Experiment lineage shall include:

- Hypothesis Linkage — References to tested hypotheses per Section 9.3.6
- Data Lineage — Document 11 dataset references per D-5
- Feature Lineage — References to features from Document 12
- Model Lineage — References to models from Document 12
- Parent Experiment — When an experiment is derived from or refines a previous experiment
- Child Experiments — Experiments that are derived from this experiment
- Artifact Lineage — Research artifacts produced by this experiment per Section 9.10

Experiment lineage shall integrate with Document 11 Lineage Architecture per D-5.

---

## 9.4.7 Experiment Comparison

The platform shall support systematic comparison of multiple experiments.

Comparison capabilities shall include:

- Multi-Experiment Metric Comparison — Side-by-side comparison of metrics across selected experiments
- Statistical Comparison — Statistical significance testing between experiment results
- Visualization — Comparative visualization of experiment results, metrics, and conclusions
- Hypothesis-Centric Comparison — Comparison of experiments testing the same or related hypotheses
- Methodology Comparison — Comparison of different methodologies applied to the same research question

Comparison shall support research decision-making and knowledge synthesis.

---

## 9.4.8 Experiment Artifact Management

Research experiments shall produce governed artifacts per Section 9.10.

Artifact management shall include:

- Artifact Registration — All experiment outputs registered as governed artifacts
- Artifact Versioning — Artifact versions linked to experiment versions
- Artifact Storage — Artifacts stored through Document 11 storage infrastructure per D-7.1
- Artifact Discovery — Artifacts discoverable through experiment records and knowledge management
- Artifact Lifecycle — Artifacts follow experiment lifecycle for retention and archival

---

## 9.4.9 Experiment Collaboration

Research experiments shall support governed collaboration per Section 9.9.

Collaboration shall include:

- Experiment Sharing — Experiment owner may share experiment with collaborators
- Role-Based Access — Editor, Reviewer, Viewer roles for experiment access
- Collaborative Experimentation — Multiple researchers may contribute to experiment design and analysis
- Change Attribution — All modifications attributed to specific collaborators
- Experiment Review — Peer review of experiment methodology and conclusions per Section 9.9.4

---

## 9.4.10 Experiment Governance

Research experiments shall be governed through enterprise governance processes.

Governance shall include:

- Experiment Registration — Every experiment shall be registered before execution
- Methodology Review — Experiment methodology may be reviewed for appropriateness
- Hypothesis Compliance — Verification that experiment correctly tests declared hypotheses
- Reproducibility Verification — Completed experiments shall have reproducibility verified per Section 9.7
- Audit Trail — Every experiment lifecycle event shall produce immutable audit records per P-5

---

## 9.4.11 Experiment Security

Experiment records and artifacts shall be protected through security controls extending Document 11 Section 7.12.

Security controls shall include:

- Authentication — Experiment access shall require authenticated identity per D-9
- Authorization — Experiment visibility and modification governed by access controls
- Data Access — Experiment data access through governed contracts per D-8
- Encryption — Experiment artifacts encrypted at rest per D-7.12.5
- Audit Logging — Experiment access and lifecycle events logged per P-5

---

## 9.4.12 Experiment Performance

Experiment services shall satisfy defined performance objectives.

Performance considerations include experiment registration latency, execution support for concurrent experiments, metric recording throughput, artifact upload performance, and comparison query response time.

---

## 9.4.13 Experiment Scalability

Experiment services shall scale to support experiment volume growth, concurrent execution growth, artifact volume growth, and comparison query complexity growth. Scaling shall preserve experiment immutability and reproducibility guarantees.

---

## 9.4.14 Experiment High Availability and Disaster Recovery

Experiment services shall operate with high availability. Experiment execution shall be resilient to temporary service disruption. Disaster recovery shall preserve experiment records, metrics, artifacts, lineage, and governance records per enterprise RTO/RPO.

---

## 9.4.15 Experiment Operational Monitoring

Experiment operations shall be continuously monitored per P-15.

Monitoring domains include:

- Active Experiments — Count of experiments by lifecycle state
- Experiment Execution — Success rate, failure rate, execution duration
- Reproducibility Status — Reproducibility verification results
- Hypothesis Coverage — Hypotheses with vs without experiments
- Artifact Operations — Artifact registration and storage operations

Monitoring shall detect and alert on operational anomalies.

---

## 9.4.16 Experiment Alerting

Experiment alerts shall include experiment execution failure, reproducibility verification failure, prolonged experiment execution, artifact storage failure, and hypothesis-experiment linkage anomalies.

Experiment timeout and cleanup:

| Setting | Default | Maximum | Override |
|---------|---------|---------|----------|
| Maximum Wall-Clock Duration | 24 hours | 72 hours | Project lead approval required for > 24 hours |
| Heartbeat Interval | 5 minutes | — | Experiment must report heartbeat; 3 missed heartbeats triggers investigation |
| Timeout Action | Graceful termination with state preservation (checkpoint + notebook save) | — | Force kill after 5-minute grace period |
| Orphaned Experiment Cleanup | Experiments with disconnected researcher for > 1 hour | — | Suspend and notify researcher |
| Pre-Termination Warning | 15 minutes, 5 minutes, 1 minute before timeout | — | Notifications with option to request extension |

Long-running experiments (> 12 hours) shall checkpoint every 30 minutes at minimum. Checkpointed state shall be recoverable on restart. Experiments exceeding 72 hours shall require governance approval.

---

## 9.4.17 Experiment Testing

Experiment architecture shall satisfy testing requirements including functional testing (registration, execution, lifecycle), reproducibility testing, integration testing (with hypothesis, governance, artifact services), performance testing, and security testing.

---

## 9.4.18 Risks

The Research Experiment Architecture shall continuously assess architectural risks.

Risk categories include:

- Reproducibility Failure — Missing or incomplete reproducibility evidence
- Hypothesis-Experiment Disconnect — Experiments not correctly linked to or testing declared hypotheses
- Methodology Error — Flawed analysis methodology producing invalid results
- Artifact Loss — Loss of experiment artifacts before archival
- Comparison Bias — Selective comparison of experiments favoring desired conclusions
- Execution Non-Determinism — Identical experiment configuration producing different results

Every identified risk shall include risk classification, impact assessment, likelihood assessment, detection method, mitigation strategy, recovery procedure, and ownership.

---

## 9.4.19 Acceptance Criteria

The Research Experiment Architecture shall be considered complete when the platform demonstrates:

- Standardized experiment model capturing all required reproducibility information
- Governed experiment lifecycle with immutable completed records per P-2
- Hypothesis-experiment linkage with many-to-many relationship support
- Experiment lineage integrated with Document 11 Lineage Architecture
- Experiment reproducibility verification per Section 9.7
- Experiment comparison with statistical and visual capabilities
- Experiment governance with methodology review and hypothesis compliance
- Clear distinction from ML experiments (Document 12 Section 8.3)
- No strategy-specific experiment templates or assumptions per P-1

---

## 9.4.20 Cross References

This section shall be read together with:

- Section 9.1 — Research Platform Architecture
- Section 9.2 — Research Workspace Architecture
- Section 9.3 — Hypothesis Management Architecture
- Section 9.7 — Research Reproducibility Architecture
- Section 9.8 — Knowledge Management Architecture
- Section 9.10 — Research Artifact Management
- Section 9.11 — Research Governance Architecture
- Document 11 — Data Engineering & Data Pipeline Architecture (per D-7.1, D-7.6, D-7.7, D-7.8, D-7.11, D-7.12)
- Document 12 — Machine Learning Engineering Architecture (per Sections 8.3, 8.4, 8.6)
- handbook/ARCHITECTURAL_INVARIANTS.md (per P-1, P-2, P-5, P-9, P-13, P-17)

---

# End of Section

---

# 9.5 Exploratory Data Analysis Architecture

## 9.5.1 Purpose

The Exploratory Data Analysis (EDA) Architecture defines the canonical framework for governed data exploration within the Quant Hub research platform.

EDA shall provide the initial data understanding that informs hypothesis formulation and experiment design. It is the bridge between raw data access and structured research. EDA sessions shall be governed to distinguish exploratory (hypothesis-generating) analysis from confirmatory (hypothesis-testing) analysis.

EDA shall not be confused with confirmatory analysis. Findings from EDA are hypothesis-generating, not hypothesis-validating. The platform shall enforce this distinction through governance controls.

EDA sessions shall not embed strategy-specific assumptions per P-1.

---

## 9.5.2 Scope

The EDA Architecture applies to all exploratory data analysis within the research platform.

Coverage includes:

- Data Profiling
- Statistical Summaries
- Visualization
- Correlation Analysis
- Pattern Discovery
- Insight Capture
- EDA Session Governance
- EDA Reproducibility
- EDA-to-Hypothesis Bridging

The following topics are intentionally excluded:

- Confirmatory statistical analysis — Owned by Section 9.6
- Data quality validation — Frozen per Document 11 (D-7.9)
- ML model training — Owned by Document 12 (Section 8.4)

---

## 9.5.3 EDA Session Model

Every EDA session shall be defined through a canonical specification.

EDA session specification shall include:

- Session Identifier — Globally unique session identifier
- Session Name — Human-readable session name
- Dataset References — Document 11 dataset identifiers accessed during exploration per D-8
- Analysis Scope — Description of the exploration objectives and boundaries
- Generated Visualizations — References to all visualizations produced
- Discovered Patterns — Documented patterns, correlations, and anomalies identified
- Captured Insights — Formal insight records bridging EDA to hypothesis formulation
- Statistical Summaries — Descriptive statistics computed during exploration
- Code and Environment — Code and environment for reproducibility
- Owner — Session owner identity
- Timestamps — Session start, end, and duration
- Exploratory Flag — Explicit flag marking this session as exploratory

EDA sessions shall be registered as research activities with appropriate governance.

---

## 9.5.4 Insight Capture

EDA sessions shall produce formal insight records that bridge exploration to structured research.

Insight capture shall include:

- Insight Identifier — Globally unique insight identifier
- Insight Description — Clear description of the observation, pattern, or anomaly
- Source Session — Reference to the EDA session that produced the insight
- Supporting Evidence — References to visualizations, statistics, and data that support the insight
- Confidence Assessment — Qualitative assessment of insight reliability
- Hypothesis Candidates — Suggested hypotheses that could formalize the insight for confirmatory testing per Section 9.3
- Recommendations — Suggested next steps: further EDA, hypothesis registration, data quality investigation

Insights shall be discoverable through the knowledge management platform per Section 9.8.

Insights shall be clearly labeled as exploratory — they do not constitute validated findings.

---

## 9.5.5 EDA Governance

EDA shall be governed to maintain the distinction between exploratory and confirmatory analysis.

Governance controls shall include:

- Exploratory-Confirmatory Distinction — EDA sessions and their outputs shall be clearly flagged as exploratory
- Promotion Restriction — EDA insights shall not be promoted to production without confirmatory hypothesis testing per Section 9.3
- Methodology Flexibility — EDA methodology may be flexible and iterative, unlike confirmatory analysis which requires pre-registration
- Insight Review — Significant insights may be reviewed for research direction decisions
- Data Access Governance — EDA data access through governed contracts per D-8
- Audit Trail — EDA session records shall be immutable after completion per P-2

EDA governance shall prevent the presentation of exploratory findings as confirmatory evidence.

---

## 9.5.6 EDA Reproducibility

EDA sessions shall support appropriate reproducibility given their exploratory nature.

Reproducibility shall include:

- Code and Environment Capture — Complete code and environment specification for reproduction
- Data Version Capture — Document 11 dataset versions accessed during the session
- Visualization Reproduction — Visualizations shall be reproducible from captured code and data
- Statistical Summary Reproduction — Descriptive statistics shall be reproducible
- Insight Traceability — Insights shall trace to the specific analysis that produced them

EDA reproducibility may be at a lower tier than confirmatory analysis per Section 9.7 while still providing sufficient evidence for research continuity.

---

## 9.5.7 Data Profiling

The platform shall provide automated data profiling during EDA sessions.

Data profiling shall include:

- Schema Discovery — Automatic detection of data schema, types, and structure
- Summary Statistics — Count, mean, median, standard deviation, min, max, quartiles, null count
- Distribution Analysis — Histograms, density estimates, distribution fitting
- Correlation Matrix — Pairwise correlation analysis with visualization
- Missing Data Analysis — Null rate, missing data patterns, imputation recommendations
- Outlier Detection — Statistical outlier identification
- Temporal Analysis — Time-series specific profiling: seasonality, trends, stationarity

Profiling results shall be captured as EDA session artifacts.

---

## 9.5.8 Visualization Architecture

The platform shall support governed research visualization within EDA sessions.

Visualization capabilities shall include:

- Distribution Visualizations — Histograms, density plots, box plots, violin plots
- Relationship Visualizations — Scatter plots, correlation heatmaps, pair plots
- Temporal Visualizations — Time series plots, rolling statistics, seasonality decomposition
- Comparative Visualizations — Side-by-side comparisons across data segments or time periods
- Interactive Exploration — Interactive visualization for data exploration

Visualizations shall be captured as governed artifacts with reproducibility metadata.

---

## 9.5.9 Correlation and Pattern Discovery

The platform shall support systematic correlation and pattern discovery.

Discovery capabilities shall include:

- Linear Correlation — Pearson, Spearman correlation analysis
- Non-Linear Relationship Detection — Mutual information, distance correlation
- Pattern Detection — Clustering, anomaly detection, regime identification
- Time-Series Patterns — Lag analysis, auto-correlation, cross-correlation
- Segment Analysis — Pattern comparison across data segments

Discovered patterns shall be documented as insights per Section 9.5.4 with appropriate caveats about exploratory nature.

---

## 9.5.10 EDA-to-Hypothesis Bridging

EDA insights shall feed into structured hypothesis formulation per Section 9.3.

Bridging shall include:

- Hypothesis Candidate Generation — EDA insights may suggest hypothesis candidates
- Transition Governance — Transition from exploratory observation to formal hypothesis shall be governed
- Pre-Registration Requirement — Formalized hypotheses shall be registered before confirmatory testing
- Insight-Hypothesis Linkage — Hypotheses derived from EDA insights shall maintain traceable lineage
- Methodological Escalation — Flexible EDA methodology escalated to rigorous confirmatory methodology

The bridge shall prevent presenting EDA findings as if they were pre-registered hypothesis tests.

---

## 9.5.11 EDA Artifact Management

EDA sessions shall produce governed artifacts per Section 9.10.

Artifacts shall include session records, visualizations, statistical summaries, data profiles, insight records, and analysis code. Artifacts shall be versioned, discoverable, and governed.

---

## 9.5.12 EDA Security

EDA sessions shall implement security controls including authentication for data access, authorization governed by project and classification, encryption at rest, audit logging per P-5, and data access through governed contracts per D-8.

---

## 9.5.13 EDA Performance, Scalability, and Operations

EDA services shall satisfy performance objectives for data profiling, visualization rendering, and interactive responsiveness. Services shall scale to support concurrent EDA sessions with growing data volumes. High availability, monitoring, and alerting shall follow enterprise standards per Section 9.1.

---

## 9.5.14 Risks

The EDA Architecture shall continuously assess architectural risks including:

- Confirmatory Misrepresentation — EDA findings presented as confirmatory evidence
- Data Snooping — Repeated exploration of the same data producing spurious patterns
- Insight Loss — Failure to capture and preserve exploratory insights for research continuity
- Visualization Non-Reproducibility — Inability to reproduce exploratory visualizations
- Data Overload — Excessive exploration producing overwhelming unorganized output

Every identified risk shall include risk classification, impact assessment, likelihood assessment, detection method, mitigation strategy, recovery procedure, and ownership.

---

## 9.5.15 Acceptance Criteria

The EDA Architecture shall be considered complete when the platform demonstrates:

- Standardized EDA session model with exploratory flag
- Formal insight capture bridging EDA to hypothesis formulation
- Governed distinction between exploratory and confirmatory analysis
- Automated data profiling with statistical summaries and visualizations
- Reproducibility support appropriate to exploratory analysis
- EDA-to-hypothesis bridging with governance gates
- No strategy-specific exploration templates per P-1

---

## 9.5.16 Cross References

This section shall be read together with Section 9.1 (Research Platform), Section 9.3 (Hypothesis Management), Section 9.6 (Statistical Analysis), Section 9.7 (Reproducibility), Section 9.8 (Knowledge Management), Section 9.10 (Artifact Management), Document 11 (per D-7.1, D-7.8, D-7.9, D-7.10), and handbook/ARCHITECTURAL_INVARIANTS.md (per P-1, P-2, P-5, P-9, P-17).

---

# End of Section

---

# 9.6 Statistical Analysis Framework

## 9.6.1 Purpose

The Statistical Analysis Framework defines the standardized statistical methodology, testing infrastructure, and governance controls for quantitative research within the Quant Hub platform.

The framework shall prevent common analytical pitfalls including p-hacking, multiple testing abuse, selective reporting, and inadequate statistical power. It shall provide governed statistical practices ensuring research integrity and reproducibility.

Statistical analysis shall be deterministic per P-13 — given identical data and configuration, every statistical test shall produce identical results.

The framework shall not embed assumptions about specific asset classes, trading strategies, or research domains per P-1.

---

## 9.6.2 Scope

The Statistical Analysis Framework applies to all quantitative statistical analysis within the research platform.

Coverage includes:

- Statistical Testing
- Significance Assessment
- Multiple Testing Correction
- Effect Size Analysis
- Power Analysis
- Bayesian Methods
- Time-Series Statistics
- Statistical Reporting
- Statistical Governance

The following topics are intentionally excluded:

- ML model evaluation metrics — Owned by Document 12 (Section 8.5)
- Data quality validation — Frozen per Document 11 (D-7.9)
- Backtesting performance metrics — Owned by Document 14

---

## 9.6.3 Statistical Test Registry

The platform shall maintain a governed catalog of approved statistical tests.

The Statistical Test Registry shall include for each test:

- Test Identifier — Unique test identifier
- Test Name — Standardized test name
- Test Description — What the test measures and when it is appropriate
- Assumptions — Statistical assumptions required for valid application
- Limitations — Known limitations and conditions where the test should not be applied
- Input Requirements — Required data format, sample size considerations
- Output — Standardized output format
- References — Academic references for the test methodology

The registry shall be extensible — new statistical tests may be proposed through governance review.

---

## 9.6.4 Significance Testing

The platform shall implement standardized significance testing.

Standardized practices shall include:

- Alpha Specification — Significance level shall be specified before testing begins per hypothesis pre-registration (Section 9.3.5)
- P-Value Reporting — Exact p-values shall be reported, not threshold comparisons alone
- Confidence Intervals — Confidence intervals shall be reported alongside point estimates
- One-Tailed vs Two-Tailed — Test direction shall be pre-specified and justified
- Test Assumption Verification — Statistical test assumptions shall be verified before application; violations shall be documented

Significance shall be interpreted in context of pre-registered hypotheses per Section 9.3.

---

## 9.6.5 Multiple Testing Correction

The platform shall enforce multiple testing correction to control error rates.

Correction methods shall include:

- Bonferroni Correction — Conservative family-wise error rate control
- Holm-Bonferroni Method — Step-down procedure with greater power than Bonferroni
- Benjamini-Hochberg Procedure — False Discovery Rate (FDR) control, appropriate for exploratory contexts
- Family-Wise Error Rate — Control when testing multiple hypotheses on shared data

Multiple testing correction shall be:

- Required — When multiple hypotheses are tested on shared or overlapping data
- Pre-Registered — Correction method and family definition shall be specified before analysis
- Transparent — Both raw and corrected p-values shall be reported
- Context-Aware — Correction appropriate to the research context (exploratory vs confirmatory)

The platform shall detect and flag uncorrected multiple comparisons for governance review.

---

## 9.6.6 P-Hacking Prevention

The platform shall implement design features preventing p-hacking.

Prevention mechanisms shall include:

- Hypothesis Pre-Registration — Analysis plan registered before data analysis per Section 9.3.5
- Sequential Analysis Monitoring — Detection of repeated testing on accumulating data
- Data-Dependent Analysis Detection — Flagging of analysis decisions that depend on observed results
- Researcher Degree of Freedom Documentation — Researchers shall document analytical choices and justify them
- Analysis Plan Comparison — Automated comparison of executed analysis against pre-registered plan
- P-Curve Analysis — Distribution analysis of p-values to detect selective reporting

Violations shall be flagged for governance review.

---

## 9.6.7 Power Analysis

The platform shall support statistical power analysis.

Power analysis shall include:

- Pre-Experiment Power Analysis — Required minimum sample size estimation before confirmatory research
- Minimum Effect Size Specification — Minimum effect size of practical significance shall be specified
- Power Curves — Visualization of power as a function of sample size and effect size
- Post-Hoc Power Reporting — Achieved power reported for completed experiments
- Power Analysis Governance — Power analysis shall be included in hypothesis registration per Section 9.3.3

Underpowered studies shall be flagged for governance review.

---

## 9.6.8 Effect Size Analysis

Statistical significance shall be supplemented with effect size analysis.

Effect size measures shall include:

- Standardized Effect Sizes — Cohen's d, Hedges' g, correlation coefficients
- Financial Effect Sizes — Sharpe ratio improvement, information coefficient, economic magnitude
- Confidence Intervals — Effect size confidence intervals
- Practical Significance — Assessment of whether the effect size has practical or economic significance, distinct from statistical significance

Effect size reporting shall be required for all confirmatory findings.

Statistical significance without meaningful effect size shall not be sufficient for research validation.

---

## 9.6.9 Bayesian Methods

The platform shall support Bayesian statistical analysis where appropriate.

Bayesian methodology shall include:

- Prior Specification — Priors shall be explicitly specified and justified
- Prior Registration — Informative priors shall be registered before analysis
- Sensitivity Analysis — Analysis of results under alternative prior specifications
- Posterior Summaries — Posterior means, credible intervals, and distributions
- Bayes Factors — Bayes factors as an alternative to classical hypothesis testing
- Model Comparison — Bayesian model comparison and selection

Bayesian analysis shall be subject to the same governance rigor as frequentist analysis.

---

## 9.6.10 Time-Series Statistics

The platform shall support time-series specific statistical methods for financial research.

Time-series methods shall include:

- Autocorrelation Adjustment — Newey-West or similar standard errors for serially correlated data
- Stationarity Testing — Augmented Dickey-Fuller, KPSS, Phillips-Perron tests
- Cointegration Analysis — Engle-Granger and Johansen tests for cointegrated relationships
- Regime Detection — Markov switching models, structural break tests
- Point-in-Time Correctness — Statistical analysis shall respect data availability timestamps per Document 11

Time-series analysis shall account for the unique statistical challenges of financial data including non-stationarity, heteroskedasticity, and fat tails.

---

## 9.6.11 Statistical Reporting Standards

The platform shall enforce standardized statistical reporting.

Reporting standards shall include:

- Complete Reporting — All tests conducted shall be reported, not only significant results
- Negative Results — Non-significant and negative results shall be reported and valued
- Methodology Transparency — All analytical decisions and their justifications shall be documented
- Reproducibility Information — Code, data versions, and environment shall be reported for reproducibility
- Standardized Format — Statistical results reported in standardized format for machine-readability

Selective reporting of significant results shall be detected and flagged.

---

## 9.6.12 Statistical Governance

Statistical analysis shall be governed through enterprise governance processes.

Governance shall include:

- Methodology Review — Statistical methodology shall be reviewable for appropriateness
- Pre-Registration Compliance — Verification that executed analysis matches pre-registered plan
- Multiple Testing Compliance — Verification of appropriate multiple testing correction
- Reporting Compliance — Verification of complete and accurate statistical reporting
- Audit Trail — Statistical analysis governance shall produce immutable records per P-5

---

## 9.6.13 Statistical Tooling

The platform shall provide governed statistical tooling integrated with the research workspace.

Tooling shall include standardized statistical libraries, integration with the Statistical Test Registry, automated assumption verification, automated multiple testing correction, and standardized output formats. Tooling shall not embed assumptions about specific implementations per P-3.

---

## 9.6.14 Statistical Integration

The statistical framework shall integrate with Hypothesis Management (pre-registration enforcement), Research Experiments (automated statistical validation), Reproducibility verification, and Knowledge Management for statistical methodology documentation.

---

## 9.6.15 Statistical Performance

Statistical services shall satisfy performance objectives for test execution time, batch analysis throughput, power analysis computation, and multiple testing correction for large hypothesis families. Performance objectives shall be continuously monitored.

---

## 9.6.16 Statistical Scalability

Statistical services shall scale to support hypothesis volume growth, test complexity growth, data volume growth, and concurrent analysis sessions. Scaling shall preserve statistical accuracy and governance controls.

---

## 9.6.17 Statistical High Availability and Disaster Recovery

Statistical services shall operate with high availability. Disaster recovery shall preserve the Statistical Test Registry, analysis records, and governance records.

---

## 9.6.18 Statistical Monitoring and Alerting

Statistical operations shall be monitored for test execution volume, test assumption violations, multiple testing compliance, p-hacking detection events, and analysis-plan compliance. Alerts shall include potential statistical misconduct detection, test assumption violations, and methodology-plan discrepancies.

---

## 9.6.19 Risks

The Statistical Analysis Framework shall continuously assess risks including:

- P-Hacking Undetected — Platform controls failing to detect p-hacking behavior
- Multiple Testing Abuse — Uncorrected multiple comparisons inflating error rates
- Methodology-Plan Drift — Executed analysis diverging from pre-registered plan without governance
- Underpowered Research — Confirmatory research conducted with inadequate statistical power
- Selective Reporting — Significant results reported while non-significant results suppressed
- Time-Series Misapplication — Standard statistical methods applied to financial time series without appropriate adjustments

Every identified risk shall include risk classification, impact assessment, likelihood assessment, detection method, mitigation strategy, recovery procedure, and ownership.

---

## 9.6.20 Acceptance Criteria

The Statistical Analysis Framework shall be considered complete when the platform demonstrates:

- Governed Statistical Test Registry with standardized test specifications
- Multiple testing correction enforced for all confirmatory analysis
- P-hacking prevention through pre-registration and analysis plan comparison
- Power analysis and effect size reporting required for confirmatory findings
- Bayesian methods supported with prior registration
- Time-series specific statistical methods available
- Standardized statistical reporting preventing selective reporting
- Integration with hypothesis management and experiment platforms
- No strategy-specific statistical assumptions per P-1

---

## 9.6.21 Cross References

This section shall be read together with Section 9.1 (Research Platform), Section 9.3 (Hypothesis Management), Section 9.4 (Research Experiments), Section 9.5 (EDA), Section 9.7 (Reproducibility), Section 9.11 (Research Governance), and handbook/ARCHITECTURAL_INVARIANTS.md (per P-1, P-2, P-5, P-9, P-13, P-17).

---

# End of Section

---

# 9.7 Research Reproducibility Architecture

## 9.7.1 Purpose

The Research Reproducibility Architecture defines the comprehensive framework guaranteeing that every published research finding within the Quant Hub platform is reproducible.

The reproducibility framework extends P-13 (Deterministic Processing) and implements the Research Reproducibility by Design principle. Every published research finding shall be reproducible given identical data, code, environment, parameters, and random seeds.

Reproducibility is a prerequisite for research validation, peer review, and production promotion per Section 9.13.

---

## 9.7.2 Scope

The Research Reproducibility Architecture applies to every published research finding, experiment, and analysis within the research platform.

Coverage includes:

- Reproducibility Requirements
- Reproducibility Evidence Capture
- Reproducibility Verification
- Reproducibility Tiers
- Reproducibility Failure Handling
- Reproducibility Governance

---

## 9.7.3 Reproducibility Requirements

Every published research finding shall satisfy reproducibility requirements.

Required captures for reproducibility:

- Code Version — Complete source code version (git commit hash) at experiment execution
- Data Versions — All Document 11 dataset identifiers and versions used in the analysis
- Feature Versions — All feature versions from Document 12 Feature Engineering Architecture
- Model Versions — All model versions from Document 12 Model Registry
- Environment — Complete workspace environment specification including container image, dependencies, and configuration
- Parameters — All analysis parameters and configuration values
- Random Seeds — All random seeds controlling stochastic behavior
- Methodology — Complete analysis methodology specification including statistical tests and their parameters
- Execution Order — Recorded execution order for analyses where order matters

Reproducibility captures shall be validated at finding publication. Incomplete captures shall prevent publication.

---

## 9.7.4 Reproducibility Evidence

Every published finding shall produce immutable reproducibility evidence per P-2.

Reproducibility evidence shall include:

- Evidence Identifier — Unique reproducibility evidence identifier
- Finding Reference — Reference to the published finding being verified
- Verification Configuration — Complete configuration used for reproducibility verification
- Verification Results — Comparison of reproduced outputs against original outputs
- Match Assessment — Quantitative assessment of reproduction fidelity
- Discrepancy Classification — Classification of any discrepancies and their root causes
- Verifier Identity — Identity of the reproducibility verifier (automated or human)
- Verification Timestamp — Time of verification

Reproducibility evidence shall be stored in the Document 11 metadata and lineage infrastructure.

---

## 9.7.5 Reproducibility Verification

The platform shall implement automated reproducibility verification.

Verification shall re-execute the analysis with identical captured state and compare outputs against the original published results.

Verification shall distinguish between:

- Exact Reproduction — Binary-identical outputs
- Statistical Reproduction — Statistically equivalent outputs within tolerance
- Failed Reproduction — Outputs differ beyond acceptable tolerance

Verification shall be triggered automatically upon finding publication and may be re-executed periodically.

---

## 9.7.6 Reproducibility Tiers

Research findings shall be classified into reproducibility tiers appropriate to their significance.

Reproducibility tiers shall include:

- Gold Tier — Fully automated reproduction. Code, data, environment, and execution are fully captured. Reproduction is verified through automated re-execution producing identical or statistically equivalent results.
- Silver Tier — Reproduction with documented manual steps. Complete documentation enables manual reproduction, but automation is partial. Required captures are complete.
- Bronze Tier — Complete documentation enabling manual reproduction. Environment may not be fully containerized, but methodology, data references, and code are documented. Applicable to exploratory or preliminary research.
- Unverified — Research findings that have not yet undergone reproducibility verification. This tier is temporary and shall be resolved before publication.

Tier assignment shall be governed per Section 9.11.

Production-bound research findings shall achieve Gold or Silver tier.

---

## 9.7.7 Reproducibility Failure Classification

When reproducibility verification fails, failures shall be classified.

Failure categories include:

- Environment Drift — Environment differences preventing reproduction (missing dependencies, version mismatches)
- Data Drift — Data version differences (data has been updated, original version unavailable)
- Code Drift — Code version differences (code modified after original execution)
- Non-Determinism — Inherent non-determinism in the analysis (unseeded randomness, external state dependency)
- Incomplete Capture — Missing reproducibility information
- True Discrepancy — Original finding cannot be reproduced even with identical state

Each failure category shall trigger specific remediation workflows.

Failures shall be recorded as immutable evidence per P-2.

---

## 9.7.8 Reproducibility Remediation

Reproducibility failures shall trigger governed remediation.

Remediation shall include:

- Failure Investigation — Root cause analysis of the reproducibility failure
- Capture Completion — Addressing incomplete reproducibility captures
- Re-Execution — Re-execution with corrected state and methodology
- Re-Verification — Re-verification of reproducibility after remediation
- Finding Status Update — Finding status updated based on verification outcome
- Governance Review — Persistent reproducibility failures escalated to governance review

Remediation shall be tracked and recorded for audit.

---

## 9.7.9 Reproducibility Governance

Reproducibility shall be governed through enterprise governance processes.

Governance shall include:

- Tier Assignment Governance — Reproducibility tier assignment shall be governed and reviewable
- Verification Governance — Verification results shall be reviewed for accuracy
- Failure Escalation — Reproducibility failures shall escalate through governance
- Publication Gate — Reproducibility verification shall gate finding publication
- Audit Trail — Reproducibility governance shall produce immutable records per P-5

---

## 9.7.10 Reproducibility Integration

The reproducibility framework shall integrate with Experiments (Section 9.4 — automated verification at completion), Hypotheses (Section 9.3 — reproducibility evidence linked to hypothesis validation), Knowledge Management (Section 9.8 — reproducibility tier displayed on knowledge artifacts), and Research-to-Production Promotion (Section 9.13 — reproducibility verification required before promotion).

---

## 9.7.11 Reproducibility Tooling

The platform shall provide governed reproducibility tooling integrated with the research workspace.

Tooling shall include automated environment capture, automated data version capture, automated code version capture, automated reproducibility verification execution, reproducibility evidence generation, and tier certification automation. Tooling shall not embed technology-specific assumptions per P-3.

---

## 9.7.12 Reproducibility Performance

Reproducibility services shall satisfy performance objectives for verification execution time, evidence generation time, capture completeness validation, and tier certification processing. Performance objectives shall be continuously monitored.

---

## 9.7.13 Reproducibility Scalability, HA, DR, and Monitoring

Reproducibility services shall scale with finding volume growth. High availability shall cover verification, evidence, and certification services. Disaster recovery shall preserve evidence, tier records, and verification history. Operations shall be continuously monitored.

---

## 9.7.14 Risks

The Reproducibility Architecture shall continuously assess risks including:

- Incomplete Capture — Reproducibility information insufficient for verification
- Verification False Positive — Verification passing despite actual differences
- Environment Obsolescence — Reproducibility environment becoming unavailable over time
- Data Version Loss — Original data versions becoming unavailable for reproduction
- Tier Inflation — Findings assigned higher reproducibility tier than justified
- Verification Resource Exhaustion — Compute resources insufficient for large-scale verification

Every identified risk shall include risk classification, impact assessment, likelihood assessment, detection method, mitigation strategy, recovery procedure, and ownership.

---

## 9.7.15 Acceptance Criteria

The Reproducibility Architecture shall be considered complete when the platform demonstrates:

- Standardized reproducibility requirements for every published finding
- Automated reproducibility verification with match assessment
- Three-tier reproducibility classification with governed assignment
- Reproducibility failure classification and remediation
- Reproducibility evidence integrated with metadata and lineage
- Reproducibility verification gating finding publication and production promotion
- Production-bound findings achieving Gold or Silver tier
- No technology-specific reproducibility assumptions per P-3

---

## 9.7.16 Cross References

This section shall be read together with Section 9.1 (Research Platform), Section 9.3 (Hypothesis Management), Section 9.4 (Research Experiments), Section 9.8 (Knowledge Management), Section 9.11 (Research Governance), Section 9.13 (Promotion), Document 11 (per D-7.4, D-7.7, D-7.8), Document 12 (per Sections 8.3, 8.5), and handbook/ARCHITECTURAL_INVARIANTS.md (per P-1, P-2, P-3, P-5, P-9, P-13, P-17).

---

# End of Section

---

# 9.8 Knowledge Management Architecture

## 9.8.1 Purpose

The Knowledge Management Architecture defines the canonical framework for capturing, organizing, discovering, and governing quantitative research knowledge as enterprise assets within the Quant Hub platform.

Research knowledge — hypotheses, findings, analyses, methodologies, insights, and reports — shall be treated as governed enterprise assets per the Knowledge as Enterprise Asset principle. Knowledge shall be captured at the point of creation, organized through governed taxonomies, discoverable through search and browse, and preserved for the lifecycle of the platform.

Knowledge management shall not embed strategy-specific assumptions per P-1. Knowledge artifacts shall be immutable after publication per P-2.

---

## 9.8.2 Scope

The Knowledge Management Architecture applies to all research knowledge within the Quant Hub platform.

Coverage includes:

- Knowledge Capture
- Knowledge Organization and Taxonomy
- Knowledge Discovery
- Knowledge Lifecycle
- Knowledge Versioning
- Knowledge Governance
- Knowledge Collaboration
- Literature Management
- Research Report Generation

---

## 9.8.3 Knowledge Artifact Model

Every research knowledge artifact shall be defined through a canonical specification.

Knowledge artifact specification shall include:

- Artifact Identifier — Globally unique knowledge artifact identifier
- Artifact Type — Hypothesis, Finding, Methodology, Insight, Report, Literature Review, or Analytical Note
- Title — Descriptive title
- Content — Structured or unstructured content of the artifact
- Abstract — Concise summary for discovery
- Source References — References to source experiments (Section 9.4), hypotheses (Section 9.3), datasets (Document 11), EDA sessions (Section 9.5), and other evidence
- Authors — Creator and contributor identities
- Taxonomy Classification — Organizational taxonomy per Section 9.8.4
- Version — Artifact version per Section 9.8.6
- Status — Current lifecycle state per Section 9.8.5
- Publication Date — Date of publication
- Reproducibility Tier — Reproducibility tier per Section 9.7.6
- Tags — Discovery and organizational tags

Knowledge artifacts shall be registered in the Document 11 Metadata Registry per D-7.7.3.

---

## 9.8.4 Knowledge Taxonomy

Research knowledge shall be organized through governed taxonomies.

Taxonomy dimensions shall include:

- Research Domain — Asset class (equities, forex, futures, options, crypto), research area (signal research, risk research, portfolio research, market microstructure)
- Methodology Type — Statistical analysis, machine learning, econometric modeling, simulation, backtesting
- Signal Type — Momentum, mean reversion, carry, volatility, sentiment, arbitrage
- Market Regime — Trending, ranging, high volatility, low volatility, crisis
- Time Horizon — Intraday, daily, weekly, monthly, quarterly

Taxonomies shall be extensible through governance processes.

Artifacts may be classified under multiple taxonomy dimensions.

---

## 9.8.5 Knowledge Lifecycle

Every knowledge artifact shall progress through governed lifecycle states.

Lifecycle states include:

- Draft — Artifact is being authored. Content may be modified.
- Review — Artifact is undergoing peer review or governance review per Section 9.11.
- Published — Artifact has been reviewed and published. Published artifacts are immutable per P-2.
- Updated — A new version of the artifact has been published. The previous version remains available for historical reference.
- Deprecated — Artifact content is no longer considered current but remains available for historical reference.
- Archived — Artifact is archived per Document 11 archiving infrastructure (D-7.6). Remains discoverable and recoverable per D-7.6.2.

Lifecycle transitions shall be governed with appropriate authorization.

---

## 9.8.6 Knowledge Versioning

Every knowledge artifact modification shall create a new version per P-2.

Versioning shall include version identifier, change description, version linkage to previous versions, and immutability of published versions. Knowledge version history shall remain available for reference and audit.

---

## 9.8.7 Knowledge Discovery

The platform shall provide comprehensive knowledge discovery services.

Discovery capabilities shall include:

- Full-Text Search — Search across all knowledge artifact content
- Taxonomy Browse — Hierarchical browsing by taxonomy dimensions
- Faceted Search — Filter by type, domain, methodology, author, date, reproducibility tier
- Related Knowledge — Discovery of related artifacts through taxonomy, lineage, and content similarity
- Recommendation — Suggested knowledge based on researcher activity and interests
- Citation Tracking — Tracking of how knowledge artifacts reference and are referenced by other artifacts

Discovery shall respect governance and security access controls.

---

## 9.8.8 Literature Management

The platform shall support management of external research literature.

Literature management shall include:

- Literature Registration — Registration of external papers, articles, and research
- Literature Annotation — Researcher annotations, summaries, and relevance assessments
- Literature-to-Research Linkage — Linkage between external literature and internal research hypotheses, experiments, and findings
- Literature Discovery — Search and browse of registered literature
- Reference Management — Citation management for research reports

Literature entries shall be governed as knowledge assets.

---

## 9.8.9 Research Report Generation

The platform shall support governed research report generation.

Report generation shall include:

- Report Templates — Governed templates for standardized report formats
- Automated Content Assembly — Automated assembly of report content from knowledge artifacts, experiment results, and statistical outputs
- Reproducibility Embedding — Reports shall include reproducibility information (code, data versions, environment)
- Report Versioning — Report versions governed per Section 9.8.6
- Report Publication — Published reports are immutable per P-2
- Report Distribution — Governed distribution to stakeholders

Reports shall clearly distinguish between exploratory findings and confirmatory conclusions.

---

## 9.8.10 Knowledge Collaboration

Knowledge artifacts shall support governed collaboration per Section 9.9.

Collaboration features shall include co-authoring with attribution, commenting and discussion threads on artifacts, peer review integration, and access control for collaborative authoring.

---

## 9.8.11 Knowledge Governance

Knowledge artifacts shall be governed through enterprise governance processes.

Governance shall include publication review and approval, taxonomy governance, quality standards enforcement, retention and archival governance, and immutable audit trail per P-5 for all knowledge lifecycle events.

---

## 9.8.12 Knowledge Security

Knowledge artifacts shall be protected through security controls extending Document 11 Section 7.12 including authentication for access, authorization governed by project and classification, encryption at rest per D-7.12.5, and access audit logging per P-5.

---

## 9.8.13 Knowledge Metrics

The platform shall maintain standardized knowledge metrics including artifact creation rate by type, publication throughput, discovery query volume, taxonomy coverage, cross-reference density, and researcher engagement metrics. Metrics shall be available through research dashboards per Section 9.15.

---

## 9.8.14 Knowledge Performance, Scalability, and Operations

Knowledge services shall satisfy performance objectives for search response time, browse latency, and publication processing. Services shall scale with artifact volume growth, discovery query volume, and concurrent access. High availability, DR, monitoring, alerting, and backup shall follow enterprise standards.

---

## 9.8.15 Knowledge Testing

Knowledge management shall satisfy testing requirements including functional testing (creation, lifecycle, versioning, discovery), integration testing (with hypotheses, experiments, reproducibility, governance), performance testing, and security testing.

---

## 9.8.16 Risks

The Knowledge Management Architecture shall continuously assess risks including:

- Knowledge Loss — Loss of research knowledge due to inadequate capture or preservation
- Discovery Failure — Inability to discover relevant existing knowledge leading to duplicated research
- Taxonomy Drift — Taxonomy becoming outdated or inconsistent over time
- Publication Quality Degradation — Inadequate review leading to low-quality published knowledge
- Version Confusion — Consumers referencing outdated knowledge versions
- Collaboration Conflict — Concurrent editing conflicts causing data loss

Every identified risk shall include risk classification, impact assessment, likelihood assessment, detection method, mitigation strategy, recovery procedure, and ownership.

---

## 9.8.17 Acceptance Criteria

The Knowledge Management Architecture shall be considered complete when the platform demonstrates:

- Standardized knowledge artifact model with governed taxonomy
- Full-text search and faceted discovery across all knowledge artifacts
- Governed lifecycle from Draft through Archived with immutable publication per P-2
- Knowledge versioning with complete history
- Literature management integrated with research workflows
- Automated research report generation with reproducibility embedding
- Knowledge treated as governed enterprise assets per P-17
- No strategy-specific knowledge taxonomies or assumptions per P-1

---

## 9.8.18 Cross References

This section shall be read together with Section 9.1 (Research Platform), Section 9.3 (Hypothesis Management), Section 9.4 (Research Experiments), Section 9.5 (EDA), Section 9.6 (Statistical Analysis), Section 9.7 (Reproducibility), Section 9.9 (Collaboration), Section 9.11 (Research Governance), Document 11 (per D-7.4, D-7.6, D-7.7, D-7.12), and handbook/ARCHITECTURAL_INVARIANTS.md (per P-1, P-2, P-5, P-17).

---

# End of Section

---

# 9.9 Research Collaboration Architecture

## 9.9.1 Purpose

The Research Collaboration Architecture defines the canonical framework for multi-user research collaboration within the Quant Hub platform.

Collaboration shall enable researchers to share workspaces, co-author analyses, conduct peer review, and collaborate on experiments and knowledge artifacts while maintaining governance, security, and reproducibility.

Collaboration shall not compromise workspace isolation or data access boundaries per Section 9.2.8 and Section 9.14.

---

## 9.9.2 Scope

The Research Collaboration Architecture applies to all collaborative research activities within the Quant Hub platform.

Coverage includes:

- Workspace Sharing
- Collaborative Editing
- Peer Review
- Co-Authoring
- Access Control
- Collaboration Governance
- Collaboration Notifications
- Collaboration Security

---

## 9.9.3 Collaboration Roles

Every collaboration participant shall be assigned a governed role.

Collaboration roles include:

- Owner — Full control over the shared resource. May modify access, invite collaborators, and manage lifecycle.
- Editor — May modify the shared resource. May not change access controls or manage lifecycle.
- Reviewer — May view and comment on the shared resource. May not modify content.
- Viewer — Read-only access to the shared resource. May not modify or comment.

Roles shall be assigned per shared resource. A user may have different roles on different resources.

Role assignment shall produce immutable governance records per P-2.

---

## 9.9.4 Peer Review Architecture

The platform shall implement formal peer review for research findings.

Peer review workflow shall include:

- Review Request — Author requests peer review of a finding or knowledge artifact
- Reviewer Assignment — Reviewer(s) assigned by governance or author with appropriate expertise
- Review Execution — Reviewer evaluates methodology, statistical validity, reproducibility, and conclusions
- Review Criteria — Standardized review criteria: methodology soundness, statistical validity, reproducibility, clarity, significance
- Review Decision — Accept, Accept with Revisions, Reject
- Review Evidence — Review comments, decisions, and reviewer identity recorded as immutable evidence per P-2
- Revision Handling — Authors may revise and resubmit for re-review

Peer review shall be required before research findings are published or promoted to production per Section 9.13.

---

## 9.9.5 Workspace Sharing

Research workspaces shall support governed sharing per Section 9.2.9.

Sharing shall include invitation workflow with time-bound access grants, role assignment per Section 9.9.3, access revocation by owner or governance authority, and sharing audit trail for all access grants and revocations.

Workspace sharing shall not bypass data classification boundaries per D-7.12.6.

---

## 9.9.6 Collaborative Editing

The platform shall support concurrent collaborative editing of research artifacts.

Collaborative editing shall include real-time or near-real-time concurrent access, change tracking with per-contributor attribution, conflict detection and resolution mechanisms, version creation on significant changes, and locking for critical sections where concurrent modification would cause conflicts.

Collaborative editing shall not compromise artifact versioning per Section 9.8.6.

---

## 9.9.7 Co-Authoring

Knowledge artifacts and research reports shall support co-authoring.

Co-authoring shall include multiple authors with attribution, author order governance, contribution tracking for each author, and author approval workflow before publication. Co-authoring shall produce immutable records of author contributions per P-2.

---

## 9.9.8 Access Control

Collaboration access shall be governed through enterprise access controls.

Access control shall include role-based access per Section 9.9.3, time-bound access grants with automatic expiration, project-scoped access boundaries, data classification-aware access per D-7.12.6, and access audit logging per P-5 for all access grants, modifications, and revocations.

---

## 9.9.9 Collaboration Notifications

The platform shall provide collaboration notifications.

Notification types shall include invitation notifications, role change notifications, review request and completion notifications, artifact modification notifications, comment and discussion notifications, and access expiration warnings.

Notifications shall be delivered through enterprise notification infrastructure.

---

## 9.9.10 Collaboration Governance

Research collaboration shall be governed through enterprise governance processes.

Governance shall include collaboration policy enforcement, peer review governance, access review (periodic review of active collaborations and access grants), collaboration audit trail per P-5, and dispute resolution procedures.

---

## 9.9.11 Collaboration Security

Collaboration shall implement security controls including authentication for all collaboration actions per D-9, authorization for access grants and modifications, encryption of collaboration data, and prevention of collaboration bypassing data classification boundaries per D-7.12.6.

---

## 9.9.12 Collaboration Metrics

Collaboration metrics shall include active collaborations, peer review throughput and decision distribution, collaborative artifact creation rate, and collaboration engagement metrics. Metrics shall be available through research dashboards per Section 9.15.

---

## 9.9.13 Collaboration Performance, Scalability, and Operations

Collaboration services shall satisfy performance objectives for real-time collaboration latency and review workflow processing. Services shall scale with concurrent collaborations and active users. High availability, DR, monitoring, alerting, and backup shall follow enterprise standards.

---

## 9.9.14 Risks

The Research Collaboration Architecture shall continuously assess risks including:

- Unauthorized Access — Collaborator gaining access beyond authorized role or scope
- Access Creep — Accumulation of stale collaboration access grants over time
- Collaboration Conflict — Concurrent edits causing data loss or inconsistency
- Review Quality Degradation — Inadequate peer review compromising research quality
- Collaboration Bypass — Researchers sharing data or findings outside governed collaboration channels
- Notification Overload — Excessive collaboration notifications causing alert fatigue

Every identified risk shall include risk classification, impact assessment, likelihood assessment, detection method, mitigation strategy, recovery procedure, and ownership.

---

## 9.9.15 Acceptance Criteria

The Research Collaboration Architecture shall be considered complete when the platform demonstrates:

- Role-based collaboration with Owner, Editor, Reviewer, and Viewer roles
- Formal peer review workflow with standardized criteria and immutable evidence
- Governed workspace sharing with time-bound access grants
- Collaborative editing with change attribution and conflict resolution
- Co-authoring with contribution tracking and author approval
- Access control respecting data classification boundaries per D-7.12.6
- Complete audit trail for all collaboration actions per P-5

---

## 9.9.16 Cross References

This section shall be read together with Section 9.1 (Research Platform), Section 9.2 (Research Workspace), Section 9.4 (Research Experiments), Section 9.8 (Knowledge Management), Section 9.11 (Research Governance), Section 9.14 (Research Security), Document 11 (per D-7.12), and handbook/ARCHITECTURAL_INVARIANTS.md (per P-1, P-2, P-5, P-17).

---

# End of Section

---

# 9.10 Research Artifact Management

## 9.10.1 Purpose

The Research Artifact Management Architecture defines the canonical framework for managing research artifacts — notebooks, scripts, reports, datasets, results, and visualizations — as governed enterprise assets within the Quant Hub platform.

Every research artifact shall be versioned, governed, discoverable, and preserved. Artifacts shall be treated as first-class governed assets per P-17.

Artifact management shall integrate with Document 11 storage, metadata, lineage, and governance infrastructure without redefining them per P-9.

---

## 9.10.2 Scope

The Research Artifact Management Architecture applies to all research artifacts within the Quant Hub platform.

Coverage includes:

- Artifact Types and Models
- Artifact Storage
- Artifact Versioning
- Artifact Lifecycle
- Artifact Discovery
- Artifact Governance
- Artifact Security

The following topics are intentionally excluded:

- Data storage infrastructure — Frozen per Document 11 (D-7.1)
- ML model artifacts — Owned by Document 12 (Section 8.6)
- Knowledge artifacts — Owned by Section 9.8 (integrated but distinct)

---

## 9.10.3 Artifact Model

Every research artifact shall be defined through a canonical specification.

Artifact specification shall include:

- Artifact Identifier — Globally unique artifact identifier
- Artifact Type — Notebook, Script, Report, Dataset, Result Set, Visualization, Configuration, or Other
- Artifact Format — File format, encoding, and structure information
- Content Reference — Storage location reference through Document 11 storage infrastructure
- Provenance — Creator identity, creation timestamp, source experiment (Section 9.4), source workspace (Section 9.2)
- Version — Artifact version per Section 9.10.4
- Dependencies — References to code versions, data versions, environment specifications, and other artifacts
- Checksum — Cryptographic hash for integrity verification
- Size — Artifact size
- Status — Current lifecycle state per Section 9.10.5
- Tags — Discovery and organizational tags

Artifacts shall be registered in the Document 11 Metadata Registry per D-7.7.3.

---

## 9.10.4 Artifact Versioning

Every artifact modification shall create a new version per P-2.

Versioning shall include deterministic version identifier, change description, version linkage to source experiment and workspace versions, and immutability of published versions. Historical artifact versions shall remain available for reproducibility per Section 9.7.

---

## 9.10.5 Artifact Lifecycle

Artifact lifecycle states shall include:

- Draft — Artifact is being created. May be modified.
- Published — Artifact is published and immutable per P-2.
- Deprecated — Artifact is no longer current but remains available for reference.
- Archived — Artifact is archived per Document 11 (D-7.6). Remains discoverable and recoverable per D-7.6.2.
- Destroyed — Artifact is securely destroyed per Document 11 (D-7.4.4). Metadata and version history are preserved for audit.

Lifecycle transitions shall be governed with appropriate authorization.

---

## 9.10.6 Artifact Storage

Research artifacts shall be stored through Document 11 storage infrastructure per D-7.1.

Storage shall include storage tier selection based on artifact lifecycle state, integrity verification using checksums, format governance for long-term accessibility, and cost optimization through tier transitions per Document 11 Section 7.6.

---

## 9.10.7 Artifact Discovery

The platform shall provide artifact discovery services including search by name, type, provenance, experiment, workspace, and tags; browse by artifact type and research domain; dependency visualization; and lineage browsing. Discovery shall integrate with knowledge management discovery per Section 9.8.7 and respect governance and security access controls.

---

## 9.10.8 Artifact Governance

Research artifacts shall be governed through enterprise governance processes.

Governance shall include artifact registration governance, lifecycle transition governance, retention and archival governance, quality standards enforcement, and immutable audit trail per P-5 for all artifact lifecycle events.

---

## 9.10.9 Artifact Security

Research artifacts shall be protected through security controls including authentication for access per D-9, authorization governed by project and classification per D-7.12.6, encryption at rest per D-7.12.5, integrity verification using checksums, and access audit logging per P-5.

---

## 9.10.10 Artifact Integration

Artifact management shall integrate with Workspaces (Section 9.2 — artifacts accessible within workspaces), Experiments (Section 9.4 — experiment output artifacts), Knowledge Management (Section 9.8 — knowledge artifacts as specialized artifact types), and Reproducibility (Section 9.7 — artifact versions as reproducibility evidence).

---

## 9.10.11 Artifact Metrics

Artifact metrics shall include artifact creation rate by type, storage consumption by type and project, version frequency, discovery query volume, and retention compliance. Metrics shall be available through research dashboards per Section 9.15.

---

## 9.10.12 Artifact Performance, Scalability, and Operations

Artifact services shall satisfy performance objectives for upload throughput, download latency, and discovery query response. Services shall scale with artifact volume growth. High availability, DR, monitoring, alerting, and backup shall follow enterprise standards.

---

## 9.10.13 Artifact Testing

Artifact management shall satisfy testing requirements including functional testing (creation, versioning, lifecycle, discovery), integration testing, performance testing, and security testing.

---

## 9.10.14 Risks

The Research Artifact Management Architecture shall continuously assess risks including:

- Artifact Corruption — Storage corruption causing artifact data loss
- Version Confusion — Consumers referencing outdated or incorrect artifact versions
- Dependency Breakage — Artifact references becoming invalid due to upstream changes
- Storage Exhaustion — Uncontrolled artifact growth exceeding storage capacity
- Integrity Failure — Checksum mismatch indicating artifact tampering or corruption
- Discovery Gap — Inability to find relevant artifacts due to inadequate metadata or taxonomy

Every identified risk shall include risk classification, impact assessment, likelihood assessment, detection method, mitigation strategy, recovery procedure, and ownership.

---

## 9.10.15 Acceptance Criteria

The Research Artifact Management Architecture shall be considered complete when the platform demonstrates:

- Standardized artifact model with provenance and dependency tracking
- Artifact versioning with immutable published versions per P-2
- Governed artifact lifecycle from Draft through Destroyed
- Artifact storage through Document 11 infrastructure with integrity verification
- Artifact discovery integrated with knowledge management
- Artifact governance with lifecycle and retention policies
- Integration with workspaces, experiments, and reproducibility
- No duplication of Document 11 storage or metadata infrastructure per P-9

---

## 9.10.16 Cross References

This section shall be read together with Section 9.1 (Research Platform), Section 9.2 (Research Workspace), Section 9.4 (Research Experiments), Section 9.7 (Reproducibility), Section 9.8 (Knowledge Management), Document 11 (per D-7.1, D-7.4, D-7.6, D-7.7, D-7.12), and handbook/ARCHITECTURAL_INVARIANTS.md (per P-1, P-2, P-5, P-9, P-17).

---

# End of Section

---

# 9.11 Research Governance Architecture

## 9.11.1 Purpose

The Research Governance Architecture defines the canonical governance framework for all quantitative research activities within the Quant Hub platform.

Research governance shall ensure that research activities comply with platform principles, statistical standards, ethical guidelines, and enterprise policies. Governance shall provide accountability, auditability, and quality assurance for every research finding, hypothesis, experiment, and knowledge artifact.

Governance shall enforce the separation of exploratory and confirmatory analysis — preventing HARKing, p-hacking, and selective reporting. Governance shall gate publishing and production promotion decisions.

The governance framework itself shall be governed — governance processes and rules shall be documented, versioned, and subject to review per P-17.

---

## 9.11.2 Scope

The Research Governance Architecture applies to every research activity and artifact within the Quant Hub platform.

Coverage includes:

- Hypothesis Registration Governance
- Experiment Governance
- Analysis Methodology Governance
- Statistical Governance
- Reproducibility Governance
- Peer Review Governance
- Publication Governance
- Promotion Governance
- Collaboration Governance
- Audit Governance
- Policy Management
- Anomaly Detection and Enforcement

The following topics are intentionally excluded:

- General enterprise governance — Frozen per Document 11 (D-7.11)
- Data governance — Frozen per Document 11 (D-7.7)
- Model governance — Owned by Document 12 (Section 8.10)
- Trading governance — Owned by Document 14

---

## 9.11.3 Governance Principles

Research governance shall be founded on platform principles.

Governance principles include:

- Pre-Registration — Hypotheses and analysis plans shall be registered before confirmatory analysis per Section 9.3.5
- Immutability — Published research records shall be immutable per P-2
- Reproducibility — Published findings shall be reproducible per Section 9.7
- Transparency — All analytical decisions, data transformations, and methodology choices shall be documented
- Accountability — Every research action shall be attributable to a specific identity
- Auditability — Every research action shall produce immutable audit records per P-5
- Separation of Concerns — Exploratory and confirmatory analysis shall be clearly distinguished per the Separation of Exploratory and Confirmatory principle

---

## 9.11.4 Hypothesis Registration Governance

Hypothesis registration shall be governed to prevent HARKing.

Governance controls shall include:

- Registration Gate — Hypothesis shall be registered before confirmatory analysis on data that will test it
- Completeness Validation — Automated validation that hypothesis specification is complete per Section 9.3.3
- Methodology Review — Statistical methodology review for appropriateness and completeness
- Immutability Enforcement — Registered hypothesis fundamentals shall be immutable per P-2
- Registration Audit — Every hypothesis registration shall produce immutable audit records
- Violation Detection — Detection of hypothesis modifications after registration or confirmatory analysis without pre-registration

---

## 9.11.5 Experiment Governance

Research experiments shall be governed to ensure validity and reproducibility.

Governance controls shall include:

- Experiment Registration — Experiments shall be registered with hypothesis linkage before execution
- Methodology Validation — Experiment methodology validated for appropriateness
- Parameter Freeze — Experiment parameters frozen during execution — modification requires new experiment version
- Reproducibility Verification — Completed experiments shall have reproducibility verified per Section 9.7
- Results Validation — Experiment results validated against pre-registered success criteria
- Immutability Enforcement — Completed experiment records shall be immutable per P-2

---

## 9.11.6 Analysis Methodology Governance

Analysis methodology shall be governed through the Statistical Analysis Framework.

Governance shall include:

- Statistical Test Registry Governance — Approval and versioning of statistical tests in the registry per Section 9.6.3
- Multiple Testing Governance — Enforcement of multiple testing correction per Section 9.6.5
- P-Hacking Detection — Detection and flagging of potential p-hacking behaviors per Section 9.6.6
- Power Analysis Governance — Power analysis required for confirmatory research per Section 9.6.7
- Methodology Drift Detection — Comparison of executed analysis against pre-registered plan

Deviations from pre-registered methodology shall be documented, justified, and subject to governance review.

---

## 9.11.7 Statistical Governance

Statistical governance shall enforce statistical standards across all research.

Governance shall include:

- Significance Governance — Enforcing pre-registered significance levels and preventing threshold shopping
- Effect Size Governance — Requiring effect size reporting alongside significance per Section 9.6.8
- Reporting Governance — Enforcing complete reporting of all tests, including non-significant results per Section 9.6.11
- Prior Governance — Bayesian priors shall be pre-registered and justified per Section 9.6.9
- Assumption Verification — Validating statistical test assumptions before application per Section 9.6.4

Statistical governance shall integrate with hypothesis validation per Section 9.3.7.

---

## 9.11.8 Reproducibility Governance

Reproducibility shall be governed per Section 9.7 with tier assignment governance, verification governance, failure escalation procedures, publication gating (verification required before publication), and promotion gating for production-bound findings.

---

## 9.11.9 Peer Review Governance

Peer review shall be governed for quality assurance per Section 9.9.4.

Governance shall include review requirement enforcement before publication, reviewer qualification standards, review criteria standardization, review evidence governance (immutable records per P-2), and appeal procedures for disputed decisions.

---

## 9.11.10 Publication Governance

Research findings and knowledge artifacts shall be governed at publication.

Governance shall include:

- Publication Prerequisites — Hypothesis registration, experiment completion, reproducibility verification, peer review completion, and statistical compliance verification
- Publication Review — Governance review of findings before publication for methodology soundness, statistical validity, and reproducibility evidence
- Publication Decision — Approve, Revise, or Reject
- Publication Immutability — Published findings shall be immutable per P-2
- Publication Audit — Publication decisions and evidence recorded per P-5

---

## 9.11.11 Promotion Governance

Research findings promoted to production shall be governed per Section 9.13.

Governance shall include promotion prerequisites, promotion review, promotion decision, promotion evidence, promotion audit, and rollback procedures for failed promotions.

---

## 9.11.12 Policy Management

Research governance policies shall be managed as governed artifacts.

Policy management shall include:

- Policy Definition — Policies defined with scope, rules, enforcement mechanisms, and exceptions
- Policy Versioning — Policy versions governed per P-2
- Policy Review — Periodic policy review for relevance and effectiveness
- Policy Enforcement — Automated enforcement of applicable policies
- Policy Exception Handling — Governed exception process with documentation and approval

Policy management shall integrate with Document 11 governance infrastructure per D-7.11.

---

## 9.11.13 Anomaly Detection and Enforcement

The governance platform shall implement automated anomaly detection for research integrity.

Detection mechanisms shall include p-hacking detection, hypothesis drift detection, selective reporting detection, reproducibility failure escalation, methodological non-compliance detection, and collaboration anomaly detection.

Detected anomalies shall trigger alerting, investigation, and governance enforcement actions.

---

## 9.11.14 Policy Configuration and Governance Interfaces

The platform shall provide policy configuration interfaces enabling governance administrators to define and update research governance policies, configure enforcement automation parameters, review detected anomalies, approve exceptions, and access governance dashboards and reports.

Policy configuration changes shall themselves be governed.

---

## 9.11.15 Governance Audit

Every governance action shall produce immutable audit records per P-5.

Audit records shall include governance decision type, decision rationale, approving authority, affected research artifacts, timestamp, and evidence references. Audit trails shall be comprehensive, immutable, and queryable.

---

## 9.11.16 Governance Dashboards

The platform shall provide governance dashboards per Section 9.15.

Dashboard content shall include governance compliance metrics, anomaly detection statistics, peer review throughput and decisions, publication and promotion pipeline status, methodology compliance rates, and reproducibility tier distribution. Dashboards shall support governance oversight and continuous improvement.

---

## 9.11.17 Governance Integration

Research governance shall integrate with Document 11 governance infrastructure per D-7.11, Document 12 model governance (Section 8.10), and enterprise identity and access management per D-2. Integration shall extend without redefining frozen governance infrastructure per P-10.

---

## 9.11.18 Governance Security

Research governance shall be secured through authentication per D-9, authorization for governance actions, integrity protection for governance records, and comprehensive audit logging per P-5 including all governance decisions.

---

## 9.11.19 Governance Performance, Scalability, and Operations

Governance services shall satisfy performance objectives for policy evaluation latency and audit record processing. Services shall scale with research volume growth. High availability, DR, monitoring, alerting, and backup shall follow enterprise standards.

---

## 9.11.20 Risks

The Research Governance Architecture shall continuously assess risks including:

- Governance Bypass — Research conducted outside governed channels
- Policy Staleness — Governance policies becoming outdated relative to research practice
- False Positive Anomalies — Excessive false positive anomaly detection causing governance fatigue
- Review Bottleneck — Governance review becoming a bottleneck for research throughput
- Audit Integrity — Audit records being tampered with or lost
- Exception Abuse — Governance exceptions granted without adequate justification

Every identified risk shall include risk classification, impact assessment, likelihood assessment, detection method, mitigation strategy, recovery procedure, and ownership.

---

## 9.11.21 Acceptance Criteria

The Research Governance Architecture shall be considered complete when the platform demonstrates:

- Hypothesis pre-registration enforced before confirmatory analysis
- Experiment governance with parameter freeze and reproducibility verification
- Statistical governance enforcing multiple testing correction and complete reporting
- Publication governance with methodological and statistical compliance verification
- Promotion governance gating production-bound findings
- Automated anomaly detection for p-hacking, hypothesis drift, and selective reporting
- Comprehensive audit trail for all governance decisions per P-5
- Policy management with governed versioning and exception handling
- Integration with Document 11 governance without redefinition per P-10

---

## 9.11.22 Cross References

This section shall be read together with Section 9.1 (Research Platform), Section 9.3 (Hypothesis Management), Section 9.4 (Research Experiments), Section 9.6 (Statistical Analysis), Section 9.7 (Reproducibility), Section 9.9 (Collaboration), Section 9.13 (Research-to-Production Promotion), Section 9.14 (Research Security), Section 9.15 (Research Observability), Document 11 (per D-2, D-9, D-7.7, D-7.11, D-7.12), Document 12 (per Section 8.7), and handbook/ARCHITECTURAL_INVARIANTS.md (per P-1, P-2, P-5, P-10, P-17).

---

# End of Section

---

# 9.12 Research Lifecycle Architecture

## 9.12.1 Purpose

The Research Lifecycle Architecture defines the end-to-end research lifecycle from ideation through archival. It coordinates the lifecycles of individual research components — hypotheses (Section 9.3), experiments (Section 9.4), and knowledge artifacts (Section 9.8) — into a unified research project lifecycle with governed phase transitions.

The research lifecycle shall extend Document 11 Section 7.4 Data Lifecycle without redefining it. The lifecycle shall provide the temporal and governance framework positioning every research activity within the research platform.

The lifecycle is strategy-agnostic per P-1. No phase shall embed assumptions about specific strategies, asset classes, or research domains.

---

## 9.12.2 Scope

The Research Lifecycle Architecture applies to every research project within the Quant Hub platform.

Coverage includes:

- Research Project Lifecycle
- Lifecycle Phase Coordination
- Lifecycle Governance
- Lifecycle Monitoring
- Lifecycle Archival and Retirement

The following topics are intentionally excluded:

- Data lifecycle — Frozen per Document 11 (D-7.4)
- ML lifecycle — Owned by Document 12 (Section 8.12)
- Individual component lifecycles — Defined in Sections 9.3.4 (hypotheses), 9.4.4 (experiments), 9.8.5 (knowledge)

---

## 9.12.3 Research Project Lifecycle

Every research project shall progress through governed lifecycle phases.

Research project lifecycle phases include:

- Ideation — Research problem identification, literature review, hypothesis generation, and feasibility assessment
- Exploration — Exploratory data analysis, initial experimentation, and methodology development per Section 9.5
- Validation — Confirmatory analysis, statistical validation, reproducibility verification, and peer review
- Publication — Research finding publication, knowledge artifact creation, and stakeholder communication
- Promotion — Governed promotion of validated findings to production per Section 9.13
- Production Integration — Finding integrated into production workflows; post-promotion monitoring
- Archived — Project archived per Document 11 (D-7.6). Remains discoverable and recoverable
- Retired — Project fully retired. Metadata and history preserved

Phase transitions shall be governed with explicit approval per Section 9.11.

---

## 9.12.4 Ideation Phase

The Ideation phase encompasses research problem identification through initial hypothesis formulation.

Ideation activities include:

- Problem Identification — Clear articulation of the research question and its significance
- Literature Review — Review of existing research literature per Section 9.8.8
- Hypothesis Generation — Initial hypothesis formulation per Section 9.3
- Feasibility Assessment — Assessment of data availability, methodology, and resource requirements
- Ideation Artifacts — Ideation captured as governed knowledge artifacts per Section 9.8

Ideation transitions to Exploration upon feasibility confirmation and governance approval.

---

## 9.12.5 Exploration Phase

The Exploration phase encompasses exploratory analysis and methodology development.

Exploration activities include:

- Exploratory Data Analysis — EDA sessions per Section 9.5 producing insights and hypothesis candidates
- Methodology Development — Development and refinement of analysis methodology
- Initial Experimentation — Preliminary experiments to assess methodology feasibility
- Insight Capture — Formal insight capture per Section 9.5.4 bridging to hypothesis refinement
- Exploration Governance — Governance appropriate to exploratory intent per Section 9.11

Exploration transitions to Validation upon methodology confirmation and hypothesis formalization.

The exploratory-confirmatory distinction shall be maintained — findings from Exploration are hypothesis-generating, not hypothesis-validating.

---

## 9.12.6 Validation Phase

The Validation phase encompasses confirmatory analysis and statistical validation.

Validation activities include:

- Hypothesis Registration — Hypothesis formally registered per Section 9.3.5 before confirmatory analysis
- Experiment Execution — Governed experiment execution per Section 9.4
- Statistical Validation — Statistical analysis per Section 9.6 with multiple testing correction and complete reporting
- Reproducibility Verification — Reproducibility verification per Section 9.7
- Peer Review — Formal peer review per Section 9.9.4
- Validation Governance — Governance rigor appropriate to production intent per Section 9.11

Validation transitions to Publication upon successful validation, peer review, and governance approval.

---

## 9.12.7 Publication Phase

The Publication phase encompasses research finding publication and knowledge dissemination.

Publication activities include:

- Finding Publication — Research finding published as governed knowledge artifact per Section 9.8
- Report Generation — Research report generation per Section 9.8.9
- Artifact Publication — All supporting artifacts published per Section 9.10
- Stakeholder Communication — Governed distribution to stakeholders
- Publication Immutability — Published findings immutable per P-2

Publication transitions to Promotion for production-bound findings or directly to Archived for non-production findings.

---

## 9.12.8 Promotion Phase

The Promotion phase encompasses governed transition of validated findings to production.

Promotion activities include:

- Promotion Request — Promotion initiated with evidence submission per Section 9.13
- Promotion Review — Governance review of promotion evidence, risk assessment, and operational readiness
- Promotion Execution — Governed promotion through destination-specific gates
- Post-Promotion Monitoring — Post-promotion monitoring per Section 9.13.10

Promotion transitions to Production Integration upon successful promotion.

Failed promotions may return to Validation for further analysis or proceed to Archived.

---

## 9.12.9 Production Integration Phase

The Production Integration phase encompasses ongoing monitoring after successful promotion.

Integration activities include:

- Production Registration — Promoted findings registered in production platforms per Section 9.13.9
- Performance Monitoring — Production performance tracked against research expectations
- Drift Detection — Detection of performance drift from research baseline
- Feedback Loop — Production observability feeding back into research for continuous improvement
- Rollback Readiness — Rollback procedures maintained per Section 9.13.8

Production Integration may transition to Archived or Retired based on production lifecycle.

---

## 9.12.10 Lifecycle Phase Coordination

The research project lifecycle shall coordinate individual component lifecycles.

Coordination shall include:

- Hypothesis Lifecycle — Aligned within the research project lifecycle per Section 9.3.4
- Experiment Lifecycle — Experiments scoped to appropriate project phases per Section 9.4.4
- Knowledge Lifecycle — Knowledge artifacts published at appropriate phases per Section 9.8.5
- Artifact Lifecycle — Artifacts governed within the project lifecycle per Section 9.10.5
- Phase Gate Synchronization — Project phase transitions synchronized with component lifecycle states

Phase coordination shall prevent lifecycle inconsistencies.

---

## 9.12.11 Lifecycle Governance

Research project lifecycle transitions shall be governed per Section 9.11.

Governance shall include:

- Phase Transition Approval — Every phase transition shall require explicit approval with documented rationale
- Transition Evidence — Evidence required for transition: artifacts, validation results, review outcomes
- Transition Audit — All phase transitions recorded as immutable evidence per P-2
- Exception Handling — Governed exception process for accelerated or modified transitions
- Lifecycle Policy — Lifecycle policy defined per Section 9.11.12

Phase transitions shall not bypass governance gates per P-8.

---

## 9.12.12 Lifecycle Monitoring

Research project lifecycle shall be continuously monitored.

Monitoring shall include:

- Phase Duration — Time spent in each lifecycle phase
- Transition Success Rate — Phase transition approval and failure rates
- Project Velocity — Overall time from Ideation to Production Integration
- Bottleneck Detection — Identification of lifecycle phase bottlenecks
- Lifecycle Compliance — Compliance with lifecycle governance requirements

Monitoring results shall feed into continuous improvement per Section 9.15.

---

## 9.12.13 Lifecycle Archival and Retirement

Research projects shall be archived and retired through governed processes.

Archival shall include:

- Project Archival — Complete project state archived per Document 11 (D-7.6)
- Component Archival — Hypotheses, experiments, knowledge, and artifacts archived
- Discoverability — Archived projects remain discoverable per D-7.6.2
- Recoverability — Archived projects recoverable for reference or re-activation

Retirement shall include final state preservation, metadata retention, and audit trail preservation.

Archival and retirement shall not destroy research knowledge per P-17.

---

## 9.12.14 Risks

The Research Lifecycle Architecture shall continuously assess risks including:

- Phase Stagnation — Research projects stuck in a phase without progression
- Premature Transition — Projects transitioning to advanced phases without satisfying prerequisites
- Lifecycle Bypass — Projects progressing outside governed lifecycle
- Coordination Failure — Component lifecycles becoming inconsistent with project lifecycle
- Archival Loss — Research knowledge lost during archival or retirement
- Velocity Degradation — Lifecycle governance creating excessive research delays

Every identified risk shall include risk classification, impact assessment, likelihood assessment, detection method, mitigation strategy, recovery procedure, and ownership.

---

## 9.12.15 Acceptance Criteria

The Research Lifecycle Architecture shall be considered complete when the platform demonstrates:

- Eight-phase research project lifecycle from Ideation through Retired
- Governed phase transitions with explicit approval and evidence requirements
- Phase coordination with hypothesis, experiment, knowledge, and artifact lifecycles
- Exploratory-confirmatory distinction maintained across lifecycle phases
- Lifecycle monitoring with phase duration and transition metrics
- Archival and retirement preserving research knowledge per P-17
- No strategy-specific lifecycle assumptions per P-1

---

## 9.12.16 Cross References

This section shall be read together with Section 9.1 (Research Platform), Section 9.3 (Hypothesis Management), Section 9.4 (Research Experiments), Section 9.5 (EDA), Section 9.8 (Knowledge Management), Section 9.10 (Artifact Management), Section 9.11 (Research Governance), Section 9.13 (Promotion), Document 11 (per D-7.4, D-7.6), Document 12 (Section 8.12), and handbook/ARCHITECTURAL_INVARIANTS.md (per P-1, P-2, P-8, P-17).

---

# End of Section

---

# 9.13 Research-to-Production Promotion Architecture

## 9.13.1 Purpose

The Research-to-Production Promotion Architecture defines the canonical framework for transitioning research findings from the research platform into production trading workflows.

Promotion bridges research and production. A research finding — a hypothesis validated through governed experiments, peer review, and reproducibility verification — shall be promoted to production through a governed promotion pipeline. Promotion shall require evidence that the finding meets production-level quality, robustness, and governance standards.

Promotion is not automatic. Every promotion shall require governance approval. Failed promotions shall require documented rationale. Promotion establishes lineage between the research finding and the production artifact.

The promotion framework shall not embed strategy-specific assumptions per P-1. Promotion decisions shall be centered on evidence, governance, and risk assessment — not on the nature of the underlying strategy.

---

## 9.13.2 Scope

The Research-to-Production Promotion Architecture applies to every research finding promoted to production within the Quant Hub platform.

Coverage includes:

- Promotion Criteria
- Promotion Pipeline
- Promotion Governance
- Promotion Evidence
- Promotion Lineage
- Promotion Rollback
- Promotion Monitoring
- Promotion Audit

---

## 9.13.3 Promotion Criteria

A research finding shall satisfy promotion criteria before entering the promotion pipeline.

Promotion criteria shall include:

- Validated Hypothesis — Hypothesis has been validated per Section 9.3.7 with statistical significance meeting pre-registered criteria
- Completed Experiments — All required experiments completed with reproducible results per Section 9.4
- Reproducibility Verification — Finding achieved Gold or Silver reproducibility tier per Section 9.7.6
- Peer Review Approval — Finding has passed peer review per Section 9.9.4
- Lifecycle Phase Completion — Research project has completed Validation and Publication phases per Section 9.12
- Governance Approval — Research governance approval per Section 9.11
- Risk Assessment — Production risk assessment completed and acceptable
- Operational Readiness — Operational requirements for production deployment defined

Promotion criteria shall be evaluated and recorded as promotion evidence.

---

## 9.13.4 Promotion Pipeline

Research findings shall progress through a governed promotion pipeline.

Promotion pipeline stages include:

- Promotion Request — Promotion initiated with evidence submission
- Promotion Review — Governance review of promotion evidence, risk assessment, and operational readiness
- Pre-Production — Finding deployed to pre-production environment for operational validation
- Production — Finding promoted to production after successful pre-production validation
- Monitoring — Post-promotion monitoring for operational performance per Section 9.13.10

Each stage shall gate progression to the next stage. Failed stages shall require remediation.

---

## 9.13.5 Promotion Governance

Promotion shall be governed through enterprise governance processes per Section 9.11.

Governance shall include:

- Promotion Decision Authority — Defined roles authorized to approve promotions
- Evidence-Based Decision — Promotion decisions based on evidence, not intuition or preference
- Risk-Benefit Assessment — Formal risk-benefit assessment for every promotion
- Staged Approval — Progressive approval at each promotion stage
- Promotion Audit — Every promotion decision recorded as immutable evidence per P-2
- Exception Handling — Governed exception process for time-sensitive or experimental promotions

Governance decisions shall be recorded with rationale per P-5.

---

## 9.13.6 Promotion Evidence

Every promotion shall produce evidence documenting the transition from research to production.

Evidence shall include:

- Research Finding Summary — Summary of the finding, hypothesis, experiments, and conclusions
- Validation Evidence — Statistical validation results per Section 9.3.7
- Reproducibility Evidence — Reproducibility tier and verification results per Section 9.7.4
- Peer Review Evidence — Peer review decision and comments per Section 9.9.4
- Lifecycle Evidence — Lifecycle phase completion evidence per Section 9.12
- Risk Assessment — Production risk assessment
- Operational Readiness — Deployment requirements, monitoring requirements, and rollback plan
- Governance Approval — Approval records for each promotion stage

Promotion evidence shall be immutable per P-2.

---

## 9.13.7 Promotion Lineage

Every production artifact shall maintain lineage to its source research finding.

Lineage shall include:

- Source Finding Reference — Reference to the promoted research finding
- Source Hypothesis — Reference to the validated hypothesis
- Source Experiments — References to the experiments that produced the evidence
- Source Data — References to Document 11 datasets used in research
- Promotion Evidence — Reference to the promotion evidence package
- Promotion Decisions — Governance decisions throughout the promotion pipeline
- Production Artifact — Reference to the resulting production artifact

Promotion lineage shall integrate with Document 11 Lineage Architecture per D-5.

---

## 9.13.8 Promotion Rollback

The platform shall support governed rollback of promotions.

Rollback scenarios include:

- Operational Failure — Promoted finding fails in production
- Performance Degradation — Finding underperforms relative to expectations
- Governance Reversal — Governance review determines promotion was premature
- Risk Escalation — Risk profile of the finding exceeds acceptable thresholds

Rollback shall include documented rationale, evidence preservation, and production artifact status update. Rolled back findings shall remain in the research platform for further analysis and potential re-promotion.

Rollback decisions shall be governed and audited per P-5.

---

## 9.13.9 Production Artifact Registration

Upon promotion, production artifacts shall be registered in production platforms.

Registration shall include registration in Document 14 Trading Infrastructure Architecture, registration with Document 11 Metadata Registry, linkage to research lineage, and assignment of production owners and operational responsibility.

Production artifacts shall be governed as production assets per Document 14.

---

## 9.13.10 Post-Promotion Monitoring

Promoted findings shall be monitored in production per P-15.

Monitoring shall include:

- Performance Monitoring — Production performance tracked against research expectations
- Drift Detection — Detection of performance drift from research baseline
- Incident Management — Production incidents attributed to promoted findings
- Ongoing Validation — Periodic re-validation of continued finding validity

Monitoring results shall feed back into research for continuous improvement and potential rollback decisions.

---

## 9.13.11 Promotion Reporting

The platform shall generate promotion reports.

Reports shall include promotion pipeline throughput and cycle time, promotion success and failure rates by research domain, promotion evidence completeness metrics, rollback frequency and causes, and post-promotion performance comparison. Reports shall be governed artifacts per Section 9.10.

---

## 9.13.12 Promotion Metrics

Promotion metrics shall include promotion request rate, promotion approval rate, promotion time from request to production, pre-production pass rate, rollback rate, and post-promotion performance drift. Metrics shall be available through research dashboards per Section 9.15.

---

## 9.13.13 Promotion Security

Promotion shall implement security controls including authentication per D-9, authorization for promotion decisions, integrity protection for promotion evidence, and audit logging per P-5 for all promotion actions.

---

## 9.13.14 Promotion Performance, Scalability, and Operations

Promotion services shall satisfy performance objectives for pipeline processing latency. Services shall scale with promotion volume growth. High availability, DR, and monitoring shall follow enterprise standards.

---

## 9.13.15 Risks

The Research-to-Production Promotion Architecture shall continuously assess risks including:

- Premature Promotion — Finding promoted without sufficient validation or governance approval
- Promotion Bypass — Research findings deployed to production outside the govern promotion pipeline
- Evidence Incompleteness — Promotion proceeding with incomplete or insufficient evidence
- Post-Promotion Drift — Production performance significantly diverging from research expectations
- Rollback Failure — Inability to safely rollback a failed promotion
- Lineage Break — Loss of traceability between production artifacts and source research

Every identified risk shall include risk classification, impact assessment, likelihood assessment, detection method, mitigation strategy, recovery procedure, and ownership.

---

## 9.13.16 Acceptance Criteria

The Research-to-Production Promotion Architecture shall be considered complete when the platform demonstrates:

- Governed promotion criteria including hypothesis validation, reproducibility, peer review, and quality
- Multi-stage promotion pipeline from request through post-promotion monitoring
- Evidence-based promotion decisions with audit trail per P-5
- Promotion lineage connecting production artifacts to source research
- Governed rollback procedures for failed promotions
- Post-promotion performance monitoring with drift detection
- No strategy-specific promotion assumptions per P-1

---

## 9.13.17 Cross References

This section shall be read together with Section 9.1 (Research Platform), Section 9.3 (Hypothesis Management), Section 9.4 (Research Experiments), Section 9.7 (Reproducibility), Section 9.9 (Collaboration), Section 9.11 (Research Governance), Section 9.12 (Research Lifecycle), Document 11 (per D-5, D-7.7), Document 14, and handbook/ARCHITECTURAL_INVARIANTS.md (per P-1, P-2, P-5, P-13, P-15, P-17).

---

# End of Section

---

# 9.14 Research Security Architecture

## 9.14.1 Purpose

The Research Security Architecture defines the security framework protecting research assets — hypotheses, experiments, findings, knowledge artifacts, and research data — within the Quant Hub platform.

Security shall protect the confidentiality, integrity, and availability of research assets. Security controls shall extend enterprise security infrastructure (Document 11, D-7.12) and identity management (D-9) with research-specific protections.

Security shall not compromise research reproducibility, collaboration, or governance. Security shall enable rather than obstruct legitimate research.

---

## 9.14.2 Scope

The Research Security Architecture applies to all research assets, activities, and participants within the Quant Hub platform.

Coverage includes:

- Authentication and Authorization
- Encryption
- Data Classification Awareness
- Audit Logging
- Network Security
- Workspace Isolation Enforcement
- Intellectual Property Protection
- Security Monitoring
- Security Incident Response

The following topics are intentionally excluded:

- Enterprise authentication infrastructure — Owned by Document 9 (extended, not redefined per P-10)
- Enterprise encryption infrastructure — Frozen per Document 11 (D-7.12)
- Trading security — Owned by Document 14

---

## 9.14.3 Authentication

Research platform access shall require authenticated identity extending Document 9.

Authentication shall support multi-factor authentication for sensitive research operations, single sign-on integration with enterprise identity providers, service account authentication for automated research pipelines, and session management with appropriate timeouts.

SSO and Identity Provider integration requirements:

| Dimension | Specification |
|-----------|--------------|
| Authentication Protocol | OpenID Connect 1.0 (primary), SAML 2.0 (fallback for legacy IdPs) |
| Token Format | JWT (RS256 signed) with standard claims: sub, iss, aud, exp, iat, email, groups |
| Token Lifetime | Access token: 1 hour. Refresh token: 24 hours. Absolute maximum session: 12 hours |
| Provisioning | SCIM 2.0 for automated user lifecycle: create, update, deactivate, reactivate |
| Service Accounts | Machine identities authenticated via OAuth 2.0 client credentials grant with short-lived tokens |
| Session Management | Concurrent sessions: maximum 3 per user. Inactive session timeout: 30 minutes. Forced logout on security event |
| Authorization | Role and group claims in JWT mapped to platform roles. ABAC for fine-grained resource access |

SSO integration shall be tested during DR exercises. IdP failover shall support a secondary IdP with automatic fallback within 30 seconds.

All research actions shall be attributable to an authenticated identity per P-17.

---

## 9.14.4 Authorization

Research access shall be governed through authorization controls.

Authorization model shall include:

- Role-Based Access Control — Roles defined per Section 9.9.3 extended to platform-level permissions
- Project-Scoped Access — Research access scoped to specific projects and research domains
- Classification-Aware Access — Data classification enforcement per D-7.12.6
- Least Privilege — Research participants granted minimum necessary access
- Access Review — Periodic review of active access grants
- Temporary Access — Time-bound access grants with automatic expiration

Authorization decisions shall be logged per P-5.

---

## 9.14.5 Encryption

Research data shall be encrypted at rest and in transit extending Document 11 (D-7.12.5).

Encryption shall cover research datasets, experiment results and artifacts, knowledge artifacts, research workspace data, and collaboration data. Key management shall follow Document 11 encryption infrastructure.

---

## 9.14.6 Data Classification Awareness

Research security shall enforce data classification boundaries per Document 11 (D-7.12.6).

Classification enforcement shall include:

- Classification Inheritance — Research artifacts inherit classification from source data
- Cross-Classification Protection — Research combining data from multiple classification levels governed by the highest classification
- Classification Labeling — Research artifacts labeled with classification
- Classification Controls — Access, storage, and sharing governed by classification level
- Classification Audit — Classification changes and boundary crossings logged

Research shall not enable data exfiltration from higher to lower classification levels.

---

## 9.14.7 Audit Logging

All research security events shall produce immutable audit logs per P-5.

Audited events shall include authentication events, authorization decisions, data access, artifact access, classification changes, workspace operations, collaboration actions, governance decisions, and security configuration changes.

Audit logs shall be queryable, tamper-proof, and retained per Document 11 retention policies.

---

## 9.14.8 Network Security

Research platform access shall be protected through network security controls.

Network security shall include network isolation between research environments and production environments, encrypted communications in transit, API security with authentication and rate limiting, and network access logging and monitoring.

Research API rate limits:

| Consumer Type | Default Limit | Burst Allowance | Scope |
|--------------|---------------|-----------------|-------|
| Interactive Researcher | 200 req/s | 2x for 10 seconds | Per user session |
| Automated Research Pipeline | 500 req/s | 2x for 30 seconds | Per service account |
| Knowledge Discovery | 100 req/s | 1.5x for 10 seconds | Per user |
| Experiment Submission | 10 req/s | No burst | Per user |
| Artifact Upload | 50 req/s or 100 MB/s | No burst | Per user |

Rate limit exceeded responses shall return HTTP 429 with Retry-After header. Rate limits apply per-endpoint. Admin endpoints shall have stricter limits (10 req/s). Rate limit counters use a sliding 1-second window.

---

## 9.14.9 Workspace Isolation Enforcement

Research workspace isolation per Section 9.2.8 shall be enforced through security controls.

Enforcement shall include:

- Compute Isolation — Workspace compute resources isolated at the infrastructure level
- Network Isolation — Workspace network traffic isolated and monitored
- Data Isolation — Workspace data access restricted to authorized data contracts
- User Isolation — User workspace separation enforced
- Cross-Workspace Protection — Unauthorized cross-workspace access detected and prevented

Isolation violations shall trigger security alerts.

---

## 9.14.10 Intellectual Property Protection

Research intellectual property shall be protected through security controls.

Protection shall include:

- Access Controls — Research IP accessible only to authorized participants
- Export Controls — Governed export of research findings and knowledge artifacts
- Watermarking — Research reports and artifacts may be watermarked for traceability
- Non-Disclosure Enforcement — Platform-enforced access agreements
- IP Provenance — Clear provenance and ownership attribution for all research IP

---

## 9.14.11 Security Monitoring

Research security shall be continuously monitored per P-15.

Monitoring shall include authentication anomaly detection, authorization violation detection, data access pattern monitoring, classification boundary monitoring, workspace isolation monitoring, and API abuse detection. Security events shall generate alerts per Section 9.15.

---

## 9.14.12 Security Testing

Research security controls shall satisfy testing requirements including penetration testing, vulnerability scanning, access control testing, encryption verification, classification enforcement testing, and isolation boundary testing. Security testing shall be conducted periodically and on significant platform changes.

Security scanning requirements:

| Scan Type | Trigger | Scope | Action on Failure |
|-----------|---------|-------|-------------------|
| Container Image Scan | Image push to registry | All workspace and experiment images | Block image activation for Critical CVEs (CVSS >= 9.0); Warn for High |
| Dependency CVE Scan | Daily | All active workspace environments | Notify researcher for High+; auto-block for Critical in governed projects |
| Runtime Environment Scan | Workspace activation | Active dependencies, kernel configuration | Block activation for Critical findings |
| Research Artifact Scan | Artifact registration | Notebooks, data files, serialized objects | Block registration for detected secrets or malicious patterns |

CVE remediation SLA: Critical CVEs shall be patched within 48 hours of disclosure. High CVEs within 7 days. CVE database integration shall source from enterprise vulnerability management platform. Scan results shall be retained as immutable evidence per P-2.

---

## 9.14.13 Security Incident Response

The platform shall provide security incident response procedures for research security incidents.

Incident response shall include incident detection and classification, containment procedures, investigation and root cause analysis for research data breaches, unauthorized access, and IP theft, remediation, evidence preservation, and post-incident review. Incident response shall integrate with enterprise incident response infrastructure.

---

## 9.14.14 Security Compliance

Research security shall comply with enterprise security policies, regulatory requirements applicable to quantitative financial research, data protection regulations, and intellectual property protection requirements. Compliance shall be verified through security audits.

---

## 9.14.15 Security Performance

Security controls shall satisfy performance objectives. Authentication latency, authorization check overhead, encryption overhead, and audit logging overhead shall not materially degrade research platform performance.

---

## 9.14.16 Risks

The Research Security Architecture shall continuously assess risks including:

- Data Exfiltration — Research data or findings exfiltrated to unauthorized parties
- Unauthorized Access — Research assets accessed without authorization
- IP Theft — Research intellectual property stolen or misappropriated
- Classification Breach — Data classification boundaries violated
- Audit Tampering — Security audit logs modified or deleted
- Insufficient Isolation — Workspace isolation failures enabling cross-user or cross-project access

Every identified risk shall include risk classification, impact assessment, likelihood assessment, detection method, mitigation strategy, recovery procedure, and ownership.

---

## 9.14.17 Acceptance Criteria

The Research Security Architecture shall be considered complete when the platform demonstrates:

- Authentication and authorization extending Document 9 and Document 11
- Encryption at rest and in transit for all research data
- Data classification enforcement preventing boundary violations
- Workspace isolation enforced at compute, network, and data levels
- Comprehensive audit logging for all security events per P-5
- Security monitoring with anomaly detection and alerting
- Security incident response procedures
- No redefinition of frozen enterprise security infrastructure per P-10

---

## 9.14.18 Cross References

This section shall be read together with Section 9.1 (Research Platform), Section 9.2 (Research Workspace), Section 9.9 (Collaboration), Section 9.11 (Research Governance), Document 9 (Identity and Access Management), Document 11 (per D-7.12), and handbook/ARCHITECTURAL_INVARIANTS.md (per P-1, P-2, P-5, P-10, P-15, P-17).

---

# End of Section

---

# 9.15 Research Observability Architecture

## 9.15.1 Purpose

The Research Observability Architecture defines the research-specific observability framework extending Document 11 Section 7.13 Data Observability without redefining it.

Observability shall provide continuous visibility into research productivity, resource utilization, experiment velocity, and research activity across the Quant Hub research platform. Observability shall support operational management, governance oversight, and continuous improvement.

Observability shall implement the P-15 (Monitoring and Alerting) principle for the research domain.

The observability framework shall not embed strategy-specific assumptions per P-1.

---

## 9.15.2 Scope

The Research Observability Architecture applies to all research-specific observability within the Quant Hub platform.

Coverage includes:

- Research Metrics
- Research Dashboards
- Research Activity Monitoring
- Research Resource Utilization
- Research SLOs
- Research Alerting

The following topics are intentionally excluded:

- Enterprise observability infrastructure — Frozen per Document 11 (D-7.13)
- ML observability — Owned by Document 12 (Section 8.9)
- Trading observability — Owned by Document 14

---

## 9.15.3 Research Metrics

The platform shall maintain standardized research metrics per the enterprise observability model.

Metric categories include:

- Productivity Metrics — Hypotheses registered, experiments completed, findings published, knowledge artifacts created, reports generated per time period
- Quality Metrics — Reproducibility verification success rate, peer review pass rate, statistical compliance rate, findings per hypothesis
- Velocity Metrics — Time from hypothesis registration to validation, time from hypothesis to publication, time from promotion request to production, experiment cycle time
- Resource Metrics — Workspace utilization (CPU, memory, GPU, storage), compute consumption by user and project, active workspace count and duration, resource quota utilization
- Collaboration Metrics — Active collaborations, peer reviews completed, co-authoring activity, workspace sharing activity

Metrics shall be collected continuously per D-7.13.1 and reported through dashboards per Section 9.15.9.

---

## 9.15.4 Research Activity Monitoring

Research activity shall be monitored for operational visibility and governance oversight.

Activity monitoring shall include:

- Workspace Activity — Active, idle, and suspended workspace counts; provisioning and suspension events; resource consumption per workspace
- Experiment Activity — Experiments by lifecycle state; execution duration; success and failure rates; concurrent experiment count
- Hypothesis Activity — Registration rate, validation rate, time-to-conclusion, hypothesis-to-experiment ratio
- Knowledge Activity — Artifact creation rate, publication rate, discovery query volume, taxonomy coverage
- Promotion Activity — Promotion requests, approval rate, time-to-production, post-promotion drift

Activity monitoring shall support capacity planning and governance compliance per P-15.

---

## 9.15.5 Research Resource Utilization

Research resource utilization shall be monitored for operational efficiency and cost management.

Utilization monitoring shall include:

- Compute Utilization — CPU, memory, and GPU utilization aggregated by user, project, and domain
- Storage Utilization — Workspace storage, artifact storage, knowledge storage by project and lifecycle state
- Quota Utilization — Resource quota consumption vs allocation; quota breach alerts
- Cost Attribution — Resource cost attributed to research projects and domains for cost governance
- Utilization Trends — Resource utilization trends for capacity planning and optimization

Resource monitoring shall detect and alert on quota breaches and anomalous consumption.

---

## 9.15.6 Research SLOs

The research platform shall define and monitor Service Level Objectives per D-7.13.5.

Research SLOs shall include:

- Workspace Provisioning SLO — Time from workspace request to workspace provisioned and active
- Experiment Execution SLO — Experiment execution completion within expected duration
- Knowledge Discovery SLO — Search and browse response latency
- Artifact Access SLO — Artifact download and upload throughput and latency
- Statistical Analysis SLO — Statistical test execution time
- Governance Processing SLO — Gate evaluation and approval processing latency

SLOs shall be continuously measured. SLO violations shall trigger operational alerts and governance review.

---

## 9.15.7 Research Alerting

Research-specific alerting shall extend enterprise alerting per D-7.13.6.

Research alert categories include:

- Productivity Alerts — Significant decline in research productivity metrics
- Resource Alerts — Quota breaches, resource exhaustion, excessive consumption
- Quality Alerts — Reproducibility failure rate increases, peer review decline
- Governance Alerts — Compliance violations, anomaly detection events
- SLO Alerts — SLO violations for research services
- Anomaly Alerts — Unusual research activity patterns, potential misconduct indicators

Alerts shall include severity classification, notification routing, alert correlation, and alert suppression during planned maintenance per enterprise standards.

---

## 9.15.8 Research Dashboards

The platform shall provide research observability dashboards.

Dashboard categories include:

- Operations Dashboard — Platform health, resource utilization, SLO compliance
- Research Activity Dashboard — Active workspaces, experiments, hypotheses, knowledge artifacts
- Productivity Dashboard — Research productivity metrics, velocity trends, throughput
- Resource Dashboard — Compute, storage, and quota utilization by project and domain
- Governance Compliance Dashboard — Pre-registration compliance, reproducibility tier distribution, anomaly summary
- Researcher Dashboard — Personal activity, productivity, resource consumption, pending governance actions

Dashboards shall support real-time and historical views, role-based access, and integration with enterprise dashboards per D-7.13.

---

## 9.15.9 Observability Integration

Research observability shall integrate with enterprise observability infrastructure per D-7.13.

Integration shall include:

- Metrics Pipeline — Research metrics flowing through enterprise metrics pipeline
- Log Aggregation — Research logs aggregated with enterprise log management
- Alert Routing — Research alerts routed through enterprise alerting infrastructure
- Dashboard Federation — Research dashboards federated with enterprise dashboard platform
- Trace Correlation — Research traces correlated with Document 11 and Document 12 traces

Integration shall avoid duplication per P-10.

---

## 9.15.10 Observability Data Management

Research observability data shall be managed through enterprise observability data management per Document 11.

Management shall include metrics retention appropriate to metric type, alert history retention, log retention, and access control per D-7.13. Dashboard access shall respect governance and security boundaries.

---

## 9.15.11 Observability Governance

Research observability shall be governed through enterprise governance processes.

Governance shall include observability policy definition, metric definition governance, SLO governance, alert rule governance, dashboard governance, and observability audit trail per P-5.

---

## 9.15.12 Observability Performance, Scalability, and Operations

Observability services shall satisfy performance objectives for metric collection latency, dashboard query response time, and alert evaluation latency. Services shall scale with research platform growth. High availability, DR, and monitoring shall follow enterprise standards per Document 11.

---

## 9.15.13 Observability Security

Observability data shall be secured through access control per D-7.13, encryption, integrity protection, and audit logging. Dashboards shall not expose sensitive research data. Observability access shall respect research security boundaries per Section 9.14.

---

## 9.15.14 Risks

The Research Observability Architecture shall continuously assess risks including:

- Observability Blind Spots — Critical research activities not instrumented for observation
- Metric Misinterpretation — Metrics misleading rather than informing operational decisions
- Alert Fatigue — Excessive alert volume from research observability
- Dashboard Proliferation — Uncontrolled growth of dashboards reducing visibility
- Resource Monitoring Overhead — Observability consuming excessive research platform resources
- SLO Misalignment — SLOs not reflecting actual researcher experience

Every identified risk shall include risk classification, impact assessment, likelihood assessment, detection method, mitigation strategy, recovery procedure, and ownership.

---

## 9.15.15 Acceptance Criteria

The Research Observability Architecture shall be considered complete when the platform demonstrates:

- Standardized research metrics covering productivity, quality, velocity, resource, and collaboration
- SLOs defined and continuously monitored for all critical research services
- Research-specific alerting integrated with enterprise alerting infrastructure
- Role-based dashboards for operations, research, productivity, resource, and governance
- Observability data managed through enterprise infrastructure per Document 11
- Integration with enterprise observability without duplication per P-10
- No strategy-specific observability assumptions per P-1

---

## 9.15.16 Cross References

This section shall be read together with Section 9.1 (Research Platform), Section 9.11 (Research Governance), Section 9.12 (Research Lifecycle), Section 9.14 (Research Security), Document 11 (per D-7.13), Document 12 (Section 8.9), and handbook/ARCHITECTURAL_INVARIANTS.md (per P-1, P-5, P-10, P-15, P-17).

---

# End of Section

---

# 9.16 Research Infrastructure Architecture

## 9.16.1 Purpose

The Research Infrastructure Architecture defines the compute, storage, and networking infrastructure supporting the Quant Hub research platform. It extends platform infrastructure without redefining it.

Infrastructure shall provide the computational foundation for research workspaces, experiment execution, statistical analysis, and knowledge management. Infrastructure shall be abstracted from research tooling per P-3 — researchers shall interact with governed services, not raw infrastructure.

Infrastructure shall be strategy-agnostic per P-1. No infrastructure component shall embed assumptions about specific strategies, asset classes, or research domains.

---

## 9.16.2 Scope

The Research Infrastructure Architecture applies to all infrastructure supporting the Quant Hub research platform.

Coverage includes:

- Compute Resource Management
- Storage Allocation
- Networking
- Container Orchestration
- Infrastructure Abstraction
- Cost Optimization

The following topics are intentionally excluded:

- Enterprise infrastructure — Owned by Documents 02, 03, 07
- Data storage infrastructure — Frozen per Document 11 (D-7.1)
- ML infrastructure — Owned by Document 12
- Trading infrastructure — Owned by Document 14

---

## 9.16.3 Compute Resource Management

Research platform compute resources shall be managed for governed allocation.

Compute management shall include:

- Resource Pooling — CPU, memory, and GPU resources pooled for research workspace allocation
- Dynamic Allocation — Resources allocated and deallocated on workspace lifecycle transitions
- Resource Quotas — Per-user, per-project, and per-team resource quotas controlling allocation
- Fair Scheduling — Compute scheduling ensuring fair access across concurrent research activities
- Burst Capacity — Burst capacity for computationally intensive analyses
- GPU Allocation — Governed GPU allocation for GPU-accelerated research (ML research, simulation)

Compute resource management shall be abstracted through workspace services per Section 9.2.

---

## 9.16.4 Storage Allocation

Research platform storage shall be allocated through Document 11 storage infrastructure per D-7.1.

Storage allocation shall include:

- Workspace Storage — Ephemeral storage allocated per workspace, governed by workspace lifecycle
- Artifact Storage — Persistent storage for research artifacts through Document 11 artifact storage per Section 9.10.6
- Knowledge Storage — Storage for knowledge artifacts through Document 11 storage
- Temporary Storage — Temporary storage for intermediate computation results, cleaned on workspace archival
- Storage Quotas — Per-user and per-project storage quotas

Storage shall be classified and governed per Document 11 data classification (D-7.12.6).

---

## 9.16.5 Networking

Research platform networking shall provide governed connectivity.

Networking shall include:

- Workspace Networking — Network connectivity for research workspaces with governed egress and ingress
- Inter-Service Communication — Secure communication between research platform services
- Data Access Networking — Network connectivity to Document 11 data platform with governed access
- External Access — Governed external access for literature retrieval, package repositories
- Network Isolation — Network isolation between research workspaces, projects, and classification levels per Section 9.2.8

Networking shall implement zero-trust principles per D-7.12.3.

---

## 9.16.6 Container Orchestration

Research workspaces shall be deployed as containerized environments managed through governed orchestration.

Container orchestration shall include:

- Container Management — Container lifecycle tied to workspace lifecycle per Section 9.2.6
- Image Registry — Governed container image registry with reproducibility-pinned images per Section 9.2.4
- Resource Constraints — Container resource limits enforced per compute resource management
- Isolation — Container isolation at compute, network, and storage levels
- Orchestration Abstraction — Orchestration abstracted from research tooling per P-3

Container orchestration shall not embed assumptions about specific orchestration platforms per P-3.

---

## 9.16.7 Infrastructure Abstraction

Research infrastructure shall be abstracted from research tooling per P-3.

Abstraction shall include:

- Compute Abstraction — Researchers interact with workspace services, not compute infrastructure
- Storage Abstraction — Researchers interact with governed storage contracts, not storage infrastructure per D-7.1.3
- Networking Abstraction — Researchers interact with governed data access, not network configuration
- Orchestration Abstraction — Researchers interact with workspace lifecycle, not container orchestration
- Infrastructure Independence — Research tooling independent of specific infrastructure providers per F-5

Abstraction shall enable infrastructure migration without affecting research workflows.

---

## 9.16.8 Infrastructure Scalability

Research infrastructure shall scale to support platform growth.

Scalability dimensions include:

- Compute Scaling — Horizontal scaling of compute resources for concurrent workspaces and experiments
- Storage Scaling — Storage scaling for growing artifact and knowledge volumes
- Network Scaling — Network throughput scaling for concurrent data access and artifact transfer
- Burst Scaling — Rapid resource provisioning for computational spikes

Auto-scaling policies:

| Resource | Scale-Out Trigger | Scale-Out Target | Scale-In Trigger | Cooldown |
|----------|------------------|-----------------|------------------|----------|
| Workspace Compute Nodes | Pending workspaces > 3 for 2 minutes | +2 nodes per trigger | Idle nodes > 5 for 5 minutes | 5 minutes |
| Experiment Compute | Queued experiments > 10 for 2 minutes | +4 nodes per trigger | Completed experiments with no queue > 5 minutes | 10 minutes |
| GPU Nodes | Queued GPU requests > 2 for 1 minute | +1 GPU node per trigger | All GPU nodes idle > 10 minutes | 5 minutes |

Maximum node count shall be capped by infrastructure budget governance. Scale-in shall never terminate nodes with active workspaces or running experiments. Auto-scaling events shall be logged for cost attribution.

Scaling shall preserve resource governance, isolation, and quota enforcement.

---

## 9.16.9 Infrastructure High Availability and Disaster Recovery

Research infrastructure shall operate with high availability. Compute and networking shall be resilient to component failure. Storage shall follow Document 11 HA/DR per D-7.5. Container orchestration shall support workspace recovery.

Disaster recovery shall preserve workspace configurations, research data, artifact metadata, and infrastructure configuration.

---

## 9.16.10 Infrastructure Cost Optimization

Research infrastructure shall be governed for cost efficiency.

Cost optimization shall include:

- Resource Right-Sizing — Workspace resources provisioned appropriate to research needs
- Lifecycle-Driven Deallocation — Resources deallocated on workspace suspension and archival
- Idle Detection — Detection and suspension of idle workspaces per Section 9.2.6
- Storage Tiering — Research data tiered through Document 11 storage tiers per D-7.6.4
- Cost Attribution — Infrastructure cost attributed to projects and domains for cost governance
- Governance Reporting — Infrastructure cost and utilization reporting for governance oversight

Cost optimization shall not compromise research reproducibility or governance requirements.

---

## 9.16.11 Infrastructure Operations and Maintenance

Research infrastructure shall be operated through governed operations practices.

Operations shall include:

- Provisioning Automation — Automated infrastructure provisioning for workspaces and services
- Maintenance Windows — Planned maintenance windows communicated through research notifications
- Upgrade Management — Infrastructure upgrades managed without disruption to active research
- Operational Monitoring — Infrastructure health monitored per enterprise standards
- Operational Runbooks — Infrastructure operational runbooks maintained per Section 9.1

Operations shall follow enterprise standards extending Document 11 operational practices.

---

## 9.16.12 Risks

The Research Infrastructure Architecture shall continuously assess risks including:

- Resource Exhaustion — Compute, storage, or network capacity exhausted during critical research
- Isolation Failure — Infrastructure isolation between workspaces or classification levels violated
- Orchestration Failure — Container orchestration failure preventing workspace provisioning or operation
- Abstraction Leak — Infrastructure details leaking through abstraction to research tooling
- Cost Escalation — Uncontrolled infrastructure cost growth without governance visibility
- Scaling Failure — Infrastructure unable to scale with research platform growth

Every identified risk shall include risk classification, impact assessment, likelihood assessment, detection method, mitigation strategy, recovery procedure, and ownership.

---

## 9.16.13 Acceptance Criteria

The Research Infrastructure Architecture shall be considered complete when the platform demonstrates:

- Governed compute resource management with quotas and fair scheduling
- Storage allocation through Document 11 infrastructure per D-7.1
- Container orchestration abstracted from research tooling per P-3
- Infrastructure abstraction enabling migration without research workflow changes
- Resource deallocation on workspace lifecycle transitions for cost efficiency
- Burst capacity for computationally intensive research
- No strategy-specific or vendor-specific infrastructure assumptions per P-1, P-3

---

## 9.16.14 Cross References

This section shall be read together with Section 9.1 (Research Platform), Section 9.2 (Research Workspace), Section 9.14 (Research Security), Document 11 (per D-7.1, D-7.5, D-7.6, D-7.12), Documents 02, 03, 07 (enterprise infrastructure), and handbook/ARCHITECTURAL_INVARIANTS.md (per P-1, P-2, P-3, P-15, P-17).

---

# End of Section

---

# 

---

## Implementation Specification Requirements

This section defines research-specific implementation requirements that extend the canonical type system and specification requirements defined in Document 11. The Document 11 canonical type system SHALL be used for all fields. All requirements apply per Document 11 Implementation Specification Requirements section.

### Research-Specific Canonical Types

| Type | Definition | Example |
|------|-----------|---------|
| `hypothesis_id` | UUID v7 identifier for a research hypothesis | `"550e8400-e29b-41d4-a716-446655440001"` |
| `experiment_id` | UUID v7 identifier for a research experiment | `"550e8400-e29b-41d4-a716-446655440002"` |
| `workspace_state` | Enum of all workspace lifecycle states | `enum{"PROVISIONING","ACTIVE","IDLE","SUSPENDED","ARCHIVED","DESTROYED"}` |
| `git_commit_hash` | Full 40-character SHA-1 git commit hash | `"a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"` |
| `research_metric` | Typed metric value recorded during experiments | `{name: string(128), value: float, unit: string(32), timestamp: timestamp, statistical_test: optional[string(64)]}` |

### Workspace State Transition Guards

| From State | To State | Guard Condition | API Call | Trigger |
|-----------|----------|-----------------|----------|---------|
| (null) | PROVISIONING | Workspace creation request submitted with valid resource spec and data grants | `POST /api/v1/research/workspaces` | Manual (Researcher) |
| PROVISIONING | ACTIVE | Container image pulled; resources allocated; environment initialized; data access grants resolved; health check passed | Automatic transition | Automatic (provisioning complete) |
| PROVISIONING | DESTROYED | Provisioning failed irrecoverably (resource unavailable, image pull failure, data contract resolution failure) | Implicit (no restore) | Automatic (provisioning failure) |
| ACTIVE | IDLE | No kernel activity for 30 minutes; Idle Warning notification sent | Automatic transition | Automatic (idle timer) |
| IDLE | ACTIVE | Researcher resumes workspace (kernel activity detected or manual resume) | `POST /api/v1/research/workspaces/{id}/resume` | Manual (Researcher) or Automatic (kernel activity) |
| IDLE | SUSPENDED | Idle for 2 hours cumulative; state snapshot preserved | Automatic transition | Automatic (idle timer) |
| SUSPENDED | ACTIVE | Researcher resumes workspace; state restored from suspension snapshot | `POST /api/v1/research/workspaces/{id}/resume` | Manual (Researcher) |
| SUSPENDED | ARCHIVED | Suspended for 14 days; 24hr pre-archive notification sent | Automatic transition | Automatic (retention policy) |
| ARCHIVED | ACTIVE | Administrative restore requested with project lead approval | `POST /api/v1/research/workspaces/{id}/restore` | Manual (Project Lead + Administrator) |
| ARCHIVED | DESTROYED | Archived for 90 days; 7-day pre-destruction notification sent | Automatic transition | Automatic (retention policy) |
| Any state | DESTROYED | Governance-ordered destruction (security incident, data breach, compliance order) | Manual (Governance Officer) | Manual (administrative) |

---

## Workspace Provisioning API Contract

### POST /api/v1/research/workspaces — Request

| Field | Canonical Type | Required | Description |
|-------|---------------|----------|-------------|
| `name` | `string(128)` | Yes | Human-readable workspace name |
| `project_id` | `uuid` | Yes | Project this workspace belongs to |
| `resources` | (see below) | Yes | Resource specification |
| `environment` | (see below) | Yes | Computing environment specification |
| `data_grants` | `list[data_grant]` | No | Data access grants per D-8 contracts |
| `collaborators` | `list[uuid]` | No | Collaborator user IDs with access to workspace |
| `lifecycle_config` | (see below) | No | Override default lifecycle timeouts |
| `tags` | `dict[string,string]` | No | Workspace tags for organization and search |

**resources**: `{cpu_cores: integer, gpu_count: integer, gpu_type: optional[string(32)], memory_mb: integer, storage_gb: integer}`
**environment**: `{container_image: string(256), python_version: string(16), requirements: list[string(256)], env_vars: dict[string,string], ide: enum{"JUPYTER","VSCODE","RSTUDIO"}}`
**data_grant**: `{contract_uri: uri, version_pin: string(16), access_level: enum{"READ","READ_WRITE"}}`
**lifecycle_config**: `{idle_timeout_minutes: integer (default: 30), suspend_timeout_minutes: integer (default: 120), archive_timeout_days: integer (default: 14)}`

### POST /api/v1/research/workspaces — Response (202 Accepted)

| Field | Canonical Type | Description |
|-------|---------------|-------------|
| `workspace_id` | `uuid` | Provisioned workspace identifier |
| `status` | `workspace_state` | Initial status: `PROVISIONING` |
| `estimated_startup_seconds` | `integer` | Estimated time until ACTIVE per startup SLO |
| `status_url` | `uri` | `GET /api/v1/research/workspaces/{id}/status` for polling |

Provisioning is asynchronous. A `202 Accepted` response indicates the request is queued. The researcher polls the `status_url` or subscribes to `WorkspaceProvisioned` events via the Enterprise Event Bus.

---

## SSO Integration Concretization

### Token Validation

The Research Platform SHALL validate JWT tokens as follows:

| Parameter | Specification |
|-----------|---------------|
| Validation method | Local JWKS validation (cached with 5-minute TTL) |
| JWKS URI | Configurable per IdP: config key `auth.idp.jwks_uri` |
| Issuer validation | Against configured allowlist: config key `auth.idp.allowed_issuers` (list[string]) |
| Audience validation | Against configured expected audience: config key `auth.idp.expected_audience` |
| Clock skew tolerance | 30 seconds |
| Signature algorithm | RS256 (configurable: `auth.idp.signature_algorithm`) |

### Header Format

All authenticated requests SHALL include: `Authorization: Bearer <JWT>`

### Group Claim Mapping Requirement

The implementation SHALL provide a configurable group claim mapping table. The platform maps IdP group claims to platform roles. The configuration format SHALL be:

```
auth.role_mapping:
  - idp_group: "quant-research"
    platform_role: "RESEARCHER"
  - idp_group: "quant-research-lead"
    platform_role: "PROJECT_LEAD"
  - idp_group: "quant-reviewer"
    platform_role: "REVIEWER"
```

Case-sensitivity, nested group resolution, and group reconciliation frequency SHALL be specified per IdP integration.

### IdP Failover

| Parameter | Specification |
|-----------|---------------|
| Primary IdP | Config key: `auth.idp.primary.issuer`, `auth.idp.primary.jwks_uri` |
| Secondary IdP | Config key: `auth.idp.secondary.issuer`, `auth.idp.secondary.jwks_uri` |
| Failover trigger | Primary IdP health check failure (3 consecutive timeouts at 10s each) |
| Failover time | Within 30 seconds |
| Health check | `GET {primary_issuer}/.well-known/openid-configuration` every 30 seconds |
| Automatic fallback | After primary IdP passes 5 consecutive health checks, automatic fallback |

---

## Quota Enforcement API Contract

### Quota Error Response (HTTP 409 Conflict)

| Field | Type | Description |
|-------|------|-------------|
| `error_code` | `string(32)` | `RES_QUOTA_9001` for CPU, `RES_QUOTA_9002` for GPU, `RES_QUOTA_9003` for memory, `RES_QUOTA_9004` for storage, `RES_QUOTA_9005` for concurrent workspaces |
| `message` | `string(256)` | Human-readable: "CPU quota exceeded. Requested: 16 cores. Available: 4 cores. Current usage: 12/16." |
| `request_id` | `uuid` | Correlation identifier |
| `quota_type` | `enum{"CPU","GPU","MEMORY","STORAGE","CONCURRENT_WORKSPACES"}` | Which quota was exceeded |
| `current_usage` | `integer` or `float` | Current usage in specified units |
| `quota_limit` | `integer` or `float` | Total quota limit |
| `requested` | `integer` or `float` | What was requested |

### Quota Query API

`GET /api/v1/research/quotas?project_id={uuid}` returns:

```
{
  "project_id": "uuid",
  "quotas": [
    {"type": "CPU", "usage": 24, "limit": 64, "unit": "cores"},
    {"type": "GPU", "usage": 2, "limit": 4, "unit": "devices"},
    {"type": "MEMORY", "usage": 128, "limit": 256, "unit": "GB"},
    {"type": "STORAGE", "usage": 800, "limit": 2000, "unit": "GB"},
    {"type": "CONCURRENT_WORKSPACES", "usage": 3, "limit": 5, "unit": "workspaces"}
  ],
  "per_user": [
    {"user_id": "uuid", "quotas": [...]}
  ]
}
```

---

## Experiment Submission Contract Requirements

### POST /api/v1/research/experiments — Request

| Field | Canonical Type | Required | Description |
|-------|---------------|----------|-------------|
| `name` | `string(256)` | Yes | Human-readable experiment name |
| `project_id` | `uuid` | Yes | Owning project |
| `hypothesis_refs` | `list[uuid]` | No | Linked hypotheses |
| `input_data` | `list[{contract_uri: uri, version_pin: string(16)}]` | Yes | D-8 data contract references |
| `parameters` | `dict[string, any]` | Yes | Experiment parameters (typed per experiment definition) |
| `metrics` | `list[{name: string(128), type: enum{"SCALAR","DISTRIBUTION","TIME_SERIES","STATISTICAL_TEST"}}]` | Yes | Metrics to track |
| `code_version` | `git_commit_hash` | Yes | Git commit hash for reproducibility |
| `environment_ref` | `string(256)` | Yes | Container image or environment specification reference |
| `random_seed` | `integer` | Yes | Random seed for reproducibility per R-1 |
| `workspace_id` | `uuid` | No | Originating workspace for resource inheritance |
| `max_duration_seconds` | `integer` | No | Override default timeout (max: 86400) |
| `checkpoint_interval_seconds` | `integer` | No | Override default checkpoint interval (default: 1800) |

### POST /api/v1/research/experiments — Response (201 Created)

| Field | Canonical Type | Description |
|-------|---------------|-------------|
| `experiment_id` | `uuid` | Experiment identifier |
| `status` | `enum{"SUBMITTED","QUEUED"}` | Initial experiment status |
| `status_url` | `uri` | `GET /api/v1/research/experiments/{id}/status` |

### GET /api/v1/research/experiments/{id}/results — Response

| Field | Canonical Type | Description |
|-------|---------------|-------------|
| `experiment_id` | `uuid` | Experiment identifier |
| `status` | `enum{"COMPLETED","FAILED","CANCELLED","TIMED_OUT"}` | Final status |
| `metrics` | `list[research_metric]` | All recorded metrics with timestamps |
| `artifacts` | `list[{uri: string(512), type: string(64), size_bytes: integer, checksum: string(128)}]` | Output artifacts |
| `conclusion` | `string(4096)` | Researcher-authored conclusion |
| `started_at` | `timestamp` | Experiment start time |
| `completed_at` | `timestamp` | Experiment end time |

---

**End of Document 13 — Research Engineering Architecture**
