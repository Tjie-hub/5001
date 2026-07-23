# Production Trading Engine — Full Pipeline Audit

**Date:** 2026-07-22
**Scope:** Data ingestion → feature generation → ranking → signal generation → scheduler → daily outputs
**Method:** Static code review of the production path (scheduler jobs, engine, screener, flow, paper-trade, exits kernel) plus schema inspection of the workspace `walkforward.db`. No code was modified.

**Severity legend (trading impact):**
- **Critical** — can silently corrupt signals/positions or lose money on real setups
- **High** — materially degrades signal quality, risk control, or recoverability
- **Medium** — wrong-but-bounded behavior, staleness, or operator-facing gaps
- **Low** — cosmetic, dead code, or maintainability

**Complexity legend:** Trivial (<1h) · Low (hours) · Medium (1–3 days) · High (>3 days incl. data migration/validation)

---

## Executive summary

The architecture is unusually disciplined for a system of this size (single exit kernel, edge/veto tiers, dedup sentinels, dead-man heartbeat, `is_final` bar separation, display-name alias resolution, 1,193 passing tests). The defects found are concentrated in four themes:

1. **Unit/basis integrity of the OHLCV corpus** — volume units are ambiguous between the two ingestion sources, and corporate actions are recorded but never applied. These two issues (C-1, C-2) undermine every volume- and price-history-derived feature downstream.
2. **Silently dead wiring** — six scheduler jobs/reports are defined, documented, imported… and never registered. RED-tier market-risk alerts are *never delivered*.
3. **Fail-open as default philosophy** — liquidity, fundamental, flow, and VPIN gates all pass when data is missing or when the gate itself throws. Combined with no last-bar freshness checks, an upstream outage doesn't stop trading; it removes the safety rails while trading continues.
4. **Fresh-DB bootstrap is broken** — proven against the workspace DB: `stockbit_flow` lacks the columns production INSERTs, and `ohlcv` is never created by app startup. The system only works because the long-lived production DB carries legacy schema.

No hard look-ahead/leakage was found in the production signal path (the previously known 'Regime Adaptive' whole-window leak is already removed; the exit kernel explicitly avoids intrabar trail look-ahead). The main "leakage-adjacent" risks are *staleness* ones: signals evaluated on bars whose date is never checked.

| # | Finding | Area | Severity | Fix complexity |
|---|---------|------|----------|----------------|
| C-1 | Volume-unit ambiguity: scraper vs yfinance bars in one `ohlcv` table | Ingestion | **Critical** | Medium |
| C-2 | Corporate actions written, never applied — raw prices everywhere | Ingestion | **Critical** | Medium–High |
| H-1 | RED/ORANGE/YELLOW risk alerts never delivered (jobs unscheduled) | Scheduler/Risk | **High** | Trivial |
| H-2 | Dead report jobs: fetch/flow-broker/auto-trade reports never run | Outputs | **High** | Trivial |
| H-3 | No last-bar freshness guard in any scan or the monitor | Features/Signals | **High** | Low |
| H-4 | EOD trade plan has no liquidity floor; vol-spike source biases to illiquid names | Ranking | **High** | Low |
| H-5 | Scraper-derived EOD bars are approximations, yet are the declared authority | Ingestion | **High** | Medium |
| H-6 | Fresh-DB bootstrap broken (3 divergent `stockbit_flow` schemas; `ohlcv` never created) | Ingestion/Ops | **High** | Low–Medium |
| H-7 | `DB_PATH` relative in `.env` + divergent stale fallbacks → split-brain DB risk | Scheduler/Ops | **High** | Low |
| H-8 | `_db_connect` NameError makes the VPIN entry filter a silent no-op when enabled | Signals | **High** (latent) | Trivial |
| M-1 | Flow "closing session" windows wrong; 16:xx closing-auction bars excluded | Features | Medium–High | Low |
| M-2 | Gates fail-open on missing data (liquidity, fundamental, flow, market-cap) | Ranking/Signals | Medium | Low |
| M-3 | Watchlist sources have no age cap — stale scans silently feed next-day plans | Ranking | Medium | Low |
| M-4 | Index-membership flags (`in_idx30/lq45/idx80`) have no writer; constituents frozen | Universe | Medium–High | Medium |
| M-5 | EOD coverage fallback inserts stale last-bar as "today's" screen row | Features | Medium | Low |
| M-6 | Job-chain failure handling: sentinel-before-work; no dependency/retry | Scheduler | Medium | Medium |
| M-7 | Screener writes and strategy scans race at identical cron minutes | Scheduler | Medium | Low |
| M-8 | 16:00 daily scan trades on pre-final data; partial-day screen labels gate full-day signals | Signals | Medium | Low |
| M-9 | Broker-flow: skip-if-exists blocks refresh; no 429 retry | Ingestion | Medium | Low |
| M-10 | open_trade race conditions on max_open/duplicate checks | Signals/Risk | Medium | Low–Medium |
| M-11 | Incremental yfinance marks intraday partial bars `is_final=1`; `md>=today` skip | Ingestion | Medium | Low |
| M-12 | Suspensions marked "delisted" by discovery; discovery manual-only | Universe | Medium | Medium |
| L-1..L-8 | Metrics column bug, hardcoded capital, dead `_parse_args`, 2027 calendar cliff, lunch-window drop, misc | Various | Low | Trivial–Low |

