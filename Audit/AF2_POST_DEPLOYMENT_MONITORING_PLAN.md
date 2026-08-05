# AF-2 — Post-Deployment Monitoring Plan

**Date:** 2026-07-29
**Companion to:** `Audit/AF2_PRODUCTION_VALIDATION_REPORT.md`.
**Existing infrastructure this builds on:** `agent_decisions`/`agent_traces`/`provider_events`
tables (already written on every evaluation, per `engine/agent_firm/firm.py::_persist()` and
`engine/agent_firm/providers/events.py`); `engine/agent_firm/analytics.py`'s `cohort_summary()`/
`agent_agreement()`/`decision_log()` functions, already wired into `routes/backtest.py`;
`docs/OPERATIONS.md`'s existing `provider_events` SQL-query convention for failover health checks.
This plan proposes **queries and thresholds**, following that established convention, rather than
a new dashboarding technology — no new infrastructure is required to start tracking every metric
below; some are one `SELECT` away today.

None of the metrics below existed as a named, tracked target before this validation pass — this is
this session's own contribution, per the deliverable's explicit request for monitoring
recommendations.

---

## 1. Candidate Throughput

**What:** count of `SignalCandidate`s reaching `evaluate()`/`evaluate_staged()` per job/day.

```sql
SELECT DATE(scan_time) AS day, strategy, COUNT(*) AS candidates
FROM agent_decisions
GROUP BY 1, 2 ORDER BY 1 DESC;
```

**Why it matters:** a silent drop in candidates for `premarket`/`eod`/the intraday `multi`/`vol_weighted`
etc. strategies would indicate an upstream break (watchlist build failure, dedup-guard false-positive,
edge-veto stage over-filtering) before it ever reaches the Agent Firm — this table is the first place
such a break becomes visible.

**Suggested alert:** candidates for `strategy IN ('premarket','eod')` dropping to 0 on a trading day
(the dedup guard already logs this, but a dashboard panel makes the trend visible, not just the
single-day log line).

## 2. Context Completeness

**What:** fraction of candidates whose Tier-1 fields are non-default (i.e., real data was found, not
a fail-soft fallback).

```sql
-- Requires no new persistence — context objects are ephemeral per ADR-AF-002, so this metric
-- must be derived from agent_traces.output (each specialist's own JSON output already reflects
-- whether it had real context to reason about — e.g. technical's "insufficient data" reasoning
-- string, or regime_call staying "UNKNOWN").
SELECT DATE(ad.scan_time) AS day, at.role,
       SUM(CASE WHEN at.output LIKE '%insufficient%' OR at.output LIKE '%UNKNOWN%' THEN 1 ELSE 0 END)
         AS degraded_count,
       COUNT(*) AS total
FROM agent_traces at JOIN agent_decisions ad ON at.decision_id = ad.id
GROUP BY 1, 2 ORDER BY 1 DESC;
```

**Why it matters:** this is the single most direct signal for whether the ADR-AF-002 migration is
actually delivering context in production — a rising `degraded_count` ratio at any of the five
construction sites would mean context-building is silently failing soft more often than expected
(e.g., a table renamed, a ticker consistently missing OHLCV), which is exactly the kind of thing
`Audit/AF2_WP4_IMPLEMENTATION_REPORT.md` flagged as the pre-WP4 state for three of those five sites.

**Suggested alert:** `degraded_count / total > 20%` sustained over a rolling 3-day window for any
single `strategy`.

## 3. Decision Distribution

**What:** approve/veto/degraded/bypassed counts and confidence/size_hint distribution, per strategy.

```sql
SELECT DATE(scan_time) AS day, strategy, decision, COUNT(*) AS n,
       AVG(confidence) AS avg_confidence, AVG(size_hint) AS avg_size_hint
FROM agent_decisions GROUP BY 1, 2, 3 ORDER BY 1 DESC;
```

