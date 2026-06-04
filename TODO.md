# IDX Walkforward — TODO

_Last updated: 2026-06-04 (G9-G12 dive.html annotations shipped)_

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

## ✅ Sprint 12 — Audit Response: Tier 1 Quick Wins (SHIPPED 2026-05-30)

_Source: QuantConnect comparison audit (review.md, 2026-05-27). High impact, low effort._

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

_Source: QuantConnect comparison audit (review.md, 2026-05-27). Medium impact, medium effort._

- [x] **R5a. Split `scheduler.py`** — `scheduler/` package: `state.py` (caches), `utils.py` (shared helpers), `jobs.py` (10 job fns), `scanner.py` (11 scan fns), `reports.py` (4 report fns), `__init__.py` (start_scheduler + re-exports). Old 1887-line `scheduler.py` deleted. SHIPPED 2026-05-30.
- [x] **R5b. Split `app.py`** — `routes/` package: `backtest.py` (backtest/paper/signals/agent), `flow.py` (flow/broker), `screener.py` (ticker/dive/strategy/fastmover/premover/sector/calendar), `telegram.py` (webhook/polling). app.py reduced to 77 lines. 97 tests pass. SHIPPED 2026-05-30.
- [x] **R6. Portfolio-level backtesting** — `engine/portfolio_backtest.py` equal-split capital, equity merge on date intersection, portfolio Sharpe/drawdown/rolling-Sharpe/concurrent-positions, correlation matrix. `routes/portfolio.py` + `/portfolio` dashboard: 4 Lightweight Charts panels, concurrent-positions canvas, sortable per-ticker table, correlation heatmap. 9 unit tests. SHIPPED 2026-05-30.
- [x] **R7. Strategy parameter optimizer** — `engine/optimizer.py`: PARAM_GRIDS (5 strategies), parameterized runners (_run_vol_weighted, _run_momentum, _run_vwap_reversion, _run_conservative, _run_tfb), grid_search, optimize_strategy (WF-validated), save/get DB (optimizer_results table). `POST /api/optimizer/run` + `GET /api/optimizer/result/<ticker>/<strategy>`. 32 unit tests. SHIPPED 2026-05-30.
- [x] **R8. Standardize VPIN** — Merged screener/vpin.py + screener/vpin_multi.py → engine/vpin.py. Shims left for backward compat. vpin key added to /api/ticker/<ticker>/full. VPIN card added to dive.html. SHIPPED 2026-05-30.

---

## 🔲 Sprint 14 — Audit Response: Tier 3 Strategic Items

_Source: QuantConnect comparison audit (review.md, 2026-05-27). Strategic, longer horizon._

- [x] **R9. Build indicator library** — `engine/indicators.py`: 13 `calc_*` functions, `warmup_bars` metadata, `get_warmup()`, `IndicatorCache` (SQLite). Full migration: 9 files updated, no shims. `WARMUP_BARS` in WF harness replaced with `get_warmup()`. SHIPPED 2026-05-30.
- [~] **R10. Live broker integration research** — RESEARCHED 2026-05-30. **Verdict: no accessible IDX broker API exists in Indonesia.** Sinarmas (GUI-only ATS), Mirae Asset ID (no API; India mStock SDK is NSE/BSE only), IPOT (in-app ATM only), Stockbit Sekuritas (JWT surface is read-only market data, no order endpoints found anywhere). Industry-wide OJK/retail gap — not broker-specific. Only viable live execution path: Interactive Brokers (IBKR) via `ib_insync`. **Parked** — no `broker/` abstraction built; revisit if IBKR account opens or a local broker publishes an API.
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

## ✅ Sprint 16 — Indicator Lag Audit Fixes (SHIPPED 2026-05-30)

_Source: indicator lag audit (2026-05-27). Critical: 3 strategies use simplified ATR missing gap component. ~15 min fix + revalidation._

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