---

## 1. Data ingestion

### C-1 — Volume-unit ambiguity between the two OHLCV sources (Critical)

**Where:** `screener/idx_scraper.py:52-90` vs `data/fetcher.py:_save_df` vs `flow_filter.py:get_foreign_accumulation` / `stockbit_fetcher.py:fetch_flow`.

**Root cause:** The same Stockbit tradebook field `lot.raw` is interpreted **two contradictory ways** in the same codebase:
- `idx_scraper._ticks_from_raw` stores `volume: total_lot` with the inline comment *"lot.raw is already in shares"* — while its own docstring says *"volume: (buy_lot + sell_lot) * 100 shares"*. One of these is wrong by 100×.
- `stockbit_fetcher.fetch_flow` and `flow_filter._parse_bars` treat the identical field as **lots** (`net_lot`, `NetLot` reporting, delta in lots).
- yfinance backfill writes `ohlcv.volume` in **shares**.

Since the scraper's 16:15 EOD run `INSERT OR REPLACE`s the day's bar and yfinance fills history, the `ohlcv` table potentially mixes two volume bases across date ranges per ticker. Everything consuming `ohlcv.volume` inherits the ambiguity:

- `engine/liquidity.py` ADV gate: `ADV_MIN_LOTS = 500_000` **lots** compared against `AVG(volume)` — if volume is shares, the effective floor is 5,000 lots (100× laxer than named); if the scraper writes lots while history is shares, `vol_ratio` cliffs at the source boundary.
- Rp-turnover gate `AVG(close*volume) >= 5e9` — 100× error swings this from "everything passes" to "everything fails".
- `flow_filter.get_foreign_accumulation` divides `AVG(volume)/100` (assumes shares) to normalize foreign flow — wrong by 100× under the other basis.
- `calc_vol_ratio`, VWAP/VWMA weighting, breadth, premover `volume_dry_up`, VPIN bucketing.

**Trading impact:** Critical. The liquidity filters — the stated defense against illiquid names — and every volume-spike feature are only correct under one interpretation, and the codebase asserts both.

**Fix:** (1) Empirically verify one ticker-day against the exchange (e.g., BBCA volume in shares is O(10⁷–10⁸)); (2) declare a single canonical unit for `ohlcv.volume`, convert at the ingestion boundary in exactly one function; (3) one-off migration to re-base historical scraper rows if inconsistent; (4) add a unit assertion test (cross-source same-day volume ratio ≈ 1, not ≈ 100).

**Complexity:** Medium (the code change is small; the historical-data reconciliation and validation is the work).

### C-2 — Corporate actions are captured but never applied (Critical)

**Where:** `data/market_schema.py` (design note: *"the ohlcv basis is RAW exchange prices… research adjusts via this table"*), `data/fetcher.py:_save_actions` (writer). **Zero readers** in `engine/`, `scheduler/`, `screener/` (grep-verified; only a rebuild script and tests touch the table).

**Root cause:** The Phase-2A design assigned adjustment responsibility to "research", but the **production** engine also consumes multi-month price history (MA50/200, 52-week highs, `_detect_price_shock`, `detect_regime`, Crash Recovery / Panic Rebound crash detection, macro panic 200-day MA) and nothing adjusts it.

**Trading impact:** Critical whenever a split/large dividend occurs in a scanned name (stock splits are routine on IDX):
- A 1:2 split reads as a −50% one-day crash → `_detect_price_shock` fires (blocking keystats gate), **Crash Recovery may auto-buy a fake crash**, the suspension/crash-recovery classifiers misfire, regime flips to BEAR, every MA/momentum feature is broken for weeks.
- IHSG-relative RS and the panic-state gate are polluted if a constituent's raw series jumps.

