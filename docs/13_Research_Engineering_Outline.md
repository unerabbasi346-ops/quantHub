# Document 13 — Research Engineering Architecture

## Outline — FROZEN

**STATUS: FROZEN — 2026-06-30**

This outline is the approved implementation plan for Document 13. Content generation shall follow this structure exactly. Section identifiers, subsection counts, scope boundaries, exclusions, and shared interfaces defined herein shall not be altered without governance approval and an updated outline version. No section, subsection, domain, or architectural concept that overlaps with frozen Document 11 or Document 12 architectures shall be introduced during content generation.

---

## Purpose

Define the canonical architecture for Quant Hub's research platform. The research platform governs the complete quantitative research lifecycle: hypothesis formulation, exploratory analysis, research experiment organization, statistical validation, knowledge capture, collaboration, research governance, artifact management, and the governed promotion of research findings into downstream production platforms including ML Engineering (Document 12), Strategy Development and Backtesting (Document 14), and Portfolio Management including Risk Management (Document 15, Section 11.5).

The research platform consumes governed data from Document 11, features and models from Document 12, and serves validated research outputs to Documents 14 (Trading Infrastructure) and 15 (Portfolio Management). It sits between data/ML platforms and production trading platforms, governing the critical transition from exploration to production.

The research platform is strategy-agnostic per P-1. It shall serve every quantitative strategy uniformly without embedding strategy-specific logic, domain assumptions, or signal priors within platform infrastructure. No research workspace, hypothesis template, validation rule, or knowledge capture mechanism shall assume the existence of any specific trading strategy.

---

## Scope Boundaries

### In Scope (Document 13 owns these domains)

- Research Workspace Architecture — governed computational environments for quantitative research
- Hypothesis Management — formulation, tracking, validation, and lifecycle of research hypotheses
- Experiment Organization — structuring, versioning, and governing research experiments distinct from ML experiments
- Exploratory Data Analysis — governed frameworks for data exploration, visualization, and insight capture
- Statistical Analysis Framework — standardized statistical methodology, significance testing, multiple testing correction
- Research Reproducibility — guaranteeing that every published research finding is reproducible
- Knowledge Management — capture, organization, discovery, and governance of research knowledge
- Research Collaboration — multi-user research workspaces, sharing, review, and co-authoring
- Research Artifact Management — notebooks, scripts, reports, datasets, results, and visualizations as governed artifacts
- Research Governance — approval workflows, review processes, compliance, and audit for research activities
- Research Lifecycle — from ideation through exploration, validation, publication, retirement
- Research-to-Production Promotion — governed gates for promoting research findings into ML, strategy, or portfolio platforms
- Research Security — access control, IP protection, data isolation for research environments
- Research Observability — research activity metrics, productivity tracking, resource utilization

### Out of Scope (Owned by frozen documents)

| Topic | Frozen Document | Reference |
|-------|----------------|-----------|
| Data storage (Bronze/Silver/Gold) | Document 11 | D-7.1.1, F-1, D-1 |
| Data quality validation | Document 11 | D-7.9.5, D-7.9.6, D-7 |
| Data lineage infrastructure | Document 11 | D-7.8.1, D-7.8.4, D-5 |
| Data governance, policy, stewardship | Document 11 | D-7.11.1, D-7.11.6, D-10 |
| Data security (encryption, IAM) | Document 11 | D-7.12.5, D-7.12.6, D-9 |
| Data lifecycle | Document 11 | D-7.4.1, D-6 |
| General observability | Document 11 | D-7.13.5, D-7.13.6 |
| Feature engineering | Document 12 | Section 8.2 |
| Experiment tracking (ML) | Document 12 | Section 8.3 (distinct from research experiment organization) |
| Model training | Document 12 | Section 8.4 |
| Model validation | Document 12 | Section 8.5 |
| Model registry | Document 12 | Section 8.6 |
| Model serving | Document 12 | Section 8.7 |
| Strategy development | Document 14 | N/A |
| Backtesting execution | Document 14 | N/A |
| Risk management | Document 14/15 | N/A |
| Portfolio management | Document 15 | N/A |
| API specification | Document 10 | N/A |
| Frontend/back-end architecture | Documents 07, 08 | N/A |
| Database architecture | Document 09 | N/A |

