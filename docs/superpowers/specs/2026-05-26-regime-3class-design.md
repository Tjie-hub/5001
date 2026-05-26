# Regime 3-Class Redesign: BULL / BEAR / SIDEWAYS

**Date:** 2026-05-26
**Status:** Approved

## Problem

The current regime engine collapses direction. `label_regime_from_future` uses
`abs(forward return)` so a sharp down-move and a sharp up-move both label as
"TRENDING". The ML classifier is binary (TRENDING vs NOT_TRENDING) and the
rule-based fallback uses `abs(MA-slope)`. This means the system cannot
distinguish a bull trend worth chasing from a bear trend worth avoiding — a
real signal-quality cost for a long-only book.

## Goal

Replace the two-state (TRENDING / SIDEWAYS+UNCERTAIN) regime engine with three
**directional** states — BULL / BEAR / SIDEWAYS — each routed to a different
strategy and live behavior. UNCERTAIN is retired; ambiguous bars fold into
SIDEWAYS.

---

## Section 1: Regime Detection

### Rule-based (`detect_regime`) — cold-start fallback

Signed MA-slope replaces `abs()`:

| Condition | Regime |
|---|---|
| ADX > 25 **and** MA-slope > +1.0% | `BULL` |
| ADX > 25 **and** MA-slope < −1.0% | `BEAR` |
| Everything else | `SIDEWAYS` |

The thresholds (25 / ±1.0%) are unchanged from the existing TRENDING gate;
only direction is added. No new parameters to tune.

### ML label (`label_regime_from_future`)

Signed forward-5d return (existing `forward_days=5`, `trend_threshold=2.0`
defaults retained):

| Condition | Label |
|---|---|
| fwd5 > +2.0% | `"BULL"` |
| fwd5 < −2.0% | `"BEAR"` |
| −2.0% ≤ fwd5 ≤ +2.0% | `"SIDEWAYS"` |

Returns string labels directly; sklearn `LogisticRegression` encodes them
internally via `LabelEncoder` in `fit()`.

### ML classifier (`RegimeClassifier`)

Changes from binary to multinomial:

- `LogisticRegression(multi_class='multinomial', solver='lbfgs', C=1.0,
  max_iter=500, class_weight='balanced', random_state=42)`
- `predict()` returns `(regime_str, confidence)` where `confidence =
  max(predict_proba(...))` — unchanged interface, new label set.
- `feature_importance` in train metrics: `coef_` is now shape `(3, n_features)`;
  report per-class coefficients keyed by class name.
- Minimum sample guard raised to 60 (was 50) to ensure each class has
  reasonable support.

### Macro overlay (`apply_macro_overlay`)

