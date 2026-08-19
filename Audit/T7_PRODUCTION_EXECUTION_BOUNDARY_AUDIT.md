# T7 (Production Admission) — Execution Boundary Audit

**Date:** 2026-08-19 · **Branch:** `ops/hardening-2026-07-10` · **Authority:** implementation session
report (not a governance doc — the two open items in §4 need an explicit owner decision before
this can be called closed).

**Mandate:** IDX Master Plan T7 — make the research→production trade-execution boundary real and
enforceable. Interface of record: `registry/edge_registry.yaml` + `engine/registry_loader.py`
(single cached reader; degrades to `None`/legacy fallback on failure, never crashes — see
CLAUDE.md "Research → production contract").

---

## 1. Summary

Started from `engine/registry_loader.py::load_registry()`, found and fixed two fail-open bugs
there, then ran a full repo inventory of production-capable trade-execution entry points. Found
three live paths that bypassed the Edge Registry entirely (counter-trend book, momentum
auto-open, premover EOD). Checked the evidence trail (`gate_decisions` table) before deciding
what "Registry admission" should mean for each — none of the three had ever cleared the
gatekeeper. Per an explicit owner decision, chose the honest path over grandfathering: strategies
without a real evidence receipt are excluded from execution, not waved through.

**Net effect on live trading today:** Crash Recovery and Panic Rebound (the only one of the three
actually live and trading in production) now require real Edge Registry admission and — having
none — are excluded until they clear the gatekeeper. Momentum auto-open and premover EOD were
already dormant via their own pre-existing gates (`momentum` in the disabled-strategies list;
`auto_trade_from_premover = 'off'`); the new registry check is defense-in-depth for both, not an
active behavior change.

---

## 2. Registry loader fixes (commit `7a323f4`)

| # | Bug | Fix |
|---|---|---|
| 1 | `load_registry()` appended every entry to `entries` unconditionally, even when `validate_evidence()` found an unverified, un-grandfathered SHADOW/APPROVED receipt — the violation was logged but the entry still loaded as governed. | Moved the append behind a `continue` so un-grandfathered violations are excluded, not just flagged. |
| 2 | A manifest YAML that parses but isn't a mapping (e.g. a list) crashed `validate_evidence()` with `AttributeError`, which propagated out of `load_registry()` and — via `get_registry()`'s except-clause — zeroed **the entire registry**, not just the one bad entry. | Coerce non-dict parses to `{}`, same as the existing unreadable/missing-file path. |
| 3 | `approved_universe()` only recognizes `status=='APPROVED'`, so `scheduler/scanner.py::_edge_selectable()` treated a SHADOW-only registry entry identically to "not in the registry at all" and fell back to the ungoverned legacy `wf_edge` query — the `SHADOW → None → ungoverned → fallback → production` path T7 prohibits. | Added `registry_governance()`, distinguishing APPROVED (frozen universe), SHADOW (sentinel, must be excluded outright), and truly-unregistered/registry-unavailable (`None`, the only safe fallback case). Wired `_edge_selectable()` to it. |

All three were dormant in production at the time (`edge_registry.yaml` had exactly one entry,
`NR7_BULL`, APPROVED) but live for the next SHADOW promotion — the registry's normal intended
workflow. Tests: `tests/test_registry_loader.py`, `tests/test_registry_selector.py`,
`tests/test_edge_selector.py`.

---

## 3. Production execution inventory

| Entry point | Trigger | Registry-governed? | Classification |
|---|---|---|---|
| `paper_trade.py:281 open_trade()` | sole writer of the `paper_trade` table | N/A (the sink) | Choke point for the table, not for admission — every caller decides independently whether to call it |
| Registry-listed strategies via `_edge_selectable()` | daily scan (`scanner.py:643-679`) | Yes | VERIFIED-GOVERNED |
| Non-registry strategies via `_edge_selectable()`'s legacy branch | same | No — `wf_edge>0` query | VERIFIED-LEGACY-UNGOVERNED-BY-DESIGN (Phase 2C, audit C-6) |
| **Crash Recovery / Panic Rebound** (counter-trend book) | `adaptive_strategy_selector()`, previously appended unconditionally | **Now yes** (this session) | Was VERIFIED-UNGOVERNED-UNCLASSIFIED; **fixed** — see §4 |
| **`scan_momentum_signals()` auto-open** | daily scan (disabled by default) | **Now yes, defense-in-depth** (this session) | Was VERIFIED-UNGOVERNED-UNCLASSIFIED; **fixed** — see §4. Already dormant (config) |
| **`run_premover_eod()`** | premover cron | No | NEEDS-OWNER-DECISION — see §4.3; not fixed this session |
| `POST /api/paper/open` | manual API | No trade-logic gate; RBAC admin-only | VERIFIED-UNGOVERNED-BY-DESIGN (intentional manual override) |
| `forward_testing/*` | nightly cycle | N/A | Confirmed shadow-only — never calls `open_trade` |

