
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
        # Filter toggles: 1=on, 0=off
        ("filter_fundamental", "1"),
        ("filter_sector",      "1"),
        ("filter_flow",        "1"),
        ("filter_rs",          "1"),
        ("filter_regime",      "1"),
        ("filter_vpin",        "0"),  # off by default
        # DD circuit breaker — hysteresis: trigger at threshold, auto-reset at recover
        ("entries_blocked",    "0"),    # 1 = new entries blocked by circuit breaker
        ("dd_threshold_pct",   "8.0"),  # block new entries when 30d DD >= this %
        ("dd_recover_pct",     "5.0"),  # auto-unblock when DD recovers <= this %
        # Premover auto-execution: off / shadow / enforce
        ("auto_trade_from_premover", "off"),
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
    if 'atr14' not in cols:
        conn.execute("ALTER TABLE paper_trades ADD COLUMN atr14 REAL")
    # premover_auto_log: shadow/enforce evaluation records
    conn.execute("""
        CREATE TABLE IF NOT EXISTS premover_auto_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker       TEXT NOT NULL,
            detected_at  TEXT NOT NULL,
            pattern_type TEXT,
            score        INTEGER,
            mode         TEXT,
            would_trade  INTEGER,
            skip_reason  TEXT,
            logged_at    TEXT
        )
    """)
    conn.commit()
    conn.close()
    pass  # tables ready

def get_config():
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM paper_config").fetchall()
    conn.close()
    result = {}
    for r in rows:
        try:
            result[r["key"]] = float(r["value"])
        except (ValueError, TypeError):
            result[r["key"]] = r["value"]
    return result

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


def calc_ara_arb_levels(price: float) -> dict:
    """
    IDX Auto Rejection thresholds per BEI Peng-00009/BEI.POP/03-2023 (symmetric).
    Tier: <=200 -> ±35%; 200-5000 -> ±25%; >5000 -> ±20%.
    Returns {ara_pct, arb_pct, ara_price, arb_price}. Sub-Rp50 treated as tier 1.
    """
    if price <= 200:
        pct = 0.35
    elif price <= 5000:
        pct = 0.25
    else:
        pct = 0.20
    return {
        "ara_pct":   pct,
        "arb_pct":   pct,
        "ara_price": price * (1 + pct),
        "arb_price": price * (1 - pct),
    }


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


def get_backtest_best(ticker: str):
    """Most recent backtest_cache row for a ticker, or None.

    Columns of interest: best_strategy, best_return (total_return_pct, %),
    win_rate (0-100). Used for strategy selection and the entry quality gate.
    """
    try:
        conn = get_db()
        row = conn.execute(
            "SELECT best_strategy, best_return, win_rate FROM backtest_cache "
            "WHERE ticker=? ORDER BY computed_date DESC LIMIT 1",
            (ticker,),
        ).fetchone()
        conn.close()
        return row
    except Exception:
        return None


def get_best_strategy_for_ticker(ticker: str) -> str:
    """Backtest-optimal strategy for a ticker; Momentum Following if no cache."""
    row = get_backtest_best(ticker)
    if row and row["best_strategy"]:
        return row["best_strategy"]
    return "Momentum Following"


