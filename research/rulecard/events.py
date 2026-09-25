"""Event-time Rule Card engine (D-055 v2; design 2026-09-25): calendar-time, day-weighted.

A rule script's signal() returns a 0/1 flag per (ticker, date) row, known at that row's close
from rows dated <= it (LA-1 checks it). Each flag on an eligible row opens one position:

- entry at the name's NEXT own session's open (FILL-1). No bar, no volume or no open there =
  not tradeable: counted and dropped, because a fill that cannot happen has no return;
- held for `hold_sessions` of the name's OWN sessions, exit at that session's close. A name whose
  history ends first exits at its last close and is flagged stale (F-8: dropping it would
  condition on survival);
- never dropped for anything inside its holding window. FADE-001's >35% guard read the future
  (validity audit R-3); bad data fails SPL-1 instead.

Each session d: signal leg = EW mean of the open positions' returns (open->close on the entry
day, close->close after); book = EW close->close return of names eligible at their previous
session (BM-1: the EW liquid book, never IHSG). Daily excess = leg - book on days with >= 1 open
position. A month's value = mean daily excess on its position-days x sessions in the month, in
percent: the flagged sleeve's return relative to the book, comparable across months whatever the
event density. Why day-weighted: an avoidance overlay earns per day held, not per trade, and a
calendar-time series has no overlapping-window dependence to mis-cluster (audit R-1).

The monthly records carry the keys evaluate.py and checks.py already read, so the verdict logic is
shared with the month-end engine.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.rulecard import checks, engine

MIN_EVENT_DAYS = 5          # position-days a month needs to be valid
MAX_EVENT_SHARE = 0.50      # ID-1: a "signal" flagging most eligible rows is not a signal


def hold_sessions(card) -> int:
    return int(card["signal"]["hold_sessions"])


def _flag_array(pan: engine.Panel, flags: pd.Series) -> np.ndarray:
    return (flags.reindex(pan.P.index).fillna(0).values > 0) & pan.eligible.values


def _terciles(pan: engine.Panel, values) -> np.ndarray:
    """Tercile 1..3 of `values` among eligible rows of the same date; NaN elsewhere."""
    s = pd.Series(np.where(pan.eligible.values, values, np.nan), index=pan.P.index)
    pct = s.groupby(pan.P["date"].values).rank(pct=True, method="first")
    return np.ceil(pct.values * 3).clip(1, 3)


def build_events(pan: engine.Panel, flags: pd.Series, hold: int, start=None, end=None) -> pd.DataFrame:
    P = pan.P
    ev = _flag_array(pan, flags)
    d = P["date"].values
    if start is not None:
        ev &= d >= np.datetime64(pd.Timestamp(start))
    if end is not None:
        ev &= d <= np.datetime64(pd.Timestamp(end))
    s = np.flatnonzero(ev)
    rem = P.groupby("ticker", sort=False).cumcount(ascending=False).values
    op, vol = P["open"].values, P["volume"].values
    has_next = rem[s] >= 1
    e = np.where(has_next, s + 1, s)
    tradeable = has_next & (vol[e] > 0) & np.isfinite(op[e]) & (op[e] > 0)
    x = s + np.minimum(hold, rem[s])
    return pd.DataFrame({
        "ticker": P["ticker"].values[s], "signal_row": s, "entry_row": e, "exit_row": x,
        "signal_date": d[s], "entry_date": d[e], "exit_date": d[x],
        "tradeable": tradeable, "stale": (rem[s] < hold) & tradeable,
        "adv_terc": _terciles(pan, pan.F["adv20"].values)[s],
        "px_terc": _terciles(pan, P["close"].values)[s]})


def _positions(pan: engine.Panel, T: pd.DataFrame) -> pd.DataFrame:
    """One row per (event, held session): the day's return of that position."""
    e, x = T["entry_row"].values, T["exit_row"].values
    n = x - e + 1
    k = np.arange(n.sum()) - np.repeat(np.cumsum(n) - n, n)
    r = np.repeat(e, n) + k
    op, cl = pan.P["open"].values, pan.P["close"].values
    prev = np.where(k == 0, op[r], cl[np.maximum(r - 1, 0)])
    return pd.DataFrame({"date": pan.P["date"].values[r], "ret": cl[r] / prev - 1.0,
                         "ev": np.repeat(T.index.values, n),
                         "adv_terc": np.repeat(T["adv_terc"].values, n),
                         "px_terc": np.repeat(T["px_terc"].values, n),
                         "abs_r1": np.abs(pan.F["ret1"].values[r])})


