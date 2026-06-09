# REVERSAL_BREAKOUT Pattern — Implementation Plan

> ✅ SHIPPED 2026-05-18 — implemented in `engine/premover_detector.py`.

**Goal:** Add REVERSAL_BREAKOUT pattern detection to the premover detector so stocks exploding from a low base with unusual volume are caught early (e.g., ASPR at ~200 instead of ~450).

**Architecture:** A new `score_ticker_reversal()` function in `premover_detector.py` runs alongside the existing `score_ticker()` in `run_scan()`. Both pattern types share the `watchlist_premover` table via a `pattern_type` discriminator column. Alerts group results by pattern type.

**Tech Stack:** Python 3, pandas, numpy, sqlite3

---

### Task 1: Table migration — add pattern_type column

**Files:**
- Modify: `engine/premover_detector.py:29-49`

- [x] **Step 1: Read the current `_init_table()` function**

```python
def _init_table(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS watchlist_premover (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker       TEXT    NOT NULL,
            detected_at  TEXT    NOT NULL,
            score        INTEGER NOT NULL,
            reasons_json TEXT,
            above_ma50   INTEGER,
            adx          REAL,
            near_52w     INTEGER,
            atr_ratio    REAL,
            vol_dryup    REAL,
            rs           REAL,
            close_price  REAL,
            fired        INTEGER DEFAULT 0,
            fired_at     TEXT,
            UNIQUE(ticker, detected_at)
        )
    """)
    conn.commit()
```

- [x] **Step 2: Replace `_init_table()` to add migration logic**

Replace the entire function. The new version creates the table with new columns, then runs ALTER TABLE migrations for existing tables:

```python
def _init_table(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS watchlist_premover (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker       TEXT    NOT NULL,
            detected_at  TEXT    NOT NULL,
            pattern_type TEXT    NOT NULL DEFAULT 'CONTINUATION',
            score        INTEGER NOT NULL,
            reasons_json TEXT,
            above_ma50   INTEGER,
            adx          REAL,
            near_52w     INTEGER,
            near_low     INTEGER,
            above_3ma    INTEGER,
            green_day    INTEGER,
            atr_ratio    REAL,
            vol_ratio    REAL,
            vol_dryup    REAL,
            rs           REAL,
            close_price  REAL,
            fired        INTEGER DEFAULT 0,
            fired_at     TEXT,
            UNIQUE(ticker, detected_at, pattern_type)
        )
    """)

    # Migration: add columns for existing tables (idempotent via IF NOT EXISTS error swallow)
    existing_cols = {r[1] for r in conn.execute('PRAGMA table_info(watchlist_premover)').fetchall()}
    for col, col_def in [
        ('pattern_type', 'TEXT NOT NULL DEFAULT \'CONTINUATION\''),
        ('near_low', 'INTEGER'),
        ('above_3ma', 'INTEGER'),
        ('green_day', 'INTEGER'),
        ('vol_ratio', 'REAL'),
    ]:
        if col not in existing_cols:
            try:
                conn.execute(f'ALTER TABLE watchlist_premover ADD COLUMN {col} {col_def}')
            except Exception:
                pass

    # Migration: drop old UNIQUE index, create new composite one
    try:
        conn.execute('DROP INDEX IF EXISTS sqlite_autoindex_watchlist_premover_1')
    except Exception:
        pass
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_premover_unique
        ON watchlist_premover(ticker, detected_at, pattern_type)
    """)
    conn.commit()
```

- [x] **Step 3: Add constant for reversal threshold**

After `ALERT_THRESHOLD = 50` on line 26, add:

```python
ALERT_THRESHOLD = 50
REVERSAL_THRESHOLD = 45  # REVERSAL_BREAKOUT pattern — lower threshold for earlier catch
```

---

### Task 2: Implement `score_ticker_reversal()` function

**Files:**
- Modify: `engine/premover_detector.py` (insert after `score_ticker()` function, which ends around line 164)

- [x] **Step 1: Add the new scoring function**