def open_trade(ticker: str, entry_price: float, strategy: str = None,
               sl_atr_mult: float = 2.0, min_rr: float = 2.0,
               sl_price: float = None, tp_price: float = None, notify: bool = True,
               lots_multiplier: float = 1.0):
    # Default to the backtest-optimal strategy for this ticker, not a blanket
    # 'Momentum Following'. Explicit callers (swing screener, manual API) win.
    strategy = strategy or get_best_strategy_for_ticker(ticker)
    cfg      = get_config()
    capital  = cfg["capital"]
    risk_pct = cfg["risk_pct"]
    max_open = int(cfg["max_open"])

    if cfg.get("entries_blocked", 0) >= 1:
        return {"error": "Entries blocked: DD circuit breaker active. See /api/paper/dd_status."}

    open_trades = get_open_trades()
    if len(open_trades) >= max_open:
        return {"error": f"Max {max_open} posisi sudah terbuka"}
    if any(t["ticker"] == ticker for t in open_trades):
        return {"error": f"{ticker} sudah ada posisi terbuka"}

    # Cooldown: skip re-entry if ticker was stopped out at a loss within 3 days
    _conn = get_db()
    _recent_sl = _conn.execute("""
        SELECT exit_date FROM paper_trades
        WHERE ticker=? AND exit_reason='STOPPED_OUT' AND pnl_pct < 0
          AND exit_date >= date('now','localtime','-3 days')
        ORDER BY exit_date DESC LIMIT 1
    """, (ticker,)).fetchone()
    _conn.close()
    if _recent_sl:
        return {"error": f"{ticker} cooldown 3 hari setelah SL loss (exit {_recent_sl[0]})"}

    is_swing = (strategy or '').strip().lower() == 'swing trend'
    exit_rules_json = None

    # Always compute ATR14 upfront — used for SL/TP and sizing
    atr = _calc_atr_from_db(ticker)

    if sl_price is not None and sl_price > 0:
        # Explicit SL provided (e.g. from Swing Onset screener)
        sl_dist = entry_price - sl_price
        sl_pct  = sl_dist / entry_price if entry_price > 0 else 0
    else:
        if atr and atr > 0:
            sl_dist = atr * sl_atr_mult   # SL = entry - (2 × ATR14)
            sl_pct  = sl_dist / entry_price
        else:
            sl_pct  = cfg.get("sl_pct", 0.025)
            sl_dist = entry_price * sl_pct
        sl_price = round(entry_price - sl_dist)

    if tp_price is None or tp_price <= 0:
        if is_swing:
            # TP aim only — real exit is R1–R7, not a price level. Pick 3R as display target.
            tp_price = round(entry_price + 3 * sl_dist)
        else:
            # TP = entry + (3 × ATR14); fallback to fixed % if no ATR
            if atr and atr > 0:
                tp_price = round(entry_price + 3 * atr)
            else:
                tp_price = round(entry_price * 1.06)
            # Ensure minimum 2:1 R/R
            min_tp = entry_price + sl_dist * min_rr
            tp_price = max(tp_price, round(min_tp))

    # IDX ARA/ARB cap: TP above ARA won't fill (stock halts at limit) and SL below
    # ARB similarly unfillable. Apply with 0.5% safety margin from the limit.
    _ar = calc_ara_arb_levels(entry_price)
    if tp_price >= _ar["ara_price"]:
        _orig_tp = tp_price
        tp_price = round(_ar["ara_price"] * 0.995)
        print(f"[paper_trade] {ticker}: TP capped {_orig_tp:,.0f} -> {tp_price:,.0f} (ARA Rp {_ar['ara_price']:,.0f})")
    if sl_price <= _ar["arb_price"]:
        _orig_sl = sl_price
        sl_price = round(_ar["arb_price"] * 1.005)
        sl_dist = entry_price - sl_price
        sl_pct  = sl_dist / entry_price if entry_price > 0 else 0
        print(f"[paper_trade] {ticker}: SL capped {_orig_sl:,.0f} -> {sl_price:,.0f} (ARB Rp {_ar['arb_price']:,.0f})")

    # After capping, re-validate min_rr — skip entry if capped TP can't deliver enough
    # reward vs the SL distance (no realistic edge under IDX auto-rejection rules).
    # Swing Trend exits via R1-R7 not price TP, so skip the gate.
    if not is_swing:
        capped_reward = tp_price - entry_price
        capped_risk   = entry_price - sl_price
        if capped_risk > 0 and capped_reward / capped_risk < min_rr:
            return {"error": (
                f"{ticker} skipped: capped TP Rp {tp_price:,.0f} gives R/R "
                f"{capped_reward/capped_risk:.2f} < min {min_rr} (entry Rp {entry_price:,.0f}, "
                f"ARA Rp {_ar['ara_price']:,.0f})"
            )}

    if is_swing:
        exit_rules_json = json.dumps([
            'R1_MA_BREAK', 'R2_LOWER_LOW', 'R3_ADX_FADE',
            'R4_DISTRIBUTION', 'R5_FLOW_FLIP', 'R6_BEAR_ENGULF', 'R7_TRAIL_SL'
        ])

    # Volatility-adjusted position sizing: lots = capital_risk / (ATR14 × 100)
    cost_per_lot = entry_price * 100
    risk_rp      = capital * risk_pct
    if atr and atr > 0:
        lots = int(risk_rp / (atr * 100))
    else:
        sl_rp = cost_per_lot * sl_pct if sl_pct > 0 else cost_per_lot * 0.02
        lots  = int(risk_rp / sl_rp) if sl_rp > 0 else 1
    max_lots     = int((capital * 0.30) / cost_per_lot)
    lots         = max(1, min(int(lots * lots_multiplier), max_lots))
    capital_used = lots * cost_per_lot
    now          = datetime.now(WIB).strftime("%Y-%m-%d")

    conn = get_db()
    conn.execute("""
        INSERT INTO paper_trades
        (ticker, strategy, entry_date, entry_price, lots, capital_used, tp_price, sl_price, exit_rules, highest_seen, atr14, status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?, 'OPEN')
    """, (ticker, strategy, now, entry_price, lots, capital_used, tp_price, sl_price, exit_rules_json, entry_price, atr))
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

