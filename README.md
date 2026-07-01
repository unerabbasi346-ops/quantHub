# Quant Hub

Modular quantitative research, analytics, execution, monitoring, and portfolio platform.

## Governance

This repository is governed by the Quant Hub Engineering Handbook v1.0.

- Governing constitution: Doc 00 — Project Constitution (APPROVED & FROZEN v1.0, ratified July 2026)
- Repository structure: Doc 04 — Repository Structure (QH-004)
- Technology stack: Doc 03 — Technology Stack (QH-003)
- AI agent governance: Doc 00 §14 — AI Agent Governance

Per Doc 00 §14.11: every implementation cites governing handbook document, section, and invariant.

## Repository Structure

Per Doc 04 — Repository Structure (QH-004):

| Directory | Purpose |
|-----------|---------|
| `docs/` | Engineering handbook and ADRs |
| `backend/` | Core APIs and business services |
| `frontend/` | Dashboard UI |
| `data/` | Data ingestion and storage logic |
| `strategies/` | Strategy plugins (Lancaster and future) |
| `research/` | Experimental quantitative research |
| `ml/` | Machine learning pipelines |
| `infrastructure/` | Deployment and DevOps |
| `scripts/` | Automation utilities |
| `tests/` | Unit, integration and regression tests |
| `configs/` | Configuration files |
| `docker/` | Containers and compose files |
| `logs/` | Runtime logs (gitignored) |
| `assets/` | Icons, images and branding |
| `notebooks/` | Exploratory research only |
| `.github/` | GitHub workflows and templates |

Doc 04 naming conventions: directories use `lowercase_snake_case`, Python modules use `snake_case`, classes use `PascalCase`, functions use `snake_case`, constants use `UPPER_CASE`, configuration files use `descriptive lowercase`.

## Technology Stack

Per Doc 03 — Technology Stack (QH-003):

| Component | Choice |
|-----------|--------|
| Language | Python 3.12 |
| Backend Framework | FastAPI |
| Frontend | Next.js + React + TypeScript |
| Styling | Tailwind CSS |
| Database | PostgreSQL |
| Cache | Redis |
| ORM | SQLAlchemy |
| Data Validation | Pydantic |
| Containerization | Docker |

## Invariant Compliance

Architectural invariants governing this repository (per handbook/ARCHITECTURAL_INVARIANTS.md):

- P-1 Strategy Independence — platform never assumes any specific trading strategy
- P-3 Technology Independence — architecture independent of storage engines, clouds, frameworks
- P-9 Separation of Concerns — each directory owns exactly one architectural domain
- P-14 Security by Design — no secrets committed to version control
- P-17 Enterprise Governance — every asset governed; governance by default
