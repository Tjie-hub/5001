"""Portfolio v2 — the G1-bis portfolio layer (2026-10-07, PORTFOLIO_FIX.md).

Fixes the three G1 portfolio defects: legs are modelled per the frozen arm
definitions, cash can never go negative, positions are capped (20% at entry,
30% at adds), and skips are counted by reason. The frozen trio is untouched:
simulate_legs() is a faithful TRANSCRIPTION of the frozen simulate_trade()
day-loop (same precedence, gap rules, arming rules, bottom-of-loop P4 fill),
proven equivalent by the parity gate (legs' net_pct == frozen net_pct within
1e-9). Quantities here are canonical frozen units (1.0 base / 0.5 adds); the
engine scales them and sizes each leg ON ITS OWN FILL DAY.

Not one of the three frozen artifacts; covered by PORTFOLIO_FIX.sha256.
"""
from __future__ import annotations

import numpy as np

import exit_study as E

BUY_COST = E.COST_BUY + E.SLIP_RT          # 0.35% on buy notional
SELL_COST = E.COST_SELL                    # 0.25% on sale notional
RISK_FRAC = 0.01
ENTRY_CAP = 0.20
ADD_CAP = 0.30
MIN_ENTRY_NOTIONAL = 0.02
MIN_ADD_NOTIONAL = 0.01
MAX_POSITIONS = 10


# ── leg reconstruction (transcription of the frozen simulate_trade) ───────────

