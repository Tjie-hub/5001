# Full-Universe One-Day Data Pilot — Audit Report

**Date:** 2026-09-01 · **Pilot trading date:** 2026-08-31 · **Author:** Claude Code session ·
**Status:** TOOLING BUILT + VERIFIED + AUDITED. **The broker-flow full-universe fetch was NOT
executed this session** (deliberately deferred — see §9); every number below for stockbit flow
bars, daily OHLCV, ticks, and idx_tickers reflects real, already-collected production data, not a
fetch performed by this pilot. No PIT/membership changes, no hypotheses/backtests run, no schema
changes, no destructive operations. `git status` at the end of this session shows only new files
(this report, the new driver, its tests) — no existing production file was modified.

---

## 1. Exact one-day universe

**Pilot date: 2026-08-31** — the most recent fully settled IDX trading session as of 2026-09-01
(today is itself a trading day per `engine.calendar_filter.is_trading_day()`, but not yet settled;
`trading_calendar`, `bandar_detector`, and IHSG `ohlcv` all agree 2026-08-31 is the latest confirmed
session).

**Universe: 958 tickers** — `data.fetcher.load_all_tickers()` → `idx_tickers WHERE status='active'`
(confirmed live, not assumed). Fail-closed guard (§4) did not trip: 958 is far above the ~79-ticker
IDX80-fallback floor.

**Caveat found this session, not previously documented:** `idx_tickers` itself has not been
refreshed since **2026-04-27** (`last_checked` is a single value across all 972 rows; one manual
`status` edit on 2026-07-04 affected 14 rows and nothing else). `data/ticker_discovery.py`, the only
writer, has apparently never been run again since introduction. This means **"full universe" here
is "everything known as of 2026-04-27,"** not "everything currently listed" — any IDX listing added
after that date would be invisible to every pipeline that calls `load_all_tickers()`, silently, with
no error. This is a real gap distinct from the per-dataset coverage gaps below and is not something
this pilot fixes (rediscovery is a ~30–60 min separate operation, deliberately out of scope this
session per its own read-only "audit only" framing).

---

## 2–3. Datasets discovered and pipelines used

No new vendor integration was built. One new *driver* was written (item below) that calls an
existing, unmodified vendor function with a wider ticker list — everything else uses tooling that
already existed before this session.

