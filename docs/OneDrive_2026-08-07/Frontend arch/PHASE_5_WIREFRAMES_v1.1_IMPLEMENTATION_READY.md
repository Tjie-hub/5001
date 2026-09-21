# PHASE_5_WIREFRAMES_v1.1_IMPLEMENTATION_READY.md

# Phase 5 — Frontend Wireframes Specification

## Document Status

| Item | Value |
|---|---|
| Version | v1.1 |
| Status | IMPLEMENTATION READY |
| Previous Document | PHASE_5_WIREFRAMES_v1.0.md |
| Authority | Derived from PHASE_4_UX_BLUEPRINT_v1.1 and PHASE_6_DESIGN_SYSTEM_v1.0 |

---

# 1. Purpose

Phase 5 defines the structural wireframe contract between UX architecture and frontend implementation.

It defines:

- screen composition
- information hierarchy
- component placement
- interaction regions
- responsive behavior
- state coverage

It does not define visual styling. Styling belongs to Phase 6 Design System.

---

# 2. Global Application Shell

All workspaces inherit the same shell.

```
+------------------------------------------------+
| Global Header                                  |
+----------------+-------------------------------+
| Global Sidebar | Active Workspace              |
|                |                               |
|                |                               |
+----------------+-------------------------------+
| Status Footer                                  |
+------------------------------------------------+
```

---

# 3. Standard Workspace Layout

All workspaces follow:

```
Header
  |
Executive Summary
  |
Primary Visualization
  |
Secondary Visualization
  |
Analytical Table
  |
Supporting Information
```

---

# 4. Decision Center

Routes:

```
/decision
/decision/:symbol
```

Structure:

```
+----------------------+----------------------+
| Recommendation Queue | Recommendation Detail|
+----------------------+----------------------+
| Evidence / Signals / Risk                  |
+--------------------------------------------+
| Portfolio Context                          |
+--------------------------------------------+
| Market Context                             |
+--------------------------------------------+
| Action Panel                               |
+--------------------------------------------+
| Activity Timeline                          |
+--------------------------------------------+
```

Only Decision Center owns actions:

- Buy
- Scale In
- Hold
- Rotate
- Reduce
- Exit
- No Action

---

# 5. Watchlist

Routes:

```
/watchlist
/watchlist/:group
```

Structure:

```
Header

Summary Metrics

Candidate List + Candidate Detail

Activity Timeline
```

Frontend displays lifecycle state.
Frontend does not modify lifecycle.

---

# 6. Market

Routes:

```
/market
/market/index/:index
/market/sector/:sector
```

Structure:

```
Market Summary

Index Overview

Breadth Visualization

Sector Heatmap

Analytical Table

Events Calendar
```

---

# 7. Ticker

Route:

```
/ticker/:symbol
```

Structure:

```
Security Header

Price Summary

Tabs:
- Overview
- Technical
- Fundamentals
- Ownership
- Flow
- Financial Statements
- Corporate Actions
- News
- Compare

Charts

Analytical Data
```

---

# 8. Portfolio

Routes:

```
/portfolio
/portfolio/:symbol
```

Structure:

```
Portfolio Summary

Allocation View

Performance Chart

Holdings Table

Risk Context
```

Frontend never calculates portfolio metrics.

---

# 9. Search

Route:

```
/search
```

Structure:

```
Search Input

Filters

Search Results Table

Destination Preview
```

Result contract:

- Resource Type
- Display Name
- Canonical Identifier
- Destination Workspace
- Canonical URL

---

# 10. Settings

Route:

```
/settings
```

Structure:

```
Profile

Preferences

Notifications

Security

Save Action
```

---

# 11. Responsive Rules

Desktop:

- persistent sidebar
- multi-column layout

Tablet:

- collapsible sidebar
- reduced columns

Mobile:

- drawer navigation
- single column

Business workflow remains identical.

---

# 12. State Coverage

Every screen supports:

- Default
- Loading
- Empty
- Success
- Warning
- Error
- Disabled

---

# 13. Accessibility

Every page requires:

- one H1
- semantic landmarks
- keyboard navigation
- focus restoration
- screen reader labels

---

# 14. Completion Criteria

Phase 5 complete when:

- all screens mapped
- layouts defined
- components assigned
- responsive behavior defined
- accessibility structure defined

