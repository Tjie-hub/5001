# IDX Walkforward — TODO

_Last updated: 2026-05-06 (Sprint 3 shipped)_

---

## ✅ Sprint 3 — Foreign Accumulation Score (SHIPPED 2026-05-06)

- [x] `get_foreign_accumulation(ticker, days=5)` in [flow_filter.py](flow_filter.py) — score_pct = (net_lots_5d / avg_vol_lots) × 100, with ohlcv_dates coverage tracking
- [x] `get_top_foreign_accumulation(top_n=N)` for batch use in scheduler
- [x] `foreign_score REAL` column added to `stockbit_flow` (ALTER TABLE migration in `save_results_to_db`)
- [x] Foreign score ±1 weight wired into `flow_confirms_signal()`: score_pct > 2 → +1, < −2 → −1
- [x] "🏛️ Foreign Flow" section added to 17:15 `flow_broker_report` (top 5 buy + top 5 sell, inline compact format)
- [x] `run_foreign_snapshot()` job at **14:30 WIB** — pre-close Telegram alert for top accumulation/distribution tickers

---

## 🟡 Sprint 8 — News Volume Spike Detector (Cold-start in progress)

> 7/14 days accumulated (2026-04-26 → 2026-05-05). Spike rule meaningful ~2026-05-09.

- [x] News source: **Google News RSS** (`<ticker> saham`, `hl=id`)
- [x] Schema: `news_mentions(ticker, date, count, headlines_json, updated_at)` — auto-created by [news_filter.py](news_filter.py)
- [x] Daily fetch all tickers @ **17:00 WIB** (`run_news_fetch` in [scheduler.py](scheduler.py))
- [x] Spike rule: `today_count ≥ 3× 30d_avg AND today_count ≥ 3` → `has_news_spike(ticker)`
- [x] Surface ⚡ tag + dedicated section in 17:15 `flow_broker_report` Telegram message
- [ ] **Cold-start:** ~7 more days of data needed before spike baseline is reliable (~2026-05-09)
- [ ] Optional follow-up: promote spike from informational tag → entry filter once we observe whether spikes correlate with profitable moves

---

## ❌ Dropped from Roadmap

| Item | Reason |
|------|--------|
| Stockbit community feed scraper | High effort, fragile scraping, account ban risk |
| Full sentiment NLP on Google News | Signal lags price; keyword matching too noisy. Replaced by Sprint 8. |

---

## ✅ Completed

Sprint 1 (data foundation — `broker_flow` covers all investor types incl. `Asing`; dead `broker_summary` table + stub fetchers removed 2026-04-26), Sprint 2 (perf/N+1), Sprint 4 (schedule cleanup), Sprint 5 (RS vs IHSG), Sprint 6 (ATR risk mgmt), Sprint 7 (codebase cleanup), Phase 1 (Strategi 9 — Trend Following Breakout), Phase 2 (Pre-Breakout Detector — IDX-calibrated setup scoring), Phase 3 (Full `/dive/<ticker>` deep-dive page), Phase 4A (TradingView deep dive), Phase 5 (Fast-Mover Forensic Study) — see git log for details.