| # | Dataset | Table(s) | Fetcher / pipeline | Universe scope (before this session) |
|---|---|---|---|---|
| 1 | Stockbit flow bars (intraday) | `stockbit_flow_bars`, `stockbit_flow` | `stockbit_fetcher.py::run_flow()` via live cron (18:30 WIB) or `tools/backfill_flow_bars.py` / `tools/agent_backfill_idx80.py` | **Already full-universe** — cron runs `flow` with no `--cat`, which has defaulted to `ALL` since commit `bca0ca2` (2026-04-28) |
| 2 | Daily OHLCV | `ohlcv` | `data/fetcher.py::fetch_all[_incremental]` (yfinance) + `screener/idx_scraper.py::save_ohlcv_to_db()` (Stockbit EOD, `is_final=1` authority) | Already full-universe (`load_all_tickers()`) |
| 3 | Broker flow + foreign flow (same table, `investor_type='Asing'` is the foreign slice) | `broker_flow`, `bandar_detector` | `stockbit_fetcher.py::fetch_broker_flow()` via `tools/backfill_broker_flow_idx80.py` | **IDX80-only, hardwired** (`idx_tickers WHERE in_idx80=1`) — no override existed |
| 4 | 1-minute ticks / intraday tradebook | `ticks` | `screener/idx_scraper.py` via live scheduler (5×/day + EOD) | Already full-universe; **no historical backfill capability exists at all** (no `date=` param) |
| 5 | Regime / market-state | *(computed, not stored)* | `engine.regime_filter.detect_regime()`, `engine.risk_score.compute_market_risk_score()` + its component functions (`engine.vpin`, `flow_filter`, `engine.breadth`, `engine.technicals`) | N/A — live computation over `ohlcv`/flow tables, zero writes; note `regime_profiles`/`regime_profile_cells` (the *research*-owned regime taxonomy) is keyed by strategy, not by date, and was correctly left untouched |
| 6 | IDX universe/membership | `idx_tickers` | `data/ticker_discovery.py` (manual, unscheduled) | Audited only, not refreshed (per this session's own decision, §1) |

**New this session:** `tools/backfill_broker_flow_full_universe.py` — a single-date, full-universe
driver for dataset #3. It imports `fetch_and_store_cell()`, `missing_cells()`, and
`canonical_trading_dates()` from the existing IDX80 runner/gap modules **unchanged** and calls them
with `data.fetcher.load_all_tickers()`'s roster instead of `idx80_universe()`. No vendor code, retry
logic, or write path was duplicated or modified. It adds: a fail-closed universe-size guard, a
trading-day guard, its own `fcntl` lock, and a `/proc`-scan concurrency check (reusing
`tools.agent_backfill_broker_flow_idx80.other_backfill_pids()`) against all four existing
broker/foreign-flow runner and orchestrator scripts. See its module docstring for the full design
rationale, including the one accepted asymmetry: the four existing tools are not retrofitted to
recognize *this* script's marker, since it is a manually-supervised one-off tool, not a scheduled
writer.

---

## 4–5. Execution results and per-dataset coverage (2026-08-31, full 958-ticker universe)

| Dataset | Expected | Attempted this session | Present (already, in production data) | Missing | Coverage | Full-session or windowed | Suitable for research? |
|---|---:|---|---:|---:|---:|---|---|
| Stockbit flow bars | 958 | *(audit only — already complete)* | 958 cell-complete (bars or confirmed-empty); 829 have actual bars | 0 | **100%** cell-complete; 86.5% bars-coverage (genuine zero-liquidity days, not a defect — see readiness report §C) | Full-session | Yes |
| Daily OHLCV | 958 | *(audit only — not re-fetched this session)* | 826 (`is_final=1`) | 132 | 86.2% | Full-session (EOD) | Yes, for the 826; the 132 need the reason classified before assuming "missing" (see §7) |
| Broker + foreign flow | 958 | **Dry-run planned only — no vendor calls made** | 824 (from earlier IDX80/PIT-scoped work, per the readiness report's "31,178/31,178 PIT ticker-days COMPLETE" mission context) | 134 | 86.0% pre-pilot | Full-session | Driver ready; real fetch **not yet run** |
| Ticks / intraday | 958 | *(audit only — cannot be fetched retroactively at all)* | 780 | 178 | 81.4% (81.3% on the prior trading day — typical, not anomalous) | Windowed (live session capture only) | Yes for the 780, but this ceiling is **permanent** for any past date |
| Regime / market-state | 1 (market-wide) | **Computed live, read-only** | 1/1 | 0 | 100% | Point-in-time snapshot | Yes — SIDEWAYS (`detect_regime`), risk score 25.3/GREEN, breadth NEUTRAL (49.0% advancing), accdist NEUTRAL (-0.252, dist-leaning), technicals label UPTREND (a distinct MA-crossover signal — it can legitimately disagree with `detect_regime`'s ADX-based read) |
| IDX universe/membership | — | Audited only | 958 active / 972 total | — | `in_idx30`=30, `in_lq45`=45, `in_idx80`=79 — **real values, not "never set"** (correcting an earlier same-session finding — see §8) but frozen since 2026-04-27 | — | Usable, with the frozen-since-April caveat in §1 |

No vendor calls at all were made for datasets #1, #2, #4, #5, #6 this session (all figures are
pre-existing production data, queried read-only). For #3, exactly the calls needed to plan (DB
reads) were made — zero HTTP calls to Stockbit.

---

## 6. Cross-dataset reconciliation (ticker-level, 2026-08-31)

```
FULL UNIVERSE (958)
  ├─ Stockbit flow bars:  958 cell-complete (100%)
  ├─ Daily OHLCV:         826 present  (132 missing)
  ├─ Broker/foreign flow: 824 present  (134 missing)
  └─ Ticks:               780 present  (178 missing)

Present in ALL FOUR ticker-level datasets: 779 / 958 (81.3%)
```

Ticker-level overlap (computed directly, not estimated):

- **The 132 OHLCV-missing tickers are a subset of the 178 ticks-missing tickers, and are exactly
  the intersection of all three gaps** (`broker_missing ∩ ohlcv_missing ∩ ticks_missing` = 132,
  identical to `ohlcv_missing` itself). This is one coherent cohort, not three independent failures:
  87 tickers with a clean one-trading-day-old bar (last seen 2026-08-28), 41 tickers stale ~6 weeks
  (matching known suspended/restructuring names — SRIL, WSKT), 4 other outliers. **Broker flow's 2
  extra missing tickers (134 vs 132) are the only genuinely unexplained delta** and were not chased
  further this session.
- **Ticks has an additional 46-ticker gap that is NOT explained by the above** — these 46 tickers
  *are* present in OHLCV (i.e., they traded and settled normally on 2026-08-31) but have zero rows
  in `ticks`. This is a real, ticks-pipeline-specific capture gap, separate from the
  suspension/staleness story, and is exactly why the ticks dataset (780) sits below OHLCV (826)
  even though ticks is "already full-universe" by design.
- No duplicate `(ticker, date[, time])` rows were found in any of `ohlcv`, `ticks`,
  `stockbit_flow_bars`, or `stockbit_flow` for 2026-08-31 (unique constraints hold empirically, not
  just by schema declaration).
- No impossible values, timestamp/date mismatches, or partial-pagination symptoms were found in any
  dataset for this date.
- **No discrepancy was auto-corrected.** All of the above is reported as found.

---

## 7. Failures and likely causes

- **132-ticker cohort missing from OHLCV/broker-flow/ticks:** most likely genuine trading
  suspension or a one-day settlement gap, **not a collector defect** — cross-checked against
  `idx_tickers` (still `status='active'`, `fail_count=0` for the blue-chip sample) and against
  OHLCV's own last-seen dates, which show a clean, coherent pattern (87 exactly one day stale, 41
  exactly ~6 weeks stale) rather than random scatter. Two of the 87 (BBMD, SAFE) even have a
  provisional 2026-09-01 row with nothing for 08-31 — a skipped pipeline day for those two
  specifically, worth a narrower follow-up, but not evidence of a universe-wide failure.
