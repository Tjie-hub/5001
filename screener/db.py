"""
screener/db.py — Screener DB helpers using the shared walkforward.db
"""
import sqlite3

from config import DB_PATH
from data.db import connect as db_connect


def get_conn():
    conn = db_connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_screener_tables():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS ticks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT    NOT NULL,
                ticker      TEXT    NOT NULL,
                time        TEXT,
                price       INTEGER,
                volume      INTEGER,
                tick_type   TEXT,
                UNIQUE(date, ticker, time)
            );
            CREATE INDEX IF NOT EXISTS idx_ticks ON ticks(date, ticker);

            CREATE TABLE IF NOT EXISTS daily_screen (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT    NOT NULL,
                ticker      TEXT    NOT NULL,
                close       INTEGER,
                volume      INTEGER,
                avg_vol_20d INTEGER,
                vol_ratio   REAL,
                vwap        REAL,
                delta       INTEGER,
                cum_delta   INTEGER,
                signal      TEXT,
                consec_up   INTEGER DEFAULT 0,
                vpin        REAL,
                vpin_label  TEXT,
                updated_at  TEXT    DEFAULT (datetime('now','localtime'))
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_screen ON daily_screen(date, ticker);

            CREATE TABLE IF NOT EXISTS screen_run_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                run_at      TEXT    DEFAULT (datetime('now','localtime')),
                run_type    TEXT,
                tickers_ok  INTEGER DEFAULT 0,
                tickers_err INTEGER DEFAULT 0,
                duration_s  REAL,
                notes       TEXT
            );

            CREATE TABLE IF NOT EXISTS trade_alert_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                logged_at   TEXT    DEFAULT (datetime('now','localtime')),
                ticker      TEXT    NOT NULL,
                trade_id    INTEGER,
                alert_type  TEXT,
                message     TEXT
            );
        """)
        # Migrations for existing schemas
        for col, defn in [
            ('vpin', 'REAL'),
            ('vpin_label', 'TEXT'),
            ('vpin_buckets', 'INTEGER'),
        ]:
            try:
                assert col.replace('_', '').isalnum(), f"unsafe column: {col}"
                conn.execute(f"ALTER TABLE daily_screen ADD COLUMN {col} {defn}")
            except Exception:
                pass

        # Self-healing ticks dedup: older DBs whose ticks table predates the
        # UNIQUE(date,ticker,time) constraint never deduped (INSERT OR IGNORE/REPLACE
        # had no constraint to fire against → 3x+ row bloat). Enforce it once. Skipped
        # on every normal boot when a unique index already covers the key (the
        # table-level autoindex on fresh installs, or this one), so no per-boot cost.
        already_unique = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='index' AND tbl_name='ticks' "
            "AND (name='idx_ticks_unique' OR "
            "     (sql IS NULL AND name LIKE 'sqlite_autoindex_ticks%'))"
        ).fetchone()
        if not already_unique:
            conn.execute(
                "DELETE FROM ticks WHERE id NOT IN "
                "(SELECT MIN(id) FROM ticks GROUP BY date, ticker, time)"
            )
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_ticks_unique "
                "ON ticks(date, ticker, time)"
            )
            print("[screener/db] ticks deduped + unique index created")
    print("[screener/db] Tables initialized.")


def insert_ticks(rows: list):
    if not rows:
        return 0
    with get_conn() as conn:
        # OR REPLACE + UNIQUE(date,ticker,time): re-scraping the same minute updates
        # in place instead of appending a duplicate (the old OR IGNORE never fired
        # because idx_ticks was non-unique, which 3x-inflated the table).
        conn.executemany("""
            INSERT OR REPLACE INTO ticks (date, ticker, time, price, volume, tick_type)
            VALUES (:date, :ticker, :time, :price, :volume, :tick_type)
        """, rows)
    return len(rows)


def get_ticks(date: str, ticker: str) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM ticks WHERE date=? AND ticker=? ORDER BY time",
            (date, ticker)
        ).fetchall()
    return [dict(r) for r in rows]


def upsert_daily_screen(row: dict):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO daily_screen
                (date, ticker, close, volume, avg_vol_20d, vol_ratio,
                 vwap, delta, cum_delta, signal, consec_up)
            VALUES
                (:date, :ticker, :close, :volume, :avg_vol_20d, :vol_ratio,
                 :vwap, :delta, :cum_delta, :signal, :consec_up)
            ON CONFLICT(date, ticker) DO UPDATE SET
                close=excluded.close, volume=excluded.volume,
                avg_vol_20d=excluded.avg_vol_20d, vol_ratio=excluded.vol_ratio,
                vwap=excluded.vwap, delta=excluded.delta,
                cum_delta=excluded.cum_delta, signal=excluded.signal,
                consec_up=excluded.consec_up,
                updated_at=datetime('now','localtime')
        """, row)


def get_screen_results(date: str) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM daily_screen WHERE date=? ORDER BY vol_ratio DESC", (date,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_avg_vol_from_db(ticker: str, before_date: str, days: int = 20):
    with get_conn() as conn:
        row = conn.execute(
            """SELECT AVG(volume) as avg_vol FROM daily_screen
               WHERE ticker=? AND date < ? ORDER BY date DESC LIMIT ?""",
            (ticker, before_date, days)
        ).fetchone()
    return int(row['avg_vol']) if row and row['avg_vol'] else None


def log_run(run_type: str, tickers_ok: int, tickers_err: int, duration_s: float, notes: str = ''):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO screen_run_log (run_type, tickers_ok, tickers_err, duration_s, notes) VALUES (?,?,?,?,?)",
            (run_type, tickers_ok, tickers_err, duration_s, notes)
        )


def get_run_log(limit: int = 20) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM screen_run_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def log_trade_alert(ticker: str, trade_id: int, alert_type: str, message: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO trade_alert_log (ticker, trade_id, alert_type, message) VALUES (?,?,?,?)",
            (ticker, trade_id, alert_type, message)
        )