## 🔲 Sprint 17 — BRPT Deep-Dive Gap Analysis (NEW 2026-05-27)

_Source: BRPT.md live analysis — BRPT crash -35% May 2026 exposed critical gaps not covered by any existing sprint. Case study: BRPT 2300 → 1495 with 11-day suspension gap._

### 🔴 Critical — Extreme Event Handling

- [x] **G1. Backtest auto-rolling pipeline** — SHIPPED 2026-06-04. `engine/backtest_roller.py`: `backtest_windows` DB table (per-window data), `roll_ticker()`, `roll_all()`, `export_meta_dataset()`. Scheduler: monthly 1st Sunday 10:00 WIB. `POST /api/backtest/roll` on-demand endpoint. Initial population: 3,367 complete + 849 partial windows for 866 tickers; 4,216 records in `out/meta_dataset_backtest.json`. BRPT now has window 5 (2026-04-16→2026-06-04, partial) — May crash visible. 8 unit tests.
- [x] **G2. Trading suspension / data gap detector** — SHIPPED 2026-05-28. `engine/suspension_detector.py` with three-layer API (`detect_gaps`, `scan_all`, `get_status`), persisted to new `suspension_events` table, wired fail-soft into `fetch_latest`. Calendar-aware trading-day counter via `engine.calendar_filter.is_trading_day`; classifies suspension vs `data_gap` by 10% price-discontinuity threshold. 15 unit tests. Backfill detected the BRPT/DEWA/BULL May-2026 cluster (`missing_td=5`, ~-22% gap-down). Followed by full SKB audit of 2024/2025/2026 calendars (commits 3efebc4..768079f). Indicator-math edits deferred to R9; Telegram alert is G8; chart marker is G9.
- [x] **G3. Crash recovery strategy pattern** — SHIPPED 2026-06-05. `strategy_crash_recovery()` in `engine/strategies.py`: detects gap ≥5 cal-days + ≥20% gap-down, enters on VR>2x + bullish close within 3 bars, SL=resume bar low (not ATR), TP=50% gap retracement from resume open. `check_crash_recovery_signal()` for live use (queries `suspension_events`). Added to `STRATEGY_FUNCS`. Bypasses weekly-trend gate (counter-trend). BRPT validation: 1 trade 2026-05-28→29, TP +22.4%. 7 unit tests.

### 🟡 High Value — Detection-Action Gap

- [ ] **G4. VR spike context classifier** — VR 2.73x after -35% crash ≠ VR 2.73x during normal uptrend. Add `classify_volume_context()` to VR calculation: tag as `crash_absorption`, `breakout_accumulation`, `exhaustion_distribution`, or `normal`. Adjust strategy thresholds per context. ~2 hr. **Evidence: BRPT REVERSAL_BREAKOUT score=55 but near_low=0, above_3ma=0 — misleading without context.**
- [x] **G5. Fundamental data auto-refresh on price shock** — SHIPPED 2026-05-29. `check_keystats_freshness()` in `scheduler.py`: blocks stale+shock signals; allows stale-but-quiet through; attempts inline re-fetch via `.stockbit_token` before blocking. 17 unit tests.
- [ ] **G6. Premover → paper trade auto-execution** — BRPT REVERSAL_BREAKOUT fired May 26 (score=55) but `paper_trades` empty. Add config toggle: `auto_trade_from_premover` (off/shadow/enforce). In shadow mode, log why trade was/wasn't opened (regime block? fundamental fail? calendar blackout?). ~2 hr. **Evidence: 0 BRPT paper trades despite premover alert. Gap between knowing and doing.**

### 🟡 High Value — Adaptive Intelligence

