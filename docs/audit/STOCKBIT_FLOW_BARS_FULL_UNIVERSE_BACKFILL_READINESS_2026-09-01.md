# stockbit_flow_bars Full-Universe Backfill — Readiness Report

**Date:** 2026-09-01 · **Author:** Claude Code research session · **Status:** DIAGNOSIS ONLY —
no backfill executed. Read-only throughout; no DB writes, no code changes, no commits, no PIT/
membership changes, no hypotheses/backtests run.

**Mission context:** the IDX80-scoped Stockbit mission (144/144 k=7-realized broad days) and
broker-flow PIT coverage (31,178/31,178 PIT ticker-days) are both COMPLETE. This report assesses
whether the *same* collector/backfill machinery can safely be pointed at the full ~900-ticker
`stockbit_flow_bars` universe to close the historical gap the IDX80-only mission never touched.

This report consolidates and extends two prior read-only sessions in this conversation (an
affected-set closure across the full universe, and a root-cause diagnostic of the dropout/recovery
boundary) with new investigation specific to backfill readiness: the existing orchestrator/runner
machinery, exact exclusion criteria, precise workload, and a single live vendor probe.

---

## A. Exact full-universe population and affected-set accounting

`stockbit_flow_bars` has ever held rows for **900** distinct tickers. Classified against the
signature (data before 2025-05-15, zero coverage through the gap, data after):

| Bucket | Count | Disposition |
|---|---:|---|
| Continuously covered (no gap) — the blue-chip watchlist, `data/fetcher.py::IDX80` | 79 | Already complete — **exclude**, nothing to backfill |
| Identical full dropout (before + after data, zero inside the window) | 774 | **Backfill target** |
| Started during/after the gap, listed inside the gap window itself | 13 | No pre-listing history is possible — **exclude** (already ~100% covered since their own listing date) |
| Started during/after the gap, but actually long-listed (OHLCV since 2021) with **zero** flow-bar rows even before 2025-05-15 | **2** (PPRO, WMPP) | Not caught by the "identical dropout" signature because they had no *pre-gap* flow either — **add to the backfill target**, with a floor of 2025-01-02 instead of 2025-05-15 |
| "Stopped before the gap, never resumed" (had pre-gap data, none after) | 32 | Re-investigated this session (new finding, not in the prior report): every one is `idx_tickers.status='active'` with OHLCV rows through 2026-08-28, but **average and max OHLCV volume are exactly 0** for all 84 trading days in the post-recovery window (2026-04-23→08-31) — these are trading-suspended stocks, not a collection defect. **Exclude from the active target list** (their vendor requests would legitimately return empty; including them wastes rate-limited calls for zero yield, though would not corrupt anything if included) |

**Recommended backfill target: 774 + 2 = 776 tickers.** 900 − 79 (already complete) − 32 (suspended,
nothing to fetch) − 13 (no history possible before their own listing) = 776.

---

## B. Root cause of the historical dropout

Carried forward from this session's prior root-cause diagnostic, unchanged:

- **2025-05-15 narrowing (dropout start): UNKNOWN, no evidence recoverable.** This repository's
  entire git history begins **2026-04-18** (`5705715`, the first commit) — five months after the
  dropout started. No commit, log, or config predating that survives to explain the trigger.
- **2026-04-20→23 recovery: CONFIRMED.** Git shows a locally-hardcoded, module-level `TICKERS`
  list in `stockbit_fetcher.py` (commented `"# 77 tickers (LQ45 + IDX80)"`, visible at commits
  `9ec439c`/`6ac9aa1`, both 2026-04-23) being the sole fallback whenever the `flow` subcommand ran
  with no arguments — exactly how the live crontab invokes it (`stockbit_fetcher.py flow --token
  ...`, no `--cat`). Commit `bca0ca2` (2026-04-28) atomically replaces this with `data/fetcher.py`'s
  `IDX30/LQ45/IDX80/CATEGORIES` hierarchy + `load_all_tickers()` (`idx_tickers WHERE
  status='active'`) + `_run_flow_cmd()`'s `get_tickers(category or "ALL")` default. The 79-name
  `IDX80` constant is byte-identical to the "no gap" set (A above); 7 of the 9 tickers unique to the
  older 77-list are exactly the 7 tickers that recovered 2 days early (2026-04-20 vs. the bulk's
  2026-04-22) — direct, exact evidence the hardcoded-list mechanism is what determined coverage,
  not vendor behavior or rate limiting.
