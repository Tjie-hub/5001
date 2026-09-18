"""The weekly MTF gate as a causal per-bar mask must BE the live gate.

If engine/filters_mtf.py and engine/indicators.calc_weekly_trend ever diverge,
every rule-parity claim built on wf_edge_rule is void — a strategy would be
admitted on evidence measured under a rule production does not run, which is
finding L-1 reintroduced one level deeper.
"""
import numpy as np
import pandas as pd
import pytest

from engine.filters_mtf import (weekly_mtf_mask, weekly_mtf_filter,
                                clear_mask_cache, WARMUP_BARS, MIN_BARS)
from engine.indicators import calc_weekly_trend, clear_indicator_cache


def _series(n, seed=0, drift=0.0006, vol=0.012, start="2022-01-03"):
    rng = np.random.default_rng(seed)
    close = 1000 * np.cumprod(1 + drift + rng.normal(0, vol, n))
    dates = pd.bdate_range(start, periods=n)
    return pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"),
        "open": close * 0.998, "high": close * 1.01,
        "low": close * 0.99, "close": close,
        "volume": np.full(n, 1_000_000.0),
    })


class TestEquivalence:

    @pytest.mark.parametrize("seed,drift", [(1, 0.0008), (2, -0.0008), (3, 0.0)])
    def test_matches_the_live_gate_bar_for_bar(self, seed, drift):
        df = _series(700, seed=seed, drift=drift)
        mask = weekly_mtf_mask(df)
        mismatches = []
        for i in range(90, len(df), 7):
            clear_indicator_cache()
            live = calc_weekly_trend(df.iloc[:i + 1])[0]
            if bool(mask.iloc[i]) != live:
                mismatches.append((i, df["date"].iloc[i], live, bool(mask.iloc[i])))
        assert not mismatches, mismatches[:5]

    def test_matches_across_the_soft_pass_boundary(self):
        """The gate soft-passes below 100 bars and below 22 weeks; the mask must
        reproduce those exemptions, not invent a stricter rule."""
        df = _series(200, seed=9)
        mask = weekly_mtf_mask(df)
        for i in range(0, 140):
            clear_indicator_cache()
            assert bool(mask.iloc[i]) == calc_weekly_trend(df.iloc[:i + 1])[0], i

    def test_short_frames_pass(self):
        df = _series(MIN_BARS - 1, seed=4)
        assert weekly_mtf_mask(df).all()

    def test_empty_frame_is_handled(self):
        out = weekly_mtf_mask(pd.DataFrame({"date": [], "close": []}))
        assert len(out) == 0


class TestCausality:

    def test_mask_value_at_i_is_unchanged_by_later_bars(self):
        """No future bar may influence a decision. Truncating the frame after i
        must not change mask[i]."""
        df = _series(500, seed=11)
        full = weekly_mtf_mask(df)
        for i in (150, 220, 300, 410, 499):
            trunc = weekly_mtf_mask(df.iloc[:i + 1])
            assert bool(trunc.iloc[i]) == bool(full.iloc[i]), i

    def test_mask_is_aligned_to_the_frame_index(self):
        df = _series(300, seed=5).iloc[50:].reset_index(drop=True)
        m = weekly_mtf_mask(df)
        assert list(m.index) == list(df.index)


class TestFilterPlumbing:

    def test_memoised_filter_agrees_with_the_mask(self):
        df = _series(400, seed=6)
        clear_mask_cache()
        a = weekly_mtf_filter(df)
        b = weekly_mtf_filter(df)          # cache hit
        assert a.equals(weekly_mtf_mask(df))
        assert b.equals(a)

    def test_apply_filters_accepts_it(self):
        from engine.strategies import apply_filters
        from engine.filters_mtf import WEEKLY_MTF_FILTER
        df = _series(400, seed=7)
        mask = apply_filters(df, [WEEKLY_MTF_FILTER])
        assert mask.dtype == bool and len(mask) == len(df)

    def test_warmup_exceeds_the_gate_requirement(self):
        """160 bars must clear 100 bars AND ~25 weeks, or the parity run would
        silently measure 'gate mostly soft-passing'."""
        assert WARMUP_BARS >= MIN_BARS
        df = _series(WARMUP_BARS, seed=8)
        weeks = pd.to_datetime(df["date"]).dt.to_period("W").nunique()
        assert weeks >= 25, weeks


