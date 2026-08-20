# ADR-003 — Server State Architecture

| Item | Value |
|---|---|
| ADR ID | FRONTEND-ADR-003 |
| Title | Server State Architecture — library selection and integration contract |
| Status | **APPROVED — 2026-08-20, by Owner.** See §21 Ratification Note: §15.1's "greenfield, no migration cost" premise is now stale (Decision Center and Settings exist) and is corrected there, not silently — the substantive decision in §2–§14 and §16 is unaffected and is what was approved. |
| Date | 2026-08-07 |
| Depends On | `FRONTEND_ARCHITECTURE_RECONCILIATION_ADR_001.md` (APPROVED) |
| Authority | Phase 4 UX Blueprint v1.1 (FROZEN) · Phase 6 Design System v1.0 (FROZEN) · Phase 7 Technical Architecture v1.1 · ADR-001 §3 |
| Closes | Blocker **U-5** · unblocks Phase 9 Workstream B tasks **B2**, **B6** and Workstream E task **E4** |
| Freeze effect | On approval, the Server State architecture defined here is **FROZEN**. Subsequent change requires a superseding ADR |

---

# 1. Context

ADR-001 §3 established that the frontend implements **seven** state layers — the six frozen Phase 4
P4-12 layers plus **Server State** — and that Server State does not replace Resource State. It did
not select an implementation.

Phase 7 v1.1 §7 names "Server State" as a layer and assigns it ownership of the API cache, but
selects no library. Phase 7 §8 defines the data-flow chain and Phase 7 §9 the DTO isolation rule,
both of which any candidate must preserve.

This is the last open architecture decision that blocks the Application Shell. Workstream A can
proceed without it; Workstream B cannot complete without it.

## 1.1 Constraints the decision must satisfy

| # | Constraint | Source |
|---|---|---|
| C-1 | React + TypeScript + Vite, **SPA, no SSR** | ADR-001 §2 · Phase 7 v1.1 §3 |
| C-2 | No global state library is selected; introducing one is a new architectural commitment | Phase 7 v1.1 — silent by omission |
| C-3 | Data flows Component → View Model → Domain Adapter → Repository → API Client → Backend | Phase 7 v1.1 §8 |
| C-4 | Backend DTOs never enter UI components | Phase 7 v1.1 §9 |
| C-5 | Resource State is owned by URL/Router; Server State never appears in a URL | ADR-001 §3 |
| C-6 | Background refresh must not reset navigation, scroll, workspace or focus | Phase 4 P4-14 §9 |
| C-7 | Incremental loading must preserve scroll position, selected resource, filters and sorting | Phase 4 P4-14 §8 |
| C-8 | Four loading categories: Initial · Resource · Incremental · Background | Phase 4 P4-14 §5 |
| C-9 | Automatic destructive retries are prohibited; Retry / Cancel / Return must be offered | Phase 4 P4-14 §12 |
| C-10 | Four connectivity states: Connected · Reconnecting · Offline · Maintenance | Phase 4 P4-14 §13 |
| C-11 | Each browser tab maintains an independent navigation and data context | Phase 4 P4-12 §16 |
| C-12 | Recommendations are recalculated on events; refresh is event-driven by preference | DEC-006 |
| C-13 | Workspace switch < 300 ms excluding network; search open < 100 ms | Phase 7 v1.1 §19 |
| C-14 | The frontend never calculates scores, ranks, recommendations or portfolio metrics | FOUND-006 |
| C-15 | Testable under Vitest + React Testing Library; E2E under Playwright | Phase 7 v1.1 §17 |
| C-16 | Five frozen error states per workspace: NETWORK_ERROR · API_ERROR · PARTIAL_DATA · STALE_DATA · UNAUTHORIZED | The seven workspace design specs, §11 |

---

# 2. Decision

## Selected: **TanStack Query v5** (`@tanstack/react-query`)

One library. No secondary server-state mechanism is permitted anywhere in the application.

TanStack Query owns **Server State only**: API response caching, deduplication, staleness,
background revalidation, retry, and mutation lifecycle. It owns **no other layer**. It does not
hold Application, Workspace, Resource, Page, Component or Overlay State.

---

# 3. Alternatives Considered

## 3.1 Evaluation matrix

Legend: ● full · ◐ partial / requires custom work · ○ absent or requires building from scratch

| Criterion | TanStack Query | RTK Query | SWR | fetch + custom cache |
|---|---|---|---|---|
| React + Vite compatibility (C-1) | ● native, zero config | ● works | ● native | ● trivially |
| **No SSR requirement** | ● SSR optional | ● SSR optional | ● SSR optional | ● n/a |
| Cache invalidation | ● hierarchical key-prefix invalidation | ● tag-based | ◐ key-match / global mutate | ○ build it |
| Request deduplication | ● automatic, in-flight | ● automatic | ● automatic | ○ build it |
| Optimistic updates | ● `onMutate`/`onError`/`onSettled` with rollback context | ● `onQueryStarted` with `patchResult.undo()` | ◐ `optimisticData` + `rollbackOnError`, thinner | ○ build it |
| Retries + backoff | ● predicate fn, exponential + jitter | ◐ `retry` wrapper, less granular | ◐ `onErrorRetry`, manual | ○ build it |
| Stale data handling | ● `staleTime` per query | ◐ `keepUnusedDataFor` only (gc, not staleness) | ◐ `dedupingInterval` + revalidate flags | ○ build it |
| Background refresh (C-6) | ● focus/reconnect/interval, `isFetching` distinct from `isPending` | ● polling + refetchOn* | ● focus/reconnect | ○ build it |
| Pagination (C-7) | ● `placeholderData: keepPreviousData` | ◐ `merge` on endpoint | ◐ manual | ○ build it |
| Infinite scrolling | ● `useInfiniteQuery` + `getNextPageParam` | ◐ manual merge | ◐ `useSWRInfinite` | ○ build it |
| Developer experience | ● mature devtools, large ecosystem | ◐ devtools via Redux DevTools | ◐ minimal devtools | ○ none |
| Bundle size (gzip, approx.) | ~13 kB | ~14 kB **+ ~12 kB** required Redux Toolkit + react-redux | **~5 kB** | ~0 kB library, high code cost |
| Testing (C-15) | ● `QueryClientProvider` wrapper, `retry:false`; MSW-friendly | ◐ requires a store per test | ● simple provider | ◐ testing your own cache |
| **Alignment with Phase 7 §8 layering (C-3)** | ● `queryFn` calls the Repository; library never sees HTTP | ○ **endpoint definitions duplicate the Repository layer** | ● fetcher calls the Repository | ● by construction |
| **Alignment with ADR-001 §3 (C-2, C-5)** | ● owns Server State only; no pull toward other layers | ○ **imports Redux, creating a rival home for Workspace/Page State** | ● owns Server State only | ◐ undefined by default |
| Query cancellation | ● `AbortSignal` wired | ● abort supported | ◐ limited | ○ build it |

