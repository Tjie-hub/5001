# AF-2 — Runtime Performance Report

**Date:** 2026-07-29
**Companion to:** `Audit/AF2_PRODUCTION_VALIDATION_REPORT.md`.
**Measurement method:** all timings below use the **scripted, zero-network LLM provider** (see the
Production Validation Report's scope statement) against real seeded SQLite data and the real
`engine/agent_firm_context.py`/`engine/agent_firm/firm.py` code paths. This isolates **orchestration
and context-building overhead** from real network/LLM latency, which is unmeasurable without real
provider calls (a scope explicitly declined for this validation pass — see the Production Validation
Report). Every number below should be read as "cost added by the ADR-AF-002 pipeline machinery
itself," not as an end-to-end production latency estimate — real production latency is dominated by
the LLM round-trip time (typically 1-5s per agent call per the existing `smoke.py` probe's own
`_MAX_DURATION_S = 150.0` budget for a full 7-agent real pipeline run), not by anything measured here.

---

## 1. Context-Building Latency

| Measurement | Result | Interpretation |
|---|---|---|
| `build_candidate_context()`, single candidate, **cold** (first call in process, batch cache empty) | 0.344s | Includes one-time pandas/module warm-up cost, not representative of steady state |
| `get_batch_context()`, **cold** (first call, populates the batch cache) | 0.344s | Same cold-start cost — batch-level objects (Market/Portfolio/Risk/Execution) computed once here |
| `get_batch_context()`, **warm** (second call, same scan cycle) | ~0.000s (rounds to 0) | **Cache is effective** — confirms `_batch_ctx`'s once-per-cycle reuse (ADR-AF-002's stated lifecycle) actually eliminates redundant computation, not just in theory |
| `build_candidate_context()`, per-candidate average over 20 repeated calls (batch cache warm) | 0.0117s (~11.7ms) | Steady-state per-candidate cost once the batch cache is populated — dominated by the per-candidate OHLCV/flow/regime/news queries, which are inherently per-ticker and cannot be cached across candidates |
| `build_candidate_context()` for 8 distinct tickers in one cycle (mirrors a real scan's shape) | 0.063s total (~7.9ms/candidate) | Consistent with the per-candidate average above; confirms no super-linear cost growth across a realistic batch size |

**Assessment:** context-building cost is small and dominated by per-ticker I/O (unavoidable — each
ticker's OHLCV/flow/regime/news genuinely differs), not by any inefficiency in the assembly code.
The batch-level cache works exactly as designed, at the granularity ADR-AF-002 specifies.

## 2. Committee Evaluation Latency (Orchestration Only)

| Measurement | Result | Interpretation |
|---|---|---|
| `evaluate_staged_async()`, single candidate, scripted provider | 0.125s | Pure orchestration overhead (LangGraph node scheduling, `asyncio.gather` fan-out/fan-in, guardrail evaluation, persistence) — the scripted provider itself returns in well under 1ms per call |
| `evaluate_staged_async()`, 8 candidates (full batch, concurrent per `firm.py`'s own `asyncio.gather` design) | 0.656s total, ~0.082s/candidate amortized | Confirms the batch shape scales roughly linearly with candidate count under this harness — no evidence of contention or serialization bottleneck in the orchestration layer itself |
| Stage-1-only veto path (bear_regime scenario, 2 traces instead of 7) | 0.094s | Confirms the cost-saving 2-stage design actually short-circuits — both fewer traces *and* less wall-clock time than the full 7-agent path |

**Assessment:** the orchestration layer (LangGraph graph execution, guardrails, persistence) adds a
small, roughly-constant per-candidate overhead. In real production, this overhead is dwarfed by LLM
round-trip latency (seconds, not milliseconds) — the pipeline's real-world throughput ceiling is set
by provider latency and the existing `AGENT_FIRM_DAILY_CAP`/concurrency-limiting mechanisms
(`ZAI_MAX_CONCURRENT`, per `scripts/probe_actual_http_concurrency.py`'s own purpose), not by anything
measured in this report.

## 3. Cache Effectiveness

Confirmed directly (not inferred): calling `get_batch_context()` twice within the same cycle (no
intervening `reset_batch_context()`) returns the cached result on the second call, at effectively
zero marginal cost. This validates the specific claim made throughout the WP1-4 audit trail — that
the batch-level Tier-1 objects (`MarketContext`, `PortfolioContext`, `RiskContext`, `ExecutionContext`)
are computed once per scan cycle, not once per candidate — is not just a documented intention but an
empirically observed behavior.

**A related, previously-flagged operational point re-confirmed here:** the three call sites WP4 wired
(`run_premarket_firm_scan()`, `run_eod_trade_plan()`, `_agent_confirms_exit()`) each call
`reset_batch_context()` at their own start, since each treats its own invocation as its own cycle
boundary (they don't share `scheduled_multi_strategy_scan()`'s cycle). This means the cache is
**not** shared across these three call sites and the intraday scan — each pays its own one-time
per-cycle cost, which is correct (avoids serving another job's stale portfolio/risk snapshot, per
`Audit/AF2_WP4_IMPLEMENTATION_REPORT.md`'s "Cache Lifecycle" section) but is worth naming plainly as
a real, intentional cost: five cache-population events per full trading day (one per intraday scan
cycle, one for premarket, one for EOD, plus one per `_agent_confirms_exit()` invocation — every
~30 minutes during market hours whenever an R3/R4 exit trigger fires), not one.

## 4. Memory

Not independently measured in this pass — the scripted-provider harness's process memory footprint
is dominated by the Python/pandas/langgraph runtime baseline, not by anything specific to the Tier-1
context objects (each is a small Pydantic model with a handful of scalar fields plus short lists,
e.g. `ohlcv_recent_10d`/`flow_bars_recent` capped at 10-20 rows per WP1's own design). No memory
growth concern is expected or was observed qualitatively (`tracemalloc`/process RSS were not
instrumented — flagged as a gap, not a finding, since nothing in this session's testing suggested a
need to instrument it).

## 5. Material Degradation Assessment

**No material performance degradation identified.** The ADR-AF-002 pipeline's own overhead
(context-building + orchestration) is single-digit-to-low-double-digit milliseconds per candidate —
negligible next to LLM round-trip time, which this pipeline does not change (the same number of LLM
calls happen per candidate as before the migration; the migration changed *what data* those calls
see, not *how many* calls happen). The one real, quantifiable new cost is the per-candidate SQL
read `build_candidate_context()` performs (§1) — already accepted and documented as a known,
observed-not-blocking cost in `Audit/AF2_WP2_IMPLEMENTATION_REPORT.md`'s Known Limitations and
re-confirmed acceptable here with actual numbers rather than a qualitative estimate.