- [ ] **G7. Adaptive strategy switching by regime** — System detects regime (BULL/BEAR/SIDEWAYS) and knows which strategies perform in each (from walk-forward)... but doesn't auto-switch. Add `adaptive_strategy_selector()` in scheduler: BULL+ADX 25-40+near MA → TFB, BULL+ADX>45+extended → Conservative, BEAR → no entry, SIDEWAYS+below MA → VWAP Reversion. ~3 hr. **Evidence: BRPT.md Section 5 heatmap shows clear strategy-regime mapping but it's manual only.**
- [x] **G8. Post-suspension alert pipeline** — `send_suspension_resume_alerts()` in `scheduler.py`: queries `suspension_events WHERE resume_date=today AND classification='suspension'`, fires Telegram alert per ticker with duration, gap%, and CAUTION warning. Wired into `fetch_latest()` after `scan_all()`. 9 unit tests. SHIPPED 2026-05-30.

### 🟡 High Value — dive.html UI Gaps

_These are frontend-only changes to `templates/dive.html`. They surface the backend intelligence (G2, G5, G7) visually so the user sees it without reading logs._

- [x] **G9. Suspension gap marker on chart** — SHIPPED 2026-06-04. Marker at resume bar (red ▼ SUSP Nd X%) using existing setMarkers() API; suspension events fetched from DB via /full.
- [x] **G10. Regime → strategy recommendation badge** — SHIPPED 2026-06-04. Tooltip on existing regime badge: "Recommended: [strategy]". Regime×ADX lookup in backend; recommended_strategy field in /full.
- [x] **G11. Crash context annotation on chart** — SHIPPED 2026-06-04. Client-side scan of _rawCandles for >20% drop in 10-bar window; red ▼ CRASH X% markers; de-duplicated within 5 bars.
- [x] **G12. Fundamental red flag badge** — SHIPPED 2026-06-04. Red ⚠️ badge in topbar; flags: NPM<0, DER>3, earn_growth<-100; data from stockbit_keystats via /full.

### 🔵 Documentation

