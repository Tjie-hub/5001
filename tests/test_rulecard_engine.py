"""Rule Card statistics, card validation and the central verdict (D-055).

The numbers asserted here are the ones quoted in
docs/research_notes/RULE_FIRST_PROTOCOL_2026-09-24.md (R3, R5); if a test here
changes, that document is stale.
"""
import copy
import math
from pathlib import Path

import numpy as np
import pytest

from research.rulecard import card as cardmod
from research.rulecard import checks, engine, evaluate, synthetic
from research.rulecard.stats import (minimum_bayes_factor_p_null, mr_test,
                                     needed_effect, nw_t)

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "docs" / "research_notes" / "RULE_CARD_TEMPLATE.yaml"


def valid_card():
    return {
        "id": "RC-TEST", "title": "test rule", "tier": "R",
        "tier_justification": "two published replications incl. one EM",
        "mechanism": {"statement": "s", "loser": "l", "barrier": "b", "side": "avoid"},
        "literature": [{"cite": "A", "tag": "V"}, {"cite": "B", "tag": "V2"}],
        "external_prior": {"series": "JKP EM ex-IDN", "sign": "negative", "t": -2.1},
        "signal": {"script": "rule.py", "description": "d", "parameter_source": "paper",
                   "formation": "month_end"},
        "universe": {"preset": "liquid_idx_v1"},
        "portfolio": {"bucketing": "decile", "use": "avoid", "use_end": "high"},
        "estimand": {"primary_kind": "top_minus_bottom", "predicted_sign": "negative", "nw_lag": 3},
        "deployment": {"predicted_sign": "negative", "hurdle_t": 2.0},
        "power": {"sigma_planning": 3.47, "sigma_source": "Julianto-Ekaputra 2020",
                  "sigma_noise_floor": 3.0, "literature_effect": 1.6, "haircut": 0.5, "n_months": 155},
        "monotonicity": {"shape": "tail", "shape_justification": "lottery demand acts in the tail",
                         "alpha": 0.10, "n_boot": 400},
        "fingerprints": [{"name": "adv_tercile", "predicted_sign": "negative"}],
        "windows": {"split": "2017-01-01"}, "costs": {"round_trip_pct": 0.60},
        "survivorship_direction": "conservative", "kill_rule": "k", "family_mapping": "{X1}",
        "trials": {"n_trials": 1},
    }


# ── stats: the protocol's own numbers ────────────────────────────────────────────────

def test_power_numbers_match_protocol_r5():
    assert needed_effect(2.0, 3.5, 155) == pytest.approx(0.799, abs=1e-3)
    assert needed_effect(2.0, 0.75, 155) == pytest.approx(0.171, abs=1e-3)
    assert needed_effect(2.0, 3.5, 67) == pytest.approx(1.215, abs=1e-3)
    assert needed_effect(3.0, 3.5, 155) == pytest.approx(1.080, abs=1e-3)


def test_minimum_bayes_factor_table_matches_protocol_r3():
    assert minimum_bayes_factor_p_null(2.0, 0.5) == pytest.approx(0.119, abs=1e-3)
    assert minimum_bayes_factor_p_null(2.0, 0.1) == pytest.approx(0.549, abs=1e-3)
    assert minimum_bayes_factor_p_null(3.0, 0.1) == pytest.approx(0.091, abs=1e-3)


def test_nw_t_lag0_is_the_iid_t_with_population_variance():
    x = np.random.default_rng(1).normal(0.3, 1.0, 200)
    assert nw_t(x, 0) == pytest.approx(x.mean() / math.sqrt(x.var() / len(x)))


def test_nw_t_matches_remeasure_v2_estimator():
    # remeasure_v2.nw_t, the estimator behind the D-053 re-measurement
    def ref(a, L=3):
        a = np.asarray(a, float); n = len(a); d = a - a.mean()
        v = d @ d / n
        for k in range(1, L + 1):
            v += 2 * (1 - k / (L + 1)) * (d[k:] @ d[:-k]) / n
        return a.mean() / np.sqrt(v / n)
    x = np.random.default_rng(2).normal(0.1, 1.0, 150)
    assert nw_t(x, 3) == pytest.approx(ref(x, 3))