---

## 4. Fixes and decisions this session

### 4.1 Counter-trend book (Crash Recovery, Panic Rebound) — FIXED

`scheduler/scanner.py::adaptive_strategy_selector()` appended both strategies to the selection
result unconditionally whenever the BEAR/SIDEWAYS regime map listed them, bypassing every other
gate (`_edge_selectable`, `wf_scores` consistency, the Edge Registry). Checked `gate_decisions`:
**zero rows for either strategy** — neither has ever cleared the gatekeeper.

Per explicit owner decision (register honestly, don't grandfather), each counter-trend strategy
now must independently clear `registry_governance()` — APPORVED status with the ticker in its
frozen universe — before it's included. Since neither has a registry entry, **both are excluded
today**; this is a deliberate behavior change, not a bug, and it means Crash Recovery / Panic
Rebound do not currently generate live trades. A second-order fallback bug was found and fixed in
the same change: `adaptive_strategy_selector()`'s "no strategy selected at all" fallback to the
unrestricted `get_ticker_best_strategies()` was gated on `not counter_trend` (the post-admission
list), so losing admission silently re-widened selection to a wf_scores-consistency scan off the
regime map entirely. Fixed to gate on `not counter_trend_candidates` (pre-admission regime-map
membership) instead, preserving the original fallback's intent.

Tests: `tests/test_adaptive_strategy.py`.

### 4.2 Momentum auto-open — FIXED (defense-in-depth)

`scan_momentum_signals()` opens trades directly, bypassing `adaptive_strategy_selector` and
`_edge_selectable` entirely; its only gate was `_get_disabled_strategies()` (config, currently has
`momentum` disabled) plus its own quality/regime/event guards — none of them the Edge Registry.
Checked `gate_decisions`: zero rows. Added a `registry_governance("Momentum Following")` check
alongside the existing disabled-list check: the scan now returns early unless that strategy holds
real APPROVED admission. Currently always blocks (no registry entry), which is consistent with —
and independent of — the existing disabled-by-default config, so a future accidental removal from
the disabled list can't alone re-enable live momentum trading.

Note: the actual `open_trade()` call in this function (`scanner.py:617`) doesn't pass
`strategy=`, so the opened trade is attributed via `open_trade()`'s own default
(`get_best_strategy_for_ticker(ticker)`), not a fixed `"Momentum Following"` tag — the registry
gate added here is a whole-scan gate on the "Momentum Following book" capability as this function's
own docstring frames it, not a per-trade attribution check. Making the per-trade attribution
Registry-aware too would be a larger change to `open_trade()`'s strategy-resolution logic, out of
scope for this session.

Tests: `tests/test_edge_selector.py`.

### 4.3 Premover EOD — NOT FIXED, flagged as owner decision

`run_premover_eod()` → `open_trade(ticker, close_price, strategy=None, notify=True)`. Two
findings:

1. **Evidence**: zero `gate_decisions` rows for premover; it is currently dormant anyway
   (`paper_config.auto_trade_from_premover = 'off'` in the live production DB), so there is no
   live-trading impact either way today.
2. **Schema mismatch**: premover trades are opened with `strategy=None` — they are never
   attributed to any `strategy_fn` at all. The Edge Registry's admission model
   (`universe_artifact` = a frozen ticker set keyed by `strategy_fn`) has no natural fit for a
   pattern-detection scanner that fires per-ticker on its own signal, independent of any named
   strategy identity. Forcing it into the existing schema (e.g. inventing a placeholder
   `strategy_fn`) would be a design change to what the Registry represents, not the smallest
   correct fix this session's other three changes could each be. Premover already has its own
   local off/shadow/enforce discipline (`get_premover_mode()`/`set_premover_mode()`,
   `paper_config` key `auto_trade_from_premover`) — structurally parallel to, but disconnected
   from, the Registry.

**Decision needed:** should premover ever be admitted through the Edge Registry (requiring a
`strategy_fn` concept to be added to its trades), or is its existing off/shadow/enforce mechanism
the intended permanent admission model for pattern-scanners of this kind, with the Registry
reserved for named backtested strategies only? Not resolved here.

### 4.4 `wf_edge` dual-use — NOT FIXED, flagged as owner decision

`_edge_selectable()`'s legacy branch (`scanner.py:668-679`) runs
`SELECT strategy FROM wf_edge WHERE ticker=? AND expectancy_pct>0` as **sufficient authorization
to open a live trade** for any strategy not in the Edge Registry — this is intentional, documented
legacy behavior (Phase 2C, audit C-6), left unchanged this session per explicit owner instruction.

The finding: `wf_edge` is therefore currently serving **two roles simultaneously** — research
output (read by the gatekeeper, dashboards) and a live production authorization source (read
directly by the scanner, no Edge Registry entry in between). CLAUDE.md's Edge Registry section
states the Registry is intended as the *sole* research→production interface; `wf_edge` acting as a
parallel, un-registry'd authorization channel is exactly the ambiguity that section is meant to
prevent, and it is the concrete mechanism by which invariant #2 ("every production-capable
execution path governed") is still not fully true — any strategy that appears in `wf_edge` with
positive pooled expectancy can trade today without ever touching `registry/edge_registry.yaml`.

**Decision needed:** either (a) formally ratify `wf_edge>0` as a second, permanent, legacy
admission channel with its own explicit rules (distinct from "ungoverned" — currently it has none
beyond the positive-expectancy threshold), or (b) set a migration path/deadline to route every
currently-legacy strategy through a real Edge Registry entry and retire the fallback. Not resolved
here — code unchanged.

---

## 5. Invariant #8 (fail-closed runtime) — closed (commit `3af07d3`)

`tests/test_t7_fail_closed_admission.py` drives real on-disk registry fixtures through the real
`load_registry()`/`get_registry()`/`registry_governance()` chain and the real
`adaptive_strategy_selector()`/`scan_momentum_signals()` gates (not mocking `registry_governance()`
itself, unlike the pre-existing selector unit tests). Proves all 9 required scenarios — missing
registry, malformed YAML, invalid evidence, missing evidence, missing receipt, non-admitted
strategy, SHADOW (even with an otherwise-valid receipt), execution-model/`requires` mismatch,
unreadable universe artifact — produce no admission and no selection, plus a positive control
proving APPROVED-with-valid-evidence *is* selected (so the gate isn't just trivially blocking
everything). Caught and fixed one test-fixture bug in the process (a flat-price synthetic OHLCV
series detects regime SIDEWAYS, not BEAR, which would have made these proofs vacuous for the
counter-trend book). No production code changed — all 9 scenarios already held from §2-4; this
closes the gap between "unit-tested with a mocked admission function" and "proven at the actual
execution boundary." Scope explicitly excludes the legacy `wf_edge>0` fallback (§4.4), unchanged.

---

## 6. Invariant #6 (edge/evidence/registry/strategy lineage) — closed for `NR7_BULL`

Found one genuine gap while tracing the full chain: nothing tied an Edge Registry entry's
`strategy_fn` back to a real, live-checker-backed production strategy — the exact audit-C-1 bug
pattern (a strategy name selectable with no checker behind it), one layer up from where
`tests/test_strategy_specs.py::test_regime_map_strategies_are_live_capable` already guards it for
the regime map. Closed with one new regression test,
`test_every_registry_entry_strategy_fn_has_a_live_production_checker` in
`tests/test_registry_lifecycle.py`, asserting every entry in `load_registry()['entries']` has a
`strategy_fn` present in `engine.strategy_specs.SPECS` with `live_checker=True` and present in
`engine.strategies._CHECKER_DISPATCH`. Passed immediately (no drift exists today) — this is a
regression guard against future drift, not a fix for a live violation. No production code changed;
"do not create a duplicate registry" honored — this reuses the existing `SPECS`/`_CHECKER_DISPATCH`
consistency web `test_strategy_specs.py` already established, just extends its reach to the Edge
Registry.

**Full lineage trace for `NR7_BULL` (the one live registry entry), file:line evidence:**

| Link | Evidence |
|---|---|
| Edge | NR7 (narrow-range-7) breakout pattern, BULL regimes only — `docs/superpowers/results/2026-07-07-nr7-generalization-study.md`, `docs/superpowers/results/2026-07-07-regime-edge-scan.md` |
| Evidence | `registry/manifests/NR7_BULL_v1.yaml` `evidence_summary` block (oos, pooled_44_ticker, robustness) — legacy pre-R-10 format; separately, `gate_decisions` (in `data/research.db`) has 3 REJECT rows for "NR7 Breakout" (2026-07-12/14), all *postdating* this entry's 2026-07-04 approval, which is exactly why it needs grandfathering (next row) rather than clean evidence |
| `edge_registry.yaml` | `registry/edge_registry.yaml` — the `NR7_BULL` entry (id/version/status/strategy_fn/regimes/universe_artifact/manifest/requires/changelog) |
| R-10 receipt | `engine/registry_loader.py:40-47` `_LIFECYCLE_DEBT[("NR7_BULL",1)]` — dated grandfather record (reason, remediation, deadline `2027-01-08`), since the legacy manifest doesn't match `validate_evidence()`'s expected `evidence.gate_decision`/`evidence.forward` shape |
| Strategy identity | `engine/strategy_specs.py:38` `StrategySpec("NR7 Breakout", "breakout", True)` in `SPECS` |
| Production implementation | `engine/strategies.py:1286` `'NR7 Breakout': lambda ticker, df: check_nr7_signal(df)` in `_CHECKER_DISPATCH` |
| Admission | `engine/registry_loader.py::registry_governance()`/`approved_universe()`, reading `get_registry()['entries']` |
| Signal | `scheduler/scanner.py:1498 adaptive_strategy_selector()` → `scanner.py:1506 check_current_entry_signal(ticker, strategy, df=df)` → `engine/strategy_specs.py::ensure_entry_price()` contract |
| Execution | `scheduler/scanner.py:1744 open_trade(ticker, float(entry_price), notify=False, ...)` → `paper_trade.py:281 open_trade()` |

---

## 8. Invariant #7 (execution-model compatibility) — closed for `NR7_BULL`

Compared research's backtest execution model against production's live scan on bar finality,
entry timing, price, signal timestamp, scan frequency, and partial-bar handling.

**Finding — currently aligned, not by accident:** research (`research/jobs.py`) loads OHLCV with
`final_only=True` (partial bars excluded); production's live scan (`scheduler/scanner.py:1438`)
defaults to `final_only=False` — partial bars *are* the signal input during intraday scans, by
documented design (`data/loaders.py`). This is a real, system-wide asymmetry. For `NR7_BULL`
specifically it is benign: `check_nr7_signal()` (`engine/strategies.py`) takes its signal from
`df.iloc[-2]` — a prior, already-closed bar — and prices entry off `df.iloc[-1]`'s `open`, which is
fixed at market open and doesn't mutate intraday even if that bar is still "partial." This exactly
mirrors the research side's own convention (`raw_entry = row['open']`, the bar *after* the signal
bar). The 5x/day intraday scan cadence (`scheduler/__init__.py:258-263`) vs. research's once-daily
evaluation is also immaterial for NR7: since both fields it reads (yesterday's `high`, today's
`open`) are fixed by the time any of the 5 daily scans run, the signal condition can't flip
mid-session — there is no "detected late, priced early" scenario. **This is a property of this
one checker, verified by reading it — not a system-wide guarantee.** Any future registry-governed
strategy whose live checker reads `high`/`low`/`close` off the still-forming last bar without an
`is_final` check would have a genuine look-ahead gap research's `final_only=True` convention
doesn't share.

