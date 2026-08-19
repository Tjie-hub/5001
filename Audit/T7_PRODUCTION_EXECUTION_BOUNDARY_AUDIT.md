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

## 7. Remaining T7 scope (not started this session)

Invariants #1-6 and #8 are addressed by §2-6 above (modulo the two open decisions in §4.3/§4.4).
#5 (exceptions explicit/governed) is partial — counter-trend/momentum/premover are each now
explicitly classified, not silently ungoverned. #7 (execution-model compatibility — bar
convention, entry delay, price, timestamp, scan frequency, partial-bar handling between research
backtest and production scan), #9 (admission auditability — every production admission
explainable after the fact: strategy/edge/evidence/registry entry/admission decision/execution
model/when), and #10 (capital/promotion semantics vs. the authoritative SSOT docs) are in
progress / not yet investigated.
