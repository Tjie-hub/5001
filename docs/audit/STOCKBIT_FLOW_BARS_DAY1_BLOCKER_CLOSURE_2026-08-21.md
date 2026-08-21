# stockbit_flow_bars Day-1 Blocker Closure (B1–B4) — 2026-08-21

**Authority:** operator tasking *"RESEARCH EDGE — CLOSE THE FINAL DAY-1 BLOCKERS"* (ZCode
implementation session, 09:30–10:00 WIB). Correctness state at entry: GREEN (predicate,
13/13 tests, 2025-01-06 idempotency, 2025-01-07 discrimination/resume, DB integrity — see
`STOCKBIT_FLOW_BARS_BACKFILL_CORRECTNESS_FIX_2026-08-21.md`). **Day 1 remains NOT LAUNCHED.**
No HYP-PM-0002 / OFI / cont_k / power work performed; unrelated dirty-tree changes untouched.

---

## B1 — Production runner location: CLOSED

**Change:** the validated runner moved from gitignored `scratchpad/backfill_flow_5liquid.py`
to tracked **`tools/backfill_flow_bars.py`** (new), following the `tools/backfill_broker_flow_gap.py`
convention (argparse, repo-root log file, `data.db.connect` for ALL connections). The
scratchpad file is now a thin **in-process delegating shim** (env contract preserved:
`FLOW_TICKERS` incl. legacy comma lists, `FLOW_DATE_FROM/TO`, `BUDGET_S`, `--probe`) — no two
competing runners exist. Behaviour preserved: completion via `tools.flow_bars_gap.bars_cell_complete`,
identical `_write` path, per-cell durable commits, budget-in-cell-loop, checkpoint on exit.

- **git:** staged + committed (server `ops/hardening-2026-07-10`; same commit locally);
  `git archive HEAD` (what `scripts/release.sh` ships) now includes the runner, the predicate
  module, and both test files.
- **cron contract:** recognized as `backfill_flow_bars_day1` job name through `scripts/cron_wrap.sh`.
- **raw `sqlite3.connect` fixed:** the old `gap_dates()` opened its own raw connection; the
  tool routes every connection through `data.db.connect` (busy_timeout + WAL, the repo's one
  SQLite entry point). No raw `sqlite3.connect` remains in the production path.
- **Tests:** `tests/test_backfill_flow_bars.py` — 14 new cases; **27/27 pass** with the
  predicate suite (local `.winvenv` and server venv). Live server checks: targeted-fixture
  refusal (rc=5), barrier stop (rc=0, zero fetches), dry-run plan (2025-01-02: 888 incomplete
  cells), shim delegation (rc=0).
- **Pre-existing failures (not this change):** 5 tests in `tests/test_historical_replay_operational.py`
  fail with `AttributeError: module 'engine.agent_firm' does not have the attribute 'firm'` —
  a monkeypatch-target mismatch in other agents' uncommitted `engine/` work; no import
  relationship to the backfill path. 40/40 fetcher/flow/backfill-related tests pass.

## B2 — Failure signalling / monitoring: CLOSED

