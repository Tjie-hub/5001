"""PIT and mechanics tests for the dividend clientele study — G0 gate.

Synthetic panels only; no real DB, no outcomes. Each test pins one
predeclared claim from PREDECLARATION.md §5:

  (a) the anchor precedes the entry session, and an AGM at cum-3 sessions
      (window 2) is dropped from D1;
  (b) ADV20, yield and Parkinson-60 are identical when the panel is truncated
      at the reference date (only earlier bars are used);
  (c) book membership on day t is identical when the panel is truncated at
      t-1 (ADV on earlier days only);
  (d) the total-return add-back uses the EX date, never the cum date;
  (e) the D2 synthetic outcome is EXACTLY -0.001;
  (f) the G0 census path never computes a post-entry return: AST proof that
      g0_census.py / dividend_clientele.py import neither `outcomes` nor any
      outcome function, plus a forbidden-token grep;
  plus the frozen bar (N=607 -> 3.2968, re-frozen 2026-10-08) and the primary-t arithmetic.

Run:  venv/bin/python -m pytest \
        docs/research_programs/P-M/dividend_clientele/test_pit_dividend_clientele.py -v
"""
from __future__ import annotations

import ast
import math
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3]))

import dividend_clientele as DC  # noqa: E402
import outcomes as OC  # noqa: E402
import synthetic as SYN  # noqa: E402


def _world(f01_div=False):
    conn = SYN.make_db(f01_div=f01_div)
    panel = DC.Panel(conn)
    rows, dq = DC.load_dividend_rows(conn)
    freq = DC.created_date_freq(rows)
    ca_ex = DC.load_ca_exdates(conn)
    rups = DC.load_rups(conn)
    built = DC.build_events(panel, rows, freq, ca_ex, rups)
    return conn, panel, rows, freq, ca_ex, rups, built


def _event(built, ticker):
    return {e["ticker"]: e for e in built["events"]}[ticker]


def _d1_population(built):
    return [e for e in built["events"] if e["anchor"] is not None
            and e["window"] is not None
            and DC.WINDOW_MIN <= e["window"] <= DC.WINDOW_MAX
            and e["entry_bar_ok"]]


# --- (a) anchors and the short-window rule ----------------------------------
def test_a_anchor_precedes_entry_and_short_window_dropped():
    _, panel, _, _, _, _, built = _world()
    ev1 = _event(built, "EVT")     # both anchors exist; created (cum-25 sessions) wins
    assert ev1["anchor"] == ev1["created_anchor"]
    assert ev1["created_anchor"] < ev1["rups_anchor"]
    assert ev1["entry_session"] == ev1["cum_session"] - 10  # binds at the 10-session cap
    assert ev1["window"] == 10
    ev4 = _event(built, "EVT4")    # created-only anchor, late (cum-5 sessions)
    assert ev4["anchor"] == ev4["created_anchor"]
    assert ev4["entry_session"] == ev4["cum_session"] - 4   # max(cum-10, created+1)
    assert ev4["window"] == 4
    ev2 = _event(built, "EVT2")    # rups at cum-3 sessions, no created date
    assert ev2["anchor"] == ev2["rups_anchor"]
    assert ev2["entry_session"] == ev2["cum_session"] - 2
    assert ev2["window"] == 2 < DC.WINDOW_MIN
    d1 = _d1_population(built)
    assert all(e["anchor"] < e["entry_session_date"] for e in d1)
    assert all(DC.WINDOW_MIN <= e["window"] <= DC.WINDOW_MAX for e in d1)
    assert all(e["ticker"] != "EVT2" for e in d1)           # short window dropped
    assert {e["ticker"] for e in d1} >= {"EVT", "EVT4"}


# --- (b) truncation identity of pre-entry metrics ----------------------------
def test_b_truncation_identical_pre_entry_metrics():
    _, panel, _, _, _, _, built = _world()
    d = _event(built, "EVT")["cum"]
    full = (panel.adv20("EVT", d), panel.park60("EVT", d),
            panel.close_before("EVT", d), panel.vol60_daily("EVT", d),
            panel.vol60_overnight("EVT", d))
    conn2 = SYN.make_db()
    conn2.execute("DELETE FROM ohlcv WHERE date >= ?", (d.isoformat(),))
    conn2.commit()
    p2 = DC.Panel(conn2)
    trunc = (p2.adv20("EVT", d), p2.park60("EVT", d),
             p2.close_before("EVT", d), p2.vol60_daily("EVT", d),
             p2.vol60_overnight("EVT", d))
    for a, b in zip(full, trunc):
        assert a == b