Insert the new function between `score_ticker()` and `run_scan()`. Here's the complete function:

```python
def score_ticker_reversal(df: pd.DataFrame, flow_score: float = None) -> dict:
    """
    Score ticker for REVERSAL_BREAKOUT pattern.
    
    Detects stocks reversing from a low/support base with explosive volume.
    Catches moves BEFORE the uptrend is established (opposite of CONTINUATION).
    
    Scoring (sum=100, threshold=45):
      30 pts  VOLUME_EXPLOSION   — vol > 2x 20d median
      20 pts  PRICE_NEAR_LOW     — close within 20% of 50d low
      20 pts  BREAKING_SHORT_TREND — close > 3d SMA
      15 pts  POSITIVE_CLOSE     — close > prev close (green)
      10 pts  ATR_EXPANSION      — ATR14 >= ATR30 median (vol not contracting)
       5 pts  FLOW_CONFIRMATION  — stockbit composite > 0
    
    Returns dict with score, reasons, and individual indicator values.
    Returns score=0 with reasons=['insufficient_data'] if df too short.
    """
    MIN_BARS = 50
    MEDIAN_VOL_FLOOR = 100_000

    if len(df) < MIN_BARS:
        return {'score': 0, 'reasons': ['insufficient_data'],
                'vol_ratio': None, 'near_low': 0, 'above_3ma': 0,
                'green_day': 0, 'atr_ratio': None, 'close': None}

    close  = df['close'].astype(float)
    high   = df['high'].astype(float)
    low    = df['low'].astype(float)
    volume = df['volume'].astype(float)
    j = len(df) - 1

    atr14   = _calc_atr(df, 14)
    atr_med = atr14.rolling(30, min_periods=15).median()
    low_50d = close.rolling(50, min_periods=20).min()
    vol_med_20 = volume.rolling(20, min_periods=5).median()
    ma3 = close.rolling(3, min_periods=2).mean()

    def _f(s, i=j):
        v = s.iloc[i]
        return float(v) if not pd.isna(v) else float('nan')

    cl_j      = _f(close)
    vol_j     = _f(volume)
    atr_j     = _f(atr14)
    atr_m_j   = _f(atr_med)
    low50_j   = _f(low_50d)
    vol_m_j   = _f(vol_med_20)
    ma3_j     = _f(ma3)

    # ── Indicators ──────────────────────────────────────────────────────────

    # 1) VOLUME_EXPLOSION (30 pts): vol > 2x 20d median
    vol_ratio = (vol_j / vol_m_j) if vol_m_j > MEDIAN_VOL_FLOOR else 0.0
    vol_spike = int(vol_ratio > 2.0)

    # 2) PRICE_NEAR_LOW (20 pts): within 20% of 50d low
    near_low = 0
    if low50_j > 0 and not pd.isna(low50_j) and cl_j > 0:
        pct_from_low = (cl_j - low50_j) / low50_j
        near_low = int(pct_from_low <= 0.20)

    # 3) BREAKING_SHORT_TREND (20 pts): close > 3d SMA
    above_3ma = int(not pd.isna(ma3_j) and cl_j > ma3_j)

    # 4) POSITIVE_CLOSE (15 pts): close > prev close
    prev_close = float(close.iloc[j - 1]) if j >= 1 else float('nan')
    green_day = int(not pd.isna(prev_close) and cl_j > prev_close)

    # 5) ATR_EXPANSION (10 pts): ATR14 >= ATR30 median
    atr_ratio = (atr_j / atr_m_j) if atr_m_j > 0 and not pd.isna(atr_j) else float('nan')
    atr_ok = int(not pd.isna(atr_ratio) and atr_ratio >= 1.0)

    # 6) FLOW_CONFIRMATION (5 pts): stockbit composite > 0
    flow_pos = int(flow_score is not None and flow_score > 0)

    # ── Scoring ─────────────────────────────────────────────────────────────
    score = 0
    reasons = []

    if vol_spike:
        score += 30
        reasons.append(f'VOLUME_EXPLOSION({vol_ratio:.1f}x)')
    if near_low:
        score += 20
        reasons.append('PRICE_NEAR_LOW')
    if above_3ma:
        score += 20
        reasons.append('BREAKING_SHORT_TREND')
    if green_day:
        score += 15
        reasons.append('POSITIVE_CLOSE')
    if atr_ok:
        score += 10
        reasons.append(f'ATR_EXPANSION({atr_ratio:.2f})')
    if flow_pos:
        score += 5
        reasons.append('FLOW_CONFIRMATION')

    return {
        'score':     min(score, 100),
        'reasons':   reasons,
        'vol_ratio': round(vol_ratio, 1) if not pd.isna(vol_ratio) else None,
        'near_low':  near_low,
        'above_3ma': above_3ma,
        'green_day': green_day,
        'atr_ratio': round(atr_ratio, 3) if not pd.isna(atr_ratio) else None,
        'close':     cl_j,
    }
```

