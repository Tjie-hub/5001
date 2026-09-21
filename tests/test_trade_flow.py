"""Tests for engine/trade_flow.py + GET /api/v1/tickers/<symbol>/trade-flow.

Fixture DB mirrors the production schema of stockbit_flow_bars and
trading_calendar only (copy-verified against broker-flow-v001). The vendor
semantics under test: buy_lot/sell_lot are CUMULATIVE session totals,
net_value is per-minute, price is the minute price.
"""
import sqlite3

import pytest
from flask import Flask

from engine.trade_flow import LOT_SHARES, get_trade_flow
from routes.v1 import api_v1_bp
from routes.v1.envelope import ApiError
import routes.v1.trade_flow as trade_flow_route
import config


# ── fixture DB ────────────────────────────────────────────────────────────

def _init_db(path):
    conn = sqlite3.connect(str(path))
    conn.execute("""
        CREATE TABLE stockbit_flow_bars (
            ticker TEXT NOT NULL, trade_date TEXT NOT NULL, bar_time TEXT NOT NULL,
            buy_lot INTEGER, sell_lot INTEGER, buy_freq INTEGER, sell_freq INTEGER,
            net_value INTEGER, price INTEGER, delta INTEGER,
            PRIMARY KEY (ticker, trade_date, bar_time)
        )
    """)
    conn.execute("CREATE TABLE trading_calendar (date TEXT PRIMARY KEY)")
    return conn


def _bar(ticker, d, t, bl, sl, nv, px):
    return (ticker, d, t, bl, sl, 1, 1, nv, px, bl - sl)


@pytest.fixture()
def db_path(tmp_path):
    path = tmp_path / "flow.db"
    conn = _init_db(path)
    # Day 1 (2026-09-01): cumulative buy 100→250, sell 40→140; price 100→102.
    conn.executemany(
        "INSERT INTO stockbit_flow_bars VALUES (?,?,?,?,?,?,?,?,?,?)",
        [
            _bar("TOWR", "2026-09-01", "09:00", 100, 40, 1_000_000, 100),
            _bar("TOWR", "2026-09-01", "09:01", 250, 140, 2_000_000, 102),
        ],
    )
    # Day 2 (2026-09-02): fresh session — cumulative resets.
    conn.executemany(
        "INSERT INTO stockbit_flow_bars VALUES (?,?,?,?,?,?,?,?,?,?)",
        [
            _bar("TOWR", "2026-09-02", "09:00", 300, 50, -500_000, 101),
            _bar("TOWR", "2026-09-02", "09:01", 380, 90, -300_000, 100),
        ],
    )
    # Calendar: 09-01..09-04 trade, but 09-03 has no bars (ingestion gap).
    conn.executemany(
        "INSERT INTO trading_calendar VALUES (?)",
        [("2026-09-01",), ("2026-09-02",), ("2026-09-03",), ("2026-09-04",)],
    )
    conn.commit()
    conn.close()
    return str(path)


# ── engine: de-cumulation + value maths ──────────────────────────────────

def test_decumulation_and_value(db_path):
    flow = get_trade_flow(db_path, "TOWR", "2026-09-01", "2026-09-01")
    s = flow["series"]
    # Bar 0: opening-auction deltas = the cumulative values themselves.
    # buy 100 lots × 100 sh × 100 = 1_000_000; sell 40 × 100 × 100 = 400_000.
    assert s["cum_buy"][0] == 100 * LOT_SHARES * 100
    assert s["cum_sell"][0] == 40 * LOT_SHARES * 100
    # Bar 1: deltas 150 buy / 100 sell at price 102.
    assert s["cum_buy"][1] == s["cum_buy"][0] + 150 * LOT_SHARES * 102
    assert s["cum_sell"][1] == s["cum_sell"][0] + 100 * LOT_SHARES * 102
    assert s["net_flow"] == [b - sl for b, sl in zip(s["cum_buy"], s["cum_sell"])]
    assert s["price"] == [100, 102]


def test_multiday_chaining(db_path):
    flow = get_trade_flow(db_path, "TOWR", "2026-09-01", "2026-09-02")
    s = flow["series"]
    assert len(s["time"]) == 4
    # Day 2 continues the cumulative chain (no reset across sessions).
    assert s["cum_buy"][2] == s["cum_buy"][1] + 300 * LOT_SHARES * 101
    assert s["cum_sell"][2] == s["cum_sell"][1] + 50 * LOT_SHARES * 101
    assert [sess["date"] for sess in flow["sessions"]] == ["2026-09-01", "2026-09-02"]


