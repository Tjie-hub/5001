# DECISION_CENTER_DESIGN_SPEC_v1.0

Status: FROZEN

## 1. Executive Summary
Decision Center is the primary operational workspace for evaluating, prioritizing, and acting on investment recommendations. It presents backend intelligence without owning business logic.

## 2. Design Goals
- Understand portfolio status within 5 seconds.
- Surface the highest-priority recommendation.
- Explain every recommendation.
- Show portfolio impact before action.
- Complete decisions within a single workspace.

## 3. User Personas
Primary: Portfolio Manager
Secondary: Active Investor
Future: Investment Team

## 4. Business Outcomes
- Know today's priorities.
- Understand recommendation rationale.
- Understand risks.
- Understand opportunity cost.
- Decide with full portfolio context.

## 5. User Scenarios
- Morning Review
- Buy Candidate
- Rotate Position
- Hold Decision
- Exit Decision
- No Recommendation

## 6. UX Principles
- Decision Before Analysis
- Portfolio Before Stock
- Explain Before Execute
- Simulate Before Confirm
- One Primary Action
- No Dead Ends

## 7. Information Priority
Critical Action → Recommendation → Portfolio Context → Evidence → History

## 8. Region Specification
1. Executive Summary
2. Recommendation Queue
3. Recommendation Detail
4. Portfolio Context
5. Market Context
6. Action Panel
7. Activity Timeline

## 9. Widget Specification
Recommendation Card includes:
- Recommendation
- Priority
- Confidence
- Expected Return (Gross/Net)
- Expected Risk
- Opportunity Cost
- Fundamental Rank
- Investability Rank
- Risk Flags
- Explanation

## 10. Interaction & Decision Journey
Review Recommendation →
Review Evidence →
Review Portfolio Impact →
Review Opportunity Cost →
Execution Simulation →
Confirmation →
Portfolio Update

## 11. Implementation Specification
### State Model
INITIAL → LOADING → READY → REVIEWING → SIMULATING → CONFIRMING → COMPLETED → REFRESHING → READY

Error States:
- NETWORK_ERROR
- API_ERROR
- PARTIAL_DATA
- STALE_DATA
- UNAUTHORIZED

### API Boundary
Frontend consumes frozen APIs only.
No business logic duplication.
No recommendation calculation.

### Refresh
- Automatic after EOD/events
- Manual refresh supported
- Event-driven preferred

### Accessibility
- Keyboard navigation
- Screen reader support
- WCAG contrast
- Visible focus

### Acceptance Criteria
- Supports Buy, Scale In, Hold, Rotate, Exit, No Recommendation
- No business logic in frontend
- Consistent state synchronization
- Responsive across devices

## 12. Architectural Constraints

### Frontend SHALL
- Present backend results.
- Orchestrate workspace information.
- Support operator review.
- Support execution simulation.
- Record recommendation responses.

### Frontend SHALL NOT
- Calculate recommendations.
- Calculate rankings or scores.
- Modify portfolio directly.
- Modify market intelligence.
- Hide risk flags.
- Become source of truth.

### Frontend MAY
- Format data.
- Filter locally.
- Persist UI preferences.
- Manage presentation state.

### Domain Ownership
Decision Center consumes:
- Decision Engine
- Market Intelligence
- Investability
- Portfolio
- Watchlist

It owns presentation only.

## Freeze Decision
This document is approved as the baseline implementation specification for Decision Center and serves as the reference for wireframes, prototype, frontend implementation, and QA.
