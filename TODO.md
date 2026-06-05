# IDX Walkforward — TODO

_Last updated: 2026-06-05 (Sprint 17 fully shipped; IHSG crash -2%+ today → Sprint 18 critical)_

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
- [x] Backtest windows exclude non-trading days
- [x] Suspension gap detector uses trading-day counter

---

## ✅ Sprint 12 — Audit Response: Tier 1 Quick Wins (SHIPPED 2026-05-30)

- [x] **R1. Execute `PLAN.md` — Frontend Strategy Registry** — Server-side implementation: `/api/strategy/list` + `/api/strategy/markers/<key>/<ticker>` using canonical engine strategies. Dropdown auto-populated, markers cached per key, daily-only gate, color-coded per strategy. 10 strategies live. SHIPPED (verified 2026-05-30).
- [x] **R2. Consolidate `DB_PATH` and config** — `config.py` at project root: `load_dotenv()` once, exports `DB_PATH` + Telegram vars. Updated 9 files: `routes_backtest_multi.py`, `monitor.py` (4 inline getenv → 1 module-level), `engine/sector_rotation.py`, `engine/sectors_app_filter.py`, `engine/suspension_detector.py`, `screener/fundamental.py`, `screener/db.py`, `flow_filter.py`. 166 tests pass. SHIPPED 2026-05-30.
- [x] **R3. Extract `send_telegram()` to shared utility** — `utils/telegram.py` with rate limiting (1s interval) and retry (2 retries, exp backoff). Replaced in `scheduler.py` and `monitor.py`. 8 unit tests. SHIPPED 2026-05-29.
- [x] **R4. Add `/health` endpoint** — Flask route returning `{"status", "db", "last_scan", "open_trades"}`. 7 unit tests. SHIPPED 2026-05-29.

---

## ✅ Stockbit Screener Integration (SHIPPED 2026-05-30)

- [x] `screener/stockbit_screener.py` — JWT capture from DS browser session, token validation, `fetch_template_tickers(id)`, `run_screener(id)`, `GURU_TEMPLATES` (id 63 high_volume_breakout, id 77 foreign_flow_uptrend)
- [x] `screener/fundamental.py` — `run_query()` gains `ticker_filter` param; safe IN-clause injection
- [x] `screener/routes.py` — `GET /screener/fundamental` accepts `stockbit_template`; `GET /screener/stockbit/templates`; `GET /screener/stockbit/run`
- [x] `templates/screener.html` — Stockbit Filter sidebar with template dropdown and badge indicator
- [x] **ohlcv chart fix** — `/api/ticker/<ticker>/full` now returns 250-bar OHLCV array; dive chart was showing "Chart data loading…" placeholder because `d.ohlcv` was missing from response

### ✅ Follow-up bugs (found + fixed during verification 2026-05-30)

- [x] **SB-1. Silent Stockbit filter failure** — `screener/routes.py` now propagates `stockbit_error` (exception message) and always sets `stockbit_template` in response on failure. `renderResults` in `screener.html` shows ⚠️ in amber in `sbStatus` div. 6 unit tests. SHIPPED 2026-05-30.
- [x] **SB-2. Dead `/api/screener/stockbit/templates` endpoint** — `loadStockbitTemplates()` added to `screener.html`; fetches on `init()`, populates `<select>` dynamically (saved templates preferred, builtin as fallback). Hardcoded options removed. SHIPPED 2026-05-30.

---

## ✅ Sprint 13 — Audit Response: Tier 2 Medium Improvements (SHIPPED 2026-05-30)

