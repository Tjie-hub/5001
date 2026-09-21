# VWMA20 Pullback — Intraday Orderflow Workflow & Engine Upgrade Plan

> Generated 2026-06-25 | TOWR case study

---

## Phase 0: Current State

### What Works (Daily)
```
Daily thesis: P1 Breakout → P2 Pullback zone → P3 Entry trigger
Problem:      Daily bar always 1 day late. Jun 24 was the pullback touch
              at VWMA20, but trigger only confirmed after Jun 25 close.
              
              By the time daily signal fires, price already ran +7%.
```

### What We Already Have (Intraday)
| Component | Module | Status |
|---|---|---|
| 1-min flow bars | `delta_flow.load_bars()` | ✅ Ready |
| Session delta stats | `delta_flow.session_delta_stats()` | ✅ Ready |
| Cumulative delta (CVD) | `delta_flow.cvd()` | ✅ Ready |
| Delta imbalance spikes | `delta_flow.stacked_imbalances()` | ✅ Ready |
| Flow confirmation gate | `smc_flow.confirm_sweep_flow()` | ✅ Ready |
| Smart money score | API `/full` → `flow.latest.smart_money` | ✅ Ready |
| Intraday ORB | `strategies.check_orb_intraday_signal()` | ✅ Ready |

### What's Missing
| Gap | Priority |
|---|---|
| Daily pullback zone scanner (auto-identify candidates) | P0 |
| Intraday flow confirmation module (specific to VWMA20 thesis) | P0 |
| 1H/15min OHLCV aggregation from flow_bars | P1 |
| Real-time monitor script (runs during market hours) | P1 |
| Backtest with intraday entry timing | P2 |

---

## Phase 1: Daily Scanner — Identify Pullback Zone Candidates

### Module: `engine/vwma_pullback_scanner.py`

```python
def scan_pullback_candidates(date: str, db_path: str = DB_PATH) -> list[dict]:
    """
    Scan all tickers for VWMA20 pullback zone status.
    
    Returns list of candidates:
    {
        ticker, close, vwma20, dist_pct, ma50,
        quality_cross_date, quality_cross_age_days,
        in_pullback_zone: bool,          # dist 0% to +5% from VWMA20
        no_cross_below: bool,            # hasn't closed below VWMA20 since cross
        no_big_wick: bool,               # <2 big wick candles in pullback window
        quiet_preceding: bool,           # last 3 bars quiet
        regime_ok: bool,                 # above MA50 + VWMA rising + not from peak
        cluster_num, days_in_cluster,    # from cluster methodology
        bh_pct,                          # structural trend check
        score: int                       # 0-10 composite score
    }
    """
```

**Filter priority:**
1. `in_pullback_zone == True` (mandatory)
2. `regime_ok == True` (mandatory)
3. `cluster_num <= 3` (from cluster methodology)
4. `bh_pct > 0` (structural uptrend)
5. Score >= 6 for intraday monitoring

**Output:** Ranked list of tickers to monitor intraday.

---

## Phase 2: Intraday Monitor — Flow Confirmation

### Module: `engine/vwma_intraday_confirm.py`

```python
def check_intraday_confirmation(ticker: str, date: str, 
                                 db_path: str = DB_PATH) -> dict:
    """
    Check if intraday flow confirms the VWMA20 pullback bounce.
    
    Conditions (all must pass):
    1. CVD RISING: cumulative delta trend is positive (last 60 min)
    2. SMART MONEY: composite_score > 0 OR session net_value > 0
    3. PRICE ABOVE VWMA20: last price > VWMA20 (not breaking below)
    4. NO DISTRIBUTION SPIKE: no single bar delta < -2σ (no panic selling)
    5. BUYING INTO CLOSE: last 30 min buy% > 55%
    
    Returns:
    {
        confirmed: bool,
        confidence: 'HIGH' | 'MEDIUM' | 'LOW',
        signals: {
            cvd_rising, smart_money_buy, above_vwma20,
            no_distribution, buying_into_close
        },
        metrics: {
            cvd_current, cvd_30m_ago, net_value_session,
            smart_money_score, last_price, vwma20,
            buy_pct_last_30m
        },
        entry_suggestion: {
            entry_zone_low, entry_zone_high,
            stop_loss, target_1, target_2
        }
    }
    """
```

### Confirmation Signal Logic

```
Intraday flow bar (1-min):
  │
  ├─ CVD (cumulative delta)
  │   └─ Rising over last 60 min → buyer accumulation ✓
  │
  ├─ Delta spikes
  │   └─ No single minute delta < -2σ → no panic distribution ✓
  │
  ├─ Smart money
  │   └─ composite_score > 0 (daily) OR net_value_session > 0 (intraday) ✓
  │
  ├─ Price vs VWMA20
  │   └─ last_price > VWMA20 → support holding ✓
  │
  └─ Buy/Sell ratio (last 30 min)
      └─ buy_lot / (buy_lot + sell_lot) > 0.55 → buying into close ✓
```