### Shared Interfaces (Document 13 collaborates at these boundaries)

| Interface | Frozen Document Role | Document 13 Role |
|-----------|---------------------|-------------------|
| Data Platform | Governed data access via contracts (D-8), Gold-layer datasets, Bronze-layer raw data | Research workspace consumes data through governed contracts; research datasets are temporary working copies scoped to research projects |
| Feature Store | Persists feature data as governed assets | Researchers discover and consume features for hypothesis testing; may prototype new feature definitions for later promotion to Document 12 |
| Experiment Tracking | ML experiment tracking (Section 8.3) | Research experiments are distinct from ML experiments; research experiments may reference ML experiments as evidence; research-to-ML promotion bridges the two experiment domains |
| Model Registry | Model identity and versioning (Section 8.6) | Researchers consume model predictions and metadata for analysis; research findings may recommend model improvements or new model development |
| Metadata Registry | Single authoritative metadata source (D-7.7.2) | Research artifacts are registered in the metadata registry with research-specific metadata domains |
| Lineage | Data lineage infrastructure (D-5) | Research activities record lineage from input data and models through analysis to published findings |
| Governance | Policy enforcement, audit (D-7.11) | Research governance workflows integrate with enterprise governance; research approval gates feed into promotion pipelines |
| Observability | Metrics, logging, alerting (D-7.13) | Research-specific metrics (productivity, resource utilization, experiment velocity) flow through enterprise observability |
| ML Platform | Feature Engineering, Training, Validation (Sections 8.2–8.5) | Research generates hypotheses, feature candidates, and model concepts that feed into ML platform development pipelines |

---

## Architectural Principles (Document 13-specific)

These principles extend platform invariants P-1 through P-18 with research-domain specifics. They shall not contradict frozen invariants.

### Research Reproducibility by Design
Every published research finding, analysis result, and statistical conclusion shall be reproducible given identical data, code, and environment. Reproducibility shall not depend on mutable external state. This principle extends P-13 (Deterministic Processing).

### Hypothesis-Experiment Separation
Research hypotheses (what is being tested) shall remain separate from research experiments (how testing is executed). Hypothesis definitions shall be governed independently of experiment implementations. This principle extends P-9 (Separation of Concerns).

### Governed Research-to-Production Promotion
No research finding shall enter production (strategy, model, or portfolio construction) without passing formal governance gates. Research artifacts shall be validated, reviewed, and approved before production promotion. This principle extends P-17 (Enterprise Governance) and P-8 (No Bypass Architecture).

### Knowledge as Enterprise Asset
Research knowledge — hypotheses, findings, analyses, methodologies, and insights — shall be treated as governed enterprise assets. Knowledge shall be captured, organized, discoverable, and preserved. This principle extends P-17 (Enterprise Governance).

### Independent Research Workspaces
Research workspaces shall be isolated, reproducible computational environments. Workspace configuration shall not embed assumptions about specific tools, libraries, or infrastructure per P-3.

### Strategy Independence (Research Domain)
Research hypotheses, analysis methodologies, and knowledge artifacts shall remain independent of any specific trading strategy. Research platform infrastructure shall serve all strategies without strategy-specific customization. This principle extends P-1.

### Multiple Testing Awareness
The research platform shall provide statistical infrastructure for multiple testing correction, p-hacking prevention, and false discovery rate control. Research governance shall require appropriate statistical rigor per the research risk classification.

---

## Part 9 — Research Engineering Architecture

Document 13 is organized as Part 9 of the Engineering Handbook, continuing the numbering convention established in Document 11 (Parts 1–7) and Document 12 (Part 8). Each section uses `## 9.X.Y` heading format. Subsections are `###` for named sub-items. The document file is `docs/13_Research_Engineering.md`. Every section ends with Risks, Acceptance Criteria, and Cross References.

---

### 9.1 Research Platform Architecture — 25 subsections

