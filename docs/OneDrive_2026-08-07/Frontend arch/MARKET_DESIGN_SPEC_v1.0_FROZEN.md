# MARKET_DESIGN_SPEC_v1.0

Status: FROZEN

## 1. Executive Summary
Market Workspace is the shared market context workspace for the Decision Operating System. It explains the market environment used consistently across all workspaces without generating investment recommendations.

## 2. Design Goals
- Understand market condition within 30 seconds.
- Explain market regime.
- Explain sector rotation.
- Explain market breadth and participation.
- Provide consistent market context.
- Show portfolio impact from market conditions.

## 3. User Personas
- Portfolio Manager
- Active Investor
- Research Analyst (Future)

## 4. Business Outcomes
- Understand the current market regime.
- Understand market participation.
- Understand sector rotation.
- Understand portfolio exposure to market conditions.
- Navigate back to decision workflows with shared context.

## 5. User Scenarios
- Morning Market Review
- Regime Review
- Breadth Review
- Sector Rotation Review
- Historical Review
- Portfolio Context Review

## 6. UX Principles
- Context Before Decision
- Macro Before Instrument
- Trend Before Snapshot
- Explain Every Regime
- Shared Market Context
- No Prediction
- No Recommendation Generation

## 7. Information Priority
1. Executive Market Summary
2. Market Regime
3. Market Breadth
4. Sector Rotation
5. Historical Evolution
6. Portfolio Impact

## 8. Region Specification
- Executive Market Summary
- Market Regime Analysis
- Market Breadth & Participation
- Sector Rotation
- Historical Market Evolution
- Portfolio Impact
- Workspace Navigation

## 9. Widget Specification
Core widgets:
- Market Health
- Regime Classification
- Breadth Indicators
- Sector Ranking
- Rotation Analysis
- Historical Timeline
- Portfolio Impact
- Snapshot Metadata
- Navigation Actions

## 10. Interaction & Market Context Experience
Journey:
Review Executive Summary → Review Regime → Review Breadth → Review Sector Rotation → Review Historical Evolution → Review Portfolio Impact → Continue Workflow

Market provides context only.

## 11. Implementation Specification

### State Model
INITIAL → LOADING → READY → SNAPSHOT_SELECTED → REVIEWING → READY → REFRESHING → READY

### Error States
- NETWORK_ERROR
- API_ERROR
- PARTIAL_DATA
- STALE_DATA
- UNAUTHORIZED

### API Boundary
Consumes backend market APIs only.
No frontend market calculations.

### Refresh
- Automatic after backend snapshot updates.
- Manual refresh supported.
- Preserve active snapshot.

### Accessibility
- Keyboard navigation
- Screen reader support
- WCAG contrast
- Visible focus

### Acceptance Criteria
- Regime, breadth, rotation and history review complete.
- Shared context preserved.
- No business logic in frontend.
- Responsive and synchronized.

## 12. Architectural Constraints

### SHALL
- Present backend market analysis.
- Explain regime, breadth and rotation.
- Present portfolio impact context.
- Support navigation to Decision Center, Watchlist, Ticker and Portfolio.

### SHALL NOT
- Generate recommendations.
- Generate trading signals.
- Modify market classifications.
- Become source of truth.

### MAY
- Filter
- Sort
- Group
- Format
- Persist UI preferences

### Domain Ownership
Consumes Market Intelligence, Sector Analysis and Portfolio context.
Owns presentation state only.

## Freeze Validation
Business boundary, API boundary, UX consistency, architecture, state model, accessibility, performance and constraints reviewed and approved.

## Freeze Decision
Approved as the baseline implementation specification for the Market Workspace. Reference for wireframes, prototype, frontend implementation and QA.
