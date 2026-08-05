# AF-2 WP3 — Regression Report (vs. WP2)

Companion to `Audit/AF2_WP3_IMPLEMENTATION_REPORT.md`. Scope: confirm this work package changed
*how* specialists receive input without changing *what* the pipeline decides, except for the one
explicitly-flagged Risk Manager gap closure.

## Behavior Preserved (verified by unchanged, passing tests)

- **`evaluate()`/`evaluate_staged()` public signatures and short-circuit behavior** — daily spend
  cap, disabled-firm bypass, and the full async pipeline all pass unchanged
  (`tests/agent_firm/test_firm.py`, `test_firm_v2.py`, all 3 test-cap/bypass tests still pass
  byte-for-byte against their original assertions).
- **Guardrail override logic** (`apply_guardrails()` downgrading approve→veto on bearish-flow
  contradiction or sub-floor confidence in a weak regime) — unmodified file, confirmed by
  `test_guardrail_overrides_llm_approve_to_veto` passing unchanged in `test_firm_v2.py`.
- **Every specialist's output JSON schema** — `verdict`/`conviction`/`key_levels` (technical),
  `flow_verdict`/`smart_money_signal`/`net_foreign_14d` (flow), `regime_call`/`sector_tailwind`/
  `macro_risk` (regime), `sentiment`/`catalyst`/`key_headline` (news), `decision`/`confidence`/
  `size_hint` (risk) — every field name and type is unchanged. This matters because `guardrails.py`,
  `analytics.py::_is_aligned()`, and `firm.py::_run_risk()` all pattern-match on these exact keys;
  none of them needed a change, and none were changed.
- **2-stage pre-scan veto logic** (`_is_both_bearish()`, Stage 1 technical+regime auto-veto) —
  unmodified; `_run_stage1()`'s two calls now omit the removed `ctx`/`db_path` arguments but read
  the same `candidate.technical`/`candidate.regime_context` any Stage 2 call would.
- **Persistence** (`agent_decisions`/`agent_traces` schema and insert logic) — `_persist()`
  unmodified.
- **LangGraph node ordering after `run_analysts`** — `run_bull → run_bear → run_risk → persist` is
  byte-for-byte unchanged; only the entry point moved from `build_context` to `run_analysts` (the
  removed node's sole purpose was feeding data nothing downstream of `run_analysts` ever consumed).

## Behavior Changed (one instance, explicitly flagged)

**Risk Manager can now actually veto on an open position / blocked entries.** Before this work
package, `risk_v2.md` instructed "Veto if ticker already has an open paper trade (no doubling up)"
and referenced "Current open paper trades" as an input, but `risk.run()` was never given open-trades
data — the instruction was structurally unenforceable. After this work package,
`candidate.portfolio.has_open_position(ticker)` and `candidate.risk_limits.entries_blocked` are
real inputs the Risk Manager prompt now references by name.

**Why this is not scope creep:** the decision rule itself is not new — it was already written into
`risk_v2.md` before this work package touched it. What changed is that the rule can now actually
fire. This is the direct, foreseeable consequence of "migrate consumption of Tier 1 context objects
already produced by WP2," applied to the one specialist (Risk) whose prompt already assumed data
that was never wired. No existing test asserted the old (undeliverable) behavior, so nothing needed
to be reconciled — but production behavior in `AGENT_FIRM_PROVIDER=zai|claude|auto` live traffic will
differ going forward: a candidate on a ticker with an existing open paper trade, or evaluated while
the drawdown circuit breaker is tripped, is now more likely to be vetoed than before. Operators
should watch `agent_decisions.decision` distribution for a shift toward more vetoes in exactly these
two conditions after this change ships; this is the intended fix, not an anomaly.

**Verified non-regressive for the default case:** every pre-existing test that calls `risk.run()`
without setting `candidate.portfolio`/`candidate.risk_limits` (i.e. every test written before this
work package) gets `PortfolioContext()`/`RiskContext()` defaults —
`already_open_position=False`, `entries_blocked=False` — so none of those tests' expected outcomes
changed. Confirmed: all of `test_risk.py`'s and `test_risk_v2.py`'s pre-existing assertions pass
unchanged.

## Test Count Reconciliation

WP2's reported full-suite baseline: **1549 passed, 44 failed, 9 errors**
(`pytest -q --ignore=tests/agent_firm/providers`).

This work package's re-run of the identical command: **1560 passed, 44 failed, 9 errors** — same 44
failures, same 9 errors, same files, same categories (Windows-local Node/Playwright/shell-script/env
issues catalogued in WP2's own report, re-verified present and unchanged by this work package). The
**+11 passed** is exactly the 11 new tests this work package added (3 in `test_technical.py`; 2 each
in `test_flow.py`, `test_regime.py`, `test_news.py`, `test_risk.py`) — not a change in any
pre-existing test's outcome.

## Explicitly Re-Verified Unaffected

- `tests/test_architecture_boundary.py`, `test_research_data_fence.py`, `test_db_centralization.py`,
  `tests/security/test_route_policy.py` — **13 passed**. This work package added no new production
  import of `research.*`, no new write to a research-owned table, and no new route.
- `tests/test_agent_firm_context_wiring.py` (WP2's own scanner-integration tests) — **passes
  unchanged** (once the documented Windows lazy-import ordering artifact is worked around by running
  `tests/agent_firm/` first in the same session — pre-existing, see Implementation Report). These
  tests mock `firm.evaluate_staged` entirely, so they are structurally insulated from any internal
  `firm.py`/agent change; their continued pass confirms WP2's producer-wiring contract (Tier 1
  context populated on `SignalCandidate` before `evaluate_staged()` is called) is untouched by this
  work package.
