"""Feasibility census for mechanism-inventory Task 3, classes G/H/I/K/M/N/O (2026-10-07).

NO OUTCOMES, per brief ZCODE_BRIEF_MECHANISM_INVENTORY_B_2026-10-07.md rule 1:
no return, price change or excess return is computed, printed or stored after any
event's decision date (or after a calendar window starts), for any horizon or
aggregate. The only panel statistics computed are liquidity (ADV20 turnover, a
control/risk measure) and volatility of returns strictly BEFORE each event's
decision date. Class M is excluded here entirely: it is closed by prior coverage
+ D-062 (see FEASIBILITY_B_2026-10-07.md) and the brief says to stop on it.
Class J has no event dates to enumerate (no PIT filing dates anywhere); its
inventory is a schema/coverage audit, not a census. Class G has no event dates
in the DB either; it gets a panel risk summary only, labeled as such.

Read-only: every DB handle is data.db.connect(read_only=True); the only writes
are this script's own JSON output. Deterministic: no sampling, no RNG, no seed.

Inputs
- data/walkforward.db (DB corpus, ohlcv is_final=1, from 2021-07-05)
- pre-2021 backfill pickle (default the forward_volex remeasure work file; the
  run recorded in HANDOFF.md passed the production tree's copy via --hist)
- merged via research/rulecard/data.load_extended_ohlcv(issuance=True), the
  D-053/D-055/D-064 canonical panel (gap-verified split repair + issuance
  correction), exactly as S1/S2 used it.

Conventions (declared)
- decision date d: class H = unlock session (first session >= listing + 8
  months); class I = resume_date (halt onsets counted beside); class K = the
  window's first session (known ex ante forever); class G has none (n/a).
- liquid universe at d: adv20 = mean(close*volume) over the ticker's 20
  sessions ending the session BEFORE d, >= Rp 10bn.
- pre-event vol: SD of the ticker's daily simple returns over its own 60
  sessions ending the session BEFORE d (>= 40 required else null).
- eras: era1 = decision < 2021-10-01, era2 = decision >= 2021-10-01.
- deflation bars (owner ruling 2026-10-07, DECISION_DRAFT_CENSUS_RATIFICATION_2026-10-07.md
  @ 2937488): census ratified at N = 595 (recount 561 + HYP-PM-0015 6 + BOS 8 + exit study 20),
  bar 3.2912; each new gate freezes at 595 + its own configurations — this inventory reports
  MDEs at N = 599 (595 + HYP-PM-0016's 4, bar 3.2931) as the PRIMARY figure and at the
  276-count bar (+ own arms, N = 280, bar 3.0713) as a SECONDARY line only. The brief's
  "276 vs 561" wording is superseded.
- MDE of the mean cumulative effect over H sessions: independent-events
  estimate bar * sigma_daily * sqrt(H) / sqrt(n); month-clustered (worst case,
  within-cluster correlation 1) bar * sigma_daily * sqrt(H) * sqrt(m/C) with
  C = distinct event months and m = n/C average events per cluster.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta
from scipy import integrate, stats

REPO = Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
PM = REPO / "docs" / "research_programs" / "P-M"
DEFAULT_HIST = PM / "forward_volex" / "remeasure" / "work" / "hist_pre2021.pkl"
OUT = Path(__file__).resolve().parent
DEFAULT_DB = REPO / "data" / "walkforward.db"

ERA2_START = pd.Timestamp("2021-10-01")
EVENT_FLOOR = pd.Timestamp("2009-01-01")   # census era floor (brief: 2009..2026)
ADV_GATE = 10e9                             # Rp 10bn, the day before the decision
VOL_WIN, VOL_MIN = 60, 40
ADV_WIN = 20
HORIZONS = [5, 10, 20]


def e_max_abs_z(n: int) -> float:
    return integrate.quad(lambda z: 1.0 - (2.0 * stats.norm.cdf(z) - 1.0) ** n, 0, 40)[0]


# --------------------------------------------------------------------------- #
# session index: O(log n) per-ticker lookups of past-only liquidity/vol
# --------------------------------------------------------------------------- #

class SessionIndex:
    """Per-ticker sorted (dates, adv20_prev, vol60_prev) — every value is keyed
    to the LAST session strictly before the queried date, so no query can read
    a same-day or future statistic."""

    def __init__(self, T: pd.DataFrame):
        T = T.sort_values(["ticker", "date"], kind="mergesort")
        self.idx = {}
        for tk, g in T.groupby("ticker", sort=False):
            self.idx[tk] = (g["date"].values.astype("datetime64[D]"),
                            g["adv20_prev"].values, g["vol60_prev"].values)

    def adv(self, tk: str, d: pd.Timestamp):
        return self._at(tk, d, 1)

    def vol(self, tk: str, d: pd.Timestamp):
        return self._at(tk, d, 2)

    def _at(self, tk, d, col):
        v = self.idx.get(tk)
        if v is None:
            return None
        dates, adv, vol = v
        i = np.searchsorted(dates, np.datetime64(pd.Timestamp(d), "D"), side="left")
        if i == 0:
            return None
        x = (adv, vol)[col - 1][i - 1]
        return None if pd.isna(x) else float(x)

    def liquid_before(self, d: pd.Timestamp, gate: float = ADV_GATE) -> set:
        """Tickers whose LAST session strictly before d had adv20_prev >= gate."""
        out = []
        d64 = np.datetime64(pd.Timestamp(d), "D")
        for tk, (dates, adv, _vol) in self.idx.items():
            i = np.searchsorted(dates, d64, side="left")
            if i > 0 and not pd.isna(adv[i - 1]) and adv[i - 1] >= gate:
                out.append(tk)
        return set(out)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def era_of_list(dates) -> dict:
    s = pd.Series(pd.to_datetime(list(dates))).dropna()
    s = s[s >= EVENT_FLOOR]
    return {"era1_2009_2021-09": int((s < ERA2_START).sum()),
            "era2_2021-10_2026": int((s >= ERA2_START).sum())}


def count_by_year(dates) -> dict:
    s = pd.Series(pd.to_datetime(list(dates))).dropna()
    s = s[s >= EVENT_FLOOR]
    return {str(y): int(c) for y, c in s.dt.year.value_counts().sort_index().items()}


def pack_vol(series) -> dict:
    s = pd.Series(list(series)).dropna()
    if s.empty:
        return {"n": 0}
    q = s.quantile([0.25, 0.5, 0.75])
    return {"n": int(s.size), "median": round(float(q.loc[0.5]), 6),
            "iqr": [round(float(q.loc[0.25]), 6), round(float(q.loc[0.75]), 6)]}


def mde(sigma_daily, n: int, n_clusters: int, bar: float) -> dict:
    out = {"n": int(n or 0), "n_clusters": int(n_clusters or 0)}
    if not n or not sigma_daily or not n_clusters:
        out.update({str(h): None for h in HORIZONS})
        return out
    C = max(int(n_clusters), 1)
    sd_pct = sigma_daily * 100.0
    for h in HORIZONS:
        indep = bar * sd_pct * (h ** 0.5) / (n ** 0.5)
        # worst case: all m = n/C events inside a month move together, so the
        # cluster mean has SE sigma_H/sqrt(C) — clustering costs sqrt(n/C)
        clust = bar * sd_pct * (h ** 0.5) / (C ** 0.5)
        out[str(h)] = {"indep_pct": round(indep, 3), "month_clustered_pct": round(clust, 3)}
    return out


def load_panel(hist: Path) -> pd.DataFrame:
    from research.rulecard.data import load_extended_ohlcv
    O = load_extended_ohlcv(hist=hist, issuance=True)
    O["date"] = pd.to_datetime(O["date"])
    return O.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)


# --------------------------------------------------------------------------- #
# class H: IPO lock-up expiry (first-bar listing proxy, S2 onboarding rules)
# --------------------------------------------------------------------------- #

def class_H(panel: pd.DataFrame, SI: SessionIndex, BAR: dict) -> dict:
    first = panel.groupby("ticker", sort=True)["date"].min()
    corpus_start = pd.Timestamp("2021-07-05")
    backfill_start = first.min()
    onboarding = first[(first == corpus_start) | (first == backfill_start)]
    listing = first.drop(index=onboarding.index)
    listing = listing[listing >= EVENT_FLOOR]

    cal = np.sort(panel["date"].unique())
    rows, vols_all, vols_liq = [], [], []
    exited, liq_dates = 0, []
    last_bar = panel.groupby("ticker", sort=True)["date"].max()
    panel_end = panel["date"].max()
    for tk, ld in listing.items():
        unlock = ld + relativedelta(months=8)
        i = np.searchsorted(cal, np.datetime64(unlock, "D"))
        if i >= len(cal):
            continue
        d = pd.Timestamp(cal[i])                       # unlock session
        a, v = SI.adv(tk, d), SI.vol(tk, d)
        if a is not None and a >= ADV_GATE:
            liq_dates.append(d)
            if v is not None:
                vols_liq.append(v)
        if v is not None:
            vols_all.append(v)
        rows.append(d)
        if last_bar.get(tk, panel_end) < panel_end - pd.Timedelta(days=183):
            exited += 1

    from data.db import connect
    with connect(path=DEFAULT_DB, read_only=True) as c:
        susp_tickers = {r[0] for r in c.execute("SELECT DISTINCT ticker FROM suspension_events")}
    overlap_susp = sum(1 for tk in listing.index if tk in susp_tickers)

    return {
        "class": "H_ipo_lockup_8m",
        "listing_proxy": "first panel bar; onboarding artifacts excluded "
                         "(first bar == 2021-07-05 corpus start or backfill start)",
        "onboarding_artifacts_excluded": int(onboarding.size),
        "listing_tickers_since_2009": int(listing.size),
        "lockup_rule": "8 months post-listing (POJK-era statutory rule; exact article "
                       "and start year flagged TO-VERIFY against primary source — "
                       "no fetching allowed in this task)",
        "unlock_events_since_2009": len(rows),
        "events_by_unlock_year": count_by_year(rows),
        "events_by_era": era_of_list(rows),
        "liquid_unlock_events_total": len(liq_dates),
        "liquid_events_by_era": era_of_list(liq_dates),
        "cohort_tickers_exited_panel_gap6m": exited,
        "overlap_tickers_with_any_suspension_row": overlap_susp,
        "preevent_vol_all": pack_vol(vols_all),
        "preevent_vol_liquid": pack_vol(vols_liq),
        "mde_liquid": {
            "bar_primary_599": mde(np.median(vols_liq) if vols_liq else None,
                                   len(liq_dates), len({str(d)[:7] for d in liq_dates}),
                                   BAR["primary_599"]),
            "bar_secondary_280": mde(np.median(vols_liq) if vols_liq else None,
                                     len(liq_dates), len({str(d)[:7] for d in liq_dates}),
                                     BAR["secondary_280"]),
        },
    }


# --------------------------------------------------------------------------- #
# class I: suspension / resumption (outcome-tainted fields excluded)
# --------------------------------------------------------------------------- #

def class_I(panel: pd.DataFrame, SI: SessionIndex, BAR: dict) -> dict:
    from data.db import connect
    with connect(path=DEFAULT_DB, read_only=True) as c:
        S = pd.read_sql("SELECT ticker, last_normal_date, resume_date, missing_td, "
                        "classification FROM suspension_events", c)
    S["last_normal_date"] = pd.to_datetime(S["last_normal_date"])
    S["resume_date"] = pd.to_datetime(S["resume_date"])

    first = panel.groupby("ticker", sort=True)["date"].min()

    # price-free population split (amendment 1, class I). The recorded
    # `classification` label derives from the resume-gap rule (outcome-derived),
    # so the census also splits episodes by session-presence breadth only: an
    # episode is ticker-specific when, on its missing sessions, < 50% of the
    # PIT-liquid peers (gate as of the halt onset) are also absent. Episodes
    # whose entire missing period is absent from the panel's session axis have
    # NO observable missing session — the market-wide/infra signature (every
    # name missing together removes those dates from the session axis) — and
    # are counted as such. No price is read anywhere in this split.
    sessions_all = np.sort(panel["date"].unique())
    present = panel.groupby("date", sort=True)["ticker"].apply(set).to_dict()
    episode_tag = {}
    for r in S.itertuples():
        miss = sessions_all[(sessions_all > np.datetime64(r.last_normal_date, "D"))
                            & (sessions_all < np.datetime64(r.resume_date, "D"))]
        if len(miss) == 0:
            episode_tag[(r.ticker, r.last_normal_date)] = "no_observable_missing_session"
            continue
        peers = SI.liquid_before(pd.Timestamp(r.last_normal_date)
                                 + pd.Timedelta(days=1))
        if len(peers) < 20:
            episode_tag[(r.ticker, r.last_normal_date)] = "peer_set_too_small"
            continue
        ratios = []
        for m in miss:
            mset = present.get(pd.Timestamp(m), set())
            ratios.append(sum(1 for pk in peers if pk not in mset) / len(peers))
        episode_tag[(r.ticker, r.last_normal_date)] = (
            "breadth_ticker_specific" if np.mean(ratios) < 0.50
            else "breadth_market_infra")

    S["episode_tag"] = [episode_tag[(r.ticker, r.last_normal_date)]
                        for r in S.itertuples()]

    def summarize(sub, label):
        resume_dates, resume_liq, vols_res, vols_res_liq = [], [], [], []
        for r in sub.itertuples():
            resume_dates.append(r.resume_date)
            a = SI.adv(r.ticker, r.resume_date)
            liquid = a is not None and a >= ADV_GATE
            if liquid:
                resume_liq.append(r.resume_date)
            v = SI.vol(r.ticker, r.resume_date)
            if v is not None:
                vols_res.append(v)
                if liquid:
                    vols_res_liq.append(v)
        med = np.median(vols_res_liq) if vols_res_liq else None
        return {
            "rows": int(len(sub)),
            "resumptions_total": len(resume_dates),
            "resumptions_by_era": era_of_list(resume_dates),
            "liquid_resumptions_total": len(resume_liq),
            "liquid_by_era": era_of_list(resume_liq),
            "preevent_vol_liquid": pack_vol(vols_res_liq),
            "mde_liquid": {
                "bar_primary_599": mde(med, len(resume_liq),
                                       len({str(d)[:7] for d in resume_liq}),
                                       BAR["primary_599"]),
                "bar_secondary_280": mde(med, len(resume_liq),
                                         len({str(d)[:7] for d in resume_liq}),
                                         BAR["secondary_280"]),
            },
        }

    first_loop = True
    young = 0
    for r in S.itertuples():
        ld = first.get(r.ticker)
        if ld is not None and (r.last_normal_date - ld).days <= 2 * 365:
            young += 1

    out = {
        "class": "I_suspension_resumption",
        "rows_total": int(len(S)),
        "field_taint": "gap_pct and classification are OUTCOME-TAINTED "
                       "(engine/suspension_detector.py: gap_pct=(resume_open-last_close)/"
                       "last_close; classification = abs(gap_pct)>=10%) — neither enters "
                       "any statistic below except as a population LABEL (disclosed)",
        "db_span": [str(S["last_normal_date"].min().date()), str(S["resume_date"].max().date())],
        "note_db_era_only": "suspension_events derives from the DB corpus (ohlcv from "
                            "2021-07-05); no pre-2021 suspension history exists",
        "halt_onsets_by_year_last_normal": count_by_year(S["last_normal_date"]),
        "missing_td_median": float(S["missing_td"].median()),
        "missing_td_p90": float(S["missing_td"].quantile(0.9)),
        "events_within_2y_of_listing_proxy": young,
        "board_placement_data": "ABSENT (dataset_b/foundation.py: 'Pemantauan Khusus "
                                "call-auction names are NOT modelled'); no announcement "
                                "dates stored — halt knowable T+1 by absence, resumption "
                                "date not known before the resume session",
        "populations": {
            "all_rows_upper_bound_incl_collection_gaps": summarize(S, "all"),
            "recorded_suspension_label_outcome_conditioned_label": summarize(
                S[S["classification"] == "suspension"], "rec"),
            "breadth_ticker_specific_price_free": summarize(
                S[S["episode_tag"] == "breadth_ticker_specific"], "bts"),
        },
        "episode_tag_counts": {str(k): int(v)
                               for k, v in S["episode_tag"].value_counts().items()},
        "breadth_split_note": "no_observable_missing_session = the missing dates are "
                              "not panel sessions at all — the market-wide/infra "
                              "signature; those episodes have no session to price and "
                              "are excluded from resumption populations by construction",
    }
    return out


# --------------------------------------------------------------------------- #
# class K: calendar windows (pooled; exactly 2 predeclared windows)
# --------------------------------------------------------------------------- #

def class_K(panel: pd.DataFrame, SI: SessionIndex, BAR: dict) -> dict:
    cal = pd.to_datetime(pd.Series(np.sort(panel["date"].unique())))
    by_month_last = cal.groupby(cal.dt.to_period("M")).max()
    by_month_first = cal.groupby(cal.dt.to_period("M")).min()
    cal_arr = cal.values.astype("datetime64[D]")

    def sessions_from(d: pd.Timestamp, n: int):
        i = np.searchsorted(cal_arr, np.datetime64(d, "D"))
        if i + n > len(cal_arr):
            return None
        return list(pd.to_datetime(cal_arr[i:i + n]))

    def portfolio_vol_before(d: pd.Timestamp):
        """EW liquid-portfolio daily-return SD over the 60 sessions strictly
        before d. Membership fixed at the session BEFORE that 60-session block
        (the brief's 'day before' gate); pre-block only, no window data.
        (Revision: reads the shared WIDE close matrix; identical semantics to
        the first run's pivot-table construction.)"""
        return ew_book_vol_before(panel, SI, d, min_names=20)

    w1, w2 = [], []
    for m in sorted(by_month_first.index):
        if m < pd.Period("2009-01") or m >= by_month_first.index.max():
            continue
        nxt = m + 1
        if nxt not in by_month_first.index:
            continue
        d = by_month_first[nxt]
        sess = sessions_from(d, 3)
        if sess is None:
            continue
        w1.append({"start": d, "sessions": [by_month_last[m]] + sess})
        if m.month in (3, 6, 9, 12):
            i = np.searchsorted(cal_arr, np.datetime64(by_month_last[m], "D"))
            if i >= 4:
                start = pd.Timestamp(cal_arr[i - 4])
                sess2 = sessions_from(start, 5)
                if sess2 is not None:
                    w2.append({"start": start, "sessions": sess2})

    s1 = {str(s) for w in w1 for s in w["sessions"]}
    s2 = {str(s) for w in w2 for s in w["sessions"]}
    shared = len(s1 & s2)

    out = {}
    for key, wins, defn in (
        ("W1_turn_of_month_last1_plus_next3", w1,
         "last session of month + first 3 of next month (4 sessions); mechanism: "
         "scheduled payroll/pension/mutual-fund inflows concentrating at month turns"),
        ("W2_quarter_end_last5_MJSD", w2,
         "last 5 sessions of Mar/Jun/Sep/Dec (5 sessions); mechanism: quarter/year-end "
         "window dressing by local funds + quarter-end institutional rebalancing"),
    ):
        starts = [w["start"] for w in wins if w["start"] >= EVENT_FLOOR]
        vols = [v for d in starts if (v := portfolio_vol_before(d)) is not None]
        out[key] = {
            "definition": defn,
            "instances_since_2009": len(starts),
            "instances_by_era": era_of_list(starts),
            "preevent_vol_ew_liquid_portfolio": pack_vol(vols),
            "mde_portfolio": {
                "bar_primary_599": mde(np.median(vols) if vols else None,
                                       len(starts), len({str(d)[:7] for d in starts}),
                                       BAR["primary_599"]),
                "bar_secondary_280": mde(np.median(vols) if vols else None,
                                         len(starts), len({str(d)[:7] for d in starts}),
                                         BAR["secondary_280"]),
            },
        }
    out["multiplicity_note"] = (
        "exactly 2 windows predeclared in this inventory; no window scan and no "
        "alternative offsets were computed — calendar effects are the classic "
        "data-mining zoo, and any window beyond these 2 is a new census entry")
    out["session_overlap_W1_W2_sessions"] = int(shared)
    out["lebaran_thr_note"] = (
        "Lebaran/THR NOT computed: Eid al-Fitr closure dates are not in the DB and "
        "hardcoding recalled holiday dates was judged too error-prone for a frozen "
        "inventory; needs the official IDX holiday archive (small effort, backfillable "
        "point-in-time). Valid candidate window for a later D-entry, NOT one of the 2 "
        "predeclared windows here.")
    return out


# --------------------------------------------------------------------------- #
# class G: no event dates — panel risk summary only (labeled)
# --------------------------------------------------------------------------- #

def class_G(panel: pd.DataFrame, SI: SessionIndex, BAR: dict) -> dict:
    cal = pd.Series(np.sort(panel["date"].unique()))
    cal = pd.to_datetime(cal).drop_duplicates().reset_index(drop=True)
    qe = cal[cal.dt.month.isin([3, 6, 9, 12])]
    qe = qe.groupby(qe.dt.to_period("Q")).max()          # last session per quarter
    vols, liq_sizes = [], []
    for d in qe[qe >= EVENT_FLOOR]:
        liq = SI.liquid_before(d)
        liq_sizes.append(len(liq))
        for tk in liq:
            v = SI.vol(tk, d)
            if v is not None:
                vols.append(v)
    return {
        "class": "G_global_index_rebalances",
        "event_dates_in_db": "NONE — no membership table; scheduler/scanner.py:889 "
                             "_event_guard_active() holds ONE hardcoded window "
                             "(paper_config event_guard 2026-06-15..2026-06-24, MSCI "
                             "accessibility review Jun 18 + classification Jun 23 2026); "
                             "no announcement/effective/add-delete history",
        "panel_risk_summary_NOT_event_power": (
            "60-session daily SD of liquid names (ADV20 >= Rp 10bn), read at the last "
            "session of each quarter 2009..2026 — a panel risk measure per D-070, NOT "
            "event-conditioned power; MDE below is parameterized by the unknown event "
            "count N (announcement dates do not exist yet)"),
        "liquid_names_at_quarter_ends_median": int(np.median(liq_sizes)) if liq_sizes else 0,
        "preevent_vol_liquid_names_quarter_ends": pack_vol(vols),
        "mde_parameterized_by_N": {
            str(n): {
                "bar_primary_599": mde(np.median(vols) if vols else None, n,
                                       max(n // 4, 1), BAR["primary_599"]),
                "bar_secondary_280": mde(np.median(vols) if vols else None, n,
                                         max(n // 4, 1), BAR["secondary_280"]),
            }
            for n in (50, 100, 200)
        },
        "cluster_assumption": "quarterly/semi-annual reviews mean ~3-6 event months per "
                              "year; the clustered column assumes ~4 events per month "
                              "cluster, worst-case within-cluster correlation 1 — "
                              "illustrative until announcement dates exist",
    }



# --------------------------------------------------------------------------- #
# module-level EW-book pre-vol (shared by M and N; class K keeps its own nested
# variant frozen as first run)
# --------------------------------------------------------------------------- #

WIDE = None  # date x ticker close matrix, set once in main()


def ew_book_vol_before(panel: pd.DataFrame, SI: SessionIndex, d: pd.Timestamp,
                       members=None, min_names: int = 5):
    """EW book daily-return SD over the 60 sessions strictly before d.
    members = PIT membership set (default: the liquid gate at d).
    Reads the precomputed WIDE close matrix; the slice is strictly < d."""
    if WIDE is None:
        return None
    pre = WIDE.index[WIDE.index < d]
    if len(pre) < VOL_WIN + 1:
        return None
    pre = pre[-(VOL_WIN + 1):]
    liq = set(members) if members is not None else SI.liquid_before(pre[0])
    if len(liq) < min_names:
        return None
    r = WIDE.loc[pre, sorted(liq)].pct_change().dropna(how="all")
    port = r.mean(axis=1).dropna()
    return float(port.std()) if len(port) >= VOL_MIN else None


# --------------------------------------------------------------------------- #
# class M: pooled short-term reversal — STOPPED; allowed stats only
# --------------------------------------------------------------------------- #

def class_M(panel: pd.DataFrame, SI: SessionIndex, BAR: dict) -> dict:
    cal = pd.to_datetime(pd.Series(np.sort(panel["date"].unique())))
    iso = cal.dt.isocalendar()
    weekly_last = cal.groupby([iso["year"], iso["week"]]).max().sort_values()
    weekly_last = weekly_last[weekly_last >= EVENT_FLOOR]
    xs_sizes, vols, eras = [], [], {"era1_2009_2021-09": 0, "era2_2021-10_2026": 0}
    for d in weekly_last:
        eras["era1_2009_2021-09" if d < ERA2_START else "era2_2021-10_2026"] += 1
        xs_sizes.append(len(SI.liquid_before(d)))
        v = ew_book_vol_before(panel, SI, d)
        if v is not None:
            vols.append(v)
    return {
        "class": "M_pooled_short_term_reversal",
        "status": "STOPPED — prior coverage: Price-Reversal {R1,R2} (HYP-PM-0012 "
                  "FADE-001 / HYP-PM-0014 BANK-001, in forward test), M2x NO-GO "
                  "(DISCOVERY_2026-08-21), factor_zoo 1-week reversal dead in "
                  "robustness, D-062 bars correlated registration",
        "n_formation_dates": int(len(weekly_last)),
        "formation_dates_by_era": eras,
        "median_xs_size": int(np.median(xs_sizes)) if xs_sizes else 0,
        "preevent_vol_ew_liquid_book": pack_vol(vols),
        "note": "per the brief's M rule: formation-date counts, cross-section size "
                "and pre-formation volatility ONLY. No portfolio return exists in "
                "this census.",
    }


# --------------------------------------------------------------------------- #
# class N: global commodity / geopolitical conditions -> IDX exporter sectors
# --------------------------------------------------------------------------- #

COMMODITY_MAP = {
    "coal": [("Energy", "Thermal Coal"), ("Basic Materials", "Coking Coal")],
    "oil_gas": [("Energy", "Oil & Gas E&P"), ("Energy", "Oil & Gas Drilling"),
                ("Energy", "Oil & Gas Equipment & Services"),
                ("Energy", "Oil & Gas Refining & Marketing")],
    "gold": [("Basic Materials", "Gold"),
             ("Basic Materials", "Other Precious Metals & Mining")],
    "copper_nickel": [("Basic Materials", "Other Industrial Metals & Mining"),
                      ("Basic Materials", "Aluminum")],
    "cpo": [("Consumer Defensive", "Farm Products")],
}


def class_N(panel: pd.DataFrame, SI: SessionIndex, BAR: dict) -> dict:
    from data.db import connect
    with connect(path=DEFAULT_DB, read_only=True) as c:
        SEC = pd.read_sql("SELECT ticker, sector, industry FROM ticker_sector", c)
    bucket_tickers = {}
    for b, pairs in COMMODITY_MAP.items():
        tks = set()
        for sec, ind in pairs:
            tks |= set(SEC.loc[(SEC["sector"] == sec) & (SEC["industry"] == ind),
                               "ticker"])
        bucket_tickers[b] = sorted(tks)

    cal = pd.to_datetime(pd.Series(np.sort(panel["date"].unique())))
    month_ends = cal.groupby(cal.dt.to_period("M")).max().sort_values()
    month_ends = month_ends[month_ends >= EVENT_FLOOR]

    out = {"class": "N_commodity_geopolitical_exporter_sectors",
           "mapping_basis": "ticker_sector (industry level; yfinance-style taxonomy)",
           "rebalance_dates_total": int(len(month_ends)),
           "rebalance_dates_by_era": era_of_list(month_ends),
           "buckets": {}}
    for b, tks in bucket_tickers.items():
        per_year, sigs, n_rebal = {}, [], 0
        for d in month_ends:
            mem = [t for t in tks if (a := SI.adv(t, d)) is not None and a >= ADV_GATE]
            per_year.setdefault(d.year, set()).update(mem)
            if len(mem) >= 3:
                n_rebal += 1
                v = ew_book_vol_before(panel, SI, d, members=mem, min_names=3)
                if v is not None:
                    sigs.append(v)
        med = float(np.median(sigs)) if sigs else None
        out["buckets"][b] = {
            "tickers_mapped": len(tks),
            "liquid_names_per_year": {str(y): len(v)
                                      for y, v in sorted(per_year.items())},
            "rebalance_dates_with_3plus_liquid": n_rebal,
            "pre_formation_vol_book": pack_vol(sigs),
            "mde_monthly_21d": {
                "bar_primary_599": mde(med, n_rebal, n_rebal, BAR["primary_599"]),
                "bar_secondary_280": mde(med, n_rebal, n_rebal, BAR["secondary_280"]),
            },
        }
    out["note"] = ("signal legs (commodity returns, GPR) are the SIGNAL series, "
                   "not outcomes; their acquisition is a separate logged one-time "
                   "probe (probe_class_n.py), not part of this census. No sector or "
                   "stock return after any formation date is computed here.")
    return out


# --------------------------------------------------------------------------- #
# class O: opening-auction order imbalance (minute bars) — feasibility only
# --------------------------------------------------------------------------- #

IDX_TICK_LADDER = ((200.0, 1.0), (500.0, 2.0), (2000.0, 5.0),
                   (5000.0, 10.0), (float("inf"), 25.0))


def _tick_size(px: float) -> float:
    for lim, t in IDX_TICK_LADDER:
        if px < lim:
            return t
    return 25.0


DECISION_MINUTE = "09:15"   # declared; no price at/after this minute is read


def class_O(panel: pd.DataFrame, SI: SessionIndex, BAR: dict) -> dict:
    # The frozen minute store is production-host-only and NOT in this worktree;
    # this census runs ON the production host, so the production-tree path is
    # used READ-ONLY (mode=ro URI; nothing in the production tree is written,
    # checked out or modified — the brief's production rule targets writes).
    store = REPO / "data" / "frozen" / "stockbit-flow-bars-v002" / "stockbit-flow-bars-v002.db"
    if not store.exists():
        store = Path("/home/tjiesar/10 Projects/idx-walkforward-5001/data/frozen/"
                     "stockbit-flow-bars-v002/stockbit-flow-bars-v002.db")
    if not store.exists():
        return {"class": "O_opening_auction_imbalance",
                "store_present": False, "store_path": str(store)}
    con = sqlite3.connect(f"file:{store}?mode=ro", uri=True, timeout=30)
    cols = [r[1] for r in con.execute("PRAGMA table_info(stockbit_flow_bars)")]
    tcol = "bar_time" if "bar_time" in cols else cols[2]
    pcol = "price" if "price" in cols else ("last_price" if "last_price" in cols else None)
    dates = [r[0] for r in con.execute(
        f"SELECT DISTINCT trade_date FROM stockbit_flow_bars ORDER BY trade_date")]

    # cumulative-within-day verification (deterministic sample, lots only)
    pick = [dates[i * (len(dates) - 1) // 11] for i in range(12)]
    viol, checked, flat_share_all = 0, 0, []
    for d in pick:
        tks = [r[0] for r in con.execute(
            "SELECT DISTINCT ticker FROM stockbit_flow_bars WHERE trade_date=? "
            "ORDER BY ticker LIMIT 5", (d,))]
        for tk in tks:
            rows = con.execute(
                f"SELECT buy_lot, sell_lot, buy_freq, sell_freq FROM stockbit_flow_bars "
                f"WHERE trade_date=? AND ticker=? ORDER BY {tcol}", (d, tk)).fetchall()
            if len(rows) < 2:
                continue
            checked += 1
            for a, b in zip(rows, rows[1:]):
                if any(y < x for x, y in zip(a, b)):
                    viol += 1
                    break

    # per-session pre-decision-minute aggregates (price ONLY < 09:15)
    sig_days, imb_days, tick_days, liquid_days = [], [], [], 0
    flat_counts, ret_counts = [], []
    for d in dates:
        df = pd.read_sql(
            f"SELECT ticker, {tcol} AS t, buy_lot, sell_lot, {pcol} AS px "
            f"FROM stockbit_flow_bars WHERE trade_date=? AND {tcol} < ?",
            con, params=(d, DECISION_MINUTE))
        if df.empty:
            continue
        # liquid gate as of the session BEFORE d: querying d+1day returns the
        # row at d itself, whose adv20_prev ends the session before d
        liq = SI.liquid_before(pd.Timestamp(d) + pd.Timedelta(days=1))
        for tk, g in df.groupby("ticker"):
            g = g.sort_values("t")
            b0, s0 = int(g["buy_lot"].iloc[0]), int(g["sell_lot"].iloc[0])
            if tk in liq:
                liquid_days += 1
                px = g["px"].dropna()
                px = px[px > 0]
                if b0 + s0 > 0:
                    imb_days.append(abs(b0 - s0) / (b0 + s0))
                if len(px) >= 9:
                    r = px.pct_change().dropna()
                    if len(r) >= 8:
                        sig_days.append(float(r.std(ddof=1)))
                        flat_counts.append(int((r == 0).sum()))
                        ret_counts.append(len(r))
                if len(px):
                    p0 = float(px.iloc[0])
                    tick_days.append(_tick_size(p0) / p0)
    con.close()

    med_sig = float(np.median(sig_days)) if sig_days else None
    flat_share = (float(np.sum(flat_counts) / np.sum(ret_counts))
                  if ret_counts else None)
    clean_sessions = None
    live_cols, live_idx, live_note = [], [], ""
    try:
        from data.db import connect
        with connect(path=DEFAULT_DB, read_only=True) as c:
            live_cols = [r[1] for r in c.execute(
                "PRAGMA table_info(stockbit_flow_bars)")]
            live_idx = [r[1] for r in c.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name="
                "'stockbit_flow_bars'")]
    except Exception as e:  # live probe is best-effort; never fatal
        live_cols, live_note = str(e), "live schema probe failed"
    # The live table has no trade_date index (a COUNT DISTINCT would full-scan a
    # production DB mid-service), so the clean-window session count comes from
    # the daily panel's session axis — the same IDX calendar the live table
    # appends to.
    clean_sessions = int((WIDE.index > pd.Timestamp("2026-04-27")).sum())
    live_note = (live_note or
                 "clean-window sessions from the panel calendar (live table has no "
                 "trade_date index; a full scan of the production DB was skipped)")

    out = {
        "class": "O_opening_auction_imbalance",
        "store": {"path": str(store), "columns": cols, "time_column": tcol,
                  "price_column": pcol,
                  "seen_window": [dates[0], dates[-1]], "sessions_seen": len(dates)},
        "cumulative_check": {
            "method": f"12 dates x first 5 tickers each, full day ordered by {tcol}; "
                      "buy_lot/sell_lot/buy_freq/sell_freq must be nondecreasing",
            "ticker_days_checked": checked, "violations": viol,
            "conclusion": "cumulative within the day" if viol == 0 else
                          f"{viol}/{checked} violated — per-minute flow needs differencing",
        },
        "decision_minute": DECISION_MINUTE,
        "seen_window_liquid": {
            "liquid_ticker_days": liquid_days,
            "sigma_1min_pre_decision": pack_vol(sig_days),
            "flat_minute_share_of_returns": flat_share,
            "imbalance_computable_share": (len(imb_days) / liquid_days
                                            if liquid_days else None),
            "median_abs_imbalance_09_00": (float(np.median(imb_days))
                                            if imb_days else None),
            "tick_le_0_2pct_of_price_share": (float(np.mean([t <= 0.002
                                                             for t in tick_days]))
                                              if tick_days else None),
        },
        "power": {
            "horizons_minutes": {"to_10_00": 45, "to_close": 275,
                                 "note": "minutes from 09:15; 275 = 135 pre-lunch "
                                         "+ 140 post-lunch; iid minute scaling declared"},
            "n_independent_ticker_days": len(sig_days),
            "n_date_clusters": len(dates),
            "median_sigma_1min": med_sig,
            "mde_pct_of_price": {
                f"{hz}_{bkey}": (None if med_sig is None else round(
                    bar * med_sig * 100.0 * (mins ** 0.5)
                    / ((len(sig_days) if bkey.startswith("indep") else len(dates)) ** 0.5), 3))
                for hz, mins in (("to_10_00", 45), ("to_close", 275))
                for bkey, bar in (("indep_bar599", BAR["primary_599"]),
                                  ("indep_bar280", BAR["secondary_280"]),
                                  ("dateclust_bar599", BAR["primary_599"]),
                                  ("dateclust_bar280", BAR["secondary_280"]))
            },
            "note": "MDE = bar * sigma_1min * sqrt(minutes) / sqrt(n); indep n = "
                    "liquid ticker-days, date-clustered n = distinct dates",
        },
        "live_clean_window": {
            "live_table_columns": live_cols, "live_indexes": live_idx,
            "distinct_dates_since_2026_04_28": clean_sessions,
            "live_note": live_note,
            "note": "clean (never-seen) window starts 2026-04-28; 2025-01..2026-04 "
                    "is SEEN by the planner's descriptive volatility-profile read",
        },
        "costs": {
            "round_trip_fees_tax_pct": 0.4,
            "tick_ladder_idr": [[200, 1], [500, 2], [2000, 5], [5000, 10], ["inf", 25]],
            "verdict_inputs": "one tick is 0.1-0.6% of price on mid-priced names; "
                              "fees+tax ~0.4% RT — an intraday effect must clear "
                              "~0.5-1.0% per round trip to matter",
        },
        "no_outcome_note": "no price at or after 09:15 was read in any window; "
                           "volatility uses minutes 09:00..09:14 only",
    }
    return out


def main():
    global DEFAULT_DB
    ap = argparse.ArgumentParser()
    ap.add_argument("--hist", type=Path, default=DEFAULT_HIST)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = ap.parse_args()
    DEFAULT_DB = args.db

    BAR = {
        "primary_599": round(e_max_abs_z(599), 4),
        "secondary_280": round(e_max_abs_z(280), 4),
        "reference_595": round(e_max_abs_z(595), 4),
        "reference_276": round(e_max_abs_z(276), 4),
        "check_266": round(e_max_abs_z(266), 4),
    }
    assert abs(BAR["check_266"] - 3.0558) < 5e-4, BAR["check_266"]
    assert abs(BAR["reference_595"] - 3.2912) < 5e-4, BAR["reference_595"]
    assert abs(BAR["primary_599"] - 3.2931) < 5e-4, BAR["primary_599"]

    panel = load_panel(args.hist)
    SI = SessionIndex(_session_table(panel))
    global WIDE
    WIDE = panel.pivot_table(index="date", columns="ticker",
                             values="close").sort_index()

    out = {
        "census": "FEASIBILITY_B_2026-10-07 (mechanism inventory B, classes G/H/I/K/M/N/O)",
        "no_outcomes_rule": "no return/price-change/excess computed after any decision "
                            "date or window start; liquidity (ADV20) and pre-event vol only",
        "panel": {
            "rows": int(len(panel)),
            "tickers": int(panel["ticker"].nunique()),
            "span": [str(panel["date"].min().date()), str(panel["date"].max().date())],
            "loader": "research/rulecard/data.load_extended_ohlcv(issuance=True) — "
                      "D-053 backfill + DB corpus is_final=1, gap-verified split repair, "
                      "D-064 issuance correction (recorded per D-064 section D)",
            "hist_input": str(args.hist),
        },
        "deflation_bar": {
            "method": "exact E[max|Z|] = int_0^inf 1-(2*Phi(z)-1)^N dz (iid, two-sided), "
                      "identical to deflation_audit/bar_v2.py (D-064 section C)",
            "owner_ruling": "2026-10-07: the stricter recount governs "
                            "(DECISION_DRAFT_CENSUS_RATIFICATION_2026-10-07.md @ 2937488, "
                            "draft D-071). Census ratified at N=595 = 270 recorded + 245 "
                            "pattern studies + 20 double-top + 20 gap-battery + 6 X1 + 6 "
                            "HYP-PM-0015 + 8 BOS + 20 exit study. The brief's '276 vs 561' "
                            "wording is superseded.",
            "primary": "N = 599 = 595 + HYP-PM-0016's 4 configurations at filing; bar",
            "bar_primary_599": BAR["primary_599"],
            "bar_reference_595": BAR["reference_595"],
            "bar_secondary_280": BAR["secondary_280"],
            "bar_reference_276": BAR["reference_276"],
            "secondary_line_rule": "276-count bars (3.07) are reported as a secondary "
                                   "line only, per the ratification draft",
            "check_266": BAR["check_266"],
        },
        "power_convention": {
            "preevent_vol": "SD of daily simple returns over the ticker's 60 sessions "
                            "ending the session before the decision date (min 40)",
            "liquid_gate": "ADV20 (mean close*volume over 20 sessions ending the session "
                           "before the decision date) >= Rp 10bn",
            "mde": "bar * sigma_daily * sqrt(H) / sqrt(n) [independent]; month-clustered "
                   "= bar * sigma_daily * sqrt(H) * sqrt(m/C), C = event months, "
                   "m = n/C, worst-case within-cluster correlation 1",
        },
    }
    out["G"] = class_G(panel, SI, BAR)
    out["H"] = class_H(panel, SI, BAR)
    out["I"] = class_I(panel, SI, BAR)
    out["K"] = class_K(panel, SI, BAR)
    out["M"] = class_M(panel, SI, BAR)
    print("M done", flush=True)
    out["N"] = class_N(panel, SI, BAR)
    print("N done", flush=True)
    out["O"] = class_O(panel, SI, BAR)
    print("O done", flush=True)
    out["J"] = {
        "class": "J_earnings_pead",
        "census": "NONE POSSIBLE — no PIT filing dates; see FEASIBILITY_B section J",
        "stockbit_keystats": "9,781 rows, 110 fetch_dates 2026-04-10..2026-10-07, 972 "
                             "tickers; ratio snapshots only, no dates of record",
        "fundamentals_artifacts": "fund_quarterly.pkl ABSENT (script exists: "
                                  "factor_zoo/scripts/fetch_quarterly.py, output never "
                                  "committed); fund_annual.pkl 2,217 rows / 552 tickers, "
                                  "period_end 2021-12-31..2026-06-30; brief's '2,908 "
                                  "observations' not locatable in repo — DISCREPANCY "
                                  "RECORDED",
        "filing_dates": "none anywhere (yfinance period_end columns only)",
    }
    path = OUT / "CENSUS_FEASIBILITY_B.json"
    path.write_text(json.dumps(out, indent=1, default=str))
    print(f"wrote {path}")
    for cls in "GHIKMNO":
        c = out[cls]
        flat = {k: v for k, v in c.items() if k.startswith("mde")}
        for wk, wv in c.items():
            if isinstance(wv, dict):
                flat.update({f"{wk}.{k}": v for k, v in wv.items() if k.startswith("mde")})
        print(cls, json.dumps(flat, default=str)[:400])


def _session_table(panel: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for tk, g in panel.groupby("ticker", sort=False):
        g = g.sort_values("date")
        ret = g["close"].pct_change()
        adv20 = (g["close"] * g["volume"]).rolling(ADV_WIN).mean()
        vol60 = ret.rolling(VOL_WIN, min_periods=VOL_MIN).std()
        parts.append(pd.DataFrame({
            "ticker": tk, "date": g["date"].values,
            "adv20_prev": adv20.shift(1).values,   # as of the session BEFORE date
            "vol60_prev": vol60.shift(1).values,   # 60 sessions ending before date
        }))
    return pd.concat(parts, ignore_index=True)


if __name__ == "__main__":
    main()
