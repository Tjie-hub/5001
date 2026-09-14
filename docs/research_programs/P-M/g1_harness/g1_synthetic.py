#!/usr/bin/env python3
"""Synthetic fixture for the G1 harness dry-run. TINY and HAND-VERIFIABLE.

Calendar: 40 consecutive calendar days 2025-01-01..2025-02-09;
"2025-01-21" is a declared excluded (holiday) session -> 39 admitted sessions.
  admitted index:  0..19  = 2025-01-01..2025-01-20  (prefix window; fixture
                    prefix_end = 2025-01-20 so the species classifier sees only
                    these dates)
                 20..38  = 2025-01-22..2025-02-09

PIT roster (membership changes mid-sample; QQ always a member but QUARANTINED;
GGG has prices/flow/net-flow but is NEVER a member):
  idx 0..23:  AAA BBB CCC DDD EEE QQ
  idx 24..38: AAA BBB CCC DDD FFF QQ

Brokers (tickets = |value|/freq on prefix rows):
  D1 Asing  DESK (10M)   D2 Asing  DESK (12M)
  A1 Lokal  AGG  (5M)    A2 Lokal  AGG  (2M)
  N1 first appears post-prefix -> unclassified; ZF has only freq=0 prefix rows
  -> unclassified.

Standard ticker-day pattern (every admitted session idx>=20):
  AAA ST=+1: BUY D1 +50M f5            | SELL A1 -10M f2      gross 60M
  BBB ST=-1: BUY A1 +10M f2            | SELL D1 -50M f5      gross 60M
  CCC ST=+1: same shape as AAA
  DDD ST=-1: same shape as BBB
  EEE/FFF ST=0: BUY D2 +30M f5, A2 +30M f15 | SELL D2 -30M f5, A2 -30M f15
  QQ: BUY D1 +10M f1 | SELL A1 -10M f1   (quarantined; never reaches panel)

Engineered net-flow control: AAA +0.5, BBB +0.4, CCC -0.4, DDD -0.5,
EEE/FFF 0, QQ +0.9, GGG +0.3.

Engineered prices: close=200 everywhere except EEE close 202 on 2025-01-25 and
AAA/CCC close 204 on 2025-02-06.

Hand-verifiable expectations (see test_g1_harness.py):
  fwd3(2025-02-03): AAA +2%, CCC +2%, BBB 0, DDD 0  -> theta_t = +2% exactly,
    the ONLY nonzero k=3 daily theta.
  fwd3(EEE, 2025-01-22) = +1% (EEE close 202 on 01-25) -> the ONLY nonzero C3
    daily spread (+1%) because EEE is broad (breadth 4/6) and DDD narrow
    (-1/3) on 2025-01-22.
  fwd3(EEE, 2025-01-23/24/25) dropped by the CA window filter (EEE's applied
    5:1 split ex 2025-01-26 lies inside (t, t+3]).
  No formation before 2025-01-22 (strict contiguity across excluded 01-21).
  (CCC, 2025-01-24) dropped: suspended/no bar on outcome 2025-01-27.
"""
from g1_harness import DataBundle

SESSIONS_ALL = [f"2025-{m:02d}-{d:02d}" for m, d in
                [(1, dd) for dd in range(1, 32)] + [(2, dd) for dd in range(1, 10)]]
EXCLUDED = {"2025-01-21": "synthetic holiday"}
SESSIONS = [d for d in SESSIONS_ALL if d not in EXCLUDED]
PREFIX_END = "2025-01-20"
IDX20 = SESSIONS.index("2025-01-22")            # 20
LATE = SESSIONS[IDX20:]                          # 19 sessions idx 20..38

CORE = ["AAA", "BBB", "CCC", "DDD"]
NF = {"AAA": 0.5, "BBB": 0.4, "CCC": -0.4, "DDD": -0.5,
      "EEE": 0.0, "FFF": 0.0, "QQ": 0.9, "GGG": 0.3}
TICKERS = ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "QQ", "GGG"]


def roster_for(d: str) -> list[str]:
    members = list(CORE)
    members.append("FFF" if d >= "2025-01-25" else "EEE")
    members.append("QQ")
    return members


def _row(tk, d, broker, side, value, freq, itype):
    return {"ticker": tk, "trade_date": d, "broker_code": broker, "side": side,
            "lot": abs(value) // 1000, "lot_value": abs(value) // 100,
            "value": value, "avg_price": 200.0, "freq": freq, "investor_type": itype}


