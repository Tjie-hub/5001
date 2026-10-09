"""Daily order-flow imbalance (OIB) continuation -- G0-frozen module (D-088). PRE-OUTCOME ONLY.

OIB(i, t) = (B - S) / (B + S), with B and S the session's FINAL cumulative buy- and sell-aggressor lots
from the trade-book minute bars (MAX over the day's bars; the counters are cumulative, fix 47ff225).
Prediction (I7, order-splitting continuation): high OIB -> higher next-day return, so
S = EW(Q5, highest OIB) - EW(Q1) > 0.

This module never reads a price after a formation date. Outcomes live in outcomes.py, which neither
this file nor g0_census.py imports (AST-tested). Prices, dividends, split factors and the D-081
regular-volume basis come from `ownership.py`, a verbatim copy of the frozen retail-ownership module
(b7f84ac, sha256 856afe18...).
"""
from __future__ import annotations

import json
import math
import sys
from datetime import date
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3]))

import ownership as OW  # noqa: E402
from data.db import connect as db_connect  # noqa: E402

DAILY_CACHE = Path.home() / "scratch" / "oib_daily_2026-10-08.json"
ADV_MIN = 1.0e9
PRICE_MIN = 50.0
MIN_BARS = 200            # a ticker-day needs >= 200 minute bars (typical day 335) to count as captured
MIN_UNIVERSE = 100        # a day needs >= 100 eligible names to be a test day
QUINTILE = 5
BLOCK = 5                 # tradeability block: 5 sessions
H1_LAST = date(2025, 12, 31)

CENSUS_LEDGER = 611       # after D-085 (D-087 withdrew before registration)
N_ARMS = 1
N_FROZEN = CENSUS_LEDGER + N_ARMS   # 612
BAR_EXACT = OW._bar.e_max_abs_z(N_FROZEN)
BAR_FROZEN = round(BAR_EXACT, 4)

# Stop rule (frozen before power is computed): if the power to detect a 0.10%/day gross spread at
# the bar is below 20%, G1 does not run. sigma for the test is the pre-sample random-spread sigma
# scaled by sqrt(pre-sample leg size / test leg size) (idiosyncratic variance ~ 1/k).
STOP_EFFECT_DAILY = 0.0010
STOP_POWER_MIN = 0.20


def load_daily(path=DAILY_CACHE) -> dict[tuple[str, date], tuple[float, float, int]]:
    raw = json.loads(Path(path).read_text())
    assert raw["wf_sha256"] == OW.WF_SHA256, "daily cache is not from the pinned snapshot"
    out = {}
    for t, d, b, s, n in raw["rows"]:
        dd = OW.parse_date(d)
        if dd is not None and b is not None and s is not None:
            out[(t, dd)] = (float(b), float(s), int(n))
    return out


def load_opens(hl, since: date) -> dict[tuple[str, date], float]:
    return {(t, OW.parse_date(d)): float(o) for t, d, o in hl.execute(
        "SELECT ticker, date, open FROM ohlcv_long WHERE date >= ?", (since.isoformat(),)) if o}


def oib_of(daily, t, days):
    b = s = 0.0
    n = 0
    for d in days:
        x = daily.get((t, d))
        if x is None or x[2] < MIN_BARS:
            continue
        b += x[0]
        s += x[1]
        n += 1
    if n == 0 or b + s <= 0:
        return None
    return (b - s) / (b + s)


def cross_section(panel, daily, tickers_by_day, days: list[date]) -> dict:
    """Universe, OIB over `days`, and controls at the close of days[-1] (pre-outcome)."""
    k = days[-1]
    rows, drop = [], {"no_flow": 0, "no_bar": 0, "adv": 0, "price": 0, "hist": 0}
    for t in tickers_by_day.get(k, ()):
        o = oib_of(daily, t, days)
        if o is None:
            drop["no_flow"] += 1
            continue
        ft = panel.features(t, k)
        if ft is None:
            drop["no_bar"] += 1
            continue
        if not (ft["adv"] >= ADV_MIN):
            drop["adv"] += 1
            continue
        if not (ft["close"] >= PRICE_MIN):
            drop["price"] += 1
            continue
        g = panel.tickers[t]
        i = g["idx"][k]
        if i < 61 or not np.isfinite(ft["park60"]):
            drop["hist"] += 1
            continue
        r_t = (g["c"][i] + panel.divs.get((t, k), 0.0)) / g["c"][i - 1] - 1.0
        rows.append({"t": t, "oib": o, "r_t": r_t, "ladv": math.log(ft["adv"]), "adv": ft["adv"],
                     "park60": ft["park60"], "sigma60": ft["sigma60"]})
    return {"k": k, "days": days, "rows": rows, "drop": drop}


def quintiles(rows, key="oib"):
    xs = sorted((r[key], r["t"]) for r in rows if np.isfinite(r[key]))
    n = len(xs)
    kq = n // QUINTILE
    if kq < 1:
        return [], [], n
    return [t for _, t in xs[:kq]], [t for _, t in xs[-kq:]], n


def tickers_by_day(daily):
    out: dict[date, list[str]] = {}
    for (t, d) in daily:
        out.setdefault(d, []).append(t)
    for d in out:
        out[d].sort()
    return out


def load_all():
    panel, _ = OW.load_all()
    hl = db_connect(path=OW.HL_SNAPSHOT, read_only=True)
    daily = load_daily()
    opens = load_opens(hl, date(2024, 12, 1))
    return panel, daily, opens
