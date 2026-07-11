# Institutional Research Engine Audit — 2026-07-11

**Scope:** Research Engine only (`research/`, `registry/`, `engine/wf_edge.py`, walk-forward/backtest/optimization stack, forward testing, promotion pipeline, research data products in `walkforward.db`). Production Engine treated as feature-frozen. Repository state on branch `ops/hardening-2026-07-10` is the sole source of evidence. No code was modified.

**Question answered:** Is this engine suitable for institutional quantitative research — discovering, validating, and promoting trading edge?

---

## Executive Summary

The Research Engine is a genuinely honest research system with one critical data-integrity hole and no experiment-tracking layer. Its strengths are unusual for a system of this size: real rolling walk-forward with ~16 out-of-sample windows per ticker, round-trip costs from a single authority applied to both legs, survivorship-aware full-corpus scoring, pre-registered pass/fail thresholds with cross-validation hurdles that have demonstrably killed mirages (TFB +3.38% → −7.20% OOS), a git-versioned Edge Registry with immutable approval manifests, and CI-enforced import/write boundaries. It has produced honest negative results (11/14 strategies rejected, flow study closed at "no edge") — the hallmark of a research process that isn't fooling itself.

Against that: **corporate actions are collected but never applied** — every backtest runs on raw prices through 101 splits (81 tickers) and ~2,069 dividend events, contaminating exactly the breakout-family signals the shop trades; the architecture boundary has a hole (`routes/` imports `research.*` into the production Flask process and is invisible to both guard tests); the optimizer duplicates strategy logic and still contains the intrabar look-ahead bug that was fixed in the engine on 2026-06-30; and no experiment is exactly reproducible because research outputs are overwritten in place with no run IDs, code hashes, or dataset versioning.

**Overall Research Engine Score: 5.9 / 10**
**Verdict: RESEARCH READY** (not yet READY FOR STRATEGY DISCOVERY — blocked by findings R-1, R-3, R-4).

---

## Phase 1 — Architecture

### What exists

- **Dependency direction is designed and CI-enforced.** `tests/test_architecture_boundary.py` forbids `research.*` imports in `scheduler/`, `engine/`, `forward_testing/`, `data/`, `screener/` + 6 root files, and forbids research importing execution modules (`scheduler|monitor|paper_trade|forward_testing|app`). Allowlist is empty and pinned at zero (`test_allowlist_shrinks_only`).
- **Write fence.** `tests/test_research_data_fence.py`: only `research/` may write `wf_scores`, `wf_edge`, `backtest_cache`; DAO exception `engine/wf_edge.py` with `save_wf_edge` callable only from research (rules W1/W2).
- **Shared floor is deliberate:** `engine/strategies.py` (STRATEGY_FUNCS), `engine/exits/`, `engine/indicators.py`, `data/loaders.py` serve both sides — one strategy implementation for backtest and live is a parity feature (plan 1C conformance test), not a violation.
- Research jobs run off the production scheduler via `research/cli.py` + crontab (verified installed and executing: last `wf-refresh` 2026-07-10 16:05→18:31, rc=0).

### Findings

**R-2 — Boundary hole: `routes/` is production but invisible to both guard tests — HIGH**
- **Evidence:** `app.py:14–19` registers `routes.backtest`, `routes.screener`, `routes_backtest_multi` etc. into the production Flask app. `routes/backtest.py` imports `research.walkforward_multi` at 5 sites (lines 106, 254, 430, 555, 675), `research.optimizer` (lines 1128, 1161), `research.backtest_roller` (line 1174); `routes_backtest_multi.py:13` imports research at module top level; `routes/screener.py:155,162` imports `research.fastmover_study`. Neither `PRODUCTION_SCOPES` nor `PRODUCTION_FILES` in `test_architecture_boundary.py` / `test_research_data_fence.py` includes `routes/` or `routes_backtest_multi.py`.
- **Impact:** (a) The production web process executes research code on HTTP request — `POST /api/optimizer/run` runs a full grid-search × walk-forward inside a gunicorn worker and writes `optimizer_results` into the shared DB; (b) the boundary tests give a false sense of completeness; (c) any future research-module change can break production endpoints with no CI signal.
- **Recommendation:** Add `routes/` and `routes_backtest_multi.py` to both tests' scopes; then either (i) move these endpoints to a research-only UI surface, or (ii) allowlist them explicitly as documented, shrink-only exceptions.
- **Effort:** 1–2 days. **Priority: P1.**