def test_mr_test_separates_graded_from_flat():
    rng = np.random.default_rng(4)
    graded = np.arange(5) * 0.5 + rng.normal(0, 1.0, (150, 5))
    flat = rng.normal(0, 1.0, (150, 5))
    assert mr_test(graded, "increasing", 500)["p"] < 0.05
    assert mr_test(graded[:, ::-1], "decreasing", 500)["p"] < 0.05
    assert mr_test(flat, "increasing", 500)["p"] > 0.10


# ── card validation ──────────────────────────────────────────────────────────────────

def test_blank_template_is_not_admissible():
    card = cardmod.load(TEMPLATE)
    with pytest.raises(cardmod.CardError):
        cardmod.validate(card, strict=False)


def test_valid_card_passes_strict_and_reports_power():
    table = cardmod.validate(valid_card(), strict=True)
    assert table["admissible"] and table["needed_effect_80pct"] == pytest.approx(0.792, abs=1e-3)


@pytest.mark.parametrize("mutate, needle", [
    (lambda c: c.update(literature=[{"cite": "A", "tag": "M"}, {"cite": "B", "tag": "M"}]), "tagged V or V2"),
    (lambda c: c.update(hurdle={"t_min": 1.65}), "below the tier-R floor"),
    (lambda c: c["monotonicity"].pop("shape_justification"), "shape_justification"),
    (lambda c: c["portfolio"].update(bucketing="flag"), "flag bucketing has no top/bottom"),
    (lambda c: c.update(tier="X"), "tier must be R or N"),
])
def test_invalid_cards_list_the_problem(mutate, needle):
    c = valid_card()
    mutate(c)
    with pytest.raises(cardmod.CardError) as e:
        cardmod.validate(c, strict=False)
    assert any(needle in p for p in e.value.problems)


def test_underpowered_blocks_freeze_but_not_a_dry_run():
    c = valid_card()
    c["power"]["literature_effect"] = 0.8                      # 0.8 x 0.5 = 0.4 < 0.792
    cardmod.validate(c, strict=False)
    with pytest.raises(cardmod.CardError) as e:
        cardmod.validate(c, strict=True)
    assert any("underpowered" in p for p in e.value.problems)


def test_pending_owner_fields_block_freeze_only():
    c = valid_card()
    c["family_mapping"] = "PENDING — Owner call"
    cardmod.validate(c, strict=False)
    with pytest.raises(cardmod.CardError):
        cardmod.validate(c, strict=True)


def test_noise_floor_raises_sigma_and_is_required_at_freeze():
    c = valid_card()
    c["power"]["sigma_noise_floor"] = 6.5                    # our deciles hold ~13 names
    t = cardmod.validate(c, strict=False)
    assert t["sigma"] == 6.5 and not t["admissible"]         # 0.8 < 2.84*6.5/sqrt(155) = 1.48
    c["power"]["sigma_noise_floor"] = None
    with pytest.raises(cardmod.CardError) as e:
        cardmod.validate(c, strict=True)
    assert any("sigma_noise_floor" in p for p in e.value.problems)


def test_tier_n_hurdle_is_three():
    c = valid_card()
    c["tier"] = "N"
    assert cardmod.hurdle_t(c) == 3.0


# ── verdict truth table ──────────────────────────────────────────────────────────────

def _summary(t=-3.0, halves=(-1.0, -0.8), ex25=-0.9, mr_p=0.01, fp=-0.3, dep_t=-2.5):
    w = lambda n, m, tt, dt: {"n": n, "primary_mean": m, "primary_t": tt, "deployment_mean": m,
                              "deployment_t": dt, "uplift_net_mean": 0.1, "turn_book_mean": 0.2}
    return {"windows": {"FULL": w(150, -1.0, t, dep_t), "DISCOVERY": w(80, halves[0], -2, -2),
                        "CONFIRMATION": w(70, halves[1], -2, -2), "EX2025": w(140, ex25, -2, -2)},
            "monotonicity": {"applicable": True, "direction": "decreasing", "alpha": 0.10, "p": mr_p},
            "fingerprints": [{"name": "adv_tercile", "predicted_sign": "negative", "observed": fp}],
            "primary_series": list(np.random.default_rng(0).normal(-1.0, 3.0, 150))}