**Fix:** A load-time adjustment layer in `data/loaders._load_ohlcv_bulk` (split-ratio back-adjustment from `corporate_actions`), or minimally: (a) an "action within lookback" exclusion flag per ticker consumed by the crash/shock detectors, (b) a Telegram alert when a split lands in the active universe.

**Complexity:** Medium–High (correctness across both ingestion sources, cache invalidation, backtest parity).

### H-5 — Scraper bars are approximations, yet the scraper is the EOD authority (High)

**Where:** `idx_scraper._ohlcv_from_ticks`, `save_ohlcv_to_db(is_final=True)`; `data/reconcile.py`.

**Root cause:** Final daily bars are derived from 1-minute tradebook aggregates: `high/low` = max/min of per-minute prices (misses intrabar extremes), `open` = first tradebook minute (may miss opening auction), volume = buy+sell lot sum. These bars **replace** yfinance bars (`INSERT OR REPLACE`) and yfinance is forbidden from correcting them (`WHERE ohlcv.close IS NULL`). Reconciliation compares **close only**, at 0.1%, alert-only.

**Trading impact:** High. ATR (position sizing, trail stops, TP), swing-high TP targets, gap-aware exit fills, and `classify_volume_context` all consume high/low that is systematically understated on volatile days — exactly when exits matter.

**Fix:** Either make yfinance (or another official EOD source) the *final* authority with the scraper providing intraday-only provisional bars, or extend reconciliation to O/H/L/V with auto-repair for beyond-tolerance rows.

**Complexity:** Medium.

### H-6 — Fresh-database bootstrap is broken; three divergent `stockbit_flow` schemas (High)

**Where:** `stockbit_fetcher.init_flow_db` vs `flow_filter.save_results_to_db` vs migration-by-ALTER (`foreign_score` only); `app.py:__main__` (never calls `data.db.init_db`).

**Root cause & evidence:** `init_flow_db()` (run at every app start) creates `stockbit_flow` **without** `composite_score/verdict/smart_money`, but both `run_flow()` and `flow_filter.save_results_to_db()` INSERT those columns. The workspace DB proves it: its `stockbit_flow` has the incomplete schema, so every flow save would raise `OperationalError`. Separately, nothing in `app.py` startup creates the `ohlcv` table (`data.db.init_db` is never invoked) — also confirmed missing in the workspace DB.

**Trading impact:** High for disaster recovery / new environment: on a rebuilt DB the entire flow pipeline and OHLCV persistence fail until someone intervenes manually. Zero impact on the current long-lived DB (legacy schema already has the columns) — which is why it has gone unnoticed.

**Fix:** One idempotent schema module (single CREATE + ALTER migration list per table), executed at startup; delete the two stale CREATE TABLE variants.

**Complexity:** Low–Medium.

### M-9 — Broker-flow persistence: skip-if-exists + no rate-limit retry (Medium)

**Where:** `stockbit_fetcher.run_flow` (broker section), `fetch_broker_flow`.

**Root cause:** If *any* broker rows exist for (ticker, date), the fresh fetch is discarded (`_bf_existing > 0 → SKIP`) — so a partial/early fetch can never be upgraded to final EOD data. `fetch_broker_flow` also lacks the HTTP-429 backoff that `fetch_flow` has; past the rate-limit wall, every remaining ticker's broker data is silently dropped for the day.

**Trading impact:** Medium — broker/bandar accdist feeds the market risk score, reversal watchlist, and foreign-flow features.

