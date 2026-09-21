"""FWD-PM-TREND-001 (DRAFT) -- frozen backtest specification. v6, 2026-09-20.

Donchian 20/10 time-series trend, big-cap IDX universe (monthly top-80 by ADV60).

v6 AMENDMENT (2026-09-20, pre-registration era): v5's position-lag step,
`held = pos.shift(1)`, ran on the WHOLE ticker-sorted panel with no
`.groupby(ticker)` -- at every ticker boundary this bled the terminal
position of the PRECEDING ticker (in sort order) into the FIRST row of the
NEXT ticker, one spurious held-day per boundary (reviewer-verified: 21
impossible held-positions landed on 2021-07-05, the DB's true start date,
where 717 of 952 tickers begin -- impossible under the entry logic, which
requires 20 prior bars before hh20 is even defined). v6 groups the shift by
ticker (`pos.groupby(d.ticker).shift(1)`), the only line touched -- 29 of
1,047,710 rows change. v5's -12.0%/Sharpe -0.34 was itself still an
artifact; the honest number is -6.1%/Sharpe -0.17. Directional conclusion is
unchanged (book stays flat-to-negative against IHSG's +1.6% over the same
window) -- only the magnitude used throughout the protocol document changes.
See PROTOCOL_DRAFT.md section 1.5.

v5 AMENDMENT (2026-09-20, pre-registration era): v4's aggregation divided the
daily sum of held-position returns by the COUNT OF HELD NAMES -- an unstated
deviation from section 2 ("remainder cash"), which concentrates the book into
whatever is currently trending and overstates vol/drawdown (v4: -61.1%,
Sharpe -0.82). v5 restores the section 2 denominator: the daily return is the
sum of held-position returns divided by the CURRENT TOP-80 MEMBER COUNT
(the opportunity set; remainder cash earns zero). Member-gating of entries,
calendar windows, loss accrual and all guards are unchanged from v4.

v4 AMENDMENT (2026-09-20, pre-registration era): the v3 (month,ticker) inner
merge fixed membership but re-introduced window splicing from the other side --
after the merge, a ticker's rows skip non-member months, so hh20/ll10 at
re-entry were computed over stale rows (reviewer: 216/3,314 entry signals,
6.5%, with lookback windows spanning >40 calendar days; worst 554d, BBYB
2025-10-02). v4 adopts the reviewer's construction: ALL rolling windows
(hh20, ll10, adv60, traded20, sma60) are computed on each ticker's FULL
calendar frame -- rows are never dropped before window computation -- and
membership is attached as a `member` flag gating ENTRIES only. A window-span
check is printed every run so this defect class stays observable.

v3 AMENDMENT: v1/v2/v2.1 collapsed monthly top-80 membership into a flat
ticker set (`isin`) -- 69.5% of rows never ranked <=80 in their own month.
v2 AMENDMENT: v1 dropped zero-volume rows upstream, making the traded-days
guard a provable no-op; v2 keeps all priced sessions so windows span calendar
sessions.

Independent replication of the effect registered as HYP-PM-0010
(Price-Trend {T1}; forward test FWD-PM-REGIME-002). Not a novel alpha claim.
"""
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from data.db import connect

# ---- frozen constants (section 2 of the protocol) ----
WINDOW_IN = 20          # Donchian breakout lookback (prior highs), calendar sessions
WINDOW_OUT = 10         # Donchian exit lookback (prior lows), calendar sessions
GUARD_MIN_TRADED = 18   # of trailing 20 sessions must have volume > 0
GUARD_WINDOW = 20
PRICE_FLOOR = 50        # Rp
ADV_MONTHS_TOP = 80     # monthly top-N by trailing ADV60
ADV_MIN_PERIODS = 40
COST_PER_TURN = 0.003   # 0.30% charged on each position turn (0.60% round trip)
CONTAM_MOVE = 0.35      # zero position-days whose window contains a +/-35% session
HYGIENE_EXCLUDE = ("TMAS", "MLPT", "RMKE", "RAJA",  # known unadjusted-split histories
                   "INET", "PYFA")  # added v2.1: >35% single-session moves verified inside
                                    # monthly top-80 membership (83.3% / 207.1%) --
                                    # split-artifact class; BNBR (36.2%) unresolved, kept
                                    # under the +/-35% position-day mask


def load():
    with connect(read_only=True) as c:
        d = pd.read_sql(
            "SELECT ticker,date,open,high,low,close,volume FROM ohlcv "
            "WHERE is_final=1 AND ticker!='IHSG'",
            c,
        )
    d["date"] = pd.to_datetime(d["date"])
    # price validity only. Zero-volume (carried-forward) sessions are KEPT so
    # that traded20, hh20, ll10 and adv60 all span calendar sessions. The
    # volume > 0 requirement lives at the entry check in main(), not here.
    d = d[(d.open > 0) & (d.close > 0) & (d.low > 0)]
    d = d[~d.ticker.isin(HYGIENE_EXCLUDE)]
    return d.sort_values(["ticker", "date"]).reset_index(drop=True)


