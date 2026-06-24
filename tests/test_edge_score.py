"""Tests for engine/edge_score.py — composite edge score (5 weighted terms)."""
import pytest

from engine.edge_score import (
    compute_edge,
    edge_breakdown,
    norm_expectancy,
    norm_consistency,
    norm_flow,
    norm_regime,
    norm_technical,
    MAX_EXPECTANCY_PCT,
    DEFAULT_REGIME_FIT,
    W_EXPECTANCY, W_CONSISTENCY, W_FLOW, W_REGIME, W_TECHNICAL,
)


class TestNormExpectancy:
    def test_zero(self):
        assert norm_expectancy(0.0) == 0.0

    def test_negative_clamps_to_zero(self):
        assert norm_expectancy(-1.0) == 0.0

    def test_mid(self):
        assert norm_expectancy(MAX_EXPECTANCY_PCT / 2) == 0.5

    def test_capped(self):
        assert norm_expectancy(MAX_EXPECTANCY_PCT * 2) == 1.0

    def test_none_is_zero(self):
        assert norm_expectancy(None) == 0.0


class TestNormConsistency:
    def test_floor(self):
        assert norm_consistency(30.0) == 0.0

    def test_ceiling(self):
        assert norm_consistency(100.0) == 1.0

    def test_mid(self):
        assert norm_consistency(65.0) == 0.5

    def test_none_is_zero(self):
        assert norm_consistency(None) == 0.0


class TestNormFlow:
    def test_neutral(self):
        assert norm_flow(0) == 0.5

    def test_bullish(self):
        assert norm_flow(4) == 0.75

    def test_bearish(self):
        assert norm_flow(-4) == 0.25

    def test_extremes(self):
        assert norm_flow(8) == 1.0
        assert norm_flow(-8) == 0.0

    def test_none_is_zero(self):
        assert norm_flow(None) == 0.0


class TestNormRegime:
    def test_bull(self):
        assert norm_regime('BULL') == 1.0

    def test_sideways(self):
        assert norm_regime('SIDEWAYS') == 0.5

    def test_bear(self):
        assert norm_regime('BEAR') == 0.0

    def test_unknown_uses_default(self):
        assert norm_regime('WEIRD') == DEFAULT_REGIME_FIT

    def test_none_uses_default(self):
        assert norm_regime(None) == DEFAULT_REGIME_FIT


class TestNormTechnical:
    def test_min(self):
        assert norm_technical(1) == 0.0

    def test_max(self):
        assert norm_technical(4) == 1.0

    def test_mid(self):
        assert norm_technical(2.5) == 0.5

    def test_none_is_zero(self):
        assert norm_technical(None) == 0.0

    def test_below_min_is_zero(self):
        assert norm_technical(0) == 0.0


class TestComputeEdge:
    def test_weights_sum_to_one(self):
        assert W_EXPECTANCY + W_CONSISTENCY + W_FLOW + W_REGIME + W_TECHNICAL == 1.0

    def test_all_max_is_one(self):
        edge = compute_edge(expectancy_pct=MAX_EXPECTANCY_PCT, consistency_pct=100,
                            flow_score=8, regime='BULL', technical_votes=4)
        assert edge == 1.0

    def test_all_min_is_zero(self):
        edge = compute_edge(expectancy_pct=-1, consistency_pct=0,
                            flow_score=-8, regime='BEAR', technical_votes=1)
        assert edge == 0.0

    def test_good_combo_above_085(self):
        edge = compute_edge(expectancy_pct=2.5, consistency_pct=90,
                            flow_score=5, regime='BULL', technical_votes=4)
        assert edge >= 0.85

    def test_all_none_is_regime_default_only(self):
        # only norm_regime returns non-zero on None → W_REGIME * DEFAULT_REGIME_FIT
        assert compute_edge() == round(W_REGIME * DEFAULT_REGIME_FIT, 4)

class TestBreakdown:
    def test_keys_and_edge_match_compute_edge(self):
        args = dict(expectancy_pct=2.5, consistency_pct=90,
                    flow_score=5, regime='BULL', technical_votes=4)
        b = edge_breakdown(**args)
        assert set(b) == {'expectancy', 'consistency', 'flow', 'regime', 'technical', 'edge'}
        assert b['edge'] == compute_edge(**args)

    def test_contributions_sum_to_edge(self):
        b = edge_breakdown(expectancy_pct=1.5, consistency_pct=65,
                           flow_score=0, regime='SIDEWAYS', technical_votes=2)
        terms = sum(b[k] for k in ('expectancy', 'consistency', 'flow', 'regime', 'technical'))
        assert round(terms, 4) == b['edge']

    def test_each_term_capped_by_weight(self):
        b = edge_breakdown(expectancy_pct=99, consistency_pct=999,
                           flow_score=99, regime='BULL', technical_votes=99)
        assert b['expectancy'] == W_EXPECTANCY
        assert b['flow'] == W_FLOW
        assert b['regime'] == W_REGIME


class TestComputeEdgeBounded:
    def test_bounded_for_arbitrary_inputs(self):
        for exp in (-5, 0, 1.5, 99):
            for cons in (0, 50, 200):
                for flow in (-99, 0, 99):
                    for reg in ('BULL', 'BEAR', None, 'X'):
                        for v in (0, 2, 9):
                            e = compute_edge(exp, cons, flow, reg, v)
                            assert 0.0 <= e <= 1.0
