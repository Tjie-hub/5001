# Portfolio Backtest Implementation Plan (R6)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add sector-level portfolio backtesting — run N tickers with equal-split capital, merge equity curves, compute portfolio Sharpe/drawdown/correlation, and display a full dashboard at `/portfolio`.

**Architecture:** `engine/portfolio_backtest.py` runs each ticker sequentially using existing `STRATEGY_FUNCS`, merges per-ticker equity Series on the date intersection, computes portfolio + per-ticker metrics + correlation matrix. A new Flask Blueprint `routes/portfolio.py` exposes `GET /api/portfolio/sectors` and `POST /api/portfolio/backtest`. `templates/portfolio.html` renders 4 Lightweight Charts panels, a concurrent-positions bar chart, a per-ticker table, and a correlation heatmap.

**Tech Stack:** Python (pandas, numpy), Flask Blueprint, SQLite, Lightweight Charts v4.2.0, vanilla JS.

---

## File Map

| File | Action | Role |
|---|---|---|
| `engine/portfolio_backtest.py` | Create | Core engine: load OHLCV, run strategy per ticker, merge equity, compute metrics |
| `tests/test_portfolio_backtest.py` | Create | Unit tests (mock `_load_ohlcv` to avoid DB) |
| `routes/portfolio.py` | Create | Blueprint: `/api/portfolio/sectors`, `/api/portfolio/backtest` |
| `templates/portfolio.html` | Create | Full dashboard UI |
| `app.py` | Modify | Import + register `portfolio_bp`; add `GET /portfolio` page route |

**Baseline:** 97 tests pass:
```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && \
  /home/tjiesar/10\ Projects/idx-walkforward-5001/venv/bin/python -m pytest tests/ -q --tb=no \
  --ignore=tests/agent_firm --ignore=tests/test_scheduler_firm_hook.py \
  --ignore=tests/test_screener_stockbit_error.py
```

---

## Task 1: Write failing tests

**Files:**
- Create: `tests/test_portfolio_backtest.py`

- [ ] **Step 1: Write the test file**

```python
"""Tests for engine/portfolio_backtest.py"""
import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch


def _make_df(n=80, seed=42):
    np.random.seed(seed)
    close = np.cumprod(1 + np.random.normal(0.0005, 0.02, n)) * 1000
    return pd.DataFrame({
        'date':   pd.date_range('2024-01-02', periods=n, freq='B').strftime('%Y-%m-%d'),
        'open':   (close * 0.99).round(0),
        'high':   (close * 1.02).round(0),
        'low':    (close * 0.97).round(0),
        'close':  close.round(0),
        'volume': np.random.randint(1_000_000, 5_000_000, n).astype(float),
    })


def test_run_returns_expected_keys():
    from engine.portfolio_backtest import run_portfolio_backtest
    df = _make_df(80, seed=1)
    with patch('engine.portfolio_backtest._load_ohlcv', return_value=df):
        result = run_portfolio_backtest(['AAA', 'BBB'], 'vol_weighted', 10_000_000, ':memory:')
    assert 'portfolio' in result
    assert 'per_ticker' in result
    assert 'correlation' in result
    assert 'tickers_used' in result
    assert 'tickers_skipped' in result


def test_equity_curve_length_equals_date_intersection():
    from engine.portfolio_backtest import run_portfolio_backtest
    df_a = _make_df(80, seed=1)
    df_b = _make_df(80, seed=2)  # same 80 dates

    def _mock(ticker, db_path):
        return df_a if ticker == 'AAA' else df_b

    with patch('engine.portfolio_backtest._load_ohlcv', side_effect=_mock):
        result = run_portfolio_backtest(['AAA', 'BBB'], 'vol_weighted', 10_000_000, ':memory:')

    assert len(result['portfolio']['equity_curve']) == 80


def test_portfolio_return_equals_equal_weight_average():
    from engine.portfolio_backtest import run_portfolio_backtest
    df_a = _make_df(80, seed=1)
    df_b = _make_df(80, seed=2)

    def _mock(ticker, db_path):
        return df_a if ticker == 'AAA' else df_b

    with patch('engine.portfolio_backtest._load_ohlcv', side_effect=_mock):
        result = run_portfolio_backtest(['AAA', 'BBB'], 'vol_weighted', 10_000_000, ':memory:')

    r_a = result['per_ticker'][0]['total_return_pct']
    r_b = result['per_ticker'][1]['total_return_pct']
    expected = (r_a + r_b) / 2
    assert abs(result['portfolio']['total_return_pct'] - expected) < 1.0


def test_correlation_matrix_symmetric_and_diagonal_one():
    from engine.portfolio_backtest import run_portfolio_backtest
    df_a = _make_df(80, seed=1)
    df_b = _make_df(80, seed=2)

    def _mock(ticker, db_path):
        return df_a if ticker == 'AAA' else df_b

    with patch('engine.portfolio_backtest._load_ohlcv', side_effect=_mock):
        result = run_portfolio_backtest(['AAA', 'BBB'], 'vol_weighted', 10_000_000, ':memory:')

    m = result['correlation']['matrix']
    assert m[0][0] == 1.0
    assert m[1][1] == 1.0
    assert abs(m[0][1] - m[1][0]) < 0.001


def test_ticker_skipped_if_less_than_60_bars():
    from engine.portfolio_backtest import run_portfolio_backtest
    df_short = _make_df(30, seed=1)
    df_ok    = _make_df(80, seed=2)

    def _mock(ticker, db_path):
        return df_short if ticker == 'SHORT' else df_ok

    with patch('engine.portfolio_backtest._load_ohlcv', side_effect=_mock):
        result = run_portfolio_backtest(['SHORT', 'OK'], 'vol_weighted', 10_000_000, ':memory:')

    assert 'SHORT' in result['tickers_skipped']
    assert 'OK' in result['tickers_used']


def test_all_skipped_raises_value_error():
    from engine.portfolio_backtest import run_portfolio_backtest
    df_short = _make_df(30, seed=1)
    with patch('engine.portfolio_backtest._load_ohlcv', return_value=df_short):
        with pytest.raises(ValueError, match='No tickers with sufficient data'):
            run_portfolio_backtest(['AAA', 'BBB'], 'vol_weighted', 10_000_000, ':memory:')


def test_unknown_strategy_raises_value_error():
    from engine.portfolio_backtest import run_portfolio_backtest
    with pytest.raises(ValueError, match='Unknown strategy'):
        run_portfolio_backtest(['AAA'], 'nonexistent_strat', 10_000_000, ':memory:')


def test_single_ticker_correlation_is_one_by_one():
    from engine.portfolio_backtest import run_portfolio_backtest
    df = _make_df(80, seed=1)
    with patch('engine.portfolio_backtest._load_ohlcv', return_value=df):
        result = run_portfolio_backtest(['AAA'], 'vol_weighted', 10_000_000, ':memory:')
    assert result['correlation']['matrix'] == [[1.0]]
    assert result['correlation']['tickers'] == ['AAA']


def test_per_ticker_allocation_sums_to_capital():
    from engine.portfolio_backtest import run_portfolio_backtest
    df = _make_df(80, seed=1)
    with patch('engine.portfolio_backtest._load_ohlcv', return_value=df):
        result = run_portfolio_backtest(['AAA', 'BBB', 'CCC'], 'vol_weighted', 9_000_000, ':memory:')
    total = sum(t['allocation'] for t in result['per_ticker'])
    assert abs(total - 9_000_000) < 10  # rounding tolerance
```

