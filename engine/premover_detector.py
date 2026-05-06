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


ALERT_THRESHOLD = 50


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


def _calc_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
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
        'score':      min(score, 100),
        'reasons':    reasons,
        'above_ma50': above_ma50,
        'adx':        round(adx_j, 1)   if not pd.isna(adx_j)   else None,
        'near_52w':   near_52w,
        'atr_ratio':  round(atr_ratio, 3) if not pd.isna(atr_ratio) else None,
        'vol_dryup':  round(vol_dryup, 3) if not pd.isna(vol_dryup) else None,
        'rs':         round(rs, 3)       if not pd.isna(rs)       else None,
        'close':      cl_j,
    }


def run_scan(db_path: str, send_alert_fn=None) -> list:
    """
    Scan all tickers EOD, store qualifying setups in watchlist_premover.

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
        try:
            result = score_ticker(df, ihsg_df=ihsg_df, flow_score=flow_map.get(ticker))
            if result['score'] < ALERT_THRESHOLD:
                continue

            conn.execute("""
                INSERT OR IGNORE INTO watchlist_premover
                (ticker, detected_at, score, reasons_json,
                 above_ma50, adx, near_52w, atr_ratio, vol_dryup, rs, close_price)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                ticker, detected_at, result['score'],
                json.dumps(result['reasons']),
                result['above_ma50'], result['adx'],
                result['near_52w'],   result['atr_ratio'],
                result['vol_dryup'],  result['rs'],
                result['close'],
            ))
            if conn.execute('SELECT changes()').fetchone()[0] > 0:
                new_setups.append({'ticker': ticker, **result})
        except Exception as e:
            print(f"[premover] {ticker} error: {e}")

    conn.commit()
    conn.close()

    if new_setups and send_alert_fn:
        msg = f"🔍 <b>Pre-Breakout Setups — {detected_at}</b>\n\n"
        for s in sorted(new_setups, key=lambda x: x['score'], reverse=True)[:10]:
            msg += f"<b>{s['ticker']}</b> — Score {s['score']}/100\n"
            msg += f"  {' · '.join(s['reasons'])}\n"
            msg += f"  Close: {s['close']:,.0f}\n\n"
        if len(new_setups) > 10:
            msg += f"... +{len(new_setups) - 10} more\n\n"
        msg += f"Total: {len(new_setups)} new setups"
        try:
            send_alert_fn(msg)
        except Exception as e:
            print(f"[premover] Telegram alert error: {e}")

    return new_setups


def get_watchlist(db_path: str, min_score: int = ALERT_THRESHOLD,
                  days: int = 5, fired: bool = False) -> list:
    """Return active watchlist entries from the last N days."""
    conn = sqlite3.connect(db_path)
    _init_table(conn)
    try:
        rows = conn.execute(f"""
            SELECT ticker, detected_at, score, reasons_json,
                   above_ma50, adx, near_52w, atr_ratio, vol_dryup, rs, close_price,
                   fired, fired_at
            FROM watchlist_premover
            WHERE score >= ? AND fired = ?
              AND detected_at >= date('now', '-{int(days)} days')
            ORDER BY score DESC, detected_at DESC
        """, (min_score, int(fired))).fetchall()
        return [
            {
                'ticker':      r[0], 'detected_at': r[1], 'score': r[2],
                'reasons':     json.loads(r[3]) if r[3] else [],
                'above_ma50':  r[4], 'adx': r[5], 'near_52w': r[6],
                'atr_ratio':   r[7], 'vol_dryup': r[8], 'rs': r[9],
                'close_price': r[10], 'fired': bool(r[11]), 'fired_at': r[12],
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