**Fix:** Replace skip with `INSERT OR REPLACE` (it's already keyed on ticker/date/broker/side); copy the 429 backoff. **Complexity:** Low.

### M-11 — Intraday yfinance bars stored as `is_final=1`; `md >= today` skip (Medium)

**Where:** `data/fetcher._save_df` (hardcodes `is_final=1`), `fetch_all_incremental`.

**Root cause:** The 16:00 `fetch_latest()` runs during/just after the closing auction; yfinance may serve a not-yet-settled bar for today, which is stored as final. The design expects the 16:15 scraper to replace it — but if the scraper run fails (token death), the partial bar remains flagged final, and the `md >= today` skip prevents yfinance from ever refreshing it.

**Trading impact:** Medium — a wrong "final" close propagates to next-day features and research (`final_only=True` loaders trust the flag).

**Fix:** Mark yfinance rows for *today* as `is_final=0` (settled history stays 1); allow refetch of the most recent date. **Complexity:** Low.

### Universe construction

**M-4 — Index-membership flags have no writer (Medium–High).** `idx_tickers.in_idx30/in_lq45/in_idx80` are read as *mandatory* gates (`reversal_filter`: only LQ45/IDX30 names can enter the reversal watchlist; `brpt_filter` scoring bonuses) but **no code path ever sets them** — `ticker_discovery.upsert_to_db` omits them and defaults are 0. They can only have been set by a one-off manual SQL. IDX rebalances constituents twice a year; the hardcoded `IDX30/LQ45/IDX80` lists in `data/fetcher.py` are frozen ("preserved for backward compat"). **Impact:** the reversal watchlist universe silently diverges from the actual index — or is empty on a fresh DB. **Fix:** scheduled constituent sync (IDX publishes lists) writing these flags with an as-of date. **Complexity:** Medium.

**M-12 — Discovery is manual; suspensions become "delisted" (Medium).** `ticker_discovery` must be run by hand; a stock suspended >5 days (common on IDX) is marked `delisted` on the next recheck and drops out of the universe, then reappears with a history gap — interacting badly with the Crash Recovery/suspension classifier. **Fix:** schedule discovery monthly; distinguish `suspended` from `delisted` using the existing suspension_events table. **Complexity:** Medium.

---

## 2. Feature generation

**Positive findings:** all indicator functions in `engine/indicators.py` are strictly trailing-window (no centered/forward windows); warmup contracts are declared; the session cache is fingerprinted against the id-reuse bug it previously had; the exit evaluator explicitly anchors trailing stops to prior-bar extremes to avoid intrabar look-ahead; the one known look-ahead strategy ('Regime Adaptive') was already removed. **No forward-looking bias was found in the production feature path.**

### H-3 — No last-bar freshness guard anywhere (High)

**Where:** `scheduler/scanner.py` (`scan_momentum_signals`, `scheduled_multi_strategy_scan`), `monitor.py` (`_latest_bar`, `_evaluate_swing_trend`), `paper_trade.check_trend`, `engine/trade_plan.edge_prescreen`.

**Root cause:** Every consumer evaluates `df.iloc[-1]` / `ORDER BY date DESC LIMIT 1` without checking the bar's date. If a ticker's fetch fails (token death, yfinance gap, suspension), its last bar may be days old; the scan will happily compute "today's" signal from it, `chg_pct` compares two stale bars, and the monitor re-evaluates the same stale bar hourly (repeat alerts; SL/TP decisions on old prices).

**Trading impact:** High. This is the mechanism by which the data outages the pipeline-health jobs *detect* still leak into live signals — the coverage checks alert humans but nothing stops the scans from consuming stale rows.

**Fix:** A shared `is_fresh(df, max_age_sessions=1)` guard applied at the top of each scan loop and in the monitor (skip + count + one aggregated alert). **Complexity:** Low.

### M-1 — Flow session windows are wrong; closing auction excluded (Medium–High)

**Where:** `flow_filter._analyze`.

**Root cause:** Three related time-window defects:
1. `market_bars = [b for b in bars if "09:" <= b["time"] <= "16:"]` — the string comparison excludes every `"16:xx"` bar (`"16:00" > "16:"`), so the closing-auction prints the dedicated **16:05 flow fetch exists to capture** (per the scheduler comment) never enter scoring.
2. "closing_net" is measured over **14:30–15:00**, but the IDX session runs to 15:50 plus closing auction — the smart-money labels (STRONG_BUY / ACCUMULATION / MORNING_TRAP) classify mid-afternoon flow as "the close".
3. `screener/calculator._hour_bucket` drops 11:30–13:29 for all days, discarding real Mon–Thu session-I trades from 11:30–12:00.

**Trading impact:** Medium–High. `smart_money` and `composite_score` feed the flow-confirmation gate, the reversal watchlist, edge scoring, and the EOD trade plan. Systematic mislabeling of the close means the "smart money at the close" thesis is computed on the wrong data.

**Fix:** Correct the window constants (`<= "16:59"`, closing window 15:00–16:15 or last-30-bars) and add a unit test with synthetic 16:0x bars. **Complexity:** Low.

### M-5 — EOD coverage fallback fabricates "today's" screen row from stale bars (Medium)

**Where:** `screener/screener_jobs.run_eod` coverage-fallback block.

**Root cause:** For tickers missing from `daily_screen`, the fallback takes `df.iloc[-1]` from all-of-ohlcv **without checking the bar date equals `trade_date`** and inserts it as today's row (close, volume, vol_ratio, proxy delta, signal label). A ticker that didn't trade today gets yesterday's (or last week's) data recorded as today's screen — which then feeds `gather_long_candidates` (S/V sources), the momentum quality gate, and reversal `prev_delta` joins.

