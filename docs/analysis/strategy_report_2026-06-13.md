# IDX Agent (5001) — Strategy Audit, Winning-Strategy Analysis & Forward Plan

**Date:** 2026-06-13 (Saturday) · **Author:** Claude Code audit session

---

## 1. Agent health check

| Item | Status |
|---|---|
| Flask app (port 5001) | UP — `/health` returns ok |
| Last scan | 2026-06-12 14:35 (Friday) |
| Walkforward scores | Fresh — 9,586 ticker×strategy rows updated 2026-06-12 16:00, 872 tickers × 11 strategies |
| Signals today | 0 (Saturday, expected) |
| Open trades | 1 — NEST: entry 560 (2026-05-13), last close 535 (−4.5%), SL 464 / TP 752 |
| Uncommitted code | `scheduler/scanner.py` (+21, EOD timing fix) and `engine/dashboard.py` (1 line) — **not committed** |

### Architecture (as running)
- **Signal pipeline:** `scheduler/scanner.py` → multi-strategy scan over IDX universe → `adaptive_strategy_selector` picks per-ticker strategies from `wf_scores` (consistency + weighted_score) → flow filter (Stockbit broker flow) → per-ticker `RegimeClassifier` (logistic regression) + macro overlay → DeepSeek agent-firm approve/reject → `scheduled_signals` / paper trades.
- **Strategy roster (11):** vol_weighted, momentum, vwap_reversion, conservative, VWMA Breakout-Pullback, Volume Profile POC, Inside Bar Breakout, NR7 Breakout, ORB, Swing Trend, Trend Following Breakout, Crash Recovery (added ~Jun 5, signal-routed).
- **Walkforward:** rolling windows (max 4 per ticker, quarterly test windows Apr-2025 → Jun-2026), per-window metrics in `backtest_windows.metrics_json`.

### Known defects confirmed in this audit
1. **`avg_sharpe` in `wf_scores` is corrupted** (values like +923 / −5,274). Sharpe is computed on per-bar equity including flat periods, not per-trade equity (open item from 2026-05-27 audit). Any ranking touching it is garbage.
2. **`weighted_score` rewards trade frequency, not profitability.** Top-scored strategies (vwap_reversion 0.59, vol_weighted 0.54) have *negative* average per-window returns (−0.58%, −0.53%). The score feeds `adaptive_strategy_selector`, so the agent preferentially routes **losing** strategies into live signals. This is the single most damaging defect.
3. **No time-stop** — BSML sat 27 days to exit flat; capital is parked in dead trades during a bear market.
4. Recent live signal mix (since 15 May): 2,092 of 2,201 signals are `distribution` (sell-side warnings); only ~109 BUY-side, mostly from vol_weighted/conservative/vwap_reversion — i.e. the three weakest performers in the current regime.

---

## 2. What the data says: the winning strategy

### 2.1 Per-traded-window performance (all 4,216 walkforward windows, Apr-2025 → Jun-2026)

| Strategy | % windows traded | Avg ret/window | Median | Avg win rate | % windows positive |
|---|---|---|---|---|---|
| **Crash Recovery** | 1.4% | **+3.28%** | +3.21% | 75% | **75%** |
| NR7 Breakout | 32% | +0.27% | −0.79% | 34% | 38% |
| Trend Following Breakout | 45% | +0.10% | −0.32% | 30% | 31% |
| momentum | 66% | −0.04% | −0.84% | 32% | 34% |
| ORB | 53% | −0.21% | −0.89% | 38% | 39% |
| Volume Profile POC | 39% | −0.23% | −0.73% | 32% | 33% |
| Inside Bar Breakout | 36% | −0.25% | −1.03% | 27% | 30% |
| Swing Trend | 2.8% | −0.37% | −0.88% | 18% | 30% |
| vol_weighted | 87% | −0.53% | −1.12% | 28% | 34% |
| vwap_reversion | 83% | −0.58% | −0.81% | 35% | 40% |
| conservative | 86% | −0.70% | −0.96% | 27% | 31% |

**The `weighted_score` ranking is inverted from reality.** The three highest-scored strategies are the three biggest losers per traded window; they only score well because they trade constantly.

### 2.2 Performance is regime-dependent — and the regime broke in January 2026

