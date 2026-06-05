"""Tests for D2 — /api/dashboard/watchlist aggregation.

Tests the pure engine.dashboard.get_watchlist() function.
BUY WATCH: hammer (>3% intraday bounce) + foreign BUY >5B today + volume >50M
AVOID:     foreign SELL >100B in 3d + YTD drop >20%
WAIT:      hammer + foreign net sell today
"""
import sqlite3
import tempfile
import pytest


DATE = '2026-06-05'


def _make_db(rows_ohlcv=None, rows_broker_flow=None):
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    conn.executescript("""
        CREATE TABLE ohlcv (
            date TEXT, ticker TEXT, open REAL, high REAL, low REAL,
            close REAL, volume INTEGER,
            PRIMARY KEY (date, ticker)
        );
        CREATE TABLE broker_flow (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date TEXT,
            ticker TEXT,
            investor_type TEXT,
            side TEXT,
            lot_volume INTEGER,
            lot_value REAL
        );
    """)
    if rows_ohlcv:
        conn.executemany(
            "INSERT OR IGNORE INTO ohlcv (date,ticker,open,high,low,close,volume) "
            "VALUES (?,?,?,?,?,?,?)",
            rows_ohlcv,
        )
    if rows_broker_flow:
        conn.executemany(
            "INSERT INTO broker_flow (trade_date,ticker,investor_type,side,lot_value) "
            "VALUES (?,?,?,?,?)",
            rows_broker_flow,
        )
    conn.commit()
    conn.close()
    return tmp.name


def _ohlcv(date, ticker, low, close, volume, open_=None):
    """Build an OHLCV row; open_ defaults to just above low."""
    o = open_ if open_ is not None else low * 1.005
    h = close * 1.005
    return (date, ticker, o, h, low, close, volume)


# ── Shape ─────────────────────────────────────────────────────────────────────

def test_watchlist_returns_required_keys():
    db = _make_db()
    from engine.dashboard import get_watchlist
    result = get_watchlist(db, DATE)

    assert set(result.keys()) >= {'date', 'buy_watch', 'avoid', 'wait'}
    assert result['date'] == DATE
    assert isinstance(result['buy_watch'], list)
    assert isinstance(result['avoid'], list)
    assert isinstance(result['wait'], list)


def test_watchlist_empty_db_returns_empty_lists():
    db = _make_db()
    from engine.dashboard import get_watchlist
    result = get_watchlist(db, DATE)

    assert result['buy_watch'] == []
    assert result['avoid'] == []
    assert result['wait'] == []


# ── BUY WATCH ─────────────────────────────────────────────────────────────────

def test_watchlist_buy_watch_appears_with_hammer_and_foreign_buy():
    """BBRI: bounce 3.09%, vol 100M, foreign net buy 6B → in buy_watch."""
    ohlcv = [_ohlcv(DATE, 'BBRI', low=3880, close=4000, volume=100_000_000)]
    flow = [
        (DATE, 'BBRI', 'Asing', 'BUY',  7_000_000_000),
        (DATE, 'BBRI', 'Asing', 'SELL', 1_000_000_000),
    ]
    db = _make_db(rows_ohlcv=ohlcv, rows_broker_flow=flow)
    from engine.dashboard import get_watchlist
    result = get_watchlist(db, DATE)

    tickers = [e['ticker'] for e in result['buy_watch']]
    assert 'BBRI' in tickers

    entry = next(e for e in result['buy_watch'] if e['ticker'] == 'BBRI')
    assert entry['foreign_net_today'] == 6_000_000_000
    assert entry['bounce_pct'] > 3


def test_watchlist_buy_watch_entry_has_all_display_fields():
    ohlcv = [_ohlcv(DATE, 'BBCA', low=8800, close=9100, volume=80_000_000)]
    flow = [(DATE, 'BBCA', 'Asing', 'BUY', 10_000_000_000)]
    db = _make_db(rows_ohlcv=ohlcv, rows_broker_flow=flow)
    from engine.dashboard import get_watchlist
    result = get_watchlist(db, DATE)

    entry = next(e for e in result['buy_watch'] if e['ticker'] == 'BBCA')
    for field in ('close', 'chg_pct', 'bounce_pct', 'foreign_net_today',
                  'foreign_net_3d', 'volume', 'ytd_pct'):
        assert field in entry, f"Missing field: {field}"


def test_watchlist_buy_watch_excluded_when_volume_low():
    """Hammer + foreign buy but volume only 10M (< 50M) → NOT in buy_watch."""
    ohlcv = [_ohlcv(DATE, 'SMGR', low=6200, close=6400, volume=10_000_000)]
    flow = [(DATE, 'SMGR', 'Asing', 'BUY', 8_000_000_000)]
    db = _make_db(rows_ohlcv=ohlcv, rows_broker_flow=flow)
    from engine.dashboard import get_watchlist
    result = get_watchlist(db, DATE)

    assert 'SMGR' not in [e['ticker'] for e in result['buy_watch']]


