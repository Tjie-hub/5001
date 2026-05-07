# Dive Multi-Timeframe Chart Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace TradingView 1H and 1W tabs in `/dive/<ticker>` with a self-hosted lightweight-charts panel backed by a yfinance Flask endpoint with SQLite caching; 1D stays on TradingView.

**Architecture:** Backend adds an `ohlcv_cache` table to `walkforward.db` and a new Flask route `/api/ticker/<tk>/ohlcv?tf=` that checks cache (TTL 15 min for 1H, 24h for 1W) before fetching from yfinance. Frontend swaps between TradingView widget (1D) and lightweight-charts canvas (1H/1W) using two mutually exclusive divs.

**Tech Stack:** Python/Flask, yfinance, SQLite, lightweight-charts v4.2.0 (CDN)

---

## File Map

| File | Change |
|------|--------|
| `stockbit_fetcher.py` | Add `ohlcv_cache` DDL inside `init_flow_db()` before `conn.commit()` |
| `app.py` | Add `api_ohlcv_cache()` route after `api_ticker_full()` (line ~1720) |
| `templates/dive.html` | Add lightweight-charts CDN, dual chart divs, update `setTf()` + add `fetchAndRender()` |

---

## Task 1: Add `ohlcv_cache` table to `init_flow_db()`

**Files:**
- Modify: `stockbit_fetcher.py:589-590` (inside `init_flow_db`, before `conn.commit()`)

- [ ] **Step 1: Add DDL inside `init_flow_db()`**

In `stockbit_fetcher.py`, insert this block between the last `conn.execute("""...""")` block and the `conn.commit()` line (currently line 590):

```python
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ohlcv_cache (
            ticker      TEXT NOT NULL,
            tf          TEXT NOT NULL,
            fetched_at  REAL NOT NULL,
            data        TEXT NOT NULL,
            PRIMARY KEY (ticker, tf)
        )
    """)
```

- [ ] **Step 2: Verify table is created**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
python3 -c "
from stockbit_fetcher import init_flow_db
conn = init_flow_db()
rows = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name='ohlcv_cache'\").fetchall()
print('Table exists:', len(rows) == 1)
conn.close()
"
```
Expected output: `Table exists: True`

- [ ] **Step 3: Commit**

```bash
git add stockbit_fetcher.py
git commit -m "feat(ohlcv-cache): add ohlcv_cache table to init_flow_db"
```

---

## Task 2: Add `/api/ticker/<tk>/ohlcv` Flask endpoint

**Files:**
- Modify: `app.py` — insert new route after `api_ticker_full` function (around line 1720, after its closing brace)

- [ ] **Step 1: Add the route to `app.py`**

Find the end of `api_ticker_full()` in `app.py` and insert this complete function immediately after it:

```python
@app.route('/api/ticker/<ticker>/ohlcv', methods=['GET'])
def api_ohlcv_cache(ticker):
    import sqlite3, json, time
    import yfinance as yf

    ticker = ticker.upper()
    tf = request.args.get('tf', '1h').lower()
    if tf not in ('1h', '1w'):
        return jsonify({'error': 'tf must be 1h or 1w'}), 400

    ttl = 900 if tf == '1h' else 86400  # 15 min or 24h
    now = time.time()

    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        'SELECT fetched_at, data FROM ohlcv_cache WHERE ticker=? AND tf=?',
        (ticker, tf)
    ).fetchone()

    if row and (now - row[0]) < ttl:
        conn.close()
        return jsonify(json.loads(row[1]))

    # cache miss or expired — fetch from yfinance
    try:
        if tf == '1h':
            df = yf.Ticker(ticker + '.JK').history(period='60d', interval='1h', timeout=10)
        else:
            df = yf.Ticker(ticker + '.JK').history(period='2y', interval='1wk', timeout=10)
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 502

    if df is None or df.empty:
        conn.close()
        return jsonify({'error': f'No data for {ticker}'}), 404

    candles = []
    for ts, row_df in df.iterrows():
        t = int(ts.timestamp())
        candles.append({
            'time':   t,
            'open':   round(float(row_df['Open']),  2),
            'high':   round(float(row_df['High']),  2),
            'low':    round(float(row_df['Low']),   2),
            'close':  round(float(row_df['Close']), 2),
            'volume': int(row_df['Volume']),
        })

    payload = {'tf': tf, 'ticker': ticker, 'candles': candles}
    data_str = json.dumps(payload)

    conn.execute(
        'INSERT OR REPLACE INTO ohlcv_cache (ticker, tf, fetched_at, data) VALUES (?,?,?,?)',
        (ticker, tf, now, data_str)
    )
    conn.commit()
    conn.close()
    return jsonify(payload)
