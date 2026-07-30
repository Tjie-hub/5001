# Evidence — P0.E2.S3.T1

**Date:** 2026-07-30
**Trace tag:** [L-1]
**Branch:** implemented directly on `master` (single-session, operator-directed continuation — see Time-gate note)

## Verification (before coding)

- `docs/PLAN-001-Implementation-Master-Plan.md` §3, line 83: "T1: `/metrics`
  column fix `[L-1]`" — confirms this is the correct next task.
- `docs/EXEC-STATUS.md` §7 "Next up" listed `P0.E2.S3.T1–T4` as the
  remaining group, in order, with T1 first — confirmed still current.
- `git log --oneline -5` showed `P0.E2.S2.T2` (`76c1802`) as `HEAD`, no
  intervening work; `git status` showed no `p0/e2-s3-t1-*` branch and no
  stray uncommitted work touching `app.py` or `market_risk_log`. No
  discrepancy found.
- PLAN-001's `[L-1]` tag alone doesn't say *what* the column bug is —
  traced to the original audit that produced these severity codes:
  `Audit/PRODUCTION_ENGINE_AUDIT_2026-07-22.md` line 326: "**L-1:**
  `/metrics` `idx_market_risk_score` queries `risk_score`/`computed_at`;
  the table's columns are `score`/`created_at` → the gauge is permanently
  NaN (`app.py:154`)." — read before writing any code, per the "capture
  its exact wording" and "understand the intent" instructions.

## Root cause

`app.py`'s `/metrics` route (Prometheus endpoint) ran
`SELECT risk_score FROM market_risk_log ORDER BY computed_at DESC LIMIT 1`.
`market_risk_log`'s real schema (`engine/risk_alert.py`'s `_ensure_table`,
the sole owner of this table's DDL) has columns `score` and `created_at`
— not `risk_score`/`computed_at`. Every invocation of this query raised
`sqlite3.OperationalError: no such column`, silently caught by `app.py`'s
own `_q()` helper (`try: ... except Exception: return None`, used
uniformly by every `/metrics` query so one bad column never 500s the
whole endpoint) — so `idx_market_risk_score` rendered as Prometheus `NaN`
unconditionally, regardless of how much real risk-alert data existed.

**Literal wording vs. root cause:** identical here — PLAN-001's "column
fix" and the audit's precise column-name mismatch are the same fact; no
divergence to reconcile or document beyond citing the audit source above.

## Fix

One line, `app.py`:
```diff
- risk_score      = _q(conn, "SELECT risk_score FROM market_risk_log ORDER BY computed_at DESC LIMIT 1")
+ risk_score      = _q(conn, "SELECT score FROM market_risk_log ORDER BY created_at DESC LIMIT 1")
```
The Python variable name `risk_score` (left of `=`) is unrelated to the
bug and left unchanged — only the SQL column names, which must match
`engine/risk_alert.py`'s actual `CREATE TABLE`, were wrong.

**Options considered for *where* to fix it:**
1. Fix the inline SQL string in place (chosen) — the query has exactly one
   call site; `market_risk_log` has no other read helper to fix instead.
