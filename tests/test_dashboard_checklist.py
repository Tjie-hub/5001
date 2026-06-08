"""Tests for D12 — get_dashboard_checklist() engine function."""
import sqlite3
import tempfile
import pytest

DATE = '2026-06-08'


def _make_db(ohlcv=0, flow=0, signals=0, agents=0):
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    conn.executescript("""
        CREATE TABLE ohlcv (
            ticker TEXT, date TEXT, open REAL, high REAL, low REAL,
            close REAL, volume REAL
        );
        CREATE TABLE broker_flow (
            ticker TEXT, trade_date TEXT, investor_type TEXT,
            side TEXT, lot_value REAL
        );
        CREATE TABLE scheduled_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_time TEXT NOT NULL,
            ticker TEXT NOT NULL,
            flow_verdict TEXT,
            signal_direction TEXT
        );
        CREATE TABLE agent_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_time TEXT NOT NULL,
            ticker TEXT NOT NULL,
            strategy TEXT,
            decision TEXT,
            confidence REAL
        );
    """)
    for i in range(ohlcv):
        conn.execute("INSERT INTO ohlcv VALUES (?,?,100,110,90,105,1000000)",
                     (f'T{i}', DATE))
    for i in range(flow):
        conn.execute("INSERT INTO broker_flow VALUES (?,?,?,?,?)",
                     (f'T{i}', DATE, 'Asing', 'BUY', 1e9))
    for i in range(signals):
        conn.execute("INSERT INTO scheduled_signals(scan_time,ticker,flow_verdict,signal_direction) VALUES (?,?,?,?)",
                     (f'{DATE} 09:00:00', f'T{i}', 'BUY_WATCH', 'BUY'))
    for i in range(agents):
        conn.execute("INSERT INTO agent_decisions(scan_time,ticker,strategy,decision,confidence) VALUES (?,?,?,?,?)",
                     (f'{DATE} 10:00:00', f'T{i}', 'swing', 'BUY', 0.8))
    conn.commit()
    conn.close()
    return tmp.name


def _call(db_path):
    from engine.dashboard import get_dashboard_checklist
    return get_dashboard_checklist(db_path, DATE)


def test_all_empty():
    r = _call(_make_db())
    assert r['date'] == DATE
    assert r['all_done'] is False
    assert len(r['items']) == 4
    assert all(not item['done'] for item in r['items'])


def test_ohlcv_done():
    r = _call(_make_db(ohlcv=5))
    ohlcv_item = next(i for i in r['items'] if i['name'] == 'OHLCV data')
    assert ohlcv_item['done'] is True
    assert ohlcv_item['count'] == 5


def test_all_done_requires_ohlcv_and_signals():
    r = _call(_make_db(ohlcv=3, flow=2, signals=10, agents=4))
    assert r['all_done'] is True


def test_all_done_false_without_signals():
    r = _call(_make_db(ohlcv=3, flow=2, signals=0, agents=4))
    assert r['all_done'] is False


def test_broker_flow_item():
    r = _call(_make_db(flow=7))
    item = next(i for i in r['items'] if i['name'] == 'Broker flow')
    assert item['done'] is True
    assert item['count'] == 7


def test_signals_item():
    r = _call(_make_db(signals=15))
    item = next(i for i in r['items'] if i['name'] == 'Signals scanned')
    assert item['done'] is True
    assert item['count'] == 15


def test_agent_decisions_item():
    r = _call(_make_db(agents=3))
    item = next(i for i in r['items'] if i['name'] == 'Agent reviews')
    assert item['done'] is True
    assert item['count'] == 3


def test_last_scan_populated():
    r = _call(_make_db(signals=2))
    assert r['last_scan'] is not None
    assert r['last_scan'].startswith(DATE)


def test_last_scan_none_when_no_signals():
    r = _call(_make_db())
    assert r['last_scan'] is None


def test_detail_strings():
    r = _call(_make_db(ohlcv=5, signals=12))
    ohlcv_item = next(i for i in r['items'] if i['name'] == 'OHLCV data')
    sig_item   = next(i for i in r['items'] if i['name'] == 'Signals scanned')
    assert '5' in ohlcv_item['detail']
    assert '12' in sig_item['detail']