def simulate_legs(tr, arm, P, I_by_stock):
    """Canonical legs for one trade under one arm, mirroring the frozen
    simulate_trade() exactly. Returns {legs: [(idx, px, qty, role)], exit_idx,
    exit_px, exit_reason, buy_notional, net, net_pct}. Roles: entry, half2,
    add, topup_buy, topup_sell, exit. net/net_pct use the frozen cost model so
    the parity gate can compare them to the frozen outcome directly."""
    tk = tr["ticker"]
    O = P["open"][tk].values.astype(float)
    H = P["high"][tk].values.astype(float)
    L = P["low"][tk].values.astype(float)
    C = P["close"][tk].values.astype(float)
    ma20 = I_by_stock[tk]["ma20"]
    T = len(C)
    s, t1, atr = tr["s"], tr["t1"], tr["atr"]
    legs, buys = [], []

    def buy(idx, px, qty, role):
        legs.append((int(idx), float(px), qty, role))
        buys.append((float(px), qty))

    def sell(idx, px, qty, role):
        legs.append((int(idx), float(px), qty, role))

    if arm == "P1":
        buy(t1, tr["entry"], 0.5, "entry")
        pending_half2 = {"px": tr["zone_low"], "cancel": s + E.WATCH}
    else:
        pending_half2 = None
        buy(t1, tr["entry"], 1.0, "entry")
    first_px = buys[0][0]
    core_qty = sum(q for _, q in buys)

    pending_add = None
    p3_done = p4_armed = False
    topup = None

    if arm == "X0":
        stop_px = target_px = None
    elif arm == "X2":
        stop_px, target_px = tr["entry"] - E.X2_STOP_ATR * atr, tr["entry"] + E.X2_TGT_ATR * atr
    elif arm == "X6":
        stop_px, target_px = None, tr["target"]
    else:                                    # X1, X3, X4, X5, P0..P4
        stop_px, target_px = tr["stop"], (None if arm in ("X3", "X4") else tr["target"])
    hold_max = 20 if arm == "X0" else E.MAX_HOLD
    k_end = min(t1 + hold_max, T - 1)
    trail_hi = float(first_px)

    exit_idx = exit_px = None
    reason = None
    k = t1
    while k <= k_end:
        hi_k, lo_k, cl_k = H[k], L[k], C[k]
        if np.isfinite(lo_k):
            eff_stop = stop_px
            if arm == "X3":
                trail_stop = trail_hi - E.X3_TRAIL_ATR * atr
                eff_stop = max(stop_px, trail_stop) if stop_px is not None else trail_stop
            if eff_stop is not None and lo_k <= eff_stop:
                exit_idx, exit_px, reason = k, float(O[k] if O[k] <= eff_stop else eff_stop), "stop"
                break
            if pending_half2 is not None and k <= pending_half2["cancel"] \
                    and lo_k <= pending_half2["px"]:
                px = O[k] if O[k] <= pending_half2["px"] else pending_half2["px"]
                buy(k, px, 0.5, "half2")
                core_qty += 0.5
                pending_half2 = None
            if pending_add is not None and lo_k <= pending_add:
                px = O[k] if O[k] <= pending_add else pending_add
                buy(k, px, 0.5, "add")
                core_qty += 0.5
                pending_add = None
            if topup is not None:
                if topup["entry_px"] is None and k > topup["armed_day"] \
                        and lo_k <= topup["px"]:
                    fpx = O[k] if O[k] <= topup["px"] else topup["px"]
                    buy(k, fpx, 0.5, "topup_buy")
                    topup.update({"entry_px": float(fpx), "entry_idx": k,
                                  "sell_px": float(fpx) + E.P4_SELL_ATR * atr,
                                  "exited": False})
                if topup["entry_px"] is not None and not topup["exited"] \
                        and k > topup["entry_idx"] and hi_k >= topup["sell_px"]:
                    px = O[k] if O[k] >= topup["sell_px"] else topup["sell_px"]
                    sell(k, px, 0.5, "topup_sell")
                    topup["exited"] = True
            if target_px is not None and hi_k >= target_px:
                exit_idx, exit_px, reason = k, float(O[k] if O[k] >= target_px else target_px), "target"
                break
        if np.isfinite(cl_k):
            if arm == "P2" and pending_add is None and core_qty < 1.5 \
                    and tr["entry"] - E.P2_ADD_ATR * atr > tr["stop"]:
                pending_add = tr["entry"] - E.P2_ADD_ATR * atr
            if arm == "P3" and not p3_done and cl_k >= tr["entry"] + E.P3_ADD_ATR * atr:
                buy(k, cl_k, 0.5, "add")
                core_qty += 0.5
                p3_done = True
            if arm == "P4" and not p4_armed and cl_k >= tr["entry"] + E.X5_PROFIT_ATR * atr:
                p4_armed = True
                topup = {"px": tr["entry"] - E.P4_PULLBACK_ATR * atr, "armed_day": k,
                         "entry_px": None, "entry_idx": None, "qty": 0.5,
                         "sell_px": None, "exited": None}
            if k >= t1:
                trail_hi = max(trail_hi, cl_k)
            if arm == "X4" and k > t1 and np.isfinite(ma20[k]) and cl_k < ma20[k]:
                exit_idx, exit_px, reason = k, float(cl_k), "ma20"
                break
            if arm == "X5" and k == t1 + E.X5_TIME and cl_k < tr["entry"] + E.X5_PROFIT_ATR * atr:
                exit_idx, exit_px, reason = k, float(cl_k), "time10"
                break
        k += 1
    if exit_idx is None:
        exit_idx = k_end
        exit_px = float(C[k_end])
        reason = ("hold20" if arm == "X0" else "max60") if k_end < T - 1 else "eos"

    if topup is not None and topup["entry_px"] is not None and not topup["exited"]:
        sell(exit_idx, float(exit_px), 0.5, "exit")     # topup rides with the core
        topup["exited"] = True
    sell(exit_idx, float(exit_px), core_qty, "exit")

    buy_notional = sum(px * q for px, q in buys)
    sell_notional = sum(px * q for i, px, q, r in legs if r in ("topup_sell", "exit"))
    net = sell_notional - buy_notional - BUY_COST * buy_notional - SELL_COST * sell_notional
    return {"legs": legs, "exit_idx": int(exit_idx), "exit_px": float(exit_px),
            "exit_reason": reason, "buy_notional": float(buy_notional),
            "net": float(net), "net_pct": float(net / buy_notional) if buy_notional > 0
            else float("nan")}


# ── the portfolio engine ──────────────────────────────────────────────────────