**The real gap:** `engine/registry_loader.py`'s `requires{}`/`ENGINE_VERSIONS` compatibility gate —
the mechanism that exists precisely to catch this kind of drift — has been touched in exactly one
commit since its introduction (`git log -p --all -- engine/registry_loader.py`) and nothing
verifies it tracks anything real. Its four fields *were* defined with real meaning in the original
design spec (`docs/superpowers/specs/2026-07-07-research-production-separation-design.md:176-185`)
but that definition was never carried into the code as a comment, and no test enforces the
"bump on any semantic change" discipline the spec itself states. Separately,
`registry/manifests/NR7_BULL_v1.yaml` already pins a `config_hash` (sha256 of the research-side
`strategy_nr7_breakout` source) — verified this session to still match exactly — but nothing
re-verifies it, and the live checker (`check_nr7_signal`) has no equivalent pin at all.

**Fix applied (smallest correct, no architecture change):**
1. `engine/registry_loader.py` — added the four fields' real definitions as a comment on
   `ENGINE_VERSIONS`, sourced verbatim from the design spec, plus the "bump on semantic change"
   rule and a pointer to the new drift test.
2. `tests/test_t7_execution_model_pinning.py` — two source-hash regression tests: (a) the
   manifest's pinned `config_hash` still matches the current `strategy_nr7_breakout` source, (b) a
   newly-pinned hash for the live `check_nr7_signal` source (not previously covered by any
   mechanism). Either failing means a future edit changed the execution-model assumptions
   NR7_BULL's evidence relied on — the test docstring instructs *not* to just update the pinned
   hash, but to first determine whether the evidence still holds.

