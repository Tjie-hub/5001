# FRONTEND_DECISION_REGISTRY

**Status:** Draft v0.1\
**Depends On:** FRONTEND_DOMAIN_MODEL v1.0 (Frozen)

------------------------------------------------------------------------

# Purpose

This registry is the single source of truth for all frontend
architectural and business decisions.

It consolidates the previously discussed F-001...F-040 decisions into
canonical decision records.

Rules:

-   One decision = one owner domain.
-   No duplicated decisions.
-   Cross-domain references only.
-   All decisions are either LOCKED or FUTURE.
-   Changes require ADR after freeze.

------------------------------------------------------------------------

# Registry Structure

  Domain                     Prefix   Purpose
  -------------------------- -------- --------------------------------
  Foundation                 FOUND    Vision, principles, governance
  Reference                  REF      Shared reference models
  Market Intelligence        MI       Shared market intelligence
  Investability              INV      Instrument quality assessment
  Decision Intelligence      DEC      Recommendation engine
  Portfolio Intelligence     PORT     Portfolio analytics
  Watchlist Intelligence     WATCH    Dynamic persistent watchlist
  User Intelligence          USER     User facts and execution state
  Information Architecture   UI       Pages and navigation
  User Experience            UX       Presentation and interaction

------------------------------------------------------------------------

# Decision Record Template

Each decision follows the same format.

``` text
Decision ID

Owner Domain

Title

Status

Dependencies

Description

Rationale

Consequences

Referenced By
```

------------------------------------------------------------------------

# FOUNDATION

## FOUND-001 --- Decision First

Status: LOCKED

The frontend exists to support investment decisions rather than display
raw market data.

------------------------------------------------------------------------

## FOUND-002 --- Portfolio First

Status: LOCKED

All recommendations are evaluated relative to the user's portfolio.

------------------------------------------------------------------------

## FOUND-003 --- Single Owner Domain

Status: LOCKED

Each business concept has exactly one owner domain.

------------------------------------------------------------------------

## FOUND-004 --- Frozen API Contract

Status: LOCKED

Frontend adapts to the frozen backend API.

------------------------------------------------------------------------

# MARKET INTELLIGENCE

## MI-001 --- Shared Market Intelligence

Status: LOCKED

Market intelligence is computed once and shared across all users.

------------------------------------------------------------------------

## MI-002 --- Market Edge

Status: LOCKED

Long Edge, Short Edge, Regime and Sector Rotation are objective market
outputs.

------------------------------------------------------------------------

# INVESTABILITY

## INV-001 --- Investability Assessment

Status: LOCKED

Investability evaluates whether capital is safe in an instrument.

------------------------------------------------------------------------

## INV-002 --- Capital Entrapment Risk

Status: LOCKED

Ownership concentration, free float, liquidity and suspension risk
contribute to Capital Entrapment Risk.

------------------------------------------------------------------------

## INV-003 --- Ownership Risk

Status: LOCKED

Ownership concentration is assessed independently from market edge.

------------------------------------------------------------------------

# DECISION INTELLIGENCE

## DEC-001 --- Personalized Recommendation

Status: LOCKED

Recommendations are generated per user using shared market intelligence
and personalized constraints.

------------------------------------------------------------------------

## DEC-002 --- Opportunity Cost

Status: LOCKED

Every recommendation considers opportunity cost against existing
holdings.

------------------------------------------------------------------------

## DEC-003 --- Position Sizing

Status: LOCKED

Decision Intelligence owns position sizing, scale-in and scale-out
guidance.

------------------------------------------------------------------------

## DEC-004 --- Event Driven Review

Status: LOCKED

Recommendations are recalculated after meaningful events.

------------------------------------------------------------------------

# PORTFOLIO

## PORT-001 --- Portfolio Health

Status: LOCKED

Portfolio quality is evaluated beyond profit and loss.

------------------------------------------------------------------------

## PORT-002 --- Investment Capacity

Status: LOCKED

Recommendations use investable capital instead of current cash balance.

------------------------------------------------------------------------

# WATCHLIST

## WATCH-001 --- Dynamic Persistent Watchlist

Status: LOCKED

Watchlists evolve continuously and are not equivalent to buy signals.

------------------------------------------------------------------------

# USER

## USER-001 --- Recommendation Response

Status: LOCKED

User responses reference Recommendation IDs and never redefine
recommendations.

------------------------------------------------------------------------

# UI

## UI-001 --- Decision Center

Status: LOCKED

Decision Center is the primary operational workspace.

------------------------------------------------------------------------

## UI-002 --- Portfolio Dashboard

Status: LOCKED

Portfolio Dashboard focuses on portfolio quality and decision support.

------------------------------------------------------------------------

# UX

## UX-001 --- Executive Summary

Status: LOCKED

Executive Summary presents ratings and recommendations rather than raw
financial metrics.

------------------------------------------------------------------------

# Next Phase

This registry will be expanded until every canonical decision from the
brainstorming process has been mapped into an owner domain.

Once complete and frozen, it becomes the source document for:

1.  FRONTEND_MASTER_PLAN.md
2.  Page Specifications
3.  Wireframes
4.  HTML/PWA implementation