**Exit codes** (all nonzero paths page the operator via cron_wrap's Telegram alert):

| Code | Meaning |
|---|---|
| 0 | success — including a **planned** budget stop (work remains; rerun resumes) |
| 2 | authentication failure (no valid token at launch, or refresh failed mid-run — the old runner exited 0 here) |
| 3 | sustained fetch failure (25 consecutive errors ⇒ vendor outage / hard 429 wall) |
| 4 | database/write failure (`sqlite3.Error` on fetch-path or `_write`) |
| 5 | run explicitly targets the frozen fixture without `--release-fixture` |

Every abort path emits the PASS END + CHECKPOINT lines before exiting. **Launch contract is
`scripts/cron_wrap.sh`** (existing per-job logging, nonzero-rc Telegram alert with secret
redaction) — NOT bare `nohup`. No new monitoring infrastructure built.

**Monitoring mapping (existing machinery only):**

| Requirement | Mechanism |
|---|---|
| Process-death alert | job runs under `timeout 18120` inside cron_wrap → kill/OOM/timeout yields nonzero rc → Telegram alert (`EXIT ... rc=` also logged) |
| Stall detection | same `timeout` backstop (a wedged process is reaped at 5h02m → alert); per-cell `requests` timeout=15 and the 429 ladder cannot hang indefinitely; PASS END/CHECKPOINT lines timestamp the log |
| Authentication failure alert | exit 2 → cron_wrap alert |
| 429/error handling | in-cell backoff ladder (20/40/60/80s) + exit 3 on 25 consecutive failures → alert |
| DB/write failure alert | exit 4 → cron_wrap alert; `busy_timeout=30000` via `data.db.connect` |

The APScheduler heartbeat (`scripts/check_scheduler_heartbeat.py`, */10 cron) monitors the
app scheduler and is intentionally NOT duplicated for this job: the backfill is a
cron-invoked bounded process, for which cron_wrap + `timeout` is the established pattern.

## B3 — 5-hour safety margin: CLOSED (structural)

Old margin (60 s) could be exceeded by one worst-case in-flight cell:
429 Retry-After ladder **20+40+60+80 s** plus up to **4 × 15 s** request timeouts = **260 s**.

- `WORST_CASE_CELL_S = 260` (documented derivation), `CELL_MARGIN_S = 300` (> worst case).
- `effective_budget()` clamps any requested budget to `HARD_CAP_S = 5 * 3600`.
- New cells stop starting at `elapsed + 300 > BUDGET_S`; a cell started at the last permitted
  instant finishes by `(BUDGET_S − 300) + 260 = BUDGET_S − 40 < 5 h` — the guarantee is
  arithmetic, not luck. (Deliberately tiny test budgets get a reduced margin and a bounded
  ≤260 s overshoot that can never approach the 5 h constraint.)
- **Regression tests:** `test_margin_covers_documented_worst_case_cell`,
  `test_structural_5h_guarantee`, `test_budget_clamped_to_5h_hard_cap`,
  `test_budget_boundary_exact_edges`, `test_planned_budget_stop_is_success` — all green.

## B4 — Session-planning arithmetic: CORRECTED

Basis (unchanged, not silently altered): planning rate **≈1.91 s/cell** — the rate underlying
the established 142 h (868 names) / 157 h (958 names) continuous figures (= RATE_DELAY 1.6 s
+ ~0.3 s mean request). Measured bounds from real runs: 2.14–2.91 s/cell (2026-08-20/21
full-universe passes). Remaining work at 2026-08-21: **290,456 cells** (309-date window,
958-name universe, 5,566 cells complete).

Explicitly separated (the old "157 h / 6.5 days" line mixed the two regimes):

| Quantity | Planning basis (1.91 s/cell) | Measured bounds (2.14–2.91) |
|---|---|---|
| Theoretical continuous runtime | 290,456 × 1.91 s ≈ **154 h** (full-window variant: 157 h) | 173–235 h |
| Cells per ≤5 h session (budget 17,400 s − 300 margin) | 17,100 / 1.91 ≈ 8,956 | 5,876–7,991 |
| Expected number of ≤5 h sessions | ceil(290,456 / 8,956) = **33** | 37–50 |
| Calendar duration at 5 sessions/week (one session per weekday) | 33 / 5 ≈ **6.6 weeks (~46 days)** | 7.4–10 weeks (52–70 days) |

The 51–68 h estimate is NOT restored. Operator option (no assumption change): the code permits
multiple ≤5 h invocations per day; at 10 sessions/week the calendar span roughly halves
(~3.3–5 weeks) — an operating choice, not a re-estimate.

## Frozen regression fixture: 2025-04-14

Selected from the intact 2025 dates (defect cells present, zero bars): **2025-04-14** —
Monday, ohlcv 944 tickers, exactly **79 IDX80 activity-summary-no-bars cells, 0 bars, 0
zero-activity rows** (canonical discrimination profile; 109 such intact dates existed at
selection). Freeze enforcement in `tools/backfill_flow_bars.py`:

- any run whose entire work list is the fixture without `--release-fixture` → **rc=5 refusal**;
- otherwise the fixture is a **barrier**: dates before it process normally, the run stops
  with a planned-stop checkpoint *before* consuming it (verified live: rc=0, zero fetches);
- Day 1 therefore needs no special flag, and the fixture survives until the sign-off
  discrimination test deliberately runs it with `--release-fixture`.

## Token-boundary test — prepared for 2026-08-22 08:40 WIB

Current token (verified 2026-08-21 09:38 WIB): **exp = 2026-08-22T08:40:07 WIB** (24 h JWT,
refreshed daily by the 08:40 weekday `auto_token` cron). The boundary is natural — no forced
invalidation. Prepared one-shot: `scratchpad/token_boundary_test_20260822.sh` on the server
(to be run at ≥08:41), which:

1. records pre-state (token `exp`, mtime);
2. confirms the 08:40 `auto_token` cron exited rc=0 (`logs/cron_auto_token.log`);
3. runs a bounded production-path fetch through the real launch contract:
   `cron_wrap.sh backfill_flow_bars_tokentest timeout 600 ... --date-from 2025-01-08
   --date-to 2025-01-09 --budget-s 60` (~15–20 cells on an intact non-fixture date);
4. records post-state (advanced `exp`, fetched-cell count, exit code).

**Success criteria:** auto_token rc=0 AND token exp advanced (≥ +20 h) AND tokentest rc=0
with ≥1 cell fetched. **Failure criteria (any):** auto_token rc≠0, exp not advanced, or
tokentest rc=2 — in every failure case cron_wrap has already paged the operator. The test is
bounded (≤600 s hard, ~60 s budget), idempotent, touches no frozen fixture, and does not
launch Day 1. A workspace automation is scheduled for 2026-08-22 08:41 WIB to execute it
(and the command is recorded below for manual use).

## Day-1 launch command (RECORDED — NOT EXECUTED)

```bash
cd /home/tjiesar/idx-walkforward-5001
scripts/cron_wrap.sh backfill_flow_bars_day1 timeout 18120 \
  venv/bin/python3 tools/backfill_flow_bars.py \
  --date-from 2025-01-02 --date-to 2026-04-28 --budget-s 17400
```

Manual token-boundary test (2026-08-22, ≥08:41 WIB):
`bash scratchpad/token_boundary_test_20260822.sh`

**Remaining risks:** (1) commit is on `ops/hardening-2026-07-10` among 118 unrelated dirty
files — release.sh requires a clean tree, so the operator's pending merge/release decisions
still gate deployment; (2) token-boundary test not yet executed (scheduled 08:41 tomorrow);
(3) pre-existing `engine.agent_firm` test failures belong to other in-flight work.

**Lineage:** `STOCKBIT_FLOW_BARS_BACKFILL_CORRECTNESS_FIX_2026-08-21.md` ·
`STOCKBIT_FLOW_BARS_BACKFILL_STATE_2026-08-20.md` · `tools/backfill_flow_bars.py` ·
`tools/flow_bars_gap.py` · `tests/test_backfill_flow_bars.py`.
