#!/usr/bin/env python3
"""C7 registration tests — deterministic mini fixture, hand-verifiable.

Fixture: 24 consecutive sessions 2025-06-02..2025-06-25 (no exclusions);
ADV20 first defined at S20 = 2025-06-22 (panel window S20..S23).
Tickers: HI (always high, intensity 2.5), LO (non-high 1.0; exactly 2.0 on
06-24 — inclusive boundary), PF (close 99 — price floor), SUS (suspended
06-23), NOFLOW (roster member, no flow rows), Q (quarantined).
Engineered outcome: HI close 102 on 2025-06-25 -> fwd3(HI, 06-22) = +2%.

Hand-derived expectations are asserted inline. Runnable standalone/pytest.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import g1_harness as gh  # noqa: E402

SESSIONS = [f"2025-06-{d:02d}" for d in range(2, 26)]   # 06-02 .. 06-25
TV = 10000.0                                            # close(100) x volume(100)
HI_GROSS = 25000.0                                      # intensity 2.5
LO_GROSS = 10000.0                                      # intensity 1.0


def make_c7_bundle():
    roster_tk = ["HI", "LO", "PF", "SUS", "NOFLOW", "Q"]
    ohlcv = {}
    for tk in roster_tk:
        for d in SESSIONS:
            close = 102.0 if (tk == "HI" and d == "2025-06-25") else \
                    (99.0 if tk == "PF" else 100.0)
            vol = 200000 if (tk == "HI" and d == "2025-06-21") else 100
            ohlcv[(tk, d)] = {"open": close, "high": close, "low": close,
                              "close": close, "volume": vol, "value": close * vol}
    flow = []

    def row(tk, d, value):
        flow.append({"ticker": tk, "trade_date": d, "broker_code": "AA",
                     "side": "BUY" if value >= 0 else "SELL", "lot": 0,
                     "lot_value": 0, "value": value, "avg_price": 100.0,
                     "freq": None, "investor_type": "Lokal"})

    for d in SESSIONS:
        row("HI", d, HI_GROSS)
        row("LO", d, 20000.0 if d == "2025-06-24" else LO_GROSS)
        row("PF", d, 5000.0)
        row("SUS", d, 5000.0)
        row("Q", d, 5000.0)
    return gh.DataBundle(
        sessions=SESSIONS, excluded={},
        roster={d: list(roster_tk) for d in SESSIONS},
        ohlcv=ohlcv, flow=flow, bandar={},
        suspensions={("SUS", "2025-06-23")}, corporate_actions=[],
        net_flow={}, quarantined={"Q"},
        provenance={"fixture": "test_c7_registration.mini"})


def c7_cfg(registered=True):
    return {"c7_registered": registered, "synthetic": True,
            "_config_sha256": "test"}


def test_fail_closed_gate():
    try:
        gh.run_c7(make_c7_bundle(), c7_cfg(registered=False))
        raise AssertionError("run_c7 executed with c7_registered=false")
    except SystemExit as e:
        assert "c7_registered" in str(e)


def test_intensity_threshold_and_boundary():
    rows, _ = gh.c7_build_panel(make_c7_bundle())
    by = {(r["ticker"], r["date"]): r for r in rows}
    hi = by[("HI", "2025-06-22")]
    assert abs(hi["intensity"] - 2.5) < 1e-12 and hi["high"] is True
    lo = by[("LO", "2025-06-22")]
    assert abs(lo["intensity"] - 1.0) < 1e-12 and lo["high"] is False
    # boundary INCLUSIVE: exactly 2.0 is high
    b = by[("LO", "2025-06-24")]
    assert abs(b["intensity"] - 2.0) < 1e-12 and b["high"] is True


def test_adv20_median_prior20_shift1():
    bundle = make_c7_bundle()
    rows, _ = gh.c7_build_panel(bundle)
    tv = {}
    for (tk, d), b in bundle.ohlcv.items():
        if b.get("close") and b.get("volume"):
            tv[(tk, d)] = b["close"] * b["volume"]
    sessions = bundle.sessions
    for r in rows:
        i = sessions.index(r["date"])
        window = [tv[(r["ticker"], sessions[j])] for j in range(i - 20, i)]
        expected = sorted(window)[len(window) // 2]
        assert abs(r["adv20"] - expected) < 1e-9, (r["ticker"], r["date"])
    # shift(1) probe: HI's 20,000,000-volume session on 06-21 is OUTSIDE the
    # window of formation 06-22 -> ADV20 stays at the 10,000 baseline
    hi = [r for r in rows if r["ticker"] == "HI" and r["date"] == "2025-06-22"][0]
    assert abs(hi["adv20"] - TV) < 1e-9


def test_freq_never_accessed():
    b1 = make_c7_bundle()
    b2 = make_c7_bundle()
    for r in b2.flow:
        r["freq"] = "POISON"
        r["value_total"] = -999
    o1 = gh.run_c7(b1, c7_cfg())
    o2 = gh.run_c7(b2, c7_cfg())
    s1 = json.dumps(o1, sort_keys=True, default=str, allow_nan=False)
    s2 = json.dumps(o2, sort_keys=True, default=str, allow_nan=False)
    assert s1 == s2


def test_registered_exclusions_counted():
    rows, acc = gh.c7_build_panel(make_c7_bundle())
    tickers = {r["ticker"] for r in rows}
    assert "Q" not in tickers and "PF" not in tickers
    assert acc["dropped_quarantine"] == 24        # 1 row x 24 sessions
    assert acc["excluded_suspension_at_t"] == 1   # SUS on 06-23
    assert acc["excluded_price_floor"] == 4       # PF, S20..S23
    assert acc["excluded_missing_adv20"] == 100   # 5 bar-tickers x 20 pre-history sessions
    assert acc["excluded_gross_zero"] == 4        # NOFLOW, S20..S23
    assert acc["panel_rows_formed"] == 11         # 3+2+3+3


def test_ks_primary_contrast_and_costs():
    out = gh.run_c7(make_c7_bundle(), c7_cfg())
    assert out["ks"] == [3, 5, 10] and out["primary_k"] == 5
    by = {(c["k"]): c for c in out["cells"]}
    # k=3: exactly one contrast day (06-22) with the engineered +2% spread
    c3 = by[3]
    assert c3["n_days"] == 1 and len(c3["theta_t"]) == 1
    assert c3["theta_t"][0][0] == "2025-06-22"
    assert abs(c3["theta_t"][0][1] - 0.02) < 1e-12
    assert abs(c3["theta_mean"] - 0.02) < 1e-12
    # k=5/k=10: every formation would need an outcome beyond the fixture end
    c5 = by[5]
    assert c5["n_days"] == 0 and c5["theta_mean"] is None
    assert by[10]["n_days"] == 0 and by[10]["theta_mean"] is None
    # k=10: no formation has an outcome 10 sessions ahead -> empty
    assert by[10]["n_days"] == 0 and by[10]["theta_mean"] is None
    # net-of-cost sensitivity on the one k=3 day
    assert abs(c3["theta_net_cost_floor"] - (0.02 - 0.006)) < 1e-12


def test_determinism():
    o1 = gh.run_c7(make_c7_bundle(), c7_cfg())
    o2 = gh.run_c7(make_c7_bundle(), c7_cfg())
    assert json.dumps(o1, sort_keys=True, default=str, allow_nan=False) == \
           json.dumps(o2, sort_keys=True, default=str, allow_nan=False)


def main():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