---

## Phase 3: Daily Workflow (Human + Engine)

### Morning (08:30 WIB)

```
1. Run daily scanner:
   $ python engine/vwma_pullback_scanner.py --date 2026-06-26

2. Output: "3 tickers in pullback zone. Monitor: TOWR (score 7), EXCL (score 6), ..."

3. For each candidate:
   - Open TV chart via tv bridge
   - Set alert at VWMA20 level
   - Mark entry zone on chart
```

### During Market (09:00–15:00 WIB)

```
4. Every 15 minutes, run intraday check:
   $ python engine/vwma_intraday_confirm.py --ticker TOWR

5. When confirmation fires:
   → Telegram alert
   → "TOWR: VWMA20 Pullback Confirmed. CVD rising +85K, Smart Buy.
      Entry zone: 358-365. SL: 348. TP1: 380. TP2: 400."

6. Manual entry execution (or paper trade auto-entry)
```

### After Close (16:00 WIB)

```
7. Update daily thesis state:
   - Did any monitored tickers confirm?
   - Which ones bounced without confirmation?
   - Update scanner for next day

8. Log entry/exit to paper_trade.py
```

---

## Phase 4: Engine Code — What to Build

### File: `engine/vwma_pullback_scanner.py`

```
Responsibilities:
- Daily scan of all tickers for VWMA20 pullback zone
- Reuses indicator functions from engine/indicators.py (calc_vwma, calc_sma)
- Integrates with cluster methodology (cluster_num, days_in)
- Outputs ranked candidate list
- REST endpoint: GET /api/scanner/vwma-pullback
```

### File: `engine/vwma_intraday_confirm.py`

```
Responsibilities:
- Checks intraday flow for VWMA20 pullback confirmation
- Uses delta_flow.cvd(), delta_flow.stacked_imbalances()
- Uses smc_flow.confirm_sweep_flow() for daily tier
- Reads VWMA20 from daily OHLCV + current price from flow_bars
- Outputs confirmation signal with entry zone
- REST endpoint: GET /api/intraday/vwma-confirm?ticker=TOWR
```

### File: `scheduler/jobs.py` (add job)

```
New scheduled job:
- Every 15 min during market hours (09:00-15:00 WIB, Mon-Fri)
- Run scan for all monitored tickers
- If confirmation fires → Telegram alert
- Store confirmation log to DB
```

### File: `routes/intraday.py` (new route)

```
GET  /api/intraday/candidates        → list tickers in pullback zone
GET  /api/intraday/confirm/<ticker>   → check intraday confirmation
GET  /api/intraday/cvd/<ticker>       → CVD chart data (1-min)
POST /api/intraday/monitor/<ticker>   → add ticker to monitor list
```

### File: `scratchpad/intraday_monitor.py` (CLI tool)

```
Quick CLI for manual monitoring:
  $ python scratchpad/intraday_monitor.py --scan
  $ python scratchpad/intraday_monitor.py --watch TOWR
  $ python scratchpad/intraday_monitor.py --watch TOWR --interval 60
```

---

## Phase 5: Backtest Upgrade (Future)

### Goal
Backtest the thesis with intraday entry timing to measure:
- How much better is intraday entry vs daily bar entry?
- What % of pullback zones get intraday confirmation?
- Optimal confirmation parameters (CVD length, delta threshold, buy%)

### Approach
```
1. For each daily pullback zone:
   a. Load 1-min flow_bars for each day in the pullback window
   b. Check if intraday confirmation fired before daily close
   c. If yes → entry at confirmation price (not next day open)
   d. If no → skip (no intraday confirmation = no entry)

2. Compare:
   - "Daily entry" backtest (enter next day open)
   - "Intraday entry" backtest (enter at confirmation moment)
   - Difference in avg entry price, win rate, returns
```

### Data Limitation
`stockbit_flow_bars` only available from 2026-04-20. Full 2-year backtest with intraday data is not possible. Backtest window: Apr 20–Jun 25, 2026 (~2 months).

---

## Summary: Priority Order

| # | Task | Effort | Impact |
|---|---|---|---|
| 1 | `vwma_pullback_scanner.py` — daily scan | 2h | High |
| 2 | `vwma_intraday_confirm.py` — flow check | 3h | High |
| 3 | `routes/intraday.py` — REST endpoints | 1h | Medium |
| 4 | `intraday_monitor.py` — CLI tool | 1h | Medium |
| 5 | Telegram alert integration | 1h | Medium |
| 6 | Intraday backtest module | 4h | Future |

**Total Phase 1 (tradeable workflow): ~7 hours**