This directly operationalizes the fork research's evidence-backed recommendation (option C: the
`requires{}` version-pin mechanism is the right *shape* of fix, it just needed real content and
enforcement) over inventing a new mechanism or forcing a change to either side's code for a
strategy that's already aligned.

---

## 9. Invariant #9 (admission auditability) — closed for the live governed path

**Finding:** `paper_trades` recorded `strategy` (the strategy_fn) and `entry_date`, but nothing
tied a trade back to which registry state or which admission decision authorized it. The only way
to answer "what evidence/registry entry justified this trade" was manual `git log`/`git show`
archaeology on `registry/edge_registry.yaml`, correlated by guessing which commit was live on
`entry_date`.

**Fix (no duplicate registry — both values are read straight off the existing `get_registry()`):**
1. `engine/registry_loader.py::admission_path(strategy_fn)` — classifies the current admission
   state as one of `UNREGISTERED` / `SHADOW` / `APPROVED_DEBT` (via `_LIFECYCLE_DEBT`) /
   `APPROVED_CLEAN`. Tested against a real production-registry case (`"NR7 Breakout"` →
   `APPROVED_DEBT`, matching its known grandfather status) plus synthetic SHADOW/clean cases.
2. `paper_trade.py` — two new nullable columns on `paper_trades` (idempotent `ALTER TABLE`
   migration, matching this codebase's existing pattern): `admission_path`, `registry_hash` (the
   `get_registry()['hash']` at the moment of admission — a git short-hash or content hash an
   auditor can `git show` directly, no need to guess a date-correlated commit). `open_trade()`
   gained matching optional kwargs, both `None` by default so existing callers (manual API,
   premover) are unaffected.