- [x] **Step 2: Verify function syntax**

Run: `python3 -c "import ast; ast.parse(open('engine/premover_detector.py').read()); print('OK')"`
Expected: `OK`

---

### Task 3: Add helper for inserting reversal setups

**Files:**
- Modify: `engine/premover_detector.py` (insert helper before `run_scan()`)

- [x] **Step 1: Add insert helper function**

Insert before `run_scan()` (around line 167):

```python
def _upsert_setup(conn: sqlite3.Connection, ticker: str, detected_at: str,
                  pattern_type: str, result: dict) -> bool:
    """Insert or ignore a setup into watchlist_premover. Returns True if new."""
    if pattern_type == 'CONTINUATION':
        conn.execute("""
            INSERT OR IGNORE INTO watchlist_premover
            (ticker, detected_at, pattern_type, score, reasons_json,
             above_ma50, adx, near_52w, atr_ratio, vol_dryup, rs, close_price)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            ticker, detected_at, pattern_type, result['score'],
            json.dumps(result.get('reasons', [])),
            result.get('above_ma50'), result.get('adx'),
            result.get('near_52w'),   result.get('atr_ratio'),
            result.get('vol_dryup'),  result.get('rs'),
            result.get('close'),
        ))
    elif pattern_type == 'REVERSAL_BREAKOUT':
        conn.execute("""
            INSERT OR IGNORE INTO watchlist_premover
            (ticker, detected_at, pattern_type, score, reasons_json,
             near_low, above_3ma, green_day, atr_ratio, vol_ratio, close_price)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            ticker, detected_at, pattern_type, result['score'],
            json.dumps(result.get('reasons', [])),
            result.get('near_low'), result.get('above_3ma'),
            result.get('green_day'), result.get('atr_ratio'),
            result.get('vol_ratio'), result.get('close'),
        ))
    return conn.execute('SELECT changes()').fetchone()[0] > 0
```

- [x] **Step 2: Verify syntax**

Run: `python3 -c "import ast; ast.parse(open('engine/premover_detector.py').read()); print('OK')"`
Expected: `OK`

---

### Task 4: Update `run_scan()` for dual-pattern scoring

**Files:**
- Modify: `engine/premover_detector.py` (the `run_scan()` function starting around line 167)

- [x] **Step 1: Replace `run_scan()` with dual-pattern version**

Replace `run_scan()` entirely:

