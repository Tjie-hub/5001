"""
premover_detector.py — Pre-Breakout Detector for IDX universe.

Scores tickers on setup quality BEFORE a potential +5% move,
calibrated against empirical IDX fast-mover data (Phase 5 study):
  CONTINUATION 44% | RANDOM 40% | NEWS_SPIKE 9% | RANGE_BREAK 6% | VCP 0.3%

Scoring weights (sum = 100):
  35 pts  above_ma50 AND adx >= 22  — CONTINUATION (dominant IDX pattern)
  20 pts  near_52w_high             — within 8% of 52-week high
  15 pts  atr_contracted            — ATR < 85% of its 60-bar median
  15 pts  volume_dry_up             — 5-day vol < 80% of 20-day avg
  10 pts  rs_vs_ihsg_pos            — 20-bar RS > 1.0 vs IHSG
   5 pts  foreign_net_pos           — stockbit composite_score > 0

Alert threshold: score >= 50 (at minimum CONTINUATION + one more check).
"""

import sqlite3
import json
import pandas as pd
import numpy as np
from datetime import datetime

from engine.indicators import classify_volume_context


ALERT_THRESHOLD = 50
REVERSAL_THRESHOLD = 45  # REVERSAL_BREAKOUT pattern — lower threshold for earlier catch


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

    # Migration: add columns for existing tables (idempotent)
    existing_cols = {r[1] for r in conn.execute('PRAGMA table_info(watchlist_premover)').fetchall()}
    for col, col_def in [
        ('pattern_type', "TEXT NOT NULL DEFAULT 'CONTINUATION'"),
        ('near_low', 'INTEGER'),
        ('above_3ma', 'INTEGER'),
        ('green_day', 'INTEGER'),
        ('vol_ratio', 'REAL'),
        ('vol_context', 'TEXT'),
    ]:
        if col not in existing_cols:
            try:
                assert col.replace('_', '').isalnum(), f"unsafe column: {col}"
                conn.execute(f'ALTER TABLE watchlist_premover ADD COLUMN {col} {col_def}')
            except Exception:
                pass

    # Migration: ensure composite unique index
    try:
        conn.execute('DROP INDEX IF EXISTS sqlite_autoindex_watchlist_premover_1')
    except Exception:
        pass
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_premover_unique
        ON watchlist_premover(ticker, detected_at, pattern_type)
    """)

    # pattern_metrics: join of alerts to the first paper trade opened within
    # 10 days of the alert. Always-fresh; no sync drift vs a materialized table.
    conn.execute('DROP VIEW IF EXISTS pattern_metrics')
    conn.execute("""
        CREATE VIEW pattern_metrics AS
        SELECT
            w.id           AS alert_id,
            w.ticker,
            w.pattern_type,
            w.detected_at  AS alerted_at,
            w.score,
            w.fired,
            w.fired_at,
            p.id           AS trade_id,
            p.entry_date,
            p.entry_price,
            p.exit_date,
            p.exit_price,
            p.status       AS trade_status,
            p.pnl_pct,
            p.exit_reason
        FROM watchlist_premover w
        LEFT JOIN paper_trades p ON p.id = (
            SELECT id FROM paper_trades
            WHERE ticker = w.ticker
              AND entry_date >= w.detected_at
              AND entry_date <= date(w.detected_at, '+10 days')
            ORDER BY entry_date ASC LIMIT 1
        )
    """)
    conn.commit()


def _calc_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    # SMA-ATR matches strategies.py convention. Wilder's EWM is only used in regime_filter.py for ADX.
    hi, lo, cl = df['high'], df['low'], df['close']
    prev_cl = cl.shift(1)
    tr = pd.concat([hi - lo, (hi - prev_cl).abs(), (lo - prev_cl).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def _calc_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    hi, lo = df['high'], df['low']
    up   = hi.diff()
    down = -lo.diff()
    plus_dm  = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    atr = _calc_atr(df, period)
    plus_di  = 100 * pd.Series(plus_dm,  index=df.index).rolling(period).mean() / atr
    minus_di = 100 * pd.Series(minus_dm, index=df.index).rolling(period).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-9)
    return dx.rolling(period).mean()


def score_ticker(df: pd.DataFrame, ihsg_df: pd.DataFrame = None,
                 flow_score: float = None) -> dict:
    """
    Compute pre-breakout setup score for a single ticker.

    Returns dict with 'score' (0-100), 'reasons' list, and individual features.
    Returns score=0 with reasons=['insufficient_data'] if df too short.
    """
    if len(df) < 60:
        return {'score': 0, 'reasons': ['insufficient_data']}

    close  = df['close'].astype(float)
    high   = df['high'].astype(float)
    volume = df['volume'].astype(float)
    j = len(df) - 1

    atr14     = _calc_atr(df, 14)
    atr60_med = atr14.rolling(60, min_periods=20).median()
    adx14     = _calc_adx(df, 14)
    ma50      = close.rolling(50, min_periods=20).mean()
    avg_vol20 = volume.rolling(20, min_periods=5).mean()
    high_252w = high.rolling(252, min_periods=60).max()

    def _f(s, i=j): return float(s.iloc[i]) if not pd.isna(s.iloc[i]) else float('nan')

    cl_j    = _f(close)
    atr_j   = _f(atr14)
    atr60_j = _f(atr60_med)
    adx_j   = _f(adx14)
    ma50_j  = _f(ma50)
    h52     = _f(high_252w) if not pd.isna(high_252w.iloc[j]) else float(high.max())
    vol20_j = _f(avg_vol20) if not pd.isna(avg_vol20.iloc[j]) else float(volume.mean())
    vol5    = float(volume.iloc[max(0, j - 4):j + 1].mean())

    atr_ratio  = (atr_j / atr60_j)  if atr60_j > 0 and not pd.isna(atr_j)  else float('nan')
    vol_dryup  = (vol5 / vol20_j)   if vol20_j > 0                          else float('nan')
    near_52w   = int(cl_j >= 0.92 * h52) if h52 > 0 else 0
    above_ma50 = int(cl_j > ma50_j)      if not pd.isna(ma50_j) else 0

    rs = float('nan')
    if ihsg_df is not None and len(ihsg_df) >= 21:
        try:
            t_ret = close.pct_change(20).iloc[j]
            i_ret = ihsg_df['close'].astype(float).pct_change(20).iloc[-1]
            if not pd.isna(t_ret) and not pd.isna(i_ret) and (1 + i_ret) != 0:
                rs = (1 + t_ret) / (1 + i_ret)
        except Exception:
            pass

    score   = 0
    reasons = []

    # 35 pts: CONTINUATION — above MA50 with meaningful trend (ADX ≥ 22)
    if above_ma50 and not pd.isna(adx_j) and adx_j >= 22:
        score += 35
        reasons.append(f'CONTINUATION(ADX={adx_j:.0f})')

    # 20 pts: near 52-week high (within 8%)
    if near_52w:
        score += 20
        reasons.append('NEAR_52W_HIGH')

    # 15 pts: ATR contraction below 60-bar median (VCP-like)
    if not pd.isna(atr_ratio) and atr_ratio < 0.85:
        score += 15
        reasons.append(f'ATR_CONTRACTED({atr_ratio:.2f})')

    # 15 pts: volume dry-up (5-day avg < 80% of 20-day avg)
    if not pd.isna(vol_dryup) and vol_dryup < 0.80:
        score += 15
        reasons.append(f'VOL_DRYUP({vol_dryup:.2f})')

    # 10 pts: positive relative strength vs IHSG (20-bar)
    if not pd.isna(rs) and rs > 1.0:
        score += 10
        reasons.append(f'RS_POS({rs:.2f})')

    # 5 pts: positive foreign/smart-money net flow (stockbit)
    if flow_score is not None and flow_score > 0:
        score += 5
        reasons.append(f'FLOW_POS({flow_score:+.0f})')

    return {
        'score':       min(score, 100),
        'reasons':     reasons,
        'above_ma50':  above_ma50,
        'adx':         round(adx_j, 1)   if not pd.isna(adx_j)   else None,
        'near_52w':    near_52w,
        'atr_ratio':   round(atr_ratio, 3) if not pd.isna(atr_ratio) else None,
        'vol_dryup':   round(vol_dryup, 3) if not pd.isna(vol_dryup) else None,
        'rs':          round(rs, 3)       if not pd.isna(rs)       else None,
        'close':       cl_j,
        'vol_context': classify_volume_context(df),
    }


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
    volume = df['volume'].astype(float)
    j = len(df) - 1

    atr14    = _calc_atr(df, 14)
    atr_med  = atr14.rolling(30, min_periods=15).median()
    low_50d  = close.rolling(50, min_periods=20).min()
    vol_med  = volume.rolling(20, min_periods=5).median()
    ma3      = close.rolling(3, min_periods=2).mean()

    def _f(s, i=j):
        v = s.iloc[i]
        return float(v) if not pd.isna(v) else float('nan')

    cl_j    = _f(close)
    vol_j   = _f(volume)
    atr_j   = _f(atr14)
    atr_m_j = _f(atr_med)
    low50_j = _f(low_50d)
    vol_m_j = _f(vol_med)
    ma3_j   = _f(ma3)

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

    score   = 0
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
        'score':       min(score, 100),
        'reasons':     reasons,
        'vol_ratio':   round(vol_ratio, 1) if not pd.isna(vol_ratio) else None,
        'near_low':    near_low,
        'above_3ma':   above_3ma,
        'green_day':   green_day,
        'atr_ratio':   round(atr_ratio, 3) if not pd.isna(atr_ratio) else None,
        'close':       cl_j,
        'vol_context': classify_volume_context(df),
    }


def _upsert_setup(conn: sqlite3.Connection, ticker: str, detected_at: str,
                  pattern_type: str, result: dict) -> bool:
    """Insert or ignore a setup into watchlist_premover. Returns True if new.

    Cooldown: suppress alert if same (ticker, pattern) was detected in the
    last 3 days AND the current close has not risen >10% above that prior
    alert's close. Prevents alert fatigue while still re-firing when the
    move actually starts.
    """
    cur_close = result.get('close')
    prior = conn.execute("""
        SELECT close_price FROM watchlist_premover
        WHERE ticker = ? AND pattern_type = ?
          AND detected_at >= date(?, '-3 days')
          AND detected_at < ?
        ORDER BY detected_at DESC LIMIT 1
    """, (ticker, pattern_type, detected_at, detected_at)).fetchone()
    if prior and prior[0] and cur_close and cur_close <= prior[0] * 1.10:
        return False

    if pattern_type == 'CONTINUATION':
        conn.execute("""
            INSERT OR IGNORE INTO watchlist_premover
            (ticker, detected_at, pattern_type, score, reasons_json,
             above_ma50, adx, near_52w, atr_ratio, vol_dryup, rs, close_price,
             vol_context)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            ticker, detected_at, pattern_type, result['score'],
            json.dumps(result.get('reasons', [])),
            result.get('above_ma50'), result.get('adx'),
            result.get('near_52w'),   result.get('atr_ratio'),
            result.get('vol_dryup'),  result.get('rs'),
            result.get('close'),      result.get('vol_context'),
        ))
    elif pattern_type == 'REVERSAL_BREAKOUT':
        conn.execute("""
            INSERT OR IGNORE INTO watchlist_premover
            (ticker, detected_at, pattern_type, score, reasons_json,
             near_low, above_3ma, green_day, atr_ratio, vol_ratio, close_price,
             vol_context)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            ticker, detected_at, pattern_type, result['score'],
            json.dumps(result.get('reasons', [])),
            result.get('near_low'), result.get('above_3ma'),
            result.get('green_day'), result.get('atr_ratio'),
            result.get('vol_ratio'), result.get('close'),
            result.get('vol_context'),
        ))
    return conn.execute('SELECT changes()').fetchone()[0] > 0


def run_scan(db_path: str, send_alert_fn=None) -> list:
    """
    Scan all tickers EOD, store qualifying setups in watchlist_premover.
    Runs both CONTINUATION and REVERSAL_BREAKOUT patterns.

    Returns list of NEW setups inserted this run (not previously seen today).
    """
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
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

        # CONTINUATION pattern
        try:
            result = score_ticker(df, ihsg_df=ihsg_df, flow_score=flow_map.get(ticker))
            if result['score'] >= ALERT_THRESHOLD:
                if _upsert_setup(conn, ticker, detected_at, 'CONTINUATION', result):
                    new_setups.append({'ticker': ticker, 'pattern': 'CONTINUATION', **result})
        except Exception as e:
            print(f"[premover] {ticker} CONTINUATION error: {e}")

        # REVERSAL_BREAKOUT pattern
        try:
            result = score_ticker_reversal(df, flow_score=flow_map.get(ticker))
            if result['score'] >= REVERSAL_THRESHOLD:
                if _upsert_setup(conn, ticker, detected_at, 'REVERSAL_BREAKOUT', result):
                    new_setups.append({'ticker': ticker, 'pattern': 'REVERSAL_BREAKOUT', **result})
        except Exception as e:
            print(f"[premover] {ticker} REVERSAL error: {e}")

    conn.commit()
    conn.close()

    if new_setups and send_alert_fn:
        reversal = [s for s in new_setups if s['pattern'] == 'REVERSAL_BREAKOUT']
        cont     = [s for s in new_setups if s['pattern'] == 'CONTINUATION']

        msg = f"\U0001f50d <b>Pre-Breakout Setups — {detected_at}</b>\n\n"

        _VOL_CTX_LABELS = {
            'crash_absorption':        'CRASH_ABSORB',
            'exhaustion_distribution': 'EXHAUST_DIST',
            'breakout_accumulation':   'BRK_ACCUM',
        }
        if reversal:
            msg += f"── REVERSAL_BREAKOUT ({len(reversal)}) ──\n"
            for s in sorted(reversal, key=lambda x: x['score'], reverse=True)[:5]:
                ctx = s.get('vol_context', 'normal')
                ctx_tag = f" [{_VOL_CTX_LABELS[ctx]}]" if ctx in _VOL_CTX_LABELS else ''
                msg += f"<b>{s['ticker']}</b> — Score {s['score']}/100{ctx_tag}\n"
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
                'ticker':       r[0],
                'detected_at':  r[1],
                'pattern_type': r[2],
                'score':        r[3],
                'reasons':      json.loads(r[4]) if r[4] else [],
                'above_ma50':   r[5], 'adx': r[6], 'near_52w': r[7],
                'near_low':     r[8], 'above_3ma': r[9], 'green_day': r[10],
                'atr_ratio':    r[11], 'vol_ratio': r[12], 'vol_dryup': r[13],
                'rs':           r[14],
                'close_price':  r[15],
                'fired':        bool(r[16]),
                'fired_at':     r[17],
            }
            for r in rows
        ]
    finally:
        conn.close()


def mark_fired(db_path: str, ticker: str):
    """Mark ticker's unfired setups as fired (breakout occurred)."""
    conn = sqlite3.connect(db_path)
    _init_table(conn)
    conn.execute("""
        UPDATE watchlist_premover SET fired=1, fired_at=datetime('now')
        WHERE ticker=? AND fired=0
    """, (ticker,))
    conn.commit()
    conn.close()


def daily_pattern_summary(db_path: str, days: int = 1) -> str:
    """Aggregate pattern_metrics over the last N days into a human summary.

    Returns a multi-line string suitable for logging or Telegram. Lines are
    one-per-pattern_type ordered by alert count desc. Returns an empty
    string when there are no alerts in the window.
    """
    conn = sqlite3.connect(db_path)
    _init_table(conn)
    rows = conn.execute("""
        SELECT
            pattern_type,
            COUNT(*)                                              AS alerts,
            COUNT(trade_id)                                       AS traded,
            SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END)          AS winning,
            AVG(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct END)   AS avg_pnl
        FROM pattern_metrics
        WHERE alerted_at >= date('now', ?)
        GROUP BY pattern_type
        ORDER BY alerts DESC
    """, (f'-{days} days',)).fetchall()
    conn.close()

    if not rows:
        return ''

    lines = []
    for pattern, alerts, traded, winning, avg_pnl in rows:
        avg_txt = f"{avg_pnl:+.1f}% avg" if avg_pnl is not None else "no PnL yet"
        lines.append(
            f"{pattern}: {alerts} alerts, {traded} traded, "
            f"{winning or 0} winning ({avg_txt})"
        )
    return '\n'.join(lines)
