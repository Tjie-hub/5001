# IDX Agent Review — May 26, 2026

Branch: `master` | DB: 416K OHLCV bars, 959 tickers, 2024-04 → 2026-05-26

---

## Part A: System Issues

### Summary

The paper trading system has 4 open and 2 closed positions. Both closed trades were losses (-12.3% combined), and the open book is net negative. Five structural issues are degrading signal quality and trade selection.

---

### Issue 1: Paper Trade Ignores Backtest-Optimal Strategy

**What's happening**

Every paper trade uses `"Momentum Following"` as the entry strategy, regardless of what the backtest cache says is optimal for that ticker. The `open_trade()` default parameter and the scheduler's `scan_momentum_signals()` both hardcode this.

**Evidence**

| Ticker | Paper Used | Backtest Says Best | Predicted Return | Win Rate |
|--------|-----------|-------------------|-----------------|----------|
| CLAY | Momentum | Vol-Weighted Entry | 33–35% | 76.5% |
| BSML | Momentum | Conservative Confirm | 9–10% | 50% |
| POWR | Momentum | ORB | 0.69% | 57% |
| UNIC | Momentum | Momentum | 8.9–11% | 40–47% |

CLAY is the worst case — backtest predicts 33% return with a 76% win rate under Vol-Weighted Entry, but it's running Momentum Following (which has a 6% aggregate win rate). POWR was predicted to return 0.69% under ORB (essentially a coin flip) yet was entered anyway; it got stopped out at -6.5%.

**How to fix**

**File: `paper_trade.py`** — `open_trade()` function (line ~230)

Instead of defaulting `strategy='Momentum Following'`, look up the best strategy from `backtest_cache` for the ticker on the most recent `computed_date`:

```python
def get_best_strategy_for_ticker(ticker: str) -> str:
    conn = get_db()
    row = conn.execute(
        "SELECT best_strategy FROM backtest_cache "
        "WHERE ticker=? ORDER BY computed_date DESC LIMIT 1",
        (ticker,)
    ).fetchone()
    conn.close()
    return row["best_strategy"] if row else "Momentum Following"

# In open_trade():
strategy = strategy or get_best_strategy_for_ticker(ticker)
```

**File: `scheduler.py`** — `scan_momentum_signals()` (line ~243)

Change the hardcoded `STRATEGY = "Momentum Following"` to use the per-ticker best from cache. The signal record already stores the strategy used in `scheduled_signals.strategies`. Keep Momentum Following as the fallback only when no cache entry exists.

**Also add a guard**: if the backtest predicts return < 1% or win rate < 40%, skip the entry entirely. POWR at 0.69% return on 7 trades should never have been entered.

---

### Issue 2: All 972 Tickers Signal "Neutral" — Screener Runs Too Early

**What's happening**

The intraday screener ran at 09:17 WIB today. At 17 minutes after open, volume ratios (VR) haven't built up enough to cross the 1.5× threshold. The coverage fallback in `screener/screener_jobs.py` only assigns `bullish`/`bearish`/`watch` when VR > 1.5:

```python
signal = 'neutral'
if vr is not None and vr > 1.5:
    if delta_p > 0 and last['close'] > tp:
        signal = 'bullish'
    elif delta_p < 0 and last['close'] < tp:
        signal = 'bearish'
    else:
        signal = 'watch'
```

At 09:17, VR for almost every ticker is near 1.0 (no volume accumulation yet), so all fall through to `neutral`. Compare yesterday: at 13:46 and 14:45 runs, there were 38 bullish, 41 bearish, 72 watch.

**Evidence**

```
screen_run_log:
  2026-05-26 09:17:36  intraday  972 OK  756s
  2026-05-25 15:40:33  eod       972 OK  633s
  2026-05-25 14:45:43  intraday  972 OK  643s
  2026-05-25 13:46:39  intraday  972 OK  699s
```

Daily screen May 26: 972 neutral, 0 everything else.
Daily screen May 25: 821 neutral, 72 watch, 41 bearish, 38 bullish.

**How to fix**

**File: `scheduler.py`** — `start_scheduler()` (line ~1544)

Change the first intraday screener run from 09:00/09:15 to **10:00 or 10:15**. The market needs at least 60 minutes for meaningful volume ratios to accumulate. The current schedule:

