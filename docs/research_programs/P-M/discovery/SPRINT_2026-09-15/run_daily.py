#!/usr/bin/env python3
"""Discovery sprint — daily-grain candidates (families A, C1, E + baselines).

Every tested candidate (including every parameterization) is appended to the
ledger. Fixed small grids, declared ex ante; no post-hoc threshold search.
Long-only. Mask: PIT liquidity floor + trades next day + sprint window.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import sprint_lib as sl

LEDGER = []


def z(p):  # shorthand
    return sl.trailing_z(p)


def sgn(p):
    return np.sign(p)


def main():
    p = sl.SprintPanel()
    mask = p.mask_base()
    nbz = z(p.nb)                     # PIT z of daily net flow value
    noa = p.nb / p.adv60              # net flow / ADV60
    volz = z(p.volume)
    r1 = p.ret1
    ret5z = z(p.ret5)

    # ---------------- Family A: flow x price response ----------------
    # A1 absorption: strong net buying, muted price response (grid)
    for zt in (1.5, 2.0):
        for mt in (0.01, 0.02):
            sig = nbz.where((nbz >= zt) & (r1.abs() <= mt), 0.0)
            sl.eval_signal(f"A1-absorb-buy-muted_z{zt}_m{mt}", sig, mask, p, LEDGER,
                           {"family": "A", "def": f"nb_z>={zt} & |ret1|<={mt}", "grain": "ticker-day",
                            "source": "stockbit_flow daily + ohlcv"})
    # A1b absorption into a dip
    for zt in (1.5, 2.0):
        sig = nbz.where((nbz >= zt) & (r1 <= -0.01), 0.0)
        sl.eval_signal(f"A1b-absorb-buy-dip_z{zt}", sig, mask, p, LEDGER,
                       {"family": "A", "def": f"nb_z>={zt} & ret1<=-1%", "grain": "ticker-day"})
    # A2 sell absorption: heavy net selling, price holds up -> long
    for zt in (1.5, 2.0):
        sig = (-nbz).where((-nbz >= zt) & (r1 >= 0.01), 0.0)
        sl.eval_signal(f"A2-absorb-sell-rise_z{zt}", sig, mask, p, LEDGER,
                       {"family": "A", "def": f"nb_z<=-{zt} & ret1>=+1%", "grain": "ticker-day"})
    # A3 bullish divergence: buying while price falls hard
    for (zt, rt) in ((1.0, -0.03), (1.5, -0.02)):
        sig = nbz.where((nbz >= zt) & (r1 <= rt), 0.0)
        sl.eval_signal(f"A3-bull-div_z{zt}_r{rt}", sig, mask, p, LEDGER,
                       {"family": "A", "def": f"nb_z>={zt} & ret1<={rt:.0%}", "grain": "ticker-day"})
    # A4 flow magnitude vs ADV (no z)
    for ft in (0.05, 0.10):
        sig = noa.where(noa >= ft, 0.0)
        sl.eval_signal(f"A4-flow-over-adv_{ft}", sig, mask, p, LEDGER,
                       {"family": "A", "def": f"net_value/ADV60 >= {ft:.0%}", "grain": "ticker-day"})
    # A5 flow acceleration: z of 5d-flow minus prior 5d-flow
    nb5 = p.nb.rolling(5, min_periods=3).sum()
    accel = nb5 - nb5.shift(5)
    accz = z(accel)
    for zt in (1.0, 1.5):
        sig = accz.where(accz >= zt, 0.0)
        sl.eval_signal(f"A5-flow-accel_z{zt}", sig, mask, p, LEDGER,
                       {"family": "A", "def": f"z60(5d_net - prior5d_net) >= {zt}", "grain": "ticker-day"})

    # ---------------- Family C1: daily-flow persistence ----------------
    up = (p.nb > 0).astype(float)
    streak = up.rolling(5).sum()
    for n in (4, 5):
        sig = nbz.where((streak >= n) & (nbz > 0), 0.0)
        sl.eval_signal(f"C1-flow-streak{n}of5", sig, mask, p, LEDGER,
                       {"family": "C", "def": f"net_value>0 on >= {n} of last 5 sessions & nb_z>0", "grain": "ticker-day"})

    # ---------------- Family E: event-conditioned flow ----------------
    # E1 volume spike + flow direction
    sig = nbz.where((volz >= 2.0) & (nbz >= 1.0), 0.0)
    sl.eval_signal("E1-volspike+buyflow", sig, mask, p, LEDGER,
                   {"family": "E", "def": "vol_z>=2 & nb_z>=1", "grain": "ticker-day"})
    # E2 volume spike + selling flow (informational mirror)
    sig = (-nbz).where((volz >= 2.0) & (nbz <= -1.0), 0.0)
    sl.eval_signal("E2-volspike+sellflow[MIRROR]", sig, mask, p, LEDGER,
                   {"family": "E", "def": "vol_z>=2 & nb_z<=-1 (long side of mirror)", "grain": "ticker-day"})
    # E3 big move + confirming flow
    sig = nbz.where((r1.abs() >= 0.03) & (np.sign(nbz) == np.sign(r1)), 0.0)
    sl.eval_signal("E3-bigmove-flow-confirms", sig, mask, p, LEDGER,
                   {"family": "E", "def": "|ret1|>=3% & sign(nb_z)=sign(ret1)", "grain": "ticker-day"})
    # E3b big move + fading flow (mirror)
    sig = (-nbz * sgn(r1)).where((r1.abs() >= 0.03) & (np.sign(nbz) == -np.sign(r1)), 0.0)
    sl.eval_signal("E3b-bigmove-flow-fades", sig, mask, p, LEDGER,
                   {"family": "E", "def": "|ret1|>=3% & sign(nb_z)=-sign(ret1) -> long (fade wins)", "grain": "ticker-day"})
    # E4 accumulation at 20d lows
    low20 = p.close.rolling(20, min_periods=15).min()
    near_low = (p.close / low20 - 1.0) <= 0.02
    sig = nbz.where(near_low & (nbz >= 1.5), 0.0)
    sl.eval_signal("E4-low20-accumulation", sig, mask, p, LEDGER,
                   {"family": "E", "def": "close within 2% of 20d low & nb_z>=1.5", "grain": "ticker-day"})
    # E5 gap day + flow against the gap
    gap = p.close - p.close.shift(1)  # proxy with close-to-close gap share
    openc = p.close  # open not pivoted; use return-based event instead
    sig = (-nbz).where((r1 >= 0.05) & (nbz <= -1.0), 0.0)
    sl.eval_signal("E5-up5-sold[MIRROR]", sig, mask, p, LEDGER,
                   {"family": "E", "def": "ret1>=+5% & nb_z<=-1 (mirror long)", "grain": "ticker-day"})

    # ---------------- Baselines (incrementality comparators) ----------------
    sig = nbz.where(nbz >= 2.0, 0.0)
    sl.eval_signal("BL-raw-flow_z2", sig, mask, p, LEDGER,
                   {"family": "BL", "def": "nb_z>=2 (unconditioned flow)", "grain": "ticker-day"})
    sig = ret5z.where(ret5z >= 1.5, 0.0)
    sl.eval_signal("BL-momentum", sig, mask, p, LEDGER,
                   {"family": "BL", "def": "ret5_z>=1.5", "grain": "ticker-day"})
    sig = (0.0 - r1).where(r1 <= -0.03, 0.0)
    sl.eval_signal("BL-reversal", sig, mask, p, LEDGER,
                   {"family": "BL", "def": "ret1<=-3% (long reversal)", "grain": "ticker-day"})
    sig = volz.where(volz >= 2.0, 0.0)
    sl.eval_signal("BL-volspike", sig, mask, p, LEDGER,
                   {"family": "BL", "def": "vol_z>=2", "grain": "ticker-day"})
    # unconditional reference
    sig = pd.DataFrame(1.0, index=mask.index, columns=mask.columns)
    sl.eval_signal("BL-unconditional", sig, mask, p, LEDGER,
                   {"family": "BL", "def": "all liquid tradable ticker-days", "grain": "ticker-day"})

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache", "ledger_daily.json")
    sl.save_ledger(LEDGER, out)
    print(f"ledger entries: {len(LEDGER)} -> {out}")
    for e in LEDGER:
        h5 = e.get("h5")
        print(f"{e['id']:38s} {e['status']:18s} n={e.get('n_obs',0):7d} "
              + (f"h5 gross={h5['gross_mean']:.4f} net={h5['net_floor']:+.4f}" if h5 else ""))


if __name__ == "__main__":
    main()
