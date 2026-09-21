# PHASE_7_FRONTEND_TECHNICAL_ARCHITECTURE_v1.1_IMPLEMENTATION_READY.md

# Phase 7 — Frontend Technical Architecture

## Document Status

| Item | Value |
|---|---|
| Version | v1.1 |
| Status | IMPLEMENTATION READY |
| Previous Document | PHASE_7_FRONTEND_TECHNICAL_ARCHITECTURE_v1.0.md |
| Previous Status | Outline only |
| Authority | Derived from Phase 3 Domain Architecture, Phase 4 UX Blueprint, Phase 6 Design System |

---

# 1. Purpose

This document defines the technical implementation architecture for the frontend application.

It resolves the missing decisions from the previous Phase 7 document:

- framework
- repository structure
- routing
- state ownership
- API architecture
- DTO mapping
- styling strategy
- testing strategy
- quality gates

---

# 2. Architecture Principles

The frontend follows:

```
Backend computes
        |
        v
Frontend composes
        |
        v
User interaction
```

Frontend MUST NOT:

- calculate scores
- rank securities
- generate recommendations
- calculate portfolio metrics
- modify backend lifecycle state

---

# 3. Technology Stack

## Framework

Decision:

```
React + TypeScript
```

Reason:

- complex analytical interfaces
- strong typing
- reusable component architecture
- suitable ecosystem

---

## Build Tool

Decision:

```
Vite
```

Reason:

- fast development
- modern build pipeline
- simple deployment model

---

## Application Type

Decision:

```
Single Page Application (SPA)
```

Reason:

The system is an authenticated analytical workspace.

Primary requirements:

- browser state
- deep linking
- workspace navigation
- persistent context

---

# 4. Repository Structure

Frontend location:

```
frontend/
```

Structure:

```
frontend/

src/

├── app/
│   ├── router/
│   ├── providers/
│   └── shell/

├── domains/

│   ├── decision/
│   ├── portfolio/
│   ├── watchlist/
│   ├── ticker/
│   ├── market/
│   ├── search/
│   └── settings/

├── design-system/

│   ├── tokens/
│   ├── components/
│   └── charts/

├── api/

├── models/

├── state/

├── hooks/

├── utils/

└── tests/
```

---

# 5. Domain Dependency Rules

Implementation follows:

```
FOUND
 |
REF
 |
+-------------+
|             |
MI            INV
|             |
+------+------+
       |
      DEC
       |
      UI
       |
      UX
```

Domain ownership is preserved.

---

# 6. Routing Architecture

Library:

```
React Router
```

Routes:

```
/
/settings
/search

/market
/market/index/:index
/market/sector/:sector

/watchlist
/watchlist/:group

/ticker/:symbol

/decision
/decision/:symbol

/portfolio
/portfolio/:symbol
```

URL rules:

- resource identifiers stay in path
- query parameters are presentation only
- canonical URLs required

---

# 7. State Architecture

The frontend implements six state layers.

```
1. Application State

2. Workspace State

3. Page State

4. Component State

5. Overlay State

6. Server State
```

Ownership:

| State | Owner |
|-|-|
| Authentication | Application |
| Theme | Application |
| Workspace | Router |
| Filters | Page |
| Modal/Dialog | Component |
| API Cache | Server State |

---

# 8. API Architecture

Pattern:

```
Component

    |

View Model

    |

Domain Adapter

    |

Repository

    |

API Client

    |

Backend API
```

Example:

```
DecisionRepository

getRecommendation()

submitDecisionResponse()
```

---

# 9. DTO Mapping

Backend DTOs never directly enter UI components.

Flow:

```
Backend DTO

↓

Mapper

↓

Domain Model

↓

View Model

↓

Component
```

Purpose:

- isolate backend changes
- preserve frontend ownership
- avoid business logic leakage

---

# 10. Design System Implementation

Implementation follows Phase 6.

Structure:

```
design-system/

tokens/

components/

charts/

accessibility/
```

Token hierarchy:

```
Core Tokens

↓

Semantic Tokens

↓

Component Tokens
```

Rules:

Forbidden:

- hardcoded HEX
- arbitrary spacing
- duplicate components

---

# 11. Styling Architecture

Decision:

```
CSS Variables + CSS Modules
```

Reasons:

- token compatibility
- component isolation
- theme support

---

# 12. Visualization Strategy

Decision:

```
Apache ECharts
```

Supports:

- financial charts
- heatmaps
- large analytical datasets
- responsive visualization

---

# 13. Table Strategy

Decision:

```
TanStack Table
```

Requirements:

- sorting
- filtering
- pagination
- accessibility
- responsive adaptation

---

# 14. Form Strategy

Decision:

```
React Hook Form

+

Zod Validation
```

Used for:

- settings
- user preferences
- future write flows

---

# 15. Authentication Architecture

Frontend responsibility:

```
Auth Provider

Session Context

Route Guard

Permission Handling
```

Backend remains authority.

Frontend never determines business permission.

---

# 16. Error Architecture

Global:

```
Error Boundary
```

API mapping:

| Code | Handling |
|-|-|
|400|Validation error|
|401|Authentication recovery|
|403|Access denied|
|404|Resource missing|
|429|Rate limit|
|500|Retry/support|

---

# 17. Testing Strategy

Stack:

```
Vitest

React Testing Library

Playwright

axe-core
```

Testing layers:

## Unit

- components
- hooks
- adapters

## Integration

- routes
- state
- API integration

## End-to-End

Critical user journeys:

- login
- navigation
- search
- workspace transitions

---

# 18. Quality Gates

Required before merge:

```
npm run lint

npm run typecheck

npm test

npm run build

npm run e2e
```

---

# 19. Performance Requirements

Must satisfy:

- workspace switch <300ms excluding network
- search opening <100ms
- preserve browser history
- avoid unnecessary rerender

---

# 20. Phase 7 Completion Criteria

Phase 7 is complete when:

✓ framework selected

✓ repository structure defined

✓ routing defined

✓ state ownership defined

✓ API pattern defined

✓ design system integration defined

✓ testing defined

✓ quality gates defined

---

# END OF DOCUMENT