def _book(pan: engine.Panel):
    P = pan.P
    prev_el = pan.eligible.groupby(P["ticker"], sort=False).shift(1)
    prev_el = prev_el.astype("boolean").fillna(False).astype(bool)
    r1 = pan.F["ret1"]
    m = prev_el & r1.notna()
    g = r1[m].groupby(P["date"][m])
    return g.mean(), g.size()


def _daily_excess(pos: pd.DataFrame, book: pd.Series) -> pd.Series:
    if pos.empty:
        return pd.Series(dtype=float)
    leg = pos.groupby("date")["ret"].mean()
    return (leg - book.reindex(leg.index)).dropna()


def _by_month(s: pd.Series) -> dict:
    if s.empty:
        return {}
    return {str(m): v for m, v in s.groupby(pd.DatetimeIndex(s.index).to_period("M"))}


def run_event_months(pan: engine.Panel, flags: pd.Series, card: dict, start=None, end=None,
                     with_returns: bool = True):
    """Monthly records (the month-engine schema evaluate.py reads) + the event table."""
    hold = hold_sessions(card)
    rt = float(card["costs"]["round_trip_pct"])
    P = pan.P
    E = build_events(pan, flags, hold, start, end)
    T = E[E["tradeable"]]
    cal = pd.DatetimeIndex(np.sort(P["date"].unique()))
    cal_m = cal.to_period("M").astype(str)
    n_sess = pd.Series(1, index=cal).groupby(cal_m).sum()
    first_sess = pd.Series(cal, index=cal).groupby(cal_m).min()
    book, book_n = _book(pan)
    Pos = _positions(pan, T)
    npos = Pos.groupby("date").size() if len(Pos) else pd.Series(dtype=float)

    sig_m = pd.Series(pd.DatetimeIndex(E["signal_date"]).to_period("M").astype(str), index=E.index)
    ent_m = pd.Series(pd.DatetimeIndex(T["entry_date"]).to_period("M").astype(str), index=T.index)
    pos_m = _by_month(npos)
    bookn_m = _by_month(book_n)
    months = sorted(set(sig_m) | set(pos_m))

    if with_returns:
        cl, op = P["close"].values, P["open"].values
        hold_ret = pd.Series(cl[T["exit_row"].values] / op[T["entry_row"].values] - 1.0, index=T.index)
        max_move = Pos.groupby("ev")["abs_r1"].max().reindex(T.index).fillna(0.0)
        ex = _daily_excess(Pos, book)
        ex_m = _by_month(ex)
        fp = {}
        for name, col in (("adv", "adv_terc"), ("price", "px_terc")):
            for side, q in (("low", 1), ("high", 3)):
                fp[f"fp_{name}_{side}"] = _by_month(_daily_excess(Pos[Pos[col] == q], book))
        w = (npos / book_n.reindex(npos.index)).clip(upper=0.99) if len(npos) else npos
        up_m = _by_month(-(w / (1 - w)) * ex.reindex(w.index).fillna(0.0))
        el_state = pan.F["ret63"].where(pan.eligible)
        state_by_date = el_state.groupby(P["date"]).mean()

    rows = []
    for m in months:
        if m not in n_sess.index:
            continue
        pdays = pos_m.get(m, pd.Series(dtype=float))
        bn = bookn_m.get(m, pd.Series(dtype=float))
        in_ent = ent_m[ent_m == m].index
        rec = {"month": m, "formation": str(first_sess[m].date()),
               "entry": str(pd.Timestamp(pdays.index.min()).date()) if len(pdays) else str(first_sess[m].date()),
               "exit": str(pd.Timestamp(pdays.index.max()).date()) if len(pdays) else str(first_sess[m].date()),
               "events": int((sig_m == m).sum()),
               "not_tradeable_at_entry": int(((sig_m == m) & ~E["tradeable"]).sum()),
               "univ": int(len(in_ent)), "stale_exits": int(T.loc[in_ent, "stale"].sum()),
               "position_days": int(len(pdays)),
               "book_median": float(bn.median()) if len(bn) else 0.0}
        if rec["position_days"] < MIN_EVENT_DAYS:
            rec.update(valid=False, reason="fewer than MIN_EVENT_DAYS position-days")
        elif rec["book_median"] < engine.MIN_UNIVERSE:
            rec.update(valid=False, reason="book below minimum universe")
        else:
            rec["valid"] = True
        if with_returns and rec["valid"]:
            ns = int(n_sess[m])
            e_m = ex_m.get(m, pd.Series(dtype=float))
            rec["primary"] = float(e_m.mean() * ns * 100.0) if len(e_m) else float("nan")
            rec["deployment"] = rec["primary"]
            for k, dct in fp.items():
                v = dct.get(m, pd.Series(dtype=float))
                rec[k] = float(v.mean() * ns * 100.0) if len(v) >= MIN_EVENT_DAYS else float("nan")
            n_book = float(bn.mean()) if len(bn) else float("nan")
            turn = len(in_ent) / n_book if n_book else float("nan")
            rec.update(zero_returns=int((hold_ret.loc[in_ent] == 0).sum()),
                       big_moves_in_hold=int((max_move.loc[in_ent] > engine.SPLIT_BAND).sum()),
                       max_abs_move_in_hold=float(max_move.loc[in_ent].max()) if len(in_ent) else 0.0,
                       turn_book=float(turn), turn_univ=0.0,
                       uplift_net=float(up_m.get(m, pd.Series(dtype=float)).sum() * 100.0 - rt * turn),
                       state=float(state_by_date.get(first_sess[m], np.nan)))
        rows.append(rec)
    return rows, E


