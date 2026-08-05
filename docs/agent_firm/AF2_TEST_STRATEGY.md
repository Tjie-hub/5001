# AF-2 — Test Strategy

**Date:** 2026-07-29
**Basis:** `AF2_IMPLEMENTATION_READINESS.md`, `AF2_WORK_PACKAGE_SEQUENCE.md`.
**Principle:** every deterministic function this remediation introduces must be unit-testable without an
LLM call — this is not a new requirement invented for this document, it is `guardrails.py`'s own
existing, stated design principle (`guardrails.py:1-14`) extended to every new pure function this work
introduces. Every behavior-changing package additionally needs a shadow-mode validation path before
`enforce`.

---

## Existing Test Infrastructure This Strategy Reuses

**`scripts/replay_firm_offline_run.py` already exists and is the correct tool for shadow-mode
validation — verified by direct read, not assumed.** It runs the real production path
(`engine.agent_firm.firm.evaluate_staged()`, a real `ProviderRouter`, the real DB) with a distinct
`scan_time` marker (`"REPLAY-<timestamp>"`) so rows it writes to `agent_decisions`/`agent_traces`/
`provider_events` are identifiable and separately cleanable from real scheduler activity. This is
precisely the mechanism WP4/WP5's shadow-mode comparisons need — **AF-2 should extend this script**,
not build new tooling, for:
- Replaying a fixed candidate set through the pre-guardrail and post-guardrail decision logic and diffing
  the two (WP4).
- Replaying the same set through the LLM-derived `size_hint` (pre-WP5) and `resolve_size_hint()`
  (post-WP5) and logging both without switching which one `scanner.py` actually consumes (WP5's
  mandatory shadow period per `AF1_REMEDIATION_PLAN.md`).

**`engine/agent_firm/config.py`'s existing `FIRM_ENABLED`/`get_enforce()`/`set_mode(enabled, enforce)`
pattern is the concrete mechanism for WP4/WP5's shadow-mode flag** — verified present today, already the
established convention (mirroring `AUTH_MODE`/`EDGE_SCORE_MODE`/`SECTORS_APP_MODE`'s repo-wide
`off`/`shadow`/`enforce` pattern per `CLAUDE.md`). Recommend a scoped extension rather than a bespoke new
env var: e.g. `AGENT_FIRM_GUARDRAILS_MODE` (`off`/`shadow`/`enforce`, defaulting to `shadow` on first
deploy) gating whether `apply_guardrails`'s new WP4 vetoes and `resolve_size_hint()`'s WP5 output are
*logged* (`shadow`) or *consumed* (`enforce`) by `scanner.py`. This was previously stated only as "ship
in shadow mode first" with no named mechanism (Gap G7) — this document closes that gap with a concrete
flag name and default.

---

## Per-Work-Package Test Plan

### WP0a-WP0d (blocker resolutions)

Not code — no test required. Verification is that `AF2_IMPLEMENTATION_READINESS.md`'s Parts 2-5 each
have a recorded, dated resolution before any WP1+ work starts, the same append-only-decision discipline
`docs/roadmap/DECISION_LOG.md` already uses elsewhere in this repository.

### WP1 — `TechnicalContext`

- **Unit tests:** direct tests of whichever producer WP0b selects (`engine/indicators.py`'s functions or
  `engine/technicals.py::tech_direction()`) against fixed OHLCV fixtures with known expected output — no
  LLM, no mock provider needed for the computation itself.
- **Integration test:** `tests/agent_firm/test_technical.py` updated to assert the agent's prompt payload
  contains `TechnicalContext`'s fields, using a mock `FirmLLMProvider` (existing pattern in this test
  file) — verifies wiring, not model quality.
- **Regression check (per B1):** if WP0b resolves to reusing `engine/technicals.py::tech_direction()`,
  add one test asserting `TechnicalContext`'s directional read and `engine/veto.py`'s own
  `tech_direction` read agree for the same ticker/date — a direct, automated check against the exact
  disagreement risk B1 named, not just a design-time assertion.

### WP2 — `FlowContext`

- **Unit tests:** `net_foreign_14d`'s `SUM()` and `trend_7d`'s rolling-sign function against fixed
  `broker_flow`/`stockbit_flow_bars` fixtures.
- **Regression check (required, not optional):** `tests/agent_firm/test_analytics.py` must be updated in
  the *same* change as the taxonomy passthrough (per `AF2_WORK_PACKAGE_SEQUENCE.md` WP2's hidden
  prerequisite) — a test asserting `analytics.py::agent_agreement()` correctly matches whatever taxonomy
  `FlowContext.verdict` actually carries, run end-to-end through `_is_aligned()`, not just at the
  `FlowContext` construction boundary.

### WP3 — `RegimeContext`

- **Unit tests:** the new/reused regime function against fixed `wf_scores`/`daily_screen` fixtures
  spanning each of the five `regime_call` values, including the `UNKNOWN` fallback path.
- **Regression check (per B1, same shape as WP1):** one test asserting `RegimeContext.regime_call` and
  `engine/edge_enrich.py::market_regime()`'s read agree for the same date, if WP0b resolves to wrapping
  the existing function; if WP0b resolves to keeping them independent, this test instead asserts the
  *disagreement is surfaced*, not silently possible.