PASS_CHECKS = [{"code": "LA-1", "check": "prefix_invariance", "status": "PASS"}]


@pytest.mark.parametrize("kw, expected", [
    ({}, "PASS"),
    ({"t": -1.5}, "FAIL"),
    ({"t": 2.5}, "FAIL"),                                     # wrong sign
    ({"halves": (-1.0, 0.2)}, "FAIL"),                        # confirmation half flips
    ({"ex25": 0.1}, "FAIL"),                                  # a 2025-only effect
    ({"mr_p": 0.5}, "FAIL_NOT_MONOTONE"),
    ({"fp": 0.2}, "EFFECT_PRESENT_MECHANISM_UNCONFIRMED"),
    ({"dep_t": -1.0}, "PASS_NOT_DEPLOYABLE"),
])
def test_verdict_truth_table(kw, expected):
    assert evaluate.verdict(valid_card(), _summary(**kw), PASS_CHECKS)["verdict"] == expected


def test_a_miss_on_a_short_sample_is_inconclusive_not_failed():
    summ = _summary(t=-1.5)
    summ["windows"]["FULL"]["n"] = 100                       # plan said 155; 100 < 80%
    assert evaluate.verdict(valid_card(), summ, PASS_CHECKS)["verdict"] == "INCONCLUSIVE_UNDERPOWERED"


def test_any_failed_check_makes_the_run_invalid_not_failed():
    bad = PASS_CHECKS + [{"code": "SPL-1", "check": "split_band", "status": "FAIL"}]
    v = evaluate.verdict(valid_card(), _summary(), bad)
    assert v["verdict"] == "INVALID" and "SPL-1 split_band FAIL" in v["reasons"]


def test_tier_n_needs_t_three():
    c = valid_card()
    c["tier"] = "N"
    assert evaluate.verdict(c, _summary(t=-2.5), PASS_CHECKS)["verdict"] == "FAIL"


def test_mr_direction_follows_card():
    c = valid_card()
    assert evaluate.mr_direction(c) == "decreasing"
    c["estimand"]["primary_kind"] = "bucket_minus_rest"
    c["portfolio"]["use_end"] = "low"
    assert evaluate.mr_direction(c) == "increasing"


# ── end to end on planted effects ────────────────────────────────────────────────────

def _run(shape, effect, card, seed=3):
    pan = engine.Panel(synthetic.make_panel(n_tickers=120, years=6, effect_pct_per_month=effect,
                                            seed=seed, shape=shape))
    cal = engine.calendar(pan.P)
    s = synthetic.z_signal(pan.P)
    months = engine.run_months(pan, s, card, cal)
    plac = engine.run_months(pan, engine.placebo_scores(pan, s, cal), card, cal)
    forms = list(cal["formation"])
    res = [checks.prefix_invariance(pan, synthetic.z_signal, s, forms),
           checks.traded_days_guard(pan, forms),
           checks.predictor_nondegenerate(months, pan, s, forms, "decile"),
           checks.entry_exit_order(months), checks.forward_returns_nontrivial(months),
           checks.split_band(months), checks.placebo([m["primary"] for m in plac if m.get("valid")])]
    summ = evaluate.summarize(months, card)
    return summ, evaluate.verdict(card, summ, res)


def _e2e_card(shape):
    c = valid_card()
    c["power"]["n_months"] = 70                               # the synthetic panel's length
    c["fingerprints"] = []
    c["monotonicity"]["shape"] = shape
    return c


def test_planted_tail_effect_is_recovered_and_passes():
    summ, v = _run("tail", -4.0, _e2e_card("tail"))
    assert v["verdict"] == "PASS", v
    assert summ["windows"]["FULL"]["primary_mean"] == pytest.approx(-3.6, abs=0.8)


def test_no_effect_fails():
    _, v = _run("tail", 0.0, _e2e_card("tail"))
    assert v["verdict"] == "FAIL"


