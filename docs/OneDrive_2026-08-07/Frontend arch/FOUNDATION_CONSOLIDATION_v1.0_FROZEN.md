# FOUNDATION_CONSOLIDATION

**Status:** Batch 1 --- FROZEN v1.0

**Owner Domain:** FOUND --- Foundation

## Purpose

Foundation defines the immutable architectural principles governing the
Production Decision OS frontend.

These principles are inherited by every other domain.

------------------------------------------------------------------------

# Canonical Decisions

## FOUND-001 --- Decision First

**Status:** LOCKED

The frontend exists to support investment decisions rather than merely
display market information.

------------------------------------------------------------------------

## FOUND-002 --- Portfolio First

**Status:** LOCKED

Every recommendation is evaluated in the context of the user's existing
portfolio.

------------------------------------------------------------------------

## FOUND-003 --- Evidence Driven

**Status:** LOCKED

Every recommendation must be supported by explainable evidence.

No opaque or black-box recommendations are permitted.

------------------------------------------------------------------------

## FOUND-004 --- Shared vs Personalized Intelligence

**Status:** LOCKED

Shared intelligence (Market Intelligence and Investability) is computed
once.

Recommendations are personalized using user portfolio and constraints.

------------------------------------------------------------------------

## FOUND-005 --- Single Owner Domain & Single Source of Truth

**Status:** LOCKED

Each business concept has exactly one owner domain.

Other domains may reference but never redefine that concept.

------------------------------------------------------------------------

## FOUND-006 --- Backend Computes, Frontend Composes

**Status:** LOCKED

Backend owns:

-   Business rules
-   Market intelligence
-   Recommendation generation
-   Portfolio analytics

Frontend owns:

-   Read models
-   View models
-   Presentation models
-   Composition
-   User interaction

Frontend must adapt to the frozen backend API and never reimplement
backend business logic.

------------------------------------------------------------------------

## FOUND-007 --- Governance & Architecture Evolution

**Status:** LOCKED

Architecture evolves only through controlled governance.

Rules:

-   Scope Freeze before implementation
-   Canonical decisions are version controlled
-   Architectural changes require ADR approval
-   Deprecated decisions must be superseded rather than silently
    modified

------------------------------------------------------------------------

# Dependency Rules

All domains depend on Foundation:

-   REF
-   MI
-   INV
-   DEC
-   PORT
-   WATCH
-   USER
-   UI
-   UX

Foundation depends on no other domain.

------------------------------------------------------------------------

# Freeze Decision

Batch 1 is frozen.

Future modifications require an approved Architecture Decision Record
(ADR).
