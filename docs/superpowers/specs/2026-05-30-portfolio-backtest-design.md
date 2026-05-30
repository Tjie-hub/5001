# Portfolio Backtest — Design Spec (R6)

**Date:** 2026-05-30
**Status:** Approved for implementation

---

## Goal

Add portfolio-level backtesting to IDX Walkforward so a single sector's tickers can be run as a group, revealing sector concentration risk, combined equity performance, and inter-ticker correlation. Primary use case: "How would BRPT have looked as part of the BasicMaterials sector portfolio?"

---

## Architecture

### New files

| File | Role |
|---|---|
| `engine/portfolio_backtest.py` | Core engine: equal-split capital, per-ticker runs, equity merge, metrics |
| `routes/portfolio.py` | Flask Blueprint: `POST /api/portfolio/backtest`, `GET /api/portfolio/sectors` |
| `templates/portfolio.html` | Full dashboard UI |
| `tests/test_portfolio_backtest.py` | Unit tests for engine |

### Modified files

| File | Change |
|---|---|
| `app.py` | Import + register `portfolio_bp`; add `GET /portfolio` page route |

### Data flow

```
User picks sector + strategy + capital
  → POST /api/portfolio/backtest
  → IDX_SECTOR_MAP[sector] → N tickers
  → for each ticker: load OHLCV from DB, skip if < 60 bars
  → run STRATEGY_FUNCS[strategy](df, capital=capital/N)
  → build date-indexed equity Series per ticker
  → merge on date intersection → portfolio equity curve
  → compute portfolio metrics + per-ticker metrics + correlation matrix
  → return JSON → render dashboard
```

---

## Engine: `engine/portfolio_backtest.py`

### Entry point

```python
def run_portfolio_backtest(
    tickers: list[str],
    strategy: str,
    capital: float,
    db_path: str,
) -> dict
```

### Per-ticker processing

- `per_cap = capital / len(tickers)`
- Load OHLCV via `pd.read_sql` for each ticker; skip if `len(df) < 60`
- Run `STRATEGY_FUNCS[strategy](df, capital=per_cap)` → raw result with `trades`, `equity`
- Align equity list to df's date column → `pd.Series` indexed by date string

### Equity curve merging

- Find date intersection across all tickers with data
- Sum per-ticker equity Series on common dates → portfolio equity Series
- Portfolio daily returns: `portfolio_equity.pct_change().dropna()`

### Metrics computed

**Portfolio-level:**
- `total_return_pct`: `(final - initial) / initial * 100`
- `sharpe`: annualised `(mean_daily_ret / std_daily_ret) * sqrt(252)`
- `max_drawdown_pct`: min of `(equity - running_max) / running_max * 100`
- `rolling_sharpe`: 60-day rolling window of the above Sharpe formula, one point per date
- `drawdown_curve`: per-date drawdown % of portfolio equity
- `concurrent_positions`: per-date count of tickers with an open trade

**Per-ticker:**
- `total_return_pct`, `sharpe`, `max_drawdown_pct` — same formulas applied to per-ticker equity
- `total_trades`, `win_rate` — from `compute_metrics()` in `walkforward_multi.py`
- `equity_curve`, `drawdown_curve` — per-ticker series

**Correlation:**
- Build DataFrame of per-ticker daily returns (date × ticker)
- `df.corr()` → symmetric N×N matrix
- Return as `{"tickers": [...], "matrix": [[...], ...]}`

### Output schema

```python
{
  "sector": str,
  "strategy": str,
  "capital": float,
  "tickers_used": list[str],
  "tickers_skipped": list[str],        # < 60 bars
  "portfolio": {
    "equity_curve":           list[{"date": str, "value": float}],
    "drawdown_curve":         list[{"date": str, "dd_pct": float}],
    "rolling_sharpe":         list[{"date": str, "sharpe": float}],
    "concurrent_positions":   list[{"date": str, "count": int}],
    "total_return_pct":       float,
    "sharpe":                 float,
    "max_drawdown_pct":       float,
  },
  "per_ticker": list[{
    "ticker":             str,
    "allocation":         float,
    "equity_curve":       list[{"date": str, "value": float}],
    "drawdown_curve":     list[{"date": str, "dd_pct": float}],
    "total_return_pct":   float,
    "sharpe":             float,
    "max_drawdown_pct":   float,
    "total_trades":       int,
    "win_rate":           float,
  }],
  "correlation": {
    "tickers": list[str],
    "matrix":  list[list[float]],
  }
}
```