```
Current:  09:15, 10:30, 11:30, 13:45, 14:45
Proposed: 10:15, 11:30, 13:00, 14:30, 15:15
```

The 09:00 auto-trading status check should remain — it serves a different purpose (checking if trading is enabled, not generating signals).

**Also**: add a 10-minute "market warmup" guard in `run_intraday()` that skips signal generation if the market has been open < 60 minutes and VR_median across all tickers < 1.2. This prevents wasting a 756-second scan on data that won't produce signals.

---

### Issue 3: Hardcoded Telegram Credentials

**What's happening**

`scheduler.py` has the bot token and chat ID baked into the source as default parameter values:

```python
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "8790169868:AAE6qno0LrxxIdFydSKSLKhD8EPUzevPIFo")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "5919142813")
```

These are committed to git history (visible in `git diff`, will persist in `git log`). Anyone with repository access can read them and impersonate the bot — send messages, read chat history, or abuse the token.

**How to fix**

1. **Immediately**: rotate the bot token via [@BotFather](https://t.me/BotFather) — use `/revoke` then generate a new token
2. **Code fix** in `scheduler.py` — remove the hardcoded defaults:

```python
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise RuntimeError("TELEGRAM_TOKEN and TELEGRAM_CHAT_ID must be set in environment")
```

3. Store the new values in a `.env` file (already gitignored) or systemd environment
4. **Rewrite git history** to remove the credentials from the commit — use `git filter-branch` or `BFG Repo-Cleaner` to purge the strings from all commits, then force-push. If the repo has ever been pushed to a public remote, treat the token as permanently compromised

---

### Issue 4: NEST Stop-Loss Inconsistency

**What's happening**

NEST entered at Rp 560 with a stop-loss at Rp 464. That's a **17.1%** stop distance, not the configured 2.5%. The current price is Rp 505 (-9.8%), and it still hasn't triggered the stop.

The 2.5% config SL would put the stop at Rp 546, which would have been hit days ago. But the actual stop in the DB is 464 — way wider.

**Root cause**

The stop was likely set by external logic (possibly a swing/ATR-based calculation) when the trade was opened, not from the `sl_pct` config. The `open_trade()` function allows callers to pass a custom `sl_price`, and if one is provided, it skips the config-based calculation.

**How to fix**

**File: `paper_trade.py`** — `open_trade()` (line ~265)

Add a guard that caps the stop-loss distance regardless of what the caller passes:

```python
max_sl_distance = entry_price * cfg["sl_pct"] * 2.0  # hard cap at 2x configured SL

if sl_price is not None and sl_price > 0:
    sl_dist = entry_price - sl_price
    if sl_dist > max_sl_distance:
        print(f"[paper_trade] {ticker}: SL overridden — "
              f"requested {sl_price:,.0f} ({sl_dist/entry_price*100:.1f}%) "
              f"capped to {entry_price - max_sl_distance:,.0f} (max {cfg['sl_pct']*200:.1f}%)")
        sl_price = round(entry_price - max_sl_distance)
```

**Also check**: the `check_all_open_trades()` monitor — verify it's actually checking SL levels. Search for where `sl_price` is compared against current price. If the monitor only checks TP and ignores SL, open trades will bleed indefinitely.

---

### Issue 5: RegimeClassifier Breaking in Signal Pipeline

**What's happening**

The scheduler calls `RegimeClassifier.train()` on every ticker during `scan_momentum_signals()`. This function has three known breakages with the new 3-class labels (BULL/BEAR/SIDEWAYS):

1. Numeric label filter incompatible with string labels
2. `y.astype(int)` fails on string labels
3. Return metrics hardcoded for binary (`n_trending`/`n_not_trending`)

A `NotImplementedError` guard was added to `train()` but the scheduler's `except` clause silently swallows it:

```python
except Exception as _re:
    logging.warning(f"RegimeClassifier error [{ticker}]: {_re}")
    regime_info = None
```

When `regime_info = None`, the regime filter is effectively disabled for that ticker — trades enter without regime context. The logging happens at WARNING level so it may be missed.

**How to fix**

**Short-term**: Set `filter_regime` to `0` in paper_config until the 3-class classifier is fully implemented (Tasks 6-9 from the regime 3-class plan). This avoids silently degraded filtering:

```sql
INSERT OR REPLACE INTO paper_config (key, value) VALUES ('filter_regime', '0');
```

Or via API: `POST /api/paper/config` with `{"filter_regime": 0}`

**Long-term**: Complete Tasks 6-9 from `docs/superpowers/plans/2026-05-21-regime-3class-plan.md`:
- Task 6: Update RegimeClassifier.train() for 3-class labels
- Task 7: Update all strategy routing references
- Task 8: Integration tests
- Task 9: Walk-forward revalidation

---

### Issue 6: Gap-Up Detection Removed

**What's happening**

The scheduler diff removes holiday/weekend gap-up detection from the momentum signal:

```python
# Removed:
- _date_diff = pd.to_datetime(df["date"]).diff().dt.days
- _gap_up = (df["close"] > df["close"].shift(1)) & (_date_diff > 1)
- sig = (streak | _gap_up) & (vr > 1.3) & (vr <= 5.0)

# Current:
+ sig = streak & (vr > 1.3) & (vr <= 5.0)
```

Monday morning gap-ups after weekends no longer trigger signals. If a stock gaps up 5% on Monday with VR 3×, it won't fire because the single-bar streak check fails (`df["close"] > df["close"].shift(1)` is True for the gap-up bar but the previous close was from Friday).

**How to fix**

**File: `scheduler.py`** — `scan_momentum_signals()` (line ~340)

Restore the gap-up detection but gate it more carefully (original had no volume check on the gap itself):

```python
_date_diff = pd.to_datetime(df["date"]).diff().dt.days
_gap_up = (
    (df["close"] > df["close"].shift(1)) &
    (_date_diff > 1) &
    (df["close"] > df["close"].shift(1) * 1.01)  # min 1% gap
)
sig = (streak | _gap_up) & (vr > 1.3) & (vr <= 5.0)
```

The 1% minimum gap filter prevents tiny drift over weekends from triggering false signals while capturing meaningful pre-market moves.

---

### Quick Wins (15 minutes or less)

| # | Fix | Impact |
|---|-----|--------|
| 1 | Rotate Telegram token | Security: prevent token abuse |
| 2 | `filter_regime=0` via API/config | Stop silent classifier failures from degrading signals |
| 3 | Push first screener run to 10:15 | Today would have generated 0 signals — this alone fixes the drought |
| 4 | Add NEST SL cap guard | Prevents future trades from bleeding past configured risk |

---

### Current Paper Book

| Ticker | Strategy | Entry | Price | SL | Current | P&L | Days Open |
|--------|----------|-------|-------|-----|---------|-----|-----------|
| BSML | Momentum | May 1 | 402 | — | 410 | +2.0% | 25 |
| NEST | Momentum | May 13 | 560 | 464 | 505 | -9.8% | 13 |
| CLAY | Momentum | May 14 | 2,900 | — | 2,920 | +0.7% | 12 |
| UNIC | Momentum | May 25 | 15,200 | — | 15,150 | -0.3% | 1 |

Closed: POWR (-6.5%), KSIX (-5.8%) | Combined: -12.3%

---

### Filter State

```
risk_pct: 2%      sl_pct: 2.5%       tp_pct: 3.5%
max_open: 5       dd_threshold: 8%   dd_recover: 5%
entries_blocked: 0 (not in drawdown)
filters ON:  flow, fundamental, regime, vpin, sector
filters OFF: rs
sectors_app_mode: shadow (logging only, not blocking)
agent_firm: OFF
```

---

## Part B: Video Strategy Comparison — "Hedge Fund Method" vs IDX

**Source**: "I Re-Created A Quant Trading Strategy With Claude Code" — Rowan's Markov regime framework (10 elements)

---

### The Video's 10 Elements

| # | Element | Description |
|---|---------|-------------|
| 1 | **3 States** | Bull (20d return ≥ +5%), Bear (≤ -5%), Sideways (between) |
| 2 | **State Labeling** | Label every historical day with its state (rolling 20d window) |
| 3 | **Markov Property** | Tomorrow's state depends ONLY on today's state, not full history |
| 4 | **Transition Matrix (3×3)** | Count all state transitions (bull→bear, etc.), convert to probabilities. Each row = 100% |
| 5 | **Persistence / Stickiness** | Diagonal of matrix = same-state continuation probability. Bull and Bear are "sticky" |
| 6 | **Matrix Squaring** | For N-day forecast: matrix^N. 2-day = matrix², 3-day = matrix³ |
| 7 | **Convergence** | Distant forecasts converge to uniform — no edge beyond ~28 days |
| 8 | **Signal Extraction** | `Signal = P(bull tomorrow) - P(bear tomorrow)`. Positive = long, magnitude = position size. If bear > bull → short |
| 9 | **Walk-Forward Backtesting** | Each day's matrix calibrated independently — no future data leak into past training |
| 10 | **Hidden Markov Model (HMM)** | Let HMM learn state definitions from raw price data (no subjective 5% threshold). Compare HMM labels vs rule-based labels — only trade when they agree |

The entire method is a **regime probability engine**. It doesn't use technical indicators (no RSI, MACD, VWAP, volume profile). It's pure state-transition math: count how often regimes change, compute probabilities, extract a directional signal from the probability differential.

---

### What IDX Already Has

| Video Element | IDX Equivalent | Match Quality |
|---------------|---------------|---------------|
| 1. 3 States | `detect_regime()` → BULL/BEAR/SIDEWAYS (3-class redesign in progress) | Good — same 3 labels, different thresholds |
| 2. State labeling | `label_regime_from_future()` — forward-return based labels for ML training | Partial — labels are for training, not stored as daily state series |
| 3. Markov property | Not implemented | **Missing** |
| 4. Transition matrix | Not implemented | **Missing** |
| 5. Stickiness | Not implemented | **Missing** |
| 6. Matrix squaring | Not implemented | **Missing** |
| 7. Convergence | Not implemented | **Missing** |
| 8. Signal extraction | `strategy_regime_adaptive()` routes to Momentum (trending) or VWAP Reversion (sideways) | Partial — routes strategies by regime, but doesn't extract signal from regime probabilities |
| 9. Walk-forward | `engine/walkforward_multi.py` — 12mo train / 3mo test rolling windows | Good — same concept, already running daily |
| 10. HMM | `RegimeClassifier` — Logistic Regression (not HMM) | Weak — uses LR not HMM; rule-based labels are subjective (2% threshold); no ML vs rule-based confirmation step |

### What IDX is Missing (The Gaps)

**Gap 1: Transition Matrix — The Core Engine**

The video's central innovation is the 3×3 transition probability matrix. This doesn't exist anywhere in IDX. Building it is straightforward:

```python
def build_transition_matrix(df, state_col='regime'):
    """Count state transitions and return probability matrix."""
    states = ['BULL', 'BEAR', 'SIDEWAYS']
    transitions = defaultdict(int)
    state_counts = defaultdict(int)

    for i in range(len(df) - 1):
        s_from = df[state_col].iloc[i]
        s_to = df[state_col].iloc[i + 1]
        transitions[(s_from, s_to)] += 1
        state_counts[s_from] += 1

    matrix = {}
    for s_from in states:
        matrix[s_from] = {}
        total = state_counts.get(s_from, 1)
        for s_to in states:
            matrix[s_from][s_to] = transitions[(s_from, s_to)] / total
    return matrix
```

**Gap 2: Signal from Regime Probabilities**

IDX routes strategies by regime (momentum if trending, reversion if sideways), but never computes `P(bull) - P(bear)` as a standalone signal. The video uses this differential both as:
- **Entry signal**: positive = long, negative = short
- **Position sizing**: larger differential = larger position

This could be added as a meta-layer on top of any strategy:

```python
def extract_regime_signal(transition_matrix, current_regime):
    """Signal = P(bull tomorrow) - P(bear tomorrow)"""
    probs = transition_matrix[current_regime]
    signal = probs['BULL'] - probs['BEAR']
    # signal > 0 → long bias, signal < 0 → short/cash bias
    # abs(signal) → conviction (position sizing)
    return signal
```

**Gap 3: Hidden Markov Model vs Logistic Regression**

IDX uses Logistic Regression for ML regime classification. The video describes an HMM that learns state definitions from raw price data without human-defined thresholds (the 5% bull/bear cutoff is "subjective"). The HMM discovers states from:
- Magnitude and direction of price moves
- Volatility patterns  
- Duration of stays in each state

Then the HMM labels are compared against rule-based labels — only when both agree do you trade. This dual-confirmation step eliminates false signals from either method alone.

**Gap 4: Stickiness and Forecast Horizon**

IDX has no concept of state persistence or forecast decay. The video shows:
- Bull → Bull might be 80% (sticky)
- Bear → Bear might be 75% (sticky)
- Sideways → Sideways might be 50% (less sticky — more likely to break out)

And that matrix^28 converges to uniform — meaning regime-based edge disappears beyond ~1 month. IDX's walk-forward uses 3-month test windows but doesn't analyze regime forecast horizon.

---

### How to Integrate This Into IDX

The video's method is **not a replacement** for IDX's 10 strategies. It's a **regime probability layer** that complements them. Three integration paths:

**Path A: Meta-Filter (Lowest Risk, Fastest)**

Add transition matrix computation to the signal pipeline. Before entering a trade, check:
```
if P(bull tomorrow | current regime) - P(bear tomorrow) > 0.15:
    allow trade
else:
    skip (regime doesn't confirm)
```
This would have blocked POWR (regime signal was likely weak given it was in UNCERTAIN).

Files to change: `scheduler.py` `scan_momentum_signals()`, add a `regime_signal` field to the signal dict.

**Path B: Position Sizing (Medium Risk)**

Use the regime probability differential to scale position size:
```
position_pct = base_risk_pct * (1 + abs(regime_signal))
```
Strong bull conviction → larger position. Weak signal → smaller position.

Files to change: `paper_trade.py` `open_trade()`, modify `risk_pct` calculation.

**Path C: Standalone Regime Strategy (Higher Risk, New Backtest Required)**

Implement the full Markov regime method as a new strategy in `engine/strategies.py`:
- Build transition matrix from historical daily states
- Extract signal from P(bull) - P(bear)
- Enter long when signal > threshold, exit when signal flips negative
- Run through walk-forward backtesting before paper trading

New file: `engine/markov_regime.py` (transition matrix, signal extraction, HMM integration)

**Recommendation**: Start with Path A (meta-filter). It requires the least new code, can't break existing strategies, and immediately prevents entries when regime probabilities don't support the trade direction. Implement the transition matrix in ~50 lines, add a single gate check in the signal pipeline, and observe in shadow mode for 2 weeks before enforcing.

---

### Architecture Comparison

```
VIDEO METHOD                          IDX CURRENT
─────────────                         ────────────
Price data                            Price data
    │                                      │
    ▼                                      ▼
Label daily states                    Technical indicators
(20d return threshold)                (ADX, MA slope, VR, etc.)
    │                                      │
    ▼                                      ▼
Count transitions                     Strategy signal checks
(Bull→Bear, Bear→Bull, etc.)          (check_momentum_signal, etc.)
    │                                      │
    ▼                                      ▼
3×3 probability matrix                Entry/Exit decision
    │                                 (TP/SL from config)
    ▼
Extract signal:
P(bull) - P(bear)
    │
    ▼
Position size ∝ signal
    │
    ▼
HMM confirmation
(ML labels vs rule labels)
    │
    ▼
Walk-forward validate
```

**Key difference**: The video method derives the ENTIRE trading decision from regime transition probabilities. IDX derives it from technical indicator patterns. The video method has zero technical indicators — it's pure state math. IDX has 10 strategies each with their own indicator suites.

The two approaches are orthogonal and can be stacked: IDX strategies generate candidate trades, the Markov regime layer filters and sizes them.

---

### Effort vs Impact

| Integration | Code | Backtest Required | Risk | Impact |
|------------|------|-------------------|------|--------|
| A: Meta-filter | ~50 lines | No (shadow first) | Low | Blocks bad-regime entries immediately |
| B: Position sizing | ~30 lines | No (uses existing risk framework) | Low | Scales bets by regime conviction |
| C: Standalone strategy | ~300 lines | Yes (full walk-forward) | Medium | New signal source, diversifies away from indicator-only approach |

**Total for Path A+B**: ~80 lines of Python, no new dependencies, deployable in an afternoon.