## 3.2 RTK Query — rejected

**Primary reason: it violates C-2 and C-3.**

RTK Query cannot be adopted without adopting Redux Toolkit and react-redux. Phase 7 v1.1 selects
**no** global state library, and ADR-001 §3 already assigns every non-server layer a specific,
non-Redux owner — Application State to providers, Workspace State to the workspace, Resource State
to the URL/Router, Page and Component State to local React state. Introducing a Redux store to
obtain server-state caching would create a second, unassigned home for state that already has an
owner. In practice this reliably drifts: workspace filters and page state migrate into the store
"because it is there," and the seven-layer model that ADR-001 was written to protect erodes.

**Secondary reason: structural duplication.** RTK Query's model is a centralized API slice of
endpoint definitions. Phase 7 v1.1 §8 already mandates a Repository layer that performs exactly
that role. Adopting RTK Query means either writing endpoints twice or collapsing the Repository
layer into RTK Query — the latter deleting a frozen layer and taking the DTO-isolation boundary
(C-4) with it.

Also relevant: it carries the largest total bundle cost of the four options, and its staleness
model is weaker — `keepUnusedDataFor` controls garbage collection, not staleness, so the
per-domain freshness policy in §7 would have to be simulated with polling intervals.

## 3.3 SWR — rejected

**Primary reason: the write path.**

SWR is excellent and the smallest option at roughly 5 kB. For a read-only application it would be
the correct choice. This application does not stay read-only: Phase 7 v1.1 §8 names
`submitDecisionResponse()`; the Decision Center spec requires recording recommendation responses;
Settings requires save; empty states offer Create Watchlist and Import Portfolio.

`useSWRMutation` is materially thinner than `useMutation`. It lacks a first-class mutation cache,
per-mutation retry policy, and the `onMutate` → context → `onError` rollback contract that §9 of
this ADR makes mandatory for optimistic updates. Implementing deterministic rollback for the
Decision Center accept/reject flow on top of SWR means hand-rolling snapshot and restore logic —
which is the custom-cache option wearing a smaller library.

**Secondary reasons.** `useSWRInfinite` is workable but less structured than `useInfiniteQuery` for
the analytical tables that Phase 6 P6-35 requires. Devtools are weaker, which matters for a
seven-layer state model where "which layer is this value in?" is the recurring debugging question.

The ~8 kB saved against TanStack Query is not material next to Apache ECharts and TanStack Table.

## 3.4 Native fetch + custom cache — rejected

**Rejected on risk, not on capability.**

Selecting this means building and owning: in-flight deduplication, per-key staleness, garbage
collection, exponential backoff with jitter, focus and reconnect revalidation, request
cancellation, pagination continuity, infinite-query accumulation, optimistic rollback, and
devtools. Every one is a correctness surface, and several are subtly hard — deduplication under
concurrent key changes, and rollback ordering under overlapping mutations, in particular.

It also reintroduces the failure mode ADR-001 exists to correct. A hand-rolled cache becomes
undocumented architecture: its behavior lives only in its implementation, no ADR governs it, and
Phase 9's AC-5 architecture-compliance check has nothing to verify against.

The only argument in its favor is bundle size. Roughly 13 kB gzipped is not a defensible reason to
hand-write a cache for a seven-workspace analytical application.

## 3.5 Why TanStack Query wins

1. **It slots into the frozen chain without deforming it.** `queryFn` calls the Repository. The
   library never sees HTTP, never sees a DTO, and never learns a domain rule. Phase 7 §8 and §9
   survive intact — this is the decisive structural point.
2. **It owns exactly one layer.** No store, no provider hierarchy competing with Application or
   Workspace State, no gravitational pull on Page State. ADR-001 §3 stays enforceable.
3. **Query keys are hierarchical arrays**, which map onto Resource State cleanly: the key is
   *derived from* the route, so Resource and Server State stay correspondent without cache ever
   entering a URL (C-5).
4. **`isPending` and `isFetching` are distinct.** This is the exact mechanism that satisfies C-6 —
   background refetch never unmounts and never triggers a skeleton. See §11.
5. **`placeholderData: keepPreviousData`** directly serves C-7 and C-13: the previous page's data
   remains rendered while the next resolves, so scroll, selection and sort survive and the
   workspace-switch budget is met without a network round trip.
6. **Per-query `staleTime`** allows the per-domain freshness policy in §7, which this product
   genuinely needs — Market moves on an EOD cadence, Watchlist intraday, fundamentals quarterly.
7. **`retry` as a predicate** expresses C-9 precisely: retry 408/429/5xx, never 4xx-client, never
   mutations.