- [ ] **Step 2: Run tests — confirm they all FAIL**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && \
  /home/tjiesar/10\ Projects/idx-walkforward-5001/venv/bin/python -m pytest \
  tests/test_portfolio_backtest.py -v 2>&1 | tail -15
```

Expected: all 9 tests FAIL with `ModuleNotFoundError: No module named 'engine.portfolio_backtest'`

- [ ] **Step 3: Commit the test file**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && \
  git add tests/test_portfolio_backtest.py && \
  git commit -m "test(r6): add failing tests for portfolio_backtest engine"
```

---

## Task 2: Implement `engine/portfolio_backtest.py`

**Files:**
- Create: `engine/portfolio_backtest.py`

- [ ] **Step 1: Create the engine file**

```python
"""engine/portfolio_backtest.py — Portfolio-level backtesting across N tickers."""
import sqlite3
import logging

import numpy as np
import pandas as pd

from engine.walkforward_multi import STRATEGY_FUNCS, compute_metrics


def _load_ohlcv(ticker: str, db_path: str) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql(
        'SELECT date, open, high, low, close, volume FROM ohlcv '
        'WHERE ticker=? ORDER BY date ASC',
        conn, params=(ticker,)
    )
    conn.close()
    for c in ['open', 'high', 'low', 'close', 'volume']:
        df[c] = df[c].astype(float)
    return df


def _drawdown_curve(equity_series: pd.Series) -> list:
    peak = equity_series.cummax()
    dd = (equity_series - peak) / peak * 100
    return [{'date': str(d)[:10], 'dd_pct': round(float(v), 2)} for d, v in dd.items()]


def _rolling_sharpe(daily_ret: pd.Series, window: int = 60) -> list:
    def _sharpe(x):
        s = x.std()
        return float((x.mean() / s) * np.sqrt(252)) if s > 0 else 0.0
    rs = daily_ret.rolling(window).apply(_sharpe, raw=False)
    return [
        {'date': str(d)[:10], 'sharpe': round(float(v), 2)}
        for d, v in rs.dropna().items()
    ]


def _concurrent_positions(all_trades: list, dates: list) -> list:
    date_index = {d: i for i, d in enumerate(dates)}
    counts = [0] * len(dates)
    for ticker_trades in all_trades:
        for trade in ticker_trades:
            try:
                rng = pd.date_range(trade.entry_date, trade.exit_date, freq='B')
                for d in rng:
                    ds = d.strftime('%Y-%m-%d')
                    if ds in date_index:
                        counts[date_index[ds]] += 1
            except Exception:
                pass
    return [{'date': d, 'count': counts[i]} for i, d in enumerate(dates)]


def _correlation_matrix(ticker_returns: dict) -> dict:
    tickers = list(ticker_returns.keys())
    if len(tickers) < 2:
        return {'tickers': tickers, 'matrix': [[1.0]]}
    df = pd.DataFrame(ticker_returns).dropna()
    corr = df.corr()
    matrix = [
        [round(float(corr.loc[t1, t2]), 3) for t2 in tickers]
        for t1 in tickers
    ]
    return {'tickers': tickers, 'matrix': matrix}


def run_portfolio_backtest(
    tickers: list,
    strategy: str,
    capital: float,
    db_path: str,
) -> dict:
    """Run strategy on each ticker with equal capital split; return combined portfolio metrics.

    Args:
        tickers:  List of ticker strings.
        strategy: Key into STRATEGY_FUNCS.
        capital:  Total portfolio capital (IDR). Split equally across tickers.
        db_path:  SQLite database path.

    Returns:
        Dict with keys: tickers_used, tickers_skipped, portfolio, per_ticker, correlation.

    Raises:
        ValueError: Unknown strategy, or no tickers with sufficient data.
    """
    if strategy not in STRATEGY_FUNCS:
        raise ValueError(f'Unknown strategy: {strategy}')

    func = STRATEGY_FUNCS[strategy]
    n = len(tickers)
    per_cap = capital / n

    ticker_equity: dict[str, pd.Series] = {}
    ticker_daily_ret: dict[str, pd.Series] = {}
    all_trades: list = []
    per_ticker_out: list = []
    tickers_used: list = []
    tickers_skipped: list = []

    for ticker in tickers:
        try:
            df = _load_ohlcv(ticker, db_path)
        except Exception as e:
            logging.warning('portfolio_backtest: failed to load %s: %s', ticker, e)
            tickers_skipped.append(ticker)
            continue

        if len(df) < 60:
            tickers_skipped.append(ticker)
            continue

        raw = func(df, capital=per_cap)
        dates = [str(d)[:10] for d in df['date']]
        eq = pd.Series(raw['equity'], index=dates)
        daily_ret = eq.pct_change().dropna()

        metrics = compute_metrics(raw)
        ticker_equity[ticker] = eq
        ticker_daily_ret[ticker] = daily_ret
        all_trades.append(raw['trades'])
        tickers_used.append(ticker)

        per_ticker_out.append({
            'ticker':            ticker,
            'allocation':        round(per_cap),
            'equity_curve':      [{'date': d, 'value': round(float(v))} for d, v in eq.items()],
            'drawdown_curve':    _drawdown_curve(eq),
            'total_return_pct':  metrics['total_return_pct'],
            'sharpe':            metrics['sharpe'],
            'max_drawdown_pct':  metrics['max_drawdown_pct'],
            'total_trades':      metrics['total_trades'],
            'win_rate':          metrics['win_rate'],
        })

    if not tickers_used:
        raise ValueError('No tickers with sufficient data')

    # ── Merge equity curves on date intersection ──────────────────────────────
    common_dates = sorted(
        set.intersection(*[set(s.index) for s in ticker_equity.values()])
    )

    portfolio_eq = sum(s.loc[common_dates] for s in ticker_equity.values())
    port_daily_ret = portfolio_eq.pct_change().dropna()

    peak = portfolio_eq.cummax()
    dd_series = (portfolio_eq - peak) / peak * 100
    total_return = (float(portfolio_eq.iloc[-1]) - float(portfolio_eq.iloc[0])) / float(portfolio_eq.iloc[0]) * 100
    std = port_daily_ret.std()
    sharpe = float((port_daily_ret.mean() / std) * np.sqrt(252)) if std > 0 else 0.0

    return {
        'tickers_used':    tickers_used,
        'tickers_skipped': tickers_skipped,
        'portfolio': {
            'equity_curve':         [{'date': d, 'value': round(float(v))} for d, v in portfolio_eq.items()],
            'drawdown_curve':       [{'date': str(d)[:10], 'dd_pct': round(float(v), 2)} for d, v in dd_series.items()],
            'rolling_sharpe':       _rolling_sharpe(port_daily_ret),
            'concurrent_positions': _concurrent_positions(all_trades, common_dates),
            'total_return_pct':     round(total_return, 2),
            'sharpe':               round(sharpe, 2),
            'max_drawdown_pct':     round(float(dd_series.min()), 2),
        },
        'per_ticker':  per_ticker_out,
        'correlation': _correlation_matrix(ticker_daily_ret),
    }
```

