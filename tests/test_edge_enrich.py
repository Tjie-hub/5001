"""Tests for engine/edge_enrich.py — candidate enrichment for the veto stage."""
import sqlite3

from engine.edge_enrich import _flow_direction, _is_mean_reversion, enrich_candidate
from engine.wf_edge import ensure_wf_edge_table, save_wf_edge


class TestFlowDirection:
    def test_verdict_distributing_is_bearish(self):
        assert _flow_direction(2, 'DISTRIBUTING') == 'BEARISH'

    def test_verdict_accumulating_is_bullish(self):
        assert _flow_direction(-2, 'ACCUMULATING') == 'BULLISH'

    def test_sign_positive_is_bullish(self):
        assert _flow_direction(3, None) == 'BULLISH'

    def test_sign_negative_is_bearish(self):
        assert _flow_direction(-3, 'NEUTRAL') == 'BEARISH'

    def test_zero_or_none_is_neutral(self):
        assert _flow_direction(0, None) == 'NEUTRAL'
        assert _flow_direction(None, None) == 'NEUTRAL'


class TestMeanReversion:
    def test_reversal_source(self):
        assert _is_mean_reversion(['REVERSAL'], []) is True

    def test_bear_dip_source(self):
        assert _is_mean_reversion(['BEAR_DIP'], []) is True

    def test_mr_strategy(self):
        assert _is_mean_reversion([], ['vwap_reversion']) is True

    def test_momentum_is_not_mr(self):
        assert _is_mean_reversion(['PREMOVER'], ['momentum']) is False


class TestEnrichCandidate:
    def _db(self):
        conn = sqlite3.connect(':memory:')
        conn.execute("CREATE TABLE stockbit_flow (ticker TEXT, trade_date TEXT, "
                     "composite_score INT, verdict TEXT)")
        ensure_wf_edge_table(conn)
        return conn

    def test_joins_flow_and_wf_edge(self):
        conn = self._db()
        conn.execute("INSERT INTO stockbit_flow VALUES ('INCO','2026-06-22',-5,'DISTRIBUTING')")
        save_wf_edge(conn, 'INCO', [{
            'strategy': 'conservative', 'expectancy_pct': 2.5, 'expectancy_rp': 1.0,
            'win_rate': 55.0, 'consistency_pct': 80.0, 'sharpe': 0.5,
            'n_trades': 40, 'windows_tested': 5,
        }], 'now')
        c = enrich_candidate(conn, 'INCO', '2026-06-22',
                             closes=[200 - i for i in range(60)],  # downtrend
                             regime='SIDEWAYS', sources=['BEAR_DIP'])
        assert c['flow_score'] == -5
        assert c['flow_direction'] == 'BEARISH'
        assert c['tech_direction'] == 'BEARISH'
        assert c['is_mean_reversion'] is True
        assert c['has_catalyst'] is False        # empty catalyst table → strict False
        assert c['expectancy_pct'] == 2.5
        assert c['n_trades'] == 40

    def test_missing_wf_edge_leaves_none(self):
        conn = self._db()
        c = enrich_candidate(conn, 'XYZ', '2026-06-22', closes=[], regime='BULL')
        assert c['n_trades'] is None
        assert c['expectancy_pct'] is None