- Independently corroborated by three pre-existing, first-party sources: `tools/check_broker_flow_coverage.py:40-46`
  (names commit `6ac9aa1` as broker_flow's introduction, verified by a prior session via `git log
  -S`), `scheduler/jobs.py:117` ("the 2026-04-22/23 zero-ticker gap"), and `docs/cycle_phases_strong12.md:180`
  ("There is no flow before April 2026") — a differently-motivated document stating the same fact.

---

## C. Is the post-2026-04-22 residual shortfall the same mechanism?

**No — confirmed as a distinct, non-defect mechanism, not "unfinished backfill."**

The live daily cron (`logs/cron_stockbit_flow.log`, 2026-08-31 run) shows the collector completing
its full run every day: `"Flow category: ALL — 958 tickers"` ... `"DONE: 958/958 success"`. Yet only
829/958 tickers got a `stockbit_flow_bars` row that date. Reconciled directly from the same log: 132
tickers logged `NetLot=+0 NetVal=+0` (an empty tradebook response) vs. 129 tickers actually missing
from `stockbit_flow_bars` that date — a near-exact match. `run_flow()`'s write path inserts a
`stockbit_flow` summary row unconditionally, but only inserts `stockbit_flow_bars` rows when the
response actually contains bars; a genuinely zero-liquidity day produces no bars and correctly
produces no row. Directly tested and **refuted**: an alphabetical-truncation/timeout hypothesis (a
long job not finishing) — missing tickers on sampled dates span the full alphabet (index 2–955 of
958), not the tail.

**Implication for the backfill:** this ceiling is a property of genuine trading activity, not
something a backfill "fixes." Item I below sets expectations accordingly.

---

## D. Exact backfill date range and estimated workload

**Range:** `2025-01-02` → `2026-04-28` (exclusive upper bound) — this is the runner's own
already-documented default (`tools/backfill_flow_bars.py`'s module docstring, "Day-1 launch
contract"), and it is safe to use unmodified for the full population: cells already covered
(774 tickers' 2025-01-02→05-14 stretch, ~98% populated already) are skipped for free by the
resumable completion predicate (`tools/flow_bars_gap.py::bars_cell_complete`) — no manual
per-ticker date-range carving is needed.

**Workload (upper bound, before completion-skip):**

| Component | Tickers | Trading days | Cells |
|---|---:|---:|---:|
| Core dropout population | 774 | 224 (2025-05-15→2026-04-21) | 173,376 |
| PPRO / WMPP (no pre-gap flow either) | 2 | 305 (2025-01-02→2026-04-21) | 610 |
| **Total candidate cells** | 776 | — | **~174,000** |

A small number of these (the 7 early-recovering tickers' 2026-04-20/21 cells) are likely already
complete and will be skipped instantly; not worth adjusting the estimate for.

**Runtime estimate**, at the previously-measured live pace of ~1.6–2.5s/ticker
(`tools/backfill_flow_bars.py::RATE_DELAY=1.6s` plus real network latency, consistent with the
2026-07-26 feasibility study's own measured range):

- **~77–121 hours of cumulative vendor-call time.**
- Via the bare runner's 5-hour (`HARD_CAP_S`) budget-per-invocation design: **~19–20 separate
  invocations**, each resumable, each safely stoppable mid-window.
- Via the orchestrator's supervised **one-trading-date-at-a-time** execution: ~774 tickers ×
  ~2s ≈ 26 minutes per date × 224 dates ≈ **~96 hours** if run back-to-back with no gaps between
  dates (in practice: spread across multiple sessions/days — see H).

---

## E. Vendor feasibility / rate-limit assessment

**Historical feasibility: CONFIRMED**, via a prior, dated, first-party live-HTTP study already in
this repo (`docs/archive/flow_audit/STOCKBIT_FLOW_BACKFILL_FEASIBILITY.md`, 2026-07-26): the same
tradebook endpoint `fetch_flow()`/`run_flow()` use accepts a historical `date=` parameter and
returns real minute-level data back to a hard, evidence-bisected cutoff of **2025-01-02** (nothing
before that — HTTP 200 with an empty payload, which looks like success but isn't). The entire
776-ticker target range falls inside that recoverable window. That study only sampled two
already-always-covered names (BBCA, TLKM); this session's live probe (below) targets a genuinely
affected ticker instead.

**Live vendor probe performed this session (exactly one call, fully reported):**

1. `sf.verify_token(token)` against the live Stockbit API, using the token stored in `.stockbit_token`
   (mode 600, last refreshed 2026-09-01 08:41 per file mtime, well-formed JWT shape) → **returned
   `False`**. The stored token is not currently usable.
2. Given the invalid token, the planned second call — `fetch_flow(token, "GJTL", "2025-09-15")`, a
   ticker from the affected population, chosen because the July study never tested an affected name
   — was **not attempted** (would have failed on auth, not tested anything new). No further vendor
   calls were made. No DB writes were made or attempted at any point (`fetch_flow()`/`verify_token()`
   perform no writes; `run_flow()`/`_write()` were never called).

**Conclusion:** this is not a feasibility blocker — token staleness is routine and already handled
by the runner's own `ensure_valid_token()` / the existing `auto_token.py` refresh cron at actual
execution time. But it does mean **feasibility for this specific moment is not freshly re-confirmed
live**; the conclusion rests on the 5-week-old study plus this session's confirmed-invalid-token
finding, not a fresh successful fetch. A fresh token check should be the first step of any actual
execution, which the runner already does automatically (`ensure_valid_token()`, `EXIT_AUTH=2` on
failure).

**Rate limits:** the runner already implements a `1.6s` inter-request delay and a documented `429`
backoff ladder (`20+40+60+80s`) inside `fetch_flow`, plus a `SUSTAINED_FAIL_LIMIT=25`
consecutive-failure abort. No changes needed for full-universe scope — these are universe-size-
agnostic.

---

## F. Exact existing command/mechanism for the recovery

**No new code is required.** Two existing, already-committed tools cover this exactly:

**Recommended — the supervised orchestrator** (adds concurrency guard, per-date timeout/stall
detection, and DB re-verification the bare runner lacks):

```
tools/agent_backfill_idx80.py \
  --action execute \
  --cat ALL --allow-non-idx80 \
  --yes-run-vendor-backfill \
  --date-from 2025-01-02 --date-to 2026-04-28
```

`--cat ALL` and `--allow-non-idx80` are both required together — the orchestrator refuses any
non-IDX80 category without the explicit override by design (`MISSION_CATEGORY = "IDX80"`,
`OVERRIDE_FLAG = "--allow-non-idx80"`), which is exactly why the prior mission never touched the
other 774+2 tickers even though the underlying runner always defaulted to ALL.

**Alternative — the bare runner directly** (its own documented default is already full-universe):

```
scripts/cron_wrap.sh backfill_flow_bars_day1 timeout 18120 \
  venv/bin/python3 tools/backfill_flow_bars.py \
  --date-from 2025-01-02 --date-to 2026-04-28 --budget-s 17400
```

(`--cat` defaults to `ALL` already — no flag needed.) Less safe: no concurrency guard beyond what's
built into the runner, no per-date supervision, no DB re-verification of the claimed result.

In neither case pass `--release-fixture` — `2025-04-14` is a deliberately frozen regression fixture
reserved for a specific sign-off test and must stay untouched by this backfill.

---

## G. Safety / checkpoint / idempotency assessment

| Property | Assessment |
|---|---|
| Enumerate all ~900 tickers | Yes — `--cat ALL` → `load_all_tickers()` → `idx_tickers WHERE status='active'` (958 rows; the runner's own `get_tickers()` fallback degrades to the 79-name IDX80 list only on a load failure, never silently truncates otherwise) |
| Fetch historical dates | Yes — `fetch_flow(token, ticker, date)` accepts an explicit `date=` param, proven live (2026-07-26 study) |
| Skip already-complete cells | Yes — `bars_cell_complete()` (bars exist OR a `stockbit_flow` summary row proves a genuinely empty session), DB-state-derived, not a cursor |
| Retry failures | Yes — in-request 429 backoff ladder; per-cell soft failures increment a counter without aborting until `SUSTAINED_FAIL_LIMIT=25` |
| Resume after interruption | Yes — resume is recomputed from DB state on every invocation; no external checkpoint file to lose or corrupt |
| Avoid duplicate/corrupt writes | Yes — `INSERT OR REPLACE` keyed on the table's own primary key `(ticker, trade_date, bar_time)`; re-running a completed cell is a no-op overwrite of identical data |
| Respect vendor rate limits | Yes — `1.6s` delay + 429 backoff, unchanged by universe size |
| Avoid a second concurrent writer | Yes, via the **orchestrator** only — `fcntl` lock + `/proc` scan (bare runner has no such guard) |
| Touch only `stockbit_flow`/`stockbit_flow_bars` | Confirmed by reading `_write()`/`run_flow()` — no other table is ever written by this path; `idx80_membership_history`/`idx80_reconstitution_periods`/PIT tables are never referenced |
| A prior known defect in this exact machinery | **Yes — already fixed.** 2026-08-20/21: an earlier completion check tested `stockbit_flow` (summary) instead of `stockbit_flow_bars`, silently skipping 9,341 cells with real activity but no bars. Fixed via `tools/flow_bars_gap.py`'s bars-vs-empty-session predicate (regression-tested). 2026-08-27: 5 further correctness bugs in the orchestrator (`--probe` cost/crash/exit-code bugs, a concurrency-guard gap, an `ALL`-path fallback gap) found and fixed, committed at `9b6e380` — the current top-of-branch commit |

---

## H. Recommended execution plan

1. **Confirm a valid token before starting** — this session's probe found the stored token invalid;
   run `stockbit_fetcher.py`'s normal auth path (or let the orchestrator's `ensure_valid_token()`
   handle it) before launching anything long-running.
2. **Use the orchestrator**, not the bare runner, for its concurrency guard and re-verification.
3. **Batch by trading date, not by one long invocation** — the orchestrator already does this
   (`--action execute` runs one date at a time with `--date-timeout-s`/`--no-progress-timeout-s`
   guards); do not bypass this by driving the bare runner with a single multi-month window.
4. **Schedule around the existing 18:30 WIB daily flow cron** — run the backfill in windows that
   don't overlap that job (both eventually touch `stockbit_flow`/`stockbit_flow_bars`; the
   orchestrator's concurrency guard will block a true overlap, but scheduling around it avoids
   losing backfill throughput to a blocked wait).
5. **Cooldown between sessions** — given the ~96–120 hour total estimate, plan for multiple
   multi-hour sessions across several days rather than one continuous run; this also gives natural
   checkpoints to sanity-check partial results before continuing.
6. **Never pass `--release-fixture`.**
7. **Spot-check after each session** — re-run the affected-set signature check (Step 1's method)
   on a sample of dates to confirm coverage is climbing as expected, before continuing the next
   session.

---

## I. Expected before/after coverage metrics

| | Before | After (projected) |
|---|---|---|
| 774-ticker core population, 2025-05-15→2026-04-21 window | 0% (0/173,376 cells) | **~80–90%**, matching the same liquidity-driven ceiling already observed for this exact population post-recovery (item C) — **not 100%, and that is expected, not a shortfall** |
| PPRO / WMPP, 2025-01-02→2026-04-21 | 0% | Similarly ~80–90%, consistent with their peers |
| Full 900-ticker universe, full 2025-01-02→2026-04-28 window | Currently ~86% overall gap-affected (Step 1 finding) | Converges toward the same ~80–90% ceiling the always-covered 79 and the post-recovery collection already demonstrate — i.e., the dataset becomes **uniformly characterized** rather than split into a covered-79 / uncovered-774 population |

Pre-registering this expectation matters: a completed backfill landing at ~85% should be read as
**success**, not as an incomplete run — re-litigating that after the fact against a false 100%
expectation would misdiagnose a healthy result as a failure.

---

## J. Go/no-go recommendation

**Qualified GO — conditional on separate, explicit authorization to execute (per mission
instructions, not granted by this report) and on:**

1. Obtaining a fresh valid token first (today's stored token failed live verification this session).
2. Using `tools/agent_backfill_idx80.py --action execute --cat ALL --allow-non-idx80
   --yes-run-vendor-backfill --date-from 2025-01-02 --date-to 2026-04-28` (or the equivalent bare
   runner invocation only if the orchestrator is unavailable for some reason).
3. Never passing `--release-fixture`.
4. Scheduling in multiple bounded sessions with cooldowns, not one continuous run, per H.
5. Accepting the ~80–90% ceiling in I as the correct success criterion, not 100%.
6. Excluding the 32 confirmed-suspended tickers and the 13 tickers with no possible pre-listing
   history from the active target list (both are safe to include and will self-resolve to empty via
   existing completion logic if left in, but excluding them avoids ~10,000+ wasted rate-limited
   calls with zero possible yield).

No architectural change, no new tooling, and no research-methodology change is required — the
existing, already-hardened machinery (post the 2026-08-20/21 and 2026-08-27 fixes) is sufficient
as-is. The only gap between "ready" and "safe to run" is the operator explicitly overriding the
orchestrator's IDX80-only default, which is a deliberate design safeguard working exactly as
intended, not a defect to route around casually.

**This report stops here. No backfill was executed. Awaiting separate authorization.**
