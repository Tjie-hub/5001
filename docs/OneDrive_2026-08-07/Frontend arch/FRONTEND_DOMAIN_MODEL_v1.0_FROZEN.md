# FRONTEND_DOMAIN_MODEL

**Status:** v1.0 (Frozen)\
**Phase:** Phase 3A -- Architecture Foundation

------------------------------------------------------------------------

# 1. Purpose

This document defines the canonical frontend domain model for the
Production Decision OS.

It establishes:

-   Domain boundaries
-   Domain ownership
-   Dependency rules
-   Shared vs Personalized boundaries
-   Frontend architectural responsibilities

This document does **not** define backend business logic.

------------------------------------------------------------------------

# 2. Core Principles

-   Decision First
-   Portfolio First
-   Evidence Driven
-   Event Driven
-   Shared Market Intelligence
-   Personalized Recommendation
-   Single Owner Domain
-   Frozen API Contract
-   Frontend owns presentation models, not backend business logic.

------------------------------------------------------------------------

# 3. Ownership Model

Backend owns:

-   Business rules
-   Calculations
-   Market intelligence generation
-   Recommendation generation
-   REST API contract

Frontend owns:

-   Read Models
-   View Models
-   Presentation Models
-   Page composition
-   Interaction
-   User experience

The frontend never re-implements backend business rules.

------------------------------------------------------------------------

# 4. Domain Classification

## Shared Domains

Shared across every user:

-   FOUND
-   REF
-   MI
-   INV

## Personalized Domains

Generated from user state:

-   DEC
-   PORT
-   WATCH
-   USER

## Presentation Domains

-   UI
-   UX

------------------------------------------------------------------------

# 5. Canonical Domains

## FOUND --- Foundation

Owns:

-   Vision
-   Principles
-   Architecture Rules
-   Naming Conventions
-   Dependency Rules

------------------------------------------------------------------------

## REF --- Reference Model

Owns canonical shared reference data:

-   Instrument / Ticker
-   Sector Taxonomy
-   Corporate Actions
-   Data Freshness
-   Event Lifecycle
-   API Contract

All business domains reference REF. REF owns no business decisions.

------------------------------------------------------------------------

## MI --- Market Intelligence

Answers:

> Is this market opportunity attractive?

Owns:

-   Long Edge
-   Short Edge
-   Market Regime
-   Sector Rotation
-   Order Flow
-   Seasonal Intelligence
-   Market-level Fundamental Assessment

------------------------------------------------------------------------

## INV --- Investability

Answers:

> Is capital safe in this instrument?

Owns assessment only:

-   Cash Flow Quality
-   Financial Health
-   Ownership Risk
-   Free Float Assessment
-   Governance
-   Trading Quality
-   Capital Entrapment Risk
-   Speculation Score

INV produces scores and assessments only.

It never produces recommendations.

------------------------------------------------------------------------

## DEC --- Decision Intelligence

Answers:

> What action should this user take?

Consumes:

-   MI
-   INV
-   PORT
-   USER

Owns:

-   Recommendation
-   Position Sizing
-   Priority
-   Opportunity Cost
-   Rotation
-   Scale In
-   Scale Out
-   Hold
-   Exit
-   Alpha Differential
-   Probability

------------------------------------------------------------------------

## PORT --- Portfolio Intelligence

Owns portfolio analytics:

-   Portfolio Health
-   Diversification
-   Capital Allocation
-   Position Lifecycle
-   Trade Cycle
-   Investment Capacity

Consumes execution records from USER.

------------------------------------------------------------------------

## WATCH --- Watchlist Intelligence

Owns the personalized Dynamic Persistent Watchlist.

Consumes:

-   MI
-   INV
-   USER

Owns:

-   Ranking
-   Promotion
-   Demotion
-   Lifecycle
-   History

------------------------------------------------------------------------

## USER --- User Intelligence

Owns user facts only.

-   User Profile
-   Portfolio Records
-   Execution Records
-   Recommendation Response State

Recommendation Response stores **RecommendationID references only**.

USER never owns recommendations.

------------------------------------------------------------------------

## UI --- Information Architecture

Owns:

-   Navigation
-   Routing
-   Page hierarchy
-   Screen composition

------------------------------------------------------------------------

## UX --- Experience System

Owns:

-   Executive Summary presentation
-   Explainability presentation
-   Visualization
-   Component behaviour
-   Interaction patterns
-   Design language

UX never owns business concepts.

------------------------------------------------------------------------

# 6. Explicit Dependency Rules

The following rules are normative.

-   MI depends on FOUND and REF.
-   INV depends on FOUND and REF.
-   DEC depends on MI, INV, PORT and USER.
-   PORT depends on USER.
-   WATCH depends on MI, INV and USER.
-   UI depends on DEC, PORT, WATCH and USER view models.
-   UX depends on UI components.
-   Shared domains never depend on personalized domains.
-   One business concept has exactly one owner domain.
-   Cross-domain access is by reference only.

------------------------------------------------------------------------

# 7. Out of Scope

Excluded from this document:

-   Research Engine internals
-   Agent Firm
-   Broker Integration
-   OMS
-   AI Training
-   Backend implementation

------------------------------------------------------------------------

# 8. Next Deliverables

1.  FRONTEND_DECISION_REGISTRY.md
2.  FRONTEND_MASTER_PLAN.md
3.  Page Specifications
4.  Wireframes
5.  HTML Prototype
6.  PWA Implementation

------------------------------------------------------------------------

# Freeze Decision

This document is frozen as the canonical frontend domain model.

Future architectural changes must be introduced through an Architecture
Decision Record (ADR) before modifying this document.