**Why it matters:** this is the metric `Audit/AF2_WP4_FINAL_CERTIFICATION.md` and
`Audit/AF2_BEHAVIORAL_REGRESSION_REPORT.md` both explicitly call out as expected to shift for
`premarket`/`eod`/exit-review traffic — this query is how that expected shift gets confirmed against
real data rather than left as a documented prediction. Track before/after the WP4 deploy date
specifically for these three call sites.

## 4. Specialist Failures

**What:** per-role failure rate (`agent_traces.status = 'failed'`), and error message clustering.

```sql
SELECT role, COUNT(*) AS failures, GROUP_CONCAT(DISTINCT substr(error, 1, 60)) AS sample_errors
FROM agent_traces WHERE status = 'failed'
  AND created_at >= datetime('now', '-7 days')
GROUP BY role ORDER BY failures DESC;
```

**Why it matters:** `_run_risk()` maps a failed Risk trace straight to `decision='degraded'` —
elevated Risk-role failures directly reduce the fraction of candidates the firm can actually decide
on, silently pushing more traffic to fallback/deterministic ranking (`tp.fallback_rank()` in
`run_eod_trade_plan()`).

**Suggested alert:** any single role's failure rate > 10% over a rolling 24h window (mirrors the
existing `SCHEDULER_JOB_ERROR_COOLDOWN_S` pattern's spirit — rate-limited, trend-based, not
one-failure-fires).

## 5. Cache Hit Rate (Batch Context)

**What:** `engine.agent_firm_context._batch_ctx` population count vs. `build_candidate_context()` call
count, per cycle.

**Current gap:** no persistence exists for this today (the cache is an in-memory, per-process
global, by design — ephemeral per ADR-AF-002). **Recommended minimal addition** (not performed in
this validation pass, per the "no architecture expansion" rule — proposed as a future, separately
reviewed instrumentation change): a lightweight counter/log line in `get_batch_context()` distinguishing
a cache-fill call from a cache-hit call, surfaced via existing structured logging
(`utils/logging_config.py`), not a new table. Until then, cache effectiveness is validated
structurally (per `Audit/AF2_RUNTIME_PERFORMANCE_REPORT.md` §3 — confirmed working) rather than
monitored continuously in production.

## 6. Decision Latency

**What:** wall-clock time from candidate construction to decision persistence.

```sql
SELECT DATE(scan_time) AS day, strategy, AVG(duration_s) AS avg_duration_s,
       MAX(duration_s) AS max_duration_s
FROM agent_decisions GROUP BY 1, 2 ORDER BY 1 DESC;
```

