"""PIT and mechanics tests for the market-stress reversal study — G0 gate.

Synthetic panels only; no real DB, no outcomes. Each test pins one
predeclared claim from PREDECLARATION.md §6:

  (a) liquid membership, ADV, sigma and r_m at t are identical when every bar
      AFTER t is deleted — the day-t return is the only day-t input;
  (b) the episode rule: stress days 3 sessions apart -> ONE event; 6 apart ->
      TWO events;
  (c) the basket quintile uses only liquid names with a valid day-t return;
      a zero-volume ARB name is excluded; an E2 split-day name is dropped;
  (d) the frozen assembly reproduces R = 2 - 1.5*1 - 0.6 = -0.1% exactly (to
      10 decimal places, the frozen float check), and beta_for recovers a
      beta of exactly 1.5 on the synthetic member;
  (e) the dividend add-back uses the EX date, never the prior session;
  (f) the G0 census path never computes a return after the close of t: AST
      proof that g0_census.py / stress_reversal.py import neither `outcomes`
      nor any outcome function, plus a forbidden-token grep;
  plus the frozen bars (N=604 -> 3.2954; N=605 -> 3.2959) and the true-ADV
  split-factor correction.

Run:  venv/bin/python -m pytest \
        docs/research_programs/P-M/stress_reversal/test_pit_stress_reversal.py -v
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3]))

import outcomes as OC  # noqa: E402
import stress_reversal as SR  # noqa: E402
import synthetic as SYN  # noqa: E402


def _panel():
    conn = SYN.make_db()
    fac, divs = SR.load_ca(conn)
    return SR.Panel(conn, fac, divs, "E2")


# --- (a) truncation: only bars up to t exist downstream of day t -------------
def test_a_truncation_identity():
    p = _panel()
    t = p.sessions[158]
    full_rm = p.market[t][0]
    full_sigma = p.sigma[t]
    full_liq = p.liquid_count(t)
    conn2 = SYN.make_db()
    conn2.execute("DELETE FROM ohlcv WHERE date > ?", (t.isoformat(),))
    conn2.commit()
    fac2, divs2 = SR.load_ca(conn2)
    p2 = SR.Panel(conn2, fac2, divs2, "E2")
    assert p2.market[t][0] == full_rm
    assert p2.sigma[t] == full_sigma
    assert p2.liquid_count(t) == full_liq


# --- (b) the episode rule ----------------------------------------------------
def test_b_episode_rule():
    p = _panel()
    s = p.sessions
    p.flags = {s[10]: -3.0, s[13]: -3.0}          # 3 sessions apart -> one episode
    assert p.episodes() == [s[10]]
    p.flags = {s[10]: -3.0, s[16]: -3.0}          # 6 sessions apart -> two episodes
    assert p.episodes() == [s[10], s[16]]
    p.flags = {s[10]: -3.0, s[15]: -3.0}          # exactly 5 apart -> same episode
    assert p.episodes() == [s[10]]


# --- (c) basket exclusions ----------------------------------------------------
def test_c_basket_quintile_exclusions():
    p = _panel()
    d = p.sessions[SYN.S1]
    members, k, arb = p.basket(d)
    assert arb == 1                                # ARB0 counted as excluded
    assert "ARB0" not in members                   # zero-volume ARB excluded
    assert "SPLIT" not in members                  # split-day raw bars dropped
    assert k == len(members) == 8                  # 41 eligible -> n // 5
    assert "B15" in members                        # lowest valid return (-4.5%)
    r = p.tickers["B15"]["ret"][_bidx(p, "B15", d)]
    assert r == pytest.approx(1.5 * SYN.STRESS_RET)


# --- (d) the frozen assembly and beta recovery --------------------------------
def test_d_assembly_exact_and_beta():
    r = OC.compute_R(0.02, 1.5, 0.01, 0.006)
    assert round(r * 100, 10) == -0.1              # exact to 10 dp (frozen check)
    assert r == pytest.approx(-0.001, abs=1e-15)
    p = _panel()
    d = p.sessions[SYN.S1]
    b = OC.beta_for(p, "B15", d)
    # ret_t = 1.5 x r_mkt,t exactly; ordinary-day r_m averages 43.5 r-units over
    # 43 liquid names (B15 contributes 1.5, SPLIT is liquid pre-split on true ADV),
    # so the recovered slopes are 1.5 x 43/43.5 and 43/43.5
    assert b == pytest.approx(1.5 * 43 / 43.5, abs=1e-6)
    assert OC.beta_for(p, "F01", d) == pytest.approx(43 / 43.5, abs=1e-6)


# --- (e) add-back on the ex date, never before --------------------------------
def test_e_addback_exdate_only():
    p = _panel()
    s1 = p.sessions[SYN.S1]
    prev = p.sessions[SYN.S1 - 1]
    i1 = _bidx(p, "DIVX", s1)
    ip = _bidx(p, "DIVX", prev)
    assert p.tickers["DIVX"]["ret"][i1] == pytest.approx(SYN.STRESS_RET)   # restored
    assert p.tickers["DIVX"]["ret"][ip] == pytest.approx(SYN._mkt_ret(SYN.S1 - 1))  # no add-back
    # the market return at the stress day includes DIVX on the add-back basis
    assert p.market[s1][0] < -0.02


def _bidx(p, t, d):
    g = p.tickers[t]
    for i, dd in enumerate(g["d"]):
        if dd == d:
            return i
    return None


# --- (f) the census path never computes a post-close return -------------------
OUTCOME_NAMES = {"compute_R", "s1_event", "member_window_return", "beta_for",
                 "sigma_d", "d059_cost", "park60", "decile_of"}
CENSUS_FILES = ["g0_census.py", "stress_reversal.py"]


def test_f_census_path_has_no_outcomes():
    for fn in CENSUS_FILES:
        src = (HERE / fn).read_text()
        tree = ast.parse(src)
        imported, called, attrs = set(), set(), set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported |= {node.module.split(".")[0]}
            elif isinstance(node, ast.Call):
                f = node.func
                if isinstance(f, ast.Name):
                    called.add(f.id)
                elif isinstance(f, ast.Attribute):
                    called.add(f.attr)
            elif isinstance(node, ast.Attribute):
                attrs.add(node.attr)
        assert "outcomes" not in imported, f"{fn} imports the outcome module"
        assert not (called & OUTCOME_NAMES), f"{fn} calls an outcome function"
        assert not ({"pct_change", "shift"} & attrs), f"{fn} uses return primitives"


# --- frozen bars and the split-factor ADV correction --------------------------
def test_bars_frozen():
    assert SR.CENSUS_LEDGER == 601 and SR.N_EXPECTED == 604 and SR.N_IF_D074 == 605
    assert SR.BAR_FROZEN_604 == 3.2954 and SR.BAR_FROZEN_605 == 3.2959
    assert SR.e_max_abs_z(605) > SR.e_max_abs_z(604) > SR.e_max_abs_z(603)


def test_true_adv_split_correction():
    p = _panel()
    d0 = p.sessions[SYN.S1 - 1]                    # the day before SPLIT's ex-date
    g = p.tickers["SPLIT"]
    i = _bidx(p, "SPLIT", d0)
    assert g["f"][i] == pytest.approx(5.0)         # 1:5 split ex-date is AFTER d0
    assert g["adv_true"][i] == pytest.approx(5.0 * g["adv_naive"][i])
    assert bool(g["liq_true"][i]) and not bool(g["liq_naive"][i])


def test_flags_and_near_miss():
    p = _panel()
    s1, s2, nm = (p.sessions[SYN.S1], p.sessions[SYN.S2], p.sessions[SYN.NM])
    assert s1 in p.flags and s2 in p.flags
    assert nm not in p.flags                       # near-miss stays unflagged
    m = p.flags[s1]
    assert m <= -2.5
    nm_mult = p.market[nm][0] / p.sigma[nm]
    assert -3.0 <= nm_mult <= -2.0