- [ ] **Step 2: Run tests — confirm they all PASS**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && \
  /home/tjiesar/10\ Projects/idx-walkforward-5001/venv/bin/python -m pytest \
  tests/test_portfolio_backtest.py -v 2>&1 | tail -15
```

Expected: 9 passed

- [ ] **Step 3: Run full suite to confirm no regressions**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && \
  /home/tjiesar/10\ Projects/idx-walkforward-5001/venv/bin/python -m pytest tests/ -q --tb=short \
  --ignore=tests/agent_firm --ignore=tests/test_scheduler_firm_hook.py \
  --ignore=tests/test_screener_stockbit_error.py
```

Expected: 106 passed (97 + 9 new)

- [ ] **Step 4: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && \
  git add engine/portfolio_backtest.py && \
  git commit -m "feat(r6): add engine/portfolio_backtest.py — equal-split capital, equity merge, metrics, correlation"
```

---

## Task 3: API routes + app.py wiring

**Files:**
- Create: `routes/portfolio.py`
- Modify: `app.py`

- [ ] **Step 1: Create `routes/portfolio.py`**

```python
"""routes/portfolio.py — Portfolio backtest API."""
import logging

from flask import Blueprint, jsonify, request

from config import DB_PATH
from engine.sector_rotation import IDX_SECTOR_MAP
from engine.walkforward_multi import STRATEGY_FUNCS
from engine.portfolio_backtest import run_portfolio_backtest