### WP4 — `ConsensusContext` + Guardrail Vetoes

- **Unit tests:** `build_consensus_summary()` and the three new `apply_guardrails` veto paths
  (`negative_count` threshold, `already_open_position`, `entries_blocked`), each independently, against
  constructed `AgentResult` fixtures — pure functions, no LLM, matching `guardrails.py`'s existing test
  pattern (`tests/agent_firm/test_risk_v2.py` already tests `apply_guardrails` this way).
- **Signature-change regression suite:** `tests/agent_firm/test_firm.py`, `test_firm_v2.py`,
  `test_risk.py`, `test_risk_v2.py` — all four confirmed (by grep) to call `risk.run()` or construct its
  fixtures directly — must be updated for the new `context`/`PortfolioContext` parameter **in the same
  commit** as the signature change. Acceptance: full green run of `pytest tests/agent_firm/ -q` with zero
  skips, not just the new tests passing in isolation.
- **Shadow-mode validation:** `scripts/replay_firm_offline_run.py`, extended to run a representative
  historical candidate set through both pre-WP4 and post-WP4 `apply_guardrails`, diffing which decisions
  change from `approve` to `veto`. Reviewed by a human before `AGENT_FIRM_GUARDRAILS_MODE=enforce`.

### WP8 — `MarketContext.ihsg_trend` + `market_risk_score`

- **Unit tests:** none beyond WP1's (same producer function, applied to IHSG's OHLCV instead of a
  per-ticker series) — no new computation, only new wiring.
- **Integration test:** assert `MarketContext.ihsg_trend`/`market_risk_score` are present and non-null in
  the assembled context at least once per scan cycle — a presence check, since this closes a "computed
  but never delivered" dead-data gap, and a regression here would silently recreate exactly that gap.

### WP9 — `ExecutionContext`

- **Unit tests:** `get_execution_context()` (the new extraction from `open_trade()`) against fixed
  capital/`paper_trades` fixtures.
- **Critical regression test, required before merge:** a before/after comparison of `open_trade()`'s
  actual sizing output (lots, `capital_used`, error/skip conditions) across a representative set of
  historical trade scenarios, run against both the pre-extraction and post-extraction code paths,
  asserting byte-for-byte identical results. This directly targets the "Medium risk from the refactor
  itself" flagged in `AF2_WORK_PACKAGE_SEQUENCE.md` — the goal is proving the extraction changed nothing
  observable about `open_trade()`, not just that `ExecutionContext` reads sensible-looking numbers.

### WP5 — Deterministic `size_hint`

- **Unit tests:** `resolve_size_hint()` against every combination of `size_tier` × representative
  `ConsensusContext`/`ExecutionContext` states, asserting the output is always in `[0.0, 1.5]`. **Per Gap
  G8** (`hypothesis` is not a current dependency, verified absent from `requirements.txt`): restate the
  original "property-style test" acceptance criterion as **exhaustive boundary-case testing** — three
  `size_tier` values × boundary values for `negative_count`/`aligned_bullish`/`aggregate_open_exposure_pct`
  (zero, mid-range, saturated) is a small, enumerable matrix, achievable without adding a new test
  dependency. If AF-2 separately decides property-based testing is worth the new dependency, that is an
  explicit decision to make then, not an assumption baked into this document.
- **B2 regression test (required, not optional):** a test exercising both `EDGE_SCORE_MODE=enforce` and
  `AGENT_FIRM_ENABLED=true` simultaneously, asserting the documented WP0d precedence rule actually holds
  end-to-end in `scanner.py`'s pipeline — this is the one test in this entire suite that would have
  caught Blocker B2 before it shipped the first time, and its absence today is itself evidence for why
  this check belongs in the required suite, not the optional one.
- **Shadow-mode validation:** same `replay_firm_offline_run.py` extension as WP4, logging both the old
  LLM-derived `size_hint` and `resolve_size_hint()`'s output side by side for a full evaluation cycle
  before `scanner.py:1609`'s `_size_mult` source is switched.

### WP6, WP7

- WP6: one rejection test (`AgentDecision(size_hint=2.0)` raises).
- WP7: no test — documentation only; verification is a read-through, not a test run.

---

## Summary — What "Green" Means Before AF-2 Is Called Complete

1. `pytest tests/agent_firm/ -q` fully green, including the four updated signature-change test files
   (WP4) — zero skips, zero xfails introduced to paper over an incomplete migration.
2. Every new pure function (`build_consensus_summary`, `resolve_size_hint`, `get_execution_context`, and
   whichever WP0b selects for regime/technical) has direct unit test coverage with no LLM/provider mock
   in the call path.
3. The two B1/B2 regression tests named above (regime/technical agreement, `EDGE_SCORE_MODE` +
   `AGENT_FIRM_ENABLED` precedence) exist and pass — these are the tests that specifically encode this
   certification's two most severe findings as permanent, automated guarantees, not just as document text.
4. At least one full shadow-mode cycle (via the extended `replay_firm_offline_run.py`) has been reviewed
   by a human for both WP4 and WP5 before either flips to `enforce`.
5. WP9's before/after `open_trade()` regression test passes with byte-for-byte identical output on the
   historical scenario set.