def _set_config(key: str, value) -> None:
    """Update a paper_config key. Value is coerced to str for storage."""
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO paper_config (key, value) VALUES (?, ?)",
                 (key, str(value)))
    conn.commit()
    conn.close()


def get_premover_mode() -> str:
    """Read auto_trade_from_premover from paper_config. Returns 'off' if not set."""
    conn = get_db()
    row = conn.execute(
        "SELECT value FROM paper_config WHERE key='auto_trade_from_premover'"
    ).fetchone()
    conn.close()
    return str(row[0]) if row else "off"


def set_premover_mode(mode: str) -> None:
    """Set auto_trade_from_premover. Must be 'off', 'shadow', or 'enforce'."""
    if mode not in ("off", "shadow", "enforce"):
        raise ValueError(f"Invalid mode '{mode}'. Must be: off, shadow, enforce.")
    _set_config("auto_trade_from_premover", mode)


def compute_drawdown(days: int = 30) -> dict:
    """
    Realized-equity drawdown from closed trades in the last `days`.
    Equity series = capital_base + cumulative PnL (chronological by exit_date).
    Returns {peak, current, dd_pct, n_trades, capital_base}.
    Empty/insufficient data => dd_pct = 0.
    """
    cfg = get_config()
    capital_base = cfg["capital"]

    conn = get_db()
    rows = conn.execute("""
        SELECT exit_date, pnl_rp FROM paper_trades
        WHERE status='CLOSED' AND exit_date IS NOT NULL
          AND exit_date >= date('now','localtime', ?)
        ORDER BY exit_date ASC, id ASC
    """, (f"-{int(days)} days",)).fetchall()
    conn.close()

    if not rows:
        return {"peak": capital_base, "current": capital_base, "dd_pct": 0.0,
                "n_trades": 0, "capital_base": capital_base}

    equity = capital_base
    peak   = capital_base
    for r in rows:
        equity += (r["pnl_rp"] or 0)
        if equity > peak:
            peak = equity
    dd_pct = (peak - equity) / peak * 100 if peak > 0 else 0.0
    return {"peak": peak, "current": equity, "dd_pct": round(dd_pct, 2),
            "n_trades": len(rows), "capital_base": capital_base}


def is_entries_blocked() -> bool:
    """Quick check used by entry gates."""
    cfg = get_config()
    return cfg.get("entries_blocked", 0) >= 1