- **46-ticker ticks-only gap:** likely a genuine scraper capture miss (rate limiting, a transient
  vendor error during one of the intraday capture windows, or a ticker-specific tradebook-endpoint
  quirk) — this session did not root-cause it further; flagged as a remediation candidate (§C below)
  rather than diagnosed to completion.
- **idx_tickers staleness (127 days):** not a "failure" in the sense of a broken pipeline, but a
  silent, unbounded blind spot — no error is raised anywhere when a new listing is simply absent
  from the table.

---

## 8. Data-quality issues found (including one self-correction)

- **Correction to an earlier finding in this same session:** an initial pipeline-inventory pass
  concluded `in_idx30`/`in_lq45`/`in_idx80` "are never set by any production writer," based on a
  code-path grep. A direct data audit this session found real, plausible values (30/45/79) confined
  to active rows, consistent with every downstream reader. The code-path finding was correct in a
  narrower sense — `data/ticker_discovery.py` genuinely never writes those columns — but the
  conclusion drawn from it was wrong: the columns hold real data seeded out-of-band at initial load
  (~2026-04-27), just never refreshed since. This report treats the *frozen-since-April* framing as
  the accurate one, not "never populated."
- `idx_tickers.last_checked`/`updated_at` are effectively a single frozen snapshot, not a live
  freshness signal.
- The ticks dataset's 46-ticker OHLCV-present/ticks-absent gap (§6) is a genuine, previously
  unquantified data-quality issue in the live scraper, independent of the suspension cohort.

---

## 9. Did the full-universe one-day pilot pass?

**Partially — by explicit design, not by shortfall.** This session's own execution plan (confirmed
via the "verify everything first, execute in a follow-up step" instruction) deliberately built and
verified the one missing piece of tooling (the broker-flow full-universe driver: 16 new unit tests,
all passing; a real dry-run against the live 958-ticker/2026-08-31 window; the existing IDX80/
foreign-flow/stockbit-flow-bars orchestrator suites re-run and confirmed green, 220/220; the full
repo suite re-run, 2782/2784 passing with the 2 failures pre-existing and unrelated — both in
`tests/test_news_filter.py`, a file untouched by this work) **without spending real vendor-call time
or writing new rows**, per the authorization boundary set for this session.

What *is* proven, with real production data: stockbit flow bars, daily OHLCV, ticks, and the live
regime/risk signal are all already operating at full-universe scope today, and their actual
2026-08-31 coverage is now precisely measured and reconciled across datasets for the first time.
What is *not yet* proven end-to-end: an actual live vendor fetch through the new broker-flow driver
(only a dry-run/plan was executed).

