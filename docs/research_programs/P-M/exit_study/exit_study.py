"""Exit & position-management practice study on the owner's sniper entry (2026-10-06).

G0 STATE: machinery only. census_g0() counts setups and fills — it reads NO
returns. No trade outcome is computed on real data at G0. run_g1() (one run ->
RESULT/VERDICT/PRACTICE_NOTE) refuses without EXIT_STUDY_G1_APPROVED=1.

This is a PRACTICE STUDY per ZCODE_BRIEF_EXIT_POSITION_STUDY_2026-10-06.md: not a
hypothesis registration, no family slot, not filed in FAILURE_REGISTRY. Still
predeclared and frozen before any outcome is read, because choosing the best of
many exit rules is itself a multiple-comparison problem.

Everything numeric is fixed by PREDECLARATION.md (the sha256 sidecar covers this
file, the predeclaration and the PIT test file). Constants marked FROZEN must not
change after the freeze — a change is a new, disclosed, re-frozen run.

G0-bis re-freeze 2026-10-06 (planner review, BEFORE any outcome was read; the
one authorized re-freeze): the E-SN level logic now matches jurnal26 exactly —
server.py::_levels with w=5/tol=0.04 and watchlist._sniper. Pivots widened to
5 bars each side (confirmation lag 5); pivot highs and lows POOLED into one
ascending list and grouped at 4% anchored on each group's lowest price; support
= the highest-MEAN group below the close; target = the MIN of the lowest-mean
group above the close with a <= zone-top fallback to the 52-week high. See the
dated note in PREDECLARATION §3.

Research-side only: numpy/pandas + research.rulecard.data + research.tracking +
data.db read-only. No ~/jurnal26 code is imported; the sniper rules are
re-implemented from the brief's text.
"""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.rulecard.data import load_extended_ohlcv  # noqa: E402
from research.tracking import dataset_fingerprint, git_commit  # noqa: E402
from data.db import connect as db_connect  # noqa: E402

# ── FROZEN constants (PREDECLARATION.md §3–§11) ──────────────────────────────
SEED = 20261006
COST_BUY = 0.0015               # per buy fill (owner's broker)
COST_SELL = 0.0025              # per sell fill
SLIP_RT = 0.0020                # slippage allowance per round trip, on buy notional
ADV20_MIN = 10.0e9              # owner screen: ADV20 >= Rp 10bn (C*V 20-session mean)
ADV60_TOP = 150                 # parity universe (census-level report only)
ADV60_MIN_PERIODS = 40
ERA_SPLIT = "2021-10"           # signal month >= this is E2; E1 is 2001-01..2021-09
ERA_END = "2026-09"             # brief: eras end at 2026-09; later signals excluded (counted)
WATCH = 20                      # sessions a limit order is watched (setup window)
MAX_HOLD = 60                   # sessions any arm may hold; also the fill lock
PIVOT_HALF = 5                  # 11-bar pivots: 5 bars each side (jurnal26 w=5; G0-bis)
PIVOT_WINDOW = 250              # pivots over the last PIVOT_WINDOW bars
MERGE_PCT = 0.04                # pooled pivots: joins a group iff p <= group[0]*(1+4%) (jurnal26 tol)
ZONE_TOP_ATR_FLOOR = 0.5        # zone top = min(max(zmax, zlow + 0.5*ATR), close)
STOP_ATR = 0.75                 # stop = zone low - 0.75*ATR
SETUP_PROX = 0.10               # setup when close within 10% above the zone top
TREND_MA20_K = 2.0              # close <= MA20 + 2*ATR14
X2_STOP_ATR, X2_TGT_ATR = 2.0, 3.0
X3_TRAIL_ATR = 3.0
X5_TIME = 10                    # sessions
X5_PROFIT_ATR = 1.0
P2_ADD_ATR = 1.0                # average down +50% at entry - 1*ATR
P3_ADD_ATR = 1.0                # pyramid +50% at entry + 1*ATR on a close
P4_PULLBACK_ATR = 0.5           # swing-lot top-up at entry - 0.5*ATR
P4_SELL_ATR = 1.5               # top-up sells at its own entry + 1.5*ATR
BRK_HIGH_N = 20                 # E-BRK: close above the 20-day high
BRK_ZONE_ATR = 1.0              # E-BRK synthetic zone low = entry - 1*ATR
RISK_FRAC = 0.01                # equal-risk portfolio: 1% of equity per trade
PORT_MAX_CONCURRENT = 10
PORT_SESSIONS_PER_YEAR = 250.0
G1_ENV = "EXIT_STUDY_G1_APPROVED"

EXIT_ARMS = ("X0", "X1", "X2", "X3", "X4", "X5", "X6")
POS_ARMS = ("P0", "P1", "P2", "P3", "P4")

HIST_PKL = os.getenv("EXIT_STUDY_HIST_PKL")
SPLITS_PKL = os.getenv("EXIT_STUDY_SPLITS_PKL")


# ── Panel ─────────────────────────────────────────────────────────────────────

def load_panel(hist=None, splits=None):
    """Frozen dataset: load_extended_ohlcv(issuance=True), daily OHLCV only."""
    kw = {}
    if hist or HIST_PKL:
        kw["hist"] = hist or HIST_PKL
    if splits or SPLITS_PKL:
        kw["splits"] = splits or SPLITS_PKL
    X = load_extended_ohlcv(issuance=True, **kw)
    return {k: X.pivot(index="date", columns="ticker", values=k).sort_index()
            for k in ("open", "high", "low", "close", "volume")}


def true_range_1d(H, L, C):
    prev_c = np.concatenate([[np.nan], C[:-1]])
    with np.errstate(invalid="ignore"):
        tr = np.nanmax(np.vstack([H - L, np.abs(H - prev_c), np.abs(L - prev_c)]), axis=0)
    tr[0] = H[0] - L[0]
    return tr


