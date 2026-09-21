# ADR-006 — Legacy Flask UI Disposition

| Item | Value |
|---|---|
| ADR ID | FRONTEND-ADR-006 |
| Title | Legacy Flask UI disposition — retirement path for `/` and `/portfolio` Jinja templates |
| Status | **PROPOSED — decision not made.** This document lays out options and a recommendation; it does not select one. |
| Date | 2026-08-19 |
| Depends On | Shares a serving-layer surface with ADR-005 (deployment strategy) — see §8. Neither ADR blocks the other from being decided first. |
| Authority | `frontend/README.md` blocker U-9 · `ADR-001` §7 ("Follow-up ADRs required" names ADR-006) · `Audit/PRODUCTION_ENGINE_BACKLOG.md` · `app.py` catch-all route comment ("disposing of the legacy UI is ADR-006/U-9's decision, not this route's") |
| Closes | Blocker **U-9** (blocks cutover) |
| Freeze effect | None yet. On approval of an option, the retirement rule for the legacy pages becomes FROZEN; changing it again requires a superseding ADR. |

---

# 1. Context

## 1.1 What the legacy pages actually are

Two Flask routes serve pre-existing Jinja templates today, registered in `app.py` **before** the SPA catch-all
(Werkzeug matches the more specific rules first, so there is no accidental collision at the Flask-routing
level — see §5 for where the collision actually happens):

- `@app.route("/")` (aliased `/backtest/multi`) → `render_template("workspace.html")` — a 2,224-line template,
  a screener/multi-strategy-backtest workspace.
- `@app.route("/portfolio")` → `render_template("portfolio.html")` — a 414-line template with a real,
  functioning portfolio-backtest UI: `lightweight-charts@4.2.0` integration, metric cards, a sector-concentration
  canvas, custom dark-theme CSS.

**Neither of these is a stub or dead code.** They are live, working features currently in production use. Any
disposition decision has to be weighed against removing functionality that works today, not against removing
placeholder pages.

## 1.2 What the SPA has in their place, today

Per the frozen 7-workspace architecture (Decision, Portfolio, Watchlist, Market, Search, Settings, Ticker —
`ADR-001` §3), the SPA's client-side router (`frontend/src/app/router/app-router.tsx`) defines a `/portfolio`
route rendering `WorkspaceRoute id="portfolio"`, which resolves to a generic `WorkspaceShellPage`. That
component's own docstring states plainly: *"A generic container standing in for all seven workspaces... There
is no business UI, no data and no API access anywhere in it... Workstream D replaces each route element here
with the real workspace."* Its rendered output includes the literal placeholder text *"Workspace shell. Content
is delivered in Phase 9 Workstream D."*

Confirmed directly against the source tree: `frontend/src/domains/decision/` and `frontend/src/domains/portfolio/`
each contain **only a `.gitkeep` file** — genuinely empty, nothing built. Per
`PHASE_9_FRONTEND_IMPLEMENTATION_v1.1_RESET.md`'s Workstream D table, both are **BLOCKED**: Portfolio (D5) on
U-2 (backend API covers ~1 of 8 domains) and U-4 (no identity layer); Decision Center (D6) on U-2, U-3 (zero
write endpoints), U-4, and U-11/ADR-007 (terminology). None of these blockers has a resolution date.

The **only** real, populated SPA content live today is `/internal/operations` (the Operations Dashboard / Job
History slice) — deliberately **not** one of the 7 frozen workspaces, mounted as a standalone route "reachable
by direct URL/bookmark rather than global nav" per its own page docstring, needing zero new backend endpoints
since it consumes pre-existing scheduler/status APIs.

## 1.3 The `/` page's SPA mapping is unclear

`workspace.html`'s functional scope — screener plus multi-strategy backtest — doesn't map cleanly onto any of
the 7 frozen workspace names (Decision, Portfolio, Watchlist, Market, Search, Settings, Ticker). This is flagged
here as a real gap this ADR surfaces but does not resolve — see §7 Open Questions. Whatever option is chosen,
"feature-complete" can't be defined for `/` until its SPA-side owner (if any) is identified.

---

# 2. Decision Drivers

| # | Driver |
|---|---|
| D-1 | The legacy `/portfolio` page is a real, working feature (§1.1) — premature retirement removes functionality users have today, not a placeholder. |
| D-2 | The SPA's Portfolio and Decision Center workspaces are empty shells, blocked on backend work (U-2/U-3/U-4) with no scheduled resolution (§1.2). |
| D-3 | "Retire once the SPA equivalent is feature-complete" is only a real rule if "feature-complete" is defined concretely per page — otherwise it never actually triggers. |
| D-4 | Whatever is chosen must be an explicit, documented state, not accidental coexistence — the routing inconsistency in §5 is a direct symptom of "undecided by default." |
| D-5 | Solo operator: prefer not maintaining two live implementations of the same feature indefinitely without a stated reason, given D-2 makes "indefinitely" a real possibility rather than a formality. |

