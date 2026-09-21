# Data Foundation Gates: Stabilization, Universe Freshness, and Stockbit Historical Recoverability

**Date:** 2026-09-01 · **Author:** Claude Code session · **Status:** DIAGNOSIS + SMALL LIVE PROBE
ONLY. No bulk backfill executed. No files staged or committed. No DB writes at all (the probe uses
`stockbit_fetcher.fetch_flow()` directly, which only reads). No IDX80/PIT changes, no hypothesis
registration, no backtest/research execution.

**Question this report answers:** *Can we recover the known Stockbit historical gap, and are we
ready to authorize the full repair?*

**Answer: recovery is PROVEN feasible for the sampled population. Authorization is NOT yet
recommended — three concrete, cheap prerequisites remain (§G) before the large repair should run.**

---

## A. Working-tree / stabilization status

`git status` was audited, not modified — nothing here was staged, committed, or reverted.

**Headline counts:** 202 renames, 20 modified tracked files, 104 untracked new files (326 total
entries). This predates this session; none of it was introduced by this or the prior pilot session
except the three files noted below.

**Staged vs. unstaged — material for "clean checkpoint" planning:** the 202 renames are already
**staged** (`git diff --cached` shows them, 0 insertions/deletions — pure renames sitting in the
index vs. HEAD). This was true before this session started; nothing here ran `git add`. The 20
modified files and all 104 untracked files are **unstaged/untracked**. Practically: a bare `git
commit` right now, with no `git add`, would commit only the 202-rename doc reorg — the modified
production files and all new tooling would be left behind, uncommitted. Anyone establishing a clean
checkpoint should know the index and working tree are already in two different states.

**By category:**

