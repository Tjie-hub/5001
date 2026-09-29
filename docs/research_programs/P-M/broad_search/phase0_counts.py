"""Phase 0 counts for the broad edge search (brief ZCODE_BRIEF_BROAD_EDGE_SEARCH_2026-09-29).

COUNTS ONLY. This script never computes a forward return. The only price-derived
quantities are TRAILING observables (adv20 at an announcement date, a last close
strictly before an announcement, a jump-presence flag around an ex-date) used for
liquidity gating, MDE sizing and the rights-adjustment audit. Every DB read goes
through the fingerprinted 2026-09-28 snapshot (~/wf_snapshot_20260929/), never the
production database; history_long.db is opened read-only.

Outputs phase0_counts.json next to this file.
"""
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))

SNAP = Path.home() / "wf_snapshot_20260929" / "walkforward-20260928-213012.db"
SNAP_SHA256 = "10f9c97fb20bf8e89b0688a4728bdae531dce9711f31ddd5270b414ea7946c13"
LONG_DB = ROOT / "data" / "history_long.db"
ADV_LIQUID = 5e9          # brief rule 5: adv20 >= Rp 5bn
CUT = pd.Timestamp("2026-09-16")   # program data cutoff

out = {"snapshot": {"path": str(SNAP), "sha256": SNAP_SHA256,
                    "meta": str(SNAP).replace(".db", ".meta.json")}}

# ---------------------------------------------------------------- corporate actions
CREATED_KEY = {"rightissue": "rightissue_created", "warrant": None,
               "tenderoffer": "tender_created", "stocksplit": "stocksplit_created",
               "stock_reverse": "stocksplit_created", "bonus": "stocksplit_created",
               "dividend": "dividend_created", "rups": "rups_created"}


def parse_events():
    con = sqlite3.connect(f"file:{SNAP}?mode=ro", uri=True)
    df = pd.read_sql(
        "SELECT ticker, action_type, event_date, raw_json, fetch_date "
        "FROM corporate_action_events", con)
    con.close()
    rows = []
    for _, r in df.iterrows():
        j = json.loads(r["raw_json"])
        ak = r["action_type"]
        rec = {"ticker": r["ticker"], "type": ak,
               "db_event_date": r["event_date"],
               "created": j.get(CREATED_KEY[ak]) if CREATED_KEY[ak] else None,
               "exdate": j.get(f"{ak}_exdate") or j.get("stocksplit_exdate"),
               "raw": j}
        if ak == "rightissue":
            rec.update(ratio_old=j.get("rightissue_old"), ratio_new=j.get("rightissue_new"),
                       sub_price=j.get("rightissue_price"),
                       factor=j.get("rightissue_factor"))
        elif ak in ("stocksplit", "stock_reverse", "bonus"):
            rec.update(factor=j.get("stocksplit_factor"),
                       ratio_old=j.get("stocksplit_old"), ratio_new=j.get("stocksplit_new"))
        elif ak == "tenderoffer":
            rec.update(tender_price=j.get("tender_price"),
                       t_start=j.get("tender_start"), t_end=j.get("tender_end"),
                       pct=j.get("tender_percentage"))
        elif ak == "rups":
            rec.update(rups_date=j.get("rups_date"),
                       agenda=j.get("rups_iqp_agenda") or j.get("rups_iqp_result"))
        elif ak == "dividend":
            rec.update(div_value=j.get("dividend_value"))
        rows.append(rec)
    E = pd.DataFrame(rows)
    for c in ("created", "exdate"):
        E[c + "_ts"] = pd.to_datetime(E[c], errors="coerce", format="mixed")
    E["db_event_date_ts"] = pd.to_datetime(E["db_event_date"], errors="coerce")
    return E


E = parse_events()
out["events_total"] = {k: int(v) for k, v in E["type"].value_counts().items()}

# PIT hygiene per type: created present, created <= exdate when both exist, weekend share
pit = {}
for t, g in E.groupby("type"):
    has_c = g["created_ts"].notna()
    both = g[has_c & g["exdate_ts"].notna()]
    order_ok = (both["created_ts"] <= both["exdate_ts"]).mean() if len(both) else np.nan
    wk = (pd.DatetimeIndex(g.loc[has_c, "created_ts"]).dayofweek >= 5).mean() if has_c.any() else np.nan
    pit[t] = {"n": int(len(g)), "created_present": float(has_c.mean()),
              "created_le_exdate": None if pd.isna(order_ok) else round(float(order_ok), 4),
              "n_created_le_exdate": int(len(both)),
              "created_weekend_share": None if pd.isna(wk) else round(float(wk), 4)}