portfolio_bp = Blueprint('portfolio', __name__)


@portfolio_bp.route('/api/portfolio/sectors', methods=['GET'])
def api_portfolio_sectors():
    return jsonify({'sectors': {k: list(v) for k, v in IDX_SECTOR_MAP.items()}})


@portfolio_bp.route('/api/portfolio/backtest', methods=['POST'])
def api_portfolio_backtest():
    body = request.get_json(force=True) or {}
    sector   = body.get('sector', '')
    strategy = body.get('strategy', 'vol_weighted')
    capital  = float(body.get('capital', 50_000_000))

    if sector not in IDX_SECTOR_MAP:
        return jsonify({'error': f'Unknown sector: {sector}'}), 400
    if strategy not in STRATEGY_FUNCS:
        return jsonify({'error': f'Unknown strategy: {strategy}'}), 400
    if capital <= 0:
        return jsonify({'error': 'capital must be > 0'}), 400

    tickers = list(IDX_SECTOR_MAP[sector])
    try:
        result = run_portfolio_backtest(tickers, strategy, capital, DB_PATH)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception:
        logging.exception('portfolio backtest error')
        return jsonify({'error': 'internal error'}), 500

    return jsonify({'sector': sector, 'strategy': strategy, 'capital': capital, **result})
```

- [ ] **Step 2: Wire into `app.py`**

Add after the existing blueprint imports (e.g. after `from routes.backtest import backtest_bp`):

```python
from routes.portfolio import portfolio_bp
```

Add after the existing `app.register_blueprint(backtest_bp)` line:

```python
app.register_blueprint(portfolio_bp)
```

Add after the existing `screener_page` route (before `if __name__ == "__main__":`):

```python
@app.route("/portfolio")
def portfolio_page():
    return render_template("portfolio.html")
```

- [ ] **Step 3: Verify import and routes registered**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && \
  /home/tjiesar/10\ Projects/idx-walkforward-5001/venv/bin/python -c "
import os; os.environ.setdefault('DB_PATH', 'data/walkforward.db')
import app as m
rules = [str(r) for r in m.app.url_map.iter_rules()]
print([r for r in rules if 'portfolio' in r])
"
```

Expected: `['/api/portfolio/sectors', '/api/portfolio/backtest', '/portfolio']`

- [ ] **Step 4: Run full test suite**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && \
  /home/tjiesar/10\ Projects/idx-walkforward-5001/venv/bin/python -m pytest tests/ -q --tb=short \
  --ignore=tests/agent_firm --ignore=tests/test_scheduler_firm_hook.py \
  --ignore=tests/test_screener_stockbit_error.py
```

Expected: 106 passed

- [ ] **Step 5: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && \
  git add routes/portfolio.py app.py && \
  git commit -m "feat(r6): add routes/portfolio.py + /portfolio page route"
```

---

## Task 4: Frontend dashboard `templates/portfolio.html`

**Files:**
- Create: `templates/portfolio.html`

- [ ] **Step 1: Create the template**