| Category | Count | What it is |
|---|---:|---|
| Renames | 202 | `docs/agent_firm/*` → `docs/archive/agent_firm_adr/*` — a documentation reorganization (agent-firm ADRs moved into an archive folder). Content-neutral; git sees these as pure renames, not edits. |
| Modified: production code | 3 | `app.py`, `flow_filter.py`, `stockbit_fetcher.py` — small, additive-looking diffs (+15/-146/-8/-50 lines across the three; see `git diff --stat`). Consistent with continued work after commit `9b6e380` ("fix --probe scoping, concurrency-guard, and ALL-fallback gaps") that was never committed. |
| Modified: tests | 1 | `tests/test_backfill_flow_bars.py` (+64 lines, pure addition) |
| Modified: research governance docs | 6 | `HYPOTHESIS_REGISTRY.md`, `FAILURE_REGISTRY.md`, and 4 files under `docs/research_programs/P-A/experiments/EXP-PA-0001/` — **flagged, not touched**: these are append-only-in-spirit per `docs/roadmap/DECISION_LOG.md` convention; this session did not read their diffs in detail and makes no claim about whether the edits are additive |
| Modified: misc config/frontend | 7 | `.gitignore`, `.vscode/settings.json`, `TODO.md`, `idx-walkforward-5001.code-workspace`, 2 frontend router files, 1 frontend README, 1 frontend ADR doc |
| Untracked: **this session's own work** | 3 | `tools/backfill_broker_flow_full_universe.py`, `tests/test_backfill_broker_flow_full_universe.py`, `docs/audit/FULL_UNIVERSE_ONE_DAY_PILOT_2026-09-01.md` (from the prior pilot task) |
| Untracked: broker/foreign-flow tooling (pre-existing, built on by this session) | 9 | `tools/{agent_backfill_broker_flow_idx80,agent_backfill_foreign_flow_idx80,backfill_broker_flow_idx80,backfill_foreign_flow_idx80,broker_flow_idx80_gap,broker_flow_pit_planning,check_stockbit_flow_coverage,foreign_flow_idx80_gap,token_boundary_test}.py` + 12 corresponding test files |
| Untracked: agent-firm reliability probes | 6 | `scripts/probe_{actual_http_concurrency,zai_concurrency_limit,zai_large_payload,zai_sustained_rate}.py`, `scripts/replay_{firm_offline_run,governor_ab}.py` — unrelated to this data-foundation work |
| Untracked: research modules + reports | 7 | `research/idx80_membership.py`, `research/studies/idx80_flow_study.py`, `research_reports/{BBCA,BRPT,BULL,DEWA,trade}.md` |
| Untracked: docs — frontend architecture import | 30 | `docs/OneDrive_2026-08-07/Frontend arch/*.md` — an entire frontend PRD/spec corpus, unrelated to data pipelines |
| Untracked: docs — research program P-M | ~19 | `docs/research_programs/P-M/*` (hypothesis drafts, discovery notes, power analysis, lifecycle checkpoints LC-PM-0001..0010) |
| Untracked: docs — new directories | 3 dirs | `docs/audit/` (this report + the 2 pilot/readiness reports), `docs/data/`, `docs/infra/`, `docs/research_notes/` |
| Untracked: top-level misc | 3 | `P2_RESOLUTION_REPORT_2026-09-01.md` (today's IDX80 membership work), `PLAN/vwma20-intraday-workflow.md`, `_archive/idx-start.sh` |

**Assessment:** this is a multi-workstream repo with substantial real, working, uncommitted output
across at least five unrelated initiatives (frontend redesign, agent-firm reliability, research
programs P-A/P-M, IDX80 membership resolution, and this data-foundation/backfill-tooling line of
work). Nothing here blocks the historical-backfill decision this report exists to make. **No
staging or committing was performed, per instruction.** A future "clean checkpoint" pass should
commit in logical groups (e.g., the broker/foreign-flow tooling as one commit, the doc reorg as
another) rather than one bulk commit — but that is a separate, later task.

---

## B. Universe freshness findings

`idx_tickers` (the canonical full-universe source via `data.fetcher.load_all_tickers()`) has not
been refreshed since **2026-04-27** — confirmed again this session (single `last_checked` value
across all 972 rows).

**What the canonical source should be:** `idx_tickers`, populated by `data/ticker_discovery.py`'s
yfinance-based `.JK`-symbol scan, remains the right approach — there is no working alternative in
this repo (IDX's own official listing site is Cloudflare-blocked per this session's own recent P2
membership work). The problem is refresh cadence (manual, never re-run), not the source design.

**Is 958 still correct?** Empirically, **yes — cross-validated against real activity, not
assumed.** Comparing `idx_tickers`'s active set against every ticker with any recorded activity
(`ohlcv` ∪ `stockbit_flow_bars` ∪ `stockbit_flow`) since the 2026-04-27 refresh date:

- **0 tickers** have real recent activity but are absent from `idx_tickers` entirely (no missed new
  listings detected).
- **0 tickers** are marked `status='active'` with zero activity anywhere since the refresh (no
  stale/dead tickers hiding in the active set).
- The 14 tickers marked `status='inactive'` (a 2026-07-04 manual pass) all show a **single
  `stockbit_flow` summary row dated exactly 2026-07-03** and nothing in `ohlcv`/`stockbit_flow_bars`
  ever — evidence they were checked once, found to have no real trading history, and correctly
  excluded. This is a coherent, well-evidenced exclusion, not a false negative.

**Caveat:** this cross-check can only detect drift among tickers this pipeline has *tried* to fetch
at some point. A genuinely new IDX listing that has never been queried by anything (not even the
88-day-old cron) would produce no rows anywhere and would be invisible to this test. "No drift
detected" is a lower bound, not a guarantee of zero drift.

**What would change if refreshed?** Based on the above, likely very little for the *active* set —
zero add/remove candidates were found among tickers with any historical footprint. A refresh would
mainly (a) confirm or catch genuinely-new listings this cross-check can't see, and (b) potentially
review the 14 inactive tickers, though the evidence supports their exclusion as-is.

**Is refresh required before the historical Stockbit backfill? No.** The historical backfill's
target population is derived directly from `stockbit_flow_bars`'s own historical ticker set (900
tickers that have ever held a row, narrowed to a 776-ticker backfill target per the prior readiness
report) — it does not depend on `idx_tickers` at all. `idx_tickers` freshness matters for
*forward-looking* full-universe operations (the daily cron, the one-day pilot), not for this
backward-looking repair.