```python
def run_scan(db_path: str, send_alert_fn=None) -> list:
    """
    Scan all tickers EOD, store qualifying setups in watchlist_premover.
    Runs both CONTINUATION and REVERSAL_BREAKOUT patterns.

    Returns list of NEW setups inserted this run (not previously seen today).
    """
    conn = sqlite3.connect(db_path)
    _init_table(conn)

    detected_at = datetime.now().strftime('%Y-%m-%d')

    all_df = pd.read_sql('SELECT * FROM ohlcv ORDER BY ticker, date ASC', conn)
    for c in ['open', 'high', 'low', 'close', 'volume']:
        all_df[c] = all_df[c].astype(float)
    ohlcv_map = {t: g.reset_index(drop=True) for t, g in all_df.groupby('ticker')}
    ihsg_df = ohlcv_map.get('IHSG')

    flow_map = {}
    try:
        rows = conn.execute("""
            SELECT ticker, composite_score FROM stockbit_flow
            WHERE trade_date = (SELECT MAX(trade_date) FROM stockbit_flow)
        """).fetchall()
        flow_map = {r[0]: r[1] for r in rows if r[1] is not None}
    except Exception:
        pass

    new_setups = []

    for ticker, df in ohlcv_map.items():
        if ticker == 'IHSG' or len(df) < 60:
            continue

        # ── CONTINUATION pattern ────────────────────────────────────────────
        try:
            result = score_ticker(df, ihsg_df=ihsg_df, flow_score=flow_map.get(ticker))
            if result['score'] >= ALERT_THRESHOLD:
                if _upsert_setup(conn, ticker, detected_at, 'CONTINUATION', result):
                    new_setups.append({'ticker': ticker, 'pattern': 'CONTINUATION', **result})
        except Exception as e:
            print(f"[premover] {ticker} CONTINUATION error: {e}")

        # ── REVERSAL_BREAKOUT pattern ───────────────────────────────────────
        try:
            result = score_ticker_reversal(df, flow_score=flow_map.get(ticker))
            if result['score'] >= REVERSAL_THRESHOLD:
                if _upsert_setup(conn, ticker, detected_at, 'REVERSAL_BREAKOUT', result):
                    new_setups.append({'ticker': ticker, 'pattern': 'REVERSAL_BREAKOUT', **result})
        except Exception as e:
            print(f"[premover] {ticker} REVERSAL error: {e}")

    conn.commit()
    conn.close()

    # ── Alert ───────────────────────────────────────────────────────────────
    if new_setups and send_alert_fn:
        reversal = [s for s in new_setups if s['pattern'] == 'REVERSAL_BREAKOUT']
        cont     = [s for s in new_setups if s['pattern'] == 'CONTINUATION']

        msg = f"🔍 <b>Pre-Breakout Setups — {detected_at}</b>\n\n"

        if reversal:
            msg += f"── REVERSAL_BREAKOUT ({len(reversal)}) ──\n"
            for s in sorted(reversal, key=lambda x: x['score'], reverse=True)[:5]:
                msg += f"<b>{s['ticker']}</b> — Score {s['score']}/100\n"
                msg += f"  {' · '.join(s.get('reasons', []))}\n"
                msg += f"  Close: {s.get('close', 0):,.0f}\n\n"

        if cont:
            msg += f"── CONTINUATION ({len(cont)}) ──\n"
            for s in sorted(cont, key=lambda x: x['score'], reverse=True)[:5]:
                msg += f"<b>{s['ticker']}</b> — Score {s['score']}/100\n"
                msg += f"  {' · '.join(s.get('reasons', []))}\n"
                msg += f"  Close: {s.get('close', 0):,.0f}\n\n"

        total = len(new_setups)
        if total > 10:
            msg += f"... +{total - 10} more\n\n"
        msg += f"Total: {total} new setups"
        try:
            send_alert_fn(msg)
        except Exception as e:
            print(f"[premover] Telegram alert error: {e}")

    return new_setups
```

- [x] **Step 2: Verify syntax**

Run: `python3 -c "import ast; ast.parse(open('engine/premover_detector.py').read()); print('OK')"`
Expected: `OK`

---

### Task 5: Update `get_watchlist()` to support pattern_type filter

**Files:**
- Modify: `engine/premover_detector.py` (the `get_watchlist()` function starting around line 243)

- [x] **Step 1: Update `get_watchlist()` with pattern_type filter**

Replace the function:

