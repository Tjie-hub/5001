"""Tests for engine/veto.py — two-tier pre-LLM vetoes + edge-based sizing."""
from engine.veto import apply_vetoes, diagnose, N_MAX, FLOW_DISTRIB_CUT


def _cand(ticker='X', **over):
    """A directionally-clean, statistically-strong candidate (survives in BULL)."""
    c = dict(
        ticker=ticker,
        # directional (all benign)
        flow_score=5, flow_verdict='ACCUMULATING', flow_direction='BULLISH',
        tech_direction='BULLISH', is_mean_reversion=False, has_catalyst=False,
        # statistical (all strong)
        n_trades=30, consistency_pct=85, win_rate=60,
        expectancy_pct=2.2, regime='BULL', technical_votes=4,
    )
    c.update(over)
    return c


class TestBaseline:
    def test_strong_candidate_survives_and_is_sized(self):
        out = apply_vetoes([_cand()], market_regime='BULL')
        assert len(out) == 1
        assert out[0]['edge_score'] > 0.65
        assert out[0]['size_mult'] == round(out[0]['edge_score'], 2)


class TestTierADirectional:
    def test_d1_distributing_no_catalyst_skipped(self):
        c = _cand(flow_score=FLOW_DISTRIB_CUT - 2, flow_verdict='DISTRIBUTING')
        assert apply_vetoes([c], market_regime='BULL') == []

    def test_d1_distributing_with_catalyst_survives(self):
        c = _cand(flow_score=FLOW_DISTRIB_CUT - 2, flow_verdict='DISTRIBUTING',
                  flow_direction='BULLISH', has_catalyst=True)
        assert len(apply_vetoes([c], market_regime='BULL')) == 1

    def test_d2_bearish_tech_no_mr_skipped(self):
        # neutral flow so only d2 can fire
        c = _cand(tech_direction='BEARISH', flow_score=0,
                  flow_verdict='NEUTRAL', flow_direction='NEUTRAL')
        assert apply_vetoes([c], market_regime='BULL') == []

    def test_d2_bearish_tech_mean_reversion_survives(self):
        c = _cand(tech_direction='BEARISH', is_mean_reversion=True,
                  flow_score=0, flow_verdict='NEUTRAL', flow_direction='NEUTRAL')
        assert len(apply_vetoes([c], market_regime='BULL')) == 1

    def test_d3_directions_disagree_skipped(self):
        # tech bullish, flow bearish (but not distributing enough for d1)
        c = _cand(tech_direction='BULLISH', flow_direction='BEARISH', flow_score=-2)
        assert apply_vetoes([c], market_regime='BULL') == []

    def test_d4_market_risk_off_no_catalyst_skipped(self):
        assert apply_vetoes([_cand()], market_regime='BEAR') == []


class TestTierBStatistical:
    def test_s1_insufficient_trades(self):
        assert apply_vetoes([_cand(n_trades=10)], market_regime='BULL') == []

    def test_s1_missing_n_trades(self):
        assert apply_vetoes([_cand(n_trades=None)], market_regime='BULL') == []

    def test_s2_low_consistency(self):
        assert apply_vetoes([_cand(consistency_pct=20)], market_regime='BULL') == []

    def test_s3_low_win_rate(self):
        assert apply_vetoes([_cand(win_rate=30)], market_regime='BULL') == []

    def test_s4_below_edge_floor_bull(self):
        c = _cand(expectancy_pct=0.1, consistency_pct=40, win_rate=40,
                  flow_score=0, regime='SIDEWAYS', technical_votes=2)
        assert apply_vetoes([c], market_regime='BULL') == []


class TestSessionCap:
    def test_cap_trending_three(self):
        cands = [_cand(ticker=f'T{i}') for i in range(5)]
        assert len(apply_vetoes(cands, market_regime='BULL')) == N_MAX['BULL'] == 3

    def test_cap_uncertain_one(self):
        cands = [_cand(ticker=f'T{i}', regime='SIDEWAYS') for i in range(5)]
        assert len(apply_vetoes(cands, market_regime='SIDEWAYS')) == 1

    def test_cap_riskoff_zero(self):
        cands = [_cand(ticker=f'T{i}') for i in range(5)]
        assert apply_vetoes(cands, market_regime='BEAR') == []

    def test_cap_riskoff_catalyst_allows_one(self):
        cands = [_cand(ticker=f'T{i}', has_catalyst=True) for i in range(5)]
        assert len(apply_vetoes(cands, market_regime='BEAR')) == 1

    def test_cap_reduced_by_open_positions(self):
        cands = [_cand(ticker=f'T{i}') for i in range(5)]
        out = apply_vetoes(cands, market_regime='BULL', open_positions_count=2)
        assert len(out) == 1   # BULL cap 3 - 2 open = 1


class TestDiagnose:
    def test_pass_returns_edge_and_none_reason(self):
        edge, reason = diagnose(_cand(), 'BULL')
        assert reason is None
        assert edge > 0.65

    def test_d1_reason(self):
        _, reason = diagnose(_cand(flow_score=-5, flow_verdict='DISTRIBUTING'), 'BULL')
        assert reason.startswith('d1')

    def test_s1_reason(self):
        _, reason = diagnose(_cand(n_trades=5), 'BULL')
        assert reason.startswith('s1')

    def test_s4_reason_carries_edge(self):
        edge, reason = diagnose(
            _cand(expectancy_pct=0.1, consistency_pct=40, win_rate=40,
                  flow_score=0, regime='SIDEWAYS', technical_votes=2), 'BULL')
        assert reason.startswith('s4')
        assert edge is not None and edge < 0.65


class TestSortAndRegression:
    def test_survivors_sorted_desc_by_edge(self):
        # both must clear the 0.65 BULL floor; W weaker than S
        weak = _cand(ticker='W', expectancy_pct=1.5, consistency_pct=70, win_rate=50)
        strong = _cand(ticker='S', expectancy_pct=2.8, consistency_pct=95)
        out = apply_vetoes([weak, strong], market_regime='BULL')
        assert [c['ticker'] for c in out] == ['S', 'W']
        assert out[0]['edge_score'] > out[1]['edge_score']

    def test_inco_regression_distributing_plus_bearish_is_skipped(self):
        # Strong validated history, but DISTRIBUTING flow + bearish technical
        # today and no catalyst → must be skipped (this is the bug that
        # started the whole project).
        inco = _cand(ticker='INCO',
                     n_trades=40, consistency_pct=80, win_rate=55, expectancy_pct=2.5,
                     flow_score=-5, flow_verdict='DISTRIBUTING', flow_direction='BEARISH',
                     tech_direction='BEARISH', is_mean_reversion=False,
                     has_catalyst=False, regime='SIDEWAYS')
        assert apply_vetoes([inco], market_regime='SIDEWAYS') == []