out["pit_hygiene"] = pit

# ---------------------------------------------------------------- trailing adv20 gate
print("loading extended panel (backfill pkl + SNAPSHOT DB corpus) ...", flush=True)
import research.rulecard.data as rcdata                           # noqa: E402
from data.adjustments import load_split_factors, read_raw_ohlcv   # noqa: E402
from data.db import connect                                       # noqa: E402

# the sanctioned loader, with its DB leg pointed at the fingerprinted snapshot
with connect(path=SNAP, read_only=True) as _c:
    D = read_raw_ohlcv(_c)
    factors = load_split_factors(_c)
P = rcdata.merge_extended(pd.read_pickle(rcdata.DEFAULT_HIST), D,
                          pd.read_pickle(rcdata.DEFAULT_SPLITS), db_splits=factors)
P = P[P["date"] <= CUT].reset_index(drop=True)
val = P["close"] * P["volume"]
P["adv20"] = val.groupby(P["ticker"], sort=False).transform(
    lambda x: x.rolling(20, min_periods=20).mean())
P["d"] = pd.to_datetime(P["date"])

idx = P.groupby("ticker", sort=False).indices


def trailing_adv20(ticker, ts):
    ii = idx.get(ticker)
    if ii is None:
        return np.nan, False
    dts = P["d"].values[ii]
    pos = np.searchsorted(dts, np.datetime64(pd.Timestamp(ts)))
    if pos == 0:
        return np.nan, False
    a = P["adv20"].values[ii][pos - 1]   # last TRAILING adv20 at or before ts
    return (a, True) if np.isfinite(a) else (np.nan, False)


ev = E[E["created_ts"].notna() & (E["created_ts"] >= "2013-01-01")
       & (E["created_ts"] <= CUT)].copy()
adv, ok = zip(*[trailing_adv20(t, c) for t, c in zip(ev["ticker"], ev["created_ts"])])
ev["adv20_at_ann"] = adv
ev["adv_known"] = ok
gate = {}
for t, g in ev.groupby("type"):
    known = g[g["adv_known"]]
    gate[t] = {"n_2013plus": int(len(g)), "adv_known": int(len(known)),
               "adv_ge_5bn": int((known["adv20_at_ann"] >= ADV_LIQUID).sum()),
               "adv_ge_1bn": int((known["adv20_at_ann"] >= 1e9).sum()),
               "adv_median_bn": (round(float(known["adv20_at_ann"].median() / 1e9), 2)
                                 if len(known) else None)}
out["events_adv_gate"] = gate

# per-year counts (announcement year), total and adv>=5bn
yr = {}
for t, g in ev.groupby("type"):
    known = g[g["adv_known"]].copy()
    known["yr"] = known["created_ts"].dt.year
    total = known.groupby("yr").size()
    liq = known[known["adv20_at_ann"] >= ADV_LIQUID].groupby("yr").size()
    yr[t] = {str(int(y)): [int(total.get(y, 0)), int(liq.get(y, 0))]
             for y in sorted(set(total.index) | set(liq.index))}
out["events_per_year_total_liquid"] = yr

# ---------------------------------------------------------------- rups -> issuance link
rup = ev[ev["type"] == "rups"][["ticker", "created_ts"]]
ri = ev[ev["type"] == "rightissue"][["ticker", "created_ts"]]
links = 0
for tk, g in ri.groupby("ticker"):
    if g.empty:
        continue
    rr = rup[rup["ticker"] == tk]["created_ts"]
    if rr.empty:
        continue
    for c in g["created_ts"]:
        if ((rr <= c) & (rr >= c - pd.Timedelta(days=365))).any():
            links += 1
            break
out["rups_to_rightissue_12m"] = {"rightissues_2013plus": int(len(ri)),
                                 "preceded_by_rups_12m": int(links)}
agenda_n = int((E.loc[E["type"] == "rups", "raw"]
                .apply(lambda j: bool(j.get("rups_iqp_agenda")))).sum())
out["rups_agenda_nonempty"] = agenda_n

