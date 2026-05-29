# IDX Walkforward — TODO

_Last updated: 2026-05-29 (post-regime-3class merge + holiday calendar + Telegram rotation + agent-firm mode toggle + infra services diagnosed + QuantConnect audit + big-liquidity value filter backlogged + indicator lag audit + BRPT deep-dive gap analysis + G2 suspension detector shipped + 2024-2026 SKB calendar audit)_

---

## ✅ Sprint 11 — Agent-Firm Mode Toggle (SHIPPED 2026-05-27)

- [x] `engine/agent_firm/config.py` — `_runtime`, `set_mode()`, `get_enforce()`, `is_active()` runtime override
- [x] `POST /api/agent/config` — off/shadow/enforce toggle, runtime state persisted in memory
- [x] `GET /api/agent/status` — returns `get_enforce()` (runtime-aware, not static env var)
- [x] `scheduler.py` — uses `get_enforce()` to respect runtime mode
- [x] Topbar pill (OFF/SHADOW/ENFORCE) in `backtest_multi.html` with confirm modal on ENFORCE

---

## ✅ Infrastructure — Sibling Services (RESOLVED 2026-05-27)

- [x] **`idx-walkforward.service`** — was old duplicate of `idx-walkforward-5001.service`, causing port 5001 conflict. Disabled.
- [x] **`idx-monitor.service`** — pointed to `/home/tjiesar/idx-monitor/` (non-existent, never built). Disabled after 411+ crash loops.
- [x] **`idx-walkforward-5001.service`** confirmed sole authoritative service, active and healthy.

---

## ✅ Sprint 8 — News Volume Spike Detector (SHIPPED + VALIDATED 2026-05-27)

- [x] News source: **Google News RSS** (`<ticker> saham`, `hl=id`)
- [x] Schema: `news_mentions(ticker, date, count, headlines_json, updated_at)`
- [x] Daily fetch all tickers @ **17:00 WIB** (`run_news_fetch`)
- [x] Spike rule: `today_count ≥ 3× 30d_avg AND today_count ≥ 3`
- [x] Surface ⚡ tag + section in `flow_broker_report` Telegram
- [x] Cold-start window passed
- [x] **Coverage verified**: 2026-04-26 → 2026-05-26, 17 trading days, 972 tickers, 15,558 rows, 411 spike events
- [x] **Spike → entry filter REJECTED**: back-tested 344 events — win rate 35.5%, avg next-day return -0.58%. News spikes lag price (news chases moves). ⚡ Telegram tag stays as informational only.

---

## ✅ Sprint 10 — Regime 3-Class Redesign (SHIPPED 2026-05-27)

- [x] **`detect_regime()`** — ADX-14 EWM + MA20 5-bar slope → BULL / BEAR / SIDEWAYS (was TRENDING/SIDEWAYS/UNCERTAIN)
- [x] **`RegimeClassifier`** — upgraded to multinomial LogisticRegression (3 classes)
- [x] **Bear dip-scout watchlist** (`engine/watchlist.py`) — adds oversold BEAR names (RSI<35, quality gate), promotes on BULL flip
- [x] **Quality gate** — `backtest_cache` win_rate ≥ 50% + return ≥ 5% (replaced `wf_scores.weighted_score` which was per-ticker normalized, useless as absolute filter)
- [x] **Expiry bumped 30 → 60 days** — backed by hitting-time study: median BEAR→BULL = 59 cal days; 30d window captures only 20% promotions vs 43% at 60d
- [x] **Scheduler bear lane** wired into `scheduled_multi_strategy_scan()` — iterates full `ohlcv_map`, uses real OHLCV for ADX
- [x] **`app.py`** — all UNCERTAIN → SIDEWAYS; regime gate blocks BEAR; 3-class emoji (📈/🐻/➡️)
- [x] **`templates/dive.html`** — regime badge CSS for BULL/BEAR/SIDEWAYS
- [x] **Agent-firm** — `analytics.py`, `smoke.py`, `regime_v1.md` prompt updated; 6 test files migrated TRENDING → BULL
- [x] **Markov regime rejected** — per-ticker too sparse (93% zero BEAR→BULL transitions); signal = echoes current regime label only. Not worth building. (see memory)
- [x] Merged to master (d8a4a51), pushed to origin