def check_dd_circuit_breaker(send_alert: bool = True) -> dict:
    """
    Evaluate 30-day realized DD vs threshold; toggle entries_blocked on state change.
    Hysteresis: trigger when dd_pct >= dd_threshold_pct, reset when dd_pct <= dd_recover_pct.
    Returns drawdown dict + 'blocked', 'state_changed', 'threshold_pct', 'recover_pct'.
    """
    cfg       = get_config()
    threshold = cfg.get("dd_threshold_pct", 8.0)
    recover   = cfg.get("dd_recover_pct", 5.0)
    currently_blocked = cfg.get("entries_blocked", 0) >= 1

    dd = compute_drawdown(days=30)
    state_changed = False
    new_blocked   = currently_blocked

    if not currently_blocked and dd["dd_pct"] >= threshold:
        _set_config("entries_blocked", "1")
        new_blocked = True
        state_changed = True
        if send_alert:
            try:
                from scheduler import send_telegram
                send_telegram(
                    f"🛑 <b>DD CIRCUIT BREAKER ACTIVATED</b>\n"
                    f"Drawdown: <b>-{dd['dd_pct']:.2f}%</b> (threshold {threshold:.1f}%)\n"
                    f"Peak:    Rp {dd['peak']:,.0f}\n"
                    f"Current: Rp {dd['current']:,.0f}\n"
                    f"Closed trades (30d): {dd['n_trades']}\n"
                    f"New entries blocked. Auto-reset on DD ≤ {recover:.1f}%."
                )
            except Exception as e:
                print(f"[circuit_breaker] telegram error: {e}")
    elif currently_blocked and dd["dd_pct"] <= recover:
        _set_config("entries_blocked", "0")
        new_blocked = False
        state_changed = True
        if send_alert:
            try:
                from scheduler import send_telegram
                send_telegram(
                    f"✅ <b>DD CIRCUIT BREAKER RESET</b>\n"
                    f"DD recovered to -{dd['dd_pct']:.2f}% (≤ {recover:.1f}%).\n"
                    f"Equity: Rp {dd['current']:,.0f}\n"
                    f"New entries re-enabled."
                )
            except Exception as e:
                print(f"[circuit_breaker] telegram error: {e}")

    dd["blocked"]       = new_blocked
    dd["state_changed"] = state_changed
    dd["threshold_pct"] = threshold
    dd["recover_pct"]   = recover
    return dd


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


def evaluate_premover_trade(ticker: str, score: int, pattern_type: str) -> dict:
    """
    Dry-run open_trade() gates without side effects.
    Returns {'would_trade': bool, 'skip_reason': str|None, 'gates': dict}.
    Gates: DD circuit breaker → max positions → duplicate → regime.
    """
    gates: dict = {}

    # Gate 1: DD circuit breaker
    if is_entries_blocked():
        return {'would_trade': False, 'skip_reason': 'dd_circuit_breaker',
                'gates': {'entries_blocked': True}}
    gates['entries_blocked'] = False

    cfg         = get_config()
    open_trades = get_open_trades()
    max_open    = int(cfg.get('max_open', 5))

    # Gate 2: position limit
    if len(open_trades) >= max_open:
        return {'would_trade': False, 'skip_reason': f'max_open_{max_open}',
                'gates': {**gates, 'max_open': True}}
    gates['max_open'] = False

    # Gate 3: duplicate position
    if any(t['ticker'] == ticker for t in open_trades):
        return {'would_trade': False, 'skip_reason': 'already_open',
                'gates': {**gates, 'duplicate': True}}
    gates['duplicate'] = False

    # Gate 4: regime filter (reads backtest_cache, no OHLCV load)
    if int(cfg.get('filter_regime', 1)):
        conn = get_db()
        row = conn.execute(
            "SELECT regime FROM backtest_cache WHERE ticker=? "
            "ORDER BY computed_date DESC LIMIT 1",
            (ticker,)
        ).fetchone()
        conn.close()
        regime = str(row['regime']) if row and row['regime'] else 'UNKNOWN'
        if regime == 'BEAR':
            return {'would_trade': False, 'skip_reason': 'regime_bear',
                    'gates': {**gates, 'regime': regime}}
        gates['regime'] = regime

    return {'would_trade': True, 'skip_reason': None, 'gates': gates}


def _log_premover_auto(ticker: str, detected_at: str, pattern_type: str,
                       score: int, mode: str, eval_result: dict) -> None:
    """Insert one evaluation record into premover_auto_log."""
    conn = get_db()
    now_str = datetime.now(WIB).strftime('%Y-%m-%d %H:%M')
    conn.execute("""
        INSERT INTO premover_auto_log
        (ticker, detected_at, pattern_type, score, mode, would_trade, skip_reason, logged_at)
        VALUES (?,?,?,?,?,?,?,?)
    """, (ticker, detected_at, pattern_type, score, mode,
          int(eval_result.get('would_trade', False)),
          eval_result.get('skip_reason'), now_str))
    conn.commit()
    conn.close()
