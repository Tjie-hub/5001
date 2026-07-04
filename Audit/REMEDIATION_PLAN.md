# Remediation Plan — Phased Reorder of the 2026-07-02 Institutional Audit

Ordering principle (owner's): correctness → trust → stability → alpha.
No phase starts until the previous phase's exit criteria are met and verified.
Finding IDs (C-x, H-x) reference `Audit/INSTITUTIONAL_AUDIT_2026-07-02.md`.

---

## Phase 1 — Engine Correctness
**Goal: Research = Paper = Live. One signal definition, one exit engine, one sizing rule.**

> **STATUS: COMPLETE 2026-07-03** — 1A (PR #5), 1B (PR #6), 1C (PR #7). Exit
> criteria met: conformance test `tests/test_conformance.py` green (backtest =
> SHADOW to 1e-9, paper = both to 1bp); every live-selectable strategy opens
> end-to-end; wf_scores marked STALE pending the Phase-2 re-baseline.

### Work items
| # | Item | Findings | Where |
|---|---|---|---|
| 1.1 | **Unified StrategySpec registry**: one record per strategy = {name, backtest fn, live checker, exit policy, family, enabled}. Checker contract is typed and enforced: every checker MUST return `price` (entry reference), `sl`, `tp`/exit-policy id. A registry test fails CI if any live-selectable strategy lacks a checker or violates the contract. | C-1 | new `engine/strategy_registry` (finish the unmerged package) |
| 1.2 | **Fix the trade-open path**: scanner reads entry price via the registry contract, not `details['price']`. Add regression test: every strategy in `_REGIME_STRATEGY_MAP` can produce an open_trade call end-to-end with a synthetic signal. | C-1 | scheduler/scanner.py:1461-1509 |
| 1.3 | **One exit engine**: adopt `forward_testing/positions/exit_evaluator.py` (already pure + look-ahead-correct) as the single kernel. Backtests (`run_strategy`, custom runners), `monitor.py`, and the SHADOW engine all consume `ExitPolicyRegistry`. Complete the registry for all 15 strategies (incl. TFB MA20-break, Panic no-SL/5-bar time, Crash Recovery levels, VWMA-BP swing-TP). | C-3, C-8, H-7(ft registry), H-11 | forward_testing/positions/*, engine/strategies.py, monitor.py |
| 1.4 | **Fix momentum trail look-ahead** while migrating to the shared evaluator (test stop against prior extreme, ratchet after). Applies the C3-2026-06-30 fix pattern to `run_strategy(trail_sl=True)`. | C-8 | engine/strategies.py:187-190 |
| 1.5 | **Sizing off actual stop distance**: `lots = risk_rp / (stop_distance × 100)`; stop_distance = the same value the exit engine will use. Hard aggregate cap: Σ capital_used ≤ 100% of capital (simple guard now; real portfolio logic is Phase 4). | C-2 | paper_trade.py:378-388 |
| 1.6 | **Checker/backtest signal parity**: vwap_reversion checker uses the same rolling-60 `calc_vwap` as the backtest; vol_weighted checker gains the missing `delta>0 & close>open` terms; kill in-place df mutation in checkers (compute locally). | H-3, H-2 | engine/strategies.py checkers |
| 1.7 | **Entry & cost parity**: paper P&L applies the same commission/slippage as backtests; entry convention documented (signal close vs next open) and made identical in backtest, SHADOW, and paper. | H-21 | paper_trade.py close/open paths |
| 1.8 | **Regime Adaptive**: fix to per-bar (or per-window-start) classification, or remove from STRATEGY_FUNCS until fixed. Do not let it enter the next wf refresh as-is. | C-7 | engine/regime_filter.py:262 |
| 1.9 | Exit-reason taxonomy unified (cooldown matches all stop-outs; `_count_exits` Swing Trend mislabels fixed). | H-9, H-11 | walkforward_multi.py, monitor.py, paper_trade.py |

### Exit criteria
- A single synthetic-data conformance test runs each strategy through backtest, SHADOW, and paper paths and asserts identical entries, exits, and P&L (± cost rounding).
- Every live-selectable strategy opens a trade end-to-end in test.
- `wf_scores` invalidated and marked stale (they will be recomputed in Phase 2, on corrected exits).

---

## Phase 2 — Statistical Integrity
**Goal: every metric can be trusted — including the data it's computed on.**

> **STATUS: COMPLETE 2026-07-04.** 2.1/2.2 (PR #8, data freeze + 5y raw rebuild),
> 2.3/2.4/2.7 (PR #9, WF metric fixes + survivorship + 5y windows), 2.6 (PR #10,
> regime holdout honesty), 2.5 (PR #11, disable losers + wf_edge selector). The
> 2026-07-04 recompute produced the first trustworthy wf_scores: pooled per-trade
> expectancy shows ONLY NR7 Breakout positive; 8 measured strategies negative and
> now disabled; live selection gates on wf_edge expectancy, not consistency
> (C-6 fixed). Live long book is effectively empty (NR7 has no checker) — the
> honest, intended pre-capital state.

> **STATUS 2026-07-03: items 2.1 + 2.2 SHIPPED (PR #8).** Scraper 16:15 bar =
> final EOD authority (is_final flag); yfinance raw = backfill/reconcile-only
> (nightly 21:00 alert job); trading_calendar replaces the session-deleting
> purge; corporate_actions captured; research jobs exclude provisional bars.
> 5y raw corpus rebuild script shipped — prod build/verify/swap executed at
> deploy. wf_scores now DOUBLY stale (old exits AND old corpus) until 2.3/2.8.
>
> **items 2.3 + 2.4 + 2.7 SHIPPED (PR #9):** avg_pf NaN fixed + pooled
> total_trades exposed; Sharpe floor 3->5; ~16 OOS windows pinned on the 5y
> corpus; WF refresh scores the full corpus (survivorship); tuning/embargo
> protocol doc. 2.8 recompute executed at deploy (wf_scores_pre_2b archived).
> REMAINING: 2.5 strategy consolidation (roster change — needs buy-in, forces
> a 2nd recompute) + 2.6 regime-classifier honesty.

### Work items
| # | Item | Findings |
|---|---|---|
| 2.1 | **Freeze the OHLCV pipeline**: pick one canonical source; store raw prices + explicit adjustment factors; remove `WHERE ohlcv.close IS NULL` upsert rule; nightly reconciliation vs an official EOD reference; mark intraday partial bars (`is_final` flag) so no research/scan job consumes them as final. | C-4 |
| 2.2 | **Delete `_purge_duplicate_non_trading_days`**; replace with an exchange trading-calendar table. Backfill audit for previously deleted real sessions. | C-5 |
| 2.3 | **Re-baseline walk-forward**: extend history (≥5y where available) OR switch the gate from per-ticker consistency (n=4 windows) to pooled cross-ticker validation per strategy; document the tuning protocol (params frozen BEFORE the validation period; embargo between tuning data and reported OOS). | C-6, parameter leakage |
| 2.4 | **Survivorship**: score the full historical universe (keep delisted in the research set); point-in-time ticker status where feasible. | leakage audit |
| 2.5 | **Consolidate overlapping strategies** (vol_weighted/momentum/conservative → one parameterized entry; ORB-daily/NR7/InsideBar → one range-breakout). Fewer, more distinct hypotheses → less multiple testing, 2-3× faster WF. | Major/statistical |
| 2.6 | **Regime classifier honesty**: holdout validation or demote to rule-based `detect_regime` only. Stop reporting in-sample accuracy. | Major/statistical |
| 2.7 | Metric fixes: avg_pf NaN path; per-trade equity DD caveat documented or replaced with daily mark-to-market equity; Sharpe minimum-sample floor raised and flagged in outputs. | H-3, compute_metrics |
| 2.8 | Recompute wf_scores/wf_edge on Phase-1 exits + Phase-2 data; archive the old tables for comparison. | — |

### Exit criteria
- Data audit report: zero mixed-basis discontinuities in the research window; bar counts match the exchange calendar.
- WF report regenerated with documented protocol; every published metric carries its sample size.
- A leakage checklist (look-ahead / survivorship / parameter / timestamp) passes and is added to CI as tests where mechanizable.

---

## Phase 3 — Production Stability
**Goal: no silent failures, no fail-open, no hidden assumptions.**

### Work items
| # | Item | Findings |
|---|---|---|
| 3.1 | **Fail-open inventory → explicit policy**: every `except: pass/fail-open` site classified as fail-open (allowed, alarmed) or fail-closed. Specifically: agent-firm enforce bypass of the flow gate (C-9), `flow_confirms_signal` FLOW_UNAVAILABLE, unscored-ticker WF-gate bypass, liquidity-gate `except: pass`, keystats db_error. Each fail-open fires a Telegram/log alarm with a daily digest. | C-9, H-17, gate asymmetries |
| 3.2 | Fix the dead FLOW_REVERSAL alert (`date` → `trade_date`) + add a schema-drift test that runs every raw SQL string against the real schema. | H-1 |
| 3.3 | **DB layer**: one `connect()` with WAL + busy_timeout used everywhere; `run_vpin_daily_batch` and backfills converted to compute-then-write or chunked commits; connection-per-loop eliminated in scans. | Major/architecture, H-14 |
| 3.4 | **Scheduler hygiene**: idempotency sentinels on all trade-affecting jobs (not 2/20); move Fri WF refresh off the 16:00 scan slot; 16:00 momentum scan moved after bar-finalization (or gated on `is_final` from 2.1); dedup scheduled_signals within a day. | timing findings |
| 3.5 | Reproducibility: complete `requirements.txt` (yfinance, scikit-learn, …), pin versions, fix the stale agent-firm config test, document start.sh as the only entrypoint. | Major/maintainability |
| 3.6 | Move `check_keystats_freshness` network refetch out of the scan loop into a pre-scan batch. | H-18 |
| 3.7 | Ops: dead-man's-switch heartbeat for the scheduler; log unification (print → logging); token-expiry pre-alert. | Missing features |

### Exit criteria
- Grep-audit shows zero unclassified broad excepts on the trade path.
- Chaos drills pass: kill the token mid-day, kill the LLM, kill the scheduler mid-job — system blocks or alarms, never silently trades/approves.
- Fresh-clone install runs the full suite green.

---

## Phase 4 — Alpha Optimization
**Only now: ranking, scoring, portfolio, adaptive weighting.**

| # | Item |
|---|---|
| 4.1 | Forward-testing Phase 3: PORTFOLIO track, Ranker/Sizer — on top of the now-trustworthy SHADOW book (LONG-only tradeable filter; per-strategy exit policies from 1.3). |
| 4.2 | Convert soft binary gates (RS<1.0, regime UNCERTAIN, sector weight, flow score) into weighted score inputs with one calibrated threshold — the edge_score frame already exists. Keep hard gates only for data-integrity conditions. |
| 4.3 | Portfolio construction proper: heat/sector/correlation caps, vol targeting, capital allocation across strategies by pooled expectancy with shrinkage. |
| 4.4 | Adaptive weighting / decay detection; strategy health monitoring on pooled cross-ticker stats. |
| 4.5 | Optional alpha work parked until here: intraday ORB integration, Liquidity Sweep re-validation, sectors.app enforce mode, premover enforce. |

### Exit criteria
- Any new gate/weight ships with its own OOS validation under the Phase-2 protocol, and a SHADOW period before enforce.

---

## Placement judgments (deviations worth noting)
1. **Data pipeline (C-4/C-5) sits in Phase 2, not Phase 1** — Research=Paper=Live can be proven on synthetic data without touching the corpus; "metrics can be trusted" cannot. If preferred, 2.1/2.2 can run concurrently with Phase 1 since they touch disjoint files.
2. **The one-line FLOW_REVERSAL fix (3.2) and the enforce-mode bypass (3.1)** are Phase 3 by category, but both are ~minutes of work; fix opportunistically the first time those files are open. The enforce bypass is dormant only because enforce is currently off — if anyone flips it before Phase 3, that's a live hole.
3. **The aggregate exposure cap is split**: a blunt ≤100% guard lands in Phase 1 (it's a correctness/safety invariant, 5 lines); real portfolio heat management stays in Phase 4.

## Standing rule during Phases 1–3
No parameter tuning, no new strategies, no gate-threshold changes. Every wf_score produced before Phase 2 completion is treated as stale and non-actionable for live routing.