def test_watchlist_buy_watch_excluded_when_foreign_buy_below_threshold():
    """Hammer + volume OK but foreign net buy only 4B (< 5B) → NOT in buy_watch."""
    ohlcv = [_ohlcv(DATE, 'INDF', low=6500, close=6720, volume=60_000_000)]
    flow = [(DATE, 'INDF', 'Asing', 'BUY', 4_000_000_000)]
    db = _make_db(rows_ohlcv=ohlcv, rows_broker_flow=flow)
    from engine.dashboard import get_watchlist
    result = get_watchlist(db, DATE)

    assert 'INDF' not in [e['ticker'] for e in result['buy_watch']]


# ── AVOID ─────────────────────────────────────────────────────────────────────

def test_watchlist_avoid_appears_with_heavy_foreign_sell_and_ytd_drop():
    """TLKM: YTD -22%, foreign SELL 120B in 3d → in avoid."""
    jan_row = _ohlcv('2026-01-02', 'TLKM', low=3550, close=3600, volume=50_000_000)
    today_row = _ohlcv(DATE, 'TLKM', low=2780, close=2800, volume=30_000_000)
    flow = [
        ('2026-06-03', 'TLKM', 'Asing', 'SELL', 40_000_000_000),
        ('2026-06-04', 'TLKM', 'Asing', 'SELL', 40_000_000_000),
        (DATE,         'TLKM', 'Asing', 'SELL', 40_000_000_000),
    ]
    db = _make_db(rows_ohlcv=[jan_row, today_row], rows_broker_flow=flow)
    from engine.dashboard import get_watchlist
    result = get_watchlist(db, DATE)

    tickers = [e['ticker'] for e in result['avoid']]
    assert 'TLKM' in tickers

    entry = next(e for e in result['avoid'] if e['ticker'] == 'TLKM')
    assert entry['foreign_net_3d'] < -100_000_000_000
    assert entry['ytd_pct'] < -20


def test_watchlist_avoid_excluded_when_ytd_drop_insufficient():
    """Heavy foreign sell but YTD only -5% → NOT in avoid."""
    # ASII: jan=5200, today=4940 → YTD ≈ -5%
    jan_row = _ohlcv('2026-01-02', 'ASII', low=5150, close=5200, volume=50_000_000)
    today_row = _ohlcv(DATE, 'ASII', low=4920, close=4940, volume=40_000_000)
    flow = [
        ('2026-06-03', 'ASII', 'Asing', 'SELL', 40_000_000_000),
        ('2026-06-04', 'ASII', 'Asing', 'SELL', 40_000_000_000),
        (DATE,         'ASII', 'Asing', 'SELL', 40_000_000_000),
    ]
    db = _make_db(rows_ohlcv=[jan_row, today_row], rows_broker_flow=flow)
    from engine.dashboard import get_watchlist
    result = get_watchlist(db, DATE)

    assert 'ASII' not in [e['ticker'] for e in result['avoid']]


# ── WAIT ──────────────────────────────────────────────────────────────────────

def test_watchlist_wait_appears_with_hammer_but_foreign_selling():
    """ASII: bounce 3.85%, vol 80M, foreign net sell today → wait not buy_watch."""
    ohlcv = [_ohlcv(DATE, 'ASII', low=5200, close=5400, volume=80_000_000)]
    flow = [
        (DATE, 'ASII', 'Asing', 'SELL', 20_000_000_000),
        (DATE, 'ASII', 'Asing', 'BUY',   1_000_000_000),
    ]
    db = _make_db(rows_ohlcv=ohlcv, rows_broker_flow=flow)
    from engine.dashboard import get_watchlist
    result = get_watchlist(db, DATE)

    assert 'ASII' in [e['ticker'] for e in result['wait']]
    assert 'ASII' not in [e['ticker'] for e in result['buy_watch']]


# ── Exclusions ────────────────────────────────────────────────────────────────

def test_watchlist_hammer_below_threshold_excluded_from_buy_and_wait():
    """Bounce 0.67% < 3% → excluded from buy_watch and wait regardless of foreign flow."""
    # (3010 - 2990) / 2990 * 100 = 0.67%
    ohlcv = [(DATE, 'BMRI', 3000, 3020, 2990, 3010, 80_000_000)]
    flow = [(DATE, 'BMRI', 'Asing', 'BUY', 10_000_000_000)]
    db = _make_db(rows_ohlcv=ohlcv, rows_broker_flow=flow)
    from engine.dashboard import get_watchlist
    result = get_watchlist(db, DATE)

    all_tickers = (
        [e['ticker'] for e in result['buy_watch']] +
        [e['ticker'] for e in result['wait']]
    )
    assert 'BMRI' not in all_tickers