---

## ✅ Sprint 10b — IDX Holiday Calendar (SHIPPED 2026-05-27)

- [x] `IDX_MARKET_HOLIDAYS_2026` (21 dates) added to `engine/calendar_filter.py`
- [x] `is_trading_day()` — returns False on weekends + IDX public holidays
- [x] Both `scan_momentum_signals()` and `scheduled_multi_strategy_scan()` gated: skip silently on closed days (no Telegram noise)
- [x] Cuti bersama Idul Adha May 28 confirmed and added

---

## ✅ Security — Telegram Token Rotation (DONE 2026-05-27)

- [x] Old hardcoded default token (`8790169868:AAE6qno0...`) removed from `scheduler.py`
- [x] Token revoked via BotFather
- [x] New token issued and written to `.env`
- [x] Service restarted, new token confirmed live

---

## ✅ Sprint 9 — Strategy Parity & WF Harness Fixes (SHIPPED 2026-05-18)

- [x] Router gap fixed — 6 new signal checkers wired into `check_current_entry_signal()`
- [x] WF harness warmup — 75-bar tail prepend; Trend Following Breakout 0% → 23.2%
- [x] Scheduler fallback `["vwap_reversion", "vol_weighted"]`
- [x] Swing Trend ADX gate loosened; signal fire rate 0.28% → 0.70%
- [x] Score-weight rebalance: ret 0.40 dominant
- [x] `wf_scores` refreshed (2nd run 2026-05-18 22:13): Swing Trend 9 → 127 tickers ≥50%

---

## ❌ Dropped from Roadmap

| Item | Reason |
|------|--------|
| Stockbit community feed scraper | High effort, fragile scraping, account ban risk |
| Full sentiment NLP on Google News | Signal lags price; keyword matching too noisy. Replaced by Sprint 8. |
| Markov regime transition matrix | Per-ticker too sparse; signal redundant with current regime label |
| News spike → entry filter | Back-tested 344 events: win rate 35.5%, avg return -0.58%. News lags price on IDX. |

---

## ✅ Completed (earlier sprints)

Sprint 1 (data foundation), Sprint 2 (perf/N+1), Sprint 3 (foreign accumulation score), Sprint 4 (schedule cleanup), Sprint 5 (RS vs IHSG), Sprint 6 (ATR risk mgmt), Sprint 7 (codebase cleanup), Phase 1–5 (strategies + dive page + fast-mover) — see git log for details.

---

## 🔲 Sprint 12 — Audit Response: Tier 1 Quick Wins

_Source: QuantConnect comparison audit (review.md, 2026-05-27). High impact, low effort._

- [ ] **R1. Execute `PLAN.md` — Frontend Strategy Registry** — Implement the 582-line plan for `dive.html`: JS strategy registry with interactive marker plotting, exit markers, trade detail tooltips, PnL annotation, multi-strategy overlay. ~3 hr. **Gap BRPT #6: dive.html hanya plotting entry markers tanpa exit/trade detail.**
- [ ] **R2. Consolidate `DB_PATH` and config** — Create `config.py` module that reads `.env` once; all modules import from it. Eliminates 6+ duplicate definitions. ~1 hr.
- [x] **R3. Extract `send_telegram()` to shared utility** — `utils/telegram.py` with rate limiting (1s interval) and retry (2 retries, exp backoff). Replaced in `scheduler.py` and `monitor.py`. 8 unit tests. SHIPPED 2026-05-29.
- [ ] **R4. Add `/health` endpoint** — Flask route returning `{"status", "db", "last_scan", "open_trades"}`. Enables systemd health checks. ~30 min.

---

## 🔲 Sprint 13 — Audit Response: Tier 2 Medium Improvements

_Source: QuantConnect comparison audit (review.md, 2026-05-27). Medium impact, medium effort._

