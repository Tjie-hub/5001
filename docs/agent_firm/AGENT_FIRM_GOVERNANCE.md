# Agent Firm — Governance

**Date:** 2026-07-28
**Purpose:** the rules by which Agent Firm's interface, releases, and deprecations are managed, once
it begins evolving independently of Production Engine's now-frozen v1 baseline. Modeled on the
governance discipline this repository already applies elsewhere (`CLAUDE.md`'s shadow/enforce rollout
pattern, the Research Governance Corpus's append-only decision log) rather than inventing a new style.

---

## Versioning Policy

- Agent Firm adopts semantic versioning (`MAJOR.MINOR.PATCH`) scoped to the interface defined in
  `AGENT_FIRM_INTERFACE_SPEC.md` — **not** to the whole `engine/agent_firm/` codebase.
- **MAJOR** — any change to `evaluate`/`evaluate_staged`/`reset_market_ctx`'s signature, the
  `SignalCandidate`/`AgentDecision` field set (removal or type change of an existing field), or the
  decision-lifecycle enum (`approve`/`veto`/`bypassed`/`degraded`).
- **MINOR** — a new optional field added to `SignalCandidate`/`AgentDecision`, a new operation added
  to the formal `/api/agent/*` contract (post AF-2), or a new provider added internally with no
  interface change.
- **PATCH** — internal implementation changes with zero interface impact (a provider's own retry
  tuning, a new agent role's internal prompt, a bugfix that doesn't change the contract's observable
  behavior).
- Agent Firm's version is tracked independently of the Production Engine's release tag once AF-1's
  foundation work lands — until then, it inherits Production Engine's git SHA as its de facto version,
  which is itself Blocker 6 in the Architecture document.

## Release Policy

- No release ships without: (a) its own full test suite green, (b) a re-verified Dependency Audit
  confirming no new "Tight coupling" entry was introduced, (c) an explicit interface-compatibility
  statement (see Compatibility Policy) in the release notes.
- Mirrors the existing repository-wide discipline: every new capability ships behind a mode flag
  first where a behavior change is involved (matching `AUTH_MODE`/`EDGE_SCORE_MODE`/`SECTORS_APP_MODE`'s
  established `off`/`shadow`/`enforce` pattern) rather than flipping straight to enforced behavior.
- A release is a generated, point-in-time record (matching this repository's own audit-trail
  convention) — release notes are never edited after the fact; a correction is a new, dated entry.

## Compatibility Policy

- **Within a MAJOR version:** Production Engine's existing call sites (the 5 entries classified
  "Public API" in the Dependency Audit, plus whatever AF-2 formalizes for `/api/agent/*`) must
  continue to work with zero code changes on the Production Engine side.
- **Across a MAJOR version bump:** a documented migration note is required, following the same
  standard this repository already uses for its research-governance corpus (a dated, explicit
  amendment — never a silent behavior change).
- **The decision-lifecycle enum is the one field with the strongest compatibility guarantee** — per
  the Interface Spec, every caller branches on it; a new lifecycle value is additive (MINOR at most,
  if handled as "any unrecognized value = treat as bypassed/fail-open" by convention) but removing or
  renaming an existing value is always MAJOR.
- **Fail-open is a permanent compatibility guarantee, not an implementation detail.** Per the
  Interface Spec §4, the interface never raises to the caller under normal operation. Any future
  Agent Firm version that would introduce a caller-visible exception path is a MAJOR change requiring
  explicit owner sign-off — this is the single most load-bearing behavioral guarantee Production
  Engine's own fail-open architecture (`run_agent_firm_gate`, `monitor.py`'s exit-veto check) depends
  on.

## Deprecation Policy

- A deprecated field/operation must remain functional for at least one full MINOR release cycle after
  being marked deprecated, with a logged warning (not a behavior change) on use.
- The four items in `AGENT_FIRM_INTERFACE_SPEC.md` §7 ("Explicitly Out of Scope") are not yet part of
  any versioned contract — they may be removed or replaced at any time without a deprecation cycle
  until AF-2 formally brings them into the contract. Any Production Engine code still depending on
  them at that point inherits the deprecation cycle from that point forward, not retroactively.
- Following this repository's own append-only convention: a deprecation is a new, dated record, never
  a silent removal from documentation.

## Independent Repository Timing

Per the standing instruction already agreed for the sequence following this Production Engine
release: the Agent Firm repository split happens **after** the Operations Dashboard / Job History
phase, and only once AF-7 (Production Certification) has passed. This governance document applies
regardless of whether Agent Firm lives in this repository or a separate one — the versioning,
release, compatibility, and deprecation rules above are unaffected by that timing decision.
