#!/usr/bin/env python3
"""G1 harness mechanical tests — synthetic fixture, hand-verifiable expectations.

Runnable standalone (python3 test_g1_harness.py) or via pytest.
Read-only: touches no database, writes nothing.
"""
import math
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "dataset_b"))

import g1_harness as gh          # noqa: E402
import g1_synthetic as gs        # noqa: E402
import foundation                # noqa: E402

EPS = 1e-9


def _run():
    bundle = gs.make_bundle()
    out = gh.run_g1(bundle, gs.synthetic_config())
    return bundle, out


def _fwd_map(bundle, k):
    return {(o["ticker"], o["formation"]): o["fwd_ret"]
            for o in gh.forward_returns(bundle, k)}


def test_gate_blocks_real_run():
    cfg = gh.load_config(os.path.join(HERE, "g1_config.json"))
    blocks = gh.check_gates(cfg, real_data=True)
    expected_false = [name for name, val in cfg["gates"].items() if not val]
    # every false gate must block, and no true gate may appear in the blockers
    assert len(blocks) == len(expected_false), (len(blocks), expected_false)
    for name in ("dataset_b_frozen", "prereg_confirmed",
                 "freq_semantics_ratified", "net_flow_source_ratified"):
        joined = " ".join(blocks)
        if cfg["gates"][name] is False:
            assert name in joined, f"false gate {name} must block"
        else:
            assert name not in joined, f"true gate {name} must not block"
    assert gh.check_gates(cfg, real_data=False) == []


def test_calendar_indexing_and_strict_contiguity():
    bundle = gs.make_bundle()
    fwd = _fwd_map(bundle, 3)
    # windows CROSSING the excluded 2025-01-21 are invalid: formations
    # 2025-01-18/19/20 (3 sessions ahead lands on/after the holiday) must be
    # absent; earlier formations (window entirely before the holiday) are kept
    bad = [d for (_, d) in fwd if d in ("2025-01-18", "2025-01-19", "2025-01-20")]
    assert bad == [], f"contiguity leak: {bad}"
    assert any(d == "2025-01-17" for (_, d) in fwd)
    # k_ahead counts sessions, not calendar days
    assert gs.SESSIONS[gs.SESSIONS.index("2025-01-22") + 3] == "2025-01-25"


def test_horizon_exact_and_engineered_returns():
    bundle = gs.make_bundle()
    fwd = _fwd_map(bundle, 3)
    assert abs(fwd[("AAA", "2025-02-03")] - 0.02) < EPS
    assert abs(fwd[("CCC", "2025-02-03")] - 0.02) < EPS
    assert abs(fwd[("BBB", "2025-02-03")]) < EPS
    assert abs(fwd[("DDD", "2025-02-03")]) < EPS
    assert abs(fwd[("EEE", "2025-01-22")] - 0.01) < EPS
    # outcome must be exactly 3 sessions ahead, never calendar-shifted
    i = gs.SESSIONS.index("2025-02-03")
    assert gs.SESSIONS[i + 3] == "2025-02-06"


def test_corporate_action_window_filter():
    bundle = gs.make_bundle()
    out = gh.run_g1(bundle, gs.synthetic_config())
    # EEE (member 01-22..01-24) has an applied 5:1 split ex 2025-01-26:
    # k=3 windows from 01-23 and 01-24 cross it -> 2 drops;
    # k=5 windows from 01-22, 01-23, 01-24 cross it -> 3 drops
    assert out["ca_window_exclusions"]["3"] == 2, out["ca_window_exclusions"]
    assert out["ca_window_exclusions"]["5"] == 3, out["ca_window_exclusions"]
    # the underlying return engine itself must not produce a false -80% move
    fwd = _fwd_map(bundle, 3)
    assert all(abs(v) < 0.15 for v in fwd.values())
    assert ("EEE", "2025-01-22") in fwd  # window not touching ex-date survives


def test_suspension_and_missing_bar_handling():
    bundle = gs.make_bundle()
    fwd = _fwd_map(bundle, 3)
    # CCC has no bar on 2025-01-27 (suspension) -> outcome missing -> dropped
    assert ("CCC", "2025-01-24") not in fwd


def test_pit_membership_no_survivorship_leak():
    bundle = gs.make_bundle()
    out = gh.run_g1(bundle, gs.synthetic_config())
    panel = None  # panel not returned by run_g1; assert via fwd maps + accounting
    fwd3 = _fwd_map(bundle, 3)
    # EEE (delisted after 01-25) forms only while a member; FFF only from 01-25
    assert all(not (tk == "EEE" and d >= "2025-01-26") for (tk, d) in fwd3)
    # GGG has prices, flow, and net-flow but is never a roster member:
    # rebuild the panel directly to assert its absence
    classifier, _ = gh.build_species_classifier(bundle.flow, prefix_end=gs.PREFIX_END)
    rows, acc = gh.build_panel(bundle, classifier)
    tickers = {r["ticker"] for r in rows}
    assert "GGG" not in tickers
    assert "QQ" not in tickers                      # quarantined
    assert {r["ticker"] for r in rows if r["date"] < "2025-01-25"} <= {
        "AAA", "BBB", "CCC", "DDD", "EEE"}
    assert {r["ticker"] for r in rows if r["date"] >= "2025-01-25"} <= {
        "AAA", "BBB", "CCC", "DDD", "FFF"}