# --- (c) book membership uses only earlier-day ADV ---------------------------
def test_c_book_membership_uses_only_earlier_bars():
    _, panel, _, _, ca_ex, _, _ = _world()
    t = panel.sessions[-1]
    book = OC.Book(panel, ca_ex, {})
    members_full = set(book.member_ret[t])
    assert members_full                                    # non-empty
    # delete every bar STRICTLY AFTER t: membership and returns at t are identical
    conn2 = SYN.make_db()
    conn2.execute("DELETE FROM ohlcv WHERE date > ?", (t.isoformat(),))
    conn2.commit()
    p2 = DC.Panel(conn2)
    book2 = OC.Book(p2, DC.load_ca_exdates(conn2), {})
    assert set(book2.member_ret[t]) == members_full


# --- (d) add-back on the ex date, never the cum date -------------------------
def test_d_addback_uses_exdate_not_cumdate():
    _, panel, _, _, ca_ex, _, _ = _world(f01_div=True)
    conn = SYN.make_db(f01_div=True)
    rows, _ = DC.load_dividend_rows(conn)
    div_ab = {}
    for r in rows:
        k = (r["ticker"], r["ex"])
        div_ab[k] = div_ab.get(k, 0.0) + r["value"]
    book = OC.Book(panel, ca_ex, div_ab)
    cum, ex = panel.sessions[110], panel.sessions[111]
    assert div_ab[("F01", ex)] == 5.0
    assert book.member_ret[ex]["F01"] == pytest.approx(0.05)   # (100 + 5)/100 - 1
    assert book.member_ret[cum]["F01"] == pytest.approx(0.0)   # cum date: NO add-back


# --- (e) the D2 synthetic outcome is exactly -0.001 --------------------------
def test_e_synthetic_d2_exact():
    # solo fixture: EVT is the only event, so the book is perfectly flat
    conn = SYN.make_db(extra_events=False)
    panel = DC.Panel(conn)
    rows, _ = DC.load_dividend_rows(conn)
    freq = DC.created_date_freq(rows)
    ca_ex = DC.load_ca_exdates(conn)
    rups = DC.load_rups(conn)
    built = DC.build_events(panel, rows, freq, ca_ex, rups)
    div_ab = {}
    for r in rows:
        div_ab[(r["ticker"], r["ex"])] = div_ab.get((r["ticker"], r["ex"]), 0.0) + r["value"]
    book = OC.Book(panel, ca_ex, div_ab)
    ev = _event(built, "EVT")
    assert book.ew_open_return(ev["ex_session_date"], exclude="EVT") == 0.0   # flat book
    r = OC.d2_event_return(panel, book, ev)
    assert r["excess"] == -0.001                 # exact, per PREDECLARATION §5(e)


# --- (f) the census path never computes a post-entry return ------------------
OUTCOME_NAMES = {"d1_event_return", "d2_event_return", "run_arm", "load_world",
                 "month_mean_t", "two_way_cluster_t", "primary_t", "Book"}
CENSUS_FILES = ["g0_census.py", "dividend_clientele.py"]


def test_f_census_path_has_no_outcomes():
    for fn in CENSUS_FILES:
        src = (HERE / fn).read_text()
        tree = ast.parse(src)
        imported = set()
        called = set()
        attrs = set()
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


# --- frozen bar and inference arithmetic -------------------------------------
def test_bar_frozen():
    assert DC.CENSUS_LEDGER == 605 and DC.CENSUS_N == 607
    assert DC.BAR_FROZEN == 3.2968
    assert DC.e_max_abs_z(607) == pytest.approx(3.2968, abs=5e-5)
    assert DC.e_max_abs_z(608) > DC.e_max_abs_z(607) > DC.e_max_abs_z(606)


def test_primary_t_arithmetic():
    xs = [0.01, 0.02, -0.005, 0.03, 0.015, 0.025]
    months = ["2024-01", "2024-01", "2024-01", "2024-02", "2024-02", "2024-02"]
    tickers = ["A", "B", "A", "B", "A", "B"]
    tm = OC.month_mean_t(xs, months)
    mm = float(np.mean([np.mean(xs[:3]), np.mean(xs[3:])]))
    sm = float(np.std([np.mean(xs[:3]), np.mean(xs[3:])], ddof=1))
    assert tm == pytest.approx(mm / sm * math.sqrt(2))
    assert math.isfinite(OC.two_way_cluster_t(xs, months, tickers))
    rng = np.random.default_rng(7)
    big = list(rng.normal(0.001, 0.01, 400))
    assert abs(OC.month_mean_t(big, [f"m{i // 20}" for i in range(400)])) < 3.2968


def test_data_quality_funnel():
    _, _, rows, _, _, _, built = _world()
    assert all(r["ex"] > r["cum"] for r in rows)
    assert built["funnel"]["drops"]["ca_in_window"] >= 1        # EVT3 caught
    assert "EVT3" not in {e["ticker"] for e in built["events"]}