```html
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Portfolio Backtest</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
  <style>
    :root {
      --bg:     #08090d; --card:  #0d0f18; --card2: #121520;
      --border: rgba(255,255,255,.07); --text: #e8edf4;
      --mute:   #4e5f7a; --accent: #6366f1;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; font-size: 14px; }

    /* ── TOPBAR ── */
    .topbar { display: flex; align-items: center; gap: 12px; padding: 10px 20px;
      background: var(--card); border-bottom: 1px solid var(--border); flex-wrap: wrap; }
    .topbar h1 { font-size: 16px; font-weight: 600; margin-right: 8px; }
    .topbar select, .topbar input[type=number] {
      background: var(--card2); border: 1px solid var(--border); color: var(--text);
      padding: 6px 10px; border-radius: 6px; font-size: 13px; }
    .topbar label { color: var(--mute); font-size: 12px; }
    .btn { padding: 7px 18px; border-radius: 6px; border: none; cursor: pointer;
      font-size: 13px; font-weight: 600; }
    .btn-primary { background: var(--accent); color: #fff; }
    .btn-primary:disabled { opacity: .4; cursor: not-allowed; }
    .spinner { display: none; color: var(--mute); font-size: 13px; }

    /* ── METRICS CARDS ── */
    .metrics { display: flex; gap: 12px; padding: 16px 20px; flex-wrap: wrap; }
    .metric-card { background: var(--card); border: 1px solid var(--border);
      border-radius: 8px; padding: 14px 20px; min-width: 150px; }
    .metric-card .label { color: var(--mute); font-size: 11px; text-transform: uppercase;
      letter-spacing: .05em; margin-bottom: 4px; }
    .metric-card .value { font-size: 22px; font-weight: 700; }
    .pos { color: #22c55e; } .neg { color: #ef4444; } .neu { color: var(--text); }

    /* ── CHART GRID ── */
    .charts-grid { display: grid; grid-template-columns: 1fr 1fr;
      gap: 16px; padding: 0 20px 16px; }
    @media (max-width: 900px) { .charts-grid { grid-template-columns: 1fr; } }
    .chart-panel { background: var(--card); border: 1px solid var(--border);
      border-radius: 8px; overflow: hidden; }
    .chart-panel .panel-title { padding: 10px 14px; font-size: 12px; font-weight: 600;
      color: var(--mute); text-transform: uppercase; letter-spacing: .05em;
      border-bottom: 1px solid var(--border); }
    .chart-box { height: 220px; }

    /* ── CONCURRENT POSITIONS ── */
    .conc-section { padding: 0 20px 16px; }
    .conc-panel { background: var(--card); border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
    .conc-panel .panel-title { padding: 10px 14px; font-size: 12px; font-weight: 600;
      color: var(--mute); text-transform: uppercase; letter-spacing: .05em;
      border-bottom: 1px solid var(--border); }
    #concCanvas { width: 100%; height: 80px; display: block; }

    /* ── TABLE ── */
    .table-section { padding: 0 20px 16px; }
    .section-title { font-size: 13px; font-weight: 600; color: var(--mute);
      text-transform: uppercase; letter-spacing: .05em; margin-bottom: 10px; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th { background: var(--card2); padding: 8px 12px; text-align: left; color: var(--mute);
      font-weight: 500; cursor: pointer; user-select: none; font-size: 11px;
      text-transform: uppercase; border-bottom: 1px solid var(--border); }
    th:hover { color: var(--text); }
    td { padding: 8px 12px; border-bottom: 1px solid var(--border); }
    tr:hover td { background: var(--card2); }

    /* ── HEATMAP ── */
    .heatmap-section { padding: 0 20px 24px; }
    .heatmap { border-collapse: collapse; font-size: 12px; }
    .heatmap th { background: var(--card2); padding: 6px 10px; text-align: center;
      color: var(--mute); font-weight: 500; border: 1px solid var(--border); }
    .heatmap td { padding: 6px 10px; text-align: center; border: 1px solid var(--border);
      font-family: 'JetBrains Mono', monospace; min-width: 56px; }

    /* ── SKIPPED NOTICE ── */
    .notice { color: var(--mute); font-size: 12px; padding: 4px 0; }
    .hidden { display: none !important; }
    .full-width { grid-column: 1 / -1; }
  </style>
</head>
<body>

<!-- TOPBAR -->
<div class="topbar">
  <h1>Portfolio Backtest</h1>
  <div>
    <label>Sector</label><br>
    <select id="sectorSel"></select>
  </div>
  <div>
    <label>Strategy</label><br>
    <select id="strategySel"></select>
  </div>
  <div>
    <label>Capital (IDR)</label><br>
    <input type="number" id="capitalInput" value="50000000" step="5000000" min="1000000">
  </div>
  <button class="btn btn-primary" id="runBtn" onclick="runBacktest()">Run</button>
  <span class="spinner" id="spinner">⏳ Running…</span>
</div>

<!-- METRICS CARDS -->
<div class="metrics" id="metricsRow" style="display:none">
  <div class="metric-card">
    <div class="label">Total Return</div>
    <div class="value" id="mReturn">—</div>
  </div>
  <div class="metric-card">
    <div class="label">Portfolio Sharpe</div>
    <div class="value" id="mSharpe">—</div>
  </div>
  <div class="metric-card">
    <div class="label">Max Drawdown</div>
    <div class="value" id="mDD">—</div>
  </div>
  <div class="metric-card">
    <div class="label">Tickers Used</div>
    <div class="value neu" id="mTickers">—</div>
  </div>
  <div class="notice hidden" id="skippedNotice"></div>
</div>

<!-- CHARTS GRID -->
<div class="charts-grid" id="chartsGrid" style="display:none">
  <div class="chart-panel">
    <div class="panel-title">Portfolio Equity</div>
    <div class="chart-box" id="chartPortfolio"></div>
  </div>
  <div class="chart-panel">
    <div class="panel-title">Per-Ticker Equity</div>
    <div class="chart-box" id="chartTickers"></div>
  </div>
  <div class="chart-panel">
    <div class="panel-title">Rolling 60-Day Sharpe</div>
    <div class="chart-box" id="chartSharpe"></div>
  </div>
  <div class="chart-panel">
    <div class="panel-title">Drawdown Waterfall</div>
    <div class="chart-box" id="chartDD"></div>
  </div>
</div>

<!-- CONCURRENT POSITIONS -->
<div class="conc-section hidden" id="concSection">
  <div class="conc-panel">
    <div class="panel-title">Concurrent Open Positions</div>
    <canvas id="concCanvas"></canvas>
  </div>
</div>

<!-- PER-TICKER TABLE -->
<div class="table-section hidden" id="tableSection">
  <div class="section-title">Per-Ticker Breakdown</div>
  <table id="tickerTable">
    <thead>
      <tr>
        <th onclick="sortTable(0)">Ticker</th>
        <th onclick="sortTable(1)">Allocation (IDR)</th>
        <th onclick="sortTable(2)">Return %</th>
        <th onclick="sortTable(3)">Sharpe</th>
        <th onclick="sortTable(4)">Max DD %</th>
        <th onclick="sortTable(5)">Trades</th>
        <th onclick="sortTable(6)">Win Rate %</th>
      </tr>
    </thead>
    <tbody id="tickerTbody"></tbody>
  </table>
</div>

<!-- CORRELATION HEATMAP -->
<div class="heatmap-section hidden" id="heatmapSection">
  <div class="section-title">Return Correlation Matrix</div>
  <div id="heatmapContainer"></div>
</div>

<script>
const TICKER_COLORS = [
  '#6366f1','#22c55e','#f59e0b','#ef4444','#06b6d4',
  '#ec4899','#8b5cf6','#14b8a6','#a78bfa','#f97316',
  '#84cc16','#e879f9','#fb923c','#34d399','#60a5fa',
];

let _charts = [];

function destroyCharts() {
  _charts.forEach(c => { try { c.remove(); } catch(_){} });
  _charts = [];
}

async function init() {
  await Promise.all([fetchSectors(), fetchStrategies()]);
}

async function fetchSectors() {
  const r = await fetch('/api/portfolio/sectors');
  const data = await r.json();
  const sel = document.getElementById('sectorSel');
  Object.keys(data.sectors).forEach(s => {
    const o = document.createElement('option');
    o.value = s; o.textContent = `${s} (${data.sectors[s].length})`;
    sel.appendChild(o);
  });
}

async function fetchStrategies() {
  const r = await fetch('/api/strategy/list');
  const data = await r.json();
  const sel = document.getElementById('strategySel');
  data.strategies.forEach(s => {
    const o = document.createElement('option');
    o.value = s.key; o.textContent = s.label;
    sel.appendChild(o);
  });
}

async function runBacktest() {
  const sector   = document.getElementById('sectorSel').value;
  const strategy = document.getElementById('strategySel').value;
  const capital  = parseFloat(document.getElementById('capitalInput').value);
  const btn      = document.getElementById('runBtn');
  const spinner  = document.getElementById('spinner');

  btn.disabled = true;
  spinner.style.display = 'inline';
  destroyCharts();

  try {
    const r = await fetch('/api/portfolio/backtest', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({sector, strategy, capital}),
    });
    const data = await r.json();
    if (!r.ok) { alert(data.error || 'Error'); return; }
    render(data);
  } catch(e) {
    alert('Network error: ' + e);
  } finally {
    btn.disabled = false;
    spinner.style.display = 'none';
  }
}

function render(data) {
  // Metrics
  const p = data.portfolio;
  document.getElementById('metricsRow').style.display = 'flex';
  const retEl = document.getElementById('mReturn');
  retEl.textContent = (p.total_return_pct >= 0 ? '+' : '') + p.total_return_pct.toFixed(2) + '%';
  retEl.className = 'value ' + (p.total_return_pct >= 0 ? 'pos' : 'neg');
  const shEl = document.getElementById('mSharpe');
  shEl.textContent = p.sharpe.toFixed(2);
  shEl.className = 'value ' + (p.sharpe >= 1 ? 'pos' : p.sharpe >= 0 ? 'neu' : 'neg');
  const ddEl = document.getElementById('mDD');
  ddEl.textContent = p.max_drawdown_pct.toFixed(2) + '%';
  ddEl.className = 'value neg';
  document.getElementById('mTickers').textContent = data.tickers_used.length;

  const notice = document.getElementById('skippedNotice');
  if (data.tickers_skipped.length > 0) {
    notice.textContent = `Skipped (< 60 bars): ${data.tickers_skipped.join(', ')}`;
    notice.classList.remove('hidden');
  } else {
    notice.classList.add('hidden');
  }

  // Charts
  document.getElementById('chartsGrid').style.display = 'grid';
  renderPortfolioEquity(p.equity_curve);
  renderTickerEquity(data.per_ticker);
  renderRollingSharpe(p.rolling_sharpe);
  renderDrawdown(data.per_ticker, p.drawdown_curve);

  // Concurrent positions
  document.getElementById('concSection').classList.remove('hidden');
  renderConcurrent(p.concurrent_positions);

  // Table
  document.getElementById('tableSection').classList.remove('hidden');
  renderTable(data.per_ticker);

  // Heatmap
  if (data.correlation.tickers.length > 1) {
    document.getElementById('heatmapSection').classList.remove('hidden');
    renderHeatmap(data.correlation);
  } else {
    document.getElementById('heatmapSection').classList.add('hidden');
  }
}

function makeChart(containerId) {
  const container = document.getElementById(containerId);
  const chart = LightweightCharts.createChart(container, {
    autoSize: true,
    layout:   { background: { color: '#0d0f18' }, textColor: '#4e5f7a' },
    grid:     { vertLines: { color: 'rgba(255,255,255,.04)' }, horzLines: { color: 'rgba(255,255,255,.04)' } },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
    timeScale: { borderColor: 'rgba(255,255,255,.07)' },
    rightPriceScale: { borderColor: 'rgba(255,255,255,.07)' },
  });
  _charts.push(chart);
  return chart;
}

function renderPortfolioEquity(equity_curve) {
  const chart = makeChart('chartPortfolio');
  const series = chart.addLineSeries({ color: '#6366f1', lineWidth: 2, priceLineVisible: false });
  series.setData(equity_curve.map(p => ({ time: p.date, value: p.value })));
  chart.timeScale().fitContent();
}

function renderTickerEquity(per_ticker) {
  const chart = makeChart('chartTickers');
  per_ticker.forEach((t, i) => {
    const series = chart.addLineSeries({
      color: TICKER_COLORS[i % TICKER_COLORS.length],
      lineWidth: 1.5, priceLineVisible: false, lastValueVisible: true,
      title: t.ticker,
    });
    series.setData(t.equity_curve.map(p => ({ time: p.date, value: p.value })));
  });
  chart.timeScale().fitContent();
}

function renderRollingSharpe(rolling_sharpe) {
  const chart = makeChart('chartSharpe');
  const series = chart.addLineSeries({ color: '#22c55e', lineWidth: 2, priceLineVisible: false });
  series.setData(rolling_sharpe.map(p => ({ time: p.date, value: p.sharpe })));
  // Zero reference line
  series.createPriceLine({ price: 0, color: 'rgba(255,255,255,.2)', lineWidth: 1,
    lineStyle: LightweightCharts.LineStyle.Dashed, axisLabelVisible: false });
  chart.timeScale().fitContent();
}

function renderDrawdown(per_ticker, portfolio_dd) {
  const chart = makeChart('chartDD');
  // Portfolio drawdown (bold)
  const portSeries = chart.addLineSeries({
    color: '#6366f1', lineWidth: 2, priceLineVisible: false, title: 'Portfolio',
  });
  portSeries.setData(portfolio_dd.map(p => ({ time: p.date, value: p.dd_pct })));
  // Per-ticker drawdowns (lighter)
  per_ticker.forEach((t, i) => {
    const series = chart.addLineSeries({
      color: TICKER_COLORS[i % TICKER_COLORS.length],
      lineWidth: 1, priceLineVisible: false, lastValueVisible: false, title: t.ticker,
    });
    series.setData(t.drawdown_curve.map(p => ({ time: p.date, value: p.dd_pct })));
  });
  chart.timeScale().fitContent();
}

function renderConcurrent(concurrent_positions) {
  const canvas = document.getElementById('concCanvas');
  const dpr = window.devicePixelRatio || 1;
  canvas.width  = canvas.offsetWidth * dpr;
  canvas.height = canvas.offsetHeight * dpr;
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);
  const W = canvas.offsetWidth, H = canvas.offsetHeight;

  const maxCount = Math.max(1, ...concurrent_positions.map(p => p.count));
  const n = concurrent_positions.length;
  if (n === 0) return;

  const barW = Math.max(1, W / n);
  concurrent_positions.forEach((p, i) => {
    const barH = (p.count / maxCount) * (H - 16);
    ctx.fillStyle = p.count > 0 ? '#6366f180' : 'transparent';
    ctx.fillRect(i * barW, H - 16 - barH, barW - 1, barH);
  });
  // Y label
  ctx.fillStyle = '#4e5f7a';
  ctx.font = '10px Inter';
  ctx.fillText(`max ${maxCount}`, 4, 12);
}

function renderTable(per_ticker) {
  const tbody = document.getElementById('tickerTbody');
  tbody.innerHTML = '';
  per_ticker.forEach(t => {
    const sign = t.total_return_pct >= 0 ? '+' : '';
    const cls  = t.total_return_pct >= 0 ? 'pos' : 'neg';
    tbody.innerHTML += `<tr>
      <td><strong>${t.ticker}</strong></td>
      <td>${Number(t.allocation).toLocaleString('id-ID')}</td>
      <td class="${cls}">${sign}${t.total_return_pct.toFixed(2)}%</td>
      <td class="${t.sharpe >= 1 ? 'pos' : t.sharpe >= 0 ? '' : 'neg'}">${t.sharpe.toFixed(2)}</td>
      <td class="neg">${t.max_drawdown_pct.toFixed(2)}%</td>
      <td>${t.total_trades}</td>
      <td>${t.win_rate.toFixed(1)}%</td>
    </tr>`;
  });
}

let _sortDir = 1;
function sortTable(colIdx) {
  _sortDir *= -1;
  const tbody = document.getElementById('tickerTbody');
  const rows  = Array.from(tbody.querySelectorAll('tr'));
  rows.sort((a, b) => {
    const av = a.cells[colIdx].textContent.replace(/[^0-9.\-+]/g, '');
    const bv = b.cells[colIdx].textContent.replace(/[^0-9.\-+]/g, '');
    const an = parseFloat(av), bn = parseFloat(bv);
    if (!isNaN(an) && !isNaN(bn)) return _sortDir * (an - bn);
    return _sortDir * av.localeCompare(bv);
  });
  rows.forEach(r => tbody.appendChild(r));
}

function renderHeatmap(correlation) {
  const { tickers, matrix } = correlation;
  let html = '<table class="heatmap"><thead><tr><th></th>';
  tickers.forEach(t => { html += `<th>${t}</th>`; });
  html += '</tr></thead><tbody>';
  matrix.forEach((row, i) => {
    html += `<tr><th>${tickers[i]}</th>`;
    row.forEach(v => {
      // Dark theme: high corr = red, zero = card bg, negative = blue
      let bg;
      if (v >= 0) {
        const r = Math.round(50 + v * 180), g = Math.round(30), b = Math.round(30);
        bg = `rgb(${r},${g},${b})`;
      } else {
        const r = Math.round(30), g = Math.round(30), b = Math.round(50 + (-v) * 180);
        bg = `rgb(${r},${g},${b})`;
      }
      const textCol = Math.abs(v) > 0.4 ? '#e8edf4' : '#4e5f7a';
      html += `<td style="background:${bg};color:${textCol}">${v.toFixed(2)}</td>`;
    });
    html += '</tr>';
  });
  html += '</tbody></table>';
  document.getElementById('heatmapContainer').innerHTML = html;
}

init();
</script>
</body>
</html>
```

