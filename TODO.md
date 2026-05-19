# IDX Walkforward — TODO

_Last updated: 2026-05-18 evening (Sprint 9 — strategy parity + WF harness fixes + score rebalance)_

---

## 🟡 Sprint 9 — Strategy Parity & WF Harness Fixes (IN PROGRESS 2026-05-18)

- [x] **Router gap fixed** — 6 new signal checkers wired into `check_current_entry_signal()`: Volume Profile POC, Inside Bar Breakout, NR7 Breakout, ORB, Swing Trend, vwma_breakout_pullback ([engine/strategies.py](engine/strategies.py))
- [x] **WF harness warmup** — prepend 75-bar tail from train to test_df in `run_walk_forward()`; filter trades by `entry_date >= test_start` post-hoc. Fixes Trend Following Breakout (0% → 23.2% avg consistency, 198 tickers ≥50%) ([engine/walkforward_multi.py](engine/walkforward_multi.py:217))
- [x] **Scheduler fallback reverted** — `["vol_weighted", "momentum"]` → `["vwap_reversion", "vol_weighted"]` (fresh WF data: vwap_reversion is #1 by consistency, 36.2%, 365 tickers ≥50%) ([scheduler.py:647,652,678](scheduler.py))
- [x] **Swing Trend ADX gate loosened** — `(20<adx<30 AND roc>0.15)` → `(18<adx<32 AND roc>0.05)`. Gate pass rate 0.28% → 7.41%; final fire rate 0.48% → 0.70%. Backtest + signal checker in parity ([engine/strategies.py:1611,2110](engine/strategies.py))
- [x] **`wf_scores` refreshed** — 8290 rows committed at 2026-05-18 11:42 (1st refresh, pre-Swing-Trend fix)
- [x] **2nd `wf_scores` refresh** — 13:39 result: Swing Trend still 9/840 ≥50% (avg 5.4%) despite ADX loosening. Triggered deeper relaxation below.
- [x] **Scheduler strategy-name bug fixed** — `scan_momentum_signals()` had `STRATEGY = "Momentum Following"` but `wf_scores` stores `"momentum"`. Fix at [scheduler.py:209](scheduler.py). Without it `wf_map` was empty, silently disabling the consistency/blacklist gates.
- [x] **Swing Trend deeper relaxation** — `pullback_reclaim` demoted from hard gate to +10 score component, lookback widened 3 → 5 bars. Mirrored in backtest + live checker ([engine/strategies.py:1635-1650, 2133-2167](engine/strategies.py)). Max score 90 → 100; entry threshold unchanged at 50.
- [x] **Score-weight rebalance** — profit-first formula in [engine/walkforward_multi.py:317-323](engine/walkforward_multi.py): `wr 0.25/ret 0.25/sh 0.20/cons 0.20/dd 0.10` → `wr 0.15/ret 0.40/sh 0.15/cons 0.15/dd 0.15`. Sharpe weight kept low (values span -864 to +490, mostly noise).
- [x] **Verified both fixes** — manual `refresh_wf_scores()` run 2026-05-18 22:13 (47 min, 855/972 tickers). Results:
  - Swing Trend: **9 → 127 tickers ≥50% consistency** (14× lift); avg consistency 5.4% → 17.9%. Goal of ≥50 smashed.
  - Per-ticker #1 picks redistributed: vwap_reversion 204, vol_weighted 150, momentum 114, ORB 108. Rebalance is a softer nudge than simulated — formula is per-ticker so absolute global return matters less than per-ticker normalized rank.
  - Strategy-level avg wscore: vwap_reversion (0.584), vol_weighted (0.536), momentum (0.520), ORB (0.507), conservative (0.493), TFB (0.484). Consistency still dominates global ranking; scheduler fallback `["vwap_reversion","vol_weighted"]` remains a reasonable choice and is left untouched.

---

## ✅ Sprint 3 — Foreign Accumulation Score (SHIPPED 2026-05-06)

- [x] `get_foreign_accumulation(ticker, days=5)` in [flow_filter.py](flow_filter.py) — score_pct = (net_lots_5d / avg_vol_lots) × 100, with ohlcv_dates coverage tracking
- [x] `get_top_foreign_accumulation(top_n=N)` for batch use in scheduler
- [x] `foreign_score REAL` column added to `stockbit_flow` (ALTER TABLE migration in `save_results_to_db`)
- [x] Foreign score ±1 weight wired into `flow_confirms_signal()`: score_pct > 2 → +1, < −2 → −1
- [x] "🏛️ Foreign Flow" section added to 17:15 `flow_broker_report` (top 5 buy + top 5 sell, inline compact format)
- [x] `run_foreign_snapshot()` job at **14:30 WIB** — pre-close Telegram alert for top accumulation/distribution tickers

---

## 🟡 Sprint 8 — News Volume Spike Detector (Cold-start window passed 2026-05-09)

> Cold-start target date (2026-05-09) reached. Verify `news_mentions` table has ≥14 days for at least the active universe before promoting spike → entry filter.

- [x] News source: **Google News RSS** (`<ticker> saham`, `hl=id`)
- [x] Schema: `news_mentions(ticker, date, count, headlines_json, updated_at)` — auto-created by [news_filter.py](news_filter.py)
- [x] Daily fetch all tickers @ **17:00 WIB** (`run_news_fetch` in [scheduler.py](scheduler.py))
- [x] Spike rule: `today_count ≥ 3× 30d_avg AND today_count ≥ 3` → `has_news_spike(ticker)`
- [x] Surface ⚡ tag + dedicated section in 17:15 `flow_broker_report` Telegram message
- [x] **Cold-start window passed** — 2026-05-09 hit; baseline should be stable
- [ ] **Verify coverage**: `SELECT MIN(date), MAX(date), COUNT(DISTINCT date) FROM news_mentions` to confirm continuous daily fetch
- [ ] **Spike → entry filter promotion** (optional): observe whether `has_news_spike` correlates with profitable next-day moves, then wire it into the multi-strategy scan as an additional gate

---

## ❌ Dropped from Roadmap

| Item | Reason |
|------|--------|
| Stockbit community feed scraper | High effort, fragile scraping, account ban risk |
| Full sentiment NLP on Google News | Signal lags price; keyword matching too noisy. Replaced by Sprint 8. |

---

## ✅ Completed

Sprint 1 (data foundation — `broker_flow` covers all investor types incl. `Asing`; dead `broker_summary` table + stub fetchers removed 2026-04-26), Sprint 2 (perf/N+1), Sprint 4 (schedule cleanup), Sprint 5 (RS vs IHSG), Sprint 6 (ATR risk mgmt), Sprint 7 (codebase cleanup), Phase 1 (Strategi 9 — Trend Following Breakout), Phase 2 (Pre-Breakout Detector — IDX-calibrated setup scoring), Phase 3 (Full `/dive/<ticker>` deep-dive page), Phase 4A (TradingView deep dive), Phase 5 (Fast-Mover Forensic Study) — see git log for details.