2. Extract a shared `get_latest_risk_score(conn)` helper in
   `engine/risk_alert.py` (which already owns this table's DDL) so future
   readers can't reintroduce a column-name mismatch by hand-writing SQL
   again — considered and rejected: this is the *only* place in the
   codebase that reads `market_risk_log` for "latest score" (confirmed by
   `grep -n "market_risk_log" -r .`; the other three read/write sites in
   `engine/risk_alert.py` and `engine/trade_plan.py` serve different
   queries — unsent-alerts and today's-tier lookups respectively, not
   "latest score"). Introducing a one-caller helper is exactly the
   "unrelated cleanup or opportunistic refactoring" this task's rules
   forbid; a trivial fix stays trivial.

## Test-first verification (issue reproduced before the fix)

New `tests/test_metrics_endpoint.py`, written and run **before** touching
`app.py`:
```
wsl.exe -d Ubuntu -- bash -lc 'cd /home/tjies/workspace/projects/5001 && ./.venv/bin/python -m pytest -q tests/test_metrics_endpoint.py -v'
```
Pre-fix result — the regression case failed exactly as the audit
predicted:
```
tests/test_metrics_endpoint.py::test_metrics_returns_200 PASSED
tests/test_metrics_endpoint.py::test_idx_market_risk_score_is_nan_when_table_empty PASSED
tests/test_metrics_endpoint.py::test_idx_market_risk_score_reflects_most_recent_score FAILED
  AssertionError: assert 'NaN' == '71.0'
1 failed, 2 passed in 0.58s
```
After the one-line fix, same command:
```
tests/test_metrics_endpoint.py ...                                       [100%]
3 passed in 0.53s
```

3 tests:
- `test_metrics_returns_200` — endpoint doesn't 500 (control).
- `test_idx_market_risk_score_is_nan_when_table_empty` — no rows → `NaN`
  is *correct* (kept as a control so the fix isn't mistaken for "always
  return a number").
- `test_idx_market_risk_score_reflects_most_recent_score` — the
  regression case: two rows inserted using the table's real
  `score`/`created_at` columns; asserts the gauge equals the
  most-recently-`created_at` row's `score` (`71.0`), not `NaN` and not the
  higher-scored-but-older row (`42.5`) — proves `ORDER BY created_at DESC`
  is correct, not just that *a* column exists.

## Real-DB verification (not just the synthetic test DB)

This sandbox's actual `data/walkforward.db` has no `market_risk_log` table
yet (never populated in this environment) — confirmed the fixed query
still degrades gracefully (200, `NaN`, no crash) against the real,
currently-empty-of-this-table production DB, via a direct
`app.test_client()` call outside pytest:
```
GET /metrics -> 200
idx_market_risk_score NaN
```
This is the same code path `_q()`'s generic exception handling already
covers (`OperationalError: no such table`) — confirms the fix doesn't
regress the "table doesn't exist yet" case, only fixes the "table exists
with real data" case the audit flagged.

## Regression run (full suite)

```
wsl.exe -d Ubuntu -- bash -lc 'cd /home/tjies/workspace/projects/5001 && export PATH="$HOME/.local/node/bin:$PATH" && ./.venv/bin/python -m pytest -q'
```
```
1283 passed, 1 skipped in 24.18s
```
Baseline (post-`P0.E2.S2.T2`) was 1,280 passed/1 skipped/0 failed; +3 from
`test_metrics_endpoint.py`. 0 regressions, 0 failures. Targeted subset run
first: `tests/test_metrics_endpoint.py tests/test_health_endpoint.py
tests/test_chart_routes.py tests/test_scheduler_risk_alert_registration.py`
(the tests most directly adjacent to `app.py` and `market_risk_log`) — 22
passed, run before the full suite.

## Gate-script output

```
wsl.exe -d Ubuntu -- bash -lc 'cd /home/tjies/workspace/projects/5001 && export PATH="$HOME/.local/node/bin:$PATH" && ./.venv/bin/python scripts/pre_merge_gate.py'
```
```
[PASS] QG-1 full test suite — 1283 passed, 1 skipped
[PASS] QG-4 schema drift — N/A (Phase 1 deliverable)
[PASS] QG-9 grep-audits — AN-8: 37 clean, 0 violations, 0 allowlisted (unaffected — no scheduler-job surface touched)
[PASS] QG-5 evidence presence — 8 done-task card(s) checked, all have evidence

GATE: PASS
```

## Decision entries filed

None. No `§8`-classifiable event — a one-line SQL column-name correction
with a single, unambiguous root cause already fully specified by the
original audit; no design choice among materially different options
(beyond the trivial "fix in place vs. extract a helper" call, which is
documented above under "Fix" rather than as a numbered decision, matching
the same threshold used for `P0.E2.S2.T2`).

## Self-review (EXEC-001 §3.1 step 3, checklist §5.1/§5.2/§5.4)

- Diff does only what the task card says: one SQL string, one new test
  file. No drive-by changes — the other 7 `_q()` calls in `/metrics`, the
  `_gauge`/`_q` helper functions themselves, and every other route in
  `app.py` are untouched.
- No FROZEN surface touched; Phase 0 stays legacy-only.
- No new dependency (ER-12).
- No forward-phase work smuggled in (ER-2) — did not extract a shared
  risk-score-reading helper, did not touch `engine/risk_alert.py`'s table
  ownership, did not add new metrics.
- Task exists verbatim in PLAN-001 §3 (`P0.E2.S3.T1 ... [L-1]`).

## Cold review (EXEC-001 §4)

**Performed 2026-07-30, as an independent reviewer pass**, against the
operator's explicit checklist:

- **Hidden edge cases:** a `NULL` `score` value (if ever inserted) still
  correctly renders `NaN`, not a crash or a false `0` — `_q()` returns
  `row[0]` which would be `None`, and `_gauge()` already handles `None`
  as `NaN`. A tie on `created_at` (two rows with the identical timestamp)
  has SQLite-unspecified tie-break order — pre-existing ambiguity in the
  query's *intent*, not introduced or worsened by this column-name fix,
  and out of scope for a trivial L-1 correction.
- **Regressions:** full suite (1,283/1,280 baseline) and gate both clean;
  grep confirmed `risk_score`/`computed_at` (the wrong names) had exactly
  one call site in the entire live codebase (`app.py:156`) before this
  fix — nothing else depended on the broken query text or its
  always-`NaN` output.
- **Duplicate logic:** none introduced; the "extract a shared helper"
  alternative was considered and rejected (see "Fix" above) specifically
  to avoid manufacturing duplication where a single inline query was
  already sufficient and correct once the column names matched the table.
- **Unintended behavioral changes:** the gauge now reports real values
  once `market_risk_log` has rows, instead of always `NaN` — this is the
  intended fix, not a side effect; no other code path reads or depends on
  this gauge's value (Prometheus scraping is external to this repo).
- **Documentation consistency:** `Audit/PRODUCTION_ENGINE_AUDIT_2026-07-22.md`
  is the only doc mentioning `idx_market_risk_score`, and it is an
  explicitly read-only, point-in-time audit record ("Audit performed
  read-only; no code, schema, or data was modified" — its own closing
  line) describing repository state as of 2026-07-22, not a live tracker;
  it is not edited by this or any other P0 task (same treatment as every
  prior task this cycle) — `EXEC-STATUS.md`/`GATE.md` are the live
  record and are updated below.
- **Platform compatibility:** pure SQL string change; no OS/platform-
  specific code involved.
- **Maintenance implications:** none negative — this is strictly simpler
  than before (correct column names matching the one canonical schema
  definition in `engine/risk_alert.py`); no new abstraction, no new
  surface for future drift beyond what already existed.

**0 findings.** No code changes required as a result of this review.

**Time-gate note:** as with every P0 task this cycle, this cold review
occurred in the same continuous session as the implementation; operator
explicitly directed continuation.
