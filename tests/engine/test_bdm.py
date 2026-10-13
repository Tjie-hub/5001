"""engine/bdm.py -- NeoBDM-style broker-flow context screen (hermetic temp DB)."""
import math
from datetime import date, timedelta

import pytest

from data.db import connect
from engine import bdm


def _mk_db(tmp_path):
    p = tmp_path / "wf.db"
    c = connect(str(p))
    c.execute("""CREATE TABLE broker_flow (ticker TEXT, trade_date TEXT, broker_code TEXT, side TEXT,
                 lot INTEGER, lot_value INTEGER, value INTEGER, value_total INTEGER, avg_price REAL,
                 freq INTEGER, investor_type TEXT, PRIMARY KEY (ticker, trade_date, broker_code, side))""")
    c.execute("""CREATE TABLE ohlcv (id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT, date TEXT,
                 open REAL, high REAL, low REAL, close REAL, volume INTEGER, is_final INTEGER)""")
    c.commit()
    return p, c


def _row(c, t, d, b, side, net, gross, it="Lokal", avg=100.0):
    c.execute("INSERT INTO broker_flow VALUES (?,?,?,?,?,?,?,?,?,?,?)",
              (t, d, b, side, 0, 0, net, gross, avg, 1, it))


# ---- pure functions -------------------------------------------------------

def test_sides_from_net_and_listed_gross():
    assert bdm.sides("BUY", 100, 130) == (130, 30)
    assert bdm.sides("SELL", -100, 130) == (30, 130)
    assert bdm.sides("SELL", 5, 130) == (125, 130)          # ~0.3% rows carry a flipped sign
    assert bdm.sides("BUY", 200, 130) == (130, 0)           # clamp


def test_group_of_broker():
    assert bdm.group_of("XL", "Lokal") == "retail"
    assert bdm.group_of("YP", "Asing") == "retail"           # retail platform beats foreign type
    assert bdm.group_of("AK", "Asing") == "foreign"
    assert bdm.group_of("CC", "Pemerintah") == "institution"
    assert bdm.group_of("RS", "Lokal") == "zombie"
    assert bdm.group_of("??", "Lokal") == "zombie"            # unseen in the freeze window = rare
    assert "AK" in bdm.SULTAN and "XL" not in bdm.SULTAN


def test_day_stats_lines_crossing_and_shares():
    # AK (foreign, sultan) buys 100 net with 50 two-way; XL retail sells 60; RS zombie sells 40.
    brokers = {
        "AK": {"gb": 150.0, "gs": 50.0, "it": "Asing"},
        "XL": {"gb": 20.0, "gs": 80.0, "it": "Lokal"},
        "RS": {"gb": 0.0, "gs": 40.0, "it": "Lokal"},
    }
    s = bdm.day_stats(brokers)
    assert s["net"]["foreign"] == 100 and s["net"]["retail"] == -60 and s["net"]["zombie"] == -40
    assert s["net"]["nonretail"] == 60
    assert s["net"]["sultan"] == 100
    # bandar = top-5 buyers' net + top-5 sellers' net = 100 - 60 - 40
    assert s["net"]["bandar"] == 0
    # crossing ex-retail: 2*min(150,50) + 0 over (200 + 40)
    assert math.isclose(s["crossing"], 100 / 240)
    assert math.isclose(s["value"], (170 + 170) / 2)
    assert math.isclose(s["zombie_share"], 40 / 340)


def test_bandar_concentration_sign():
    # 1 broker buys 100; 10 brokers sell 10 each -> buyers concentrated => positive bandar
    brokers = {"AK": {"gb": 100.0, "gs": 0.0, "it": "Asing"}}
    for i in range(10):
        brokers[f"S{i}"] = {"gb": 0.0, "gs": 10.0, "it": "Lokal"}
    assert bdm.day_stats(brokers)["net"]["bandar"] == 100 - 50


def test_fit_picks_line_tracking_price():
    closes = [100 + i for i in range(60)]
    lines = {"bandar": [float(i) for i in range(60)], "foreign": [float((-1) ** i) for i in range(60)]}
    best, scores = bdm.fit(lines, closes)
    assert best == "bandar" and scores["bandar"] > 0.99
    assert bdm.fit({"bandar": [1.0] * 60}, closes)[0] is None   # flat line -> no fit