---

## C. Exact probe population and dates

Selected from the known-affected, still-active cohort (previously identified as genuinely trading
throughout the gap via independent OHLCV evidence), explicitly excluding the 32 confirmed-suspended
and 13 no-pre-listing-history tickers from the prior readiness report's exclusion list:

| Ticker | idx_tickers status | Sector |
|---|---|---|
| ADMR | active | Coal mining |
| GJTL | active | Tire manufacturing |
| ELSA | active | Oil & gas services |

| Date | Position in gap window (2025-05-15 → 2026-04-21) |
|---|---|
| 2025-06-16 | Early (~1 month in) |
| 2025-09-15 | Middle |
| 2025-12-15 | Late |

All 9 (ticker, date) cells were pre-verified read-only before any live call: confirmed trading days
(`trading_calendar` + IHSG bar present), confirmed zero rows in `stockbit_flow_bars`/`stockbit_flow`
for that cell, and confirmed genuine trading activity via `ohlcv` (non-zero volume, real close
price) — i.e., every probed cell is a real gap, not an already-covered or non-trading date.

**Adjacent-date baseline** (read from existing DB data, zero new vendor calls): all three tickers
show exactly **335 bars** on both 2025-05-14 (the last pre-gap day) and 2026-08-31 (today's
post-recovery data) — a precise, ticker-independent expectation for what a complete session looks
like.

---

## D. Vendor results

9 live calls to `stockbit_fetcher.fetch_flow(token, ticker, date)` — the same function the
production runner uses, called directly with no DB write. Token verified valid immediately before
(`verify_token()` → `True`) and reconfirmed at call time.

| Ticker | Date | Bars returned | Session span | Response trade_date | last_price | Matches independent OHLCV close? |
|---|---|---:|---|---|---:|---|
| ADMR | 2025-06-16 | 335 | 09:00–16:14 | 2025-06-16 | 1020 | ✅ (1020.0) |
| ADMR | 2025-09-15 | 335 | 09:00–16:14 | 2025-09-15 | 1030 | ✅ (1030.0) |
| ADMR | 2025-12-15 | 335 | 09:00–16:14 | 2025-12-15 | 1390 | ✅ (1390.0) |
| GJTL | 2025-06-16 | 335 | 09:00–16:14 | 2025-06-16 | 1145 | ✅ (1145.0) |
| GJTL | 2025-09-15 | 335 | 09:00–16:14 | 2025-09-15 | 1025 | ✅ (1025.0) |
| GJTL | 2025-12-15 | 335 | 09:00–16:14 | 2025-12-15 | 1045 | ✅ (1045.0) |
| ELSA | 2025-06-16 | 335 | 09:00–16:14 | 2025-06-16 | 510 | ✅ (510.0) |
| ELSA | 2025-09-15 | 335 | 09:00–16:14 | 2025-09-15 | 500 | ✅ (500.0) |
| ELSA | 2025-12-15 | 335 | 09:00–16:14 | 2025-12-15 | 494 | ✅ (494.0) |

**Every cell:** exactly 335 bars (matching the adjacent-date baseline precisely, not just
"nonzero"), correct requested-date echoed back in the response (no blank/shifted trade_date), full
09:00–16:14 session span, and a `last_price` that **exactly matches** the independently-collected
OHLCV close for that ticker/date — 9/9 cross-validations, zero mismatches. `buy_lot`/`sell_lot`/
`net_value` were all non-zero, non-placeholder, internally varied numbers consistent with real
trading activity (e.g., ADMR 2025-06-16: buy_lot=89,143,870, net_value=4,474,822,000).