def test_dedup_and_unclassified_and_gross_exact():
    bundle = gs.make_bundle()
    classifier, cls_acc = gh.build_species_classifier(bundle.flow,
                                                      prefix_end=gs.PREFIX_END)
    assert cls_acc["classified"] == 4
    assert classifier == {"D1": "desk", "D2": "desk", "A1": "agg", "A2": "agg"}
    rows, acc = gh.build_panel(bundle, classifier)
    assert acc["flow_rows_deduped"] == 1, acc
    assert acc["flow_rows_unclassified_broker"] == 22, acc   # 20 ZF prefix + 1 ZF post + 1 N1
    assert acc["flow_rows_zero_value"] == 1
    assert acc["flow_rows_abnormal"] == 1
    assert acc["dropped_quarantine"] == 38
    by = {(r["ticker"], r["date"]): r for r in rows}
    # dedup + unclassified exclusion proven by exact gross: 50M + 10M, counted once
    assert by[("AAA", "2025-01-22")]["gross"] == 60_000_000
    assert abs(by[("AAA", "2025-01-22")]["st"] - 1.0) < EPS
    assert by[("BBB", "2025-01-22")]["gross"] == 60_000_000
    assert abs(by[("BBB", "2025-01-22")]["st"] + 1.0) < EPS
    # filler mixed cell: ST = 0
    assert abs(by[("EEE", "2025-01-24")]["st"]) < EPS
    assert abs(by[("FFF", "2025-01-26")]["st"]) < EPS


def test_t_plus_one_no_leak():
    bundle = gs.make_bundle()
    classifier, _ = gh.build_species_classifier(bundle.flow, prefix_end=gs.PREFIX_END)
    rows, _ = gh.build_panel(bundle, classifier)
    # the +500M dump dated 2025-01-21 (excluded session) must appear nowhere
    assert not any(r["date"] == "2025-01-21" for r in rows)
    by = {(r["ticker"], r["date"]): r for r in rows}
    # formation 01-20 must reflect only trade_date==01-20 flow
    assert by[("AAA", "2025-01-20")]["gross"] == 60_000_000
    assert abs(by[("AAA", "2025-01-20")]["st"] - 1.0) < EPS


def test_breadth_floor_and_accounting():
    bundle = gs.make_bundle()
    out = gh.run_g1(bundle, gs.synthetic_config())
    acc = out["panel_accounting"]
    # 3 tickers x 20 prefix sessions = 60, minus 3 ret1-undefined on the first
    # admitted session (no prior close) = 57; post-prefix 19 x 5 = 95, minus 1
    # suspension row and minus 1 formation after the suspended session (CCC
    # 01-28 has no prior-session close) = 93; total 150.
    assert acc["panel_rows_formed"] == 150, acc
    assert acc["excluded_ret1"] == 4
    assert acc["excluded_suspension_at_t"] == 1
    assert acc["excluded_no_net_flow"] == 0
    assert len(out["formation_dates"]) == 19
    assert len(out["formation_dates_dropped_below_floor"]) == 20
    assert out["ca_window_exclusions"]["3"] == 2
    assert out["ca_window_exclusions"]["5"] == 3


def _expected_theta_nonzero(k=3):
    """Hand-derived: the 204 closes on 2025-02-06 give +2% forward returns for
    formation 02-03 and -(200/204-1) for formation 02-06 (price reverting to
    200); no other engineered return exists."""
    return {("2025-02-03", 0.02), ("2025-02-06", 200.0 / 204.0 - 1.0)}


def _assert_nonzero_theta(daily, expected):
    got = {(d, round(v, 9)) for d, v in daily if abs(v) > EPS}
    exp = {(d, round(v, 9)) for d, v in expected}
    assert got == exp, (sorted(got), sorted(exp))


def test_c1a_theta_exact_and_gating():
    bundle = gs.make_bundle()
    out = gh.run_g1(bundle, gs.synthetic_config())
    c1a3 = [c for c in out["cells"] if c["cell"] == "C1a" and c["k"] == 3][0]
    _assert_nonzero_theta(c1a3["theta_t"], _expected_theta_nonzero())
    # gating: unratified freq semantics (resolution still open) -> BLOCKED
    cfg = gs.synthetic_config()
    cfg["gates"]["freq_semantics_ratified"] = False
    out2 = gh.run_g1(bundle, cfg)
    c1a = [c for c in out2["cells"] if c["cell"] == "C1a"][0]
    assert c1a["status"] == "BLOCKED_FREQ_SEMANTICS"
    assert c1a["theta_mean"] is None and c1a["nw_t"] is None and c1a["p"] is None