**Why it matters:** `duration_s` is already persisted per decision — this is a zero-new-instrumentation
metric. Compare against `engine/agent_firm/smoke.py`'s own `_MAX_DURATION_S = 150.0` budget as the
reference ceiling for a full 7-agent real-provider run; a sustained upward trend would indicate
provider latency degradation or circuit-breaker/failover churn (cross-reference with `provider_events`,
per `docs/OPERATIONS.md`'s existing query).

## 7. Risk Veto Rate

**What:** veto rate specifically attributable to each of `risk_v2.md`'s named conditions.

```sql
SELECT DATE(scan_time) AS day, strategy,
       SUM(CASE WHEN decision='veto' AND rationale LIKE '%already open%' THEN 1 ELSE 0 END) AS veto_open_position,
       SUM(CASE WHEN decision='veto' AND rationale LIKE '%entries blocked%' THEN 1 ELSE 0 END) AS veto_circuit_breaker,
       SUM(CASE WHEN decision='veto' AND rationale LIKE '%guardrail%' THEN 1 ELSE 0 END) AS veto_guardrail_override,
       SUM(CASE WHEN decision='veto' THEN 1 ELSE 0 END) AS veto_total,
       COUNT(*) AS total
FROM agent_decisions GROUP BY 1, 2 ORDER BY 1 DESC;
```

**Why it matters:** breaking the veto rate down by *reason* (not just a raw percentage) is exactly
what lets an operator distinguish "the Risk Manager is correctly enforcing the no-doubling-up rule
more often now that it can see open positions" (expected, per the Behavioral Regression Report) from
"something is wrong and everything is getting vetoed" (a real regression) — an aggregate veto-rate
number alone cannot make that distinction.

## 8. Paper-Trade Acceptance Rate

**What:** of candidates the Agent Firm approved (or size-hinted), what fraction actually result in
`paper_trade.open_trade()` succeeding (vs. skipped for trend-filter/price-missing/error reasons).

```sql
-- Requires joining agent_decisions to paper_trades by ticker+date, same join analytics.py's
-- own cohort_summary()/decision_log() already use.
SELECT DATE(ad.scan_time) AS day,
       SUM(CASE WHEN ad.decision='approve' THEN 1 ELSE 0 END) AS approved,
       SUM(CASE WHEN ad.decision='approve' AND pt.id IS NOT NULL THEN 1 ELSE 0 END) AS opened
FROM agent_decisions ad
LEFT JOIN paper_trades pt ON ad.ticker = pt.ticker AND DATE(ad.scan_time) = pt.entry_date
WHERE ad.strategy NOT IN ('premarket', 'eod', 'watchlist')  -- these three are informational/reference only, see §1 of the Production Validation Report
GROUP BY 1 ORDER BY 1 DESC;
```

**Why it matters:** an approved candidate not converting to a paper trade is not necessarily wrong
(trend filter, missing price, shadow-mode non-filtering are all legitimate reasons — see the
Production Validation Report's four-pattern table), but a sustained, unexplained drop in this ratio
would be a genuine signal worth investigating — this metric did not exist as a named target before
this plan.

## 9. Unexpected Fail-Soft Activations

**What:** count of context-build failures (the outer try/except around the whole context-population
step at each of the five construction sites — `Audit/AF2_WP4_CALL_GRAPH_REPORT.md`), distinct from
per-field `_safe()` degradations (§2 above covers those). This is the coarser, rarer failure mode —
a broken DB connection or an unreadable table entirely, not just one ticker missing one row.

**Current gap:** these currently only reach a application log line (`logging.warning(...)` at each
call site), not a queryable table. **Recommended:** grep-based log monitoring
(`grep "context build error (fail-open"` across the five call sites' log lines, which all share this
exact phrase deliberately — confirmed by direct source read this session) as an interim measure;
promoting this to a structured, queryable event (mirroring `provider_events`'s existing shape) is a
reasonable future enhancement, not performed here (schema change, out of this validation's mandate).

**Why it matters:** this is the "something is actually broken, not just one ticker's data missing"
signal — distinguishing it from §2's routine per-field degradation is exactly the "unexpected" in
this metric's name; a spike here (as opposed to a steady low background rate) is the strongest single
indicator that a construction site's own `build_candidate_context()` call is failing wholesale (e.g.,
`DB_PATH` misconfigured, a table dropped) rather than the pipeline simply lacking data for a specific
thin ticker.

---

## Recommended Dashboard Layout (if/when a UI is built over `routes/backtest.py`'s existing
`analytics.py` wiring)

1. **Top row:** candidate throughput (§1) + decision distribution (§3) side by side, both by
   `strategy`, both trending over the last 30 days.
2. **Second row:** context completeness (§2) + specialist failure rate (§4), both as a percentage
   trend line with the alert thresholds above drawn as reference lines.
3. **Third row:** decision latency (§6) + risk veto rate breakdown (§7).
4. **Fourth row:** paper-trade acceptance rate (§8), filtered to the auto-entry-relevant strategies
   only (excluding the three informational/reference-only call sites, per the Production Validation
   Report's four-pattern table).
5. **Sidebar / alert panel:** cache hit rate (§5, once instrumented) and unexpected fail-soft log
   count (§9, once promoted to a structured event) — lower-frequency operational health checks, not
   daily-trend metrics.

This layout is a recommendation for future work, not a deliverable of this validation pass — no UI
code was written or is proposed to be written here, per the "no new Agent Firm features" rule.
