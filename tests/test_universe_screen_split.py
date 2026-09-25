"""Universe-screen split (docs/research_programs/P-M/universe_screen/screen_split.py, D-058).

The in - out difference test is an OLS dummy regression with CR1 month-clustered errors. Shown on
synthetic data (no DB): its point estimate is the plain difference in means, and under a null with
month-level shocks it rejects close to its nominal 5%.
"""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SPLIT = ROOT / "docs" / "research_programs" / "P-M" / "universe_screen" / "screen_split.py"


@pytest.fixture(scope="module")
def ss():
    spec = importlib.util.spec_from_file_location("screen_split", SPLIT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_difference_is_the_difference_in_means(ss):
    rng = np.random.default_rng(0)
    months = rng.integers(0, 60, 3000)
    dummy = rng.random(3000) < 0.4
    y = 0.01 * dummy + rng.normal(0, 0.05, 3000)
    b, _ = ss.diff_t_month(y, dummy, months)
    assert b == pytest.approx(100 * (y[dummy].mean() - y[~dummy].mean()))


def test_month_clustered_difference_has_nominal_size(ss):
    rejects = 0
    for k in range(200):
        rng = np.random.default_rng(k)
        months = rng.integers(0, 60, 2000)
        dummy = rng.random(2000) < 0.4
        shock = rng.normal(0, 1, 60)[months]
        y = rng.normal(0, 0.05, 2000) + 0.02 * shock + 0.01 * dummy * rng.normal(0, 1, 60)[months]
        rejects += abs(ss.diff_t_month(y, dummy, months)[1]) > 1.96
    assert rejects / 200 < 0.10


def test_filters_are_the_predeclared_three(ss):
    assert set(ss.FILTERS) == {"P200", "A5", "P200+A5"}
    assert ss.DATA_CUTOFF == "2026-09-16"