def random_flags(pan: engine.Panel, rate: float, seed: int = 0) -> pd.Series:
    """Power (D-056 noise floor): each eligible row flagged with probability `rate`.
    Carries no information about any rule; signal() is never called."""
    u = np.random.default_rng(seed).random(len(pan.P))
    return pd.Series(((u < rate) & pan.eligible.values).astype(float), index=pan.P.index)


def placebo_flags(pan: engine.Panel, flags: pd.Series, seed: int = 7) -> pd.Series:
    """BM-1 placebo: the same number of events per date, on random eligible names."""
    P, el = pan.P, pan.eligible.values
    f = _flag_array(pan, flags)
    k = pd.Series(f).groupby(P["date"].values).transform("sum").values
    u = np.random.default_rng(seed).random(len(P))
    r = pd.Series(np.where(el, u, np.inf)).groupby(P["date"].values).rank(method="first").values
    return pd.Series((el & (r <= k)).astype(float), index=P.index)


def event_order_check(E: pd.DataFrame) -> dict:
    """FILL-1 / EX-1 per event: signal < entry <= exit (entry never on the signal bar)."""
    T = E[E["tradeable"]]
    bad = T[~((T["signal_date"] < T["entry_date"]) & (T["entry_date"] <= T["exit_date"]))]
    return checks._res("FILL-1", "event_entry_exit_order", len(T) > 0 and bad.empty,
                       {"events": int(len(T)), "violations": int(len(bad))})


def event_nondegenerate(pan: engine.Panel, flags: pd.Series) -> dict:
    """ID-1 for flags: some eligible rows flagged, and not most of them."""
    n_el = int(pan.eligible.sum())
    n_ev = int(_flag_array(pan, flags).sum())
    share = n_ev / n_el if n_el else float("nan")
    ok = n_ev > 0 and share <= MAX_EVENT_SHARE
    return checks._res("ID-1", "event_nondegenerate", ok,
                       {"events": n_ev, "eligible_rows": n_el, "share": share})