Old behaviour: IDR-weakening downgrades `TRENDING → UNCERTAIN`.
New behaviour: IDR-weakening / high-BI-rate downgrades `BULL → SIDEWAYS`
(don't chase longs into a macro headwind). `BEAR` is never upgraded by macro
— bear stays bear regardless.

---

## Section 2: Strategy Routing

### Backtest / walk-forward (`strategy_regime_adaptive`)

| Regime | Strategy run | Notes |
|---|---|---|
| `BULL` | `strategy_momentum` | long entries as today |
| `SIDEWAYS` | `strategy_vwap_reversion` | range-fade as today |
| `BEAR` | no trades — flat equity | same safe pass-through as old UNCERTAIN |

Regime is **per-ticker** (computed from each ticker's own OHLCV df), not a
single market-wide switch. This is unchanged from the current architecture.

### Live scan (scheduler `scheduled_multi_strategy_scan`)

Same routing as backtest for BULL and SIDEWAYS. BEAR triggers the dip-scout
instead of an entry (see Section 3). The firm evaluate() call still runs on
flow-confirmed signals regardless of regime (shadow/enforce logic unchanged).

---

## Section 3: Bear Dip-Scout Watchlist

Bear is a **scouting phase** — no new longs, but identify oversold quality
names ready to re-enter when the ticker flips back to BULL.

### New table: `regime_watchlist`

```sql
CREATE TABLE IF NOT EXISTS regime_watchlist (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker      TEXT NOT NULL,
    added_date  TEXT NOT NULL,
    regime_at_add TEXT NOT NULL DEFAULT 'BEAR',
    rsi_at_add  REAL,
    close_vs_ma50_pct REAL,
    wf_score    REAL,
    status      TEXT NOT NULL DEFAULT 'active',  -- active | promoted | expired
    promoted_date TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_rwl_ticker_status ON regime_watchlist(ticker, status);
```

### Add-to-watchlist criteria (BEAR lane in live scan)

A ticker is added (or its entry refreshed) when ALL:
1. Live regime = `BEAR`
2. RSI-14 < 35 (oversold — tunable, default 35 as looser than the classic 30)
3. `wf_scores.weighted_score` (best strategy for this ticker) ≥ 60.0
4. Not already OPEN in `paper_trades`
5. Not already `active` in `regime_watchlist`

RSI-14 and close-vs-MA50 are stored at time of add for post-audit.

### Promotion to BULL entry (live scan)

When a ticker's regime flips to BULL **and** it has `status='active'` in
`regime_watchlist`, it is marked `status='promoted'` and surfaced at the top
of the flow-confirmed candidate list for that scan cycle. The existing
flow-filter and agent-firm gates still apply — promotion grants priority, not
a free pass.

### Expiry

Entries older than 20 trading days with `status='active'` are set to
`status='expired'` at the start of each scan. Twenty trading days ≈ one
calendar month; stale bear theses lose relevance quickly on IDX.

### Auto-entry vs surface-only

**Surface-only with priority.** Promoted names appear first in the candidate
list but still pass through all existing gates (flow, agent firm, sector).
Full auto-entry (bypassing gates) is deferred until watchlist outcomes
accumulate enough history to validate the thesis.

---

## Section 4: Blast Radius

### Files changed

| File | What changes |
|---|---|
| `engine/regime_filter.py` | `detect_regime`, `label_regime_from_future`, `RegimeClassifier`, `strategy_regime_adaptive`, `apply_macro_overlay` |
| `engine/walkforward_multi.py` | Verify multiclass path; update any TRENDING/UNCERTAIN string checks |
| `app.py` | Live regime status endpoint (`109–177`); backtest-cache display (`257–335`); `backtest_cache.regime` column refreshes on recompute — no destructive migration |
| `templates/` | Regime badge colours / labels (TRENDING→BULL, UNCERTAIN removed) |
| `scheduler.py` | New dip-scout block in bear lane; regime_watchlist migration on start |
| `engine/agent_firm/smoke.py` | Canned `regime="TRENDING"` → `"BULL"` |
| `engine/agent_firm/prompts/regime_v1.md` | Verify no hardcoded old labels break LLM context |
| `engine/agent_firm/analytics.py` | Regime grouping — check no hardcoded label comparisons |

### DB migrations (non-destructive)

1. New table `regime_watchlist` — `CREATE TABLE IF NOT EXISTS` on scheduler
   start (safe to run repeatedly).
2. `backtest_cache.regime` — TEXT column already exists; values refresh on
   next compute cycle. No ALTER TABLE needed.

---

## Section 5: Learning Impact ("Train and Grow")

### What trains now (price-based, data-rich)

- `RegimeClassifier` retrains every walk-forward window and on each live
  regime-status call with `train=True`. Multinomial improves as OHLCV bars
  accumulate; BEAR/BULL separation sharpens over time.
- Per-regime strategy performance (BULL-momentum vs SIDEWAYS-reversion)
  becomes independently measurable in `audit_signals.py` — feeding the
  continuous improvement loop.

### What trains slowly (outcome-based, data-starved)

- Bear-watchlist promotion win-rate: needs months of promoted→paper-trade
  outcomes before the 35 RSI / 60 wf_score thresholds can be validated.
  Treat as scaffolding for now; thresholds are deliberately conservative.

---

## Section 6: Testing

| Test type | Coverage |
|---|---|
| Unit: `label_regime_from_future` | Returns exactly three distinct string values; proportions match signed return distribution on synthetic data |
| Unit: `detect_regime` | Returns `BULL` on synthetic up-trend df, `BEAR` on down-trend, `SIDEWAYS` on flat |
| Unit: `RegimeClassifier.train` | Trains without error; `predict()` returns (str, float) where str ∈ {BULL, BEAR, SIDEWAYS} |
| Unit: `apply_macro_overlay` | IDR-weakening BULL→SIDEWAYS; BEAR unchanged |
| Unit: `strategy_regime_adaptive` | BULL routes to momentum, SIDEWAYS to vwap_reversion, BEAR returns flat equity |
| Integration: walk-forward regression | Run on 3 tickers; no crash; `Regime Adaptive` equity curve produced |
| Agent-firm fixtures | Update `regime="TRENDING"` → `"BULL"` in test conftest and smoke |
| Watchlist: add logic | Oversold BEAR ticker added; non-oversold skipped; duplicate skipped |
| Watchlist: promote logic | BULL flip promotes active entry; expired entries not promoted |

---

## Open Decisions (for implementation)

- **RSI-14 oversold threshold** — defaulting to 35. Adjust post-audit once
  watchlist has ≥30 entries.
- **wf_score minimum** — defaulting to 60.0 (top-third of typical scores).
  Adjust post-audit.
- **Forward-days for ML label** — keeping 5. Can experiment with 3 or 10 in
  a later tuning pass.
