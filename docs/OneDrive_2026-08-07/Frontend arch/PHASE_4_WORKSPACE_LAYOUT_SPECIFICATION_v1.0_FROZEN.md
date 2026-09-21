PHASE_4_WORKSPACE_LAYOUT_SPECIFICATION_v1.0
Status: FROZEN
Phase: 4.2 – Stage 3 (Workspace Layout Specification)
Objective
Define the logical layout of each workspace before wireframes. This specification fixes information hierarchy, workspace regions, interaction priorities and reusable layout rules without prescribing visual design.
Principles
- Layout follows business decisions, not aesthetics.
- Backend computes; frontend composes.
- Critical information is always visible.
- Shared regions should be reused across workspaces.
Workspace Regions
Standard regions:
1. Header
2. Executive Summary
3. Recommendation Queue
4. Recommendation Detail
5. Portfolio Context
6. Market Context
7. Action Panel
8. Activity Timeline
Information Hierarchy
Priority order:
Critical → High → Medium → Supporting.
Recommendations and required actions always appear before supporting analytics.
Widget Placement Rules
- Recommendation Queue: left/navigation region.
- Recommendation Detail: primary focus region.
- Action Panel: persistent action region.
- Context panels: supporting regions.
- Timeline: lowest visual priority.
Responsive Rules
Desktop: multi-column.
Tablet: stacked primary + secondary.
Mobile: single-column with persistent primary action.
Layout Constraints
- Recommendation Detail must remain visible during review.
- Action Panel must stay accessible.
- Portfolio Context cannot require navigation to another workspace during decision review.
Reusable Regions
- Executive Summary Region
- Recommendation Region
- Portfolio Context Region
- Market Context Region
- Action Region
- Timeline Region
Deliverables
Layout specifications will be produced for:
- Decision Center
- Portfolio
- Watchlist
- Ticker
- Market
- Search
- Settings
Exit Criteria
Workspace layout architecture is frozen. Wireframes and prototypes must conform to this specification. Architectural changes require ADR approval.