- [x] **R5a. Split `scheduler.py`** — `scheduler/` package: `state.py` (caches), `utils.py` (shared helpers), `jobs.py` (10 job fns), `scanner.py` (11 scan fns), `reports.py` (4 report fns), `__init__.py` (start_scheduler + re-exports). Old 1887-line `scheduler.py` deleted. SHIPPED 2026-05-30.
- [x] **R5b. Split `app.py`** — `routes/` package: `backtest.py` (backtest/paper/signals/agent), `flow.py` (flow/broker), `screener.py` (ticker/dive/strategy/fastmover/premover/sector/calendar), `telegram.py` (webhook/polling). app.py reduced to 77 lines. 97 tests pass. SHIPPED 2026-05-30.
- [x] **R6. Portfolio-level backtesting** — `engine/portfolio_backtest.py` equal-weight 10-stock portfolio. 8 unit tests. SHIPPED 2026-05-30.
- [x] **R7. Paper trade expiry + auto-close** — `check_expired_trades()` in `paper_trade.py`: closes trades held >30 days at market. 6 unit tests. SHIPPED 2026-05-30.
- [x] **R8. Sector rotation filter** — `engine/sector_rotation.py`: ranks sectors by momentum, flags top 3. 9 unit tests. SHIPPED 2026-05-30.

---

## ✅ Sprint 14 — Architecture Cleanup (SHIPPED 2026-05-30)

- [x] **R9. Merge `idx_screener` into main project** — `screener/` package migrated, `screener_clone.py` deleted. 22 unit tests.
- [x] **R10. Data layer consolidation** — `data/` package: `db.py`, `fetcher.py`, `ticker_discovery.py`. Single source of truth for DB schema.
- [x] **R11. Delete dead code** — `_archive/` created with 24 files, 2,880 lines archived. `scheduler.py.manual_backup` created. SHIPPED 2026-05-30.

---

## ✅ Sprint 16 — Indicator Lag Audit Fixes (SHIPPED 2026-05-30)

### ✅ Critical — Simplified ATR (missing True Range gap components) — FIXED

- [x] **I1. Fix `strategy_inside_bar_breakout()` line 753** — Replaced `(high-low).rolling(14).mean()` → `calc_atr(df, 14)` (full True Range). Affects TP (swing_hi_20 or entry+2×ATR) and position sizing.
- [x] **I2. Fix `strategy_nr7_breakout()` line 836** — Replaced `ranges.rolling(14).mean()` → `calc_atr(df, 14)`. `ranges` kept for NR7 detection. Affects TP (entry+2×ATR) and position sizing.
- [x] **I3. Fix `strategy_orb()` line 945** — Replaced `(high-low).rolling(14).mean()` → `calc_atr(df, 14)`. Affects OR range proxy (open±ATR×0.5), TP (swing_hi_20 or ATR×2), and SL.

### ⚠️ Medium — Inconsistent ATR/ADX smoothing across modules

- [x] **I4. Audit ATR methodology** — Decision: document, don't standardize. SMA used in `strategies.py` + `premover_detector.py` (position sizing, simpler, less lag). Wilder's EWM in `regime_filter.py` is required by ADX/DMI spec. Comments added to all 3 files. SHIPPED 2026-05-30.

### ⚠️ Low — Volume ratio self-inclusion

- [x] **I5. Document VR behavior** — Added comment to `calc_vol_ratio()`: rolling mean includes current bar (dampens spikes ~10%), intentional conservatism. SHIPPED 2026-05-30.

### Revalidation

- [x] **I6. Re-run walkforward** — 857/972 tickers refreshed 2026-05-30. Post-fix gains: Inside Bar +3.8pp consistency / +17% score, NR7 +4.3pp / +17%, ORB +5.7pp / +7%. Full True Range ATR measurably improves all three strategies. SHIPPED 2026-05-30.

---

## ✅ Sprint 17 — BRPT Deep-Dive Gap Analysis (FULLY SHIPPED 2026-06-05)

_Source: BRPT.md live analysis — BRPT crash -35% May 2026 exposed critical gaps._

### ✅ Critical — Extreme Event Handling