```python
def get_watchlist(db_path: str, min_score: int = ALERT_THRESHOLD,
                  days: int = 5, fired: bool = False,
                  pattern_type: str = None) -> list:
    """Return active watchlist entries from the last N days."""
    conn = sqlite3.connect(db_path)
    _init_table(conn)
    try:
        clauses = ['score >= ?', 'fired = ?',
                   "detected_at >= date('now', ? || ' days')"]
        params = [min_score, int(fired), f'-{int(days)}']

        if pattern_type:
            clauses.append('pattern_type = ?')
            params.append(pattern_type)

        where = ' AND '.join(clauses)
        rows = conn.execute(f"""
            SELECT ticker, detected_at, pattern_type, score, reasons_json,
                   above_ma50, adx, near_52w, near_low, above_3ma, green_day,
                   atr_ratio, vol_ratio, vol_dryup, rs, close_price,
                   fired, fired_at
            FROM watchlist_premover
            WHERE {where}
            ORDER BY score DESC, detected_at DESC
        """, params).fetchall()
        return [
            {
                'ticker':        r[0],
                'detected_at':   r[1],
                'pattern_type':  r[2],
                'score':         r[3],
                'reasons':       json.loads(r[4]) if r[4] else [],
                'above_ma50':    r[5], 'adx': r[6], 'near_52w': r[7],
                'near_low':      r[8], 'above_3ma': r[9], 'green_day': r[10],
                'atr_ratio':     r[11], 'vol_ratio': r[12], 'vol_dryup': r[13],
                'rs':            r[14],
                'close_price':   r[15],
                'fired':         bool(r[16]),
                'fired_at':      r[17],
            }
            for r in rows
        ]
    finally:
        conn.close()
```

---

### Task 6: Update `app.py` live score endpoint to show both patterns

**Files:**
- Modify: `app.py:1742-1765`

- [x] **Step 1: Add reversal scoring alongside existing score_ticker call**

Replace the premover scoring block (lines 1742-1765) to include both patterns:

```python
    # ── PRE-MOVER SCORE (live, not cached) ────────────────────────────────
    from engine.premover_detector import score_ticker as _score_ticker
    from engine.premover_detector import score_ticker_reversal as _score_reversal
    import sqlite3 as _sq3
    _flow_conn = _sq3.connect(DB_PATH)
    try:
        _frow = _flow_conn.execute("""
            SELECT composite_score FROM stockbit_flow
            WHERE ticker=? ORDER BY trade_date DESC LIMIT 1
        """, (ticker,)).fetchone()
    except Exception:
        _frow = None
    finally:
        _flow_conn.close()
    _ihsg_conn = _sq3.connect(DB_PATH)
    try:
        _ihsg_df = pd.read_sql(
            'SELECT * FROM ohlcv WHERE ticker=? ORDER BY date ASC',
            _ihsg_conn, params=('IHSG',)
        )
    except Exception:
        _ihsg_df = None
    finally:
        _ihsg_conn.close()
    _pm = _score_ticker(df, ihsg_df=_ihsg_df if (_ihsg_df is not None and not _ihsg_df.empty) else None,
                        flow_score=_frow[0] if _frow else None)
    _pm_rev = _score_reversal(df, flow_score=_frow[0] if _frow else None)
```

Then add `'premover_reversal': _pm_rev` to the returned JSON dict (somewhere in the jsonify call that returns around line 1767). The existing `'premover'` key stays as-is.

---

### Task 7: Update `app.py` API watchlist endpoint to support pattern_type param

**Files:**
- Modify: `app.py:1875-1881`

- [x] **Step 1: Add pattern_type query param to the watchlist API**

Replace the function:

```python
@app.route('/api/premover/watchlist', methods=['GET'])
def api_premover_watchlist():
    from engine.premover_detector import get_watchlist
    min_score    = int(request.args.get('min_score', 50))
    days         = int(request.args.get('days', 5))
    pattern_type = request.args.get('pattern_type', None)
    items = get_watchlist(DB_PATH, min_score=min_score, days=days,
                          pattern_type=pattern_type)
    return jsonify({'count': len(items), 'watchlist': items})
```

---

### Task 8: Backtest validation — verify ASPR triggers REVERSAL_BREAKOUT

**Files:**
- None (one-shot validation script)