**R-5 — Research and production share one SQLite file — MEDIUM**
- **Evidence:** `walkforward.db` holds production state (`paper_trades`, `scheduled_signals`, `ft_*`, `agent_decisions`, `audit_events`) and research products (`wf_scores` 13,202 rows, `wf_edge` 3,822, `backtest_cache` 30,992, `optimizer_results`, `backtest_windows` 16,960) side by side. The M4-lite write fence covers write direction only; the physical split was explicitly deferred (registry/SCHEMA.md, 10 known prod readers).
- **Impact:** Research jobs and live trading contend for one writer lock (this repo's history contains ≥5 separate "database is locked" incident fixes). A research bug can still corrupt the production file (single blast radius). Production reads `wf_edge`/`backtest_cache` directly — i.e., **production currently does depend on experimental outputs** through the legacy gate readers; the registry-artifact path (NR7 frozen universe) is the only reader retired so far.
- **Recommendation:** Complete the already-planned reader retirements (blacklist / quality-gate / edge-veto → registry evidence), then execute the trivial physical split into `research.db`.
- **Effort:** 1–2 weeks (mostly the reader retirements). **Priority: P2.**

**R-11 — Duplicated logic — MEDIUM**
- **Evidence:** (a) `research/optimizer.py` re-implements five strategies by hand (`_run_vol_weighted` … `_run_tfb`) instead of parameterizing the canonical `engine/strategies.py` functions — see R-3 for the consequence; (b) `engine/strategy_registry/` is a second, decorator-based strategy registry that nothing uses (`STRATEGY_FUNCS` dict in `engine/strategies.py` is authoritative) — dead code previously flagged as "deliberately not merged" yet present on this branch.
- **Impact:** Drift between research-optimized logic and what actually trades; a parameter judged optimal in the optimizer is evaluated on a *different implementation* than production runs.
- **Recommendation:** Delete `engine/strategy_registry/` or adopt it; refactor optimizer runners to inject params into the canonical functions.
- **Effort:** 2–3 days. **Priority: P2.**

Duplicated datasets: `ohlcv_pre_raw_rebuild`, `wf_scores_pre_2b`, `wf_edge_pre_2b` are documented, reversible archives — acceptable; `ohlcv_cache` and root-level empty `walkforward.db` / `flow.db` / `idx_data.db` stubs are hygiene noise only.

**Phase 1 conclusion:** Direction is right and mostly enforced; the fence has one real hole (routes) and the physical data split is unfinished. Research does not modify production state (fence holds where it looks); production *does* still read experimental outputs via documented legacy gates.

---

## Phase 2 — Research Workflow Lifecycle

| Step | Exists? | Evidence |
|---|---|---|
| Idea | ⚠️ informal | `docs/superpowers/plans/*.md` written per initiative; no template/backlog |
| Implementation | ✅ | strategy fn in `engine/strategies.py` + registration in `STRATEGY_FUNCS`; study scripts in `research/studies/` |
| Backtest | ✅ | `run_all_strategies`, `backtest_cache`, routes UI |
| Optimization | ⚠️ built, unused | `research/optimizer.py` (WF-validated grid search) — `optimizer_results` contains **1 row** ever |
| Walk-forward | ✅ | `run_walk_forward`, weekly cron, 943/959 tickers scored 2026-07-10 |
| Forward testing | ✅ engine, ⚠️ loop | ft_* lifecycle live (793 shadow positions, 135 closed trades); GO/NO-GO evaluation is a hardcoded NR7-only script (`phase5_tracker.py`), not generic |
| Approval | ✅ | pre-registered rule frozen in manifest; human decision |
| Promotion | ✅ | git commit + PR of `registry/edge_registry.yaml` + manifest |
| Production | ✅ | `engine/registry_loader.py` reads once at startup, validates, alarms on skip |

**Missing steps:** (1) an experiment registry connecting idea → runs → conclusion (see R-4); (2) automated walk-forward reporting (only a negative-expectancy Telegram alert exists in `research/jobs.py:154`); (3) a generic forward-test → approval evaluator (one-off script per strategy today); (4) any use of the optimization stage in practice — parameters are frozen by protocol (`docs/wf_tuning_protocol.md` referenced), which is defensible, but then the optimizer is untested surface kept alive in a production route.

---

## Phase 3 — Backtesting Integrity

### What is done right (verified in code)

- **Entry timing:** signals evaluated on bar *i−1*, fills at bar *i* open (`strategy_trend_following_breakout` and generic `run_strategy` path) — no same-bar close fills.
- **Exit kernel parity:** one shared kernel (`engine/exits/evaluate_exit`) for backtest, live monitor, and forward test; trailing stops anchor on **prior-bar** extremes (C-8 fix, comment at `engine/strategies.py:158–166`); entry bar itself is evaluated (gap-day-one exits) matching the forward-test engine.
- **Costs:** single authority `engine/exits/costs.py` (0.15% buy / 0.25% sell commission + 0.10% slippage per leg) applied to both legs; `research/nr7_study.py.round_trip_net_pct` re-derives net from raw prices so studies don't trust upstream cost handling.
- **Survivorship:** WF refresh iterates the **full corpus** (`_load_ohlcv_bulk`), not active-only `idx_tickers` (`research/jobs.py:73–77` documents this deliberately); delisted names keep their losing history.
- **Partial-bar leakage:** research jobs load `is_final=1` only (Phase 2A); 779 provisional rows currently excluded.
- **Data corpus:** 1,045,166 rows, 959 tickers, 2021-07-05 → 2026-07-10, `UNIQUE(ticker,date)` prevents duplicates; nightly scraper-vs-yfinance reconciliation (alert-only, `data/reconcile.py`); IHSG-derived `trading_calendar` (1,203 sessions) replaced the destructive purge.

### Findings

**R-1 — Corporate actions collected but never applied — CRITICAL**
- **Evidence:** The corpus basis is RAW exchange prices by design (audit C-4); `data/market_schema.py:8–9` states "research adjusts via this table." The `corporate_actions` table is populated (2,170 rows: **101 splits across 81 tickers**, ~2,069 dividends) by `data/fetcher.py` and `scripts/rebuild_ohlcv_raw.py`. A repo-wide grep finds **zero readers**: no module in `research/`, `engine/`, or anywhere else ever SELECTs from `corporate_actions` to adjust prices. The promised adjustment step was never implemented.
- **Impact:** Every backtest, walk-forward window, wf_edge expectancy, and study statistic runs through unadjusted split gaps and dividend drops. A 1:10 split prints as a −90% bar; a reverse split prints as a fake +900% breakout — and the roster is dominated by breakout/momentum strategies (NR7, TFB, ORB, inside-bar) whose entry conditions are *exactly* "price gaps above a channel on volume." 81/959 tickers (8.4%) carry at least one split; dividends systematically penalize long expectancy on ex-dates across the whole universe. The flagship NR7 result (+1.18%/trade OOS, N=346) has not been verified clean of split-affected tickers.
- **Recommendation:** Implement back-adjustment (multiplicative for splits, optional for dividends) in the `final_only=True` path of `data/loaders.py._load_ohlcv_bulk` — one choke point feeds all research; then re-run the WF recompute and re-verify the NR7 manifest evidence against the adjusted corpus. Until then, treat all per-ticker expectancies on split-affected names as unreliable.
- **Effort:** 2–4 days implementation + one overnight recompute. **Priority: P0 — blocks trust in all backtest output.**

**R-3 — Optimizer retains the fixed intrabar look-ahead bug — HIGH**
- **Evidence:** `research/optimizer.py:_run_tfb` lines 161–166: `new_stop = row['close'] − mult×ATR; trail_stop = max(trail_stop, new_stop)` **then** `if row['low'] <= trail_stop` — the stop is ratcheted from the *current bar's close* and triggered against the *same bar's low*. This is precisely the C-8/C3 look-ahead identified 2026-06-30 and fixed in `engine/strategies.py` (kernel now tests first, ratchets after, anchored on prior-bar highs). The fix never reached the duplicated optimizer copy. Historical context: this same artifact once made looser trails look monotonically better (PF 1.82→2.34 gradient that evaporated after the fix).
- **Impact:** Any TFB parameter search through the optimizer produces inflated, look-ahead-contaminated results and would select wrong parameters. Mitigant: `optimizer_results` has 1 row, so damage-to-date is minimal — but the surface is exposed live via `POST /api/optimizer/run`.
- **Recommendation:** Route `_run_tfb` (and ideally all five runners) through the shared exit kernel / canonical strategy functions; add a parity test asserting optimizer trades == engine trades at default params.
- **Effort:** 1–2 days. **Priority: P1.**

**Minor (accepted-risk) items:** warmup-tail trades are dropped post-hoc by `entry_date >= test_start` string compare (ISO dates — correct), but a position opened in warmup that would still be held into the test window is discarded rather than carried, slightly altering early-window exposure; fills assume full execution at open with flat slippage — no volume-participation cap on illiquid IDX names (the NR7 universe is described in memory as "mostly illiquid," so flat 0.10% slippage is optimistic there); reconciliation is alert-only with scraper as authority (documented owner decision).

**Trustworthiness of results:** Directionally credible (costs, OOS discipline, and survivorship are handled better than most retail systems) but **not trustworthy at the per-ticker level until R-1 is fixed.**

---

## Phase 4 — Walk-Forward Validation

- **Rolling windows:** 12-month train / 3-month test, step = 3 months (`walk_forward_split`), non-overlapping OOS segments; ~16 windows per ticker on the 5y corpus — verified in data: 9,562 of 13,202 wf_scores rows have 16 windows; 72% have ≥9. No expanding-window variant (minor; rolling is the defensible default).
- **OOS hygiene:** warmup tail (60 bars, derived from actual indicator requirements via `get_warmup`) prepended to test slices; equity rebuilt from kept trades only.
- **Aggregation:** `engine/wf_edge.py` pools expectancy across windows Σ-over-trades (not mean-of-means), excludes claims below N=20 pooled trades, trade-weights Sharpe; `_summarize_strategy` handles the all-lossless PF=NaN case; per-trade Sharpe annualized by realized trade frequency with a 5-trade floor and ±10 clip.
- **Parameter stability:** the *optimizer* records per-window best-params and picks the modal winner — a real stability measure — but it's unused (1 row). The production WF runs **frozen parameters** by protocol, which sidesteps in-sample tuning entirely. Defensible, and arguably stronger than per-window re-optimization at this maturity.
- **Automatic reporting:** partial — a Telegram alert fires when a live-selectable strategy's cross-ticker mean WF return turns negative (`research/jobs.py:135–159`); there is no per-run WF report artifact.
- **Statistical meaningfulness:** with 16 OOS windows, pooled N floors, and a hard profitability gate (`_rank_strategies` zeroes any strategy with avg return ≤ 0), the WF layer is statistically meaningful for its purpose. Caveat: within-ticker min-max normalization in the ranker makes scores incomparable across tickers (mitigated by the Phase-2C pooled cross-ticker gate that supersedes it for live selection).

**Phase 4 verdict: sound design, one of the strongest components.**

---

## Phase 5 — Experiment Tracking / Reproducibility

**R-4 — No experiment tracking layer; exact reproduction impossible — HIGH**

- **Experiment IDs:** none. No runs table, no run UUIDs anywhere in the research stack.
- **Parameter versioning:** parameters are frozen in code; the only pinned config is the promoted strategy's `config_hash` (sha256 of the NR7 source) in the approval manifest — promotion-time only, not per-run.
- **Dataset versioning:** none. `ohlcv` is mutated in place daily; a WF run's input corpus is unrecoverable afterward. The manifest records only `{as_of, basis, history}` prose. (Nightly DB backups exist for ops, not pinned to runs.)
- **Random seeds:** not applicable — the entire pipeline is deterministic (grep confirms no RNG use in `research/`). This is a genuine reproducibility asset.
- **Metrics history:** destroyed on each run — `wf_scores`/`wf_edge` use `INSERT OR REPLACE` keyed (ticker,strategy) with no run dimension; only the `*_pre_2b` one-off archives preserve any history. `backtest_windows` (roller) is the exception: append-only per (ticker, test_start) with `computed_at`.
- **Result storage:** study conclusions live as hand-written markdown in `docs/superpowers/results/` (2 files) — good narrative artifacts, pinned in manifests, but not machine-readable or linked to run inputs.

**Can an experiment be reproduced exactly?** No. Re-running `wf-refresh` today uses a different corpus than last week's run and overwrites its output. The single promoted strategy (NR7_BULL v1) is the only *approximately* reproducible result, via manifest-pinned code commit + config hash + study docs — and even it lacks a data snapshot.

- **Recommendation:** add a `research_runs` table (run_id, git SHA, corpus fingerprint = max(date)+row count per ticker hash, params, started/finished), stamp `run_id` onto wf_scores/wf_edge rows (append-only or versioned), and emit study outputs as JSON alongside markdown.
- **Effort:** 3–5 days. **Priority: P1.**

---

## Phase 6 — Strategy Registry

A formal registry exists: `registry/edge_registry.yaml` + `registry/SCHEMA.md` + `engine/registry_loader.py`.

- **States:** CANDIDATE, SHADOW, APPROVED, SUSPENDED, RETIRED, SUPERSEDED. Loader loads only APPROVED/SHADOW; other states are lifecycle, not errors. Entries immutable once past CANDIDATE; changes = new version.
- **Compatibility contract:** `requires: {data_schema, exit_kernel, regime_model, engine_version}` checked against `ENGINE_VERSIONS`; mismatches skip the entry with a fail-open alarm — a mechanical stale-approval invalidator. Institutionally good design.
- **Gaps (R-10 — MEDIUM-LOW):**
  1. No pre-candidate states (Draft / Research / Backtested / WF-Passed). Those stages live implicitly in wf tables and study docs; a strategy's position in the funnel is not queryable.
  2. **State-evidence inconsistency:** `NR7_BULL_v1.yaml` records `shadow: {trades: 0, verdict: pending}` yet status is APPROVED — the strategy skipped from backtest evidence straight to APPROVED with the forward test running *after* approval (Phase-5 GO/NO-GO is effectively post-hoc). Institutionally, SHADOW with N≥15 should gate APPROVED.
  3. Population n=1. The registry's process has run exactly once; RETIRED/SUSPENDED/SUPERSEDED paths are untested in practice. The 8 disabled losing strategies live in `paper_config.disabled_strategies`, not as RETIRED registry entries — two parallel lifecycle systems.
- **Effort to close:** 2–3 days (schema states + backfill roster entries). **Priority: P2.**

---

## Phase 7 — Promotion Pipeline

The strongest audited component.

- **Approval process:** human decision recorded in an immutable manifest (`approved_by`, date, decision rationale including explicit rejections — SIDEWAYS rejected at −0.82%/trade N=628, universe generalization rejected at T1 −0.001%).
- **Evidence requirements:** manifest binds walkforward output doc, frozen universe artifact, report, config hash, code commit, corpus snapshot description. Pre-registered GO/NO-GO rule frozen before trades accumulate (`phase5_tracker.py` RULE dict).
- **Rollback:** supersede-with-new-version by git commit; loader re-reads at restart. Atomic and audited by construction (git history). No hot-reload — acceptable.
- **Version tracking / history:** git is the promotion ledger; registry entries immutable post-CANDIDATE.
- **Research never activates production automatically:** confirmed — promotion requires a PR + manual merge + process restart; the loader validates and fail-open-alarms rather than trusting.
- **Residual weaknesses:** nothing *verifies* the manifest's `config_hash` still matches the live strategy source at load time (drift between approved code and running code would be silent); shadow-evidence gate not enforced (see R-10.2).
- **Effort:** 1 day to add a config-hash verification check in the loader. **Priority: P2.**

---

## Phase 8 — Data Quality

- **Completeness:** 959 tickers × 5y, 1.05M rows; 943/959 scored in the last WF run (16 skipped for <60 bars — correct behavior). Coverage monitor (17:00) and token-expiry pre-alerts exist on the production side.
- **Consistency:** nightly scraper-vs-yfinance close reconciliation, alert-only, 0.1% tolerance.
- **Timestamp integrity:** TEXT ISO dates, daily granularity; WIB timezone pinned via pytz where clocks matter; `trading_calendar` derived from IHSG bars arbitrates real sessions vs missing data (the old purge that deleted real illiquid-name sessions is dead).
- **Duplicates:** `UNIQUE(ticker,date)` constraint — structural prevention.
- **Missing-value policy:** implicit — missing sessions are simply absent rows; strategies iterate what exists; NaN indicator warmups compare False and exclude bars naturally. No forward-fill contamination (good), but also no per-ticker gap report feeding research (a ticker with 30% missing sessions is scored like a complete one). MEDIUM-LOW.
- **Corporate actions:** the one critical failure — see R-1.
- **Provisional bars:** `is_final` fence verified present and used by all three research jobs.

Score dragged down almost entirely by R-1.

---

## Phase 9 — Performance & Scalability

**Measured (not estimated):** the full walk-forward sweep — 959 tickers × 14 strategies × ~16 windows — ran 2026-07-10 **16:05:01 → 18:31:21 = 2h26m**, single process, single thread (`logs/cron_research_wf_refresh.log`). Memory: the whole corpus is loaded into one pandas dict (~1M rows) — a few hundred MB, comfortably within a single host.

- **Backtest speed:** ~9.1s per ticker for a full 14-strategy WF; ~0.65s per strategy-ticker. Pure-Python bar loops (no vectorized fills); indicators recomputed per strategy per window with no cross-strategy caching.
- **Optimization speed:** TFB grid = 81 combos × 16 windows ≈ 1,300 backtests per ticker → tens of minutes per ticker; executed inside a web worker if invoked via the route (R-2).
- **Throughput / scale readiness:**
  - **100 experiments:** feasible as practiced — each "experiment" is a study script plus an overnight sweep; the shop has run ~6 studies in 3 weeks. ✅ (manual, serial)
  - **1,000 experiments:** not feasible. No run orchestration, no parallelism, no result store (R-4), and the weekly 2.4h sweep monopolizes the shared SQLite file (R-5). ❌
  - **10,000 experiments:** out of scope of this architecture (SQLite single-writer, in-place outputs, one host, no queue). ❌
- **Cheap wins available:** `multiprocessing.Pool` over tickers (embarrassingly parallel, ~8× on typical hardware), indicator memoization per (ticker, window). Effort 2–3 days. **Priority: P3** — current cadence (weekly) doesn't demand it; experiment throughput ambitions would.

**R-9 — Roller cron fires ~11×/month instead of first-Sunday — LOW.** `0 10 1-7 * 0`: vanilla cron ORs day-of-month with day-of-week, so this runs every day 1–7 *and* every Sunday. Benign (roller only appends new windows) but wasteful and contrary to the documented intent. Fix: guard with `[ "$(date +\%u)" = "7" ]`. Effort: minutes. Also noted: `research/optimizer.py` uses raw `sqlite3.connect` (lines 387, 420) instead of the repo-standard `data.db.connect` (WAL + busy_timeout) — the exact pattern behind five prior lock incidents. Effort: minutes. **Priority: P3.**

---

## Phase 10 — Statistical Quality

**Strengths (verified):**
- Pooled sample-size floors everywhere: N≥20 for any edge claim (`wf_edge.N_MIN_TRADES`), N≥5 for Sharpe, pre-registered study floors (T1 N≥300, T2 N≥150, T3 N≥100 per regime).
- Overfitting protection that has *demonstrated* bite: CV early/late split with 50% retention requirement (`nr7_study.cv_split`/`evaluate`) killed TFB's apparent +3.38% (→ −7.20% OOS) and the mid-cap flow edge (p=0.137, honored the bar, closed the hunt); stock-level smoothness pre-screen rejected on OOS failure.
- Pre-registered thresholds frozen before results (THRESHOLDS dict, frozen GO/NO-GO rule with 6-month timebox), honest negative reporting (11/14 strategies negative, "roster tapped out"), selection-bias awareness (44-name NR7 result correctly diagnosed as selection bias; only the regime-conditional slice promoted).
- Robustness kit from the flow study (split-half, per-ticker, non-overlapping windows) exists as reusable practice.

**Gaps:**
- **No multiple-testing control (MEDIUM):** the regime scan evaluated 14 strategies × 3 regimes = 42 cells against a fixed +0.5% bar; with ~47k trades pooled, one cell clearing the bar by chance is a live risk. The CV hurdle and per-cell N floors mitigate but don't quantify it. No White's Reality Check / SPA / deflated-Sharpe style correction.
- **No Monte Carlo / bootstrap:** absent entirely. No confidence intervals on expectancy, no trade-resampling drawdown distributions, no permutation tests. The +1.18% NR7 expectancy (N=346) carries no standard error anywhere.
- **No parameter-sensitivity analysis in practice:** the machinery exists (optimizer per-window stability) but is unused; frozen params were never mapped against a sensitivity surface (is NR7 robust to 6-bar or 8-bar narrowest-range definitions?).
- **Regime-conditioned inference on one regime cycle:** 5y of IDX data contains essentially one of each regime episode; BULL-conditional expectancy is estimated from clustered, overlapping market conditions. Acknowledged implicitly by the forward-test timebox — the right compensation.

**Are research conclusions statistically reliable?** The *negative* conclusions (which strategies to kill) are reliable — they required less power and survived multiple lenses. The *positive* conclusion (NR7 BULL edge) is plausible but under-quantified (no CI, no multiplicity adjustment, split-contamination unverified per R-1) and is correctly being resolved by a pre-registered forward test rather than by the backtest alone. That is the institutionally right posture; the missing piece is the quantification, not the discipline.

**Effort to close:** bootstrap CI + deflated-Sharpe utilities ~3–4 days. **Priority: P2.**

---

## Consolidated Findings Table

| ID | Finding | Severity | Effort | Priority |
|---|---|---|---|---|
| R-1 | Corporate actions collected, never applied — raw splits/dividends contaminate all backtests | **CRITICAL** | 2–4 d + recompute | **P0** |
| R-2 | `routes/` imports research into prod Flask app; invisible to boundary + write-fence tests | HIGH | 1–2 d | P1 |
| R-3 | Optimizer `_run_tfb` retains the fixed intrabar look-ahead (C-8) via duplicated logic | HIGH | 1–2 d | P1 |
| R-4 | No experiment tracking: no run IDs, outputs overwritten in place, no dataset versioning | HIGH | 3–5 d | P1 |
| R-5 | Shared prod/research SQLite; prod still reads experimental tables via legacy gates | MEDIUM | 1–2 wk | P2 |
| R-6 | No multiplicity control, no bootstrap/Monte Carlo, no CI on promoted expectancy | MEDIUM | 3–4 d | P2 |
| R-10 | Registry lifecycle gaps: no pre-candidate states; APPROVED granted with shadow N=0; parallel disable-list lifecycle | MEDIUM-LOW | 2–3 d | P2 |
| R-11 | Duplicated strategy implementations (optimizer runners) + dead `engine/strategy_registry/` pkg | MEDIUM-LOW | 2–3 d | P2 |
| R-7 | Single-threaded 2h26m sweeps; no orchestration; not ready beyond ~100 manual experiments | MEDIUM-LOW | 2–3 d | P3 |
| R-9 | Roller cron fires ~11×/month (DOM/DOW OR-semantics); optimizer bypasses `data.db.connect` | LOW | <1 h | P3 |

Suggested sequence: R-1 → R-3 → R-2 → R-4 (≈2 weeks) unlocks the READY FOR STRATEGY DISCOVERY tier.

---

## Final Scores (0–10)

| Dimension | Score | Rationale |
|---|---|---|
| Architecture | 6.5 | Enforced boundaries and deliberate shared floor, but a real hole (routes), shared DB, duplicated logic |
| Research Quality | 7.0 | End-to-end lifecycle exercised once with honest negatives; optimizer stage unused; reporting partial |
| Statistical Validity | 6.0 | Excellent discipline (pre-registration, CV, N floors, pooled expectancy); no CI/multiplicity/MC; R-1 taints inputs |
| Reproducibility | 3.5 | Deterministic pipeline + promotion manifests, but no run IDs, in-place overwrites, no data versioning |
| Scalability | 4.0 | Weekly cadence fine; 2.4h serial sweeps, SQLite single-writer, no orchestration — caps at ~100 manual experiments |
| Promotion Readiness | 7.5 | Immutable manifests, compatibility versioning, git-gated promotion, no auto-activation; shadow gate not enforced |
| Maintainability | 5.5 | Well-tested core (14 research-adjacent test files) vs dead registry pkg, duplicated runners, research-in-routes |
| **Overall Research Engine Score** | **5.9** | |

---

## Final Verdict: RESEARCH READY

**Justification (evidence only):**

- It is more than NOT READY: the complete lifecycle — idea → implementation → backtest → walk-forward → forward test → approval → promotion — has been executed end-to-end (NR7_BULL v1, manifest-pinned, registry-loaded, live-gated), CI enforces the core research/production boundaries, walk-forward is methodologically sound (~16 OOS windows, pooled costs-inclusive expectancy, survivorship handled), and the process has repeatedly produced and honored negative results — the defining behavior of functional research.

- It is not READY FOR STRATEGY DISCOVERY: discovery output cannot yet be trusted at the per-ticker level because every backtest runs through unadjusted splits on 81 of 959 tickers and universe-wide unadjusted dividends (R-1) — a direct distortion of the breakout-family signals this roster trades; the one parameter-search tool contains a known, previously-fixed look-ahead bug (R-3); and no experiment can be exactly reproduced or even compared to last week's run because outputs are overwritten in place with no run identity or data versioning (R-4).

- It is far from INSTITUTIONAL RESEARCH READY: that tier additionally requires physical research/production data separation (R-5), quantified uncertainty and multiplicity control on promoted claims (R-6), enforced evidence-gated lifecycle states (R-10), and experiment throughput beyond one serial 2.4-hour sweep on a shared SQLite file (R-7).

The distinguishing asset of this system is its epistemic honesty — frozen rules, pre-registration, and a graveyard of correctly-killed strategies. The distinguishing liability is that its raw-price corpus silently breaks the promise its own schema documentation makes ("research adjusts via this table"). Fix R-1 through R-4 (≈2 weeks) and the verdict moves up one tier.

*Audit performed read-only 2026-07-11. No code, configuration, or data was modified.*

---

## ADDENDUM 2026-07-11 (post-Phase A): R-1 diagnosis corrected

Phase A validation disproved R-1's factual premise. The corpus contains **no
split gaps**: yfinance adjusts OHLC for splits even with `auto_adjust=False`,
and the 2026-07-03 rebuild inherited that basis (dividends remain unadjusted).
Verified at ex-dates (CUAN 1340→1420 across a 10:1; DSSA 2680→3120 across a
25:1). Historical backtests were therefore NOT split-contaminated, and blindly
applying `corporate_actions` factors double-adjusts (first recompute printed
CUAN momentum +39%/trade before being caught and rolled back).

What survives of R-1: (a) `data/market_schema.py`'s "research adjusts via this
table" promise was still unimplemented — the risk is real but FUTURE-tense: a
split occurring after bars are stored gaps the scraper-maintained series until
refetch; (b) the shipped fix is a gap-VERIFIED adjustment layer that applies a
factor only when a persistent gap actually exists (zero apply today).
See `Audit/RESEARCH_ENHANCEMENT_PHASE_A_2026-07-11.md`.