def test_withdrawn_arms_represented_and_holm_shrinks():
    """Registered withdrawal state: C1a/C1b emit WITHDRAWN_FREQ_DEPENDENT with
    no numbers regardless of gates, and the Holm family shrinks to the
    retained arms (C2, C3)."""
    bundle = gs.make_bundle()
    cfg = gs.synthetic_config()
    cfg["freq_resolution"] = "withdrawn"
    out = gh.run_g1(bundle, cfg)
    fam = [c for c in out["cells"] if c["k"] == out["primary_k"]]
    by = {c["cell"]: c for c in fam}
    assert by["C1a"]["status"] == "WITHDRAWN_FREQ_DEPENDENT"
    assert by["C1a"]["theta_mean"] is None and by["C1a"]["p"] is None
    assert by["C2"]["status"] == "COMPUTED" and by["C3"]["status"] == "COMPUTED"
    assert by["C2"]["holm_p"] is not None and by["C3"]["holm_p"] is not None
    # even with the freq gate OPEN, withdrawal is unconditional
    cfg2 = gs.synthetic_config()
    cfg2["freq_resolution"] = "withdrawn"
    cfg2["gates"]["freq_semantics_ratified"] = True
    out2 = gh.run_g1(bundle, cfg2)
    c1a = [c for c in out2["cells"] if c["cell"] == "C1a"][0]
    assert c1a["status"] == "WITHDRAWN_FREQ_DEPENDENT"


def test_c2_theta_exact():
    bundle = gs.make_bundle()
    out = gh.run_g1(bundle, gs.synthetic_config())
    c2 = [c for c in out["cells"] if c["cell"] == "C2" and c["k"] == 3][0]
    _assert_nonzero_theta(c2["theta_t"], _expected_theta_nonzero())


def test_c3_theta_exact():
    bundle = gs.make_bundle()
    out = gh.run_g1(bundle, gs.synthetic_config())
    c3 = [c for c in out["cells"] if c["cell"] == "C3" and c["k"] == 3][0]
    nonzero = [(d, v) for d, v in c3["theta_t"] if abs(v) > EPS]
    assert len(nonzero) == 1 and nonzero[0][0] == "2025-01-22", nonzero
    assert abs(nonzero[0][1] - 0.01) < 1e-9


def test_inference_nan_safe_and_holm():
    # constant zero series -> NW t is nan (no crash, no fake significance)
    t, n = gh.nw_t([0.0] * 30, 5)
    assert math.isnan(t) and n == 30
    # a single-engineered-day series still clusters by date
    t2, n2 = gh.nw_t([0.0] * 10 + [0.02] + [0.0] * 8, 3)
    assert math.isfinite(t2) and n2 == 19
    # Holm: monotone step-down adjustment sanity on known inputs
    assert gh.holm([0.03, 0.01, 0.04]) == [0.06, 0.03, 0.06]


def test_output_deterministic_and_machine_readable():
    import json
    o1 = gh.run_g1(gs.make_bundle(), gs.synthetic_config())
    o2 = gh.run_g1(gs.make_bundle(), gs.synthetic_config())
    # strict JSON: NaN/Infinity literals are not machine-readable
    s1 = json.dumps(o1, sort_keys=True, default=str, allow_nan=False)
    s2 = json.dumps(o2, sort_keys=True, default=str, allow_nan=False)
    assert s1 == s2
    for key in ("config_sha256", "panel_accounting", "cells", "family_alpha",
                "primary_k", "ks", "formation_dates", "ca_window_exclusions"):
        assert key in o1
    fam = [c for c in o1["cells"] if c["k"] == o1["primary_k"]]
    assert len(fam) == 3 and all("holm_p" in c and "status" in c for c in fam)


def test_parity_with_foundation_forward_returns():
    """The harness return engine must mirror foundation.forward_returns
    (Dataset B-owned measurement) rule for rule on the fixture data."""
    bundle = gs.make_bundle()
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, close REAL)")
    conn.executemany("INSERT INTO ohlcv VALUES (?,?,?)",
                     [((tk), d, b["close"]) for (tk, d), b in bundle.ohlcv.items()])
    cal = foundation.SessionCalendar(sessions=list(bundle.sessions),
                                     excluded=dict(bundle.excluded), sha256="test")
    cal._idx = {d: i for i, d in enumerate(cal.sessions)}
    roster = foundation.PitRoster(universe=sorted({t for s in bundle.roster.values()
                                                   for t in s}),
                                  session_members=dict(bundle.roster),
                                  periods=[], sha256="test")
    ours = {(o["ticker"], o["formation"]): round(o["fwd_ret"], 12)
            for o in gh.forward_returns(bundle, 3)}
    theirs_rows, _ = foundation.forward_returns(conn, roster, cal, 3,
                                                quarantined={"QQ"})
    theirs = {(o["ticker"], o["formation"]): round(o["fwd_ret"], 12)
              for o in theirs_rows}
    assert ours == theirs, (len(ours), len(theirs))


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