---

## 10. Recommended next step

Execute the already-built, already-tested `tools/backfill_broker_flow_full_universe.py` for
2026-08-31 with `--yes-run-vendor-backfill` (134 planned cells, ≈134×1.5s ≈ 3–4 minutes of vendor
time at current rate limits) as the immediate next action — this is the one piece of this pilot that
was deliberately left unexecuted. After that, re-run the reconciliation query in §6 to confirm the
134→0 gap closes as expected, and only then consider this specific pilot fully executed.

---

## Critical decision gate

**A. Can we reliably fetch the complete research data stack for one full-universe trading day?**
Mostly yes, with one dataset structurally exempt. Stockbit flow bars: **yes, already proven in
production** (100% cell-complete daily since 2026-04-28). Daily OHLCV: **yes for current/recent
dates** (86.2% is a suspension/staleness ceiling, not a fetch-capability limit — the existing
`data/fetcher.py` incremental path could likely close most of the 87 one-day-gap tickers, untested
this session). Broker/foreign flow: **structurally yes, but not yet demonstrated live** — the driver
is built and dry-run-verified, real vendor execution is the deferred next step. Ticks: **no, not for
any past date** — this is a permanent limitation of the live-only scraper, not a gap that "fetching
more" can close.

**B. Which datasets are production-ready for a larger backfill?**
Stockbit flow bars only — and per the pre-existing readiness report
(`STOCKBIT_FLOW_BARS_FULL_UNIVERSE_BACKFILL_READINESS_2026-09-01.md`), it needs **no new tooling at
all**, just `tools/agent_backfill_idx80.py --cat ALL --allow-non-idx80` plus separate authorization.

**C. Which datasets need remediation first?**
Ticks (the 46-ticker OHLCV-present/ticks-absent gap deserves root-causing before treating ticks
coverage as a fixed ceiling), and `idx_tickers` itself (a 127-day-stale universe source is a
silent risk to every pipeline that reads it, independent of any one dataset's backfill).

**D. What exact historical date range should eventually be repaired for each dataset?**
- **Stockbit flow bars** — the only dataset with a well-quantified historical deficit: **224
  trading days, 2025-05-15→2026-04-21** (814 tickers, zero rows) plus an **86-trading-day incomplete
  recovery tail, 2026-04-22→2026-08-31**, for the same 814 tickers — ≈200,326 (ticker, day) cells
  total (re-verified this session against live DB, correcting this morning's rougher 774/972-based
  estimate). **Not** a 2-year blanket backfill.
- **Daily OHLCV, broker flow, ticks** — no historical deficit was sized this session; each would
  need its own gap analysis (analogous to §6 but run across a date range, not one day) before any
  historical repair could be scoped. This report does not recommend a number for these.

**E. What should NOT be backfilled?**
- **Ticks, for any date before today** — impossible by construction (no historical endpoint
  parameter exists), not merely deprioritized.
- **The suspension/staleness cohort (132 tickers)** across OHLCV/broker-flow/ticks — these appear to
  be genuinely inactive names; backfilling them would waste rate-limited vendor calls for confirmed-
  empty results, mirroring the same conclusion the stockbit-flow readiness report already reached
  for its own 32 suspended tickers.
- **Any multi-year, multi-dataset blanket backfill** — nothing in this session's evidence supports
  one; every dataset's real deficit (where quantified) is a specific, bounded window, not "as much
  history as possible."

---

## Deliverable status

**A. Tooling complete:** Yes — `tools/backfill_broker_flow_full_universe.py` +
`tests/test_backfill_broker_flow_full_universe.py` (16/16 passing), zero modifications to any
existing production file, full repo suite green apart from 2 pre-existing unrelated failures.

**B. Pilot-ready:** Yes, for broker/foreign flow specifically — dry-run verified against the live
DB and current universe. The other five dataset categories don't need new tooling to be "pilot
ready" — they already run at full-universe scope in production.

**C. Large historical backfill authorization: still required, and still not requested here.**
Only stockbit flow bars has a demonstrated, bounded, evidence-sized historical deficit
(§D). No other dataset's historical repair has been scoped. **No backfill — one day, multi-day, or
multi-year — was executed by this session.**
