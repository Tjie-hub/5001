"""
fastmover_study.py — Empirical fast-mover pattern study for IDX universe.

Scans all OHLCV data, finds +5% single-day moves, extracts the 20-bar
setup window before each move, classifies the pattern, and stores results
in the fastmover_patterns table.

Pattern taxonomy (IDX-calibrated):
  VCP          — volatility contraction near 52w high before expansion
  CONTINUATION — already trending (above MA50 + high ADX)
  RANGE_BREAK  — was ranging (low ADX, not near highs), clean breakout
  NEWS_SPIKE   — massive volume + open gap (news-driven, no setup)
  RANDOM       — no detectable pattern

Use: calibrate Phase 2 pre-breakout detector weights with real IDX base rates.
"""

import sqlite3
import json
import pandas as pd
import numpy as np
from datetime import datetime


MOVE_THRESHOLD  = 0.05   # +5% daily return = "fast mover"
SETUP_BARS      = 20     # look-back window before move day
MIN_SETUP_BARS  = 15     # minimum bars needed for feature extraction


# ── DB helpers ────────────────────────────────────────────────────────────────

def _init_table(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fastmover_patterns (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker          TEXT    NOT NULL,
            move_date       TEXT    NOT NULL,
            move_pct        REAL    NOT NULL,
            move_vol_ratio  REAL,
            open_gap_pct    REAL,
            pattern_type    TEXT    NOT NULL,
            atr_ratio       REAL,
            vol_dryup_ratio REAL,
            near_52w_high   INTEGER,
            adx_avg         REAL,
            above_ma50      INTEGER,
            setup_features  TEXT,
            studied_at      TEXT    NOT NULL,
            UNIQUE(ticker, move_date)
        )
    """)
    conn.commit()


# ── Indicator helpers ─────────────────────────────────────────────────────────

def _calc_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    hi, lo, cl = df['high'], df['low'], df['close']
    prev_cl = cl.shift(1)
    tr = pd.concat([hi - lo, (hi - prev_cl).abs(), (lo - prev_cl).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def _calc_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    hi, lo, cl = df['high'], df['low'], df['close']
    up   = hi.diff()
    down = -lo.diff()
    plus_dm  = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    atr = _calc_atr(df, period)
    plus_di  = 100 * pd.Series(plus_dm,  index=df.index).rolling(period).mean() / atr
    minus_di = 100 * pd.Series(minus_dm, index=df.index).rolling(period).mean() / atr
    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-9))
    return dx.rolling(period).mean()


# ── Feature extraction ────────────────────────────────────────────────────────

def _extract_features(full_df: pd.DataFrame, idx: int) -> dict:
    """
    Extract features at bar idx-1 (day before the move) using full_df context
    so long-period indicators (ADX, MA50, ATR60) are computed correctly.
    """
    if idx < MIN_SETUP_BARS:
        return None

    close  = full_df['close'].astype(float)
    volume = full_df['volume'].astype(float)
    high   = full_df['high'].astype(float)

    # Compute indicators on full df, sample at idx-1 (last setup bar)
    atr14      = _calc_atr(full_df, 14)
    atr60_med  = atr14.rolling(60, min_periods=20).median()
    adx14      = _calc_adx(full_df, 14)
    ma50       = close.rolling(50, min_periods=20).mean()
    avg_vol20  = volume.rolling(20, min_periods=5).mean()
    high_252w  = high.rolling(252, min_periods=60).max()

    j = idx - 1  # last bar of setup window

    # ATR contraction: current ATR vs its 60-bar median (VCP indicator)
    atr_j    = float(atr14.iloc[j])    if not pd.isna(atr14.iloc[j])    else float('nan')
    atr60_j  = float(atr60_med.iloc[j]) if not pd.isna(atr60_med.iloc[j]) else float('nan')
    atr_ratio = (atr_j / atr60_j) if (atr60_j and atr60_j > 0) else float('nan')

    # Volume dry-up: 5-bar avg vs 20-bar avg
    vol5_avg = float(volume.iloc[max(0, j-4):j+1].mean())
    vol20_j  = float(avg_vol20.iloc[j]) if not pd.isna(avg_vol20.iloc[j]) else float(volume.iloc[:j+1].mean())
    vol_dryup = (vol5_avg / vol20_j) if vol20_j > 0 else float('nan')

    # Near 52-week high
    h52  = float(high_252w.iloc[j]) if not pd.isna(high_252w.iloc[j]) else float(high.iloc[:j+1].max())
    cl_j = float(close.iloc[j])
    near_52w = int(cl_j >= 0.92 * h52) if h52 > 0 else 0

    # ADX at setup end
    adx_j    = float(adx14.iloc[j]) if not pd.isna(adx14.iloc[j]) else float('nan')

    # Above MA50
    ma50_j   = float(ma50.iloc[j]) if not pd.isna(ma50.iloc[j]) else float('nan')
    above_ma50 = int(cl_j > ma50_j) if not pd.isna(ma50_j) else 0

    # Move-day stats
    move_row   = full_df.iloc[idx]
    prev_close = float(full_df.iloc[idx - 1]['close'])
    move_vol   = float(move_row['volume'])
    move_vol_r = (move_vol / vol20_j) if vol20_j > 0 else float('nan')
    open_gap   = ((float(move_row['open']) - prev_close) / prev_close) if prev_close > 0 else 0.0

    def _r(v): return round(v, 3) if not pd.isna(v) else None

    return {
        'atr_ratio':       _r(atr_ratio),
        'vol_dryup_ratio': _r(vol_dryup),
        'near_52w_high':   near_52w,
        'adx':             round(adx_j, 1) if not pd.isna(adx_j) else None,
        'above_ma50':      above_ma50,
        'move_vol_ratio':  round(move_vol_r, 2) if not pd.isna(move_vol_r) else None,
        'open_gap_pct':    round(open_gap * 100, 2),
    }


# ── Pattern classifier ────────────────────────────────────────────────────────

def _classify(f: dict) -> str:
    """
    Rule-based pattern classification. Priority order matters.

    Thresholds calibrated against IDX data (490-bar universe):
      - atr_ratio < 0.85: ATR is 15%+ below its 60-bar median (contraction)
      - vol_dryup  < 0.80: 5-day vol is 20%+ below 20-day avg (dry-up)
      - adx >= 22: meaningful trend (IDX ADX skews lower than US markets)
      - adx < 18:  ranging
    """
    if f is None:
        return 'RANDOM'

    atr_ratio    = f.get('atr_ratio')
    vol_dryup    = f.get('vol_dryup_ratio')
    near_52w     = f.get('near_52w_high', 0)
    adx          = f.get('adx')
    above_ma50   = f.get('above_ma50', 0)
    move_vol_r   = f.get('move_vol_ratio')
    open_gap_pct = f.get('open_gap_pct', 0)

    # 1. NEWS_SPIKE — massive volume + gap, setup irrelevant
    if (move_vol_r is not None and move_vol_r >= 3.5
            and open_gap_pct is not None and open_gap_pct >= 3.0):
        return 'NEWS_SPIKE'

    # 2. VCP — ATR + volume contraction near highs before expansion
    atr_contracted = atr_ratio is not None and atr_ratio < 0.85
    vol_dried      = vol_dryup  is not None and vol_dryup  < 0.80
    if atr_contracted and vol_dried and near_52w:
        return 'VCP'

    # 3. CONTINUATION — stock already in strong uptrend
    if above_ma50 and adx is not None and adx >= 22:
        return 'CONTINUATION'

    # 4. RANGE_BREAK — was ranging (low ADX), not at highs
    if adx is not None and adx < 18 and not near_52w:
        return 'RANGE_BREAK'

    return 'RANDOM'


# ── Main study function ───────────────────────────────────────────────────────

def run_study(db_path: str, min_move_pct: float = MOVE_THRESHOLD,
              progress_cb=None) -> dict:
    """
    Scan full OHLCV universe, classify fast-mover patterns, store results.

    Args:
        db_path: path to walkforward.db
        min_move_pct: daily return threshold (default 0.05 = +5%)
        progress_cb: optional callable(ticker, i, total) for progress

    Returns:
        summary dict with counts by pattern_type
    """
    conn = sqlite3.connect(db_path)
    _init_table(conn)

    tickers = [r[0] for r in conn.execute(
        'SELECT DISTINCT ticker FROM ohlcv ORDER BY ticker'
    ).fetchall()]

    studied_at = datetime.now().isoformat(timespec='seconds')
    inserted = 0
    skipped  = 0

    for i, ticker in enumerate(tickers):
        if progress_cb:
            progress_cb(ticker, i, len(tickers))

        df = pd.read_sql(
            'SELECT date, open, high, low, close, volume FROM ohlcv '
            'WHERE ticker=? ORDER BY date ASC',
            conn, params=(ticker,)
        )
        if len(df) < MIN_SETUP_BARS + 5:
            continue
        for c in ['open', 'high', 'low', 'close', 'volume']:
            df[c] = df[c].astype(float)

        df['ret'] = df['close'].pct_change()
        big_idx = df.index[df['ret'] >= min_move_pct].tolist()

        for idx in big_idx:
            if idx < MIN_SETUP_BARS:
                continue

            move_row = df.iloc[idx]
            feats    = _extract_features(df, idx)
            pat      = _classify(feats)

            move_date    = str(move_row['date'])[:10]
            move_pct     = round(float(move_row['ret']) * 100, 2)
            move_vol_r   = feats.get('move_vol_ratio') if feats else None
            open_gap_pct = feats.get('open_gap_pct')   if feats else None

            try:
                conn.execute("""
                    INSERT OR REPLACE INTO fastmover_patterns
                    (ticker, move_date, move_pct, move_vol_ratio, open_gap_pct,
                     pattern_type, atr_ratio, vol_dryup_ratio, near_52w_high,
                     adx_avg, above_ma50, setup_features, studied_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    ticker, move_date, move_pct, move_vol_r, open_gap_pct,
                    pat,
                    feats.get('atr_ratio')       if feats else None,
                    feats.get('vol_dryup_ratio') if feats else None,
                    feats.get('near_52w_high')   if feats else None,
                    feats.get('adx')             if feats else None,
                    feats.get('above_ma50')      if feats else None,
                    json.dumps(feats) if feats else None,
                    studied_at,
                ))
                inserted += 1
            except Exception:
                skipped += 1

    conn.commit()

    # Summary
    rows = conn.execute("""
        SELECT pattern_type, COUNT(*) as cnt,
               AVG(move_pct) as avg_pct,
               AVG(move_vol_ratio) as avg_vol_r
        FROM fastmover_patterns
        GROUP BY pattern_type ORDER BY cnt DESC
    """).fetchall()
    total = sum(r[1] for r in rows)

    summary = {
        'total': total,
        'inserted_this_run': inserted,
        'patterns': [
            {
                'pattern':      r[0],
                'count':        r[1],
                'pct_of_total': round(r[1] / total * 100, 1) if total else 0,
                'avg_move_pct': round(r[2], 2) if r[2] else None,
                'avg_vol_ratio': round(r[3], 2) if r[3] else None,
            }
            for r in rows
        ]
    }
    conn.close()
    return summary