- [ ] **Step 2: Verify the page loads in the browser**

```bash
curl -s http://localhost:5001/portfolio | grep -c "Portfolio Backtest"
```

Expected: `1` (the page title appears once)

- [ ] **Step 3: Smoke test the API**

```bash
curl -s -X POST http://localhost:5001/api/portfolio/backtest \
  -H "Content-Type: application/json" \
  -d '{"sector":"Telecom","strategy":"vol_weighted","capital":50000000}' \
  | python3 -m json.tool | head -20
```

Expected: JSON with `tickers_used`, `portfolio`, `per_ticker`, `correlation` keys (Telecom has only 6 tickers so it runs fast)

- [ ] **Step 4: Run full test suite**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && \
  /home/tjiesar/10\ Projects/idx-walkforward-5001/venv/bin/python -m pytest tests/ -q --tb=short \
  --ignore=tests/agent_firm --ignore=tests/test_scheduler_firm_hook.py \
  --ignore=tests/test_screener_stockbit_error.py
```

Expected: 106 passed

- [ ] **Step 5: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && \
  git add templates/portfolio.html && \
  git commit -m "feat(r6): add portfolio.html — equity charts, drawdown, rolling Sharpe, correlation heatmap"
```

---

## Task 5: Mark R6 complete in TODO.md