**Fix:** `if str(last['date'])[:10] != trade_date: continue`. **Complexity:** Trivial.

### Missing values — assessment

Missing-value handling is generally deliberate (NaN-guards on ATR/VWAP, `min_periods` fallbacks, `COALESCE(is_final,1)`) but the *policy* is uniformly **fail-open / neutral-fill**: `calc_relative_strength` returns 1.0 (neutral-pass) on missing IHSG or short history; `compute_value_score` returns 50 with no data; missing keystats/flow/market-cap all pass their gates (see M-2). Individually defensible; collectively it means degraded data quietly relaxes standards rather than tightening them.

---

## 3. Ranking engine

**Positive findings:** `engine/edge_score.py` uses fixed (not cross-sectional) anchors so a weak universe can't manufacture a top score; win_rate/sharpe are hard vetoes rather than score inputs (no double counting); `unified_watchlist` tiers by actionability so the noisy premover source can't bury validated reversals; `candidate_score` explicitly refuses to treat S+V (same screen row) as independent confirmation. Weight calculation is sound and explainable (`edge_breakdown`).

### H-4 — EOD trade plan has no liquidity floor; structural bias toward illiquid names (High)

**Where:** `engine/trade_plan.gather_long_candidates` / `select_top`; contrast with `run_premarket_firm_scan` which applies `select_top_liquid_longs`.

**Root cause:** The 16:40 flagship plan pulls candidates from `daily_screen` over the **full ~900-ticker universe** with two source rules that structurally favor illiquid names: `signal='bullish'` (no turnover requirement) and `vol_ratio >= 5` (a 5× volume spike is far easier to print on a low-base-volume small cap than on BBCA). The premarket path's Rp-5B turnover gate is *not* applied here; neither `evaluate_premover_trade` (the auto-entry gate chain) nor the agent firm receives any liquidity input. The V-source cap (`min(vol_ratio/50, 1)`) limits its score weight but not its presence.

**Trading impact:** High. This is the requested "unintended bias toward illiquid stocks" — confirmed. Illiquid movers reach the firm and the published TOP LONGS list; the stated large-cap preference exists only in the premarket path, the reversal filter's LQ45/IDX30 gate (itself broken by M-4), and a fail-open market-cap floor.

**Fix:** Apply `passes_value_liquidity_gate` inside `gather_long_candidates` (or between gather and `select_top`), and add the same gate to `evaluate_premover_trade`. **Complexity:** Low.

### M-2 — Gates fail open on missing data and on their own exceptions (Medium)

**Where:** `engine/liquidity.py` (no OHLCV → pass; no keystats → pass; no market_cap → pass), `check_fundamental` (`no_data`/`db_error` → pass), `flow_confirms_signal` (`FLOW_UNAVAILABLE` → confirmed), scanner's liquidity-gate exception handler (fail-open with log-only alarm), `_agent_confirms_exit` (error → close proceeds).

**Root cause:** A consistent "don't block what we can't measure" philosophy. But the names most likely to lack keystats/market-cap/OHLCV depth are precisely the small, illiquid, recently-listed names the gates exist to exclude — so the gate is weakest exactly where it is most needed, and a data outage disables all gates at once while scanning continues (H-3 compounds this).

**Fix:** For *entry-candidate* paths, fail closed on missing liquidity/fundamental data (a missed trade is the cheap error); keep fail-open only for monitoring/exit paths. **Complexity:** Low (policy flips), plus expectation-setting that signal counts will drop.

### M-3 — No age cap on watchlist sources (Medium)

**Where:** `engine/unified_watchlist.py` (`MAX(scan_date)` reversal, `MAX(detected_at)` premover, `regime_watchlist` status-only), `trade_plan.get_vpin_gate` (correctly labels its date — good contrast).

**Root cause:** When last night's EOD chain fails (screener EOD error, premover crash), the 08:35 premarket firm and the unified panel silently serve the **most recent surviving** scan — possibly days old, with stale close prices — with no indication of age.

**Trading impact:** Medium: next-morning shortlist built on obsolete setups, precisely on the mornings following a pipeline failure.

**Fix:** Discard (or age-flag) source rows older than the last trading day; surface source dates in the Telegram message. **Complexity:** Low.

