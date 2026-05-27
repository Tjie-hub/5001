# IDX Walkforward — TODO

_Last updated: 2026-05-27 (post-regime-3class merge + holiday calendar + Telegram rotation + agent-firm mode toggle + infra services diagnosed)_

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