def stock_indicators(O, H, L, C, V):
    """Per-stock indicator arrays (all causal; min_periods = window)."""
    n = len(C)
    with np.errstate(invalid="ignore", divide="ignore"):
        ma20 = pd.Series(C).rolling(20, min_periods=20).mean().values
        ma50 = pd.Series(C).rolling(50, min_periods=50).mean().values
        ma200 = pd.Series(C).rolling(200, min_periods=200).mean().values
        atr14 = pd.Series(true_range_1d(H, L, C)).rolling(14, min_periods=14).mean().values
        adv20 = pd.Series(C * V).rolling(20, min_periods=20).mean().values
        hi20 = pd.Series(H).rolling(BRK_HIGH_N, min_periods=BRK_HIGH_N).max().shift(1).values
        hi250 = pd.Series(H).rolling(PIVOT_WINDOW, min_periods=PIVOT_WINDOW).max().values
    ma200_prev = np.full(n, np.nan)
    ma200_prev[20:] = ma200[:n - 20]        # MA200 rising over 20 sessions
    lo_flags = pivot_flags_1d(L)
    hi_flags = pivot_flags_1d(H)
    lo_idx = np.where(lo_flags)[0]
    hi_idx = np.where(hi_flags)[0]
    return {"ma20": ma20, "ma50": ma50, "ma200": ma200, "ma200_prev20": ma200_prev,
            "atr14": atr14, "adv20": adv20, "hi20": hi20, "hi250": hi250,
            "lo_idx": lo_idx, "lo_vals": L[lo_idx],
            "hi_idx": hi_idx, "hi_vals": H[hi_idx]}


def pivot_flags_1d(x):
    """Pivots with PIVOT_HALF bars each side, matching jurnal26
    server.py::_levels (w=5): strict versus the bars BEFORE (left strict),
    non-strict to the right (H[i] == max of the window), so a plateau counts
    once — at its first bar. Confirmed only at index+PIVOT_HALF (a pivot needs
    its right side to exist)."""
    pl = np.zeros(len(x), dtype=bool)
    h = PIVOT_HALF
    if len(x) < 2 * h + 1:
        return pl
    n = len(x)
    c = x[h:n - h]
    left = (c < x[h - 1:n - h - 1]) & (c < x[0:n - 2 * h])
    right = (c <= x[h + 1:n - h + 1]) & (c <= x[h + 2:n - h + 2])
    pl[h:n - h] = left & right
    return pl


def groups_from_pivots(values):
    """jurnal26 _levels grouping (G0-bis): pool every confirmed pivot value
    (highs AND lows together), sort ascending, group sequentially — a pivot
    joins the current group iff p <= group[0] * (1 + MERGE_PCT), where
    group[0] is the group's LOWEST price (the anchor; the chain does not
    slide), else it starts a new group. Each group -> (mean, count, min, max)."""
    groups = []
    for p in sorted(values):
        if groups and p <= groups[-1][0] * (1.0 + MERGE_PCT):
            groups[-1].append(float(p))
        else:
            groups.append([float(p)])
    return [{"mean": sum(g) / len(g), "count": len(g), "min": g[0], "max": g[-1]}
            for g in groups]


def zone_context(L, H, I, k):
    """Confirmed pivots in the window [k-PIVOT_WINDOW+1, k-PIVOT_HALF] (only
    bars up to k count: a pivot is knowable PIVOT_HALF sessions after it
    forms), POOLED — pivot highs and pivot lows in ONE ascending list — and
    grouped per jurnal26 _levels (tol=4% anchored on each group's lowest
    price). Pivot flags come from the per-stock indicator cache (computed
    once); L/H are kept for signature parity, the cached pivot values are
    used."""
    j = k - PIVOT_WINDOW + 1
    top = k - PIVOT_HALF
    a = np.searchsorted(I["lo_idx"], j, side="left")
    b = np.searchsorted(I["lo_idx"], top, side="right")
    vals = list(I["lo_vals"][a:b])
    a = np.searchsorted(I["hi_idx"], j, side="left")
    b = np.searchsorted(I["hi_idx"], top, side="right")
    vals += list(I["hi_vals"][a:b])
    return groups_from_pivots(vals) if vals else []


# ── Sniper setup detection (PIT) ──────────────────────────────────────────────

def sniper_signal_at(k, O, H, L, C, I):
    """The sniper setup for one stock on day k, or None. Trend filter per the
    brief; levels per jurnal26 (G0-bis): pooled pivot groups, support = the
    highest-mean group below the close, target = the min of the lowest-mean
    group above the close with a <= zone-top fallback to the 52-week high.
    Every level uses only bars <= k (pivots via the 5-session confirmation
    lag)."""
    atr, ma20, ma50, ma200, ma200p = (I["atr14"], I["ma20"], I["ma50"],
                                      I["ma200"], I["ma200_prev20"])
    if not all(np.isfinite(x) and x > 0 for x in (C[k], atr[k])):
        return None
    if not (np.isfinite(ma50[k]) and np.isfinite(ma200[k]) and np.isfinite(ma20[k])):
        return None
    if not (C[k] > ma50[k] > ma200[k] and ma200[k] > ma200p[k]):
        return None
    if C[k] > ma20[k] + TREND_MA20_K * atr[k]:
        return None
    groups = zone_context(L, H, I, k)
    below = [g for g in groups if g["mean"] < C[k]]
    if not below:
        return None
    z = max(below, key=lambda g: g["mean"])
    zlow, zmax = z["min"], z["max"]
    ztop = min(max(zmax, zlow + ZONE_TOP_ATR_FLOOR * atr[k]), C[k])
    if not (ztop > 0 and ztop <= C[k] <= ztop * (1.0 + SETUP_PROX) + 1e-9):
        return None
    above = [g for g in groups if g["mean"] > C[k]]
    if above:
        target = min(above, key=lambda g: g["mean"])["min"]
    else:
        target = float(I["hi250"][k])
    if not np.isfinite(target) or target <= ztop:
        target = float(I["hi250"][k])   # jurnal26 _sniper: a target at/below the
    if not np.isfinite(target):         # zone top degenerates to the 52w high
        return None
    return {"zone_low": float(zlow), "zone_top": float(ztop),
            "stop": float(zlow - STOP_ATR * atr[k]), "target": float(target),
            "atr": float(atr[k])}