### Large-cap preference — assessment

Intended mechanisms: reversal filter LQ45/IDX30 hard gate + IDX30 conviction bonus; premarket Rp-5B turnover top-3; ADV/market-cap gates in the momentum scan (`filter_liquidity` — **default OFF** in `paper_config`); `brpt_filter` index bonuses. Effective state: eroded by M-4 (membership flags unmaintained), C-1 (ADV units), M-2 (fail-open market cap), H-4 (EOD plan ungated), and the liquidity filter toggle defaulting off in the momentum path. Conclusion: the large-cap preference is *declared* but only partially *enforced*.

---

## 4. Signal generation

**Positive findings:** entry checkers mirror their backtest strategies (documented parity work); `ensure_entry_price` output contract prevents silent no-trade signals (fixed audit C-1); disabled-strategies default list keeps the proven-negative-expectancy book off; counter-trend strategies get their own SL/TP levels with `min_rr` relaxed deliberately; the ARA/ARB cap logic with post-cap R/R re-validation is a genuinely good IDX-specific touch; sizing uses actual stop distance (fixed audit C-2); cooldown after stop-loss; aggregate exposure cap.

### H-8 — VPIN entry filter is a silent no-op due to a NameError (High, latent)

**Where:** `scheduler/scanner.py:410` — `_vpin_conn = _db_connect(DB_PATH)`; `_db_connect` is defined nowhere in the module (the import is `connect as db_connect`).

**Root cause:** Typo inside `try/except Exception` that logs a warning **and does not `continue`** — so when `filter_vpin=1`, every ticker throws NameError, the warning is logged, and the ticker *passes* the VPIN gate. The filter cannot ever block anything.

**Trading impact:** Currently nil (`filter_vpin` defaults 0), but High latent: an operator enabling the filter gets zero protection while believing it's active — the worst failure mode for a risk control.

**Fix:** Rename to `db_connect`; make the except path *skip* the ticker (fail-closed) or at least alarm via `fail_open_alarm`. **Complexity:** Trivial.

### H-1 — RED/ORANGE/YELLOW market-risk alerts are never delivered (High)

**Where:** `engine/risk_alert.py` (design: "RED bundled hourly by scheduler; ORANGE EOD summary"), `scheduler/jobs.py` (`run_hourly_risk_bundle`, `run_eod_risk_summary`, `run_foreign_snapshot` all defined + imported), `scheduler/__init__.py` (**none registered with `add_job`** — grep-verified).

**Root cause:** The routing layer writes RED/ORANGE/YELLOW alerts to `market_risk_log` with `sent=0`, and the delivery jobs that would flush them were never scheduled. Only CRITICAL sends immediately. `run_foreign_snapshot` additionally computes its report and then never sends it (its `send_telegram` call was removed but the job kept its 14:30 docstring).

**Trading impact:** High. The operator's mental model ("I'll be told when market risk is RED") is false; deteriorating-but-not-yet-critical regimes pass silently. The `market_risk_log` accumulates unsent rows indefinitely.

**Fix:** Register the two jobs (hourly during session + EOD) or delete the tiering and send RED immediately. Decide `run_foreign_snapshot`'s fate explicitly. **Complexity:** Trivial.

### M-8 — 16:00 daily scan ordering: trades on pre-final data (Medium)

**Where:** `scheduler/__init__.py` (16:00 `daily_signal_scan` vs 16:15 `_run_screener_eod`), `scanner.daily_signal_scan`, quality-gate read of `daily_screen`.

**Root cause:** The daily momentum scan fetches yfinance at 16:00 — during/just after the closing auction — and can auto-open paper trades before the day's final bar exists (final data lands 16:15). Its quality gate reads today's `daily_screen` row, which at 16:00 was last written by the **14:35 partial-day** intraday run — a partial-day 'watch'/delta label gates a full-day signal. (Mitigated today because the momentum book is in the default disabled set — the 16:00 job is effectively report-only unless config changes.)

**Fix:** Move the scan to ≥16:20 (after screener EOD) or gate entries on `is_final` for today's bar. **Complexity:** Low.

### M-10 — Entry race conditions (Medium)

**Where:** `paper_trade.open_trade` (read `get_open_trades` → check max_open/duplicate → INSERT, non-atomic), invoked concurrently by the multi-strategy scan, premover EOD, and daily scan (screener runs at the same minutes).

**Trading impact:** Occasional max_open breach or duplicate position under overlap; bounded by the aggregate-exposure cap.

