"""PIT and synthetic tests for the retail-ownership study (G0). Hermetic: synthetic DBs only."""
import ast
import math
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3]))

import ownership as OW  # noqa: E402
import outcomes as OC  # noqa: E402
from data.db import connect  # noqa: E402


def _imports(path):
    tree = ast.parse(Path(path).read_text())
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            names |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            names.add(n.module)
    return names


def test_census_and_module_never_import_outcomes():
    for f in ("ownership.py", "g0_census.py"):
        assert "outcomes" not in _imports(HERE / f), f


def _sessions(start, n):
    d, out = start, []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def _panel(tmp_path, tickers, sessions, price_fn, end=None, divs=None):
    db = tmp_path / "hl.db"
    if not db.exists():
        c = connect(path=str(db))
        c.execute("CREATE TABLE ohlcv_long (ticker, date, open, high, low, close, adj_close, volume)")
        for t in tickers:
            for i, d in enumerate(sessions):
                p = price_fn(t, i)
                c.execute("INSERT INTO ohlcv_long VALUES (?,?,?,?,?,?,?,?)",
                          (t, d.isoformat(), p, p * 1.01, p * 0.99, p, p, 1e7))
        c.commit()
        c.close()
    return OW.Panel(connect(path=str(db), read_only=True), {}, divs or {}, {}, end=end)


def test_known_session_is_fifth_after_file_date(tmp_path):
    ss = _sessions(date(2010, 1, 4), 40)
    p = _panel(tmp_path, ["AAAA"], ss, lambda t, i: 100.0)
    fd = date(2010, 1, 29)  # a Friday month-end
    k = p.nth_session_after(fd, OW.KNOWN_LAG_SESSIONS)
    after = [d for d in ss if d > fd]
    assert k == after[4]


def test_truncation_invariance(tmp_path):
    ss = _sessions(date(2009, 1, 1), 400)
    names = [f"T{i:03d}" for i in range(12)]
    p_full = _panel(tmp_path, names, ss, lambda t, i: 100.0 + int(t[1:]) + 0.1 * i)
    k = ss[300]
    p_cut = OW.Panel(connect(path=str(tmp_path / "hl.db"), read_only=True), {}, {}, {}, end=k)
    ksei = {ss[295]: {t: {"sec_num": 1e9, "tot": 1e9, "ind": 1e8 * (1 + j), "find": 0.0, "stamp": ss[296]}
                      for j, t in enumerate(names)}}
    form = {"file": ss[295], "k": k, "stamp": ss[296]}
    a = OW.build_cross_section(p_full, ksei, form, None)
    b = OW.build_cross_section(p_cut, ksei, form, None)
    strip = lambda rows: [{kk: (round(v, 12) if isinstance(v, float) and math.isfinite(v) else v)
                           for kk, v in r.items()} for r in rows]
    assert strip(a["rows"]) == strip(b["rows"]) and len(a["rows"]) == 12


def test_synthetic_spread_and_dividend_exdate(tmp_path):
    # 10 names, constant prices except: low-retail names gain 1%/day for the 2 days after k
    ss = _sessions(date(2009, 1, 1), 300)
    names = [f"N{i:02d}" for i in range(10)]
    k0, k1 = ss[270], ss[272]

    def price(t, i):
        base = 100.0
        if int(t[1:]) < 2 and i > 270:
            return base * 1.01 ** min(i - 270, 2)
        return base
    divs = {("N09", ss[271]): 1.0}           # 1% dividend on N09's ex-date inside the window
    p = _panel(tmp_path, names, ss, price, divs=divs)
    r, st = OC.name_return(p, "N00", k0, k1)
    assert st == "ok" and abs(r - (1.01 ** 2 - 1)) < 1e-12
    r9, _ = OC.name_return(p, "N09", k0, k1)
    assert abs(r9 - 0.01) < 1e-12              # add-back on the ex-date only
    r9b, _ = OC.name_return(p, "N09", ss[271], ss[272])
    assert abs(r9b) < 1e-12                    # window starting AT the ex-date close: no add-back


def test_run_arm_synthetic(tmp_path):
    ss = _sessions(date(2009, 1, 1), 300)
    names = [f"N{i:02d}" for i in range(10)]

    def price(t, i):
        return 100.0 * (1.01 ** min(max(i - 270, 0), 2) if int(t[1:]) < 2 else 1.0)
    p = _panel(tmp_path, names, ss, price)
    rows = [{"t": t, "s": j / 10, "s_sec": j / 10, "ds": 0.0, "adv": 50e9, "size": 20.0 + j,
             "park60": 0.02 + 0.001 * j, "mom": 0.0, "sigma60": 0.02, "fshare": 0.0, "custody": 1.0,
             "volex": 0} for j, t in enumerate(names)]
    secs = [{"k": ss[270], "rows": rows}, {"k": ss[272], "rows": rows}]
    a = OC.run_arm(p, secs, "s")
    m = a["months"][0]
    assert m["q"] == 2 and abs(m["gross"] - (1.01 ** 2 - 1)) < 1e-12
    c = OC.cr.d059_cost_realised(50e9, 0.02, "normal")
    assert abs(m["net"] - (m["gross"] - 2 * c)) < 1e-12


def test_turnover_cost():
    feats = {t: {"adv": 50e9, "sigma60": 0.02} for t in "ABCDE"}
    one = OC.leg_cost(list("ABCDE"), feats, list("ABCDE"), {})
    assert one == 0.0
    full = OC.leg_cost(list("ABCDE"), feats, None, {})
    assert abs(full - OC.cr.d059_cost_realised(50e9, 0.02, "normal")) < 1e-15
    half = OC.leg_cost(list("ABCDE"), feats, list("ABXYZ"), {})
    assert abs(half - 0.6 * full) < 1e-15


def test_bar_frozen():
    assert OW.N_FROZEN == 611 and OW.BAR_FROZEN == 3.2987