def resistance_target_at(k, H, L, C, I, ref_px):
    """The min of the pooled group with the lowest mean above ref_px (the same
    G0-bis machinery as the E-SN target; no zone-top guard — E-BRK's frozen
    definition is otherwise unchanged), else the 52-week high. Used for E-BRK,
    whose target anchors on the signal close."""
    groups = zone_context(L, H, I, k)
    above = [g for g in groups if g["mean"] > ref_px]
    if above:
        t = min(above, key=lambda g: g["mean"])["min"]
    else:
        t = float(I["hi250"][k])
    return float(t) if np.isfinite(t) else None


def fill_limit(L, O, order_px, watch_start, watch_end):
    """First session in [watch_start, watch_end] with L <= order_px; fill at the
    open on a gap through, else at the order. Returns (idx, px) or None."""
    for t in range(watch_start, watch_end + 1):
        if t >= len(L):
            break
        if np.isfinite(L[t]) and np.isfinite(O[t]) and L[t] <= order_px:
            return t, float(O[t] if O[t] <= order_px else order_px)
    return None


def entry_population(P, I_by_stock, universe):
    """E-SN and E-BRK entry populations for one universe mask.

    State machine per stock, days ascending: one setup at a time; a new setup
    replaces a pending UNFILLED order (counted superseded; the old order's fill
    chances are tested only up to the day before the replacement); a fill locks
    the stock for MAX_HOLD sessions (arm-independent, so every arm trades the
    identical fill set); an unfilled order past its WATCH expires (counted).

    No returns are computed here — this is the G0 census engine and the shared
    entry definition for G1."""
    C = P["close"]
    dates = C.index
    T = len(dates)
    t_end = T - 2                     # a signal needs a next-open bar to trade
    trades, events = [], []
    brk_trades = []
    for tk in C.columns:
        if tk not in I_by_stock or not universe[tk].any():
            continue
        O = P["open"][tk].values.astype(float)
        H = P["high"][tk].values.astype(float)
        L = P["low"][tk].values.astype(float)
        Cl = C[tk].values.astype(float)
        V = P["volume"][tk].values.astype(float)
        I = I_by_stock[tk]
        liq = np.isfinite(I["adv20"]) & (I["adv20"] >= ADV20_MIN)
        n_fin = np.isfinite(Cl).sum()
        if n_fin < PIVOT_WINDOW + 2 * PIVOT_HALF + 2:
            continue

        # ── E-SN ── (eager state machine: the pending order's fill is tested
        # every session of its watch; a fill locks the stock immediately, so no
        # later signal can be mis-classified against a stale pending. Era
        # membership is by SIGNAL month; signals after ERA_END are counted and
        # never enrolled.)
        pending = None
        lock_until = -1
        for k in range(PIVOT_WINDOW + 2 * PIVOT_HALF, t_end + 1):
            if pending is not None:
                if k > pending["s"]:
                    f = fill_limit(L, O, pending["zone_top"], k, k)
                    if f is not None:
                        trades.append(_snipe_trade(pending, f))
                        lock_until = f[0] + MAX_HOLD
                        events.append({"kind": "fill", "month": pending["month"]})
                        pending = None
                    elif k > pending["s"] + WATCH:
                        events.append({"kind": "expired", "month": pending["month"]})
                        pending = None
            if not liq[k]:
                continue
            sig = sniper_signal_at(k, O, H, L, Cl, I)
            if sig is None:
                continue
            sig.update({"ticker": tk, "s": k, "month": str(dates[k])[:7]})
            if sig["month"] > ERA_END:
                events.append({"kind": "out_of_window", "month": sig["month"]})
                continue
            events.append({"kind": "setup", "month": sig["month"]})
            if k <= lock_until:
                events.append({"kind": "setup_while_locked", "month": sig["month"]})
                continue
            if pending is not None:
                events.append({"kind": "superseded", "month": pending["month"]})
            pending = sig
        if pending is not None:
            f = fill_limit(L, O, pending["zone_top"], pending["s"] + 1,
                           pending["s"] + WATCH)
            if f is not None:
                trades.append(_snipe_trade(pending, f))
                events.append({"kind": "fill", "month": pending["month"]})
            else:
                events.append({"kind": "expired", "month": pending["month"]})

        # ── E-BRK ──
        lock_until = -1
        hi20 = I["hi20"]
        for k in range(PIVOT_WINDOW + 2 * PIVOT_HALF, t_end + 1):
            if not (liq[k] and np.isfinite(Cl[k]) and np.isfinite(hi20[k])
                    and Cl[k] > hi20[k] and k > lock_until):
                continue
            if str(dates[k])[:7] > ERA_END:
                continue
            if not (np.isfinite(O[k + 1]) and O[k + 1] > 0):
                continue
            entry = float(O[k + 1])
            atr_k = float(I["atr14"][k])
            tgt = resistance_target_at(k, H, L, Cl, I, Cl[k])
            brk_trades.append({"ticker": tk, "s": k, "t1": k + 1, "entry": entry,
                               "zone_top": entry,
                               "zone_low": entry - BRK_ZONE_ATR * atr_k,
                               "stop": entry - X2_STOP_ATR * atr_k,
                               "target": tgt, "atr": atr_k,
                               "month": str(dates[k])[:7]})
            lock_until = k + 1 + MAX_HOLD
    return {"sniper": trades, "brk": brk_trades, "events": events}