- [ ] **G13. BRPT case study in docs/** — Formalize BRPT.md findings into `docs/BRPT_CASE_STUDY.md` as reference for extreme event handling design. Include: timeline, indicator contamination evidence, strategy failure analysis, gap detection methodology. ~1 hr.

---

## 🔴 Sprint 18 — Crash Early Warning System (NEW 2026-06-04)

_Source: macro_idx.md crash analysis (IHSG -34.84%, 9,135 → 5,952) + agent_firm deep audit. Three broken sensors, five detection gaps, one composite score._

---

### 🔴 Critical — Fix Broken Sensors (ship this sprint)

- [ ] **C1. Fix scheduled_signals BEARISH/SELL path** — `scheduled_signals` generated ZERO SELL/BEARISH signals during the entire -35% crash (only BULLISH + NEUTRAL). Audit `flow_filter.py` verdict mapping and strategy signal generation — the BEARISH enum exists but is never triggered. Verify `flow_verdict` database column accepts BEARISH/SELL values. Test: replay May 8-21 data, confirm SELL signals fire. ~3 hr. **Evidence: 67 BULLISH on May 1, 48 BULLISH on May 14 — mid-crash. System is blind to bear markets.**
- [ ] **C2. Fix bandar_detector accdist calculation** — `broker_accdist` field is always 0.0, producing 100% accumulation bias even during Rp 1.5T foreign outflow days. Debug the Stockbit→DB pipeline: is the raw data missing, or is the accdist formula broken? Cross-validate against `broker_flow` net values (which ARE correct — shows Rp -933M foreign net SELL on Jun 2). Should output negative accdist on heavy distribution days. ~2 hr. **Evidence: Jun 3 — 855 accumulation, 0 distribution while IHSG crashed -3.73% with 452 decliners.**
- [ ] **C3. VPIN crash alert threshold in scheduler** — `daily_screen.vpin` has been above 0.97 for 37 consecutive days (Apr 28–Jun 4) but no alert fires. Add to `scheduler/scanner.py` or `scheduler/jobs.py`: when `AVG(vpin) > 0.8` across >50% of tickers → YELLOW alert. When `AVG(vpin) > 0.95` across >75% of tickers → RED CRITICAL alert. Fire via Telegram. Use `engine/vpin.py` (standardized in R8). ~1.5 hr. **Evidence: VPIN 0.973 on Apr 28 gave 10 days warning before May 8 streak, 36 days before Jun 3 crash.**
- [ ] **C4. Add daily market breadth computation** — Compute advancers/decliners ratio from `ohlcv` table each trading day. Persist to new `market_breadth(date, advancers, decliners, pct_up, pct_down)` table. Alert thresholds: <40% advancers → YELLOW, <25% → ORANGE, <10% → RED. Wire to Telegram. ~2 hr. **Evidence: Breadth collapsed from 65% to 48% on Apr 15 — 9 days before Apr 24 crash. Peak-day breadth was only 42% — distribution already underway at the top.**

---

### 🟠 High — Build Composite Market Risk Score (next sprint)

- [ ] **C5. Composite Market Risk Score engine** — New module `engine/market_risk.py` with `compute_risk_score()` that aggregates:
  - VPIN toxicity (30% weight): avg_vpin across all tickers, % tickers with vpin > 0.8
  - Foreign flow (25% weight): 5-day and 20-day cumulative foreign net (Rp), flow acceleration/deceleration
  - Market breadth (20% weight): advancers/decliners ratio, % stocks above MA20
  - Technical structure (15% weight): IHSG vs MA5/MA20, death cross status, lower high count
  - Volatility (10% weight): daily range vs 20-day avg, extreme range days per month
  - Output: 0-100 score with tiers: GREEN (0-30), YELLOW (31-50), ORANGE (51-70), RED (71-85), CRITICAL (86-100)
  - ~4 hr
- [ ] **C6. Risk score scheduler job** — Run `compute_risk_score()` after daily data fetch (~16:00 WIB). Persist to `market_risk_log(date, score, tier, vpin_component, flow_component, breadth_component, technical_component, volatility_component)`. Fire Telegram alert on tier change (especially YELLOW→ORANGE, ORANGE→RED). ~2 hr.
- [x] **C7. Risk score surface in dashboard** — **SUPERSEDED by Sprint 19 D4-D6.** The watchlist dashboard (`templates/watchlist.html`) is the canonical risk surface with live refresh, component breakdown, and watchlist integration. Component breakdown (VPIN/Flow/Breadth/Technical/Vol weights) included in D4's expandable detail.

---

### 🟡 Medium — Agent Firm Macro Context (following sprint)

- [ ] **C8. Market-wide context in agent firm** — `_build_context()` currently fetches only per-ticker data. Add market-wide data to every agent's context:
  - `market_risk` — current risk score + tier from C5
  - `ihsg_trend` — IHSG close, MA5, MA20, death cross status (last 60d)
  - `aggregate_vpin` — market avg VPIN + % toxic tickers
  - `foreign_flow_summary` — 5d/20d cumulative foreign net (Rp) + trend direction
  - `macro_headlines` — top 5 CNBC/Kontan headlines from `news_mentions` (market-wide, not per-ticker)
  - ~3 hr. **Evidence: Risk Manager currently approves ticker signals unaware that the market is in a -35% bear regime.**
- [ ] **C9. Enrich Risk Manager prompt with macro awareness** — Update `prompts/risk_v3.md` (new version): add macro override rules:
  - If Market Risk Score ≥ RED (71+): auto-veto any BUY signal unless quant score ≥ 4.5 AND ≥3 analysts STRONGLY bullish
  - If Market Risk Score = CRITICAL (86+): veto all BUY signals, auto-approve SELL signals
  - If foreign outflow > Rp 5T in 5 days: reduce max size_hint to 1.0
  - If IHSG below MA20 and death cross active: require technical conviction ≥ 0.7 for approval
  - Include current market risk tier + key macro drivers in the system prompt
  - ~1.5 hr
- [ ] **C10. Sector-level consensus analysis** — After evaluating all ticker candidates in a scan, run a summary pass: (Surface results via D10 Sector Heatmap in watchlist dashboard.)
  - Group decisions by sector (Banking, Mining, Consumer, etc.)
  - If ≥60% of signals in a sector are vetoed → flag "Sector under distribution"
  - If all signals in a sector approved but sector index is declining → flag "Sector divergence warning"
  - Persist to `sector_consensus` table, surface in Telegram
  - ~3 hr. **Evidence: Banking sector (BBCA -11.8%, BBRI -10.4%, BBNI -11.8%) should have triggered sector-wide veto, but per-ticker evaluation missed the pattern.**

---

### 🔵 Validation — Back-test & Enable (when C1-C7 complete)

- [ ] **C11. Back-test agent firm decisions against crash data** — Replay Apr 1–Jun 4 data through the enhanced agent firm (with C8-C9 macro context). Compare:
  - Approval rate before vs after macro context (should drop significantly after Apr 15)
  - Vetoed trades hypothetical P&L (should be negative — validating veto decisions)
  - Approved trades hypothetical P&L (should outperform baseline)
  - Use `analytics.py` cohort_summary to quantify improvement
  - ~3 hr
- [ ] **C12. Staged enforce mode rollout** — After C11 validates improvement:
  - Week 1: `AGENT_FIRM_ENFORCE=true` with Market Risk Score veto only (individual signals still shadow)
  - Week 2: Enable per-signal veto for RED/CRITICAL tier days only
  - Week 3: Full enforce if false-positive rate < 10%
  - Add `agent_decisions` Telegram digest (daily: X approved, Y vetoed, Z bypassed)
  - ~2 hr

---

### 🔴 Critical — Crash-Aware Trade Management (gaps from findings.md audit)

- [ ] **C13. Auto-close paper trades on risk escalation** — When risk score transitions to RED (71+): send Telegram warning listing all open trades with current P&L. When CRITICAL (86+): auto-close all paper trades at market, log rationale to `paper_trades.notes`. Configurable via `AUTO_CLOSE_ON_CRITICAL` env var (default: true). ~2 hr. **Evidence: 67 BULLISH signals May 1 at IHSG 6,957 — system opened trades right before May 8-21 streak (-12.55%).**
- [ ] **C14. Position size scaling by risk tier** — GREEN: 100% normal size. YELLOW: 75%. ORANGE: 50%. RED: 25%. CRITICAL: 0% (block all new entries). Integrate into `paper_trade.open_trade()` — reads current risk score from `market_risk_log` before sizing. ~1.5 hr.

---

### 🟠 High — Scanner & Infrastructure Gaps

- [ ] **C15. Scanner regime gate** — Skip long-only strategies when risk is elevated. GREEN/YELLOW: all strategies. ORANGE: only mean-reversion (VWAP reversion, vol_weighted) + watchlist. RED: only VPIN/breadth/flow monitoring (no signal generation). CRITICAL: pause all scanning, only risk score + foreign flow tracking. Gate at top of `scheduled_multi_strategy_scan()` in `scheduler/scanner.py`. ~2 hr. **Evidence: Scanner ran 10+ long-only strategies every hour during May 8-21 crash (-12.55%), generating noise.**
- [ ] **C16. Foreign flow daily summary table** — New table `foreign_flow_daily(date, foreign_net, local_net, govt_net, total_value, ticker_count, top_buy_5_json, top_sell_5_json)`. New job `run_foreign_flow_summary()` after daily fetch. C5 and D1 read from this instead of scanning raw broker_flow (millions of rows). Backfill historical dates. ~1.5 hr.
- [ ] **C17. Adaptive agent count by risk tier** — GREEN (risk 0-30): 3 agents (Technical, Flow, Risk) — saves ~$0.004/signal. YELLOW (31-50): 5 agents (+Regime, Bull). ORANGE+ (51-100): full 7 agents. Configurable via `AGENT_FIRM_ADAPTIVE_COUNT`. `firm.py` selects agent set based on current risk score. ~1.5 hr.
- [ ] **C18. Sector mapping table** — New table `ticker_sectors(ticker TEXT PRIMARY KEY, sector TEXT, sub_sector TEXT)`. Populated from IDX classification or `stockbit_keystats.sector`. Used by C10 (sector consensus), D10 (sector heatmap), G7 (adaptive strategy). ~2 hr.

---

### 📋 Detection Gap Reference (from macro_idx.md)

| Crash Event | Best Early Warning | Lead Time | Sensor | Status |
|-------------|-------------------|-----------|--------|--------|
| Jan 28 (-7.35%) | Breadth collapse to 22.5% | 7 days | Breadth | C4 adds this |
| Mar 4 (-4.57%) | Lower High #1 (9,174→8,291) | 21 days | Technical | C5 tracks this |
| Apr 24 (-3.38%) | Foreign flow reversal -Rp 2.9T | 9 days | Foreign Flow | C5 tracks this |
| May 8 (-12.55%) | VPIN toxicity spike 0.973 | 10 days | VPIN | C3 alerts this |
| Jun 3 (-3.73%) | VPIN persistent 0.97+ | 36 days | VPIN | C3 alerts this |

---

## 🔵 Sprint 19 — IDX Watchlist Dashboard (NEW 2026-06-04)

_Source: macro_idx.md ticker scan + Sprint 18 market risk score concept. Single-page dashboard surfacing market regime, watchlist, foreign flow, VPIN, breadth._

---

### 🎯 Goal

Replace scattered monitoring (Telegram + DB queries + macro_idx.md reports) with a single auto-refreshing dashboard: **"What is the market doing, and which tickers should I watch?"** — answered in <5 seconds.

---

### 🔴 Core — Backend Data Layer

- [ ] **D1. `/api/dashboard/risk` endpoint** — Aggregates market risk into one JSON response:
  - `risk_score`: composite score + tier (GREEN/YELLOW/ORANGE/RED/CRITICAL) from `market_risk_log`
  - `ihsg`: latest OHLCV, MA5, MA20, death_cross_active, YTD chg%
  - `breadth`: today's advancers, decliners, pct_up, 5-day trend
  - `foreign_flow`: today's net foreign (Rp), 5d cumulative, 20d cumulative, trend
  - `vpin`: market avg VPIN, % tickers >0.8, % tickers >0.95, days above threshold
  - `sectors`: top 3 accumulating, top 3 distributing sectors
  - All queries read-only from walkforward.db. ~2 hr.
- [ ] **D2. `/api/dashboard/watchlist` endpoint** — Computes BUY WATCH / AVOID / WAIT lists:
  - `buy_watch`: tickers with hammer (>3% intraday bounce) AND foreign BUY >Rp 5B AND volume >50M, ranked by foreign net
  - `avoid`: tickers with foreign SELL >Rp 100B in 3 days AND YTD drop >20%
  - `wait`: tickers with hammer BUT foreign SELL (distribution into bounce)
  - Each entry: ticker, close, chg%, intra_bounce, foreign_net_3d, volume, entry_trigger, stop_loss
  - ~2.5 hr.
- [ ] **D3. `/api/dashboard/signals` endpoint** — Recent agent_firm decisions + scheduled_signals:
  - Last 20 agent_decisions: verdict, confidence, ticker, rationale
  - Today's scheduled_signals count by verdict
  - ~1 hr.

---

### 🟠 Core — Frontend Dashboard (`templates/watchlist.html`)

- [ ] **D4. Market Risk Gauge (sticky header)** — 
  - Large risk score (0-100) color-coded background (green→red gradient)
  - Tier label: SAFE / CAUTION / WARNING / DANGER / CRITICAL
  - Mini 7-day trend sparkline. Auto-refresh badge. Click to expand component breakdown.
  - ~3 hr.
- [ ] **D5. IHSG Panel** — 
  - Current IHSG level, day chg%, intraday range, YTD chg%
  - Mini OHLC bars (last 10 days) with inline CSS
  - Key support (5,500 / 5,000) & resistance (6,200 / 6,500) levels
  - MA status line: "MA5 < MA20 — DEATH CROSS ACTIVE" or golden cross
  - ~2 hr.
- [ ] **D6. Breadth & Flow Panel** — Side-by-side gauges:
  - Breadth bar (color-coded), 5-day trend, foreign flow sparkline (10d), VPIN gauge with days-above count
  - ~2.5 hr.

---

### 🟡 Medium — Watchlist Tables (main content)

- [ ] **D7. BUY WATCH Table** — Sortable: Ticker | Price | Chg% | IntraBounce% | Foreign 3d | Volume | Entry | Stop | Dist to Entry. Green/yellow/white row coloring. Click → dive.html. Auto-refresh 60s. ~3 hr.
- [ ] **D8. AVOID Table** — Red-tinted, collapsed by default: Ticker | Price | YTD% | Foreign 3d | Reason. ~1.5 hr.
- [ ] **D9. WAIT Table** — Yellow-tinted: Ticker | Price | Chg% | IntraBounce% | Foreign 3d | Issue. ~1 hr.
- [ ] **D10. Sector Heatmap** — 3×3 grid: sectors colored by aggregate foreign flow (green=accumulation, red=distribution). Based on broker_flow sector mapping. ~2 hr.

---

### 🟡 Medium — Live Features

- [ ] **D11. Auto-refresh with diff highlighting** — 60s poll, yellow flash on changed values, green/red dot for connection status. Pause on hover. ~1.5 hr.
- [ ] **D12. Confirmation Checklist widget** — Sticky sidebar:
  - ☐ Breadth >50% (currently: 6.9% ❌)
  - ☐ IHSG >6,000 (currently: 5,847 ❌)
  - ☐ ≥2 BUY WATCH above entry (0/6 ❌)
  - ☐ Foreign flow leaders positive (3/3 ✅)
  - ☐ VPIN targets <0.90 (0/6 ❌)
  - Progress: "1/5 — STAY IN CASH" with red→green bar
  - ~1.5 hr.

---

### 🔵 Polish — Integration

- [ ] **D13. Wire into app.py** — Register `/dashboard` route, add nav links across all templates. ~1 hr.
- [ ] **D14. Telegram `/dashboard` command** — Compact summary: risk tier + IHSG + top 3 BUY WATCH + checklist. ~1 hr.
- [ ] **D15. Mobile-responsive** — Stack panels vertical, tables → cards, touch-friendly. ~1.5 hr.

---

### 📋 Dependencies

```
C1-C6 (Sprint 18) ────→ D1 (risk endpoint) ──→ D4-D6 (panels)
broker_flow (existing) ──→ D2 (watchlist) ────→ D7-D10 (tables)
agent_decisions ─────────→ D3 (signals) ──────→ D11 (live) + D12 (checklist)
```

**Prerequisites:** C1-C6 should ship before D1. D2-D3 can ship independently.

**Total:** ~26 hours, 15 tasks.

---

## 💡 Backlog: Tier 4 Nice-to-Have

- [ ] R13. Structured logging (JSON, correlation IDs, log rotation)
- [ ] R14. Prometheus metrics endpoint (scan duration, signals generated, open trades)
- [ ] R15. Multi-timeframe support (hourly/daily/weekly bar aggregation — like QC TradeBarConsolidator)
- [ ] R16. Strategy warmup caching (avoid recomputing indicators every scan; cache per ticker per day)