def test_a_pure_step_is_a_pattern_not_a_rule():
    # the whole effect sits in the top decile, nothing graded below it — what a binary
    # chart trigger produces; R6 over the full range classifies it as a pattern
    summ, v = _run("step", -4.0, _e2e_card("full"))
    assert summ["windows"]["FULL"]["primary_t"] < -3
    assert v["verdict"] == "FAIL_NOT_MONOTONE"


# ── data: the D-053 merge, replicated ────────────────────────────────────────────────

def test_merge_extended_adjusts_only_the_backfill_and_prefers_db_rows():
    import pandas as pd
    from research.rulecard.data import merge_extended
    # raw backfill WITH the split jump (100 -> 20 on 2021-06-03): must be adjusted
    d = ["2021-05-28", "2021-05-31", "2021-06-01", "2021-06-02", "2021-06-03", "2021-06-04",
         "2021-06-07", "2021-07-05", "2021-06-01"]
    px = [100.0, 100, 100, 100, 20, 20, 20, 20, 1]
    H = pd.DataFrame({"ticker": ["AAA"] * 8 + ["IHSG"], "date": d, "open": px, "high": px,
                      "low": px, "close": px, "volume": [10.0] * 4 + [50.0] * 4 + [1.0]})
    D = pd.DataFrame({"ticker": ["AAA", "AAA", "IHSG"], "date": ["2021-07-05", "2021-07-06", "2021-07-05"],
                      "open": [20.0, 21, 1], "high": [20.0, 21, 1], "low": [20.0, 21, 1],
                      "close": [20.0, 21, 1], "volume": [50.0, 50, 1]})
    SPL = pd.DataFrame({"ticker": ["AAA"], "date": ["2021-06-03"], "ratio": [5.0]})
    O = merge_extended(H, D, SPL)
    a = O[O.ticker == "AAA"].set_index(O[O.ticker == "AAA"].date.dt.strftime("%Y-%m-%d"))
    assert a.loc["2021-06-01", "close"] == 20.0 and a.loc["2021-06-01", "volume"] == 50.0
    assert a.loc["2021-07-05", "close"] == 20.0          # DB row, not re-adjusted
    assert "IHSG" not in set(O.ticker[O.date >= "2021-07-05"])
    assert O.attrs["split_audit"]["adjusted"] == ["AAA 2021-06-03 x5"]


def test_already_adjusted_backfill_is_not_adjusted_again():
    """DATA-1: yfinance auto_adjust=False still split-adjusts; a second pass fakes a jump."""
    import pandas as pd
    from research.rulecard.data import merge_extended
    H = pd.DataFrame({"ticker": ["HMSP"] * 4, "date": ["2016-06-09", "2016-06-10", "2016-06-14", "2016-06-15"],
                      "open": [3900.0, 3830, 3850, 3860], "high": [3900.0, 3830, 3850, 3860],
                      "low": [3900.0, 3830, 3850, 3860], "close": [3900.0, 3830, 3850, 3860],
                      "volume": [1e7] * 4})
    SPL = pd.DataFrame({"ticker": ["HMSP"], "date": ["2016-06-14"], "ratio": [25.0]})
    O = merge_extended(H, H.iloc[0:0], SPL)
    assert O["close"].tolist() == [3900.0, 3830, 3850, 3860]
    assert O.attrs["split_audit"]["already_adjusted"] == 1 and not O.attrs["split_audit"]["adjusted"]


def test_backfill_scale_glitches_are_dropped_not_traded():
    """DATA-2: MAPI 2018 printed isolated bars at ~1/10 scale between normal bars."""
    import pandas as pd
    from research.rulecard.data import merge_extended
    px = [825.0, 825.0, 82.25, 815.0, 80.5, 810.0, 780.0]
    H = pd.DataFrame({"ticker": "MAPI", "date": pd.bdate_range("2018-04-30", periods=7),
                      "open": px, "high": px, "low": px, "close": px, "volume": 1e7})
    O = merge_extended(H, H.iloc[0:0], pd.DataFrame(columns=["ticker", "date", "ratio"]))
    assert O["close"].tolist() == [825.0, 825.0, 815.0, 810.0, 780.0]
    assert len(O.attrs["split_audit"]["scale_glitches_dropped"]) == 2
