"""The trade-book lot/frequency series are cumulative session totals (2026-10-09 fix).

_analyze must score per-minute flow, and fetch_flow's daily totals must be the last cumulative value,
not the sum of the running totals.
"""
from unittest import mock

import flow_filter
import stockbit_fetcher


def _bars(per_min_buy, per_min_sell, price=100):
    out, cb, cs = [], 0, 0
    for i, (b, s) in enumerate(zip(per_min_buy, per_min_sell)):
        cb += b
        cs += s
        h, m = divmod(i, 60)
        out.append({"time": f"{9 + h:02d}:{m:02d}", "buy_lot": cb, "sell_lot": cs, "buy_freq": cb, "sell_freq": cs,
                    "net_value": (b - s) * price * 100, "price": price, "delta": cb - cs})
    return out


def test_per_minute_inverts_the_cumulative_series():
    pm = flow_filter._per_minute(_bars([5, 0, 3], [1, 2, 0]))
    assert [b["buy_lot"] for b in pm] == [5, 0, 3] and [b["sell_lot"] for b in pm] == [1, 2, 0]
    assert [b["delta"] for b in pm] == [4, -2, 3]


def test_per_minute_clamps_a_vendor_revision():
    bars = _bars([5, 5], [0, 0])
    bars[1]["buy_lot"] = 3  # cumulative went down
    assert [b["buy_lot"] for b in flow_filter._per_minute(bars)] == [5, 0]


def test_analyze_scores_per_minute_flow():
    # Heavy buying in the first 30 minutes, then steady net selling for the rest of the session.
    # The cumulative net stays positive all day, so scoring the running totals read the close as
    # net buying; per-minute flow shows the closing session was selling.
    buy = [100] * 30 + [1] * 330
    sell = [0] * 30 + [3] * 330
    a = flow_filter._analyze("TEST", _bars(buy, sell))
    assert a["cum_delta"] == sum(buy) - sum(sell)
    assert a["accelerating"] is False          # last 30 minutes net selling vs first 30 net buying
    assert a["smart_money"] == "MORNING_TRAP"   # morning net buy, 14:30-15:00 net sell


def test_fetch_flow_totals_use_the_last_cumulative_value():
    data = {"buy": [{"lot": {"raw": "10"}, "frequency": {"raw": "2"}, "time": "09:00"},
                    {"lot": {"raw": "25"}, "frequency": {"raw": "5"}, "time": "09:01"}],
            "sell": [{"lot": {"raw": "4"}, "frequency": {"raw": "1"}, "time": "09:00"},
                     {"lot": {"raw": "9"}, "frequency": {"raw": "3"}, "time": "09:01"}],
            "net_values": [{"value": {"raw": "600"}}, {"value": {"raw": "1000"}}],
            "prices": [{"value": {"raw": "100"}}, {"value": {"raw": "101"}}], "date": "2026-10-09"}
    resp = mock.Mock(status_code=200)
    resp.json.return_value = {"data": data}
    with mock.patch.object(stockbit_fetcher.requests, "get", return_value=resp):
        f = stockbit_fetcher.fetch_flow("tok", "TEST")
    assert (f["buy_lot"], f["sell_lot"], f["buy_freq"], f["sell_freq"]) == (25, 9, 5, 3)
    assert f["net_lot"] == 16 and f["net_value"] == 1600
