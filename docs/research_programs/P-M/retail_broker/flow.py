"""Online-retail broker imbalance -- {RF} G0-frozen module. PRE-OUTCOME ONLY.

D-086 (mechanism accepted, owner 2026-10-09). One registered arm, B1:
  RI(i, w) = sum over the formation week of R-group net value / sum of |net value| over all
  reported brokers, R = {XL, XC, YP, PD, KK} (frozen in the 08 memo by ticket size, formation
  window 2025-01-02 .. 2025-03-31, excluded from every test).
Prediction: retail net buying is followed by LOWER returns, so S = EW(Q1, lowest RI) - EW(Q5) > 0.

This module never computes a return after a formation close. Holding-period returns live in
`outcomes.py`, which neither this file nor `g0_census.py` imports (AST-tested).

Panel (owner scope, D-086): the 98 names with broker_flow rows before 2025-04-01 (the continuous
liquid panel). Prices come from the same history_long panel and D-081 regular-volume basis as the
retail-ownership study: `ownership.py` here is a verbatim copy of that study's frozen module
(research/retail-ownership-2026-10 @ b7f84ac, sha256 856afe18...), covered by this study's sidecar.

Vendor limit: the marketdetectors summary lists the top 25 brokers per side. An R broker absent from
a ticker-day contributes 0 net (it was not among the largest 25 net buyers or sellers); absence
rates are reported at G0.
"""
from __future__ import annotations

import math
import sys
from datetime import date
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3]))

import ownership as OW  # noqa: E402  (frozen sibling study: Panel, load_ca, hashes, bar)
from data.db import connect as db_connect  # noqa: E402

R_GROUP = ("XL", "XC", "YP", "PD", "KK")
FORMATION_WINDOW_END = date(2025, 3, 31)
TEST_START = date(2025, 4, 1)
H1_LAST_FORMATION = date(2025, 12, 31)
ADV_MIN = 1.0e9
PRICE_MIN = 50.0
MIN_SESSIONS_IN_WEEK = 3          # broker data on at least 3 sessions of the formation week
QUINTILE = 5
BLOCK_WEEKS = 4                   # non-overlapping tradeability block

CENSUS_LEDGER = 611               # after D-085
N_ARMS = 1
N_FROZEN = CENSUS_LEDGER + N_ARMS  # 612
BAR_EXACT = OW._bar.e_max_abs_z(N_FROZEN)
BAR_FROZEN = round(BAR_EXACT, 4)

# Stop rule (frozen BEFORE power is computed): if the power to detect a 0.30%/week gross spread at
# the bar is below 20%, G1 does not run.
STOP_EFFECT_WEEKLY = 0.0030
STOP_POWER_MIN = 0.20


def panel_tickers(wf) -> list[str]:
    return sorted(r[0] for r in wf.execute(
        "SELECT DISTINCT ticker FROM broker_flow WHERE trade_date <= ?",
        (FORMATION_WINDOW_END.isoformat(),)))


def load_daily(wf, tickers: list[str]) -> dict[tuple[str, date], dict]:
    """Per ticker-day: R net, foreign net, gross |net| over all reported brokers, R presence."""
    out: dict[tuple[str, date], dict] = {}
    q = (f"SELECT ticker, trade_date, broker_code, value, investor_type FROM broker_flow "
         f"WHERE ticker IN ({','.join('?' * len(tickers))})")
    for t, d, b, v, it in wf.execute(q, tickers):
        dd = OW.parse_date(d)
        if dd is None or v is None:
            continue
        g = out.setdefault((t, dd), {"r": 0.0, "f": 0.0, "gross": 0.0, "rb": set()})
        v = float(v)
        g["gross"] += abs(v)
        if b in R_GROUP:
            g["r"] += v
            g["rb"].add(b)
        if it == "Asing":
            g["f"] += v
    return out


def weeks(sessions: list[date]) -> list[list[date]]:
    """Panel sessions grouped by ISO week, in order."""
    out, cur, key = [], [], None
    for d in sessions:
        k = d.isocalendar()[:2]
        if k != key and cur:
            out.append(cur)
            cur = []
        key = k
        cur.append(d)
    if cur:
        out.append(cur)
    return out


def formation_weeks(panel) -> list[list[date]]:
    """Test weeks: every session >= TEST_START (the formation window never feeds a signal)."""
    return [w for w in weeks(panel.sessions) if w[0] >= TEST_START]


def signal(daily, t: str, days: list[date]) -> dict | None:
    rows = [daily[(t, d)] for d in days if (t, d) in daily]
    if len(rows) < min(MIN_SESSIONS_IN_WEEK, len(days)):
        return None
    gross = sum(x["gross"] for x in rows)
    if gross <= 0:
        return None
    return {"ri": sum(x["r"] for x in rows) / gross, "fi": sum(x["f"] for x in rows) / gross,
            "n_days": len(rows), "r_present": sum(len(x["rb"]) for x in rows) / (len(R_GROUP) * len(rows))}


def cross_section(panel, daily, tickers: list[str], days: list[date]) -> dict:
    """Universe, signal and controls at the close of days[-1] (pre-outcome)."""
    k = days[-1]
    rows, drop = [], {"no_bar": 0, "no_flow": 0, "adv": 0, "price": 0, "hist": 0}
    for t in tickers:
        ft = panel.features(t, k)
        if ft is None:
            drop["no_bar"] += 1
            continue
        s = signal(daily, t, days)
        if s is None:
            drop["no_flow"] += 1
            continue
        if not (ft["adv"] >= ADV_MIN):
            drop["adv"] += 1
            continue
        if not (ft["close"] >= PRICE_MIN):
            drop["price"] += 1
            continue
        g = panel.tickers[t]
        i = g["idx"][k]
        j = i - len(days)
        if j < 0 or not np.isfinite(ft["park60"]):
            drop["hist"] += 1
            continue
        # prior return over the formation week itself (close before the week -> formation close),
        # dividend add-back; a pre-formation control, not an outcome
        acc = 1.0
        for m in range(j + 1, i + 1):
            acc *= (g["c"][m] + panel.divs.get((t, g["d"][m]), 0.0)) / g["c"][m - 1]
        rows.append({"t": t, "ri": s["ri"], "fi": s["fi"], "prior": acc - 1.0,
                     "ladv": math.log(ft["adv"]), "adv": ft["adv"], "park60": ft["park60"],
                     "sigma60": ft["sigma60"], "r_present": s["r_present"]})
    return {"k": k, "days": days, "rows": rows, "drop": drop}


def quintiles(rows: list[dict], key: str = "ri") -> tuple[list[str], list[str], int]:
    xs = sorted((r[key], r["t"]) for r in rows if np.isfinite(r[key]))
    n = len(xs)
    kq = n // QUINTILE
    if kq < 1:
        return [], [], n
    return [t for _, t in xs[:kq]], [t for _, t in xs[-kq:]], n


def load_all():
    panel, _ = OW.load_all()
    wf = db_connect(path=OW.WF_SNAPSHOT, read_only=True)
    tickers = panel_tickers(wf)
    daily = load_daily(wf, tickers)
    return panel, tickers, daily