**Files:**
- Modify: `TODO.md`

- [ ] **Step 1: Update TODO.md**

Change:
```
- [ ] **R6. Portfolio-level backtesting** — Create `engine/portfolio_backtest.py` ...
```

To:
```
- [x] **R6. Portfolio-level backtesting** — `engine/portfolio_backtest.py` equal-split capital, equity merge, portfolio Sharpe/drawdown/rolling metrics, correlation matrix. `routes/portfolio.py` + `/portfolio` dashboard: 4 Lightweight Charts panels, concurrent-positions canvas, sortable per-ticker table, correlation heatmap. 9 unit tests. SHIPPED 2026-05-30.
```

- [ ] **Step 2: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && \
  git add TODO.md && \
  git commit -m "chore: mark R6 complete in TODO.md"
```

---

## Self-Review

### Spec coverage

| Spec requirement | Covered by |
|---|---|
| `engine/portfolio_backtest.py` with equal-split capital | Task 2 |
| Multi-ticker sequential execution | Task 2 (`for ticker in tickers`) |
| Combined equity curve (date intersection) | Task 2 (`sum(s.loc[common_dates]...)`) |
| Portfolio Sharpe/drawdown/rolling metrics | Task 2 (`_rolling_sharpe`, `_drawdown_curve`) |
| Correlation matrix | Task 2 (`_correlation_matrix`) |
| Concurrent positions | Task 2 (`_concurrent_positions`) |
| `GET /api/portfolio/sectors` | Task 3 |
| `POST /api/portfolio/backtest` with validation | Task 3 |
| `GET /portfolio` page route | Task 3 |
| 4 Lightweight Charts panels | Task 4 |
| Concurrent positions bar chart | Task 4 |
| Per-ticker sortable table | Task 4 |
| Correlation heatmap (hidden for 1 ticker) | Task 4 |
| Error handling: unknown sector/strategy, all skipped, capital ≤ 0 | Task 3 |
| 9 unit tests with mock `_load_ohlcv` | Task 1 |

### Placeholder scan

None found — all steps contain complete code.

### Type consistency

- `run_portfolio_backtest(tickers, strategy, capital, db_path)` — used identically in Task 2 (engine), Task 3 (route), and Task 1 (tests via mock) ✅
- `equity_curve` field: `list[{"date": str, "value": float}]` — used consistently in engine output and JS (`p.date`, `p.value`) ✅
- `drawdown_curve` field: `list[{"date": str, "dd_pct": float}]` — engine and JS both use `p.dd_pct` ✅
- `rolling_sharpe` field: `list[{"date": str, "sharpe": float}]` — engine and JS both use `p.sharpe` ✅
- `concurrent_positions` field: `list[{"date": str, "count": int}]` — engine and JS canvas renderer both use `p.count` ✅