No failures, no empty responses, no rate-limiting encountered across all 9 calls (a single `1.6s`
delay between calls was used, matching the production runner's own pacing).

---

## E. Historical backfill feasibility: **PROVEN**

Not "likely" or "probably" — proven for the sampled population, on the strongest available
evidence: exact bar-count match to the ticker's own known-good baseline, correct dates, full session
span, and independent price cross-validation against a completely different data source (OHLCV) for
every single probe cell. This directly supersedes the July 2026 feasibility study's own caveat (it
only ever tested two *always-covered* tickers, BBCA/TLKM, never a genuinely gap-affected one) — this
probe closes exactly that gap with a representative, still-affected sample.

**Not proven / out of scope of this probe:** whether *every* one of the 776 target tickers recovers
this cleanly (only 3 were sampled), and whether the post-recovery ~80–90% ceiling documented in the
prior readiness report (a genuine liquidity floor, not a defect) holds at the same rate across the
full historical window — this probe used only known-liquid, actively-traded names.

---

## F. Estimated repair scope (unchanged from prior evidence, now more confident)

Re-affirming the figure independently re-derived earlier this session (not re-computed here, since
no new coverage-scan evidence was gathered this pass): **≈200,326 (ticker, trading-day) cells**,
concentrated in a well-bounded **224-trading-day gap** (2025-05-15 → 2026-04-21, 814 tickers with
zero rows) plus an **86-trading-day incomplete recovery tail** (2026-04-22 → 2026-08-31) for the
same 814 tickers. **Not** an undifferentiated multi-year backfill — both windows are precisely
dated, and the recovery-tail ceiling (~80–90%) is expected, not a shortfall to chase toward 100%.

---

## G. Exact prerequisites before authorizing the large backfill

1. **A fresh token check immediately before launch** — today's token was valid at probe time, but
   the prior readiness report found it invalid earlier the same day; token state is not durable
   across sessions and must be re-verified at actual launch time, not assumed from this report.
2. **Explicit, separate authorization to run `tools/agent_backfill_idx80.py --action execute --cat
   ALL --allow-non-idx80 --yes-run-vendor-backfill --date-from 2025-01-02 --date-to 2026-04-28`**
   (or the equivalent bare-runner invocation) — this report proves feasibility, it is not that
   authorization.
3. **Commitment to the multi-session execution plan already on record** (prior readiness report §H):
   ~77–121 hours of cumulative vendor-call time, batched by trading date via the orchestrator, run
   across multiple bounded sessions with cooldowns — not one continuous invocation.
4. **Acceptance of the ~80–90% ceiling (§F) as success, not shortfall** — re-litigating a completed
   backfill against a false 100% expectation would misdiagnose a healthy result as a failure.
5. **`--release-fixture` must never be passed** — 2025-04-14 is a deliberately frozen regression
   fixture reserved for a specific sign-off test.
6. *(Not required, but recommended before or alongside launch, per §B)*: no `idx_tickers` refresh is
   needed to start the historical repair, but running `data/ticker_discovery.py --recheck --save-db`
   at some point remains good hygiene for the *forward-looking* full-universe pipelines (the daily
   cron, the one-day pilot tooling) — decoupled from this backfill's critical path.

---

## H. Recommended next action

**Do not run the large backfill yet.** The immediate next action is a **decision, not more
diagnosis**: this report and the prior readiness report together constitute the complete evidence
base (universe is stable and correct, historical recovery is proven on a representative sample,
scope is precisely bounded, tooling already exists with no new code needed). The next step is for
the operator to either (a) grant the explicit authorization in §G.2, at which point execution can
begin immediately with no further engineering work, or (b) request a wider probe (more of the 776
target tickers, or a probe further back toward the 2025-01-02 retention boundary) if higher
confidence is wanted before committing to the full ~100-hour execution — this report takes no
position on which, since that is a risk-tolerance decision, not a technical one.

**This report stops here, per instruction.** No bulk backfill, no alpha/research scan.