**9.1.1 Purpose** — Declare the research platform as canonical architecture for quantitative research lifecycle management. Position between Document 11/12 (upstream data and ML) and Documents 14/15 (downstream production). Strategy-agnostic per P-1.

**9.1.2 Scope** — Enumerate covered domains. Enumerate excluded domains with frozen references.

**9.1.3 Design Goals** — Research reproducibility, strategy independence, governed promotion, knowledge preservation, collaboration enablement, statistical rigor, enterprise scalability.

**9.1.4 Architectural Principles** — The 7 principles defined above.

**9.1.5 Research Platform Overview** — High-level architecture showing data ingress from Document 11, feature/model consumption from Document 12, research lifecycle flow (Hypothesis→Explore→Validate→Publish→Promote), and promotion paths to Documents 14/15. Integration points with Document 11 (metadata, lineage, governance, security, observability) and Document 12 (experiments, models, features).

**9.1.6 Platform Services** — Enumeration of research platform services: Workspace Service, Hypothesis Service, Experiment Service, Statistical Analysis Service, Knowledge Service, Collaboration Service, Publication Service, Promotion Service.

**9.1.7 Integration Architecture** — Integration with data platform (Document 11), ML platform (Document 12), governance, security, and observability. Contract-governed interfaces per D-8.

**9.1.8 Research Event Model** — Research events: Hypothesis Created, Experiment Started, Experiment Completed, Finding Published, Peer Review Completed, Promotion Requested, Promotion Approved, Knowledge Artifact Created.

**9.1.9–9.1.25** — Security context, observability context, governance context, performance, scalability, HA, DR, backup, capacity planning, operational monitoring, alerting, logging, runbooks, testing, deployment, configuration management, risks, acceptance criteria, cross references.

---

### 9.2 Research Workspace Architecture — 22 subsections

**9.2.1 Purpose** — Define governed computational environments for quantitative research. Workspaces provide isolated, reproducible, and governed environments for data exploration, analysis, and experimentation.

**9.2.2 Scope** — Workspace provisioning, workspace configuration, computational resource allocation, workspace lifecycle, workspace isolation.

**9.2.3 Workspace Model** — Canonical workspace specification: identifier, owner, project, computational resources, environment specification (container image, dependencies, configuration), data access grants (Document 11 contracts), mounted artifacts.

**9.2.4 Workspace Environment Reproducibility** — Containerized workspaces with pinned dependencies. Environment versioning. Environment validation before workspace activation. Extends Document 12 environment reproducibility patterns.

**9.2.5 Workspace Data Access** — Workspaces access data through governed Document 11 contracts per D-8. Research datasets are temporary working copies scoped to the workspace. No direct storage access.

**9.2.6 Workspace Lifecycle** — States: Provisioned, Active, Idle, Suspended, Archived, Destroyed. Automatic suspension of idle workspaces. Workspace archival with reproducibility preservation.

**9.2.7 Workspace Resource Management** — Compute resource allocation (CPU, memory, GPU if required). Resource quotas per user, project, team. Fair scheduling of shared compute resources.

**9.2.8 Workspace Isolation** — Workspace isolation per user, project, data classification. No cross-workspace data leakage. Network isolation between workspaces.

**9.2.9–9.2.22** — Workspace collaboration features, persistent storage for workspaces, workspace backup, workspace security, workspace governance, performance, scalability, risks, acceptance criteria, cross references.

---

### 9.3 Hypothesis Management Architecture — 18 subsections

**9.3.1 Purpose** — Define the framework for formulating, tracking, validating, and governing quantitative research hypotheses. Hypothesis management provides the structured foundation for research accountability.

**9.3.2 Scope** — Hypothesis formulation, hypothesis registration, hypothesis tracking, hypothesis validation, hypothesis lifecycle, hypothesis-to-experiment linkage.

**9.3.3 Hypothesis Model** — Canonical hypothesis specification: identifier, statement, motivation, success criteria, statistical methodology, required data, assumptions, owner, status, timestamps.

**9.3.4 Hypothesis Lifecycle** — States: Draft, Registered, Under Investigation, Validated (Confirmed), Rejected (Disconfirmed), Inconclusive, Archived. State transitions governed with explicit rationale.