def build(d):
    # v4: every window is computed on the FULL per-ticker calendar frame.
    # Membership is attached afterwards as a flag that gates entries; rows are
    # never dropped before window computation (the v1-v3 root rot, closed).
    g = d.groupby("ticker", group_keys=False)
    d["dval"] = d.close * d.volume
    d["adv60"] = g.dval.transform(lambda s: s.rolling(60, min_periods=ADV_MIN_PERIODS).mean())
    d["pm"] = d.date.dt.to_period("M")
    d["cc"] = g.close.pct_change()
    d["hh20"] = g.high.transform(lambda s: s.shift(1).rolling(WINDOW_IN, min_periods=WINDOW_IN).max())
    d["ll10"] = g.low.transform(lambda s: s.shift(1).rolling(WINDOW_OUT, min_periods=WINDOW_OUT).min())
    d["traded20"] = (d.volume > 0).astype(int).groupby(d.ticker).transform(
        lambda s: s.rolling(GUARD_WINDOW, min_periods=GUARD_WINDOW).sum()
    )
    d["sma60"] = g.close.transform(lambda s: s.rolling(60, min_periods=60).mean())
    d["date_m20"] = g.date.shift(WINDOW_IN)   # calendar start of the hh20 window
    tm = d.groupby(["pm", "ticker"]).adv60.first().reset_index()
    tm["rank"] = tm.groupby("pm")["adv60"].rank(ascending=False)
    keep = tm[tm["rank"] <= ADV_MONTHS_TOP][["pm", "ticker"]].assign(member=1)
    d = d.merge(keep, on=["pm", "ticker"], how="left")
    d["member"] = d.member.fillna(0.0)
    return d


def main():
    d = build(load())
    # entry signal at close t: breakout of prior-20 calendar-session highs,
    # entry bar itself traded, traded-days guard satisfied, ticker is a member
    # of that month's top-80
    raw = (d.close > d.hh20) & (d.volume > 0) & d.hh20.notna() & d.sma60.notna()
    entry = raw & (d.traded20 >= GUARD_MIN_TRADED) & (d.member == 1)
    guard_blocked = int((raw & (d.traded20 < GUARD_MIN_TRADED)).sum())
    member_blocked = int((raw & (d.traded20 >= GUARD_MIN_TRADED) & (d.member != 1)).sum())
    exit_ = (d.close < d.ll10) & d.ll10.notna()
    pos = pd.Series(np.where(entry, 1.0, np.where(exit_, 0.0, np.nan)), index=d.index)
    pos = pos.groupby(d.ticker).ffill().fillna(0.0)
    pos[d.hh20.isna() | d.sma60.isna()] = 0.0
    # v6 fix: shift MUST be grouped by ticker -- an ungrouped shift bleeds
    # the previous ticker's terminal position into the next ticker's first
    # row at every panel boundary (see docstring v6 amendment; PROTOCOL_DRAFT.md §1.5)
    held = pos.groupby(d.ticker).shift(1).fillna(0.0)
    turn = held.diff().abs().fillna(0.0)
    r = d.cc * held - turn * COST_PER_TURN
    # contamination guard: zero position-days where the name moved beyond +/-35%
    extreme = d.cc.abs() > CONTAM_MOVE
    r = r.mask(extreme, 0.0)
    # portfolio day = sum of held-position returns divided by the CURRENT
    # TOP-80 MEMBER COUNT (the opportunity set; "remainder cash" earns zero,
    # section 2). v5 fix: v4 divided by the held count instead, concentrating
    # the book and overstating vol/drawdown.
    num = r.groupby(d.date).sum()
    den = d[d.member == 1].groupby("date").ticker.nunique().reindex(num.index).fillna(1)
    daily = num / den
    eq = (1 + daily).cumprod()
    yrs = (daily.index.max() - daily.index.min()).days / 365.25
    dd = (eq / eq.cummax() - 1).min() * 100
    sh = daily.mean() / daily.std() * np.sqrt(252)
    held_per_day = held.groupby(d.date).sum()
    held_active = held_per_day[held_per_day > 0]
    # window-span check: an entry's hh20 window must span ~a month of calendar,
    # not splice across membership gaps (the v3 defect this run proves closed)
    ent = d[entry].copy()
    ent["span"] = (ent.date - ent.date_m20).dt.days
    mem = d[d.member == 1]
    print("FWD-PM-TREND-001 frozen backtest v6 (DRAFT, in-sample reference)")
    print(f"window   : {daily.index.min().date()} -> {daily.index.max().date()}  ({yrs:.1f}y, {len(daily)} active days)")
    print(f"total    : {(eq.iloc[-1]-1)*100:+.1f}%   CAGR {(eq.iloc[-1]**(1/yrs)-1)*100:+.2f}%")
    print(f"maxDD    : {dd:.1f}%   Sharpe {sh:.2f}   avg deployment {100*held_active.mean()/mem.groupby('pm').ticker.nunique().mean():.1f}%")
    print(f"per-day  : mean {daily.mean()*100:+.4f}%")
    print(f"universe : {int(d.member.sum()):,} member-bars, "
          f"mean {mem.groupby('pm').ticker.nunique().mean():.0f} names/mo, "
          f"{mem.ticker.nunique()} tickers ever member")
    print(f"guards   : entry signals {int(raw.sum())} -> guard-blocked {guard_blocked}, "
          f"member-blocked {member_blocked}, taken {int(entry.sum())}")
    print(f"window-span check (entry hh20 windows): median {ent.span.median():.0f}d, "
          f">40d: {100*(ent.span>40).mean():.2f}%, max {ent.span.max():.0f}d")


if __name__ == "__main__":
    main()