- [ ] **R5. Split `scheduler.py` and `app.py`** — 1741-line scheduler → `scheduler/jobs.py`, `scanner.py`, `reports.py`. 2133-line app → `routes/backtest.py`, `flow.py`, `screener.py`, `telegram.py`. ~6 hr.
- [ ] **R6. Portfolio-level backtesting** — Create `engine/portfolio_backtest.py` with multi-ticker concurrent execution, combined equity curve, portfolio Sharpe/drawdown/correlation. ~6 hr. **Gap BRPT #9: single-ticker only, tidak bisa analisis BRPT dalam konteks sektor/portfolio.**
- [ ] **R7. Strategy parameter optimizer** — `engine/optimizer.py` with grid search + walk-forward validation. Tune VR thresholds, ATR multipliers, MA periods per-ticker. ~5 hr. **Gap BRPT #10: parameter BRPT mungkin berbeda dari rata-rata 972 ticker.**
- [ ] **R8. Standardize VPIN** — Consolidate 3 copies of `vpin.py` into `engine/vpin.py`. Wire into scheduler toggle. Add to dive.html. ~2 hr.

---

## 🔲 Sprint 14 — Audit Response: Tier 3 Strategic Items

_Source: QuantConnect comparison audit (review.md, 2026-05-27). Strategic, longer horizon._

- [ ] **R9. Build indicator library** — Extract manual calculations from `strategies.py` into `engine/indicators.py` with auto-warmup, NaN handling, caching. ~6 hr.
- [ ] **R10. Live broker integration research** — Investigate Sinarmas/Mirae/IPOT API; build `broker/` abstraction layer. Research phase first.
- [ ] **R11. Clean up legacy projects** — Archive `idx-walkforward`, delete `idx-walkforward-5002`, decide on `idx-monitor`. Document in `docs/ARCHITECTURE.md`. ~2 hr.
- [ ] **R12. CI/CD and testing** — GitHub Actions for pytest; unit tests for `run_strategy()`, `walk_forward_split()`, `compute_metrics()`. ~5 hr.

---

## 🔲 Sprint 15 — Big-Liquidity Value Signal Filter

_Source: user request (2026-05-27). Pre-entry signal gate: restrict trades to high-liquidity stocks ranked by value metrics._

- [ ] **L1. Define liquidity criteria** — ADV (avg daily volume ≥ threshold), market cap (≥ IDX30/LQ45 minimum), bid-ask spread (≤ 2%). Source: daily OHLCV volume + fundamental data.
- [ ] **L2. Build value composite score** — Fundamental ratios: P/E (trailing), P/B, PEG, dividend yield, EV/EBITDA. Normalize and weight into a single `value_score` per ticker.
- [ ] **L3. Integrate as pre-entry gate** — Insert liquidity + value filter into signal pipeline (`check_current_entry_signal()` or `scan_momentum_signals()`), before regime/quality gates. Reject signals for tickers below liquidity threshold or bottom value quartile.
- [ ] **L4. Back-test filter impact** — Compare win rate, Sharpe, and max drawdown with vs. without the filter. Establish whether value + liquidity improves signal quality on IDX.
- [ ] **L5. Surface in dive.html** — Add `ADV`, `MktCap`, `value_score` columns to screener table. Color-code liquidity tier (high/med/low) and value rank.

---

## 🔲 Sprint 16 — Indicator Lag Audit Fixes

_Source: indicator lag audit (2026-05-27). Critical: 3 strategies use simplified ATR missing gap component. ~15 min fix + revalidation._

### ✅ Critical — Simplified ATR (missing True Range gap components) — FIXED

- [x] **I1. Fix `strategy_inside_bar_breakout()` line 753** — Replaced `(high-low).rolling(14).mean()` → `calc_atr(df, 14)` (full True Range). Affects TP (swing_hi_20 or entry+2×ATR) and position sizing.
- [x] **I2. Fix `strategy_nr7_breakout()` line 836** — Replaced `ranges.rolling(14).mean()` → `calc_atr(df, 14)`. `ranges` kept for NR7 detection. Affects TP (entry+2×ATR) and position sizing.
- [x] **I3. Fix `strategy_orb()` line 945** — Replaced `(high-low).rolling(14).mean()` → `calc_atr(df, 14)`. Affects OR range proxy (open±ATR×0.5), TP (swing_hi_20 or ATR×2), and SL.

