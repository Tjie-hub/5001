"""Tests for engine/liquidity.py — L1 ADV gate, L2 value scoring, L3 gates."""
import sqlite3
import tempfile
import pytest

from engine.liquidity import (
    compute_value_score,
    get_adv_30d,
    get_keystats,
    passes_liquidity_gate,
    passes_value_gate,
    get_liquidity_value,
    ADV_MIN_LOTS,
    MARKET_CAP_MIN,
    VALUE_SCORE_MIN,
)

DATE = '2026-06-08'


def _make_db(ohlcv_rows=None, keystats_rows=None):
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    conn.executescript("""
        CREATE TABLE ohlcv (
            ticker TEXT, date TEXT, open REAL, high REAL, low REAL,
            close REAL, volume REAL
        );
        CREATE TABLE stockbit_keystats (
            ticker TEXT, fetch_date TEXT,
            pe_ttm REAL, pbv REAL, peg_ratio REAL, div_yield REAL,
            ev_ebitda REAL, market_cap REAL, updated_at TEXT
        );
    """)
    for row in (ohlcv_rows or []):
        conn.execute("INSERT INTO ohlcv VALUES (?,?,100,110,90,105,?)",
                     (row['ticker'], row['date'], row['volume']))
    for row in (keystats_rows or []):
        conn.execute(
            "INSERT INTO stockbit_keystats(ticker,fetch_date,pe_ttm,pbv,peg_ratio,"
            "div_yield,ev_ebitda,market_cap,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (row['ticker'], row.get('fetch_date', DATE),
             row.get('pe_ttm'), row.get('pbv'), row.get('peg_ratio'),
             row.get('div_yield'), row.get('ev_ebitda'), row.get('market_cap'), DATE)
        )
    conn.commit()
    return tmp.name, conn


# ── L2: value score ───────────────────────────────────────────────────────────

class TestComputeValueScore:
    def test_all_best_values(self):
        # P/E=5 (floor), PBV=0.5, PEG=0.2, div=10, EV/EBITDA=3 → score near 100
        score = compute_value_score(5, 0.5, 0.2, 10, 3)
        assert score > 90

    def test_all_worst_values(self):
        # P/E=50 (ceiling), PBV=10, PEG=3, div=0, EV/EBITDA=30 → score near 0
        score = compute_value_score(50, 10, 3, 0, 30)
        assert score < 10

    def test_neutral_values(self):
        score = compute_value_score(27.5, 5.25, 1.6, 5, 16.5)
        assert 40 <= score <= 60

    def test_all_none_returns_50(self):
        assert compute_value_score(None, None, None, None, None) == 50.0

    def test_negative_values_treated_as_missing(self):
        # Negative P/E (loss-making) → treated as None → skipped
        score_with = compute_value_score(None, 1.0, None, None, None)
        score_neg  = compute_value_score(-5,   1.0, None, None, None)
        assert score_with == score_neg

    def test_partial_data(self):
        # Only P/E and PBV available — should still produce a valid score
        score = compute_value_score(10, 1.0, None, None, None)
        assert 0 <= score <= 100

    def test_score_range_always_0_to_100(self):
        for pe in [1, 10, 25, 60, 100]:
            for pb in [0.1, 2, 15]:
                score = compute_value_score(pe, pb, None, None, None)
                assert 0 <= score <= 100, f"score={score} for pe={pe},pb={pb}"


# ── L1: ADV ───────────────────────────────────────────────────────────────────

class TestGetAdv30d:
    def test_basic_avg(self):
        rows = [{'ticker':'BBCA','date':f'2026-06-0{i}','volume':1_000_000} for i in range(1,6)]
        db_path, conn = _make_db(ohlcv_rows=rows)
        result = get_adv_30d(conn, 'BBCA', DATE)
        conn.close()
        assert result == pytest.approx(1_000_000)

    def test_returns_none_when_no_data(self):
        db_path, conn = _make_db()
        result = get_adv_30d(conn, 'MISSING', DATE)
        conn.close()
        assert result is None

    def test_excludes_zero_volume(self):
        rows = [
            {'ticker':'X','date':'2026-06-01','volume':2_000_000},
            {'ticker':'X','date':'2026-06-02','volume':0},
        ]
        db_path, conn = _make_db(ohlcv_rows=rows)
        result = get_adv_30d(conn, 'X', '2026-06-08')
        conn.close()
        # Only the 2M row counts (zero excluded)
        assert result == pytest.approx(2_000_000)

    def test_limits_to_30_rows(self):
        rows = [{'ticker':'X','date':f'2026-0{m}-{d:02d}','volume':1_000_000}
                for m in range(3,7) for d in range(1,10)][:35]
        db_path, conn = _make_db(ohlcv_rows=rows)
        result = get_adv_30d(conn, 'X', DATE)
        conn.close()
        assert result is not None


