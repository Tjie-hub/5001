# TICKER_DESIGN_SPEC_v1.0

Status: FROZEN

## 1. Executive Summary
Ticker Workspace is the investigation workspace for a single instrument. It provides comprehensive, explainable analysis to support investment decisions without generating recommendations or executing trades.

## 2. Design Goals
- Understand instrument quality within 30 seconds.
- Explain business quality and investability.
- Surface all relevant risks.
- Show portfolio context.
- Preserve investigation context across workspaces.

## 3. User Personas
- Portfolio Manager
- Active Investor
- Research Analyst (Future)

## 4. Business Outcomes
- Understand why an instrument is attractive or unattractive.
- Understand key risks.
- Assess business quality.
- Assess investability.
- Understand portfolio impact.
- Return to Decision Center with sufficient context.

## 5. User Scenarios
- Review Candidate
- Validate Recommendation
- Compare with Existing Holding
- Risk Investigation
- Historical Review
- Return to Decision

## 6. UX Principles
- Investigate Before Decide
- Business Before Market
- Risk Before Opportunity
- Trend Before Snapshot
- Explain Every Assessment
- Preserve Context
- No Hidden Risk

## 7. Information Priority
1. Instrument Summary
2. Risk Assessment
3. Fundamental Assessment
4. Investability Assessment
5. Portfolio Context
6. Historical Evolution
7. Supporting Analytics

## 8. Region Specification
- Instrument Summary
- Fundamental Assessment
- Investability & Risk
- Historical Evolution
- Portfolio Context
- Market Context
- Investigation Navigation

## 9. Widget Specification
Core widgets:
- Instrument Identity
- Executive Summary
- Fundamental Metrics
- Investability Metrics
- Risk Flags
- Historical Timeline
- Portfolio Context
- Market Context
- Navigation Actions

## 10. Interaction & Investigation Experience
Journey:
Open Instrument → Review Business Quality → Review Market Quality → Review Risk → Review Historical Evolution → Review Portfolio Context → Return to Decision

Ticker investigates only. It never recommends or executes.

## 11. Implementation Specification

### State Model
INITIAL → LOADING → READY → INSTRUMENT_SELECTED → INVESTIGATING → READY → REFRESHING → READY

### Error States
- NETWORK_ERROR
- API_ERROR
- PARTIAL_DATA
- STALE_DATA
- UNAUTHORIZED

### API Boundary
Consumes backend APIs only.
No frontend business calculations.

### Refresh
- Automatic after backend updates.
- Manual refresh supported.
- Preserve selected instrument.

### Accessibility
- Keyboard navigation
- Screen reader support
- WCAG contrast
- Visible focus

### Acceptance Criteria
- Investigation workflow complete.
- Risk always visible.
- Context preserved across workspaces.
- No business logic in frontend.
- Responsive and synchronized.

## 12. Architectural Constraints

### SHALL
- Present backend analysis.
- Explain business quality.
- Explain investability.
- Display portfolio and market context.
- Support navigation to Watchlist, Decision Center and Portfolio.

### SHALL NOT
- Generate recommendations.
- Execute trades.
- Modify rankings or scores.
- Become source of truth.

### MAY
- Filter
- Sort
- Group
- Format
- Persist UI preferences

### Domain Ownership
Consumes Instrument, Fundamental, Investability, Portfolio, Decision Engine and Market Intelligence domains.
Owns presentation state only.

## Freeze Validation
Business boundary, API boundary, UX consistency, architecture, state model and constraints reviewed and approved.

## Freeze Decision
Approved as the baseline implementation specification for the Ticker Workspace and serves as the reference for wireframes, prototype, frontend implementation and QA.
