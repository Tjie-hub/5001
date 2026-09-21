# DECISION_INTELLIGENCE_CONSOLIDATION

**Status:** Batch 2 --- FROZEN v1.0

**Owner Domain:** DEC --- Decision Intelligence

## Purpose

Decision Intelligence is the decision-making core of the Production
Decision OS.

It transforms shared market intelligence and personalized portfolio
context into explainable, actionable recommendations.

It owns recommendations only.

------------------------------------------------------------------------

# Canonical Decisions

## DEC-001 --- Personalized Recommendation

**Status:** LOCKED

Recommendations are generated using: - Shared Market Intelligence -
Investability - Portfolio State - User Constraints

Market intelligence is shared. Recommendations are personalized.

------------------------------------------------------------------------

## DEC-002 --- Today's Best Action

**Status:** LOCKED

The engine always determines the highest-priority action:

-   Buy
-   Scale In
-   Hold
-   Rotate
-   Reduce
-   Exit
-   No Action

"No Action" is a valid recommendation when no positive edge exists.

------------------------------------------------------------------------

## DEC-003 --- Opportunity Cost Engine

**Status:** LOCKED

Every recommendation evaluates:

-   Existing positions
-   New opportunities
-   Expected alpha differential
-   Transaction costs
-   Risk

Rotation must pass Opportunity Cost analysis.

------------------------------------------------------------------------

## DEC-004 --- Position Sizing

**Status:** LOCKED

Decision Intelligence owns:

-   Initial allocation
-   Scale In
-   Scale Out
-   Maximum allocation
-   Capital deployment guidance

Portfolio Intelligence provides investment capacity only.

------------------------------------------------------------------------

## DEC-005 --- Portfolio Rotation

**Status:** LOCKED

Rotation is recommended only when:

-   Better opportunity exists
-   Expected alpha exceeds switching costs
-   Risk-adjusted outcome improves

Diversification constraints remain mandatory.

------------------------------------------------------------------------

## DEC-006 --- Event Driven Review

**Status:** LOCKED

Recommendations are recalculated after:

-   End of day
-   Material news
-   Macro events
-   Corporate actions
-   Portfolio changes

------------------------------------------------------------------------

## DEC-007 --- Recommendation Lifecycle

**Status:** LOCKED

Lifecycle:

1.  Created
2.  Active
3.  Reviewed
4.  Accepted
5.  Rejected
6.  Expired
7.  Superseded

------------------------------------------------------------------------

## DEC-008 --- Recommendation Identity

**Status:** LOCKED

Every recommendation owns:

-   Recommendation ID
-   Timestamp
-   Version
-   Status

User responses reference Recommendation IDs only.

------------------------------------------------------------------------

## DEC-009 --- Recommendation Explainability

**Status:** LOCKED

Every recommendation must explain:

-   Primary drivers
-   Expected edge
-   Key risks
-   Confidence
-   Why this action is preferred

------------------------------------------------------------------------

# Dependency Rules

Consumes: - Market Intelligence - Investability - Portfolio
Intelligence - User Intelligence

Produces: - Recommendation - Recommendation Identity - Position Sizing -
Opportunity Cost Assessment

Decision Intelligence never owns:

-   Market calculations
-   Portfolio analytics
-   User records

------------------------------------------------------------------------

# Freeze

Batch 2 is frozen.

Further changes require ADR approval.