def _snipe_trade(sig, fill):
    return {"ticker": sig["ticker"], "s": sig["s"], "t1": fill[0], "entry": fill[1],
            "zone_top": sig["zone_top"], "zone_low": sig["zone_low"],
            "stop": sig["stop"], "target": sig["target"], "atr": sig["atr"],
            "month": sig["month"]}


def month_to_era(m: str) -> str:
    return "E2" if m >= ERA_SPLIT else "E1"


def random_controls(P, I_by_stock, snipes, rng):
    """E-RND: one matched control per sniper fill. Same stock, a random liquid
    day r IN THE SAME ERA as the matched fill (seeded; picks drawn in fill-
    chronological order); entry at the next open (market, always fills). The
    matched E-SN trade's own levels are expressed in multiples of ITS signal-
    day ATR and re-applied with the control day's ATR. Era stratification (not
    spacing rules) keeps the control pool comparable; era metrics are computed
    per era anyway."""
    dates = P["close"].index
    months = np.array([str(d)[:7] for d in dates])
    T = len(dates)
    out, unmatched = [], 0
    for tr in sorted(snipes, key=lambda x: (x["s"], x["ticker"])):
        tk = tr["ticker"]
        if tk not in I_by_stock:
            unmatched += 1
            continue
        O = P["open"][tk].values.astype(float)
        I = I_by_stock[tk]
        liq = np.isfinite(I["adv20"]) & (I["adv20"] >= ADV20_MIN)
        era = month_to_era(tr["month"])
        era_ok = np.array([month_to_era(m) == era for m in months])
        cand = np.where(liq & era_ok[:T] &
                        np.concatenate([np.isfinite(O[1:]) & (O[1:] > 0), [False]]))[0]
        if cand.size == 0:
            unmatched += 1
            continue
        k = int(cand[int(rng.integers(0, cand.size))])
        entry = float(O[k + 1])
        atr_r = float(I["atr14"][k])
        d_stop = (tr["entry"] - tr["stop"]) / tr["atr"]
        d_tgt = (tr["target"] - tr["entry"]) / tr["atr"]
        d_zone = (tr["entry"] - tr["zone_low"]) / tr["atr"]
        out.append({"ticker": tk, "s": k, "t1": k + 1, "entry": entry,
                    "zone_top": entry, "zone_low": entry - d_zone * atr_r,
                    "stop": entry - d_stop * atr_r, "target": entry + d_tgt * atr_r,
                    "atr": atr_r, "month": str(dates[k])[:7],
                    "match_month": tr["month"], "match_sniper_s": tr["s"]})
    return out, unmatched


# ── Trade simulation (the frozen arms) ────────────────────────────────────────

