# AF-2 WP4 — Technical Debt Audit

Companion to `Audit/AF2_WP4_IMPLEMENTATION_REPORT.md`. Full-repository search for the seven debt
categories named in the WP4 mission brief, each classified **required** / **obsolete** / **blocked
by remaining callers**.

---

## 1. `reset_market_ctx` — **blocked by remaining callers**

**What it is:** `engine/agent_firm/firm.py::reset_market_ctx()` flushes `_market_ctx`, the module-
global cache `_build_context()` used to populate. `_build_context()` itself was deleted in WP3 (per
`ADR-AF-002`'s "Required Implementation Changes") — nothing reads `_market_ctx` anymore.
`reset_market_ctx()` is therefore, as of WP3, a **pure no-op**: it sets an already-unused variable
to `None`.

**All call sites found (repository-wide grep, `*.py`):**

| Call site | Kind | Reachable in production? |
|---|---|---|
| `scheduler/scanner.py:316` (`scan_momentum_signals()`) | Production | Yes, but this function never calls `evaluate_staged()`/the Agent Firm itself — the call is already-vestigial *within this function*, independent of the WP1-3 migration |
| `scheduler/scanner.py:1389` (`scheduled_multi_strategy_scan()`) | Production | Yes — precedes `run_agent_firm_gate()`/`rank_bear_watchlist_and_notify()` |
| `scheduler/jobs.py:872` (`run_premarket_firm_scan()`) | Production | Yes — wired this WP |
| `scheduler/jobs.py:1056` (`run_eod_trade_plan()`) | Production | Yes — wired this WP |
| `monitor.py:42` (`_agent_confirms_exit()`) | Production | Yes — wired this WP |
| `scripts/probe_actual_http_concurrency.py:58` | **Developer diagnostic script** | Not part of any scheduled/production path — hardcoded personal path (`/home/tjiesar/...`), invoked manually |
| `scripts/replay_firm_offline_run.py:89` | **Developer diagnostic script** | Same as above |

**Classification: blocked by remaining callers.** The five production call sites all call a
function that is now a harmless no-op — none of them need to be edited for correctness (the
function does nothing either way). But the function **cannot be deleted** while the two developer
scripts still call `firm_mod.reset_market_ctx()` directly and unconditionally (not inside a
try/except, not behind a mock) — deleting it would break those scripts the next time a developer
runs them (`AttributeError: module 'engine.agent_firm.firm' has no attribute 'reset_market_ctx'`).

**Why not just remove the calls from production code and leave the function for the scripts?**
Considered and rejected: since the function must remain regardless (blocked by the scripts), and
every production call to it is genuinely free (a few nanoseconds, one `None` assignment), removing
the calls from five production call sites while leaving both the function and the scripts unchanged
would produce an inconsistent mid-state — some callers still call it, some don't, for a function
that behaves identically either way — at real review/diff cost and zero behavioral or performance
benefit. A single, atomic cleanup (delete the function **and** every one of its seven call sites
**and** update the two scripts) is the better-shaped change, and it requires touching
`scripts/`, which this work package's "Focus on scheduler/scanner and Agent Firm integration" does
not name.

**Proposed minimal follow-up** (not performed by this work package): a small, dedicated change that
(a) removes the `_firm.reset_market_ctx()`/`firm_mod.reset_market_ctx()` call from all seven call
sites, (b) deletes `reset_market_ctx()` and the now-fully-dead `_market_ctx` global from `firm.py`,
and (c) updates `firm.py`'s module docstring (which still lists `reset_market_ctx()` in its
"Public API" comment). Low risk, mechanical, but touches two files (`scripts/`) outside this
session's stated focus — proposed as its own reviewed change rather than folded in here.

---

## 2. Legacy context builders — **obsolete, already removed (WP3); none found remaining**

`engine/agent_firm/firm.py::_build_context()` (the 7-raw-SQL-query function) was already deleted in
WP3, per `ADR-AF-002`'s explicit instruction. A repository-wide search for any other function
matching this shape (raw per-candidate SQL assembled ad hoc, bypassing
`engine.agent_firm_context.build_candidate_context()`) found none. The three call sites this WP
wired (`scheduler/jobs.py` x2, `monitor.py` x1) were not "legacy builders" in this sense — they
built **no** context at all (an omission, not a competing implementation) — see the Implementation
Report and the Call Graph Report for the distinction.

## 3. Compatibility shims — one found (`reset_market_ctx`, above); none other

Searched for any other function whose docstring/comment self-identifies as a shim, wrapper, or
back-compat layer in `engine/agent_firm/` and `engine/agent_firm_context.py`. Only
`reset_market_ctx()` qualifies. `AgentState`'s unused `db_path`/`context` `TypedDict` keys (left in
place by WP3, since editing `schemas.py` was out of that work package's scope) are dead **fields**,
not a shim — covered under item 6 below.