def get_summary(db_path: str) -> dict:
    """Return stored pattern distribution without re-running the study."""
    conn = sqlite3.connect(db_path)
    try:
        _init_table(conn)
        total_row = conn.execute('SELECT COUNT(*) FROM fastmover_patterns').fetchone()
        total = total_row[0] if total_row else 0
        if total == 0:
            return {'total': 0, 'patterns': [], 'note': 'Study not yet run'}

        rows = conn.execute("""
            SELECT pattern_type,
                   COUNT(*)            as cnt,
                   AVG(move_pct)       as avg_pct,
                   AVG(move_vol_ratio) as avg_vol_r,
                   MAX(studied_at)     as last_run
            FROM fastmover_patterns
            GROUP BY pattern_type ORDER BY cnt DESC
        """).fetchall()
        last_run = max(r[4] for r in rows if r[4])

        # Top tickers per pattern
        top = {}
        for pat in [r[0] for r in rows]:
            t_rows = conn.execute("""
                SELECT ticker, COUNT(*) as c FROM fastmover_patterns
                WHERE pattern_type=? GROUP BY ticker ORDER BY c DESC LIMIT 5
            """, (pat,)).fetchall()
            top[pat] = [{'ticker': r[0], 'count': r[1]} for r in t_rows]

        return {
            'total':    total,
            'last_run': last_run,
            'patterns': [
                {
                    'pattern':       r[0],
                    'count':         r[1],
                    'pct_of_total':  round(r[1] / total * 100, 1),
                    'avg_move_pct':  round(r[2], 2) if r[2] else None,
                    'avg_vol_ratio': round(r[3], 2) if r[3] else None,
                    'top_tickers':   top.get(r[0], []),
                }
                for r in rows
            ]
        }
    finally:
        conn.close()