def simulate_trade(tr, arm, P, I_cache):
    """One trade under one arm. Same-day precedence (frozen, conservative):
    (1) stop (gap -> open), (2) pending limit fills (gap -> open), (3) target
    (gap -> open), (4) close-based events (P3 add, P4 arming, X4 MA20 exit, X5
    time stop), (5) chandelier trail updated with the close for the next day.
    When the position exits, all pending leg orders cancel."""
    tk = tr["ticker"]
    O = P["open"][tk].values.astype(float)
    H = P["high"][tk].values.astype(float)
    L = P["low"][tk].values.astype(float)
    C = P["close"][tk].values.astype(float)
    if tk not in I_cache:
        I_cache[tk] = stock_indicators(O, H, L, C, P["volume"][tk].values.astype(float))
    ma20 = I_cache[tk]["ma20"]
    T = len(C)
    s, t1, atr = tr["s"], tr["t1"], tr["atr"]
    legs, buys = [], []

    def buy(idx, px, qty):
        legs.append((int(idx), float(px), qty, "buy"))
        buys.append((int(idx), float(px), qty))

    def sell(idx, px, qty):
        legs.append((int(idx), float(px), qty, "sell"))

    # ── entry ──
    if arm == "P1":
        buy(t1, tr["entry"], 0.5)      # first half: already filled at t1
        pending_half2 = {"px": tr["zone_low"], "cancel": s + WATCH}
    else:
        pending_half2 = None
        buy(t1, tr["entry"], 1.0)
    first_px, first_qty = buys[0][1], buys[0][2]
    core_qty = sum(q for _, _, q in buys)

    pending_add = None      # P2 limit
    p3_done = p4_armed = False
    topup = None            # P4: {'entry_px','entry_idx','qty','sell_px','exited'}

    # ── exit levels for this arm ──
    if arm == "X0":
        stop_px = target_px = None
    elif arm == "X2":
        stop_px, target_px = tr["entry"] - X2_STOP_ATR * atr, tr["entry"] + X2_TGT_ATR * atr
    elif arm == "X6":
        stop_px, target_px = None, tr["target"]
    elif arm == "X4":
        stop_px, target_px = tr["stop"], None
    elif arm == "X3":
        stop_px, target_px = tr["stop"], None
    else:                                  # X1, X5, P0..P4: structure stop + target
        stop_px, target_px = tr["stop"], tr["target"]
    hold_max = 20 if arm == "X0" else MAX_HOLD
    k_end = min(t1 + hold_max, T - 1)
    trail_hi = float(first_px)             # chandelier anchor: the entry itself

    exit_idx = exit_px = None
    reason = None
    k = t1
    while k <= k_end:
        hi_k, lo_k, cl_k = H[k], L[k], C[k]
        if np.isfinite(lo_k):
            eff_stop = stop_px
            if arm == "X3":
                trail_stop = trail_hi - X3_TRAIL_ATR * atr
                eff_stop = max(stop_px, trail_stop) if stop_px is not None else trail_stop
            # (1) stop first — conservative when stop and target share a day
            if eff_stop is not None and lo_k <= eff_stop:
                exit_idx, exit_px, reason = k, float(O[k] if O[k] <= eff_stop else eff_stop), "stop"
                break
            # (2) pending leg fills (second half, P2 add, P4 top-up, P4 top-up sale)
            if pending_half2 is not None and k <= pending_half2["cancel"] \
                    and lo_k <= pending_half2["px"]:
                px = O[k] if O[k] <= pending_half2["px"] else pending_half2["px"]
                buy(k, float(px), 0.5)
                core_qty += 0.5
                pending_half2 = None
            if pending_add is not None and lo_k <= pending_add:
                px = O[k] if O[k] <= pending_add else pending_add
                buy(k, float(px), 0.5)
                core_qty += 0.5
                pending_add = None
            if topup is not None:
                if topup["entry_px"] is None and k > topup["armed_day"] \
                        and lo_k <= topup["px"]:
                    fpx = O[k] if O[k] <= topup["px"] else topup["px"]
                    buy(k, float(fpx), 0.5)
                    topup.update({"entry_px": float(fpx), "entry_idx": k,
                                  "sell_px": float(fpx) + P4_SELL_ATR * atr,
                                  "exited": False})
                if topup["entry_px"] is not None and not topup["exited"] \
                        and k > topup["entry_idx"] and hi_k >= topup["sell_px"]:
                    px = O[k] if O[k] >= topup["sell_px"] else topup["sell_px"]
                    sell(k, float(px), topup["qty"])
                    topup["exited"] = True
            # (3) target
            if target_px is not None and hi_k >= target_px:
                exit_idx, exit_px, reason = k, float(O[k] if O[k] >= target_px else target_px), "target"
                break
        # (4) close-based events
        if np.isfinite(cl_k):
            if arm == "P2" and pending_add is None and core_qty < 1.5 \
                    and tr["entry"] - P2_ADD_ATR * atr > tr["stop"]:
                pending_add = tr["entry"] - P2_ADD_ATR * atr
            if arm == "P3" and not p3_done and cl_k >= tr["entry"] + P3_ADD_ATR * atr:
                buy(k, float(cl_k), 0.5)
                core_qty += 0.5
                p3_done = True
            if arm == "P4" and not p4_armed and cl_k >= tr["entry"] + X5_PROFIT_ATR * atr:
                p4_armed = True
                topup = {"px": tr["entry"] - P4_PULLBACK_ATR * atr, "armed_day": k,
                         "entry_px": None, "entry_idx": None, "qty": 0.5,
                         "sell_px": None, "exited": None}
            # (5) trail update for subsequent days
            if k >= t1:
                trail_hi = max(trail_hi, cl_k)
            if arm == "X4" and k > t1 and np.isfinite(ma20[k]) and cl_k < ma20[k]:
                exit_idx, exit_px, reason = k, float(cl_k), "ma20"
                break
            if arm == "X5" and k == t1 + X5_TIME and cl_k < tr["entry"] + X5_PROFIT_ATR * atr:
                exit_idx, exit_px, reason = k, float(cl_k), "time10"
                break
        # P4 top-up fill (limit at entry - 0.5 ATR once armed; lives until trade end)
        if topup is not None and topup["entry_px"] is None and np.isfinite(lo_k) \
                and lo_k <= topup["px"]:
            fpx = O[k] if O[k] <= topup["px"] else topup["px"]
            topup.update({"entry_px": float(fpx), "entry_idx": k,
                          "sell_px": float(fpx) + P4_SELL_ATR * atr, "exited": False})
        k += 1
    if exit_idx is None:
        exit_idx = k_end
        exit_px = float(C[k_end])
        reason = ("hold20" if arm == "X0" else "max60") if k_end < T - 1 else "eos"

    # ── close everything at the exit ──
    if topup is not None and topup["entry_px"] is not None and not topup["exited"]:
        sell(exit_idx, float(exit_px), topup["qty"])
        topup["exited"] = True
    sell(exit_idx, float(exit_px), core_qty)

    gross = sum(px * q for _, px, q, sd in legs if sd == "sell") - \
        sum(px * q for _, px, q, sd in legs if sd == "buy")
    buy_notional = sum(px * q for _, px, q in buys)
    sell_notional = sum(px * q for _, px, q, sd in legs if sd == "sell")
    net = gross - (COST_BUY + SLIP_RT) * buy_notional - COST_SELL * sell_notional
    seg = L[t1:exit_idx + 1]
    lo_since = np.nanmin(seg) if np.isfinite(seg).any() else float("nan")
    init_risk = (first_px - tr["stop"]) * first_qty
    return {
        "ticker": tk, "signal_s": s, "entry_idx": t1, "exit_idx": int(exit_idx),
        "exit_px": float(exit_px), "hold": int(exit_idx - t1), "reason": reason,
        "net_pct": net / buy_notional if buy_notional > 0 else float("nan"),
        "R": net / init_risk if init_risk > 0 else float("nan"),
        "mae_pct": (lo_since / first_px - 1.0) if np.isfinite(lo_since) else float("nan"),
        "mae_R": ((first_px - lo_since) / (first_px - tr["stop"]))
        if np.isfinite(lo_since) and first_px > tr["stop"] else float("nan"),
        "net": float(net), "buy_notional": float(buy_notional),
        "entry_month": tr["month"], "n_legs": len(legs),
    }