## 4. Deprecated helper functions — none found in Agent-Firm-context scope

`engine/agent_firm/config.py` has two `DEPRECATED` warnings (`DEEPSEEK_API_KEY`/`DEEPSEEK_BASE_URL`
→ `ZAI_API_KEY`/`ZAI_BASE_URL` rename) — unrelated to ADR-AF-002 (a provider-naming migration, not
context assembly/consumption). Out of this audit's scope; not touched.

## 5. Duplicate context assembly — none found

`engine/edge_enrich.py::enrich_candidate()`/`market_regime()` build a **different**, unrelated dict
shape for the separate `EDGE_SCORE_MODE` veto pipeline — already confirmed by `ADR-AF-001` as
"Consumers-Only" (wraps `detect_regime()`/`tech_direction()`, does not re-derive them) and untouched
by WP1-3. No second implementation of any Tier 1 context object's assembly logic was found anywhere
outside `engine/agent_firm_context.py`.

## 6. Unused imports/classes

| Location | Finding | Action |
|---|---|---|
| `engine/agent_firm/firm.py:18` | `import time`, unused (predates WP1-3, confirmed by `git log`/`git show` against the last commit touching this file — not introduced by this migration) | **Removed this WP** — trivial, zero-risk, in the exact module this work package concerns |
| `engine/agent_firm/schemas.py::AgentState` | `db_path`/`context` `TypedDict` keys, unused since WP3 deleted `_build_context()` | **Not removed** — `schemas.py` is out of WP3/WP4's stated scope ("do not modify SignalCandidate schema" extended conservatively to the whole file); documented in WP3's own report, re-confirmed still true here |
| `engine/agent_firm/schemas.py::ConsensusContext` | Tier 2 type, no builder, no attach point | Not "unused" in the dead-code sense (it's a documented, deliberate future-work placeholder per `ADR-AF-002`) — see item 7 |
| `scheduler/jobs.py:36` | `_load_ohlcv_bulk` imported from `scheduler.utils`, unused (found by an `ast`-based unused-import sweep) | **Not removed** — predates WP1-3, unrelated to Agent Firm/context work, and this is a large (1300+ line) shared production job file; fixing an unrelated pre-existing import in a file this WP touches only for a narrow reason is out of mandate |
| `scheduler/scanner.py:408,691` | `_sqlite3`/`sqlite3` imports, unused | **Not removed** — same reasoning; `scanner.py` was not otherwise touched this WP (see Implementation Report — it needed no fix), and these are pre-existing, unrelated findings |

## 7. Dead code introduced by WP1–3

None found beyond what WP2/WP3's own reports already documented and this session re-confirmed
still accurate:

- `ConsensusContext` (schemas.py) — Tier 2 type with no builder (`guardrails.py::
  build_consensus_summary()` was never implemented) and no evaluation-graph attach point. Inherited
  from WP1, re-confirmed unbuilt by WP2, re-confirmed unbuilt by WP3, re-confirmed unbuilt here.
  Building it is out of WP4's mandate — it would be new Tier 2 wiring, not a completion of
  already-shipped Tier 1 producer/consumer wiring, and no analyst-node hook exists yet to feed it.
- `SessionContext` (schemas.py) / `build_session_context()` (agent_firm_context.py) — builder
  exists, no `SignalCandidate` attach point (never named in `ADR-AF-004`'s frozen field list).
  Same status as WP1/WP2/WP3 left it.
- `OpportunityContext` — named in `ADR-AF-002`'s prose, has no type definition and no builder
  anywhere in the codebase. Same status as WP1/WP2/WP3 left it.

None of these three are newly discovered — they are confirmed still in the same state WP1-3 left
them, carried forward here rather than silently resolved or silently dropped from the record.

---

## Summary Table

| Item | Classification | Action taken |
|---|---|---|
| `reset_market_ctx()` + its 7 call sites | Blocked (2 dev-script callers) | Documented; minimal follow-up proposed; not removed |
| `_build_context()` | Obsolete | Already removed in WP3; confirmed still gone |
| `AgentState.db_path`/`.context` | Dead, but schema-file-scoped | Left in place (out of mandate) |
| `firm.py`'s `import time` | Dead, pre-existing | Removed |
| `scheduler/jobs.py`'s `_load_ohlcv_bulk` import | Dead, pre-existing, unrelated | Left in place (out of mandate) |
| `scheduler/scanner.py`'s `sqlite3`/`_sqlite3` imports | Dead, pre-existing, unrelated | Left in place (out of mandate) |
| `ConsensusContext`/`SessionContext`/`OpportunityContext` | Incomplete by design (Tier 2 / no attach point) | Left in place (out of mandate) — not dead code, deliberate scope boundary |
| Three missing Tier-1-context construction sites (`jobs.py` x2, `monitor.py` x1) | **Not a "debt" category named in the brief, but the audit's central finding** | Wired this WP (see Implementation Report) |
