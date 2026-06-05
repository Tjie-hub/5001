"""Tests for D3 — /api/dashboard/signals aggregation.

Tests the pure engine.dashboard.get_signals_dashboard() function.
Returns last 20 agent_decisions + today's scheduled_signals count by verdict.
"""
import sqlite3
import tempfile
import pytest


DATE = '2026-06-05'


def _make_db(rows_decisions=None, rows_signals=None):
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    conn.executescript("""
        CREATE TABLE agent_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_time TEXT NOT NULL,
            ticker TEXT NOT NULL,
            strategy TEXT NOT NULL,
            quant_score REAL,
            decision TEXT NOT NULL,
            confidence REAL,
            size_hint REAL,
            rationale TEXT,
            overridden INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE scheduled_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_time TEXT NOT NULL,
            ticker TEXT NOT NULL,
            strategies TEXT,
            flow_score INTEGER,
            flow_verdict TEXT,
            smart_money TEXT,
            signal_reasons TEXT,
            signal_direction TEXT DEFAULT 'BUY'
        );
    """)
    if rows_decisions:
        conn.executemany(
            "INSERT INTO agent_decisions "
            "(scan_time,ticker,strategy,quant_score,decision,confidence,size_hint,rationale) "
            "VALUES (?,?,?,?,?,?,?,?)",
            rows_decisions,
        )
    if rows_signals:
        conn.executemany(
            "INSERT INTO scheduled_signals "
            "(scan_time,ticker,flow_verdict,signal_direction) VALUES (?,?,?,?)",
            rows_signals,
        )
    conn.commit()
    conn.close()
    return tmp.name


def _decision(scan_time, ticker, decision='BUY', strategy='swing_trend',
              confidence=0.8, quant_score=75.0, size_hint=1.0, rationale='ok'):
    return (scan_time, ticker, strategy, quant_score, decision, confidence, size_hint, rationale)


# ── Shape ─────────────────────────────────────────────────────────────────────

def test_signals_returns_required_keys():
    db = _make_db()
    from engine.dashboard import get_signals_dashboard
    result = get_signals_dashboard(db, DATE)

    assert set(result.keys()) >= {'date', 'recent_decisions', 'signals_today'}
    assert result['date'] == DATE
    assert isinstance(result['recent_decisions'], list)
    st = result['signals_today']
    assert 'total' in st
    assert 'by_verdict' in st
    assert 'by_direction' in st


def test_signals_empty_db_returns_empty():
    db = _make_db()
    from engine.dashboard import get_signals_dashboard
    result = get_signals_dashboard(db, DATE)

    assert result['recent_decisions'] == []
    assert result['signals_today']['total'] == 0
    assert result['signals_today']['by_verdict'] == {}
    assert result['signals_today']['by_direction'] == {}


# ── agent_decisions ───────────────────────────────────────────────────────────

def test_signals_recent_decisions_ordered_newest_first():
    rows = [
        _decision('2026-06-05 09:00:00', 'BBRI'),
        _decision('2026-06-05 10:00:00', 'BBCA'),
        _decision('2026-06-04 15:00:00', 'TLKM'),
    ]
    db = _make_db(rows_decisions=rows)
    from engine.dashboard import get_signals_dashboard
    result = get_signals_dashboard(db, DATE)

    tickers = [e['ticker'] for e in result['recent_decisions']]
    assert tickers == ['BBCA', 'BBRI', 'TLKM']


def test_signals_recent_decisions_capped_at_20():
    rows = [_decision(f'2026-06-05 {i:02d}:00:00', f'T{i:03d}') for i in range(25)]
    db = _make_db(rows_decisions=rows)
    from engine.dashboard import get_signals_dashboard
    result = get_signals_dashboard(db, DATE)

    assert len(result['recent_decisions']) == 20
    # Newest 20 — T024 through T005
    tickers = [e['ticker'] for e in result['recent_decisions']]
    assert 'T024' == tickers[0]
    assert 'T005' == tickers[-1]


def test_signals_decision_entry_has_required_fields():
    rows = [_decision('2026-06-05 09:00:00', 'BBRI', decision='BUY',
                      confidence=0.85, quant_score=78.5, size_hint=1.5)]
    db = _make_db(rows_decisions=rows)
    from engine.dashboard import get_signals_dashboard
    result = get_signals_dashboard(db, DATE)

    entry = result['recent_decisions'][0]
    for field in ('id', 'scan_time', 'ticker', 'strategy', 'decision',
                  'confidence', 'quant_score', 'size_hint', 'rationale'):
        assert field in entry, f"Missing field: {field}"
    assert entry['ticker'] == 'BBRI'
    assert entry['decision'] == 'BUY'
    assert entry['confidence'] == 0.85


# ── scheduled_signals today ───────────────────────────────────────────────────

def test_signals_today_count_by_verdict():
    """Today's signals grouped by flow_verdict."""
    rows = [
        (f'{DATE} 10:00:00', 'BBRI', 'BUY',     'BUY'),
        (f'{DATE} 10:01:00', 'BBCA', 'BUY',     'BUY'),
        (f'{DATE} 10:02:00', 'TLKM', 'SELL',    'SELL'),
        (f'{DATE} 10:03:00', 'ASII', 'NEUTRAL',  'BUY'),
    ]
    db = _make_db(rows_signals=rows)
    from engine.dashboard import get_signals_dashboard
    result = get_signals_dashboard(db, DATE)

    st = result['signals_today']
    assert st['total'] == 4
    assert st['by_verdict']['BUY'] == 2
    assert st['by_verdict']['SELL'] == 1
    assert st['by_verdict']['NEUTRAL'] == 1


def test_signals_today_count_by_direction():
    """by_direction uses signal_direction column (BUY vs SELL)."""
    rows = [
        (f'{DATE} 10:00:00', 'BBRI', 'BUY',  'BUY'),
        (f'{DATE} 10:01:00', 'TLKM', 'SELL', 'SELL'),
        (f'{DATE} 10:02:00', 'ASII', 'SELL', 'SELL'),
    ]
    db = _make_db(rows_signals=rows)
    from engine.dashboard import get_signals_dashboard
    result = get_signals_dashboard(db, DATE)

    st = result['signals_today']
    assert st['by_direction']['BUY'] == 1
    assert st['by_direction']['SELL'] == 2


def test_signals_today_excludes_other_dates():
    """Signals from other dates do NOT count toward today's totals."""
    rows = [
        (f'{DATE} 10:00:00',    'BBRI', 'BUY',  'BUY'),
        ('2026-06-04 10:00:00', 'TLKM', 'BUY',  'BUY'),  # yesterday — excluded
    ]
    db = _make_db(rows_signals=rows)
    from engine.dashboard import get_signals_dashboard
    result = get_signals_dashboard(db, DATE)

    assert result['signals_today']['total'] == 1
    assert result['signals_today']['by_verdict'].get('BUY') == 1