**9.3.5 Hypothesis Registration** — Every hypothesis shall be registered before confirmatory analysis begins. Registration creates an immutable record preventing post-hoc hypothesis modification (HARKing prevention — Hypothesizing After Results are Known).

**9.3.6 Hypothesis-Experiment Linkage** — Every experiment shall declare which hypothesis it tests. Many-to-many relationship: one hypothesis may be tested by multiple experiments; one experiment may test multiple hypotheses.

**9.3.7 Hypothesis Validation Framework** — Statistical criteria for hypothesis confirmation or rejection. Pre-registered success criteria. Multiple testing correction across related hypotheses.

**9.3.8–9.3.18** — Hypothesis search and discovery, hypothesis lineage, hypothesis governance, hypothesis metrics (confirmation rate, time-to-conclusion), risks, acceptance criteria, cross references.

---

### 9.4 Research Experiment Architecture — 20 subsections

**9.4.1 Purpose** — Define the framework for organizing, executing, versioning, and governing quantitative research experiments. Research experiments are distinct from ML experiments (Section 8.3): research experiments test hypotheses through data analysis, backtesting, simulation, or statistical modeling that may or may not involve ML.

**9.4.2 Scope** — Experiment definition, experiment execution, experiment versioning, experiment lifecycle, experiment lineage, experiment governance.

**9.4.3 Research Experiment Model** — Canonical experiment specification: identifier, name, hypothesis references, methodology, input data references (Document 11 datasets), parameters, metrics, results, artifacts, code version, environment, owner, status.

**9.4.4 Experiment Lifecycle** — States: Draft, Running, Completed, Failed, Archived. Distinct from ML experiment lifecycle while sharing reproducibility principles.

**9.4.5 Experiment Reproducibility** — Complete reproducibility evidence per P-13: code version, data version (Document 11), parameters, environment, random seeds.

**9.4.6 Experiment Lineage** — Experiment-to-hypothesis, experiment-to-data, experiment-to-feature, experiment-to-model, experiment-to-experiment (derived, refined) relationships. Integration with Document 7.8 lineage.

**9.4.7 Experiment Comparison** — Multi-experiment comparison for research analysis. Statistical comparison of results across experiments testing related hypotheses.

**9.4.8–9.4.20** — Experiment artifact management, experiment collaboration, experiment security, experiment governance, experiment metrics, risks, acceptance criteria, cross references.

---

### 9.5 Exploratory Data Analysis Architecture — 15 subsections

**9.5.1 Purpose** — Define the governed framework for exploratory data analysis (EDA) within the research platform. EDA provides the initial data understanding that informs hypothesis formulation and experiment design.

**9.5.2 Scope** — Data profiling, visualization, statistical summaries, correlation analysis, pattern discovery, insight capture.

**9.5.3 EDA Session Model** — Canonical EDA session: identifier, dataset references (Document 11), analysis scope, generated visualizations, discovered patterns, captured insights, session artifacts.

**9.5.4 Insight Capture** — Formal capture of insights discovered during EDA. Insights linked to the data and analysis that produced them. Insights feed into hypothesis formulation.

**9.5.5 EDA Governance** — EDA sessions governed as research activities. Distinction between exploratory (hypothesis-generating) and confirmatory (hypothesis-testing) analysis. Governance rigor appropriate to analysis intent.

**9.5.6–9.5.15** — Visualization architecture, statistical profiling, pattern detection, EDA reproducibility, EDA artifact management, EDA security, risks, acceptance criteria, cross references.

---

### 9.6 Statistical Analysis Framework — 20 subsections

**9.6.1 Purpose** — Define the standardized statistical methodology framework for quantitative research. The framework shall provide governed statistical practices preventing common analytical pitfalls.

**9.6.2 Scope** — Statistical testing, significance assessment, multiple testing correction, effect size analysis, power analysis, Bayesian methods, time-series statistics.

**9.6.3 Statistical Test Registry** — Catalog of approved statistical tests with applicability guidance, assumptions, and limitations.