IHSG: 7,166 (Jun-2025) → **8,647 peak (Dec-2025)** → 6,990 (Apr) → **5,347 low (Jun-8)** → 6,008 (Jun-12). A −38% peak-to-trough crash, with a **+12% rebound in the last 4 sessions**.

Average return per traded window by quarter:

| Strategy | 2025-Q2 | 2025-Q3 | 2025-Q4 | 2026-Q1 | 2026-Q2 |
|---|---|---|---|---|---|
| NR7 Breakout | +0.10 | **+1.07** | +0.49 | −0.23 | −0.88 |
| Trend Following BO | +0.07 | +0.30 | +0.09 | −0.21 | −0.18 |
| momentum | −0.13 | +0.48 | +0.23 | −0.59 | −0.71 |
| vwap_reversion | +0.05 | −0.03 | −0.14 | −0.86 | **−1.80** |
| Crash Recovery | — | — | — | — | **+3.28** |

Every long strategy worked (or broke even) in the 2025 uptrend and lost money from January 2026. Crash Recovery — buy gap-down ≥20% after suspension-proxy gaps, confirmed by volume + bullish close, SL at resume-bar low, TP at 50% gap retracement — is the **only strategy positive in the crash regime** (12 windows, small sample but the right direction and design).

### 2.3 Live paper trading confirms it

6 closed trades since May: 5 losses, 1 winner (+1.2%), worst −14% (UNIC). All from Momentum Following / Swing Trend — momentum strategies run into a bear market with no regime gate at the strategy-allocation level.

### 2.4 Verdict — winning strategy *from the data*

> **There is no all-weather winner; the winner is regime-conditional.**
> - **Current regime (post-crash / high-vol):** Crash Recovery — the only positive strategy.
> - **Trending regime (like 2025 H2):** NR7 Breakout and Trend Following Breakout (positive mean, fat right tail, low drawdown); momentum acceptable only with a regime gate.
> - **Never (as implemented):** vwap_reversion, vol_weighted, conservative — negative in every regime including the 2025 bull. Suppress until rebuilt.

---

## 3. Market context (web research)