# ---------------------------------------------------------------- tender offers (trailing)
to = ev[ev["type"] == "tenderoffer"].copy()
last_px = []
for t, c in zip(to["ticker"], to["created_ts"]):
    ii = idx.get(t)
    if ii is None:
        last_px.append(np.nan)
        continue
    dts = P["d"].values[ii]
    pos = np.searchsorted(dts, np.datetime64(pd.Timestamp(c)))
    last_px.append(float(P["close"].values[ii][pos - 1]) if pos else np.nan)
to["last_close_before"] = last_px
tp = pd.to_numeric(to["tender_price"], errors="coerce")
prem = (tp / to["last_close_before"] - 1).replace([np.inf, -np.inf], np.nan)
out["tender_offer"] = {
    "n_2013plus": int(len(to)),
    "median_duration_days": float((pd.to_datetime(to["t_end"]) -
                                   pd.to_datetime(to["t_start"])).dt.days.median()),
    "premium_median": None if prem.dropna().empty else round(float(prem.median()), 4),
    "premium_n": int(prem.notna().sum()),
    "adv_ge_5bn": gate["tenderoffer"]["adv_ge_5bn"]}

# ---------------------------------------------------------------- dividends: initiation/omission
dv = ev[ev["type"] == "dividend"][["ticker", "created_ts", "div_value"]].copy()
dv["div_value"] = pd.to_numeric(dv["div_value"], errors="coerce")
n_init = n_omit = 0
for tk, g in dv.groupby("ticker"):
    g = g.sort_values("created_ts")
    years = g["created_ts"].dt.year.values
    if len(g) == 1:
        n_init += 1
        continue
    gap = np.diff(years)
    n_init += int((gap >= 2).sum())            # >=2y since last dividend, then one: initiation
    last_y = years.max()
    n_omit += int(g["created_ts"].dt.year.between(last_y - 2, last_y - 1).any()
                  and pd.Timestamp(CUT).year - last_y >= 2)  # no dividend for >=2y by cutoff
out["dividend_io"] = {"n_dividend_events_2013plus": int(len(dv)), "initiations": int(n_init),
                      "omissions_proxy": int(n_omit)}

# ---------------------------------------------------------------- suspension events
con = sqlite3.connect(f"file:{SNAP}?mode=ro", uri=True)
S = pd.read_sql("SELECT ticker, last_normal_date, resume_date, missing_td, gap_pct, "
                "classification FROM suspension_events", con)
con.close()
S["resume_ts"] = pd.to_datetime(S["resume_date"], errors="coerce")
out["suspensions"] = {
    "by_class": {k: int(v) for k, v in S["classification"].value_counts().items()},
    "resume_2013plus": int((S["resume_ts"] >= "2013-01-01").sum()),
    "resume_2013plus_susp_class": int(((S["resume_ts"] >= "2013-01-01")
                                       & (S["classification"] == "suspension")).sum())}

# ---------------------------------------------------------------- listing lifecycle (family B)
con = sqlite3.connect(f"file:{LONG_DB}?mode=ro", uri=True)
L = pd.read_sql("SELECT ticker, MIN(date) AS first_bar, MAX(date) AS last_bar, "
                "COUNT(*) AS n FROM ohlcv_long GROUP BY ticker", con)
con.close()
L["first_ts"] = pd.to_datetime(L["first_bar"])
L["last_ts"] = pd.to_datetime(L["last_bar"])
out["listing_lifecycle"] = {
    "tickers": int(len(L)),
    "first_bar_year_counts": {str(int(y)): int(c) for y, c in
                              L["first_ts"].dt.year.value_counts().sort_index().items()},
    "last_bar_before_2026": int((L["last_ts"] < "2026-01-01").sum()),
    "last_bar_before_2025": int((L["last_ts"] < "2025-01-01").sum()),
    "note": "history_long.db read directly mode=ro (static backfill, 929-ticker corpus)"}

# ---------------------------------------------------------------- news mentions (family F)
con = sqlite3.connect(f"file:{SNAP}?mode=ro", uri=True)
N = pd.read_sql("SELECT MIN(date) AS d0, MAX(date) AS d1, COUNT(*) AS n, "
                "COUNT(DISTINCT ticker) AS tk FROM news_mentions", con)
con.close()
out["news_mentions"] = {k: (v if not isinstance(v, str) else v) for k, v in
                        dict(N.iloc[0]).items()}

