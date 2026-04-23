
import os
from dotenv import load_dotenv
import sqlite3
import json
from datetime import datetime
import pytz

load_dotenv()

WIB     = pytz.timezone("Asia/Jakarta")
DB_PATH = os.getenv("DB_PATH", "/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db")

def calc_swing_tp(ticker: str, entry_price: float, lookback: int = 20) -> float:
    """
    Hitung TP berdasarkan swing high terdekat di atas entry price.
    - Swing high: bar dengan high lebih tinggi dari N bar kiri dan kanan (N=2)
    - TP = swing high - 0.5%
    - Fallback: ATR-based jika tidak ada swing high di atas entry
    """
    import pandas as pd
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql(
            'SELECT date, high, close FROM ohlcv WHERE ticker=? ORDER BY date DESC LIMIT ?',
            conn,
            params=(ticker, lookback + 10)
        )
        conn.close()
        if len(df) < 6:
            raise ValueError("Data tidak cukup")

        df = df.iloc[::-1].reset_index(drop=True)  # balik ke ascending

        # Deteksi swing high (high > 2 bar kiri & 2 bar kanan)
        swing_highs = []
        for i in range(2, len(df) - 2):
            h = df.loc[i, 'high']
            if (h > df.loc[i-1, 'high'] and h > df.loc[i-2, 'high'] and
                h > df.loc[i+1, 'high'] and h > df.loc[i+2, 'high']):
                swing_highs.append(h)

        # Cari swing high terdekat DI ATAS entry price
        candidates = [sh for sh in swing_highs if sh > entry_price * 1.005]
        if candidates:
            swing_tp = min(candidates) * 0.995  # -0.5%
            
            # ENFORCE MINIMUM 2:1 R/R RATIO
            cfg = get_config()
            sl_pct = cfg.get("sl_pct", 0.025)
            sl_price = entry_price * (1 - sl_pct)
            sl_price = round(sl_price)
            sl_distance = entry_price - sl_price
            min_tp_for_2to1 = entry_price + (2 * sl_distance)
            final_tp = max(swing_tp, min_tp_for_2to1)
            print(f"[TP] {ticker}: Swing={swing_tp:.0f}, Min2:1={min_tp_for_2to1:.0f}, Final={final_tp:.0f}")
            return round(final_tp)
        df['tr'] = df['high'] - df['close'].shift(1).fillna(df['close'])
        atr = df['tr'].tail(14).mean()
        tp = round(entry_price + (atr * 2))
        tp = max(tp, round(entry_price * 1.02))  # minimum 2%
        return tp

    except Exception as e:
        print(f"[swing_tp] Error {ticker}: {e}, fallback ATR 4%")
        return round(entry_price * 1.04)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_paper_table():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS paper_trades (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker      TEXT NOT NULL,
            strategy    TEXT DEFAULT "Momentum Following",
            entry_date  TEXT,
            entry_price REAL,
            lots        INTEGER,
            capital_used REAL,
            tp_price    REAL,
            sl_price    REAL,
            exit_date   TEXT,
            exit_price  REAL,
            exit_reason TEXT,
            pnl_rp      REAL,
            pnl_pct     REAL,
            status      TEXT DEFAULT "OPEN"
        );
        CREATE TABLE IF NOT EXISTS paper_config (
            key   TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    # Default config
    configs = [
        ("capital",    "50000000"),
        ("tp_pct",     "0.035"),
        ("sl_pct",     "0.025"),
        ("risk_pct",   "0.02"),
        ("max_open",   "5"),
    ]
    for k, v in configs:
        conn.execute("INSERT OR IGNORE INTO paper_config (key,value) VALUES (?,?)", (k,v))
    # Add exit_rules column if missing (Swing Trend stores active R1–R7 triggers here)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(paper_trades)").fetchall()]
    if 'exit_rules' not in cols:
        conn.execute("ALTER TABLE paper_trades ADD COLUMN exit_rules TEXT")
    if 'adx_peak' not in cols:
        conn.execute("ALTER TABLE paper_trades ADD COLUMN adx_peak REAL")
    if 'highest_seen' not in cols:
        conn.execute("ALTER TABLE paper_trades ADD COLUMN highest_seen REAL")
    conn.commit()
    conn.close()
    pass  # tables ready

def get_config():
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM paper_config").fetchall()
    conn.close()
    return {r["key"]: float(r["value"]) for r in rows}

def get_open_trades():
    conn = get_db()
    rows = conn.execute("SELECT * FROM paper_trades WHERE status=\'OPEN\'").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def check_trend(ticker: str) -> str:
    """
    Check trend direction.
    Returns: 'UPTREND', 'DOWNTREND', or 'SIDEWAYS'
    """
    import pandas as pd
    try:
        conn = get_db()
        df = pd.read_sql(
            'SELECT close FROM ohlcv WHERE ticker=? ORDER BY date DESC LIMIT 25',
            conn,
            params=(ticker,)
        )
        conn.close()
        
        if len(df) < 20:
            return 'UNKNOWN'
        
        df = df.iloc[::-1].reset_index(drop=True)  # Ascending
        df['ma20'] = df['close'].rolling(20).mean()
        
        # Latest values
        price = df['close'].iloc[-1]
        ma20_now = df['ma20'].iloc[-1]
        
        # MA20 slope (last 5 bars)
        ma20_slope = (df['ma20'].iloc[-1] - df['ma20'].iloc[-6]) / 5
        
        # Trend logic
        if price > ma20_now and ma20_slope > 0:
            return 'UPTREND'
        elif price < ma20_now and ma20_slope < 0:
            return 'DOWNTREND'
        else:
            return 'SIDEWAYS'
            
    except Exception as e:
        print(f"[check_trend] {ticker} error: {e}")
        return 'UNKNOWN'


def _calc_atr_from_db(ticker: str, periods: int = 14) -> float:
    """Fetch ATR from stored OHLCV. Returns None if insufficient data."""
    import pandas as pd
    try:
        conn = get_db()
        df = pd.read_sql(
            'SELECT high, low, close FROM ohlcv WHERE ticker=? ORDER BY date DESC LIMIT ?',
            conn, params=(ticker, periods + 5)
        )
        conn.close()
        if len(df) < periods:
            return None
        df = df.iloc[::-1].reset_index(drop=True)
        tr = pd.concat([
            df['high'] - df['low'],
            (df['high'] - df['close'].shift()).abs(),
            (df['low'] - df['close'].shift()).abs(),
        ], axis=1).max(axis=1)
        return tr.rolling(periods).mean().iloc[-1]
    except Exception:
        return None


def open_trade(ticker: str, entry_price: float, strategy: str = 'Momentum Following',
               sl_atr_mult: float = 1.0, min_rr: float = 2.0,
               sl_price: float = None, tp_price: float = None, notify: bool = True):
    cfg      = get_config()
    capital  = cfg["capital"]
    risk_pct = cfg["risk_pct"]
    max_open = int(cfg["max_open"])

    open_trades = get_open_trades()
    if len(open_trades) >= max_open:
        return {"error": f"Max {max_open} posisi sudah terbuka"}
    if any(t["ticker"] == ticker for t in open_trades):
        return {"error": f"{ticker} sudah ada posisi terbuka"}

    is_swing = (strategy or '').strip().lower() == 'swing trend'
    exit_rules_json = None

    if sl_price is not None and sl_price > 0:
        # Explicit SL provided (e.g. from Swing Onset screener)
        sl_dist = entry_price - sl_price
        sl_pct  = sl_dist / entry_price if entry_price > 0 else 0
    else:
        # ATR-based SL (fallback to config sl_pct)
        atr = _calc_atr_from_db(ticker)
        if atr and atr > 0:
            sl_dist  = atr * sl_atr_mult
            sl_pct   = sl_dist / entry_price
        else:
            sl_pct   = cfg.get("sl_pct", 0.025)
            sl_dist  = entry_price * sl_pct
        sl_price = round(entry_price - sl_dist)

    if tp_price is None or tp_price <= 0:
        if is_swing:
            # TP aim only — real exit is R1–R7, not a price level. Pick 3R as display target.
            tp_price = round(entry_price + 3 * sl_dist)
        else:
            tp_price = calc_swing_tp(ticker, entry_price, lookback=20)
            # Re-enforce 2:1 on final values
            min_tp = entry_price + sl_dist * min_rr
            tp_price = max(tp_price, round(min_tp))

    if is_swing:
        exit_rules_json = json.dumps([
            'R1_MA_BREAK', 'R2_LOWER_LOW', 'R3_ADX_FADE',
            'R4_DISTRIBUTION', 'R5_FLOW_FLIP', 'R6_BEAR_ENGULF', 'R7_TRAIL_SL'
        ])

    # Lot sizing
    cost_per_lot = entry_price * 100
    risk_rp      = capital * risk_pct
    sl_rp        = cost_per_lot * sl_pct if sl_pct > 0 else cost_per_lot * 0.02
    lots         = int(risk_rp / sl_rp) if sl_rp > 0 else 1
    max_lots     = int((capital * 0.30) / cost_per_lot)
    lots         = max(1, min(lots, max_lots))
    capital_used = lots * cost_per_lot
    now          = datetime.now(WIB).strftime("%Y-%m-%d")

    conn = get_db()
    conn.execute("""
        INSERT INTO paper_trades
        (ticker, strategy, entry_date, entry_price, lots, capital_used, tp_price, sl_price, exit_rules, highest_seen, status)
        VALUES (?,?,?,?,?,?,?,?,?,?, 'OPEN')
    """, (ticker, strategy, now, entry_price, lots, capital_used, tp_price, sl_price, exit_rules_json, entry_price))
    conn.commit()
    trade_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()

    # Notify Telegram
    if notify:
        try:
            from scheduler import send_telegram
            send_telegram(
                f"📝 <b>Paper Trade OPENED</b>\n\n"
                f"🟢 <b>{ticker}</b> @ Rp {entry_price:,.0f}\n"
                f"   📈 TP: Rp {tp_price:,.0f}\n"
                f"   🛑 SL: Rp {sl_price:,.0f}\n"
                f"   Lot: {lots} | Capital: Rp {capital_used:,.0f}\n"
                f"   Strategy: {strategy}"
            )
        except Exception:
            pass

    return {
        "id":           trade_id,
        "ticker":       ticker,
        "entry_price":  entry_price,
        "lots":         lots,
        "capital_used": capital_used,
        "tp_price":     tp_price,
        "sl_price":     sl_price,
        "strategy":     strategy,
        "exit_rules":   exit_rules_json,
        "entry_date":   now
    }

def close_trade(trade_id: int, exit_price: float, exit_reason: str = "MANUAL", notify: bool = True):
    conn  = get_db()
    trade = conn.execute("SELECT * FROM paper_trades WHERE id=?", (trade_id,)).fetchone()
    if not trade:
        conn.close()
        return {"error": "Trade tidak ditemukan"}

    trade    = dict(trade)
    pnl_rp   = round((exit_price - trade["entry_price"]) * trade["lots"] * 100)
    pnl_pct  = round((exit_price - trade["entry_price"]) / trade["entry_price"] * 100, 2)
    now      = datetime.now(WIB).strftime("%Y-%m-%d")

    conn.execute("""
        UPDATE paper_trades SET
        exit_date=?, exit_price=?, exit_reason=?,
        pnl_rp=?, pnl_pct=?, status=\'CLOSED\'
        WHERE id=?
    """, (now, exit_price, exit_reason, pnl_rp, pnl_pct, trade_id))
    conn.commit()
    conn.close()

    # Notify Telegram
    if notify:
        try:
            from scheduler import send_telegram
            emoji = "🟢" if pnl_rp >= 0 else "🔴"
            send_telegram(
                f"{emoji} <b>Paper Trade CLOSED</b>\n\n"
                f"<b>{trade['ticker']}</b> @ Rp {exit_price:,.0f}\n"
                f"   Entry: Rp {trade['entry_price']:,.0f}\n"
                f"   P&L: Rp {pnl_rp:,} ({pnl_pct:+.2f}%)\n"
                f"   Reason: {exit_reason}"
            )
        except Exception:
            pass

    return {
        "ticker":       trade["ticker"],
        "entry_price":  trade["entry_price"],
        "exit_price":   exit_price,
        "lots":         trade["lots"],
        "pnl_rp":       pnl_rp,
        "pnl_pct":      pnl_pct,
        "exit_reason":  exit_reason
    }

def get_summary():
    conn   = get_db()
    closed = conn.execute("SELECT * FROM paper_trades WHERE status=\'CLOSED\'").fetchall()
    opened = conn.execute("SELECT * FROM paper_trades WHERE status=\'OPEN\'").fetchall()
    conn.close()

    closed = [dict(r) for r in closed]
    opened = [dict(r) for r in opened]

    total_pnl   = sum(t["pnl_rp"] for t in closed)
    winners     = [t for t in closed if t["pnl_rp"] > 0]
    win_rate    = round(len(winners) / len(closed) * 100, 1) if closed else 0

    return {
        "open_trades":   opened,
        "closed_trades": closed,
        "total_closed":  len(closed),
        "win_rate":      win_rate,
        "total_pnl_rp":  total_pnl,
        "total_return_pct": round(total_pnl / 50_000_000 * 100, 2)
    }

if __name__ == "__main__":
    init_paper_table()

def clear_history():
    """Hapus semua closed trades. Open trades tetap aman."""
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM paper_trades WHERE status='CLOSED'")
    count = cur.fetchone()[0]
    cur.execute("DELETE FROM paper_trades WHERE status='CLOSED'")
    conn.commit()
    conn.close()
    return {"deleted": count}