def run_arm(trades, arm, P, I_cache=None):
    I_cache = {} if I_cache is None else I_cache
    return [simulate_trade(tr, arm, P, I_cache) for tr in trades]


# ── Statistics / metrics ──────────────────────────────────────────────────────

def paired_t(a, b):
    """One-sample t of the paired differences a-b (matched trades), H1: > 0."""
    d = np.asarray([x - y for x, y in zip(a, b)
                    if np.isfinite(x) and np.isfinite(y)], dtype=float)
    if d.size < 3:
        return float("nan")
    se = d.std(ddof=1) / math.sqrt(d.size)
    if se == 0:
        return float("inf") if d.mean() > 0 else float("-inf")
    return float(d.mean() / se)


def describe(outcomes):
    nets = np.array([o["net_pct"] for o in outcomes if np.isfinite(o["net_pct"])])
    rs = np.array([o["R"] for o in outcomes if np.isfinite(o["R"])])
    wins = nets[nets > 0]
    losses = nets[nets <= 0]
    mae = np.array([o["mae_pct"] for o in outcomes if np.isfinite(o["mae_pct"])])
    return {
        "n": int(nets.size),
        "mean_net_pct": float(nets.mean()) if nets.size else None,
        "median_net_pct": float(np.median(nets)) if nets.size else None,
        "expectancy_R": float(rs.mean()) if rs.size else None,
        "win_rate": float(wins.size / nets.size) if nets.size else None,
        "avg_win": float(wins.mean()) if wins.size else None,
        "avg_loss": float(losses.mean()) if losses.size else None,
        "mean_hold": float(np.mean([o["hold"] for o in outcomes])) if outcomes else None,
        "mae_deciles": {f"p{p}": float(np.percentile(mae, p))
                        for p in (10, 25, 50, 75, 90)} if mae.size else {},
        "reasons": {r: sum(1 for o in outcomes if o["reason"] == r)
                    for r in {o["reason"] for o in outcomes}},
    }


def by_year(outcomes):
    out = {}
    for o in outcomes:
        y = o["entry_month"][:4]
        out.setdefault(y, []).append(o["net_pct"])
    return {y: {"n": len(v), "mean_net_pct": float(np.nanmean(v))}
            for y, v in sorted(out.items())}


def assemble_portfolio(outcomes, trades, dates_index, closes_getter):
    """Equal-risk portfolio (frozen): 1% of equity risked per trade, <= 10
    concurrent, next signal skipped when full; daily MTM on closes; costs on the
    portfolio's own fills (buy 0.15% + slippage 0.20% on buy notional, sell
    0.25% on sale notional). Returns CAGR, max drawdown, worst rolling 250-
    session return."""
    T = len(dates_index)
    cash = 1.0
    open_pos = {}
    curve = np.ones(T)
    taken = 0
    sched = sorted(zip(trades, outcomes), key=lambda x: (x[0]["t1"], x[0]["ticker"]))
    ji = 0
    for t in range(T):
        for key in [k for k, p in open_pos.items() if p["exit_idx"] == t]:
            p = open_pos.pop(key)
            cash += p["shares"] * p["exit_px"] * (1.0 - COST_SELL)
        while ji < len(sched) and sched[ji][0]["t1"] == t:
            tr, oc = sched[ji]
            ji += 1
            if len(open_pos) >= PORT_MAX_CONCURRENT:
                continue
            mtm = sum(p["shares"] * p["last_px"] for p in open_pos.values())
            equity = cash + mtm
            risk_per_unit = max(tr["entry"] - tr["stop"], 1e-9)
            shares = (RISK_FRAC * equity) / risk_per_unit
            if shares <= 0 or not np.isfinite(shares):
                continue
            cash -= shares * tr["entry"] * (1.0 + COST_BUY + SLIP_RT)
            open_pos[(tr["ticker"], tr["s"])] = {
                "shares": shares, "exit_idx": oc["exit_idx"], "exit_px": oc["exit_px"],
                "last_px": tr["entry"]}
            taken += 1
        mtm = 0.0
        for key, p in open_pos.items():
            c = closes_getter(p_key_ticker(key))
            px = c[t] if np.isfinite(c[t]) else p["last_px"]
            p["last_px"] = float(px) if np.isfinite(px) else p["last_px"]
            mtm += p["shares"] * p["last_px"]
        curve[t] = cash + mtm
    years = T / PORT_SESSIONS_PER_YEAR
    cagr = float((curve[-1] / curve[0]) ** (1.0 / years) - 1.0) if years > 0 else float("nan")
    max_dd = float((curve / np.maximum.accumulate(curve) - 1.0).min())
    w = int(PORT_SESSIONS_PER_YEAR)
    worst_12m = float(np.min(curve[w:] / curve[:-w] - 1.0)) if T > w else float("nan")
    return {"cagr": cagr, "max_dd": max_dd, "worst_12m": worst_12m,
            "n_signals": len(sched), "n_taken": taken,
            "final_equity": float(curve[-1])}


def p_key_ticker(key):
    return key[0]


# ── Census (G0; counts only, no returns) ──────────────────────────────────────

