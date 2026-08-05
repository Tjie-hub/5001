# AF-2 WP4 — Agent Firm Call Graph Report

Companion to `Audit/AF2_WP4_IMPLEMENTATION_REPORT.md`. Every path in the repository that
constructs a `SignalCandidate` and hands it to the Agent Firm (`evaluate()`/`evaluate_staged()`),
before and after this work package.

---

## Full Call Graph (after WP4)

```
scheduler/scanner.py::scheduled_multi_strategy_scan()   [intraday, every scan tick]
  ├─ reset_market_ctx()            (legacy, inert no-op)
  ├─ reset_batch_context()         (real Tier 1 batch cache flush)
  ├─ run_agent_firm_gate(...)                                          ── WP2 ── unchanged
  │    ├─ build_candidate_context(conn, ticker, date_str, market_risk_score=...)  [per candidate]
  │    ├─ SignalCandidate(**base, **ctx)
  │    └─ firm.evaluate_staged(candidates)
  └─ rank_bear_watchlist_and_notify(...)                                ── WP2 ── unchanged
       ├─ build_candidate_context(conn, ticker, date_str, market_risk_score=...)  [per candidate]
       ├─ SignalCandidate(**base, **ctx)
       └─ firm.evaluate_staged(candidates)

scheduler/jobs.py::run_premarket_firm_scan()            [08:35 WIB, daily]        ── WP4 ── FIXED
  ├─ get_market_risk_for_circuit_breaker()   (single call, reused for context + Telegram summary)
  ├─ reset_market_ctx()             (own cycle boundary)
  ├─ reset_batch_context()          (own cycle boundary)
  ├─ build_candidate_context(conn, ticker, date_str, market_risk_score=...)  [per candidate]
  ├─ SignalCandidate(**base, **ctx)
  └─ firm.evaluate_staged(candidates)

scheduler/jobs.py::run_eod_trade_plan()                 [16:40 WIB, daily]        ── WP4 ── FIXED
  ├─ get_market_risk_for_circuit_breaker()
  ├─ reset_market_ctx()             (own cycle boundary)
  ├─ reset_batch_context()          (own cycle boundary)
  ├─ build_candidate_context(conn, ticker, date_str, market_risk_score=...)  [per candidate]
  ├─ SignalCandidate(**base, **ctx)
  └─ firm.evaluate_staged(candidates)

monitor.py::_agent_confirms_exit()                      [intraday, every ~30 min, per R3/R4 trade]  ── WP4 ── FIXED
  ├─ reset_market_ctx()             (own cycle boundary)
  ├─ reset_batch_context()          (own cycle boundary)
  ├─ build_candidate_context(conn, ticker, today)  [single candidate]
  ├─ SignalCandidate(**base, **ctx)
  └─ firm.evaluate([_candidate])                         (note: evaluate(), not evaluate_staged() — full pipeline, not the 2-stage pre-scan; unchanged by this WP)

scheduler/scanner.py::scan_momentum_signals()            [single-strategy scan path]
  └─ reset_market_ctx()             (vestigial — this function never calls evaluate()/evaluate_staged() at all; confirmed by direct read)

scripts/probe_actual_http_concurrency.py                [developer diagnostic, manual invocation only]
  ├─ reset_market_ctx()             (blocks its removal — see Technical Debt Report)
  ├─ SignalCandidate(...)           (no Tier 1 context — by design, this script measures HTTP
  │                                  concurrency, not decision quality; out of WP4's mandate)
  └─ firm.evaluate_staged(candidates, client=<instrumented router>)

scripts/replay_firm_offline_run.py                      [developer diagnostic, manual invocation only]
  ├─ reset_market_ctx()             (blocks its removal — see Technical Debt Report)
  ├─ SignalCandidate(...)           (no Tier 1 context — same reasoning as above)
  └─ firm.evaluate_staged(candidates)
```

---

## Before WP4 (for comparison)

Identical graph, except:

- `scheduler/jobs.py::run_premarket_firm_scan()` — candidate construction had **no context step at
  all**; `SignalCandidate(...)` was built directly from watchlist row fields, every Tier 1 field
  defaulting to `None`.
- `scheduler/jobs.py::run_eod_trade_plan()` — same gap.
- `monitor.py::_agent_confirms_exit()` — same gap.

Everything else in the graph (scanner.py's two sites, the two dev scripts, `scan_momentum_signals`'s
inert call) was already in its current shape before this work package.

---

## Downstream Consumption (unchanged by this WP — confirmed, not re-verified from scratch)

Every `SignalCandidate` reaching `firm.evaluate()`/`evaluate_staged()`, regardless of which call
site constructed it, flows through the identical WP3-migrated evaluation graph:

```
evaluate_staged() / evaluate()
  └─ per candidate:
       ├─ technical.run(candidate, client)   reads candidate.technical
       ├─ flow.run(candidate, client)         reads candidate.flow
       ├─ regime.run(candidate, client)       reads candidate.regime_context
       ├─ news.run(candidate, client)         reads candidate.news (+ live web search)
       ├─ bull.run(candidate, analyst_results, client)   (analyst outputs only)
       ├─ bear.run(candidate, analyst_results, bull_result, client)   (analyst + bull outputs only)
       └─ risk.run(candidate, all_results, client)
            reads candidate.portfolio, candidate.risk_limits (WP3)
            + apply_guardrails() (deterministic, post-LLM, keyed on analyst verdict strings)
```

This part of the graph required **no change** in WP4 — it was already correct per WP3. The WP4 fix
is entirely on the **producer** side (three more construction sites now populate the fields this
graph already knew how to read); the consumer side is untouched, exactly as the mission brief's "no
architecture expansion" constraint requires.

---

## Verification That No Other Construction Site Exists

Repository-wide grep for `SignalCandidate(` and its aliased form `_SC(` across every `*.py` file
(excluding `.winvenv/`) found exactly the files enumerated above, plus test files (which construct
candidates directly as fixtures — not part of the live call graph) and `engine/agent_firm/schemas.py`
(the type definition itself) and `engine/agent_firm_context.py` (the context-builder module, which
does not itself construct `SignalCandidate` — it returns a dict of context objects for callers to
spread into one). No construction site was missed.
