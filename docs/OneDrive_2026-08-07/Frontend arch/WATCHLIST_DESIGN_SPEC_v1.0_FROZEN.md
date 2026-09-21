# WATCHLIST_DESIGN_SPEC_v1.0

Status: FROZEN

## 1. Executive Summary
Watchlist Workspace is the observation pipeline for investment candidates. It tracks candidate evolution and provides context before investigation or decision.

## 2. Design Goals
- Monitor all candidates in one place.
- Surface meaningful candidate changes.
- Explain promotions and demotions.
- Preserve objective candidate ordering.
- Support seamless transition to Ticker and Decision Center.

## 3. User Personas
- Portfolio Manager
- Active Investor
- Research Analyst (Future)

## 4. Business Outcomes
- Identify promising candidates.
- Understand candidate evolution.
- Understand why candidates change.
- Know when further investigation is required.
- Know when a candidate is ready for decision review.

## 5. User Scenarios
- Morning Watchlist Review
- Candidate Review
- Promotion Review
- Demotion Review
- Transition to Ticker
- Transition to Decision Center
- Archive Review

## 6. UX Principles
- Observation Before Decision
- Trend Before Snapshot
- Explain Every Transition
- Backend Owns Lifecycle
- Preserve Context
- Never Execute Trades

## 7. Information Priority
1. Candidate Priority
2. Status Changes
3. Trend
4. Quality Indicators
5. Supporting Evidence
6. History

## 8. Region Specification
- Executive Summary
- Candidate Queue
- Candidate Detail
- Candidate Lifecycle
- Portfolio Relevance
- Market Context
- Navigation Panel

## 9. Widget Specification
Core widgets:
- Candidate Cards
- Lifecycle Timeline
- Trend Indicators
- Supporting Signals
- Blocking Factors
- Portfolio Relevance
- Market Context
- Navigation Actions

## 10. Interaction & Candidate Lifecycle
Journey:
Discover → Observe → Monitor → Promote/Demote → Investigate → Decision Review → Archive

Official Lifecycle:
Discovered → Observed → Strengthening → Ready for Investigation → Decision Candidate → Archived

Only backend changes lifecycle state.

## 11. Implementation Specification

### State Model
INITIAL → LOADING → READY → CANDIDATE_SELECTED → REVIEWING → READY → REFRESHING → READY

### Error States
- NETWORK_ERROR
- API_ERROR
- PARTIAL_DATA
- STALE_DATA
- UNAUTHORIZED

### API Boundary
Consumes backend watchlist APIs only.
No frontend ranking or lifecycle logic.

### Refresh
- Automatic after backend updates.
- Manual refresh supported.
- Preserve selected candidate.

### Accessibility
- Keyboard navigation
- Screen reader support
- WCAG contrast
- Visible focus

### Acceptance Criteria
- Candidate lifecycle visible.
- Promotion/demotion explained.
- Navigation preserves context.
- No business logic in frontend.
- Responsive and synchronized.

## 12. Architectural Constraints

### SHALL
- Present backend candidates.
- Explain lifecycle transitions.
- Preserve observation context.
- Support navigation to Ticker and Decision Center.

### SHALL NOT
- Generate recommendations.
- Modify lifecycle or priority.
- Execute trades.
- Become source of truth.

### MAY
- Filter
- Sort
- Group
- Format
- Persist UI preferences

### Domain Ownership
Consumes backend Watchlist, Decision, Portfolio, Market Intelligence and Investability domains.
Owns presentation state only.

## Freeze Decision
Approved as the baseline implementation specification for the Watchlist Workspace. Reference for wireframes, prototype, frontend implementation and QA.