def census_g0(hist=None, splits=None) -> dict:
    t0 = datetime.now(timezone.utc)
    P = load_panel(hist=hist, splits=splits)
    C = P["close"]
    dates = C.index
    adv20 = (C * P["volume"]).rolling(20, min_periods=20).mean()
    owner = adv20 >= ADV20_MIN
    adv60 = (C * P["volume"]).rolling(60, min_periods=ADV60_MIN_PERIODS).mean()
    parity = (adv60.rank(axis=1, ascending=False, na_option="keep") <= ADV60_TOP) & C.notna()
    I_by_stock = {}
    for tk in C.columns:
        if C[tk].notna().sum() >= PIVOT_WINDOW + 2 * PIVOT_HALF + 2:
            I_by_stock[tk] = stock_indicators(
                P["open"][tk].values.astype(float), P["high"][tk].values.astype(float),
                P["low"][tk].values.astype(float),
                C[tk].values.astype(float), P["volume"][tk].values.astype(float))
    res = {"generated_utc": t0.isoformat(), "git_commit": git_commit(),
           "census_kind": "setup_and_fill_counts_only_no_returns",
           "eras": {"E1": "signals 2001-01..2021-09", "E2": "signals 2021-10..2026-09"},
           "panel": {"sessions": int(len(dates)), "tickers": int(C.shape[1]),
                     "first": str(dates[0].date()), "last": str(dates[-1].date())}}
    with db_connect(read_only=True) as conn:
        res["dataset_fingerprint"] = dataset_fingerprint(conn)
    for label, uni in (("owner_adv20_10bn", owner), ("parity_top150_adv60", parity)):
        pop = entry_population(P, I_by_stock, uni)
        rng = np.random.default_rng(SEED)
        controls, unmatched = random_controls(P, I_by_stock, pop["sniper"], rng)
        eras = {}
        for era in ("E1", "E2"):
            eras[era] = {
                "E_SN_setups": 0, "E_SN_fills": 0, "E_SN_expired": 0,
                "E_SN_superseded": 0, "E_SN_setup_while_locked": 0,
                "E_RND_matches": 0, "E_BRK_signals": 0,
                "sniper_fills_by_year": {}, "brk_signals_by_year": {}}
        for ev in pop["events"]:
            era = month_to_era(ev["month"])
            if ev["kind"] == "setup":
                eras[era]["E_SN_setups"] += 1
            elif ev["kind"] == "fill":
                eras[era]["E_SN_fills"] += 1
            elif ev["kind"] == "expired":
                eras[era]["E_SN_expired"] += 1
            elif ev["kind"] == "superseded":
                eras[era]["E_SN_superseded"] += 1
            elif ev["kind"] == "setup_while_locked":
                eras[era]["E_SN_setup_while_locked"] += 1
            elif ev["kind"] == "out_of_window":
                eras[era]["E_SN_out_of_window"] = \
                    eras[era].get("E_SN_out_of_window", 0) + 1
        for tr in pop["sniper"]:
            y = tr["month"][:4]
            eras[month_to_era(tr["month"])]["sniper_fills_by_year"][y] = \
                eras[month_to_era(tr["month"])]["sniper_fills_by_year"].get(y, 0) + 1
        for tr in pop["brk"]:
            era = month_to_era(tr["month"])
            eras[era]["E_BRK_signals"] += 1
            y = tr["month"][:4]
            eras[era]["brk_signals_by_year"][y] = \
                eras[era]["brk_signals_by_year"].get(y, 0) + 1
        for tr in controls:
            eras[month_to_era(tr["match_month"])]["E_RND_matches"] += 1
        stocks_setup = len({tr["ticker"] for tr in pop["sniper"]})
        res[label] = {
            "eras": eras,
            "whole": {"E_SN_setups_total": sum(e["E_SN_setups"] for e in eras.values()),
                      "E_SN_fills_total": len(pop["sniper"]),
                      "E_SN_stocks_with_fill": stocks_setup,
                      "E_BRK_signals_total": len(pop["brk"]),
                      "E_BRK_stocks_with_signal": len({tr["ticker"] for tr in pop["brk"]}),
                      "E_RND_matches_total": len(controls),
                      "E_RND_unmatched": unmatched},
        }
    return res


# ── G1 assembly (frozen now, exercised on synthetic panels only) ─────────────

ALL_ARMS = tuple(EXIT_ARMS) + tuple(POS_ARMS)


def recommend(blocks):
    """The frozen recommendation rule. blocks[arm][era] = {"expectancy_R",
    "paired_t_vs_base", "port_max_dd"}. Recommended over the baseline iff in
    BOTH eras: expectancy in R higher AND paired t >= 2.0 AND the portfolio max
    drawdown is not worse by more than 20% relative. Harmful iff worse (lower
    expectancy) in both eras with t <= -2.0. Everything else: no reliable
    difference."""
    out = {}
    for arm, by_era in blocks.items():
        if arm not in ("X1", "X2", "X3", "X4", "X5", "X6", "P1", "P2", "P3", "P4"):
            continue
        base = "X0" if arm.startswith("X") else "P0"
        e = {}
        for era in ("E1", "E2"):
            a, b = by_era[era], blocks[base][era]
            e[era] = {
                "expHigher": (a["expectancy_R"] is not None and b["expectancy_R"] is not None
                              and a["expectancy_R"] > b["expectancy_R"]),
                "t": a["paired_t_vs_base"],
                "dd_ok": (a["port_max_dd"] is not None and b["port_max_dd"] is not None
                          and a["port_max_dd"] >= b["port_max_dd"] * 1.2 - 1e-12),
            }
        both = all(e[era]["expHigher"] and np.isfinite(e[era]["t"])
                   and e[era]["t"] >= 2.0 and e[era]["dd_ok"] for era in ("E1", "E2"))
        worse_both = all(
            e[era]["t"] is not None and np.isfinite(e[era]["t"]) and e[era]["t"] <= -2.0
            and not e[era]["expHigher"] for era in ("E1", "E2"))
        out[arm] = {"per_era": e,
                    "verdict": "RECOMMENDED" if both else
                               ("FLAGGED_HARMFUL" if worse_both else "NO_RELIABLE_DIFFERENCE")}
    return out


