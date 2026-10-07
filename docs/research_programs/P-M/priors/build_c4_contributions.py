#!/usr/bin/env python3
"""C4 answer: median-stock return per year + top heavyweight contributors.

Consumes /tmp/c4_panel_stash.pkl written by build_c4_panel.py (run that
first). Read-only, no DB access of its own.

Layer 1: median stock return per year, within the top-200 ADV60 universe
(formed at each month's start, per build_c4_panel.py) -- the "typical
member" experience, robust to a few extreme names.

Layer 2: the 2-4 heavyweight contributors that set each year's EW-vs-IHSG
gap. "Contribution to IHSG" is proxied here by full-universe cap weight
(ALL tickers with fund_shares.pkl coverage, not just the top-200 -- IHSG's
real constituents include some large caps that miss the ADV60 liquidity
cut) x forward monthly return, summed over the year. This is a proxy, not
official IHSG index weights (not available in this repo) -- flagged
wherever used.

Also answers: are the heaviest contributors themselves inside the top-200
ADV60 universe, or outside it? That's the "different market vs broad"
check the brief asks for.
"""
import json
import pickle

import numpy as np
import pandas as pd

with open("/tmp/c4_panel_stash.pkl", "rb") as f:
    s = pickle.load(f)

ret = s["ret"]
caps_me = s["caps_me"]
universe_members = s["universe_members"]
month_ends = s["month_ends"]

years = sorted(set(dt.year for dt in month_ends[1:]))

out = {"median_by_year": {}, "top_contributors_by_year": {}}

for yr in years:
    # ---- Layer 1: median stock return within that year's universe(s) ----
    year_month_rets = []
    for i in range(len(month_ends) - 1):
        dt, dt_next = month_ends[i], month_ends[i + 1]
        if dt_next.year != yr:
            continue
        members = universe_members[dt]
        r = ret.loc[dt_next, members].dropna()
        year_month_rets.append(r)
    if not year_month_rets:
        continue
    # per-ticker compounded return across this year's months it was in-universe
    all_idx = sorted(set().union(*[set(r.index) for r in year_month_rets]))
    comp = pd.Series(1.0, index=all_idx)
    counts = pd.Series(0, index=all_idx)
    for r in year_month_rets:
        comp.loc[r.index] *= (1 + r)
        counts.loc[r.index] += 1
    comp = comp - 1
    # only count names present for the full set of that year's months (avoid
    # partial-year artifacts dominating the median)
    full_year = comp[counts == len(year_month_rets)]
    median_ret = float(full_year.median()) if len(full_year) else None
    out["median_by_year"][yr] = {
        "median_ret": median_ret, "n_full_year_names": int(len(full_year)),
        "n_any": int(len(comp)),
    }

    # ---- Layer 2: full-universe cap-weighted contribution per ticker ----
    contrib_total = pd.Series(dtype=float)
    for i in range(len(month_ends) - 1):
        dt, dt_next = month_ends[i], month_ends[i + 1]
        if dt_next.year != yr:
            continue
        w = caps_me.loc[dt].dropna()
        w = w[w > 0]
        w = w / w.sum()
        r_all = ret.loc[dt_next].reindex(w.index)
        c = (w * r_all).dropna()
        contrib_total = contrib_total.add(c, fill_value=0.0)

    top_pos = contrib_total.sort_values(ascending=False).head(4)
    top_neg = contrib_total.sort_values(ascending=True).head(4)

    def _describe(sname, series):
        rows = []
        for tk, val in series.items():
            in_universe_months = sum(
                1 for i in range(len(month_ends) - 1)
                if month_ends[i + 1].year == yr and tk in universe_members[month_ends[i]]
            )
            year_months = sum(1 for i in range(len(month_ends) - 1) if month_ends[i + 1].year == yr)
            rows.append({
                "ticker": tk, "contribution_pp": round(float(val) * 100, 3),
                "months_in_top200_this_year": in_universe_months,
                "year_months": year_months,
                "inside_top200_majority_of_year": in_universe_months >= (year_months / 2),
            })
        return rows

    out["top_contributors_by_year"][yr] = {
        "positive": _describe("pos", top_pos),
        "negative": _describe("neg", top_neg),
    }

print(json.dumps(out, indent=2, default=str))