- [x] **Step 1: Write and run a validation script**

```bash
cd /home/tjiesar/idx-walkforward-5001
python3 << 'PYEOF'
import sqlite3
import pandas as pd
from engine.premover_detector import score_ticker_reversal, REVERSAL_THRESHOLD

db = sqlite3.connect('data/walkforward.db')

# Fetch ASPR and IHSG OHLCV
aspr = pd.read_sql("SELECT * FROM ohlcv WHERE ticker='ASPR' ORDER BY date ASC", db)
ihsg = pd.read_sql("SELECT * FROM ohlcv WHERE ticker='IHSG' ORDER BY date ASC", db)

# Check flow score on key dates
flow = db.execute("""
    SELECT trade_date, composite_score FROM stockbit_flow
    WHERE ticker='ASPR' ORDER BY trade_date ASC
""").fetchall()
flow_map = {r[0]: r[1] for r in flow}

db.close()

for c in ['open','high','low','close','volume']:
    aspr[c] = aspr[c].astype(float)

# Score every day from April 20
target_dates = [
    ('2026-04-22', 199),
    ('2026-04-24', 202),
    ('2026-04-27', 212),
    ('2026-04-28', 230),
    ('2026-04-29', 256),
    ('2026-05-06', 452),  # when CONTINUATION caught it
]

print("ASPR — REVERSAL_BREAKOUT backtest")
print(f"{'Date':<14} {'Price':<8} {'Score':<8} {'Threshold':<10} {'Caught?':<10} Reasons")
print("-" * 80)

for target_date_str, expected_close in target_dates:
    mask = aspr['date'] <= target_date_str
    sub_df = aspr[mask].copy().reset_index(drop=True)
    if len(sub_df) < 50:
        print(f"{target_date_str:<14} {expected_close:<8} SKIP (insufficient data)")
        continue

    fs = flow_map.get(target_date_str)
    result = score_ticker_reversal(sub_df, flow_score=fs)
    
    caught = result['score'] >= REVERSAL_THRESHOLD
    reasons = ' · '.join(result.get('reasons', []))[:50]
    
    print(f"{target_date_str:<14} {expected_close:<8} {result['score']:<8} {REVERSAL_THRESHOLD:<10} {'✅' if caught else '❌':<10} {reasons}")

print()
print(f"Threshold: {REVERSAL_THRESHOLD}")
PYEOF
```

Expected output: ASPR triggers REVERSAL_BREAKOUT on April 24 (score >= 45) or no later than April 27.

- [x] **Step 2: Run the full scan live (EOD)**

```bash
cd /home/tjiesar/idx-walkforward-5001
python3 -c "
from engine.premover_detector import run_scan
new = run_scan('data/walkforward.db')
print(f'New setups: {len(new)}')
for s in new:
    print(f\"  {s['pattern']:20s} {s['ticker']:<8} Score {s['score']}/100\")
"
```

Expected: No errors. Shows REVERSAL_BREAKOUT and CONTINUATION setups.

---

### Task 9: Commit

**Files:**
- `engine/premover_detector.py`
- `app.py`
- `docs/reversal-breakout-pattern-design.md`
- `PLAN/reversal-breakout-implementation.md`

- [x] **Step 1: Review diff and commit**

```bash
cd /home/tjiesar/idx-walkforward-5001
git add engine/premover_detector.py app.py docs/reversal-breakout-pattern-design.md PLAN/reversal-breakout-implementation.md
git commit -m "feat: add REVERSAL_BREAKOUT pattern to premover detector

Catch stocks exploding from a low base with unusual volume — the blind
spot the existing CONTINUATION pattern misses.

- New score_ticker_reversal() function with 6-factor scoring
- Dual-pattern run_scan() scoring + grouped alerts
- Table migration: pattern_type discriminator column
- API: pattern_type filter on watchlist endpoint
- Live quote endpoint shows both pattern scores

Design: docs/reversal-breakout-pattern-design.md
Plan: PLAN/reversal-breakout-implementation.md"
```