- [x] **G1. Backtest auto-rolling pipeline** — `engine/backtest_roller.py`: 4,216 records in `out/meta_dataset_backtest.json`, `backtest_windows` DB table (4,216 rows). Scheduler: monthly 1st Sunday 10:00 WIB. BRPT window 5 (2026-04-16→2026-06-04) visible. 8 unit tests. SHIPPED 2026-06-04.
- [x] **G2. Trading suspension / data gap detector** — `engine/suspension_detector.py` with three-layer API, `suspension_events` table (1,477 rows), calendar-aware trading-day counter. Detected BRPT/DEWA/BULL May-2026 cluster. 15 unit tests. SHIPPED 2026-05-28.
- [x] **G3. Crash recovery strategy pattern** — `strategy_crash_recovery()` in `engine/strategies.py`: gap ≥5 cal-days + ≥20% gap-down, VR>2x entry within 3 bars, SL=resume bar low, TP=50% gap retracement. BRPT validation: +22.4%. 7 unit tests. SHIPPED 2026-06-05.
- [x] **G4. VR spike context classifier** — `classify_volume_context(df)` in `engine/indicators.py`: crash_absorption/exhaustion_distribution/breakout_accumulation/normal. Added to `score_ticker_reversal()`. REVERSAL_BREAKOUT alerts show context tags. 6 unit tests. SHIPPED 2026-06-05.

### ✅ High Value — Detection-Action Gap

- [x] **G5. Fundamental data auto-refresh on price shock** — `check_keystats_freshness()` in `scheduler/scanner.py`: blocks stale+shock signals, allows stale-but-quiet through, attempts inline re-fetch. 17 unit tests. SHIPPED 2026-05-29.
- [x] **G6. Premover → paper trade auto-execution** — `get/set_premover_mode()`, `evaluate_premover_trade()` (DD, max_open, duplicate, regime gates), `run_premover_eod()` in `scheduler/jobs.py`. `GET/POST /api/paper/premover_mode`. Telegram shadow summary. 8 unit tests. SHIPPED 2026-06-05.
- [x] **G7. Adaptive strategy switching by regime** — `adaptive_strategy_selector(ticker, df, min_consistency)` in `scheduler/scanner.py`: regime+ADX sub-band → strategy candidates via `_REGIME_STRATEGY_MAP`, consistency gate, fallback to `get_ticker_best_strategies()`. BEAR always returns []. Wired into `scheduled_multi_strategy_scan()`. 5 unit tests. SHIPPED 2026-06-05.
- [x] **G8. Post-suspension alert pipeline** — `send_suspension_resume_alerts()` in `scheduler/__init__.py`: queries `suspension_events WHERE resume_date=today`, fires Telegram alert with duration, gap%, CAUTION warning. 9 unit tests. SHIPPED 2026-05-30.

### ✅ High Value — dive.html UI Gaps

- [x] **G9. Suspension gap marker on chart** — Red ▼ SUSP Nd X% marker at resume bar. SHIPPED 2026-06-04.
- [x] **G10. Regime → strategy recommendation badge** — Tooltip on regime badge: "Recommended: [strategy]". SHIPPED 2026-06-04.
- [x] **G11. Crash context annotation on chart** — Client-side scan for >20% drop in 10-bar window; red ▼ CRASH X% markers. SHIPPED 2026-06-04.
- [x] **G12. Fundamental red flag badge** — Red ⚠️ badge: NPM<0, DER>3, earn_growth<-100. SHIPPED 2026-06-04.

### ✅ Documentation