# ---------------------------------------------------------------- sectors (family E)
con = sqlite3.connect(f"file:{SNAP}?mode=ro", uri=True)
T = pd.read_sql("SELECT sector, COUNT(*) AS n FROM ticker_sector GROUP BY sector "
                "ORDER BY n DESC", con)
con.close()
out["ticker_sector"] = {"rows": int(T["n"].sum()),
                        "by_sector": {r.sector: int(r.n) for r in T.itertuples()}}

# ---------------------------------------------------------------- ex-date inventory (audit input)
ex = E[E["type"].isin(["rightissue", "bonus", "stock_reverse", "stocksplit"])]
ex = ex[ex["exdate_ts"].notna() & (ex["exdate_ts"] >= "2013-01-01")]
out["exdate_inventory_2013plus"] = {
    t: {"n": int(len(g)),
        "n_2021plus": int((g["exdate_ts"] >= "2021-07-05").sum()),
        "factor_median": (round(float(pd.to_numeric(g["factor"], errors="coerce")
                                      .median()), 3) if len(g) else None)}
    for t, g in ex.groupby("type")}

# jump-presence: does the research corpus carry the mechanical drop at the ex-date?
def jump_present(ticker, ex_ts, panel):
    ii = idx.get(ticker)
    if ii is None:
        return None
    dts = panel["d"].values[ii]
    cls = panel["close"].values[ii]
    pos = np.searchsorted(dts, np.datetime64(pd.Timestamp(ex_ts)))
    if pos == 0 or pos >= len(cls):
        return None
    prev = cls[pos - 1]
    win = cls[max(0, pos - 2):pos + 2]
    r = np.abs(win / prev - 1.0)
    return bool((r > 0.35).any())

exs = ex[ex["exdate_ts"] <= CUT].copy()
jp = [jump_present(t, x, P) for t, x in zip(exs["ticker"], exs["exdate_ts"])]
exs["jump"] = jp
out["exdate_jump_presence"] = {
    t: {"n_measurable": int(g["jump"].notna().sum()),
        "n_jump_gt_35pct": int((g["jump"] == True).sum())}          # noqa: E712
    for t, g in exs.groupby("type")}

# ---------------------------------------------------------------- rights-adjustment audit inputs
LEDGERS = {
    "REGIME-002": ROOT / "docs/research_programs/P-M/forward_regime/ledger.json",
    "FADE-001": ROOT / "docs/research_programs/P-M/forward_fade/ledger.json",
    "VOLEX-001": ROOT / "docs/research_programs/P-M/forward_exclusion/ledger.json",
}
wins = {}
for name, p in LEDGERS.items():
    d = json.loads(Path(p).read_text())
    tr = d.get("trades", [])
    rows = []
    for t in tr:
        rows.append((t["ticker"], pd.Timestamp(t["entry_date"]),
                     pd.Timestamp(t["exit_date"])))
    hits = []
    for tk, e0, e1 in rows:
        m = exs[(exs["ticker"] == tk) & (exs["exdate_ts"] >= e0) & (exs["exdate_ts"] <= e1)]
        for r in m.itertuples():
            hits.append({"ticker": tk, "window": [str(e0.date()), str(e1.date())],
                         "type": r.type, "exdate": str(r.exdate_ts.date()),
                         "jump_in_corpus": r.jump})
    wins[name] = {"recorded_windows": len(rows), "exdate_hits": hits}
out["ledger_window_audit"] = wins

# prospective exposure: ex-dates of issuance-type events inside the forward tests'
# active window so far (opened 2026-09-17 -> snapshot date), on any panel name
fwd0, fwd1 = pd.Timestamp("2026-09-17"), pd.Timestamp("2026-09-28")
pros = exs[(exs["exdate_ts"] >= fwd0) & (exs["exdate_ts"] <= fwd1)]
out["forward_window_exdates_20260917_0928"] = {
    "window": ["2026-09-17", "2026-09-28"],
    "by_type": {k: int(v) for k, v in pros["type"].value_counts().items()},
    "with_jump": int((pros["jump"] == True).sum())}                 # noqa: E712

(HERE / "phase0_counts.json").write_text(json.dumps(out, indent=1, default=str))
print(json.dumps({k: v for k, v in out.items() if k != "events_per_year_total_liquid"},
                 indent=1, default=str)[:4000])
print("WROTE", HERE / "phase0_counts.json")