3. `scheduler/scanner.py`'s Step 7 governed auto-open call site now computes and passes both
   values for every trade it opens.

**Not wired:** `scan_momentum_signals()`'s auto-open call site (already always blocked — see §4.2)
was deliberately left unwired. That function's `open_trade()` call doesn't pass an explicit
`strategy=`, so the strategy actually attributed to the trade is resolved *inside* `open_trade()`
(`get_best_strategy_for_ticker()`), which the caller can't know before calling — computing
`admission_path("Momentum Following")` there would attribute the wrong strategy's admission state
to the trade. Forcing a mismatched fit would make the audit trail actively misleading rather than
merely incomplete; left as `NULL`, consistent with the rest of this document's "smallest correct
fix" discipline. `run_premover_eod()`'s `open_trade(strategy=None, ...)` call is likewise
unaffected — untouched per the standing instruction not to modify premover.

**Verification gap acknowledged:** `scheduler/scanner.py`'s Step 7 wiring (4 new lines inside
`scheduled_multi_strategy_scan()`, a very large function with no existing full-integration test —
none of this repo's scan functions have one) is verified by direct code review and by unit tests
of its two components (`admission_path()` correctness; `open_trade()` correctly storing whatever
it's given) rather than by one true end-to-end test through the real scan function. Both
components are independently proven correct; only their wiring at that specific call site rests on
manual verification.

---

## 10. Invariant #10 (capital/promotion semantics vs. authoritative SSOT) — BLOCKING FINDING

Per instruction, this section documents the exact dependency rather than making the capital
decision it implies — this is not resolved and code was deliberately not changed.

**The chain the SSOT docs specify:** `docs/research_os/EVIDENCE_MODEL.md` §3/§5.1 — capital
requires confidence **C3**, which requires evidence **tier E5 + reproducibility X3** (a severe
pre-registered OOS test, surviving realistic friction, stable across regimes, **and**
independently reproduced from specification alone by someone other than the author). C2
("survived a severe test, not yet independent of its author or its family") explicitly licenses
only "Shadow deployment; **no capital**" (§3 table). C1 licenses "Continued study; **no capital**."

**What `validate_evidence()` actually checks** (`engine/registry_loader.py:52-73`): SHADOW needs
`gate_decision.final_state == 'PROMOTE_TO_FORWARD_TEST'`; APPROVED additionally needs
`forward.verdict=='GO'` with `n>=15` and `exp_pct>=0.50`. **Neither check inspects evidence class
(K1-K7), tier (E0-E7), confidence (C0-C4), or reproducibility (X0-X4) at all** — the registry
manifest schema has no field for any of these four axes. The code enforces *receipt existence*;
the Evidence Model gates on *what the receipt's evidence is actually worth*.

**The exact contradiction, verified against primary sources:**

`docs/research_os/EVIDENCE_MODEL.md` §8 is a worked example applying the model to **this specific
strategy** — Program P0's NR7 BULL finding — and its own table scores it **K3/K4, E3-ish, C1, X2**,
concluding in the document's own words:

> **Verdict.** No capital. C3 requires E5+X3; the claim has neither.

Yet `registry/edge_registry.yaml`'s `NR7_BULL` entry is `status: APPROVED`, loaded via
`_LIFECYCLE_DEBT`'s grandfather exception (`engine/registry_loader.py:40-47`, reason: "Phase C
gate=REJECT and shadow N=0. Governs on legacy grounds"), and — per §2-9 above, verified this
session — is genuinely production-capable and live: `registry_governance("NR7 Breakout")` returns
its frozen universe, `_edge_selectable()` admits it, and it can and does reach `open_trade()`
through the real scan pipeline. **This is real capital currently at risk under evidence the
institution's own canonical, worked-example-confirmed Evidence Model states plainly does not meet
its own bar for capital.**

Compounding this: `docs/Phase_A_Scientific_Foundation/01_SCIENTIFIC_FOUNDATION.md` ADR-L1-007
("Declare the single-researcher review deficit; do not absorb it") declares adversarial/independent
review **structurally unmet** with the institution's current one-researcher headcount, revisit
condition "headcount reaches ≥2 with an enforceable OOS firewall." Since C3 requires X3
(independent reproduction by someone other than the claim's author) and the Evidence Model's own
X-axis definition requires exactly the independence ADR-L1-007 says is currently impossible, **no
claim in this institution can reach C3 — and therefore no strategy can be honestly capital-eligible
— under current staffing, regardless of how much evidence accumulates on any other axis.** This is
a structural ceiling the registry's admission gate has no mechanism to detect: `validate_evidence()`
cannot fail on a C3/X3 requirement it never checks.

**Why this isn't resolved by RESEARCH_MASTER_PLAN v3 invariant #10:** `docs/RESEARCH_MASTER_PLAN.md`
(line 84-85) states NR7_BULL's grandfather via `_LIFECYCLE_DEBT` "fences" invariant #10 ("every
promoted edge has forward-test evidence"). That invariant is about *receipt-binding* (does a
receipt exist, R-10) — a different, narrower question than *what evidence class/tier/confidence the
receipt's contents support* (Evidence Model §5.1). Both statements can be — and are — true
simultaneously: NR7_BULL has a receipt (v3's invariant #10 is satisfied) and that receipt's
evidence does not clear the capital bar (Evidence Model's C3/§8 verdict is also correctly applied).
Per CLAUDE.md's own Decision-Making Hierarchy (§2): "*On a conflict about a mechanism already built
and frozen in `docs/RESEARCH_MASTER_PLAN.md` v3, v3 wins. On a conflict about scientific method or
institutional governance, the Research OS wins.*" Receipt-binding is v3's mechanism (v3 wins on
disputes about *how* a receipt is created/bound); whether a given receipt's evidence is *sufficient
for capital* is squarely a scientific-method question the Research OS's `EVIDENCE_MODEL.md` governs
— by the hierarchy's own stated rule, on that question the Research OS wins, and its answer for
NR7_BULL, in its own words, is "No capital."

**RESOLVED 2026-08-19 — owner decision: DEMOTE.** The owner ruled `NR7_BULL` demoted from
`APPROVED` to `SHADOW`. Full governance record: `docs/roadmap/DECISION_LOG.md` **D-029**. Executed
as the smallest safe change consistent with the registry's own stated convention ("entries are
IMMUTABLE once status leaves CANDIDATE; changes = new version," `registry/edge_registry.yaml:2`):

- `registry/edge_registry.yaml` v1 (APPROVED) → `status: SUPERSEDED` (a `_LIFECYCLE` state;
  excluded from `entries`, preserved byte-for-byte as the permanent historical approval record).
  v2 (SHADOW) added — same `strategy_fn`/`regimes`/`universe_artifact`/`requires`, pointing to a
  new manifest.
- `registry/manifests/NR7_BULL_v2.yaml` (new) — carries v1's `artifacts`/`evidence_summary`
  forward **unchanged** (same `config_hash`, same underlying strategy source), plus a `demotion:`
  block recording the Evidence Model's §8 verdict verbatim and the decision date. **No evidence
  fabricated or modified.**
- `engine/registry_loader.py::_LIFECYCLE_DEBT` rekeyed `("NR7_BULL", 1)` → `("NR7_BULL", 2)`,
  reason text updated to record the demotion. **Necessary, not incidental:** removing the debt
  entry outright (a literal reading of "terminate the grandfathered exception") was checked and
  found to be actively unsafe — without it, v2 fails `validate_evidence()` as an un-grandfathered
  violation and is *excluded from `entries` entirely*, which makes `registry_governance()` return
  `None` (not `'SHADOW'`) for "NR7 Breakout," which `_edge_selectable()` treats as *unregistered*
  and falls back to the **legacy, receipt-free `wf_edge>0` path** (§4.4) — re-exposing it to live
  trading through a *worse*, ungoverned channel than the one just closed. Keeping the debt entry
  (updated to reflect SHADOW, not APPROVED) is what keeps it visibly loaded and excluded, rather
  than invisible and re-exposed.
- `docs/RESEARCH_MASTER_PLAN.md` — minimal dated amendment (top-of-file note + two inline notes at
  the existing NR7_BULL mentions); no rewrite, no invariant renumbering.

**Production verified post-change:** `registry_governance("NR7 Breakout")` returns the `'SHADOW'`
sentinel; `_edge_selectable()` excludes it for a ticker actually in its former APPROVED universe,
even against a positive legacy `wf_edge` row (proving the exclusion, not mere universe
non-membership) — `tests/test_registry_lifecycle.py::test_nr7_breakout_excluded_from_live_selection_after_demotion`.
`startup_summary()` now reports **0 approved, 1 shadow** — zero registry entries currently
authorize live capital. `scheduler/jobs.py::run_phase5_bull_watch()` (the NR7-specific monitor)
verified to degrade safely to a no-op, no crash. Shadow/research tracking is untouched and
functional (nothing in `forward_testing`/`research_runs`/the gatekeeper reads registry `status` as
a precondition). Fixed three pre-existing test fixtures (`test_registry_loader.py` ×2,
`test_nr7_live_pipeline_e2e.py`) that had fragile, undetected coupling to the real production
`_LIFECYCLE_DEBT` key matching their synthetic entries — now self-contained with their own valid
evidence. Full suite: **2418 passed**, same 3 pre-existing unrelated failures.

This closes T7 invariant #10. **No other strategies changed; the Evidence Model was not weakened;
no new capital tier was created; no exception was invented; the promotion architecture was not
redesigned** — only `NR7_BULL`'s own status, in response to its own evidence.

---

## 11. T7 status — COMPLETE

All 10 invariants are addressed. #1-9 by §2-9; #10 by §10 (owner decision executed, D-029). Two
non-blocking engineering decisions remain open by explicit instruction, not oversight: §4.3
(premover EOD — no `strategy_fn` concept to admit through the Registry schema; already dormant,
mode='off') and §4.4 (`wf_edge` dual-use as both research data and a legacy production
authorization channel — documented, deliberately unchanged pending its own governance call).
Neither affects any strategy currently reaching live execution: as of D-029, `registry/
edge_registry.yaml` has **zero APPROVED entries** — no strategy in this system currently holds
Registry-authorized live-capital status.