### ⚠️ Medium — Inconsistent ATR/ADX smoothing across modules

- [ ] **I4. Audit ATR methodology** — `strategies.py` uses SMA `.rolling().mean()`, `regime_filter.py` uses Wilder's `.ewm(alpha=1/period)`, `premover_detector.py` uses SMA. Document decision or standardize. Defer to Sprint 14 R9 if standardization is chosen.

### ⚠️ Low — Volume ratio self-inclusion

- [ ] **I5. Document VR behavior** — `calc_vol_ratio()` (line 52) includes current bar's volume in both numerator and denominator, dampening VR spikes by ~10%. Add code comment noting this is intentional conservatism.

### Revalidation

- [ ] **I6. Re-run walkforward** — Refresh `wf_scores` for Inside Bar Breakout, NR7 Breakout, ORB after ATR fixes. Compare pre/post win rates and returns.

---

## 🔲 Sprint 17 — BRPT Deep-Dive Gap Analysis (NEW 2026-05-27)

_Source: BRPT.md live analysis — BRPT crash -35% May 2026 exposed critical gaps not covered by any existing sprint. Case study: BRPT 2300 → 1495 with 11-day suspension gap._

### 🔴 Critical — Extreme Event Handling

- [ ] **G1. Backtest auto-rolling pipeline** — Current walk-forward windows are static (last ends Apr 2026). BRPT crash May 2026 is invisible. Build `engine/backtest_roller.py`: triggered weekly/monthly, appends new 3-month window, regenerates `meta_dataset_backtest.json`. ~4 hr. **Evidence: none of 4 windows cover BRPT May crash.**
- [x] **G2. Trading suspension / data gap detector** — SHIPPED 2026-05-28. `engine/suspension_detector.py` with three-layer API (`detect_gaps`, `scan_all`, `get_status`), persisted to new `suspension_events` table, wired fail-soft into `fetch_latest`. Calendar-aware trading-day counter via `engine.calendar_filter.is_trading_day`; classifies suspension vs `data_gap` by 10% price-discontinuity threshold. 15 unit tests. Backfill detected the BRPT/DEWA/BULL May-2026 cluster (`missing_td=5`, ~-22% gap-down). Followed by full SKB audit of 2024/2025/2026 calendars (commits 3efebc4..768079f). Indicator-math edits deferred to R9; Telegram alert is G8; chart marker is G9.
- [ ] **G3. Crash recovery strategy pattern** — No existing strategy handles post-suspension gap-down or crash recovery. Design `strategy_crash_recovery`: detect gap >3 days + gap-down >20%, entry after 1-2 confirmation bars (VR>2x + close>open), SL = low of first post-resume bar (not ATR-based, since ATR is inflated by gap), TP = 50% gap retracement or VWAP resistance. ~5 hr. **Evidence: BRPT -28.1% gap-down → +4.7% bounce, REVERSAL_BREAKOUT fired but no crash-aware strategy exists.**

### 🟡 High Value — Detection-Action Gap

- [ ] **G4. VR spike context classifier** — VR 2.73x after -35% crash ≠ VR 2.73x during normal uptrend. Add `classify_volume_context()` to VR calculation: tag as `crash_absorption`, `breakout_accumulation`, `exhaustion_distribution`, or `normal`. Adjust strategy thresholds per context. ~2 hr. **Evidence: BRPT REVERSAL_BREAKOUT score=55 but near_low=0, above_3ma=0 — misleading without context.**
- [x] **G5. Fundamental data auto-refresh on price shock** — SHIPPED 2026-05-29. `check_keystats_freshness()` in `scheduler.py`: blocks stale+shock signals; allows stale-but-quiet through; attempts inline re-fetch via `.stockbit_token` before blocking. 17 unit tests.
- [ ] **G6. Premover → paper trade auto-execution** — BRPT REVERSAL_BREAKOUT fired May 26 (score=55) but `paper_trades` empty. Add config toggle: `auto_trade_from_premover` (off/shadow/enforce). In shadow mode, log why trade was/wasn't opened (regime block? fundamental fail? calendar blackout?). ~2 hr. **Evidence: 0 BRPT paper trades despite premover alert. Gap between knowing and doing.**