8. **Per-tab cache by default** matches C-11 exactly, with no work and no cross-tab sync.
9. **Same vendor and idiom as TanStack Table**, already selected in Phase 7 v1.1 §13. One mental
   model for data and for the tables that display it.
10. **Testing story fits C-15** — a `QueryClientProvider` wrapper with `retry: false` and a fresh
    client per test; deterministic under Vitest.

---

# 4. Canonical Architecture

```
Component
    ↓
ViewModel
    ↓
Domain Adapter
    ↓
Repository
    ↓
Server State          ← TanStack Query
    ↓
API Client
    ↓
Backend
```

## 4.1 Layer responsibilities

| Layer | Owns | Must never |
|---|---|---|
| **Component** | Rendering, user interaction, presentation-only local state | Fetch directly · read a DTO · read a raw query result · contain a domain rule |
| **ViewModel** | Formatting, labels, derived display values, mapping domain state → the frozen error/loading states | Compute a business value (C-14) · call the API · own cache policy |
| **Domain Adapter** | Domain semantics, composing multiple read models, exposing the hook surface a workspace consumes | Contain HTTP · contain presentation concerns · bypass the Repository |
| **Repository** | Query and mutation definitions, query-key factories, cache policy declaration, DTO → Domain Model mapping | Return a DTO · hold React state · know about components |
| **Server State** | Cache storage, deduplication, staleness, background revalidation, retry, mutation lifecycle, invalidation | Contain a domain rule · appear in a URL · be treated as a source of truth for identity |
| **API Client** | Transport, base URL, headers, auth attachment, envelope unwrapping, transport → typed error normalization | Cache · retry (retry is Server State's) · interpret domain meaning |
| **Backend** | All business logic and persistence | — |

## 4.2 Placement of Server State

Server State sits **below** the Repository and **above** the API Client. It is invoked *by* the
Repository's query definitions; it does not wrap them from above. This ordering is what keeps the
library ignorant of HTTP and of domain semantics simultaneously.

---

# 5. State Ownership — seven layers

Confirms and extends ADR-001 §3. Normative.

| # | Layer | Responsibility | Owner | Lifetime | Persisted in | Restored on refresh |
|---|---|---|---|---|---|---|
| 1 | **Application** | Authentication, theme, environment, feature flags, snapshot version, time zone | Application providers | Session | Application | Yes |
| 2 | **Workspace** | Selected sector/index, active tab, compare mode, timeframe, benchmark, grouping, sort order, **workspace filters** | Workspace | Workspace lifetime | Workspace + URL where addressable | Yes, where addressable |
| 3 | **Resource** | The active analytical object — `:symbol`, `:index`, `:sector`, `:group` | **URL / Router** | Resource lifetime | **URL** | Yes |
| 4 | **Page** | Pagination position, expanded panels, local sorting, accordion state | Page | Page lifetime | Not persisted | No |
| 5 | **Component** | Dropdown open, input value, selected option, hover, focus | Component | Component lifetime | Not persisted | No |
| 6 | **Overlay** | Modal, drawer, tooltip, context menu, toast | Component | Temporary | Never | **Never** |
| 7 | **Server** | API responses, cache entries, fetch status, staleness, invalidation | **TanStack Query** | Cache policy per §7 | In-memory only | No — refetched |

## 5.1 The Resource / Server distinction

The two are orthogonal and must not be collapsed.

| | Resource State | Server State |
|---|---|---|
| Answers | *Which object is in view?* | *What did the backend return for it?* |
| Owner | URL / Router | TanStack Query |
| Addressable | Yes — it **is** the URL | No |
| Bookmarkable | Yes | No |
| Shareable | Yes | No |
| Survives refresh | Yes | No — refetched |
| Example | `/ticker/BBCA` | the ownership payload for BBCA |

**Resource State is an input to the query key. It is never an output of the cache.**

Collapsing them breaks three frozen guarantees: RM-04 / RU-04 (same URL → same state), P4-12 §14
(context restoration begins at Resource), and Appendix D (Active Resource owned by URL).

---

# 6. Query Key Strategy

## 6.1 Canonical shape

```
[ domain, readModel, resourceIdentifier?, params? ]
```

| Position | Contents | Source |
|---|---|---|
| 1 · `domain` | Lowercase domain name matching the Domain Model: `ref` · `market` · `investability` · `ticker` · `watchlist` · `portfolio` · `decision` · `user` · `ops` | Domain Model §5 |
| 2 · `readModel` | The specific read model within that domain | Repository |
| 3 · `resourceIdentifier` | The Resource State value — **must originate from the URL**, never from component state | Router |
| 4 · `params` | A stable, serializable object of presentation parameters that change the response — date, timeframe, page, filters | Workspace / Page State |

## 6.2 Examples

```
['watchlist', 'current']
['watchlist', 'byDate', '2026-08-07']
['watchlist', 'group', 'default']

['market', 'overview', null, { date: '2026-08-07' }]
['market', 'sector', 'BANKING', { date: '2026-08-07' }]
['market', 'index', 'IDX30']

['ticker', 'overview', 'BBCA']
['ticker', 'ownership', 'BBCA', { date: '2026-08-07' }]
['ticker', 'flow', 'BBCA', { timeframe: '1M' }]

['portfolio', 'holdings']
['portfolio', 'position', 'BBCA']

['decision', 'queue']
['decision', 'recommendation', 'BBCA']

['user', 'preferences']
['ops', 'health']
```

## 6.3 Rules

1. Every key is produced by a **key factory** colocated with its Repository. Inline literal keys
   are prohibited.
2. Position 1 must be a Domain Model domain name. This makes domain-scoped invalidation a prefix
   match and makes cache inspection map onto the architecture.
3. Position 3 must be read from route params. A component may not supply a resource identifier
   from local state — that would place Resource State outside the URL, violating C-5.
4. Position 4 must be **stable and serializable**. No functions, no class instances, no `Date`
   objects — ISO strings only. Key order must be normalized so that logically equal params produce
   an identical key.
5. Presentation state that does **not** change the response — expanded panels, hover, active
   overlay, column visibility — must never appear in a key.
6. Keys are typed. `as const` tuples with a discriminated key-factory return type.

---

# 7. Cache Lifetime Strategy

Freshness is declared **per domain**, driven by the real cadence of the underlying data. Declared
in the Repository, never at the call site.

| Domain | `staleTime` | `gcTime` | Refetch on focus | Refetch on reconnect | Rationale |
|---|---|---|---|---|---|
| `ref` — instruments, sector taxonomy | 24 h | 24 h | No | Yes | Reference data; changes on corporate action |
| `market` — regime, breadth, sectors | 5 min | 30 min | Yes | Yes | EOD cadence; intraday drift is slow |
| `investability` — INV assessments | 1 h | 2 h | No | Yes | Recomputed on fundamentals, not intraday |
| `ticker` — fundamentals, financials, corporate actions | 1 h | 2 h | No | Yes | Quarterly cadence |
| `ticker` — technical, flow, price | 60 s | 10 min | Yes | Yes | Intraday |
| `watchlist` — candidates, lifecycle | 60 s | 10 min | Yes | Yes | Intraday candidate movement |
| `portfolio` — holdings, allocation, performance | 30 s | 10 min | Yes | Yes | Position-sensitive |
| `decision` — queue, recommendations | 30 s | 10 min | Yes | Yes | Event-driven per DEC-006 |
| `user` — profile, preferences | `Infinity` until mutated | Session | No | No | User-owned; changes only by mutation |
| `ops` — health, status, scheduler | 15 s | 1 min | Yes | Yes | Operational telemetry |

## 7.1 Rules

- `staleTime` expresses **freshness**; `gcTime` expresses **retention**. They are set independently.
- `gcTime` must always exceed `staleTime`.
- Market-hours awareness (09:00–15:30 WIB, Mon–Fri) **may** shorten intraday `staleTime` and
  **shall** lengthen it outside session hours. Data settled at EOD need not be revalidated every
  five minutes overnight.
- `refetchInterval` polling is **prohibited by default**. DEC-006 makes refresh event-driven;
  polling is permitted only for the `ops` domain.
- Global defaults live in a single `QueryClient` configuration. Per-domain overrides live in the
  Repository. Per-call-site overrides are prohibited.

---

# 8. Mutation Pattern

```
Component
    ↓  intent
ViewModel / Domain Adapter
    ↓
useMutation( Repository.submitX )
    ↓
Repository  →  API Client  →  Backend
    ↓  onSuccess
queryClient.invalidateQueries({ queryKey: [domain, ...] })
    ↓
Affected queries refetch in background
    ↓
Component re-renders with server truth
```

## 8.1 Rules

1. Every mutation is defined in a Repository. Components never call `useMutation` with an inline
   function.
2. Success invalidates by **domain-scoped key prefix**, not by exhaustive enumeration. A decision
   response invalidates `['decision']` and `['portfolio']`, because DEC-006 recalculates on
   portfolio change.
3. `setQueryData` is permitted **only** inside an optimistic update (§9). It is prohibited as a
   substitute for invalidation — writing a computed value into the cache would make the frontend
   the source of truth, violating C-14 and the SHALL NOT in §13.
4. The server response is authoritative. After settle, cache reflects the backend, never the
   optimistic guess.
5. Mutations do not retry. See §10.
6. In-flight mutations expose a disabled state to the component so a duplicate submit is impossible
   — Phase 6 P6-15 requires buttons to prevent duplicate actions while loading.

## 8.2 Current backend reality

The backend exposes **33 read-only GET endpoints and zero writes** (blocker U-3). The mutation
architecture is specified here so that it is settled before the write path exists, but **no
mutation may be implemented until U-3 is resolved**. `submitDecisionResponse()` — named in Phase 7
v1.1 §8 — has no endpoint today.

---

# 9. Optimistic Update Policy

Optimistic updates are **restricted by default**. Permission is granted per operation, not per
library capability.

## 9.1 Permitted

An optimistic update is permitted only when **all four** hold:

1. The user-visible change is a direct echo of the user's own input.
2. The value is **not computed by the backend**.
3. The backend outcome is deterministic — success or a clean, mappable failure.
4. Rollback is complete and observable.

| Operation | Permitted | Note |
|---|---|---|
| Recommendation response — accept / reject / defer | ✅ | DEC-008: the response references a RecommendationID only. The user's own choice, echoed |
| Settings preference toggle | ✅ | User-owned value |
| Watchlist membership add / remove | ✅ | Subject to backend lifecycle authority — see §9.2 |
| UI preference persistence | ✅ | Not server-computed |

## 9.2 Prohibited

| Operation | Reason |
|---|---|
| Any score, rank, confidence, priority or conviction value | FOUND-006 · C-14 — an optimistic write would be the frontend **inventing a backend-computed value** |
| Portfolio health, allocation, diversification, capacity | Portfolio spec §12 SHALL NOT — frontend never calculates these |
| Position sizing, opportunity cost, alpha differential | DEC-004 — owned by Decision Intelligence |
| **Watchlist lifecycle state** | Watchlist spec §10 — "Only backend changes lifecycle state." Membership may be optimistic; *lifecycle* may not |
| Recommendation content, status beyond the user's own response | DEC-007 — lifecycle is backend-owned |

This is the non-obvious rule of this ADR: **optimism is permitted about the user's intent, never
about the system's judgment.**

## 9.3 Mandatory contract

Every optimistic update implements the full three-phase contract:

| Phase | Obligation |
|---|---|
| `onMutate` | Cancel in-flight queries for the affected keys · snapshot current cache · apply the optimistic value · **return the snapshot as context** |
| `onError` | **Restore the snapshot from context** · surface the error through §11 · never leave a partial state |
| `onSettled` | Invalidate affected keys so the cache converges on server truth |

An optimistic update without a rollback path is prohibited. Snapshot-and-restore is not optional.

---

# 10. Retry Policy

Implements C-9 and the frozen error map in Phase 4 P4-13 §17.

## 10.1 Queries

| Condition | Retry | Max | Backoff |
|---|---|---|---|
| Network / transport failure | Yes | 3 | Exponential + jitter, cap 30 s |
| 408 Request Timeout | Yes | 3 | Exponential + jitter |
| 429 Rate Limit | Yes | 2 | Honour `Retry-After` if present, else exponential |
| 500 / 502 / 503 / 504 | Yes | 3 | Exponential + jitter |
| 400 Invalid Request | **No** | — | Deterministic client error |
| 401 Unauthorized | **No** | — | Route to authentication recovery, then return to the original route (P4-06 §11) |
| 403 Forbidden | **No** | — | Access denied |
| 404 Not Found | **No** | — | Resource Not Found |
| Maintenance | **No** | — | Read-only notice (P4-14 §11) |

## 10.2 Mutations

**`retry: false`. Always.**

P4-14 §12 prohibits automatic destructive retries. A failed mutation surfaces **Retry / Cancel /
Return** as explicit user actions. The user retries; the application does not.

## 10.3 Rules

- Retry is configured as a **predicate function** evaluating the typed error, never as a bare count.
- Retry belongs to Server State. The API Client must not retry — double-retry would multiply
  attempts silently.
- Every retry attempt must be cancellable via `AbortSignal` when the query key changes or the
  component unmounts.
- Retry must never block navigation (P4-14 anti-pattern list).

---

# 11. Error Propagation

## 11.1 Chain

```
Backend
    ↓  HTTP status + error envelope
API Client        → normalizes to typed ApiError { code, status, message, retryable }
    ↓
Server State      → surfaces as-is; classifies retryable; does not interpret
    ↓
Repository        → maps ApiError → DomainError
    ↓
Domain Adapter    → maps DomainError → one of the five frozen workspace error states
    ↓
ViewModel         → selects message + recovery actions
    ↓
Component         → renders the Phase 6 P6-31 Error State component
```

## 11.2 Mapping to the frozen workspace error states

Every workspace design spec §11 declares the same five. This is the binding map:

| Condition | Frozen error state |
|---|---|
| Transport failure, offline, DNS, timeout | `NETWORK_ERROR` |
| 400 / 404 / 500 / 502 / 503 / 504 / malformed response | `API_ERROR` |
| Some queries in a composed view succeeded, others failed | `PARTIAL_DATA` |
| Cached data served while a background refetch is failing, or data older than its domain threshold | `STALE_DATA` |
| 401 / 403 / session expired | `UNAUTHORIZED` |

`PARTIAL_DATA` and `STALE_DATA` are the two that only exist because of caching, and both are
mandatory: a workspace composed of several queries must degrade to `PARTIAL_DATA` rather than
failing whole, and cached-but-stale data must be labelled rather than presented as current.

## 11.3 Rules

- Error Boundaries catch **render** failures only. Data failures never reach an Error Boundary —
  they are values, handled by the owning component (Phase 7 v1.1 §16).
- Every error state provides at least one recovery path. No dead ends (P4-14 §11, NP-07).
- Stack traces, HTTP internals and implementation detail must never reach the user
  (Phase 6 P6-31 anti-patterns).
- Errors are handled by their owning layer (Phase 4 P4-16 §13).

---

# 12. Loading States

Maps the library's status flags onto the four frozen loading categories of P4-14 §5.

| Category | Condition | Presentation | Constraint |
|---|---|---|---|
| **Initial** | `isPending`, no cached data, first application load | App shell + header + sidebar + workspace skeleton | **Never** a blank page, empty layout, or spinner-only screen (P4-14 §6) |
| **Resource** | `isPending` on a new query key | Navigation and layout preserved; **only the content region** shows placeholders | Navigation must remain available (P4-14 §7) |
| **Incremental** | `isFetchingNextPage`, or `isPlaceholderData` during pagination | Existing content stays; new content appends | Must preserve scroll position, selected resource, filters, sorting (C-7) |
| **Background** | `isFetching && !isPending` | Subtle non-blocking indicator only | **No** navigation reset, scroll reset, workspace switch, focus loss, or unmount (C-6) |

## 12.1 The load-bearing rule

> **`isFetching` shall never drive a region skeleton. Only `isPending` may.**

This single rule is the mechanism that satisfies C-6 and the P4-14 anti-patterns "Blocking
navigation during background refresh," "Spinner-only layouts," and "Focus loss after navigation."
Conflating the two flags is the most likely way to violate a frozen requirement, and it is
verifiable in review.

## 12.2 Pagination continuity

`placeholderData: keepPreviousData` is **mandatory** for every paginated and filtered analytical
table. It is what keeps the previous page rendered while the next resolves — satisfying C-7 and
contributing directly to the < 300 ms workspace-switch budget (C-13) by removing the blank frame.

---

# 13. Offline Behavior

## 13.1 Connectivity states (C-10)

| State | Detection | Behavior |
|---|---|---|
| **Connected** | Online, requests succeeding | Normal |
| **Reconnecting** | Online event fired, revalidation in flight | Non-blocking indicator; cached data remains readable |
| **Offline** | `onlineManager` reports offline | Cached data remains readable; navigation remains available; queries pause rather than fail |
| **Maintenance** | Backend maintenance response | Read-only notice; cached data readable; all mutations disabled |

## 13.2 Rules

1. **Navigation remains available whenever technically possible** (P4-14 §13). Offline must not
   trap the user.
2. Cached data remains readable while offline and is labelled `STALE_DATA` once past its domain
   threshold.
3. Queries **pause** when offline and resume on reconnect. They do not burn retries against a known
   disconnection.
4. **Mutations are rejected while offline, not queued.**

   This is deliberate. DEC-006 recalculates recommendations on events, and DEC-007 includes a
   `Superseded` lifecycle state. A queued decision response could be submitted minutes later
   against a RecommendationID that has since been superseded — the user would be acting on a
   recommendation that no longer exists, and DEC-008 binds responses to a specific ID and version.
   An offline mutation queue would create exactly the stale-decision hazard the lifecycle exists to
   prevent. The user is told the action requires connectivity and retries deliberately.

5. **No cache persistence to `localStorage` or `IndexedDB` in v1.** The application is an
   authenticated analytical workspace; persisting portfolio and recommendation payloads to disk
   raises the confidentiality concern in P4-13 §16 and has no owning decision. Deferred.

## 13.3 Relationship to the PWA question

This section does **not** deliver offline-first behavior. The PRD §11 "Mobile-first PWA"
requirement remains **unmet and unresolved** — blocker U-7, deferred to ADR-004. No service worker,
no manifest, no offline-first strategy is specified here. If ADR-004 selects a PWA posture, cache
persistence must be revisited as a superseding ADR to this one.

---

# 14. Implementation Rules

## SHALL

| # | Rule |
|---|---|
| S-1 | The application **shall** use TanStack Query as the sole Server State mechanism |
| S-2 | Every query and mutation **shall** be defined in a Repository |
| S-3 | Every query key **shall** be produced by a typed key factory colocated with its Repository |
| S-4 | Every query key's resource identifier **shall** originate from route params |
| S-5 | Every Repository **shall** map DTO → Domain Model before the value leaves it |
| S-6 | Cache policy **shall** be declared per domain per §7 |
| S-7 | Every optimistic update **shall** implement snapshot, rollback and settle-invalidation |
| S-8 | Mutations **shall** be configured `retry: false` |
| S-9 | Query retry **shall** be a predicate over the typed error per §10.1 |
| S-10 | Every error **shall** map to one of the five frozen workspace error states |
| S-11 | Every error state **shall** offer at least one recovery path |
| S-12 | Background refetch **shall** be invisible except for a non-blocking indicator |
| S-13 | Paginated and filtered tables **shall** use `placeholderData: keepPreviousData` |
| S-14 | Every query **shall** be cancellable via `AbortSignal` |
| S-15 | Tests **shall** construct a fresh `QueryClient` per test with `retry: false` |

## SHALL NOT

| # | Rule |
|---|---|
| N-1 | Server State **shall not** appear in a URL |
| N-2 | Server State **shall not** be the source of truth for Resource State |
| N-3 | Components **shall not** call `useQuery` or `useMutation` directly — access is via the Domain Adapter hook surface |
| N-4 | Components **shall not** receive a backend DTO |
| N-5 | A backend-computed value **shall not** be written to the cache optimistically |
| N-6 | `setQueryData` **shall not** be used as a substitute for invalidation |
| N-7 | Workspace, Page, Component or Overlay State **shall not** be stored in the query cache |
| N-8 | `isFetching` **shall not** drive a region skeleton |
| N-9 | Mutations **shall not** retry automatically |
| N-10 | Mutations **shall not** be queued while offline |
| N-11 | `refetchInterval` polling **shall not** be used outside the `ops` domain |
| N-12 | The API Client **shall not** retry |
| N-13 | Cache **shall not** be persisted to disk in v1 |
| N-14 | A second server-state library **shall not** be introduced |
| N-15 | Inline literal query keys **shall not** be written |

## MAY

| # | Rule |
|---|---|
| M-1 | A workspace **may** prefetch a likely next resource on hover or focus, subject to the S-6 cache policy |
| M-2 | A Domain Adapter **may** compose multiple queries into one hook surface, degrading to `PARTIAL_DATA` |
| M-3 | Cache policy **may** vary with IDX market hours (09:00–15:30 WIB) |
| M-4 | `select` **may** be used for cheap projection; it **may not** carry a business calculation |
| M-5 | Devtools **may** be enabled in development builds only |
| M-6 | Suspense integration **may** be adopted later, by superseding ADR |
| M-7 | Query cancellation on route change **may** be automatic |

---

# 15. Migration Implications

## 15.1 Greenfield — no migration cost

No frontend application exists. Phase 9 is NOT STARTED, 0 of 62 tasks complete, 0 lines written.
There is nothing to migrate from. This decision is being made at the only moment when it is free.

> **Correction (2026-08-20, on ratification — see §21).** This premise is no longer true and is
> preserved above as the historical record at the time this ADR was drafted (2026-08-07), not
> silently edited. By the time of approval, `frontend/src/domains/decision/` and
> `frontend/src/domains/settings/` are real, tested, and reading live `/api/v1/*` data through
> plain-`fetch` hooks (`hooks.ts` in each domain) — not the Repository/TanStack Query chain this
> ADR specifies. This was not an accidental drift: both hooks' own docstrings state, verbatim,
> that they are "the smallest working data layer" because "ADR-003 is still PROPOSED and the
> library isn't installed," and that "a future Repository migration would replace the internals
> without changing the hook's loading/error/data/refresh call signature." The actual migration
> cost is therefore low, not nil — see §21 for what was verified before approval.

## 15.2 Effect on Phase 9

| Task | Prior status | New status |
|---|---|---|
| B2 — Server State provider | BLOCKED — ADR-003 | **Unblocked on approval** |
| B6 — Seven-layer state architecture | BLOCKED — ADR-003 | **Unblocked on approval** |
| E4 — Server State cache and invalidation policy | BLOCKED — ADR-003 | **Unblocked on approval** |

Blocker U-5 closes. Workstream B becomes fully unblocked except B17 (identity, U-4).

## 15.3 Effect on the existing repository

**None.** The backend is untouched. No Python, template, route or configuration change is implied.
The existing `/api/v1` envelope and error codes are consumed as-is by the API Client.

## 15.4 Forward migration cost

| Scenario | Cost |
|---|---|
| Adding SSR later | High — would require a framework change, superseding ADR-001 §2. Not anticipated |
| Adding cache persistence | Low — `persistQueryClient` is additive. Requires a superseding ADR for the confidentiality question |
| Adding offline mutation queue | Medium — additive, but requires resolving the DEC-007 superseded-recommendation hazard in §13.2 first |
| Replacing the library | Medium — contained, because the Repository layer is the seam. Components never touch the library directly (N-3), so a replacement touches Repositories and the provider, not the workspace code |

The N-3 rule is what makes §15.4's last row acceptable. Keeping the library out of components is
the insurance policy on this decision.

---

# 16. Integration Pattern

## 16.1 Provider placement

A single `QueryClient` is created once at application startup and provided in
`app/providers/`, inside the Application State providers and outside the Router — so that route
changes do not remount the cache, and so that authentication state is available to the API Client.

```
ErrorBoundary
  └── ApplicationProviders        (theme · environment · flags · auth)
        └── QueryClientProvider   ← Server State
              └── RouterProvider  (Resource State)
                    └── WorkspaceShell
                          └── Workspace  (Workspace State)
                                └── Page (Page State)
```

Cache is per browser tab by construction, satisfying C-11. Cross-tab cache synchronization is
**not** implemented — P4-12 §16 requires tabs to be independent.

## 16.2 Per-domain file layout

Within the Phase 7 v1.1 §4 structure, no new top-level directory is introduced:

```
src/
├── api/                     API Client · envelope · typed ApiError · auth attachment
├── models/                  Domain Models · DTO types · mappers
├── state/                   QueryClient config · global defaults · key-factory helpers
└── domains/<workspace>/
      ├── repository/        queries · mutations · key factory · cache policy
      ├── adapters/          Domain Adapters — the hook surface
      ├── viewmodels/        formatting · error-state mapping
      └── components/        presentation only
```

## 16.3 The seam

The Repository is the only place that knows both the Domain Model and TanStack Query. Above it,
nothing imports the library. Below it, nothing knows about caching. This is what preserves Phase 7
§8 and §9 simultaneously and what makes N-3 enforceable by lint.

---

# 17. Acceptance Criteria

| # | Criterion | Status |
|---|---|---|
| AC-1 | One server-state solution selected | ✅ TanStack Query v5 |
| AC-2 | Architecture frozen | ⏳ On owner approval |
| AC-3 | No unresolved alternatives | ✅ RTK Query, SWR and custom cache each rejected with stated reasons |
| AC-4 | Compatible with Phase 7 | ✅ §8 chain and §9 DTO isolation preserved; no change to §4 structure |
| AC-5 | Compatible with Phase 8 | ✅ No sequence change; closes U-5 |
| AC-6 | Compatible with Phase 9 | ✅ Unblocks B2, B6, E4; adds no task |
| AC-7 | Compatible with ADR-001 | ✅ Seven layers preserved; Resource State intact; no rival state container |
| AC-8 | Layer ownership defined | ✅ §4.1, §5 |
| AC-9 | Query key strategy specified | ✅ §6 |
| AC-10 | Cache lifetime strategy specified | ✅ §7 |
| AC-11 | Mutation pattern specified | ✅ §8 |
| AC-12 | Optimistic update policy specified | ✅ §9 |
| AC-13 | Retry policy specified | ✅ §10 |
| AC-14 | Error propagation specified | ✅ §11 |
| AC-15 | Loading states specified | ✅ §12 |
| AC-16 | Offline behavior specified | ✅ §13 |
| AC-17 | SHALL / SHALL NOT / MAY defined | ✅ §14 |

---

# 18. Risks

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| R-1 | **Cache is mistaken for a state manager.** Workspace or Page State drifts into the query cache | High | N-7 · N-3 · import-boundary lint restricting the library to `repository/` · Phase 9 AC-5.5 review check |
| R-2 | **`isFetching` misused for skeletons**, breaking background-refresh invisibility | High | S-12 · N-8 · §12.1 stated as a single verifiable rule · E2E assertion that background refetch does not reset scroll or focus |
| R-3 | **Optimistic update on a backend-computed value**, making the frontend a source of truth | High | §9.2 explicit prohibition list · N-5 · AC-5.1 |
| R-4 | **Cache policy set at call sites**, producing inconsistent freshness | Medium | S-6 · policy declared only in Repositories · single `QueryClient` default |
| R-5 | **Over-invalidation** causing refetch storms and missing the 300 ms budget | Medium | Domain-prefix invalidation, not global · devtools inspection during Stage 4 |
| R-6 | **Under-invalidation** leaving stale data after a mutation | Medium | S-7 settle-invalidation mandatory · `STALE_DATA` state makes it visible rather than silent |
| R-7 | **Mutation architecture specified against endpoints that do not exist** (U-3) — the design may not survive contact with the real write API | Medium | No mutation implemented until U-3 resolves · revisit §8/§9 when the write contract is designed |
| R-8 | **Query-key sprawl** — inconsistent shapes across domains | Medium | S-3 typed key factories · shape fixed in §6.1 |
| R-9 | **Offline mutation rejection perceived as a defect** by users | Low | §13.2 rationale documented · clear messaging required · revisit under ADR-004 |
| R-10 | **Library major-version churn** | Low | Contained by the Repository seam (N-3); v5 is stable |
| R-11 | **`PARTIAL_DATA` under-implemented** — composed views fail whole instead of degrading | Medium | M-2 · workspace design-spec §11 acceptance criteria |

---

# 19. Future Implications

1. **The Repository seam is the insurance policy.** Because N-3 keeps the library out of
   components, replacing or upgrading it is a contained change. Preserve that rule even when it
   feels like ceremony.
2. **Cache persistence is now a one-ADR change**, not a rewrite — `persistQueryClient` is additive.
   The blocker is the confidentiality question in §13.2.5, not the technology.
3. **ADR-004 (PWA) may supersede §13.** If a PWA posture is adopted, offline-first, service-worker
   caching and the mutation-queue prohibition must all be revisited together. §13 is written to be
   replaceable as a unit.
4. **The write path will test §8 and §9.** They are specified ahead of the API (U-3). When the write
   contract is designed, expect to revise the invalidation map and the optimistic-permission list.
   Better to have a stated position to revise than to improvise under deadline.
5. **Market-hours-aware caching (M-3) is a real optimization**, not a nicety. IDX trades 09:00–15:30
   WIB; overnight revalidation of settled EOD data is pure waste. Worth implementing at Stage 5.
6. **Devtools will expose architecture violations.** The query-key domain prefix means the cache
   inspector reads as a map of the Domain Model. Reviewing it during Stage 4 is a cheap and
   effective architecture-compliance check.
7. **This ADR assumes a read-dominant application.** That holds today (33 GETs, 0 writes) and is
   likely to remain true — the product is a decision-support system, not a transactional one. If
   that assumption changes materially, revisit §8 and §9.

---

# 20. Recommendation

**Adopt TanStack Query v5 as the sole Server State mechanism, and approve this ADR.**

The decision is unusually low-risk and unusually well-timed:

- **Timing.** Zero lines of frontend code exist. Migration cost is nil, and will never be lower.
- **Structural fit.** It is the only candidate that slots into the frozen Phase 7 §8 chain without
  deforming a layer. RTK Query would collapse the Repository and import a rival state container;
  SWR would require hand-building rollback; a custom cache would recreate the undocumented-
  architecture problem ADR-001 exists to fix.
- **Coherence.** TanStack Table is already selected. One vendor, one idiom for data and for the
  tables that render it.
- **Containment.** The N-3 rule keeps the library out of components, so this decision is reversible
  at moderate cost — which is the right property for the last unresolved architecture choice.

The cost is roughly 13 kB gzipped and one new concept for the team. Against Apache ECharts and a
seven-workspace analytical application, neither is material.

**Recommended action:** approve ADR-003, then authorize Phase 9 Workstream A and the unblocked
portion of Workstream B.

**Recommended next decisions, in order:** ADR-002 (Ticker routes, blocks Stage 6) · U-1 design
token values (blocks Stage 3, hard blocker) · U-2/U-3 backend API and write path (block Stages
5–10).

---

# 21. Ratification Note (2026-08-20)

**Approved by Tjie, 2026-08-20**, as part of Production OS Slice 2 (ADR-003 → Watchlist vertical
slice). The substantive decision (§2 selection, §3 alternatives analysis, §4–§14 canonical
architecture/rules, §16 integration pattern) is approved **as originally drafted, unchanged** — the
evidence in this document was found to still support it on inspection, per §15.1's correction
above. Nothing in §2–§14 or §16 was rewritten to reach this approval.

**What was verified before approval, beyond re-reading the ADR itself:**

1. `frontend/tools/eslint/architecture-boundaries.js` already enforces this ADR's N-3 rule today —
   `@tanstack/react-query` is confined by lint to `domains/*/repository/**`, `state/**`,
   `app/providers/**`, `tests/**` — even though the package was not yet installed and no
   `repository/` directory existed anywhere. The tooling was already built assuming this decision;
   ratifying it closes the gap between enforced tooling and formal status rather than opening one.
2. `frontend/src/app/providers/app-providers.tsx` and `src/main.tsx` already carry an explicit,
   marked slot and provider-order comment for `QueryClientProvider`, citing this ADR's §16.1 by
   section number, written before this approval.
3. `frontend/src/domains/decision/hooks.ts` and `frontend/src/domains/settings/hooks.ts` (see
   §15.1's correction) are the only two existing consumers of server data. Neither uses `useQuery`
   directly (N-3 is not violated retroactively — there was nothing to violate it, since the library
   wasn't installed). Migrating their internals to the Repository/TanStack Query chain is explicitly
   **deferred, not performed, by this ratification** — it is a separate task from the Watchlist
   vertical slice this approval unblocks, tracked as follow-up, not silently done here.

**Decision on migration order:** Watchlist is built as the first workspace directly on the
approved architecture (Repository → Domain Adapter → ViewModel → Component, TanStack Query at the
Repository seam), establishing the reference implementation §16.2 describes. Decision Center and
Settings are **not** touched by this ratification — their interim hooks continue to work exactly as
documented in their own docstrings, and migrating them is left to a future slice so as not to
introduce unrelated risk into workspaces the master goal requires "must not regress."

Blocker U-5 closes on this ratification. Phase 9 tasks B2, B6 and E4 unblock, per §15.2 (unaffected
by the §15.1 correction — that section's blocker/unblock claims were never about the greenfield
premise). Subsequent change to the frozen architecture in §2–§14/§16 requires a superseding ADR, per
this document's own Freeze effect (header table).

---

**Status:** APPROVED — 2026-08-20, by Owner.

**On approval:** the Server State architecture defined in this document is FROZEN. Blocker U-5
closes. Phase 9 tasks B2, B6 and E4 unblock. Subsequent change requires a superseding ADR.

# End of ADR