---

# 3. Options Considered

## Option 1 — Per-page retirement once the SPA equivalent is feature-complete

Each legacy page retires individually, the moment its SPA equivalent reaches a stated bar — not "a route
exists," but defined functional parity:

- **`/portfolio`** retires when the SPA Portfolio workspace (D5) satisfies its own frozen acceptance criteria
  (`PORTFOLIO_DESIGN_SPEC_v1.0_FROZEN.md`) **and** is backed by real data rather than a shell — at minimum,
  functional coverage equivalent to `portfolio.html` today: holdings/backtest metrics, charts, sector
  concentration.
- **`/`** — cannot be given a concrete criterion yet. Its functional scope (screener + multi-strategy backtest)
  has no clear 1:1 SPA workspace owner today (§1.3). This is a real gap Option 1 exposes rather than resolves.

| | |
|---|---|
| **Cost** | Requires an explicit acceptance checklist per page. One already exists for Portfolio (its frozen design spec). One does not exist for `/` — that mapping has to be done first, as a prerequisite, before Option 1 can even be applied to that page. |
| **Benefit** | Principled — ties retirement to actual functional parity rather than a calendar date or a task-completion checkbox. Never removes working functionality prematurely (respects D-1). |
| **Risk** | Given D-2 (SPA blocked on U-2/U-3/U-4, no ETA), "feature-complete" could be a long way off. In the near term this behaves like Option 2 (long coexistence) — the difference is Option 1 has a real terminal condition once the blockers clear, Option 2 by design does not. |

## Option 2 — Explicit indefinite coexistence (legacy = simple/fallback, SPA = advanced)

Legacy pages stay permanently as a simple/fallback view; the SPA workspace is positioned as the advanced view,
once built. Coexistence becomes a stated product decision instead of an accident of timing.

| | |
|---|---|
| **Cost to build** | Lowest of the three — primarily a documentation/product-labeling exercise, plus the immediate routing fix in §5 (required regardless of which option is chosen). |
| **Cost to maintain (solo)** | Ongoing and real — two implementations of overlapping functionality (`portfolio.html` vs. the eventual SPA Portfolio workspace) both need to keep working. Any backend API change touching portfolio data potentially needs coordinating across both surfaces indefinitely. |
| **Benefit** | Zero risk of deleting working functionality (fully respects D-1). Gives users a working portfolio view today regardless of the SPA's timeline, which given D-2's lack of an ETA is not a small benefit. |
| **Risk** | This is the closest option to today's *actual* (accidental) state. Codifying it doesn't by itself fix anything — it needs a genuine stated rationale ("why keep both, on purpose") to be a decision rather than a description of drift (D-4). |

## Option 3 — Immediate per-page cutover as each SPA workspace ships

The legacy template is deleted the same day its SPA workspace is marked shipped in the Phase 9 plan.

| | |
|---|---|
| **Cost to build** | Low per cutover event — it's a deletion, not new work. |
| **Benefit** | Cleanest end state, fastest reduction in maintenance surface, and informally forces the SPA workspace toward actual completeness before anything is removed. |
| **Risk** | **Highest of the three for a user-visible functionality regression.** "Shipped" in Phase 9's Workstream D today means a task is marked done in the plan document — nothing in Phase 9 enforces a feature-parity audit against the legacy page before that happens. Given D-1 (portfolio.html has fully worked charts and metrics today), a same-day cutover risks shipping a narrower SPA feature set than what it replaces, with no buffer to catch that before users lose functionality. |

---

# 4. Evaluation Against the Decision Drivers