- **Cause of the crash:** MSCI's 27-Jan-2026 warning on market accessibility/transparency (wash-trading, opaque ownership) triggered an 11.5% two-day wipeout (~$80B). ([The Diplomat](https://thediplomat.com/2026/02/indonesias-stock-market-sell-off-explained/), [Indonesia Investments](https://www.indonesia-investments.com/finance/financial-columns/massive-sell-off-on-the-indonesia-stock-exchange-occurred-after-msci-issues-a-stern-warning/item9896))
- **May review:** MSCI kept curbs (FIF freeze, no additions), deleted 6 standard + 13 small-cap names → passive forced selling. ([Jakarta Globe](https://jakartaglobe.id/business/msci-keeps-indonesia-stocks-on-hold-as-reform-review-continues), [Investortrust](https://investortrust.id/market/103155/indonesia-dodges-frontier-downgrade-but-faces-massive-sell-off-as-msci-maintains-reform-freeze))
- **⚠️ Binary events ahead: Global Market Accessibility Review June 18; Annual Market Classification Review June 23** — the frontier-downgrade decision. ([IDNFinancials](https://www.idnfinancials.com/news/64395/msci-new-review-due-will-indonesia-stay-an-emerging-market)) The current +12% bounce is partly positioning ahead of this. Outcome unknown → treat 18–23 June as an event-risk window: reduced size, tighter stops, no fresh momentum entries.

---

## 4. New strategies from research — the pick

Candidates reviewed:

| Candidate | Evidence | Fit for IDX now |
|---|---|---|
| **Short-term reversal (liquidity provision)** | Positive & significant in majority of 21 EMs, 1990–2017; returns *highest* for small, illiquid, high-volatility stocks and **strongest when market volatility is high / investor exit is heavy** ([ScienceDirect](https://www.sciencedirect.com/science/article/pii/S1042444X20300530), [RFS 2025](https://academic.oup.com/rfs/article-abstract/38/12/3673/8240327), [Novy-Marx/Dimensional](https://www.dimensional.com/ie-en/insights/q-and-a-on-short-run-reversals-with-mamdouh-medhat-and-robert-novy-marx)) | **Excellent** — IDX is small/illiquid/high-vol post-panic: exactly where the premium concentrates. Mechanically similar to Crash Recovery but fires far more often. |
| **Dynamic (vol-managed) momentum** | Daniel & Moskowitz: momentum crashes occur in panic states (post-decline, high vol) during rebounds; vol/state-scaled momentum ≈ doubles Sharpe ([NBER w20439](https://www.nber.org/papers/w20439), [SSRN](https://www.ssrn.com/abstract=2486272)) | **High** — explains *exactly* why the agent's momentum book is bleeding (shorting-the-rebound dynamics in panic state). Gate, don't delete, momentum. |
| Defensive/DCA/options overlays | Practitioner consensus ([Motley Fool](https://www.fool.com/investing/how-to-invest/bear-market-stocks/), [SmartFinance](https://smartfinance.fyi/articles/bear-market-survival-guide-10-proven-strategies-when-stocks-crash)) | Low — portfolio advice, not a swing-signal engine; IDX options market impractical. |

**Pick: Short-Term Reversal (Panic Rebound) as the new strategy, plus a Daniel-Moskowitz panic-state gate on the existing momentum/breakout book.** The reversal strategy is the academically strongest fit for the current market, generalizes Crash Recovery's edge (75% positive windows) from rare suspension-gaps to everyday oversold conditions, and reuses infrastructure the agent already has (vol-ratio, liquidity tiers, regime classifier, flow filter).

### Sketch: `strategy_panic_rebound`
- **Universe:** liquidity tier ≥ tradable (existing `liquidity.py`), price ≥ 100 (avoid gocap), not suspended.
- **Entry:** 5-day return ≤ −15% (or z-score ≤ −2 vs 60d) **and** close > open on signal day (selling exhaustion) **and** VR > 1.5× **and** no fresh negative news (`news_mentions`). Optional confluence: stock in existing `reversal_watchlist` with validated source.
- **Exit:** TP = 50% retracement of the 5-day drop; SL = signal-day low; **time-stop 5 bars** (reversal alpha decays in days — RFS 2025).
- **Sizing:** existing `lot_size` at 2% risk; halve size when macro overlay = panic.

---

## 5. Detailed plan

### Phase 0 — Stop the bleeding (this weekend, before Monday 15 Jun open)
| # | Task | File(s) | Acceptance |
|---|---|---|---|
| 0.1 | Commit the pending scanner/dashboard changes (EOD timing fix is live-critical) | `scheduler/scanner.py`, `engine/dashboard.py` | clean `git status` |
| 0.2 | **Fix `weighted_score`**: require `avg_return_pct > 0` for a strategy to be selectable; recompute score as f(consistency, avg_return, max_dd) with no frequency reward | `engine/walkforward_multi.py`, `wf_scores` recompute | vwap_reversion/vol_weighted/conservative no longer in top selector picks |
| 0.3 | **Fix WF Sharpe**: compute on per-trade (or per-day-in-market) equity; backfill `wf_scores.avg_sharpe` | `engine/walkforward_multi.py` | values in sane range (−3…+3) |
| 0.4 | **MSCI event guard**: 18–23 Jun window → block new momentum/breakout entries, halve position size on all new entries, tighten trailing stops on open trades (NEST) | `scheduler/scanner.py` config / `paper_config` | guard active + visible on dashboard |
| 0.5 | Suppress vwap_reversion, vol_weighted, conservative from live signal generation (config flag, not code deletion) | `paper_config` / scanner filter | no BUY signals from these three |

### Phase 1 — Ship the new strategy (week of 15 Jun)
| # | Task | Acceptance |
|---|---|---|
| 1.1 | Implement `strategy_panic_rebound` per sketch §4 + `check_panic_rebound_signal` router entry (follow Crash Recovery's pattern, obs #2292) | unit tests pass incl. look-ahead test (`tests/test_lookahead.py` style) |
| 1.2 | Walkforward it over the full 2025-04→2026-06 window set | avg ret/traded window > 0 overall **and** > +1% in 2026-Q1/Q2 buckets; ≥ 100 traded windows |
| 1.3 | Add **time-stop (5 bars)** to panic_rebound and **10 bars** to all swing strategies (open audit item) | no paper trade older than its time-stop |
| 1.4 | Paper-trade it in shadow mode for 5 sessions alongside Crash Recovery | signals logged with full reasons |

### Phase 2 — Regime-gated allocation (week of 22 Jun, after MSCI verdict)
| # | Task | Acceptance |
|---|---|---|
| 2.1 | Wire macro regime (IHSG vs 50/200-MA + realized vol) into **strategy allocation**, not just per-ticker filtering: PANIC/BEAR → {Crash Recovery, Panic Rebound} only; RECOVERY → + NR7; BULL → + momentum, TFB | allocation switches verified against 2025 vs 2026 backtest buckets |
| 2.2 | Daniel-Moskowitz gate: momentum book disabled when (IHSG below 200MA) **and** (20d realized vol > 75th pct) | momentum would have been OFF Jan–Jun 2026 in replay |
| 2.3 | Re-run full walkforward with allocation layer; compare vs ungated baseline | gated portfolio beats ungated on return and max-DD |
| 2.4 | Post-MSCI decision (23 Jun): re-evaluate event guard; if EM status retained, enable RECOVERY book | decision logged in `docs/analysis/` |

### Phase 3 — Hygiene & measurement (rolling)
- Per-strategy live P&L attribution panel on the dashboard (paper_trades by strategy, rolling 20-trade win rate) so the next regime break is caught in days, not months.
- Quarterly re-validation job: re-run §2.1 table automatically after each wf refresh; alert if a live strategy's trailing-2-quarter avg goes negative.
- Backfill `windows_tested` (currently max 4) by extending walkforward history if older OHLCV is available — 4 windows per ticker is too thin for per-ticker selection.

### Risks
- Crash Recovery's +3.28% is from **12 windows** — directionally right, statistically thin. Panic Rebound (1.2) is the test that the edge generalizes.
- MSCI downgrade on 23 Jun would trigger a second forced-selling leg — the event guard (0.4) is not optional.
- Reversal strategies in illiquid IDX names have real fill/slippage risk; keep the liquidity-tier floor strict and model costs with `apply_costs`.

---

## Sources
- [The Diplomat — Indonesia's Stock Market Sell-Off, Explained](https://thediplomat.com/2026/02/indonesias-stock-market-sell-off-explained/) · [The Diplomat — $80B Wake-Up Call](https://thediplomat.com/2026/02/indonesias-eighty-billion-dollar-wake-up-call/)
- [Indonesia Investments — MSCI warning sell-off](https://www.indonesia-investments.com/finance/financial-columns/massive-sell-off-on-the-indonesia-stock-exchange-occurred-after-msci-issues-a-stern-warning/item9896)
- [Jakarta Globe — MSCI keeps Indonesia on hold](https://jakartaglobe.id/business/msci-keeps-indonesia-stocks-on-hold-as-reform-review-continues) · [IDNFinancials — June review timeline](https://www.idnfinancials.com/news/64395/msci-new-review-due-will-indonesia-stay-an-emerging-market) · [Investortrust — May deletions](https://investortrust.id/market/103155/indonesia-dodges-frontier-downgrade-but-faces-massive-sell-off-as-msci-maintains-reform-freeze)
- [ScienceDirect — Reversal returns & liquidity provision in emerging markets](https://www.sciencedirect.com/science/article/pii/S1042444X20300530) · [RFS — Short-Term Reversals and Longer-Term Momentum around the World](https://academic.oup.com/rfs/article-abstract/38/12/3673/8240327) · [Dimensional — Novy-Marx Q&A on short-run reversals](https://www.dimensional.com/ie-en/insights/q-and-a-on-short-run-reversals-with-mamdouh-medhat-and-robert-novy-marx)
- [NBER w20439 — Daniel & Moskowitz, Momentum Crashes](https://www.nber.org/papers/w20439) · [SSRN version](https://www.ssrn.com/abstract=2486272)
- [Motley Fool — Bear market stocks](https://www.fool.com/investing/how-to-invest/bear-market-stocks/) · [SmartFinance — bear market strategies](https://smartfinance.fyi/articles/bear-market-survival-guide-10-proven-strategies-when-stocks-crash)