```

- [ ] **Step 2: Verify endpoint returns data**

Restart the Flask service, then:
```bash
curl -s "http://localhost:5001/api/ticker/BRPT/ohlcv?tf=1h" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('ticker:', d.get('ticker'))
print('candles:', len(d.get('candles', [])))
print('first:', d['candles'][0] if d.get('candles') else 'none')
"
```
Expected: `ticker: BRPT`, `candles: 24` (approx), and a valid first candle dict.

- [ ] **Step 3: Verify cache hit on second request**

```bash
curl -s "http://localhost:5001/api/ticker/BRPT/ohlcv?tf=1h" | python3 -c "
import sys, json; d = json.load(sys.stdin); print('ok, candles:', len(d.get('candles',[])))
"
```
Should return instantly (cached). Also verify in DB:
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('data/walkforward.db')
row = conn.execute('SELECT ticker, tf, fetched_at FROM ohlcv_cache').fetchall()
print(row)
"
```

- [ ] **Step 4: Test 1W endpoint**

```bash
curl -s "http://localhost:5001/api/ticker/BBCA/ohlcv?tf=1w" | python3 -c "
import sys, json; d = json.load(sys.stdin); print('candles:', len(d.get('candles',[])))
"
```
Expected: ~100 candles (2 years of weekly).

- [ ] **Step 5: Commit**

```bash
git add app.py
git commit -m "feat(ohlcv-cache): add /api/ticker/<tk>/ohlcv endpoint with SQLite cache"
```

---

## Task 3: Update `dive.html` frontend

**Files:**
- Modify: `templates/dive.html`

- [ ] **Step 1: Add lightweight-charts CDN to `<head>`**

In `templates/dive.html`, add this line inside `<head>` after the Google Fonts `<link>` tags (before `<style>`):

```html
<script src="https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
```

- [ ] **Step 2: Replace chart section with dual-div layout**

Find this existing block in `dive.html`:
```html
<div class="chart-wrap"><div id="tv_chart"></div></div>
```

Replace it with:
```html
<div id="tv_chart_wrap" class="chart-wrap"><div id="tv_chart"></div></div>
<div id="lw_chart_wrap" class="chart-wrap" style="display:none;position:relative;">
  <div id="lw_loading" style="display:none;position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:var(--mute);font-size:13px;background:var(--bg);z-index:2;">Loading…</div>
  <div id="lw_chart" style="width:100%;height:100%;"></div>
</div>
```

- [ ] **Step 3: Replace the JavaScript chart section**

Find this block in `dive.html`:
```javascript
  let _currentTf = 'D';

  function buildWidget(interval) {
    document.getElementById('tv_chart').innerHTML = '';
    new TradingView.widget({
      symbol: 'IDX:' + TICKER, interval: interval, timezone: 'Asia/Jakarta',
      theme: 'dark', style: '1', locale: 'id', autosize: true,
      studies: ['MASimple@tv-basicstudies', 'Volume@tv-basicstudies', 'BB@tv-basicstudies'],
      container_id: 'tv_chart', hide_side_toolbar: false,
      allow_symbol_change: true, save_image: false,
    });
  }

  function setTf(interval) {
    if (interval === _currentTf) return;
    _currentTf = interval;
    const map = { '60': 'tf-1h', 'D': 'tf-1d', 'W': 'tf-1w' };
    ['tf-1h', 'tf-1d', 'tf-1w'].forEach(id => {
      document.getElementById(id).classList.toggle('active', id === map[interval]);
    });
    buildWidget(interval);
  }

  buildWidget('D');
```