- [x] **G13. BRPT case study in docs/** — `docs/BRPT_CASE_STUDY.md`: full timeline, ATR inflation, VR miscontextualization, strategy failure table (10 strategies), crash recovery validation, 5 design lessons. SHIPPED 2026-06-05.

---

---

# 🔲 OUTSTANDING — Sorted by Critical Priority

---

## 🔴 #1 — Sprint 18: Crash Early Warning System

_Source: macro_idx.md crash analysis (IHSG -34.84%, 9,135 → 5,952). Three broken sensors, five detection gaps, one composite score._

**⚠️ URGENT: IHSG crashing -2%+ today (June 5), approaching 5,600 from 5,839 close. System generated 67 BULLISH signals on May 1, 48 BULLISH on May 14 — mid-crash. System is blind to bear markets.**

### 🔴 Critical — Fix Broken Sensors (ship first)

- [x] **C1. Fix scheduled_signals BEARISH/SELL path** — Added `scan_distribution_signals()`: queries `stockbit_flow` for score≤-3 BEARISH tickers, filters by regime (skip BULL) + declining price, saves to `scheduled_signals` with `signal_direction='SELL'`. Extracted `_ensure_scheduled_signals_table()` + `_save_signals_to_db()` helpers; added `signal_direction` column (migration-safe). API returns `signal_direction` field. 11 unit tests. SHIPPED 2026-06-05.
- [x] **C2. Fix bandar_detector accdist calculation** — Root cause: `broker_accdist` stores text labels ('Acc'/'Dist'); `CAST(text AS REAL)` = 0.0 in SQLite, making every query that treated it as numeric return 100% accumulation bias. Added `accdist_label_to_score()` (7-level map: Big Acc→+3 … Big Dist→-3), `get_market_accdist_summary(date)` (dist_pct, acc_pct, avg_numeric_score, label). Wired into scanner daily log and `/api/market/accdist` endpoint (with `?series=1` for 30-day time series). 19 unit tests. SHIPPED 2026-06-05.
- [x] **C3. VPIN market toxicity sensor** — `get_market_vpin_summary(conn, date)` in `engine/vpin.py`: aggregates daily_screen vpin column into avg_vpin + pct_above_08 + pct_above_095 + label (GREEN/YELLOW/ORANGE/RED/CRITICAL). Thresholds: CRITICAL when pct_above_095≥75% or avg≥0.95 (matches Apr 28 crash: avg=0.973, 85% >0.95). Wired into scanner with Telegram alert on CRITICAL/RED. `/api/market/vpin` endpoint with `?series=1`. 12 unit tests. SHIPPED 2026-06-05.
- [x] **C4. Market breadth sensor** — `engine/breadth.py`: `get_market_breadth(conn, date)` computes advancers/decliners (vs prev trading day close), adv_dec_ratio, pct_advancing, pct_above_ma20 (20-day rolling), label (BULL_MARKET/NEUTRAL/WEAK/BEAR_MARKET). Wired into scanner daily log. `/api/market/breadth` endpoint with `?series=1`. 11 unit tests. SHIPPED 2026-06-05.
- [x] **C5. Technical death cross / lower high detector** — `engine/technicals.py`: `detect_ihsg_technicals(conn, date)` detects MA5/MA20 death cross (MA5 < MA20), lower high sequence (3-segment peak comparison), support breaks at 6,200/6,000/5,500. Label: BEARISH_TREND/DOWNTREND/NEUTRAL/UPTREND. Wired into scanner with Telegram alert on BEARISH_TREND+death_cross. `/api/market/technicals` endpoint. 12 unit tests. SHIPPED 2026-06-05.
- [x] **C6. Multi-sensor composite risk score** — `engine/risk_score.py`: `compute_market_risk_score()` weighted ensemble: VPIN 30% + accdist 20% + breadth 20% + technicals 15% + foreign flow 15% → 0-100 score, GREEN/YELLOW/ORANGE/RED/CRITICAL tiers. Wired into scanner pre-scan log. `/api/market/risk` endpoint (full sensor breakdown + sensors dict). 8 unit tests. SHIPPED 2026-06-05.

### 🟠 High — Alert & Response Infrastructure

- [x] **C7. Telegram alert routing by risk tier** — `engine/risk_alert.py`: `route_risk_alert()` CRITICAL→immediate Telegram, RED/ORANGE→market_risk_log (sent=0), GREEN→silent. `get_pending_risk_alerts()`, `mark_alerts_sent()`, `build_risk_summary_message()`. Scheduler: hourly RED bundle at :30, EOD ORANGE/YELLOW summary at 16:00. Wired into scanner post-risk-score computation. 10 unit tests. SHIPPED 2026-06-05.
- [x] **C8. Scheduled market health report** — `engine/health_report.py`: `build_market_health_report()` formats risk score, VPIN, breadth, accdist, foreign flow, IHSG technicals (death cross flags, support breaks) as Telegram message. Scheduler: 08:45 WIB Mon-Fri via `run_market_health_report()`. 8 unit tests. SHIPPED 2026-06-05.
- [x] **C9. Auto circuit breaker** — `engine/circuit_breaker.py`: `CircuitBreakerState` enum (OPEN/CLOSED), `check_circuit_breaker(risk)` → OPEN only on CRITICAL tier (fail-open for all others). `get_market_risk_for_circuit_breaker()` helper assembles live sensor data. `run_premover_eod()` gates on breaker state: OPEN → log + Telegram alert + return early. 9 unit tests. SHIPPED 2026-06-05.
- [x] **C10. VPIN batch compute for all tickers** — `run_vpin_daily_batch(date_str)` in `scheduler/jobs.py`: runs `calc_vpin()` for all tickers, persists to `vpin_scores` table (ticker, date, vpin, vpin_label, bucket_count, error) and updates `daily_screen.vpin`. Scheduler: Mon-Fri 18:00 WIB. `ensure_vpin_scores_table()` helper. 7 unit tests. SHIPPED 2026-06-05.
- [x] **C11. Backfill VPIN history** — `run_vpin_backfill(days=90)` in `scheduler/jobs.py`: iterates daily_screen dates for last 90 days, skips tickers already in vpin_scores, computes and saves gaps. Fail-open per ticker. SHIPPED 2026-06-05.

**Total Sprint 18:** ~26 hours, 11 tasks.

---

## 🟠 #2 — Sprint 19: IDX Watchlist Dashboard

_Source: macro_idx.md ticker scan + Sprint 18 market risk score concept. Single-page dashboard: "What is the market doing, and which tickers should I watch?"_

### 🎯 Goal

Replace scattered monitoring (Telegram + DB queries + macro_idx.md reports) with a single auto-refreshing dashboard — answered in <5 seconds.

### 🔴 Core — Backend Data Layer

- [x] **D1. `/api/dashboard/risk` endpoint** — Aggregates market risk: `risk_score` + tier, `ihsg` (OHLCV, MA5, MA20, death_cross, YTD), `breadth` (advancers/decliners, pct_up, trend), `foreign_flow` (today, 5d, 20d, trend), `vpin` (avg, % >0.8, % >0.95), `sectors` (top 3 accumulate/distribute). Read-only from walkforward.db. ~2 hr.
- [x] **D2. `/api/dashboard/watchlist` endpoint** — BUY WATCH / AVOID / WAIT lists: hammer (>3% intraday bounce) + foreign BUY >Rp 5B + volume >50M for buy_watch; foreign SELL >Rp 100B in 3d + YTD drop >20% for avoid; hammer + foreign SELL for wait. 10 unit tests. SHIPPED 2026-06-05.
- [ ] **D3. `/api/dashboard/signals` endpoint** — Last 20 agent_decisions + today's scheduled_signals count by verdict. ~1 hr.

### 🟠 Core — Frontend Dashboard (`templates/watchlist.html`)

- [ ] **D4. Market Risk Gauge (sticky header)** — Large risk score (0-100) color-coded, tier label (SAFE/CAUTION/WARNING/DANGER/CRITICAL), mini 7-day sparkline, auto-refresh badge. ~3 hr.
- [ ] **D5. IHSG Panel** — Current level, day chg%, intraday range, YTD, mini OHLC bars (10d), key support/resistance (5,500/5,000/6,200/6,500), MA status line. ~2 hr.
- [ ] **D6. Breadth & Flow Panel** — Side-by-side gauges: adv/dec ratio, % above MA20, foreign net flow bar chart (10d). ~2 hr.
- [ ] **D7. BUY WATCH Table** — Sortable columns: ticker, close, chg%, bounce%, foreign_net_3d, volume, entry_trigger, stop_loss. Color rows by conviction. ~3 hr.
- [ ] **D8. AVOID Table** — Tickers to avoid: foreign distribution + YTD laggards. Red-tinted rows. ~1.5 hr.
- [ ] **D9. WAIT List** — Distribution-into-bounce tickers. Amber rows. ~1 hr.
- [ ] **D10. Sector Heatmap** — Grid: sectors as rows, columns for momentum/flow/VPIN. Green→red gradient. ~2 hr.

### 🟡 Nice-to-Have

- [ ] **D11. Agent-Firm Live Feed** — Scrollable log of agent decisions with verdict badges. ~1.5 hr.
- [ ] **D12. Checklist Panel** — Today's auto-checklist: data fetched ✓, signals scanned ✓, trades reviewed ✓. ~1 hr.
- [ ] **D13. VPIN Toxicity Panel** — Gauge + % tickers above threshold + 30-day trend sparkline. ~1.5 hr.
- [ ] **D14. Telegram `/dashboard` command** — Compact summary: risk tier + IHSG + top 3 BUY WATCH. ~1 hr.
- [ ] **D15. Mobile-responsive** — Stack panels vertical, tables → cards, touch-friendly. ~1.5 hr.

### 📋 Dependencies

```
C1-C6 (Sprint 18) ────→ D1 (risk endpoint) ──→ D4-D6 (panels)
broker_flow (existing) ──→ D2 (watchlist) ────→ D7-D10 (tables)
agent_decisions ─────────→ D3 (signals) ──────→ D11 (live) + D12 (checklist)
```

**Prerequisites:** C1-C6 should ship before D1. D2-D3 can ship independently.

**Total Sprint 19:** ~26 hours, 15 tasks.

---

## 🟡 #3 — Sprint 15: Big-Liquidity Value Signal Filter

_Source: user request (2026-05-27). Pre-entry signal gate: restrict trades to high-liquidity stocks ranked by value metrics._

- [ ] **L1. Define liquidity criteria** — ADV (avg daily volume ≥ threshold), market cap (≥ IDX30/LQ45 minimum), bid-ask spread (≤ 2%). Source: daily OHLCV volume + fundamental data.
- [ ] **L2. Build value composite score** — Fundamental ratios: P/E (trailing), P/B, PEG, dividend yield, EV/EBITDA. Normalize and weight into `value_score` per ticker.
- [ ] **L3. Integrate as pre-entry gate** — Insert liquidity + value filter into signal pipeline (`check_current_entry_signal()` or `scan_momentum_signals()`), before regime/quality gates. Reject signals below liquidity threshold or bottom value quartile.
- [ ] **L4. Back-test filter impact** — Compare win rate, Sharpe, and max drawdown with vs. without filter.
- [ ] **L5. Surface in dive.html** — Add `ADV`, `MktCap`, `value_score` columns to screener table. Color-code liquidity tier and value rank.

**Total Sprint 15:** ~10 hours, 5 tasks.

---

## 🔵 #4 — Backlog: Tier 4 Nice-to-Have

- [ ] R13. Structured logging (JSON, correlation IDs, log rotation)
- [ ] R14. Prometheus metrics endpoint (scan duration, signals generated, open trades)
- [ ] R15. Multi-timeframe support (hourly/daily/weekly bar aggregation — like QC TradeBarConsolidator)
- [ ] R16. Strategy warmup caching (avoid recomputing indicators every scan; cache per ticker per day)