### 🟡 High Value — Adaptive Intelligence

- [ ] **G7. Adaptive strategy switching by regime** — System detects regime (BULL/BEAR/SIDEWAYS) and knows which strategies perform in each (from walk-forward)... but doesn't auto-switch. Add `adaptive_strategy_selector()` in scheduler: BULL+ADX 25-40+near MA → TFB, BULL+ADX>45+extended → Conservative, BEAR → no entry, SIDEWAYS+below MA → VWAP Reversion. ~3 hr. **Evidence: BRPT.md Section 5 heatmap shows clear strategy-regime mapping but it's manual only.**
- [ ] **G8. Post-suspension alert pipeline** — When G2 detects suspension resume, trigger dedicated Telegram alert: "BRPT resumed trading after 11-day suspension, gap-down -28.1%, VR=2.73x, REVERSAL_BREAKOUT=55. CAUTION: crash recovery — high risk." ~1 hr.

### 🟡 High Value — dive.html UI Gaps

_These are frontend-only changes to `templates/dive.html`. They surface the backend intelligence (G2, G5, G7) visually so the user sees it without reading logs._

- [ ] **G9. Suspension gap marker on chart** — When G2 detects a data gap >3 days, render a vertical shaded region + annotation on the chart: "SUSPENDED 11 days" with the gap-down % label. Prevents the chart from misleadingly drawing a continuous line across the gap. Uses `_rawCandles` date delta detection + `_candleSeries.createPriceLine()` or primitive overlay. ~1 hr. **Evidence: BRPT chart draws smooth line May 14→25, hiding the -28.1% gap-down reality.**
- [ ] **G10. Regime → strategy recommendation badge** — Extend the existing regime badge to show a strategy hint. E.g. "SIDEWAYS → try VWAP Reversion" or "BULL → Conservative Confirm". Uses the heatmap from BRPT.md Section 5. Backend: add `recommended_strategy` field to `/api/ticker/<ticker>/full`. Frontend: render below regime badge. ~1 hr. **Evidence: User sees "SIDEWAYS" but has to memorize which strategy works. BRPT.md playbook is manual.**
- [ ] **G11. Crash context annotation on chart** — When price drops >20% within 10 bars, render a shaded red region with "CRASH -35%" label on the chart. Uses lightweight-charts `createPriceLine` or background primitive. Helps user distinguish normal pullback from extreme event. ~0.5 hr. **Evidence: BRPT -35% in 3 weeks rendered identically to a normal 3% dip.**
- [ ] **G12. Fundamental red flag badge** — When G5 detects deteriorating fundamentals (NPM < 0, DER > 3, earnings growth < -100%), render a red badge next to the premover badge: "⚠️ FUND: NPM -4.5% | DER 3.5x". Fetches from `/api/ticker/<ticker>/full` or a new `/api/ticker/<ticker>/fundamental` endpoint. ~1 hr. **Evidence: BRPT REVERSAL_BREAKOUT score=55 looks actionable, but NPM -4.47% + DER 3.47 should give pause. Currently invisible.**

### 🔵 Documentation

- [ ] **G13. BRPT case study in docs/** — Formalize BRPT.md findings into `docs/BRPT_CASE_STUDY.md` as reference for extreme event handling design. Include: timeline, indicator contamination evidence, strategy failure analysis, gap detection methodology. ~1 hr.

---

## 💡 Backlog: Tier 4 Nice-to-Have

- [ ] R13. Structured logging (JSON, correlation IDs, log rotation)
- [ ] R14. Prometheus metrics endpoint (scan duration, signals generated, open trades)
- [ ] R15. Multi-timeframe support (hourly/daily/weekly bar aggregation — like QC TradeBarConsolidator)
- [ ] R16. Strategy warmup caching (avoid recomputing indicators every scan; cache per ticker per day)
