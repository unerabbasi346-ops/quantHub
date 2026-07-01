# Quant Hub Engineering Handbook

Document: 00_PROJECT_CONSTITUTION.md (Draft v1.0)
Status: APPROVED & FROZEN

Version: 1.0

Ratified: July 2026
Authority: Highest governing engineering specification

## Purpose

This constitution defines the engineering principles governing the Quant Hub platform. Every architectural, implementation, testing, documentation, and deployment decision must align with this document unless formally amended.

## Platform Definition

Quant Hub is a modular quantitative research, analytics, execution, monitoring, and portfolio platform. It is not a single trading bot. Strategies (including Lancaster) are plugins built on top of the platform.

## Mission

Build a long-lived quantitative platform whose architecture survives changing markets, strategies, and technologies.

## Vision

Provide a reusable ecosystem supporting research, backtesting, paper trading, live trading, machine learning, monitoring, risk management, and future multi-asset expansion.

## Core Principles

• Architecture before implementation
• Documentation before complexity
• Modular design
• Strategy-independent core
• Security by design
• Testing is mandatory
• Observable systems
• Measured performance
• Continuous improvement

## Engineering Rules

1. Every feature begins with a design.
2. Every module has one responsibility.
3. Public interfaces are documented.
4. No hidden business logic.
5. No undocumented breaking changes.
6. Every production feature has automated tests.
7. Technical debt must be recorded.

## Definition of Done

A feature is complete only after implementation, review, tests, documentation, logging, configuration support, and validation are finished.

## Governance

This handbook is the primary specification.
Claude Code implements the specification.
Ruflo coordinates engineering workflows.
Architectural changes require handbook updates before implementation.

## Future Direction

Quant Hub is intended to expand into a complete quantitative operating platform supporting multiple asset classes, exchanges, research pipelines, AI-assisted development, and institutional workflows.

### 14.1 Purpose

This section defines mandatory governance requirements for all AI-assisted development activities conducted within the Quant Hub project.

### 14.2 Scope

Applies to:

Claude Code

Claude AI

ChatGPT

Future AI coding agents

Any autonomous development tools

### 14.3 Handbook Authority

The Engineering Handbook is the sole architectural authority.

AI agents shall not contradict, replace, or reinterpret frozen handbook decisions.

### 14.4 Mandatory Handbook Loading

Before beginning any implementation task an AI agent shall:

Load relevant handbook documents.

Load frozen decisions.

Load implementation readiness.

Load traceability matrix.

Use these as the governing specification.

### 14.5 Human Authority

AI agents shall never become decision makers.

Architectural ownership remains with the human project owner.

Whenever ambiguity exists:

AI shall stop.

AI shall request clarification.

AI shall not invent architecture.

### 14.6 Modification Restrictions

AI agents may

implement

explain

review

audit

AI agents shall not

redefine architecture

change invariants

rewrite frozen documents

introduce conflicting terminology

unless explicitly instructed.

### 14.7 Source of Truth

If two documents disagree

AI shall

stop

report the conflict

request human resolution

AI shall never silently choose one interpretation.

### 14.8 Implementation Restrictions

Implementation shall follow

Architecture

↓

Contracts

↓

Interfaces

↓

Technology

Never the reverse.

### 14.9 Security Restrictions

AI agents shall never

access production credentials

generate secrets

execute production trades

deploy to production

modify live infrastructure

without explicit human authorization.

### 14.10 Commit Restrictions

AI shall never

commit

merge

release

tag

without explicit instruction.

### 14.11 Verification

Every completed implementation shall cite

governing handbook document

governing section

governing invariant

before being considered complete.