def test_single_day_matches_slice_of_range(db_path):
    """Day-level consistency: the single-day view of 09-02 must show the
    same per-minute activity and day totals as inside the 2-day range. The
    cumulative LEVEL differs by design (a range aggregates from its own
    start — Stockbit semantics); the increments and session totals may not."""
    multi = get_trade_flow(db_path, "TOWR", "2026-09-01", "2026-09-02")
    single = get_trade_flow(db_path, "TOWR", "2026-09-02", "2026-09-02")
    ms, ss = multi["series"], single["series"]
    n = len(ss["time"])
    assert n == 2
    assert ss["time"] == ms["time"][-n:]
    assert ss["price"] == ms["price"][-n:]

    def diffs(seq):
        return [b - a for a, b in zip(seq, seq[1:])]

    assert diffs(ss["cum_buy"]) == diffs(ms["cum_buy"][-n:])
    assert diffs(ss["cum_sell"]) == diffs(ms["cum_sell"][-n:])
    # Session-level day totals agree between the two views.
    day2_multi = next(x for x in multi["sessions"] if x["date"] == "2026-09-02")
    assert single["sessions"][0]["buy_value"] == day2_multi["buy_value"]
    assert single["totals"]["buy_value"] == day2_multi["buy_value"]
    assert single["totals"]["sell_value"] == day2_multi["sell_value"]
    assert single["totals"]["net_value"] == day2_multi["net_value"]


def test_range_totals_sum_all_sessions_and_match_chart_end(db_path):
    """Range totals must aggregate the actual trades across the whole range
    and equal the chained cumulative curves' final point (the UI's Buy (cum)
    row and the chart must agree)."""
    flow = get_trade_flow(db_path, "TOWR", "2026-09-01", "2026-09-02")
    s = flow["series"]
    d1, d2 = flow["sessions"]
    assert flow["totals"]["buy_value"] == d1["buy_value"] + d2["buy_value"]
    assert flow["totals"]["sell_value"] == d1["sell_value"] + d2["sell_value"]
    assert flow["totals"]["net_value"] == flow["totals"]["buy_value"] - flow["totals"]["sell_value"]
    assert flow["totals"]["buy_value"] == s["cum_buy"][-1]
    assert flow["totals"]["sell_value"] == s["cum_sell"][-1]
    assert flow["totals"]["net_value"] == s["net_flow"][-1]
    assert flow["totals"]["net_value_exact"] == d1["net_value_exact"] + d2["net_value_exact"]
    # Single-day range totals equal that day's session totals.
    single = get_trade_flow(db_path, "TOWR", "2026-09-01", "2026-09-01")
    assert single["totals"]["buy_value"] == d1["buy_value"]
    assert single["totals"]["buy_value"] == single["series"]["cum_buy"][-1]


def test_session_cumulative_resets_within_range(db_path):
    """Per-session buy_value is the day's own delta sum, not the chained total."""
    flow = get_trade_flow(db_path, "TOWR", "2026-09-01", "2026-09-02")
    d1, d2 = flow["sessions"]
    assert d1["buy_value"] == (100 * 100 * 100) + (150 * 100 * 102)
    assert d2["buy_value"] == (300 * 100 * 101) + (80 * 100 * 100)
    assert d1["net_value_exact"] == 1_000_000 + 2_000_000


# ── engine: date handling / honesty ──────────────────────────────────────

def test_weekend_and_gap_days_not_fabricated(db_path):
    flow = get_trade_flow(db_path, "TOWR", "2026-09-01", "2026-09-04")
    assert [s["date"] for s in flow["sessions"]] == ["2026-09-01", "2026-09-02"]
    # 09-03 is a calendar trading day with no ingested bars; 09-04 is the
    # same shape in this fixture. Both must be reported, never invented.
    assert flow["missing_sessions"] == ["2026-09-03", "2026-09-04"]
    assert len(flow["series"]["time"]) == 4


def test_empty_range_returns_empty_series_not_error(db_path):
    flow = get_trade_flow(db_path, "TOWR", "2026-08-01", "2026-08-05")
    assert flow["sessions"] == []
    assert flow["series"]["points"] == 0
    assert flow["totals"]["net_value"] == 0


def test_unknown_ticker_returns_none(db_path):
    assert get_trade_flow(db_path, "XXXX", "2026-09-01", "2026-09-02") is None


def test_default_range_is_latest_session(db_path):
    flow = get_trade_flow(db_path, "TOWR")
    assert flow["requested"] == {"start": "2026-09-02", "end": "2026-09-02"}
    assert flow["coverage"] == {
        "first_available_session": "2026-09-01",
        "last_available_session": "2026-09-02",
    }