def _era_bounds(dates, era):
    months = np.array([str(d)[:7] for d in dates])
    lo = "2001-01" if era == "E1" else "2021-10"
    hi = "2021-09" if era == "E1" else "2026-09"
    idx = np.where((months >= lo) & (months <= hi))[0]
    return (int(idx[0]), int(idx[-1])) if idx.size else (0, len(dates) - 1)


def run_portfolio_v2(trades, legs_by_key, closes_by_ticker, dates_index, era,
                     record_fills=False):
    """One era book over the full date index (equity flat outside the era, as
    in G1). Each buy leg is sized on ITS OWN fill day: entries per the base
    rule (1% risk / 20% cap / cash), half2 cash-limited, adds and top-ups at
    50% of base capped to 30% of equity and cash. Cash can never go negative
    (every buy is cash-limited); min_cash is tracked and reported. With
    record_fills=True an audit list of buy fills is returned for tests."""
    T = len(dates_index)
    C = closes_by_ticker
    sched = sorted(trades, key=lambda t: (t["t1"], t["ticker"]))
    by_t1 = {}
    for tr in sched:
        by_t1.setdefault(tr["t1"], []).append(tr)
    later = {}                    # day -> [(key, role, px)] for post-entry buy legs
    for tr in sched:
        key = (tr["ticker"], tr["s"])
        for (idx, px, q, role) in legs_by_key.get(key, ()):
            if role in ("half2", "add", "topup_buy") and idx >= tr["t1"]:
                later.setdefault(idx, []).append((key, role, px))
    pos = {}                       # key -> {core_qty, topup_qty, last_px, exit_idx, exit_px, base_qty}
    cash = 1.0
    min_cash = 1.0
    curve = np.ones(T)
    exposure_sum = 0.0
    days_at_cap = 0
    fills = []
    era_lo, era_hi = _era_bounds(dates_index, era)
    stats = {"signals": len(sched), "taken": 0, "skipped_full": 0,
             "skipped_cash": 0, "skipped_tiny": 0, "adds_skipped": 0}

    def eq_ref(t):
        # cash + mark-to-market at the PRIOR close
        i = t - 1
        if i < 0:
            return cash
        mtm = 0.0
        for k, p in pos.items():
            c = C[k[0]]
            px = c[i] if i < len(c) else np.nan
            if not np.isfinite(px):
                px = p["last_px"]
            mtm += (p["core_qty"] + p["topup_qty"]) * float(px)
        return cash + mtm

    for t in range(T):
        # 1) exits first — free cash and slots on the exit day itself
        for k in [k for k, p in pos.items() if p["exit_idx"] == t]:
            p = pos.pop(k)
            qty = p["core_qty"] + p["topup_qty"]
            cash += qty * p["exit_px"] * (1.0 - SELL_COST)
        # 2) top-up sales scheduled today (sell the actual held top-up)
        for k, p in list(pos.items()):
            for (idx, px, q, role) in legs_by_key[k]:
                if role == "topup_sell" and idx == t and p["topup_qty"] > 0:
                    cash += p["topup_qty"] * px * (1.0 - SELL_COST)
                    p["topup_qty"] = 0.0
        # 3) entries scheduled today
        for tr in by_t1.get(t, ()):
            key = (tr["ticker"], tr["s"])
            legs = legs_by_key[key]
            if len(pos) >= MAX_POSITIONS:
                stats["skipped_full"] += 1
                continue
            eq = eq_ref(t)
            entry_leg = next(lg for lg in legs if lg[3] == "entry")
            entry_px = entry_leg[1]
            denom = tr["entry"] - tr["stop"]
            risk_qty = (RISK_FRAC * eq / denom) if (denom > 0 and eq > 0) else 0.0
            cap_qty = (ENTRY_CAP * eq / entry_px) if (entry_px > 0 and eq > 0) else 0.0
            cash_qty = cash / (entry_px * (1.0 + BUY_COST)) if entry_px > 0 else 0.0
            qty = min(risk_qty, cap_qty, cash_qty)
            if qty <= 0 or qty * entry_px < MIN_ENTRY_NOTIONAL * eq:
                # binding leg: "cash" only when the cash leg is strictly smallest (ties -> tiny)
                stats["skipped_cash" if cash_qty < min(risk_qty, cap_qty) - 1e-15
                      else "skipped_tiny"] += 1
                continue
            # P1 splits the base size: half at the zone top, half at the zone low
            has_half2 = any(lg[3] == "half2" for lg in legs)
            entry_qty = 0.5 * qty if has_half2 else qty
            cash -= entry_qty * entry_px * (1.0 + BUY_COST)
            exit_legs = [lg for lg in legs if lg[3] == "exit"]
            stats["taken"] += 1
            if record_fills:
                fills.append({"t": t, "key": key, "role": "entry", "qty": entry_qty,
                              "px": entry_px, "equity_ref": eq})
            pos[key] = {"core_qty": entry_qty, "topup_qty": 0.0, "last_px": entry_px,
                        "exit_idx": exit_legs[-1][0], "exit_px": exit_legs[-1][1],
                        "base_qty": qty}
        # 4) post-entry buy legs scheduled today, for taken positions (half2 / add / topup_buy)
        for (key, role, px) in later.get(t, ()):
            p = pos.get(key)
            if p is None:
                continue
            eq = eq_ref(t)
            if role == "half2":
                want = 0.5 * p["base_qty"]
                take = min(want, cash / (px * (1.0 + BUY_COST))) if px > 0 else 0.0
                take = max(take, 0.0)                      # no skip floor: the halves ARE the position
                if take > 0:
                    cash -= take * px * (1.0 + BUY_COST)
                    p["core_qty"] += take
                    if record_fills:
                        fills.append({"t": t, "key": key, "role": "half2",
                                      "qty": take, "px": px, "equity_ref": eq})
            else:                                          # add / topup_buy
                held = p["core_qty"] + p["topup_qty"]
                want = 0.5 * p["base_qty"]
                cap30 = max(0.0, ADD_CAP * eq / px - held) if px > 0 else 0.0
                by_cash = cash / (px * (1.0 + BUY_COST)) if px > 0 else 0.0
                take = max(0.0, min(want, cap30, by_cash))
                if take * px < MIN_ADD_NOTIONAL * eq:
                    stats["adds_skipped"] += 1
                    continue
                cash -= take * px * (1.0 + BUY_COST)
                if record_fills:
                    fills.append({"t": t, "key": key, "role": role,
                                  "qty": take, "px": px, "equity_ref": eq})
                if role == "topup_buy":
                    p["topup_qty"] += take
                else:
                    p["core_qty"] += take
        min_cash = min(min_cash, cash)
        # 5) mark to market at the close
        notional = 0.0
        for k, p in pos.items():
            c = C[k[0]]
            px = c[t] if t < len(c) else np.nan
            if not np.isfinite(px):
                px = p["last_px"]
            p["last_px"] = float(px)
            notional += (p["core_qty"] + p["topup_qty"]) * p["last_px"]
        curve[t] = cash + notional
        if era_lo <= t <= era_hi:
            if len(pos) >= MAX_POSITIONS:
                days_at_cap += 1
            if curve[t] > 0:
                exposure_sum += notional / curve[t]

    n_days = era_hi - era_lo + 1
    years_full = T / 250.0
    years_era = n_days / 250.0
    final = float(curve[-1])
    max_dd = float((curve / np.maximum.accumulate(curve) - 1.0).min())
    worst_12m = float(np.min(curve[250:] / curve[:-250] - 1.0)) if T > 250 else None
    stats.update({
        "cagr_full": float(final ** (1.0 / years_full) - 1.0) if final > 0 else None,
        "cagr_era": float(final ** (1.0 / years_era) - 1.0) if final > 0 else None,
        "max_dd": max_dd, "worst_12m": worst_12m, "final_equity": final,
        "avg_gross_exposure_era": exposure_sum / n_days if n_days else None,
        "pct_days_at_10_positions_era": days_at_cap / n_days if n_days else None,
        "min_cash": min_cash,
    })
    if record_fills:
        stats["fills"] = fills
    return stats