Replace with:
```javascript
  let _currentTf = 'D';
  let _lwChart = null;

  function buildWidget() {
    document.getElementById('tv_chart').innerHTML = '';
    new TradingView.widget({
      symbol: 'IDX:' + TICKER, interval: 'D', timezone: 'Asia/Jakarta',
      theme: 'dark', style: '1', locale: 'id', autosize: true,
      studies: ['MASimple@tv-basicstudies', 'Volume@tv-basicstudies', 'BB@tv-basicstudies'],
      container_id: 'tv_chart', hide_side_toolbar: false,
      allow_symbol_change: true, save_image: false,
    });
  }

  function setTf(interval) {
    if (interval === _currentTf) return;
    _currentTf = interval;
    const map = { '60': 'tf-1h', 'D': 'tf-1d', 'W': 'tf-1w' };
    ['tf-1h', 'tf-1d', 'tf-1w'].forEach(id => {
      document.getElementById(id).classList.toggle('active', id === map[interval]);
    });
    if (interval === 'D') {
      document.getElementById('lw_chart_wrap').style.display = 'none';
      document.getElementById('tv_chart_wrap').style.display = '';
      buildWidget();
    } else {
      document.getElementById('tv_chart_wrap').style.display = 'none';
      document.getElementById('lw_chart_wrap').style.display = '';
      fetchAndRender(interval === '60' ? '1h' : '1w');
    }
  }

  async function fetchAndRender(tf) {
    const loading = document.getElementById('lw_loading');
    const container = document.getElementById('lw_chart');
    loading.style.display = 'flex';
    container.innerHTML = '';
    if (_lwChart) { _lwChart.remove(); _lwChart = null; }

    let data;
    try {
      const r = await fetch('/api/ticker/' + TICKER + '/ohlcv?tf=' + tf);
      data = await r.json();
    } catch(e) {
      loading.style.display = 'none';
      container.innerHTML = '<div style="color:var(--mute);padding:20px;text-align:center">Network error</div>';
      return;
    }
    if (data.error) {
      loading.style.display = 'none';
      container.innerHTML = '<div style="color:var(--mute);padding:20px;text-align:center">' + data.error + '</div>';
      return;
    }

    loading.style.display = 'none';
    _lwChart = LightweightCharts.createChart(container, {
      autoSize: true,
      layout: { background: { color: '#0d0f14' }, textColor: '#e2e8f0' },
      grid: { vertLines: { color: '#1e2330' }, horzLines: { color: '#1e2330' } },
      crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
      timeScale: { borderColor: '#1e2330', timeVisible: true, secondsVisible: false },
      rightPriceScale: { borderColor: '#1e2330' },
    });

    const candles = _lwChart.addCandlestickSeries({
      upColor: '#22c55e', downColor: '#ef4444',
      borderUpColor: '#22c55e', borderDownColor: '#ef4444',
      wickUpColor: '#22c55e', wickDownColor: '#ef4444',
    });

    const volPane = _lwChart.addHistogramSeries({
      color: '#26a69a',
      priceFormat: { type: 'volume' },
      priceScaleId: 'vol',
    });
    _lwChart.priceScale('vol').applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });

    const candleData = data.candles.map(c => ({
      time: c.time, open: c.open, high: c.high, low: c.low, close: c.close
    }));
    const volData = data.candles.map(c => ({
      time: c.time,
      value: c.volume,
      color: c.close >= c.open ? 'rgba(34,197,94,0.4)' : 'rgba(239,68,68,0.4)',
    }));

    candles.setData(candleData);
    volPane.setData(volData);
    _lwChart.timeScale().fitContent();
  }

  buildWidget();
```

- [ ] **Step 4: Verify in browser**

Open `http://localhost:5001/dive/BRPT` (or server IP).
- 1D button → TradingView chart loads (same as before)
- 1H button → lightweight-charts candlestick loads with volume bars
- 1W button → lightweight-charts weekly candles load
- Switching back to 1D → TradingView re-renders correctly

- [ ] **Step 5: Commit**

```bash
git add templates/dive.html
git commit -m "feat(dive): add lightweight-charts for 1H/1W; 1D stays on TradingView"
```

---

## Self-Review

**Spec coverage:**
- ✅ `ohlcv_cache` table DDL → Task 1
- ✅ Flask endpoint with TTL cache → Task 2
- ✅ yfinance params (60d/1h, 2y/1wk) → Task 2 Step 1
- ✅ Response shape `{candles: [{time,open,high,low,close,volume}]}` → Task 2 Step 1
- ✅ 502 on yfinance error, 404 on empty → Task 2 Step 1
- ✅ lightweight-charts CDN → Task 3 Step 1
- ✅ Dual div toggle (tv_chart_wrap / lw_chart_wrap) → Task 3 Step 2
- ✅ Dark theme colors matching CSS vars → Task 3 Step 3
- ✅ Candlestick + volume panels → Task 3 Step 3
- ✅ Loading spinner → Task 3 Step 3
- ✅ Error handling in frontend → Task 3 Step 3
- ✅ Chart destroyed on each switch (no stale state) → Task 3 Step 3