---

## API: `routes/portfolio.py`

### `GET /api/portfolio/sectors`

Returns sector names and their tickers from `IDX_SECTOR_MAP`:

```json
{
  "sectors": {
    "BasicMaterials": ["BRPT", "ANTM", "INCO", ...],
    "Energy": ["ADRO", "PTBA", ...],
    ...
  }
}
```

### `POST /api/portfolio/backtest`

Request body:
```json
{"sector": "BasicMaterials", "strategy": "vol_weighted", "capital": 50000000}
```

Validation:
- `sector` must be a key in `IDX_SECTOR_MAP` → 400 if not
- `strategy` must be a key in `STRATEGY_FUNCS` → 400 if not
- `capital` must be > 0 → 400 if not

Returns the full output schema above, or:
- 400 `{"error": "No tickers with sufficient data"}` if all tickers skipped

---

## Frontend: `templates/portfolio.html`

### Controls bar

Sector dropdown (populated from `GET /api/portfolio/sectors`), Strategy dropdown (populated from `GET /api/strategy/list`), Capital input (default 50,000,000), Run button. Spinner shown during compute.

### Metrics cards row

Total Return % | Portfolio Sharpe | Max Drawdown % | Tickers Used

### Chart panels (Lightweight Charts, same library as `dive.html`)

1. **Portfolio equity curve** — single line, total portfolio value over time
2. **Per-ticker equity curves** — N lines overlaid, one color per ticker, legend with ticker + return%
3. **Rolling 60-day Sharpe** — line chart, dashed horizontal zero reference line
4. **Drawdown waterfall** — per-ticker drawdown curves overlaid, semi-transparent area fills

### Concurrent positions chart

Simple bar chart (vanilla JS canvas): date on x-axis, count of open positions on y-axis. Shows capital utilization over time.

### Per-ticker breakdown table

Columns: Ticker | Allocation (IDR) | Return % | Sharpe | Max DD % | Trades | Win Rate

Sortable by any column (vanilla JS sort on click). Rows colored green/red by return sign.

### Correlation heatmap

HTML `<table>` with cells colored green (correlation = +1) → white (0) → red (−1) via inline `background-color`. Cell text shows correlation to 2 decimal places. Hidden if only 1 ticker (Infrastructure/AKRA case).

---

## Error Handling & Edge Cases

| Case | Behaviour |
|---|---|
| Ticker < 60 bars | Silently skipped; listed in `tickers_skipped` |
| All tickers skipped | 400 `{"error": "No tickers with sufficient data"}` |
| Unknown sector | 400 `{"error": "Unknown sector: X"}` |
| Unknown strategy | 400 `{"error": "Unknown strategy: X"}` |
| Single ticker (Infrastructure/AKRA) | Runs fine; correlation heatmap hidden |
| Non-overlapping date ranges | Tickers excluded from correlation; portfolio equity uses date intersection |
| Strategy returns 0 trades | Flat equity at `per_cap`; included in portfolio |
| Compute time | Sequential ~200ms/ticker; ~3s for 14-ticker sector — spinner covers this |

---

## Tests: `tests/test_portfolio_backtest.py`

- Mock OHLCV for 2 tickers (60 bars each, identical dates)
- Assert `equity_curve` length == number of dates in intersection
- Assert portfolio return equals weighted average of per-ticker returns (equal weights)
- Assert correlation matrix is symmetric and diagonal is 1.0
- Assert ticker with < 60 bars appears in `tickers_skipped`, not `tickers_used`
- Assert 400 returned when all tickers skipped
- Assert 400 returned for unknown sector / unknown strategy