# ---- DB-backed ------------------------------------------------------------

def _seed(c, days, ticker="TEST"):
    for i, d in enumerate(days):
        ds = d.isoformat()
        _row(c, ticker, ds, "AK", "BUY", 100, 150, "Asing")
        _row(c, ticker, ds, "XL", "SELL", -60, 80)
        _row(c, ticker, ds, "RS", "SELL", -40, 40)
        c.execute("INSERT INTO ohlcv (ticker,date,open,high,low,close,volume,is_final) VALUES (?,?,?,?,?,?,?,1)",
                  (ticker, ds, 100, 101, 99, 100 + i, 1000))
    c.commit()


def _days(n):
    d, out = date(2026, 6, 1), []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def test_ticker_detail(tmp_path):
    p, c = _mk_db(tmp_path)
    days = _days(70)
    _seed(c, days)
    out = bdm.ticker_detail("TEST", sessions=60, db_path=str(p))
    assert out["ticker"] == "TEST" and len(out["series"]) == 60
    last = out["series"][-1]
    assert last["date"] == days[-1].isoformat() and last["close"] == 169
    assert out["series"][-1]["cum"]["foreign"] == 60 * 100
    assert out["fit"]["best"] in bdm.METHODS
    assert set(out["acc_pct"]) == set(bdm.ACC_WINDOWS)
    assert out["top_brokers"]["buyers"][0]["broker"] == "AK"
    assert bdm.ticker_detail("NONE", db_path=str(p)) is None


def test_screener(tmp_path):
    p, c = _mk_db(tmp_path)
    days = _days(25)
    _seed(c, days, "AAA")
    _seed(c, days, "BBB")
    bdm._SCREEN_CACHE.clear()
    out = bdm.screener(db_path=str(p))
    assert out["as_of"] == days[-1].isoformat()
    assert {r["ticker"] for r in out["rows"]} == {"AAA", "BBB"}
    r = out["rows"][0]
    for k in ("acc_pct", "crossing", "zombie_share", "fit", "value_20d", "flags"):
        assert k in r
    assert out["descriptive_only"] is True


def test_routes(tmp_path, monkeypatch):
    p, c = _mk_db(tmp_path)
    _seed(c, _days(25), "AAA")
    monkeypatch.setattr(bdm, "DB_PATH", str(p))
    bdm._SCREEN_CACHE.clear()
    from app import app
    cl = app.test_client()
    assert cl.get("/bdm").status_code == 200
    r = cl.get("/api/bdm/screener")
    assert r.status_code == 200 and r.get_json()["rows"][0]["ticker"] == "AAA"
    assert cl.get("/api/bdm/ticker/aaa").get_json()["ticker"] == "AAA"
    assert cl.get("/api/bdm/ticker/ZZZ").status_code == 404


def test_check_tool_reconstruction(tmp_path):
    """tools/check_bdm.py: rebuilt lots == trade-book volume when lot_value is the listed-side gross."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("check_bdm", "tools/check_bdm.py")
    cb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cb)
    p, c = _mk_db(tmp_path)
    c.execute("CREATE TABLE stockbit_flow (ticker TEXT, trade_date TEXT, buy_lot INTEGER, sell_lot INTEGER)")
    d = "2026-10-09"
    # AA buys 3000 lots, sells 1000 (net +2000); BB sells 2000 net, buys nothing -> 3000 lots traded
    c.execute("INSERT INTO broker_flow VALUES ('T',?, 'AA','BUY', 2000, 300000, 0, 0, 100, 1, 'Lokal')", (d,))
    c.execute("INSERT INTO broker_flow VALUES ('T',?, 'BB','SELL', -2000, 200000, 0, 0, 100, 1, 'Lokal')", (d,))
    c.execute("INSERT INTO stockbit_flow VALUES ('T', ?, 1500, 1500)", (d,))
    c.commit()
    r = cb.reconstruction(c, d)
    assert len(r) == 1 and abs(r[0] - 1.0) < 1e-12