class TestGateActuallyBinds:

    def test_gate_blocks_in_a_downtrend_and_passes_in_an_uptrend(self):
        up = weekly_mtf_mask(_series(600, seed=21, drift=0.0015, vol=0.006))
        down = weekly_mtf_mask(_series(600, seed=21, drift=-0.0015, vol=0.006))
        tail = slice(200, None)
        assert up[tail].mean() > 0.8, up[tail].mean()
        assert down[tail].mean() < 0.2, down[tail].mean()


class TestRuleIdentityIntegration:

    def test_the_gate_name_matches_rule_identity(self):
        from engine.rule_identity import GATE_WEEKLY_MTF, live_gates
        assert GATE_WEEKLY_MTF == "weekly_mtf_trend"
        assert live_gates("momentum") == (GATE_WEEKLY_MTF,)
        assert live_gates("Liquidity Sweep") == ()


class TestGateIsAPureRestriction:
    """The weekly gate can only REMOVE candidate entries, never create one.

    This is what makes the parity study's outcome partly deducible: a strategy
    that could not reach the n>=20 evidence floor under the bare rule cannot
    reach it under the gated rule either, holding warm-up constant. It is also
    the safety property that makes running the gate in production strictly
    conservative relative to the researched rule.
    """

    @pytest.mark.parametrize("strategy_name", [
        "strategy_nr7_breakout",
        "strategy_trend_following_breakout",
        "strategy_inside_bar_breakout",
        "strategy_orb",
    ])
    def test_gated_run_never_has_more_trades_than_the_bare_run(self, strategy_name):
        from engine import strategies as st
        from engine.filters_mtf import WEEKLY_MTF_FILTER, clear_mask_cache
        fn = getattr(st, strategy_name)
        for seed in (31, 32, 33):
            df = _series(900, seed=seed, drift=0.0007, vol=0.014)
            clear_mask_cache()
            bare = fn(df, capital=50_000_000, filters=None)
            clear_mask_cache()
            gated = fn(df, capital=50_000_000, filters=[WEEKLY_MTF_FILTER])
            assert len(gated["trades"]) <= len(bare["trades"]), (
                f"{strategy_name} seed={seed}: gated {len(gated['trades'])} > "
                f"bare {len(bare['trades'])}")

    def test_every_gated_entry_is_also_a_bare_entry(self):
        """Not merely fewer — the gated trade set is a SUBSET of the bare set,
        so the gate reweights nothing and invents nothing."""
        from engine import strategies as st
        from engine.filters_mtf import WEEKLY_MTF_FILTER, clear_mask_cache
        df = _series(900, seed=41, drift=0.0006, vol=0.013)
        clear_mask_cache()
        bare = {t.entry_date for t in st.strategy_nr7_breakout(df)["trades"]}
        clear_mask_cache()
        gated = {t.entry_date for t in
                 st.strategy_nr7_breakout(df, filters=[WEEKLY_MTF_FILTER])["trades"]}
        assert gated <= bare, sorted(gated - bare)

    def test_the_gate_actually_removes_something(self):
        """A restriction that never binds would make the parity run meaningless."""
        from engine import strategies as st
        from engine.filters_mtf import WEEKLY_MTF_FILTER, clear_mask_cache
        removed = 0
        for seed in (51, 52, 53, 54):
            df = _series(900, seed=seed, drift=0.0002, vol=0.016)
            clear_mask_cache()
            bare = len(st.strategy_nr7_breakout(df)["trades"])
            clear_mask_cache()
            gated = len(st.strategy_nr7_breakout(df, filters=[WEEKLY_MTF_FILTER])["trades"])
            removed += bare - gated
        assert removed > 0