**9.6.4 Multiple Testing Correction** — Framework for multiple comparison correction: Bonferroni, Holm-Bonferroni, Benjamini-Hochberg (False Discovery Rate), family-wise error rate control. Required when testing multiple hypotheses on shared data.

**9.6.5 P-Hacking Prevention** — Design features preventing p-hacking: hypothesis pre-registration, analysis plan pre-registration, sequential testing protocols, data-dependent analysis detection.

**9.6.6 Power Analysis** — Pre-experiment statistical power analysis. Minimum sample size requirements. Post-hoc power reporting.

**9.6.7 Effect Size** — Effect size reporting alongside significance. Standardized effect size measures (Cohen's d, correlation coefficients, information coefficients). Economic significance alongside statistical significance.

**9.6.8 Bayesian Methods** — Support for Bayesian analysis frameworks: prior specification, posterior distribution, credible intervals, Bayes factors. Prior registration and sensitivity analysis.

**9.6.9 Time-Series Statistics** — Time-series specific methods: autocorrelation adjustment, stationarity testing, cointegration, regime detection. Point-in-time correctness for financial time series.

**9.6.10–9.6.20** — Statistical reporting standards, statistical governance, statistical tooling, integration with hypothesis and experiment frameworks, risks, acceptance criteria, cross references.

---

### 9.7 Research Reproducibility Architecture — 16 subsections

**9.7.1 Purpose** — Define the comprehensive framework guaranteeing that every published research finding is reproducible. Extends platform invariants P-13 (Deterministic Processing) and research-specific reproducibility principles.

**9.7.2 Scope** — Reproducibility requirements, reproducibility verification, reproducibility evidence, reproducibility failure handling, reproducibility governance.

**9.7.3 Reproducibility Requirements** — Every published research finding shall be reproducible. Required captures: code, data versions (Document 11), environment, parameters, random seeds, analysis methodology.

**9.7.4 Reproducibility Verification** — Automated reproducibility verification: re-executing the analysis with identical captured state and verifying output matches within tolerance.

**9.7.5 Reproducibility Evidence** — Immutable reproducibility evidence per P-2. Evidence includes: verification result, comparison metrics, any discrepancies and their classification.

**9.7.6 Reproducibility Tiers** — Tiered reproducibility: Gold (fully automated reproduction), Silver (reproduction with documented manual steps), Bronze (complete documentation enabling manual reproduction). Tier appropriate to research significance.

**9.7.7–9.7.16** — Reproducibility failure classification, reproducibility governance, reproducibility tooling, integration with experiment and knowledge frameworks, risks, acceptance criteria, cross references.

---

### 9.8 Knowledge Management Architecture — 18 subsections

**9.8.1 Purpose** — Define the framework for capturing, organizing, discovering, and governing quantitative research knowledge as enterprise assets per the Knowledge as Enterprise Asset principle.

**9.8.2 Scope** — Knowledge capture, knowledge organization, knowledge discovery, knowledge lifecycle, knowledge governance, knowledge collaboration.

**9.8.3 Knowledge Artifact Model** — Canonical knowledge artifact: identifier, type (hypothesis, finding, methodology, insight, report, literature review), content, metadata, references to source experiments, datasets, and evidence.

**9.8.4 Knowledge Taxonomy** — Organizational taxonomy for research knowledge: domain, asset class, signal type, methodology type, statistical approach, market regime.

**9.8.5 Knowledge Discovery** — Search, browse, and recommendation of research knowledge. Full-text search, taxonomy browse, related-knowledge recommendations.

**9.8.6 Knowledge Lifecycle** — States: Draft, Review, Published, Updated, Deprecated, Archived. Knowledge versioning — updates create new versions preserving history.

**9.8.7–9.8.18** — Literature management, research report generation, knowledge collaboration, knowledge security, knowledge governance, knowledge metrics, risks, acceptance criteria, cross references.

---

### 9.9 Research Collaboration Architecture — 14 subsections

**9.9.1 Purpose** — Define the framework for multi-user research collaboration including workspace sharing, peer review, co-authoring, and collaborative analysis.

**9.9.2 Scope** — Workspace sharing, collaborative editing, peer review, co-authoring, access control, collaboration governance.

**9.9.3 Collaboration Model** — Collaboration roles: Owner, Editor, Reviewer, Viewer. Role-based access to research workspaces, experiments, and knowledge artifacts.

**9.9.4 Peer Review Architecture** — Formal peer review workflow for research findings before publication. Reviewer assignment, review criteria, review evidence, review decisions.

**9.9.5–9.9.14** — Collaborative editing, version conflict resolution, collaboration notifications, collaboration security, collaboration governance, collaboration metrics, risks, acceptance criteria, cross references.

---

### 9.10 Research Artifact Management — 16 subsections

**9.10.1 Purpose** — Define the framework for managing research artifacts — notebooks, scripts, reports, datasets, results, visualizations — as governed enterprise assets.

**9.10.2 Scope** — Artifact types, artifact storage, artifact versioning, artifact lifecycle, artifact discovery, artifact governance.

**9.10.3 Artifact Model** — Canonical artifact specification: identifier, type, format, content reference, provenance (creator, timestamp, source experiment/hypothesis), version, dependencies (data, code, environment).

**9.10.4 Artifact Versioning** — Every artifact modification creates a new version per P-2. Version linkage to experiment and hypothesis versions.

**9.10.5 Artifact Storage** — Artifact storage through Document 11 storage infrastructure per D-7.1. Artifact format governance.

**9.10.6–9.10.16** — Artifact lifecycle, artifact discovery, artifact security, artifact governance, artifact metrics, risks, acceptance criteria, cross references.

---

### 9.11 Research Governance Architecture — 22 subsections

**9.11.1 Purpose** — Define the research-specific governance framework extending Document 7.11 Data Governance. Covers research approval, review, compliance, audit, and accountability.

**9.11.2 Scope** — Research approval workflows, research review, research compliance, research audit, research stewardship, research exception management, research ethics.

**9.11.3 Research Approval Gates** — Hypothesis approval, experiment approval, publication approval, promotion approval. Each gate with defined approvers, evidence requirements, and immutable records.

**9.11.4 Research Review** — Peer review and governance review of research findings. Review criteria: statistical validity, reproducibility, methodology soundness, economic relevance.

**9.11.5 Research Ethics** — Ethical guidelines for quantitative research. Prohibition of data snooping, p-hacking, selective reporting, and other research misconduct. Detection mechanisms and consequences.

**9.11.6 Research Stewardship** — Every research project shall have a designated Research Steward extending D-7.11.6. Responsibilities: methodology oversight, review coordination, knowledge preservation.

**9.11.7–9.11.22** — Research audit trail, research compliance, research exception management, research change management, governance reporting, governance dashboards, governance metrics, governance monitoring, governance performance, governance scalability, risks, acceptance criteria, cross references.

---

### 9.12 Research Lifecycle Architecture — 15 subsections

**9.12.1 Purpose** — Define the research lifecycle from ideation through promotion to production. Extends Document 7.4 Data Lifecycle without redefining it.

**9.12.2 Scope** — Research project lifecycle, hypothesis lifecycle (coordinates with Section 9.3), experiment lifecycle (coordinates with Section 9.4), knowledge lifecycle (coordinates with Section 9.8).

**9.12.3 Research Project Lifecycle** — States: Ideation, Exploration, Validation, Publication, Promotion, Production Integration, Archived, Retired. State transitions governed with approval gates.

**9.12.4 Ideation Phase** — Research ideation: problem identification, literature review, hypothesis generation, feasibility assessment. Ideation artifacts captured as knowledge.

**9.12.5 Exploration Phase** — Exploratory data analysis, initial experimentation, methodology development. Governance appropriate to exploratory intent.

**9.12.6 Validation Phase** — Confirmatory analysis, statistical validation, reproducibility verification, peer review. Governance rigor appropriate to production intent.

**9.12.7 Publication Phase** — Research finding publication, knowledge artifact creation, stakeholder communication.

**9.12.8 Promotion Phase** — Research-to-production promotion via Section 9.13. Governance gates for production entry.

**9.12.9–9.12.15** — Research project archival, retirement, lifecycle monitoring, lifecycle governance, risks, acceptance criteria, cross references.

---

### 9.13 Research-to-Production Promotion Architecture — 18 subsections

**9.13.1 Purpose** — Define the governed framework for promoting validated research findings into production platforms: strategy development (Document 14), portfolio construction (Document 15), or ML development (Document 12).

**9.13.2 Scope** — Promotion criteria, promotion gates, promotion workflow, promotion evidence, promotion governance, promotion rollback.

**9.13.3 Promotion Criteria** — Research finding shall satisfy before promotion: reproducibility verified, peer review passed, statistical validity confirmed, governance approval obtained, production impact assessed.

**9.13.4 Promotion Gates** — Gate types: Strategy Promotion (to Document 14), Portfolio Promotion (to Document 15), Model Promotion (to Document 12 Section 8.4), Feature Promotion (to Document 12 Section 8.2). Each gate with destination-specific requirements.

**9.13.5 Promotion Evidence Package** — Complete evidence package for promotion: research experiment records, statistical validation, reproducibility evidence, peer review records, governance approvals, artifact references.

**9.13.6 Promotion Workflow** — Stepwise promotion: submission, review, approval, destination platform integration, verification, monitoring.

**9.13.7–9.13.18** — Promotion to strategy development, promotion to portfolio construction, promotion to ML development, promotion rollback, promotion governance, promotion audit trail, promotion metrics, risks, acceptance criteria, cross references.

---

### 9.14 Research Security Architecture — 14 subsections

**9.14.1 Purpose** — Define research-specific security controls extending Document 7.12. Covers workspace isolation, IP protection, data access governance, and research artifact security.

**9.14.2 Scope** — Workspace isolation, data access governance, IP protection, artifact access control, collaboration security.

**9.14.3 Data Access Governance** — Research data access through governed contracts per D-8. Temporary data copies scoped to workspace and project. Access revocation on workspace suspension.

**9.14.4–9.14.14** — IP protection, artifact encryption, collaboration access control, security monitoring, threat detection, security testing, risks, acceptance criteria, cross references.

---

### 9.15 Research Observability Architecture — 12 subsections

**9.15.1 Purpose** — Define research-specific observability extending Document 7.13. Covers research productivity metrics, resource utilization, experiment velocity, and research activity monitoring.

**9.15.2 Scope** — Research metrics, research dashboards, research activity monitoring, research resource utilization.

**9.15.3 Research Metrics** — Metric categories: Productivity (hypotheses tested, experiments completed, findings published), Quality (reproducibility rate, peer review pass rate), Velocity (time-to-conclusion, time-to-promotion), Resource (workspace utilization, compute consumption).

**9.15.4–9.15.12** — Research dashboards, research SLOs, research alerting, integration with enterprise observability, risks, acceptance criteria, cross references.

---

### 9.16 Research Infrastructure Architecture — 12 subsections

**9.16.1 Purpose** — Define the compute, storage, and networking infrastructure supporting the research platform. Extends platform infrastructure without redefining it.

**9.16.2 Scope** — Compute resource management, storage allocation, networking, container orchestration for research workspaces.

**9.16.3 Compute Resource Management** — CPU, memory, GPU allocation for research workspaces. Resource pooling, scheduling, and quotas. Burst capacity for intensive analyses.

**9.16.4 –9.16.12** — Storage, networking, container management, infrastructure abstraction (P-3, M-6), cost optimization, risks, acceptance criteria, cross references.

---

## Cross-Document Dependencies

### Documents that Document 13 depends on

| Document | Title | Nature of Dependency |
|----------|-------|---------------------|
| 00 | Project Constitution | Architectural principles, strategy independence, research as platform capability |
| 02 | System Architecture | Research Engine as system component; integration boundaries |
| 03 | Technology Stack | Technology independence constraints |
| 09 | Database Architecture | Database services |
| 10 | API Specification | API design standards |
| **11** | **Data Engineering** | **Primary data dependency** — governed data access, metadata, lineage, quality, governance, security, observability |
| **12** | **Machine Learning Engineering** | Feature consumption, experiment tracking distinction, model consumption, ML-to-research promotion |
| 14 | Trading Infrastructure | Promotion target for strategy research |
| 15 | Portfolio Management | Promotion target for portfolio research |

### Documents that depend on Document 13

| Document | Title | Nature of Dependency |
|----------|-------|---------------------|
| 14 | Trading Infrastructure | Consumes promoted research findings for strategy development |
| 15 | Portfolio Management | Consumes promoted research findings for portfolio construction |

---

## Explicit Exclusions

The following topics are not covered by Document 13 and shall not be introduced:

- **Strategy-specific hypotheses or research** — Violates P-1. Research platform is generic; specific strategies are configurations.
- **Specific statistical libraries or tools** — Violates P-3. Architecture defines interfaces, not implementations.
- **Specific research methodologies for particular asset classes** — Domain-specific, not platform architecture.
- **Data storage, data quality, data governance, data security** — Frozen in Document 11.
- **Feature engineering, ML experiment tracking, model training, model validation, model registry, model serving** — Frozen in Document 12. Document 13 consumes these, does not redefine.
- **Strategy development, backtesting execution** — Owned by Document 14.
- **Portfolio construction models** — Owned by Document 15.
- **Cloud-specific deployment** — Violates F-5, P-18.
- **Frontend UI for research dashboards** — Owned by Documents 06/08.

---

## Section Summary

| Section | Topic | Subsections |
|---------|-------|-------------|
| 9.1 | Research Platform Architecture | 25 |
| 9.2 | Research Workspace Architecture | 22 |
| 9.3 | Hypothesis Management Architecture | 18 |
| 9.4 | Research Experiment Architecture | 20 |
| 9.5 | Exploratory Data Analysis Architecture | 15 |
| 9.6 | Statistical Analysis Framework | 20 |
| 9.7 | Research Reproducibility Architecture | 16 |
| 9.8 | Knowledge Management Architecture | 18 |
| 9.9 | Research Collaboration Architecture | 14 |
| 9.10 | Research Artifact Management | 16 |
| 9.11 | Research Governance Architecture | 22 |
| 9.12 | Research Lifecycle Architecture | 15 |
| 9.13 | Research-to-Production Promotion Architecture | 18 |
| 9.14 | Research Security Architecture | 14 |
| 9.15 | Research Observability Architecture | 12 |
| 9.16 | Research Infrastructure Architecture | 12 |
| **Total** | | **277** |

---

## Numbering Convention

- Document 11 = Parts 1–7 (Sections 7.1–7.13)
- Document 12 = Part 8 (Sections 8.1–8.12)
- Document 13 = Part 9 (Sections 9.1–9.16)
- Heading format: `## 9.X.Y` for subsections, `###` for named sub-items
- Document file: `docs/13_Research_Engineering.md`
- Every section ends with Risks, Acceptance Criteria, Cross References
- Cross-references to Documents 11 and 12 use frozen decision or section identifiers
- No "Continue from" or "Append the following" assembly markers
- Requirements use "shall" (not "must" or "should")
- Strategy independence: Lancaster references only in negation

---

## Writing Standards

Document 13 shall follow all rules in:

- `handbook/HANDBOOK_RULES.md`
- `handbook/WRITING_STANDARD.md`
- `handbook/ARCHITECTURE_PRINCIPLES.md`
- `handbook/ARCHITECTURAL_INVARIANTS.md` — All 36 invariants (P-1 through P-18, D-1 through D-10, M-1 through M-8)
- `handbook/TERMINOLOGY.md`
- `handbook/FROZEN_DECISIONS.md` — All frozen decisions from Documents 11 and 12

---

## Approval

| Role | Decision |
|------|----------|
| Document 13 Outline | PENDING APPROVAL |
| Sections | 9.1 through 9.16, 277 total subsections |
| Date | 2026-06-30 |
| Scope boundaries | As defined — zero overlap with frozen Documents 11 and 12 |
| Amendment process | Governance approval required for section additions, removals, or scope changes |
| Content generation | Shall follow this outline without deviation |