**Fix:** Partial unique index `(ticker) WHERE status='OPEN'` + transactional count-check (`BEGIN IMMEDIATE`). **Complexity:** Low–Medium.

### M-7 — Same-minute scheduling race (Medium)

`_run_screener_intraday` (writes today's provisional bars) and `scheduled_multi_strategy_scan` (reads `ohlcv`) are deliberately registered at the *same* cron minutes (09:05, 10:05, …). Whether the strategy scan sees today's bar is a coin flip depending on thread interleaving and per-ticker fetch pace — nondeterministic signals across runs. **Fix:** stagger by 10–15 min (scan after screener) or have the scan read the screener's in-memory result. **Complexity:** Low.

### Exit conditions — assessment

The exit kernel (`engine/exits`) is the strongest module audited: deterministic conflict ordering (STOP→TP→TIME), gap-aware fills, direction-aware, prior-bar trail anchoring (no intrabar look-ahead), single cost authority applied identically in backtest/paper/shadow. Minor notes: (a) `monitor._check_trade`'s alert numbering jumps 1→3 (a NEAR_TP alert was removed; cosmetic); (b) swing-trend R7 closes at *latest close* rather than the stop level — realistic slippage-wise but inconsistent with the kernel's stop-fill convention; (c) TIME exits count provisional bars as full bars; (d) `_agent_confirms_exit` fail-open (error → close proceeds) is the *correct* direction of fail-open. No exit-logic defects of High severity found.

### Risk filters — assessment

DD circuit breaker (8% trigger / 5% recover hysteresis), macro-panic gate (200-DMA + vol quantile), event-guard window, ARA/ARB caps, cooldown, exposure cap: all correctly implemented. Two gaps: the circuit breaker only sees **realized** P&L of closed trades (an open-position drawdown never trips it — consider mark-to-market equity), and `_event_guard_active` defaults are a hardcoded June-2026 window (config-overridable; stale defaults are harmless but confusing).

---

## 5. Production scheduler

### H-7 — DB_PATH resolution is fragile (High)

**Where:** `.env` (`DB_PATH=data/walkforward.db` — **relative**), `scheduler/*.py`, `paper_trade.py`, `engine/risk_alert.py` (fallback `/home/tjiesar/10 Projects/...` — a stale path that doesn't exist on this machine), `config.py` (module-relative default), `screener/idx_scraper.py` + `reversal_filter.py` (own absolute paths, ignoring env).

**Root cause:** Three different resolution strategies for the same database. The relative `.env` value means the effective DB depends on the process CWD; SQLite will silently *create* an empty `data/walkforward.db` under any other working directory (cron, systemd with a different `WorkingDirectory`, manual runs from `~`). The stale absolute fallback would do the same in `/home/tjiesar/...` if `.env` loading ever fails.

**Trading impact:** High operationally — the classic split-brain failure: jobs writing to one DB, scans reading another, everything "working" with empty results.

**Fix:** `config.py` resolves `DB_PATH` to an absolute path once (`Path(...).resolve()`); every module imports it from config; delete the per-module `os.getenv` fallbacks. **Complexity:** Low.

### M-6 — Failure handling: no retries, no dependency checks, sentinel-before-work (Medium)

**Where:** all of `scheduler/jobs.py`; `run_premarket_firm_scan` / `run_eod_trade_plan` dedup sentinels.

**Root cause:**
1. **No retry** on any job — a transient Stockbit 5xx at 16:15 loses the day's final bars/reversal scan permanently (and the coverage alert fires at 17:00, after the 16:30/16:40 downstream jobs already ran on the stale data).
2. **No dependency verification** — the EOD chain (16:15 screener → 16:30 premover → 16:40 trade plan → 18:00 VPIN → 18:30 forward test) is sequenced purely by clock time; each stage runs regardless of whether its upstream succeeded (compounds M-3).
3. **Sentinel inserted before the work**: both dedup guards INSERT the `_job_sentinel` row *first*; if the job then crashes (watchlist build error, firm timeout), the retry path is permanently blocked for the day — the guard converts a transient failure into a guaranteed missed report.

**Fix:** Sentinel-on-success (or a `status` column with `running/success/failed` allowing failed-state retries); each EOD stage checks its upstream's freshness (e.g., trade plan verifies `daily_screen` has today's rows) and alarms if not; one retry with backoff for network-bound jobs. **Complexity:** Medium.

### Logging — assessment (Medium)

Jobs log via ad-hoc `print()` mixed with `logging` (there *is* a `utils/logging_config.setup_logging`, but scheduler modules mostly print). There is no per-job outcome record except the screener's `log_run` — so "did the 16:15 EOD run succeed yesterday?" requires reading stdout logs. The heartbeat proves the scheduler *process* is alive, not that jobs succeed; a scheduler happily heartbeating while every job throws is indistinguishable from healthy. **Fix:** uniform logger + a `job_runs(job, date, status, duration, error)` table written by a decorator; the heartbeat watchdog can then also check last-success ages. **Complexity:** Medium.

### Other scheduler notes

- **L-4:** `_holiday_skip` fails open (calendar import error → job runs on holidays; ohlcv gets purged later but `stockbit_flow`/`daily_screen` keep junk holiday rows).
- **L-5:** Calendar hardcoded through 2026 only — from 2027-01-01 every weekday is a "trading day" and no blackouts exist. Known maintenance item; worth an automated "calendar year missing" alarm in December.
- **Review item:** `is_blackout_day` skips the *entire* multi-strategy scan (including SELL/distribution detection and bear-watchlist maintenance) for ~4–6 days/month (H-1..H+1 around each BI + FOMC date). Intended for entries; the collateral suppression of exit-side intelligence may not be.

---

## 6. Daily outputs

### H-2 — Three report functions are dead code (High for the operator's mental model)

`daily_fetch_report`, `flow_broker_report`, `auto_trade_status_report` (`scheduler/reports.py`) are imported by `scheduler/__init__.py` but never `add_job`-ed nor called from any route (grep-verified; only `open_trades_status_report` is reachable, via a backtest route). The news-fetch job's docstring even claims its spike detection "is consumed by flow_broker_report" — which never runs. **Fix:** register them or delete them; a documented output that silently doesn't exist is worse than no output. **Complexity:** Trivial.

### Watchlist & trade plan — assessment

Content and ranking logic of `build_unified_watchlist` and `tp.build_message` are sound (tiering, confluence bonuses, conflict flags, degraded-mode labeling, VPIN banner with explicit settle-date honesty). The material issues are upstream: H-4 (no liquidity floor), M-3 (no age cap), M-4 (membership flags), M-1 (flow labels). One report-content note: `fallback_rank` synthesizes confidence 0.5–0.85 displayed with the same ⭐ scale as real firm confidence — the degraded banner mitigates, but consider a distinct glyph so synthesized confidence is never screenshot-quoted as firm output.

### Low-severity output items

- **L-1:** `/metrics` `idx_market_risk_score` queries `risk_score`/`computed_at`; the table's columns are `score`/`created_at` → the gauge is permanently NaN (`app.py:154`).
- **L-2:** `get_summary().total_return_pct` divides by hardcoded 50,000,000 instead of configured capital.
- **L-3:** `stockbit_fetcher._parse_args` is dead and buggy (self-referential list comprehension); `main()` re-implements parsing correctly. Delete.
- **L-6:** `reversal_filter` "30-day" range uses 30 *calendar* days (~20 trading days) — label or window should match.
- **L-7:** `flow_filter.get_foreign_accumulation` comment claims count-normalization the code doesn't do.
- **L-8:** `run_eod` uses `conn` outside its `with` block (works — sqlite context managers don't close — but fragile to refactoring).

---

## Recommended remediation order

1. **Same-day, trivial (do first):** H-8 (`_db_connect` typo), H-1 + H-2 (register or delete the six dead jobs/reports), M-5 (fallback date guard), L-1.
2. **This week, low complexity:** H-3 (freshness guard), H-4 (EOD-plan liquidity gate), H-7 (absolute DB_PATH), M-1 (session windows), M-3 (age caps), M-9 (broker upsert + retry), M-8 (move 16:00 scan / is_final gate), M-7 (stagger crons), M-6a (sentinel-on-success).
3. **Requires validation work:** C-1 (volume-unit ruling + historical reconciliation) — *blocker for trusting any volume-derived result*; then C-2 (corporate-action adjustment), H-5 (EOD bar authority), H-6 (single schema module), M-4 (constituent sync), M-6b (job dependency/status), M-2 (fail-closed policy for entry gates).

**Verification protocol for C-1 (before any code change):** pick 3 liquid + 3 illiquid tickers, compare same-day `ohlcv.volume` for a scraper-written date vs a yfinance-written date vs the exchange's published volume; the ~100× ratio (or its absence) settles the unit question in minutes on the production DB.

---

*Audit performed read-only; no code, schema, or data was modified. Line references are to the repository state of 2026-07-22.*