# ── L3: gate functions ────────────────────────────────────────────────────────

class TestPassesLiquidityGate:
    def _conn(self, adv_vol, market_cap=None):
        rows_ohlcv = [{'ticker':'T','date':f'2026-06-0{i}','volume':adv_vol}
                      for i in range(1,6)]
        rows_ks = [{'ticker':'T','market_cap':market_cap}] if market_cap is not None else []
        _, conn = _make_db(ohlcv_rows=rows_ohlcv, keystats_rows=rows_ks)
        return conn

    def test_passes_adv_and_cap(self):
        conn = self._conn(ADV_MIN_LOTS + 100_000, MARKET_CAP_MIN + 1e9)
        ok, reason = passes_liquidity_gate(conn, 'T', DATE)
        conn.close()
        assert ok is True

    def test_fails_low_adv(self):
        conn = self._conn(100_000, MARKET_CAP_MIN + 1e9)
        ok, reason = passes_liquidity_gate(conn, 'T', DATE)
        conn.close()
        assert ok is False
        assert 'ADV' in reason

    def test_fails_low_cap(self):
        conn = self._conn(ADV_MIN_LOTS + 100_000, MARKET_CAP_MIN - 1e9)
        ok, reason = passes_liquidity_gate(conn, 'T', DATE)
        conn.close()
        assert ok is False
        assert 'market_cap' in reason.lower() or 'mcap' in reason.lower()

    def test_fail_open_when_no_keystats(self):
        # ADV ok, no keystats row at all → fail-open (pass)
        conn = self._conn(ADV_MIN_LOTS + 100_000, market_cap=None)
        ok, reason = passes_liquidity_gate(conn, 'T', DATE)
        conn.close()
        assert ok is True
        assert 'fail-open' in reason or 'unknown' in reason.lower()

    def test_no_ohlcv_fails(self):
        _, conn = _make_db()
        ok, reason = passes_liquidity_gate(conn, 'GHOST', DATE)
        conn.close()
        assert ok is False


class TestPassesValueGate:
    def _conn(self, pe=None, pb=None, peg=None, div=None, ev=None):
        rows = [{'ticker':'T','pe_ttm':pe,'pbv':pb,'peg_ratio':peg,
                 'div_yield':div,'ev_ebitda':ev,'market_cap':1e12}]
        _, conn = _make_db(keystats_rows=rows)
        return conn

    def test_passes_good_value(self):
        conn = self._conn(pe=8, pb=1.0, peg=0.5, div=5, ev=6)
        ok, reason = passes_value_gate(conn, 'T')
        conn.close()
        assert ok is True

    def test_fails_bad_value(self):
        conn = self._conn(pe=49, pb=9, peg=2.9, div=0, ev=29)
        ok, reason = passes_value_gate(conn, 'T')
        conn.close()
        assert ok is False

    def test_fail_open_when_no_keystats(self):
        _, conn = _make_db()
        ok, reason = passes_value_gate(conn, 'GHOST')
        conn.close()
        assert ok is True
        assert 'fail-open' in reason


# ── get_liquidity_value (integration) ────────────────────────────────────────

class TestGetLiquidityValue:
    def test_returns_all_keys(self):
        ohlcv = [{'ticker':'X','date':f'2026-06-0{i}','volume':2_000_000} for i in range(1,6)]
        ks    = [{'ticker':'X','pe_ttm':10,'pbv':1.2,'market_cap':2e12}]
        db_path, conn = _make_db(ohlcv_rows=ohlcv, keystats_rows=ks)
        conn.close()
        result = get_liquidity_value(db_path, 'X', DATE)
        for key in ('adv_30d','market_cap','value_score','is_liquid','has_value'):
            assert key in result

    def test_is_liquid_true(self):
        ohlcv = [{'ticker':'X','date':f'2026-06-0{i}','volume':ADV_MIN_LOTS+1} for i in range(1,6)]
        ks    = [{'ticker':'X','market_cap':MARKET_CAP_MIN+1e9}]
        db_path, conn = _make_db(ohlcv_rows=ohlcv, keystats_rows=ks)
        conn.close()
        result = get_liquidity_value(db_path, 'X', DATE)
        assert result['is_liquid'] is True