def evaluate(P, I_by_stock, universes) -> dict:
    """Full G1 assembly on the owner screen: all 12 arms x eras metrics,
    portfolios, paired tests vs the right baseline, E-SN vs E-RND, the frozen
    recommendation rule, and the P2 tail question. E-BRK is reported, never
    recommended."""
    owner = universes["owner_adv20_10bn"]
    pop = entry_population(P, I_by_stock, owner)
    rng = np.random.default_rng(SEED)
    controls, unmatched = random_controls(P, I_by_stock, pop["sniper"], rng)
    pops = {"E_SN": pop["sniper"], "E_RND": controls, "E_BRK": pop["brk"]}
    I_cache = {}
    closes = {tk: P["close"][tk].values.astype(float) for tk in P["close"].columns}

    def getter(tk):
        return closes.get(tk, np.full(len(P["close"].index), np.nan))

    result = {"populations": {}, "arms": {}, "recommendations": {}, "e_sn_vs_e_rnd": {},
              "p2_tail": {}, "e_rnd_unmatched": unmatched}
    for pname, trades in pops.items():
        result["populations"][pname] = {"n_trades": len(trades)}
        for era in ("E1", "E2"):
            tr_e = [t for t in trades if month_to_era(t["month"]) == era]
            oc = {arm: run_arm(tr_e, arm, P, I_cache) for arm in ALL_ARMS}
            pf = {arm: assemble_portfolio(o, tr_e, P["close"].index, getter)
                  for arm, o in oc.items()}
            keys = [(t["ticker"], t["s"]) for t in tr_e]
            paired = {}
            for arm in ALL_ARMS:
                base_arm = "X0" if arm.startswith("X") else "P0"
                if arm == base_arm:
                    paired[arm] = None
                    continue
                base_map = dict(zip(keys, oc[base_arm]))
                m = [(o, base_map[k]) for o, k in zip(oc[arm], keys) if k in base_map]
                paired[arm] = {
                    "paired_t_R": paired_t([x["R"] for x, _ in m], [y["R"] for _, y in m]),
                    "mean_R_diff": float(np.nanmean([x["R"] - y["R"] for x, y in m]))
                    if m else None, "n_matched": len(m)}
            result["arms"].setdefault(pname, {})[era] = {
                "n": len(tr_e),
                "metrics": {arm: describe(o) for arm, o in oc.items()},
                "portfolio": pf, "paired_vs_base": paired,
                "by_year": {arm: by_year(o) for arm, o in oc.items()},
            }
    # frozen recommendation rule (exits vs X0, positions vs P0), per population
    for pname in ("E_SN", "E_RND"):
        blocks = {}
        for arm in ALL_ARMS:
            blocks[arm] = {era: {
                "expectancy_R": result["arms"][pname][era]["metrics"][arm]["expectancy_R"],
                "paired_t_vs_base": (result["arms"][pname][era]["paired_vs_base"][arm]
                                     or {}).get("paired_t_R"),
                "port_max_dd": result["arms"][pname][era]["portfolio"][arm]["max_dd"],
            } for era in ("E1", "E2")}
        result["recommendations"][pname] = recommend(blocks)
    # E-SN vs E-RND (does the entry add anything), per arm, per era
    sn = pops["E_SN"]
    sn_keys = [(t["ticker"], t["s"]) for t in sn]
    sn_era = {k: month_to_era(t["month"]) for k, t in zip(sn_keys, sn)}
    rn_map = {(t["ticker"], t["match_sniper_s"]): i for i, t in enumerate(pops["E_RND"])}
    for arm in ALL_ARMS:
        oc_sn = run_arm(sn, arm, P, I_cache)
        oc_rn = run_arm(pops["E_RND"], arm, P, I_cache)
        for era in ("E1", "E2"):
            pairs = [(o, oc_rn[rn_map[k]]) for k, o in zip(sn_keys, oc_sn)
                     if k in rn_map and sn_era[k] == era]
            result["e_sn_vs_e_rnd"].setdefault(arm, {})[era] = {
                "paired_t_R": paired_t([x["R"] for x, _ in pairs],
                                       [y["R"] for _, y in pairs]),
                "n_matched": len(pairs)}
    # P2 tail question: expectancy vs win rate vs worst-5% tail, vs P0
    for pname in ("E_SN", "E_RND"):
        trades = pops[pname]
        tails = {}
        for label, arm in (("P0", "P0"), ("P2", "P2")):
            oc = run_arm(trades, arm, P, I_cache)
            nets = np.sort(np.array([o["net_pct"] for o in oc
                                     if np.isfinite(o["net_pct"])]))
            k = max(1, int(math.ceil(0.05 * nets.size))) if nets.size else 0
            tails[label] = {"worst5pct_mean": float(nets[:k].mean()) if k else None,
                            "win_rate": float((nets > 0).mean()) if nets.size else None,
                            "expectancy_R": float(np.nanmean([o["R"] for o in oc]))
                            if oc else None}
        result["p2_tail"][pname] = tails
    return result


def run_g1(hist=None, splits=None) -> dict:
    """THE single run (gated). Census + arms + portfolios + recommendations ->"""
    if os.environ.get(G1_ENV) != "1":
        raise SystemExit("G1 is gated: set EXIT_STUDY_G1_APPROVED=1 only after "
                         "owner/planner approval of the frozen G0.")
    raise NotImplementedError("G1 orchestration (RESULT/VERDICT/PRACTICE_NOTE "
                              "writers) is wired at the G1 gate; the frozen "
                              "simulators are exercised by the PIT tests.")


if __name__ == "__main__":
    print(__doc__)
    print("G0 state: census only. run_g1() is gated on EXIT_STUDY_G1_APPROVED=1.")