| Driver | Option 1 | Option 2 | Option 3 |
|---|---|---|---|
| D-1 (don't remove working functionality) | Respected — retirement gated on parity | Fully respected — nothing is ever removed | At risk — cutover isn't gated on a parity check |
| D-2 (SPA blocked, no ETA) | Coexistence persists until parity, same practical effect as Option 2 short-term | Coexistence is the explicit permanent design | Cutover could happen before parity, ignoring the blocker reality |
| D-3 (concrete "feature-complete" definition) | Forces one — and surfaces that `/` doesn't have one yet (§1.3) | N/A — no retirement condition to define | Uses "task marked shipped," which is not a functional-parity definition |
| D-4 (explicit, not accidental) | Explicit terminal condition | Explicit only if a real rationale is stated, not just "this is what's happening" | Explicit, but the *trigger* (task completion) isn't functionally rigorous |
| D-5 (avoid indefinite dual maintenance) | Bounded — ends when parity is hit | Not bounded by design | Most bounded — fastest to a single implementation, at the cost of D-1 risk |

---

# 5. The Confirmed Routing Bug — Fix Now, Regardless of Which Option Is Chosen

**Verified:** a full-page load of `/portfolio` hits Flask's `@app.route("/portfolio")` and returns the working
414-line legacy page. Client-side navigation to `/portfolio` from *within* an already-loaded SPA (e.g. clicking
a sidebar link after landing on `/internal/operations` or `/decision`) is intercepted by React Router instead,
and renders the empty `WorkspaceShellPage` stub. **Same URL, two different applications, depending purely on
how the user arrived.**

This is a defect under all three options above — even Option 2 (explicit coexistence) doesn't want the
coexistence decided by a race between Werkzeug's route table and React Router's route table. It should be an
explicit choice (e.g. distinct paths, or a deliberate mode switch), never an accident of which router happens
to intercept the click.

## Recommended immediate fix (does not require this ADR to be decided first)

Remove `/portfolio` (and `/`, for the same reason) from the SPA's client-side route table
(`frontend/src/app/router/app-router.tsx` / `workspaces.ts`) while these remain live Flask pages — i.e., the
SPA should never claim a URL it can't yet honor with real content. Concretely: either drop the `<Route>`
entirely so React Router's catch-all (`*` → `NotFoundPage`) doesn't fire on it either, or point it at an
explicit `window.location.href` redirect back to the Flask page instead of a client-side `<Route>` element.
This restores "one URL, one page" without deleting anything and without pre-judging which option this ADR
lands on — once a workspace is actually ready to take over its URL (Option 1 or 3), the route gets added back
deliberately, as part of that cutover.

**Alternative fix:** keep the SPA route but have it explicitly redirect/404 rather than render the empty shell
— functionally equivalent, marginally more useful if some of the 7 workspace shell routes are meant to preview
intentionally for internal dogfooding purposes. Either fix resolves the collision; the difference is cosmetic.

This is flagged as something to fix promptly — it's a live UX bug, not a debated architecture point. **It has
not been applied here** — this document is analysis and recommendation only, per the task's document-only
scope; implementing it is a separate, small, low-risk follow-up.

---

# 6. Recommendation

**Recommend Option 1 (per-page retirement on feature-complete), with Option 2's honesty about the interim
state folded in explicitly** — not as a fourth option, but as how Option 1 should be *described* while U-2/U-3/
U-4 remain open: state plainly, today, that coexistence is explicit and intentional for now, and will end per
Option 1's per-page parity criteria once the backend blockers clear.

Reasoning:

1. **Respects D-1 unconditionally** — no working feature is ever removed ahead of its replacement actually
   matching it, unlike Option 3.
2. **Has a real terminal condition**, unlike Option 2 taken alone — this matters because D-2's blockers (U-2,
   U-3, U-4) are not permanent; when they clear, Option 1 actually resolves instead of persisting by default.
3. **Surfaces, rather than papers over, the real gap** — `/`'s missing SPA-workspace mapping (§1.3) needs
   resolving either way, and Option 1 is the only choice that makes that gap visible as a concrete blocker
   instead of letting it hide behind a vaguer "eventually" framing.

**This is a recommendation only. Tjie decides.** The routing fix in §5 is recommended as an immediate action
**independent of which option is ultimately chosen** — it fixes a present bug, not a pending decision.

---

# 7. Open Questions

| # | Question |
|---|---|
| Q-1 | What is `/` (`workspace.html`)'s SPA equivalent, if any? It does not map cleanly onto one of the 7 frozen workspaces by name. Needs product-level resolution before Option 1's "feature-complete" criterion can be defined for this page at all. |
| Q-2 | Does `/internal/operations` — already real, already live, deliberately outside the 7 frozen workspaces and reachable by direct URL only — set a usable precedent for how other in-progress or partial workspaces should be exposed during their build-out? Worth considering alongside whichever option is chosen. |
| Q-3 | Once U-2/U-3/U-4 clear enough for Portfolio (D5) to be buildable, who defines "feature-complete" in practice — is `PORTFOLIO_DESIGN_SPEC_v1.0_FROZEN.md`'s acceptance criteria sufficient on its own, or does it need a side-by-side functional comparison against `portfolio.html` before cutover? |

---

# 8. Relationship to ADR-005

ADR-005 decides *how the frontend gets built and served*; this ADR decides *whether and when the legacy pages
retire*. They intersect at one point: whichever serving layer ADR-005 selects has to keep serving `/` and
`/portfolio` correctly for as long as this ADR keeps them alive.

- Under ADR-005 Option 1 (its recommendation), this is already true today — no change needed regardless of
  which option this ADR lands on.
- Under ADR-005 Option 2 (reverse proxy), the proxy needs explicit passthrough rules for these legacy routes,
  not just `/api/*` and `dist/` — an extra piece of configuration that has to stay correct through whatever
  timeline this ADR sets, including full retirement if Option 1 or 3 here is chosen.

Neither ADR blocks the other from being decided first.

---

**Status:** **PROPOSED — awaiting owner decision.** No option is approved. No page is scheduled for retirement
or cutover. The §5 routing fix is recommended as an independent, immediate action but has not been applied.

# End of ADR