def make_bundle() -> DataBundle:
    flow = []
    # ---- prefix rows (classifier food) ----
    for d in SESSIONS[:IDX20]:
        flow.append(_row("AAA", d, "D1", "BUY", 50_000_000, 5, "Asing"))
        flow.append(_row("AAA", d, "A1", "SELL", -10_000_000, 2, "Lokal"))
        flow.append(_row("DDD", d, "A1", "BUY", 10_000_000, 2, "Lokal"))
        flow.append(_row("DDD", d, "D1", "SELL", -50_000_000, 5, "Asing"))
        flow.append(_row("EEE", d, "D2", "BUY", 60_000_000, 5, "Asing"))
        flow.append(_row("EEE", d, "A2", "SELL", -30_000_000, 15, "Lokal"))
        flow.append(_row("BBB", d, "ZF", "BUY", 5_000_000, 0, "Lokal"))  # freq=0
    # ---- standard pattern, idx >= 20 ----
    for d in LATE:
        flow.append(_row("AAA", d, "D1", "BUY", 50_000_000, 5, "Asing"))
        flow.append(_row("AAA", d, "A1", "SELL", -10_000_000, 2, "Lokal"))
        flow.append(_row("BBB", d, "A1", "BUY", 10_000_000, 2, "Lokal"))
        flow.append(_row("BBB", d, "D1", "SELL", -50_000_000, 5, "Asing"))
        flow.append(_row("CCC", d, "D1", "BUY", 50_000_000, 5, "Asing"))
        flow.append(_row("CCC", d, "A1", "SELL", -10_000_000, 2, "Lokal"))
        flow.append(_row("DDD", d, "A1", "BUY", 10_000_000, 2, "Lokal"))
        flow.append(_row("DDD", d, "D1", "SELL", -50_000_000, 5, "Asing"))
        flow.append(_row("QQ", d, "D1", "BUY", 10_000_000, 1, "Asing"))
        flow.append(_row("QQ", d, "A1", "SELL", -10_000_000, 1, "Lokal"))
        filler = "FFF" if d >= "2025-01-25" else "EEE"
        flow.append(_row(filler, d, "D2", "BUY", 30_000_000, 5, "Asing"))
        flow.append(_row(filler, d, "A2", "BUY", 30_000_000, 15, "Lokal"))
        flow.append(_row(filler, d, "D2", "SELL", -30_000_000, 5, "Asing"))
        flow.append(_row(filler, d, "A2", "SELL", -30_000_000, 15, "Lokal"))
    # ---- engineered special rows ----
    flow.append(_row("AAA", "2025-01-22", "D1", "BUY", 50_000_000, 5, "Asing"))  # DUP
    flow.append(_row("AAA", "2025-01-22", "N1", "BUY", 90_000_000, 1, "Asing"))  # unclass
    flow.append(_row("BBB", "2025-01-22", "ZF", "SELL", -5_000_000, 1, "Lokal"))  # unclass
    flow.append(_row("AAA", "2025-01-21", "D1", "BUY", 500_000_000, 5, "Asing"))  # T+1 dump
    flow.append(_row("FFF", "2025-01-25", "A1", "BUY", 0, 3, "Lokal"))            # zero value
    flow.append(_row("EEE", "2025-01-23", "D1", "SELL", -10**15, 1, "Asing"))     # abnormal
    # C3 states on 2025-01-22: EEE broad (4 buys / 2 sells), DDD narrow (1/2)
    flow.append(_row("EEE", "2025-01-22", "D1", "BUY", 1_000_000, 1, "Asing"))
    flow.append(_row("EEE", "2025-01-22", "A1", "BUY", 1_000_000, 1, "Lokal"))
    flow.append(_row("DDD", "2025-01-22", "A2", "SELL", -1_000_000, 1, "Lokal"))
    # leakage bait: GGG trades but is never a roster member
    flow.append(_row("GGG", "2025-01-22", "D1", "BUY", 70_000_000, 7, "Asing"))

    ohlcv = {}
    for tk in TICKERS:
        for d in SESSIONS_ALL:  # includes the excluded day: bars exist, session doesn't
            close = 200.0
            if tk == "EEE" and d == "2025-01-25":
                close = 202.0
            if tk in ("AAA", "CCC") and d == "2025-02-06":
                close = 204.0
            ohlcv[(tk, d)] = {"open": close, "high": close, "low": close,
                              "close": close, "volume": 1000, "value": close * 1000}
    del ohlcv[("CCC", "2025-01-27")]  # suspended: no bar on that session

    roster = {d: roster_for(d) for d in SESSIONS}
    net_flow = {(tk, d): NF[tk] for d in SESSIONS for tk in TICKERS}
    corporate_actions = [
        {"ticker": "QQ", "ex_date": "2025-01-26", "factor": 5.0, "applied": False},
        {"ticker": "EEE", "ex_date": "2025-01-26", "factor": 5.0, "applied": True},
    ]
    suspensions = {("CCC", "2025-01-27")}
    return DataBundle(
        sessions=SESSIONS, excluded=dict(EXCLUDED), roster=roster, ohlcv=ohlcv,
        flow=flow, bandar={}, suspensions=suspensions,
        corporate_actions=corporate_actions, net_flow=net_flow,
        quarantined={"QQ"},
        provenance={"fixture": "g1_synthetic.make_bundle", "deterministic": True})


def synthetic_config() -> dict:
    """Config for the fixture: fixture-scale floors, freq gate OPEN so C1a's
    machinery is exercised (real runs keep it closed), prefix pinned to the
    fixture prefix."""
    import hashlib
    import json
    cfg = {
        "synthetic": True,
        "enforce_freq_gate": True,
        "freq_resolution": "open",   # synthetic fixture exercises C1a machinery;
                                     # the registered real config uses "withdrawn"
        "prefix_end": PREFIX_END,
        "breadth_floor": 4,
        "breadth_surprise_min_history": 2,
        "st_tercile_cuts": [-1.0 / 3, 1.0 / 3],
        "gates": {"dataset_b_frozen": False, "prereg_confirmed": False,
                  "freq_semantics_ratified": True,
                  "net_flow_source_ratified": True},
    }
    cfg["_config_sha256"] = hashlib.sha256(
        json.dumps(cfg, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return cfg
