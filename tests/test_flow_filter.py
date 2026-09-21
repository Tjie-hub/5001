"""Regression tests for flow_filter.py::_parse_bars.

Covers the response shape discovered while investigating the RAJA/2026-04-15
stockbit_flow_bars gap: a live tradebook-chart response where `buy`/`sell`/
`net_values` are fully populated (they drove a real, non-zero stockbit_flow
summary row) but `prices` came back as an empty array. `_parse_bars` used to
bound its loop on `min(len(buys), len(sells), len(prices))`, so an empty
`prices` array alone zeroed every bar even though buy/sell/net_values had a
full session's worth of real per-minute data.
"""
from flow_filter import _parse_bars


def _entry(lot, freq, value, t):
    return {
        "frequency": {"raw": str(freq), "formatted": str(freq)},
        "lot": {"raw": str(lot), "formatted": str(lot)},
        "time": t,
        "value": {"raw": str(value), "formatted": str(value)},
        "date": "",
    }


def _net_entry(value, t):
    return {"frequency": None, "lot": None, "time": t, "value": {"raw": str(value)}, "date": ""}


def test_parse_bars_normal_response_all_arrays_aligned():
    data = {
        "buy": [_entry(100, 5, 1000, "09:00"), _entry(200, 6, 2000, "09:01")],
        "sell": [_entry(50, 3, 500, "09:00"), _entry(80, 4, 800, "09:01")],
        "net_values": [_net_entry(500, "09:00"), _net_entry(1200, "09:01")],
        "prices": [_entry(0, 0, 4700, "09:00"), _entry(0, 0, 4710, "09:01")],
    }
    bars = _parse_bars(data)
    assert len(bars) == 2
    assert bars[0] == {
        "time": "09:00", "buy_lot": 100, "sell_lot": 50,
        "buy_freq": 5, "sell_freq": 3, "net_value": 500, "price": 4700,
        "delta": 50,
    }
    assert bars[1]["price"] == 4710


def test_parse_bars_empty_prices_array_still_produces_bars():
    """The discovered RAJA/2026-04-15 shape: buy/sell/net_values are a full,
    real session; `prices` is an empty list. Bars must still be produced from
    the buy/sell data that IS present, with price falling back to the
    existing missing-data sentinel (0) rather than the whole session
    disappearing."""
    data = {
        "buy": [_entry(31362, 822, 15829312500, "09:00"),
                _entry(211993, 7860, 104826627500, "16:14")],
        "sell": [_entry(25228, 777, 12647694500, "09:00"),
                 _entry(346553, 15284, 169937805000, "16:14")],
        "net_values": [_net_entry(3181618000, "09:00"), _net_entry(40290000, "16:14")],
        "prices": [],
    }
    bars = _parse_bars(data)
    assert len(bars) == 2
    assert bars[0]["time"] == "09:00"
    assert bars[0]["buy_lot"] == 31362
    assert bars[0]["sell_lot"] == 25228
    assert bars[0]["buy_freq"] == 822
    assert bars[0]["sell_freq"] == 777
    assert bars[0]["net_value"] == 3181618000
    assert bars[0]["price"] == 0
    assert bars[0]["delta"] == 31362 - 25228
    assert bars[1]["time"] == "16:14"
    assert bars[1]["price"] == 0


def test_parse_bars_missing_net_values_still_produces_bars():
    """net_values already had a per-index bounds check before this fix;
    pin that behaviour so it is not regressed by the prices fix."""
    data = {
        "buy": [_entry(10, 1, 100, "09:00")],
        "sell": [_entry(5, 1, 50, "09:00")],
        "net_values": [],
        "prices": [_entry(0, 0, 4700, "09:00")],
    }
    bars = _parse_bars(data)
    assert len(bars) == 1
    assert bars[0]["net_value"] == 0
    assert bars[0]["price"] == 4700


def test_parse_bars_bounded_by_shorter_of_buy_and_sell():
    """buy/sell are the pair that must stay index-aligned; a length
    mismatch between them should still bound the loop (unlike prices)."""
    data = {
        "buy": [_entry(10, 1, 100, "09:00"), _entry(20, 2, 200, "09:01")],
        "sell": [_entry(5, 1, 50, "09:00")],
        "net_values": [],
        "prices": [],
    }
    bars = _parse_bars(data)
    assert len(bars) == 1


def test_parse_bars_all_empty_arrays_produces_no_bars():
    data = {"buy": [], "sell": [], "net_values": [], "prices": []}
    assert _parse_bars(data) == []
