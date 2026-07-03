# Institutional Audit — IDX Walk-Forward Trading Engine
**Date:** 2026-07-02 · **Branch:** feat/tfb-context-filter (master-equivalent for audited paths)
**Auditor role:** Principal Quant Researcher / Trading Systems Auditor
**Method:** full read of the decision-critical path (engine/strategies.py, walkforward_multi.py, indicators.py, regime_filter.py, wf_edge/edge_score/veto/risk_score, scheduler/{__init__,jobs,scanner,utils}.py, paper_trade.py, monitor.py, data/{db,fetcher}.py, forward_testing/* , flow_filter.py public API, screener ohlcv path, config.py) + live DB interrogation + full test-suite run (921 pass / 1 fail).

---

## Executive Summary

**Would I trust this engine with real capital today? No.**

The engine has genuinely strong parts: the forward-testing SHADOW subsystem is the best-engineered module in the codebase (idempotent, look-ahead-aware, cost-consistent, survivorship-patched), the recent bug-fix discipline (WF lock, intrabar look-ahead C3, Telegram HTTP) is real, and the test suite is broad (922 tests).

But the audit found that **the research layer and the execution layer describe two different trading systems**:

1. The walk-forward scores that route capital are computed with exits the live system never executes, on a price corpus that mixes dividend-adjusted and raw prices, over a sample (4 OOS windows/ticker, 2.2 years of data) too small to support the gates built on it.
2. The live execution path cannot actually open trades for the strategies the research says are best (a missing dict key silently skips TFB/momentum/sweep entries), sizes positions at ~2× the configured risk when it does trade, and monitors exits on partial daily bars with a generic exit policy.
3. Several "safety" layers invert under failure: agent-firm *enforce* mode bypasses the flow gate and fails open; missing flow data confirms signals in one scanner and blocks them in another.

Live evidence corroborates: **0 paper trades ever closed, 358 BUY vs 5,831 SELL signals ingested** — the long book the research validates is starved to zero at execution, while the short "distribution" book (never backtested as a strategy, unshortable for IDX retail) dominates the forward test.

The engine is a promising research scaffold. It is not yet a coherent capital-deployment system.

---

## Critical Issues (money-losing / research-invalidating), ranked

**C-1. Primary strategies can never auto-open trades — silent signal-to-execution break.**
`scheduler/scanner.py:1467`: `entry_price = signal_details.get(first_strategy, {}).get('price')`. The signal checkers for **Trend Following Breakout** (`details['close']`, strategies.py:1978), **momentum** (no price key at all, strategies.py:1352), and **Liquidity Sweep** (no price key) never emit `'price'` → "No price found, skipping" for every one of their signals. Additionally `Inside Bar Breakout` and `NR7 Breakout` have **no live checker at all** (`check_current_entry_signal` returns "belum didukung"). Net effect: in BULL regimes the entire selected book (TFB, momentum, Inside Bar, NR7) emits signals that can never become trades via the 5×/day multi-strategy scan. Only the disabled trio + Crash Recovery + Panic Rebound expose `'price'`. Evidence: `paper_trades` is empty; scheduled_signals BUY=358 vs SELL=5,831.

**C-2. Position sizing risks ~2× (or worse) the configured amount; no aggregate exposure cap.**
`paper_trade.py:381-387`: `lots = int(risk_rp / (atr * 100))` — risk-per-lot is priced at **1×ATR** while the default stop is **2×ATR** (`sl_atr_mult=2.0`) → realized risk = 2× `risk_pct` (4% not 2%). When a strategy supplies its own SL (Crash Recovery: resume low, possibly 10-15% away), sizing *still* uses 1×ATR → risk unbounded relative to config. Separately, `max_open=5` × per-trade 30% cap = up to **150% of capital deployed** with no portfolio-level heat, sector, or correlation check.

**C-3. Live exits ≠ validated exits, across the board.**
`monitor.py` applies one generic exit engine (close-based SL/TP, breakeven at +1 ATR, 1-ATR trail after +2 ATR, 14-day time stop) to every non-swing position, and `daily_signal_scan` opens momentum trades with a fixed −2.5% SL + swing-high TP. The wf_scores that select these strategies were computed with entirely different exits (TFB: 3×ATR ratchet + MA20-break; momentum: 1.2×ATR trail, 2.4×ATR TP; VWMA-BP: swing-high TP / VWMA SL; Panic Rebound: no-SL + 5-bar time stop — deliberately, since stops were shown to destroy that edge). The research P&L distribution therefore does not describe the live system. Worse, monitor exits trigger on **close** while backtests fill intrabar on **low/high** — a systematic optimistic/pessimistic mismatch.

**C-4. OHLCV corpus integrity: mixed price bases + un-correctable bars.**
`data/fetcher.py:_save_df` upserts with `WHERE ohlcv.close IS NULL` — yfinance can never overwrite an existing bar — and `fetch_all_incremental` skips any ticker whose `MAX(date) >= today`. Since `screener/idx_scraper.py` writes today's bar intraday (INSERT OR REPLACE, raw Stockbit tradebook prices), the effective data source silently flipped to the scraper, while history remains **yfinance auto_adjust=True** (dividend/split-adjusted at fetch time). Consequences: (a) adjusted and raw prices coexist in one series — every corporate action since the scraper era creates a permanent phantom gap that Donchian breakouts, 5-day-drop (Panic), gap detection (Crash Recovery) and MA filters will misread; (b) incremental fetching under auto_adjust means older bars are never re-adjusted after new dividends — the discontinuity is baked in; (c) tradebook-derived OHLC may exclude auction prints (unverified — needs comparison against official IDX EOD).

**C-5. `_purge_duplicate_non_trading_days` deletes real trading days.**
`data/fetcher.py:223`: any bar whose close AND volume equal the previous bar's is deleted (Pass 1). Illiquid IDX names routinely print consecutive zero-volume, same-close days — those real sessions are destroyed, fabricating multi-day calendar gaps that `strategy_crash_recovery` explicitly interprets as suspensions (`day_diff >= 5`). It runs on every incremental fetch, per-ticker per-row, inside one write transaction.

**C-6. The statistical foundation of wf_scores cannot support the gates built on it.**
Live DB: **94% of wf_scores rows have windows_tested = 4** (data starts 2024-04; 12-mo train / 3-mo test leaves ≤4 windows). The routing gate `consistency_pct >= 50` means "≥2 of 4 windows profitable" — a zero-edge coin passes 69% of the time. `wf_edge` demands ≥20 pooled trades but the median qualifying pair has 21 — expectancy standard errors swamp the 0-3% anchor range used by edge_score. On top of this, **strategy parameters were tuned on the same full history the walk-forward re-evaluates** (TFB gates/trail chosen from full-history sweeps in June 2026, then "validated" by WF on that same data). This is rolling in-sample evaluation of hand-tuned parameters, not true OOS. Nothing re-fits per window; the "train" window trains only the regime classifier.

**C-7. Regime Adaptive strategy has whole-window look-ahead.**
`engine/regime_filter.py:strategy_regime_adaptive` classifies the regime **once, from the last bar of the input window**, then applies that one strategy to the entire window. In `run_walk_forward` the test window's *final* bar decides which strategy traded the whole quarter. Its wf_scores are invalid and it was just added to STRATEGY_FUNCS (Jul 2), so this now pollutes wf_scores/wf_edge on the next refresh.

**C-8. Intrabar look-ahead persists in the generic trailing stop.**
`engine/strategies.py:187-190` (`run_strategy`, `trail_sl=True`, used by **momentum**): `peak_price` is raised with the *current* bar's high, then the stop derived from it is tested against the *same* bar's low — the exact bug class fixed in TFB on 2026-06-30 (and correctly avoided in forward_testing's ExitEvaluator, whose docstring explains why it's wrong). Momentum's wf_scores are inflated by better-priced trail exits.

**C-9. Agent-firm enforce mode weakens, not strengthens, the pipeline.**
`scheduler/scanner.py:940-945`: in enforce mode the function returns non-vetoed **intersection_results** — i.e. candidates that FAILED flow confirmation get promoted into the trade-open list, and because the firm's contract is fail-open (degraded/bypassed/spend-capped ⇒ not vetoed), an LLM outage auto-approves the top-20 candidates for paper trading without flow confirmation. Turning the safety layer ON removes a gate.

---

## Major Issues

**Architecture**
- **DB access is not centralized.** `data/db.py:get_db()` sets neither WAL nor busy_timeout despite being the "central" helper; dozens of raw `sqlite3.connect()` calls (scanner, jobs, monitor, paper_trade, strategies, indicators) with default 5s timeout. The 2026-06 lock incidents will recur: `run_vpin_daily_batch` (18:00) holds one implicit write txn across a ~970-ticker loop, adjacent to the 18:30 forward-test cycle.
- Scheduler, Flask app, and 35-min CPU jobs share one process (GIL + APScheduler thread pool). Duplicate-run sentinels exist for only 2 of ~20 jobs; systemd restart overlap is otherwise unguarded (the WF job has a pid lock; scans do not — 5×/day scans opening trades are not idempotent).
- Two parallel live pipelines (16:00 `daily_signal_scan` momentum path vs 5×/day `scheduled_multi_strategy_scan`) implement the same concepts (flow gate, regime gate, WF gate, trade-open) with different rules and different failure semantics.
- Module boundaries leak: scanner imports from paper_trade for config; strategies.py mixes backtest engines, live checkers, DB access, and a stray `__main__`; `strategy_regime_adaptive` mutates `sys.path`.

**Logic**
- WF gates are asymmetric fail-open: tickers **without** wf_scores bypass both the 33% blacklist and the 50% consistency gate (`if wf and ...`), so unproven names trade more freely than mediocre proven ones.
- Two flow gates with opposite failure semantics: `flow_confirms_signal` → missing data **confirms** (fail-open); multi-scan batch gate → missing data **blocks** (fail-closed).
- Timing: 16:00 momentum scan and Friday-16:00 WF refresh consume today's bar while it is still the 14:35 intraday partial (finalized only by the 16:15 EOD scraper). The Friday WF refresh also collides with the 16:00 scan slot.
- Backtest entry ≈ next-open + costs; live paper entry = last close, gross, no costs; paper P&L (gross) is not comparable to backtest P&L (net).

**Statistical validity**
- Strategy overlap: `vol_weighted`, `momentum`, `conservative`, `TFB` are all volume-ratio × bullish-price variations; `ORB` (daily), `NR7`, `Inside Bar` are all next-open range breakouts with prev-low stops. Effective independent strategy count is ~5-6, not 15. wf ranking normalizes within ticker across these correlated variants, overstating differentiation.
- RegimeClassifier: trained and scored **in-sample** (train accuracy reported vs majority baseline; no holdout), 3-class logistic with confidence fallback at 0.45 (nearly always exceeded). In the live scan it retrains per ticker per day on full history — a fresh in-sample model daily.
- Sharpe on per-trade returns annualized by realized frequency with a ±10 clip and a 3-trade minimum — directionally fine, but window Sharpe on 3-10 trades is noise, and it feeds the weighted score.

**Maintainability / testing**
- `requirements.txt` missing `yfinance`, `scikit-learn`, `langgraph` extras used in prod paths → environment non-reproducible (already caused collection failures on 2026-07-01).
- 1 stale failing test (`tests/agent_firm/test_config.py` expects `deepseek-v4-pro`; default is now `glm-5.2`).
- Signal-checker dispatch keys are a mix of snake_case (`momentum`) and Title Case (`Trend Following Breakout`) that must stay in sync across STRATEGY_FUNCS, _REGIME_STRATEGY_MAP, checker dispatch, ExitPolicyRegistry, and disabled_strategies — no single registry enforces it (the strategy_registry package that would was deliberately left unmerged).

---

## Minor Issues

- Dead/unreachable code: `strategies.py:2012` (print after return, undefined var), `calc_volume_profile` stub, unused `strategies=[...]` var in scanner:1236, unused `IndicatorCache` SQLite class, `routes_backtest_multi.py` at repo root, `scheduler.py.manual_backup`, `config.py.bak`.
- f-string SQL in `get_ticker_data`/`regime_filter.__main__` (internal, but pattern risk).
- `calc_swing_tp` fallback ATR omits the low-side gap term of True Range.
- `_count_exits`' Swing Trend `reason_tag` maps any profitable exit to 'TP' and non-R7 losers to 'TRAIL' — exit_reason distributions are semantically wrong for Swing Trend.
- `get_summary` hardcodes the 50M capital base; `compute_drawdown` ignores open-position losses (circuit breaker reacts only to realized DD).
- Mixed languages (ID/EN) in comments/log strings; docstrings state "4 strategies" for a 15-strategy registry.
- Panic Rebound backtest equity list skips bars while in-trade (`continue` before append) → equity curve misaligned with bar index (metrics mostly unaffected because they use per-trade P&L).
- Cooldown matches only `exit_reason='STOPPED_OUT'`; swing R-code closes and monitor's `TP_HIT`/`R8_TIME_STOP` never trigger the 3-day cooldown.

---

## Hidden Bugs (hard to detect, wrong behavior)

1. **monitor.py:104 — FLOW_REVERSAL alert has never worked**: queries `stockbit_flow ... AND date=?`; the column is `trade_date` → OperationalError swallowed → `{}` forever. Verified against live schema.
2. **Checker df mutation**: `check_*_signal` add columns (`avg_volume_20d`, `vwap`, `daily_return`, `ma20`) to the shared per-ticker DataFrame inside the scan loop — later strategies see a mutated frame; the indicator cache survives only because its key includes len+last-close.
3. **Anchored-VWAP nondeterminism**: live `check_vwap_reversion_signal` computes VWAP as a cumsum over *however much history was loaded* — the signal changes with the data window, and differs from the backtest's rolling-60 `calc_vwap`. Same checker/backtest mismatch for vol_weighted (VR>1.8 vs backtest's additional close>open & delta terms).
4. **`avg_pf` NaN path**: if every window has PF=999, `np.mean([])` → NaN, and `if avg_pf` is truthy for NaN → NaN stored in summary/score inputs.
5. **Warmup-trade occupancy**: in `run_walk_forward`, trades opened during the prepended warmup tail are filtered from results but still occupy the single position slot into the test window, suppressing early test-window entries non-reproducibly across window boundaries; positions open at window end are force-closed EOD (truncation bias against trailing-exit strategies, i.e. TFB).
6. **`lot_size` cap bypass**: `max(1, lots)` returns 1 lot even when the 30% capital cap computes 0 lots (then only the affordability check saves it).
7. **Forward-test exit-policy mismatch**: `ExitPolicyRegistry` maps 5 strategies; `distribution` (≈97% of ingested signals), TFB, Crash Recovery, Panic Rebound all silently get DEFAULT (3×ATR trail + 10-day time stop) — the SHADOW book measures a policy nobody designed. Also the SHORT shadow book is untradeable for IDX retail, so its results cannot inform deployment.
8. **`check_keystats_freshness`** performs a network fetch + DB write per stale-shocked ticker inside the scan loop (latency spike + write contention mid-scan).
9. **Momentum scan's `_gap_up` OR-branch** fires on any >1-calendar-day gap with +1% — every Monday qualifies as a momentum "streak" candidate if VR passes.
10. **Swing Trend R1's 2-day slope check** treats NaN-yesterday as "negative" (`pd.isna(slope[i-1]) or slope[i-1] < 0`).

---

## Trading Logic Validation (implementation vs stated hypothesis)

| Strategy | Matches hypothesis? | Notes |
|---|---|---|
| Vol-Weighted Entry | **YES** (backtest) / **NO** (live) | Live checker drops the delta>0 & close>open terms; VWAP anchored not rolling. Disabled live — correctly. |
| Momentum Following | **PARTIAL** | Entry matches; trailing exit has intrabar look-ahead (C-8); live exits are fixed −2.5% SL (C-3); `_watch_signal_block` proxy unvalidated vs live gate. |
| VWAP Reversion | **NO** | Backtest uses rolling-60 VWAP; checker uses anchored cumsum VWAP; hypothesis "session VWAP reversion" matches neither on daily bars. Disabled live. |
| Conservative Confirm | **YES** | Simple and consistent; disabled live (negative WF). |
| VWMA Breakout Pullback | **YES** | Entry-filter loop reads next bar's open, but that open *is* the entry — implementable. Note comment says `>` code uses `>=`. |
| Volume Profile POC | **YES** with caveat | POC from 20-bar window is fine; volume distributed uniformly across bar range is a coarse approximation. |
| Inside Bar Breakout | **PARTIAL** | Implements 1-inside-bar, not the documented 2-inside+volume design (flagged in code); no live checker. |
| NR7 Breakout | **YES** | No live checker. |
| ORB | **NO by name** | Daily ATR-around-open proxy, not ORB; honestly documented; true intraday ORB helper exists but is not integrated into WF. |
| Swing Trend | **YES** | Pivot confirmation handled correctly (`_confirmed_pivots`); live monitor replicates R1-R7 faithfully; partial-TP before stop on same bar is optimistic. |
| Trend Following Breakout | **YES** | Gates + 3×ATR ratchet-after-test are correct post-C3; but live monitor doesn't implement MA20-break or 3×ATR trail (C-3), and scan can't open its trades (C-1). |
| Crash Recovery | **YES** | Suspension-proxy via calendar gap is fragile given C-5 (purge fabricates gaps). |
| Panic Rebound | **YES** | No-SL + time-stop encoded with documented rationale; live monitor's generic SL would violate the design if it ever traded via `_check_trade` (it passes explicit sl/tp, so monitor's SL applies — contradicting the "no hard SL" finding). |
| Liquidity Sweep | **YES** | Correctly quarantined pending WF validation. |
| Regime Adaptive | **NO** | Whole-window look-ahead (C-7). |

---

## Walk-Forward Validation

**Is the implementation statistically correct? No — structurally clean, statistically weak.**
Correct: chronological non-overlapping test windows, warmup-tail prepend with post-hoc trade filtering, regime classifier trained on train-window only, pooled expectancy in wf_edge (Σ over trades, not average-of-averages), profit-gate on ranking, per-trade Sharpe fix.
Concerns: (1) nothing is optimized per window, so "walk-forward" ≠ OOS relative to the manual parameter-selection process performed on the same data; (2) 4 windows/ticker (2.2y corpus); (3) EOD force-close at each window boundary penalizes long-hold exits; (4) warmup occupancy effect; (5) Regime Adaptive look-ahead inside the harness; (6) metrics computed on per-trade equity (no intra-trade DD); (7) survivorship — scores refreshed only for `status='active'` tickers.

---

## Data Leakage Audit

| Check | Verdict | Basis |
|---|---|---|
| Look-ahead bias | **FAIL** | C-7 (Regime Adaptive whole-window), C-8 (momentum trail intrabar). TFB/exit_evaluator fixed correctly. |
| Future leakage | **PASS w/ caveat** | Label generation (`label_regime_from_future`) is train-only; last-5-bar rows unlabeled. Caveat: daily in-sample retraining per ticker overstates classifier skill. |
| Survivorship bias | **FAIL (research) / PASS (forward-test)** | WF refresh iterates active tickers only; SHADOW engine force-closes delisted (fixed 2026-06-30). |
| Data contamination | **FAIL** | C-4 (mixed adjusted/raw bases, un-correctable bars), C-5 (real-day deletion), intraday partial bars consumed as final by 16:00 jobs. |
| Parameter leakage | **FAIL** | TFB gates/trail, Panic v3 selection, momentum thresholds all chosen from full-history studies that include every WF test window. |
| Timestamp mismatch | **FAIL (minor)** | 16:00 scan/Fri WF on 14:35 partial bar; `get_flow_from_db` default = latest date (may be prior session); premarket correctly anchors to settled date. |

---

## Signal Funnel & Starvation (long book, per scan)

```
972 active tickers
 → ~959 with OHLCV
 → sector + value-liquidity gates (fail-open on error)
 → adaptive_strategy_selector: needs wf consistency ≥50% AND avg_return>0 on ~4 windows,
   regime-mapped book; disabled trio stripped              ← statistically arbitrary gate (C-6)
 → check_current_entry_signal: only 8/15 strategies have checkers; weekly-trend W-BLOCK
 → flow batch confirm ≥ +2 (fail-CLOSED on fetch error)    ← major cliff in bear tape
 → edge veto (EDGE_SCORE_MODE=off by default → no-op)
 → agent firm (off/shadow default → no-op; enforce → C-9)
 → trend==UPTREND filter (paper_trade.check_trend)
 → open_trade gates (max 5, dup, cooldown, DD breaker)
 → entry price lookup 'price' key                          ← KILLS TFB/momentum/sweep (C-1)
= 0 trades  (observed: paper_trades empty; BUY signals 358 vs SELL 5,831)
```
**Recommendation:** the RS<1.0, regime=UNCERTAIN, sector-weight and flow-score gates should become weighted score inputs (they already exist as edge_score terms) with one calibrated threshold, instead of five independent binary cliffs; keep hard gates only for data-integrity conditions (no data, suspension, blackout). But fix C-1/C-2/C-3 first — starvation is currently masking execution bugs.

---

## Performance Bottlenecks (ranked)

| # | Bottleneck | Est. gain | Effort | Priority |
|---|---|---|---|---|
| 1 | `refresh_wf_scores`: 15 strategies × ~4 windows × ~950 tickers, each strategy recomputing its own MA/ATR/VR on the same frame (cache misses across concat frames) | 3-5× (share indicator frame per window; drop redundant strategies) | M | High |
| 2 | `_purge_duplicate_non_trading_days`: full-table per-row scan + per-date correlated subquery on every fetch | Remove/replace with calendar table: minutes→seconds; also removes C-5 | S | High |
| 3 | `_load_ohlcv_bulk` full-table load 7+×/day (~500k rows) | Load last N=260 bars per ticker via window query: ~4× less I/O/RAM | S | Med |
| 4 | Per-ticker `sqlite3.connect` inside scan loops (keystats, vpin, signal-quality, liquidity) | One connection per scan: fewer lock windows, ~10-20% scan time | S | Med |
| 5 | `run_vpin_daily_batch` single long write txn | commit per N tickers / compute-then-write: removes 18:00 lock window | S | High (correctness) |
| 6 | `check_keystats_freshness` network refetch inline in scan | Move to a pre-scan batch job | S | Med |
| 7 | flow `get_flow_batch` serial 0.8-1.2s/ticker sleeps | Bounded concurrency: scan latency ↓ | M | Low |

---

## Technical Debt

**High:** dual scan pipelines with divergent gate semantics; no unified strategy registry (name-string coupling across 5 maps); DB layer non-centralized (WAL/busy_timeout absent in `data/db.py`); requirements.txt incomplete; live/backtest exit divergence (C-3) is debt as much as it is a bug.
**Medium:** strategies.py as a 2,500-line mixed-concern module; checker/backtest logic duplication per strategy; two flow gates; scheduler job idempotency ad hoc; stale test.
**Low:** dead files/backups at repo root; mixed-language comments; magic numbers (thresholds inline: 1.3/1.8/5.0/50%/33%…) without a config table.

## Refactoring Opportunities (positive ROI only)

1. **One StrategySpec registry** (name, backtest fn, checker fn, exit policy, family, enabled) — collapses 5 hand-synced maps; makes C-1-class breaks impossible (checker contract typed: must return `price`). The unmerged `strategy_registry` package is 70% of this.
2. **Single exit engine shared by backtest, monitor, and forward-test** (forward_testing/exit_evaluator is the right kernel — it is already pure and correct). Kills C-3/C-8 permanently.
3. **Centralize DB connects** through one `connect()` with WAL+busy_timeout (finish the b7431db work — `data/db.py` regressed or never received it).
4. **Data-source unification**: pick one canonical OHLCV source; store raw + adjustment factors; nightly reconciliation vs official EOD; delete the duplicate-day purge in favor of an exchange calendar.
5. Consolidate the momentum-family strategies (vol_weighted/momentum/conservative → one parameterized entry; ORB/NR7/InsideBar → one range-breakout) — halves WF compute and removes correlated pseudo-diversity.

---

## Risk Assessment — how this loses money while looking correct

1. It finally trades (C-1 fixed) and each position risks 2×+ config risk (C-2) into a 150%-notional book with no heat cap — a normal 3-loss day breaches the monthly risk budget silently.
2. Live exits (generic, close-based, partial-bar) realize a different distribution than the WF stats that justified the strategy — the "validated +4.6%/trade" TFB becomes an unvalidated system in production.
3. A corporate action creates a phantom −20% gap (C-4/C-5) → Crash Recovery buys a fictitious crash, or a phantom breakout passes TFB.
4. Stockbit token expires mid-day → one scanner fails open (confirms all), the other fails closed (blocks all); enforce-mode agent outage approves top-20 unfiltered (C-9).
5. Consistency gates on 4 windows rotate capital into strategies whose "edge" is sampling noise (C-6), while the health alert averages only surviving tickers.

## Missing Institutional Features

- Portfolio construction: aggregate exposure/heat caps, sector/correlation limits, vol targeting (Phase 3 Ranker/Sizer is planned but absent).
- Execution realism: order/fill model beyond fixed slippage bps, ARA/ARB limit handling exists only for level capping, no partial fills, no liquidity-participation cap vs ADV.
- Reconciliation: no comparison of paper fills vs achievable prices; no data-quality dashboard (bar completeness, adjustment audit).
- Research hygiene: no experiment tracking, no multiple-testing correction, no embargo between tuning data and validation data, no benchmark comparison (vs IHSG buy-hold).
- Ops: no supervised restart semantics for all jobs (sentinels on 2/20), no dead-man's-switch for scheduler, secrets in `.env`/token files with no rotation, logs split print/logging.
- Point-in-time universe (index membership history) for survivorship-free research.

---

## Final Verdict (0-10)

| Dimension | Score | Rationale |
|---|---|---|
| Trading Logic | **4** | Backtests mostly faithful to hypotheses; two look-ahead defects; live checkers diverge from backtests. |
| Architecture | **5** | Good recent modules (forward_testing); legacy dual-pipeline + string-coupled registries + shared-process scheduler. |
| Statistical Soundness | **3** | 4 windows/ticker, tuned-on-test parameters, correlated strategy family, in-sample classifier. |
| Research Infrastructure | **6** | WF harness, wf_edge pooling, exit-aware rerun scripts, honest negative results (sweep, ADX) — genuinely above hobbyist grade. |
| Maintainability | **5** | 922 tests and good docstrings vs 2.5k-line modules, dead code, env drift. |
| Performance | **5** | Works at current scale; known 35-min WF and lock-prone batch writes. |
| Risk Management | **3** | Sizing bug, no aggregate caps, realized-only circuit breaker, dead flow-reversal alert. |
| Production Readiness | **4** | Rich alerting and fail-soft jobs, but silent fail-opens, non-reproducible env, partial-bar timing. |
| Institutional Readiness | **2** | No portfolio layer, no reconciliation, no PIT universe, single-operator ops. |
| **Overall Engine Quality** | **4** | A capable research scaffold with a broken last mile; not capital-ready. |

## Gate to deployment (minimum, in order)

1. Fix C-1 (checker `price` contract) + C-2 (size off actual stop distance; add aggregate exposure cap).
2. Unify exits on the forward_testing evaluator (C-3/C-8) and re-run WF before trusting any score.
3. Freeze the OHLCV pipeline: single source, adjustment policy, remove the purge, backfill audit (C-4/C-5).
4. Re-baseline wf_scores with ≥5y data or accept per-strategy pooled (cross-ticker) validation instead of per-ticker gates (C-6/C-7).
5. Make every fail-open explicit and alarmed (flow, firm enforce, keystats).
6. Then let the SHADOW forward test (with per-strategy exit policies and a LONG-only tradeable filter) accumulate ≥3 months / ≥100 closed trades before sizing real capital.

## Evidence Limitations

Not fully traced (skimmed or unread): `routes/backtest.py` (UI backtest), `engine/agent_firm/*` internals, `engine/vpin.py`, `engine/smc.py`, `engine/breadth.py`, `engine/liquidity.py`, `engine/trade_plan.py`, `screener/calculator.py`, `stockbit_fetcher.py` parsing, `engine/premover_detector.py`. Verifying the scraper-vs-official-EOD price question requires an external reference feed. Findings above are confined to code actually read plus live-DB checks; none of the critical findings depend on unread modules.
