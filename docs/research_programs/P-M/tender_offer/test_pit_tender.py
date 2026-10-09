"""PIT tests for the tender-offer floor G0 (HYP-PM-0018 draft).

(a) truncation: pre-event facts identical when every bar after the entry is
    deleted (prices after the entry close cannot influence the census);
(b) entry = the last session strictly before tender_start (start may be a
    non-session); exit = the last session on or before tender_end;
(c) basis rule: a synthetic 1:2 bonus AFTER tender_start rescales the raw
    offer exactly as frozen (202 -> 101 at entry close 100);
(d) exactness: entry 100, end close 103, engineered cost 0.6% ->
    R = +2.4000000000% exactly; EW book +1% -> excess +1.4% (10 dp);
(e) dividend add-back uses the EX date inside (entry, exit] only;
(f) census purity: g0_census.py imports no outcome module and neither it
    nor tender_floor.py contains forbidden pandas-style look-ahead tokens.

Run:  venv/bin/python -m pytest docs/research_programs/P-M/tender_offer/test_pit_tender.py -q
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import synthetic as SYN          # noqa: E402
import tender_floor as TF        # noqa: E402
import outcomes as OC            # noqa: E402


def _panel():
    conn = SYN.make_db()
    fac, divs = TF.load_ca(conn)
    return TF.Panel(conn, fac, divs), fac, divs


def _truncated_panel(d_entry):
    import sqlite3
    conn = SYN.make_db()
    cut = d_entry.isoformat()
    conn.execute("CREATE TABLE ohlcv_trunc AS SELECT * FROM ohlcv WHERE date <= ?", (cut,))
    conn.execute("DROP TABLE ohlcv")
    conn.execute("ALTER TABLE ohlcv_trunc RENAME TO ohlcv")
    fac, divs = TF.load_ca(conn)
    return TF.Panel(conn, fac, divs)


def _tenders():
    return {e["ticker"]: e for e in TF.load_tenders(SYN.make_db())}


def test_a_truncation_invariance():
    panel, _, _ = _panel()
    for tk in ("PX", "SP", "GUA"):
        ev = _tenders()[tk]
        full = TF.prefacts(panel, ev)
        trunc = TF.prefacts(_truncated_panel(full["d_entry"]), ev)
        assert full is not None and trunc is not None
        for k in ("d_entry", "close_entry", "f_cum_entry", "price_adj", "spread",
                  "adv20", "cost", "sigma_d", "volume_entry", "prebars"):
            assert full[k] == trunc[k], (tk, k, full[k], trunc[k])


def test_b_entry_exit_sessions():
    panel, _, _ = _panel()
    sess = panel.sessions
    ev = _tenders()["PX"]
    r = TF.eligibility(panel, ev)
    assert r["stage"] == "ELIGIBLE"
    assert ev["start"].weekday() == 5            # a Saturday
    assert r["d_entry"] == sess[SYN.E]           # last session strictly before start
    assert r["d_exit"] == sess[SYN.X]            # last session on or before the Saturday end
    assert r["window_sessions"] == SYN.X - SYN.E # sessions in (entry, exit]
    assert panel.last_session_before(sess[SYN.E]) == sess[SYN.E - 1]
    assert panel.last_session_on_or_before(sess[SYN.X]) == sess[SYN.X]


def test_c_basis_rule_rescale():
    panel, _, _ = _panel()
    r = TF.eligibility(panel, _tenders()["SP"])
    assert r["f_cum_entry"] == 2.0               # 1:2 bonus after the window
    assert r["price_adj"] == pytest.approx(101.0, abs=1e-12)
    assert r["spread"] == pytest.approx(0.01, abs=1e-12)
    assert r["close_entry"] == 100.0
    # S8 (cost floor) expected to reject the 1% spread: cost > spread - 0.006
    assert r["stage"] == "S8_spread"


def test_d_exact_R_and_excess():
    panel, _, _ = _panel()
    sess = panel.sessions
    facts = {"ticker": "PX", "event_id": "1", "start": sess[SYN.E + 1], "end": sess[SYN.X],
             "d_entry": sess[SYN.E], "d_exit": sess[SYN.X],
             "close_entry": 100.0, "price_adj": 101.0, "spread": 0.01,
             "cost": 0.006, "adv20": 5e9, "window_sessions": 5, "pct": 22.5,
             "price_raw": 101.0, "f_cum_entry": 1.0}
    r = OC.t1_event(panel, facts)
    assert abs(r["gross_ret"] - 0.03) < 1e-12    # 103/100 - 1
    assert abs(r["R"] - 0.024) < 1e-10           # +2.4% exactly (10 dp)
    assert abs(r["book_ret"] - 0.01) < 1e-12     # BX 500 -> 505
    assert abs(r["excess"] - 0.014) < 1e-10      # +1.4% (10 dp)


def test_e_dividend_addback_exdate_only():
    panel, _, _ = _panel()
    sess = panel.sessions
    g = panel.tickers["DV"]
    i_e = panel.bar_index("DV", sess[SYN.E])
    ret, _, div = OC.total_return(panel, "DV", i_e, sess[SYN.E], sess[SYN.X])
    assert div == pytest.approx(10.0)            # only the ex-date inside (entry, exit]
    assert ret == pytest.approx((200.0 + 10.0) / 200.0 - 1.0)
    # at-entry ex (d2) is never added; the after-exit ex (d3) belongs to a
    # later window only
    assert OC.total_return(panel, "DV", i_e, sess[SYN.E], sess[SYN.E + 1])[2] == 0.0
    assert OC.total_return(panel, "DV", i_e, sess[SYN.X + 1], sess[SYN.X + 3])[2] == pytest.approx(5.0)


def test_f_census_purity():
    src = (HERE / "g0_census.py").read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(a.name != "outcomes" for a in node.names), "census imports outcomes"
        if isinstance(node, ast.ImportFrom):
            assert node.module != "outcomes", "census imports outcomes"
    for name in ("g0_census.py", "tender_floor.py"):
        txt = (HERE / name).read_text()
        for tok in ("pct_change", "shift("):
            assert tok not in txt, f"forbidden token {tok} in {name}"


def test_waterfall_stages():
    panel, _, _ = _panel()
    t = _tenders()
    assert TF.eligibility(panel, t["PX"])["stage"] == "ELIGIBLE"
    assert TF.eligibility(panel, t["ZV"])["stage"] == "S5_volume"       # zero-volume entry
    assert TF.eligibility(panel, t["GUA"])["stage"] == "S9_guard"       # rights ex inside window
    bad = dict(t["PX"]); bad["start"] = t["PX"]["end"]                  # start >= end
    assert TF.eligibility(panel, bad)["stage"] == "S1_rule1"
    open_ev = dict(t["PX"])
    open_ev["start"] = panel.sessions[-4]              # window has live sessions (DOOH shape)
    open_ev["end"] = panel.sessions[-1] + __import__("datetime").timedelta(days=30)
    r = TF.eligibility(panel, open_ev)
    assert r["stage"] == "S2_settled"                                   # open offer -> recorder


def test_month_clustered_t():
    vals = [0.01, 0.02, -0.01, 0.03, 0.015, -0.005]
    months = ["2025-01", "2025-01", "2025-02", "2025-02", "2025-03", "2025-03"]
    mean, se, t, G = OC.month_clustered_t(vals, months)
    assert mean == pytest.approx(sum(vals) / len(vals))
    assert G == 3
    # single cluster -> undefined t
    m2, se2, t2, G2 = OC.month_clustered_t(vals, ["2025-01"] * 6)
    assert G2 == 1 and m2 == pytest.approx(mean) and se2 != se2  # NaN