def test_half_open_range_defaults(db_path):
    flow = get_trade_flow(db_path, "TOWR", "2026-09-02", None)
    assert flow["requested"]["end"] == "2026-09-02"
    flow = get_trade_flow(db_path, "TOWR", None, "2026-09-01")
    assert flow["requested"]["start"] == "2026-09-01"


# ── engine: vendor-revision robustness ───────────────────────────────────

def test_negative_delta_clamped_and_counted(tmp_path):
    path = tmp_path / "rev.db"
    conn = _init_db(path)
    conn.executemany(
        "INSERT INTO stockbit_flow_bars VALUES (?,?,?,?,?,?,?,?,?,?)",
        [
            _bar("AAA", "2026-09-01", "09:00", 100, 40, 0, 100),
            _bar("AAA", "2026-09-01", "09:01", 90, 50, 0, 100),  # buy revised down
            _bar("AAA", "2026-09-01", "09:02", 120, 55, 0, 0),   # zero price minute
        ],
    )
    conn.commit()
    conn.close()
    flow = get_trade_flow(str(path), "AAA", "2026-09-01", "2026-09-01")
    s = flow["series"]
    assert s["cum_buy"][1] == s["cum_buy"][0]        # clamped, no negative flow
    assert s["cum_sell"][1] == s["cum_sell"][0] + 10 * LOT_SHARES * 100
    assert s["cum_buy"][2] == s["cum_buy"][1] + 30 * LOT_SHARES * 100  # carried price
    assert s["price"][2] == 100
    assert flow["anomaly_minutes"] == 2


def test_downsample_keeps_terminal_point(tmp_path):
    path = tmp_path / "big.db"
    conn = _init_db(path)
    rows = []
    for i in range(3000):
        cum = 1000 + i * 10
        rows.append(_bar("BBB", "2026-09-01", f"{9 + i // 60:02d}:{i % 60:02d}",
                         cum, 500, 0, 100))
    conn.executemany("INSERT INTO stockbit_flow_bars VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()
    from engine.trade_flow import MAX_POINTS
    flow = get_trade_flow(str(path), "BBB", "2026-09-01", "2026-09-01")
    s = flow["series"]
    assert len(s["time"]) <= MAX_POINTS + 1
    assert s["cum_buy"][-1] == (1000 + 2999 * 10) * LOT_SHARES * 100  # terminal kept
    assert s["cum_buy"] == sorted(s["cum_buy"])  # monotone shape preserved


# ── engine: big money / filters honesty ──────────────────────────────────

def test_big_money_unavailable_and_filters(db_path):
    flow = get_trade_flow(db_path, "TOWR")
    assert flow["big_money"]["available"] is False
    assert "no production" in flow["big_money"]["reason"].lower() or \
           "No production" in flow["big_money"]["reason"]
    assert flow["filters_supported"] == {
        "investor": ["all"], "trade_type": ["regular"], "metric": ["value"],
    }


def test_unsupported_metric_raises(db_path):
    with pytest.raises(ValueError):
        get_trade_flow(db_path, "TOWR", metric="frequency")


# ── route: envelope + validation ─────────────────────────────────────────

@pytest.fixture()
def client(db_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", db_path)
    app = Flask(__name__)
    app.register_blueprint(api_v1_bp)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_route_ok_envelope(client):
    resp = client.get("/api/v1/tickers/TOWR/trade-flow?start=2026-09-01&end=2026-09-02")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["data"]["symbol"] == "TOWR"
    assert body["data"]["series"]["points"] == 4


def test_route_default_dates(client):
    resp = client.get("/api/v1/tickers/towr/trade-flow")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["requested"] == {
        "start": "2026-09-02", "end": "2026-09-02",
    }


def test_route_invalid_symbol(client):
    resp = client.get("/api/v1/tickers/TO%20WR%20/trade-flow")
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "INVALID_SYMBOL"


def test_route_invalid_date(client):
    resp = client.get("/api/v1/tickers/TOWR/trade-flow?start=01-09-2026")
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "INVALID_DATE"


def test_route_inverted_range(client):
    resp = client.get("/api/v1/tickers/TOWR/trade-flow?start=2026-09-02&end=2026-09-01")
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "INVALID_DATE_RANGE"


def test_route_unsupported_metric(client):
    resp = client.get("/api/v1/tickers/TOWR/trade-flow?metric=volume")
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "UNSUPPORTED_METRIC"


def test_route_unknown_ticker_404(client):
    resp = client.get("/api/v1/tickers/XXXX/trade-flow")
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "NO_TRADE_FLOW_DATA"


def test_route_parse_date_helper_unit():
    assert trade_flow_route._parse_date("2026-09-01", "start") == "2026-09-01"
    with pytest.raises(ApiError):
        trade_flow_route._parse_date("not-a-date", "start")
