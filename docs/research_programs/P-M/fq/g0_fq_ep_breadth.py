#!/usr/bin/env python3
"""G0 for the {FQ} E/P arm (D-112): builds the monthly E/P panel and reports BREADTH only.

Implements G0_FREEZE_FQ_EP_2026-10-26.md (the frozen copy of the draft). The freeze file's sha256 is pinned below
and the script refuses to run until it is set and matches, so breadth is never seen before the thresholds freeze.

What it reads: KSEI month-end price and shares (at D, D-1, D-2 only), fin.db owners' net income and equity rows,
the D-111 lists. It never computes a return from D to any later date, and never reads a price after D for a
formation at D (tests/test_fq_g0.py poisons later prices to check this). Writes only into this directory.

    cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
    venv/bin/python3 docs/research_programs/P-M/fq/g0_fq_ep_breadth.py
"""
from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import json
import re
import sqlite3
import sys
from datetime import date, datetime, timedelta, timezone
from math import ceil, erf, sqrt
from pathlib import Path

HERE = Path(__file__).resolve().parent
DA = HERE.parent / "data_acquisition"
FREEZE = HERE / "G0_FREEZE_FQ_EP_2026-10-26.md"
FREEZE_SHA256 = None                       # set at freeze; None = refuse to run

KSEI_CSV = Path.home() / "idx_external" / "ksei" / "ksei_equity_holdings.csv"
FIN_DB = Path.home() / "idx_external" / "stockbit_fin" / "fin.db"
LATE_CSV = DA / "12_FQ_LATE_FILERS_2026-10-26.csv"
FYX_CSV = DA / "13b_FQ_FISCAL_YEAR_EXCEPTIONS.csv"
YAHOO_CSV = Path.home() / "idx_external" / "fx" / "usdidr_month_end_yahoo_2026-10-26.csv"
NEW_CODES = Path.home() / "idx_external" / "stockbit_fin" / "_ksei_missing92.txt"
FX_TOL = 0.03                              # report-only: vendor rate vs Yahoo month-end

# ---- frozen parameters (G0 freeze §2-§5) ----
FIRST_D, LAST_D = (2009, 5), (2026, 8)
TOP_N = 200
MIN_VALID = 120
STALE_MONTHS = 15                          # latest TTM quarter must end within 15 months of D
IR_FLOOR = 0.75                            # D-112
BAR = 3.300069                             # e_max_abs_z(614), deflation_audit/bar_v2.py
MIN_POWER = 0.20
TICKER_RE = re.compile(r"^[A-Z]{4}$")

# D-111 R4: COVID relaxed deadlines, keyed by period_end
COVID = {date(2019, 12, 31): date(2020, 5, 31), date(2020, 3, 31): date(2020, 6, 30),
         date(2020, 6, 30): date(2020, 10, 31), date(2020, 9, 30): date(2020, 11, 30),
         date(2020, 12, 31): date(2021, 5, 31), date(2021, 3, 31): date(2021, 6, 30),
         date(2021, 6, 30): date(2021, 10, 31), date(2021, 9, 30): date(2021, 11, 30),
         date(2021, 12, 31): date(2022, 4, 30), date(2022, 3, 31): date(2022, 6, 30),
         date(2022, 6, 30): date(2022, 10, 31), date(2022, 9, 30): date(2022, 11, 30),
         date(2022, 12, 31): date(2023, 4, 30)}
BASE_OFFSET = {3: 1, 6: 3, 9: 1, 12: 3}    # D-111 R3: months from period_end to deadline


def eom(y: int, m: int) -> date:
    y, m0 = y + (m - 1) // 12, (m - 1) % 12   # handles offsets either way
    m = m0 + 1
    return date(y, m, calendar.monthrange(y, m)[1])


def add_months_eom(d: date, k: int) -> date:
    return eom(d.year, d.month + k)


# ---------------------------------------------------------------- D-111 availability

def deadline_for(pe: date, fy_end: str | None) -> date | None:
    """Calendar deadline (a month end) for period_end pe; None = excluded (off-quarter fiscal year, R7)."""
    if fy_end is not None and fy_end not in ("31-Mar", "30-Sep"):
        return None
    d = COVID.get(pe, add_months_eom(pe, BASE_OFFSET[pe.month]))
    if fy_end is not None:                 # R7: FY-end and H1 periods take month 3; keep the later deadline
        fy_m = 3 if fy_end == "31-Mar" else 9
        h1_m = 9 if fy_m == 3 else 3
        if pe.month in (fy_m, h1_m):
            d = max(d, add_months_eom(pe, 3))
    return d


def first_qualifying(deadline: date, kdate: dict) -> date | None:
    """First formation date D with D >= usable_from, at month-end granularity (G0 freeze §3, D11).

    kdate maps (year, month) -> KSEI file date (that month's last trading day). If the deadline month's KSEI date is
    the calendar month end, the deadline was a trading day and usable_from is the next calendar month end; else the
    deadline moved into the next month (<= ~10th) and usable_from falls in the month after that."""
    y, m = deadline.year, deadline.month
    traded = kdate.get((y, m)) == deadline
    nxt = eom(y, m + 1)
    if traded and kdate.get((nxt.year, nxt.month)) == nxt:
        return nxt
    target = eom(y, m + 2)
    later = sorted(d for (yy, mm), d in kdate.items() if (yy, mm) >= (target.year, target.month))
    return later[0] if later else None


def classify_currency(stmt_equity, derived_equity):
    """'IDR' | 'USD' | None from the order of magnitude of vendor derived equity (IDR-converted) / statement equity.

    The derived row is 'Total Equity (Quarter)' (total equity) or, in the late-filer layout, 'Total Equity'
    (parent equity), so only the magnitude is used: ~1 means IDR, ~the USD/IDR rate means USD."""
    if not stmt_equity or not derived_equity:
        return None
    r = abs(derived_equity / stmt_equity)
    if 0.2 < r < 5:
        return "IDR"
    if 5000 < r < 25000:
        return "USD"
    return None


def carry_currency(known: dict) -> dict:
    """Fill periods with no balance-sheet currency from the issuer's nearest classified periods (within 4 quarters
    either side) when they do not conflict. known: period_end -> 'IDR' | 'USD' | None | 'AMB' (AMB is never filled)."""
    pes = sorted(known)
    out = dict(known)
    for i, pe in enumerate(pes):
        if known[pe] is not None:
            continue
        before = next((known[p] for p in reversed(pes[max(0, i - 4):i]) if known[p] in ("IDR", "USD")), None)
        after = next((known[p] for p in pes[i + 1:i + 5] if known[p] in ("IDR", "USD")), None)
        if before and after and before != after:
            continue
        out[pe] = before or after
    return out


def ttm_at(D: date, quarters: dict):
    """TTM owners' NI in IDR at formation date D, or (None, reason).

    quarters: period_end -> dict(ni, ccy, rate, qual, withheld). Takes the most recent quarter q0 usable at D for
    which q0 and the three preceding calendar quarters are all usable, unwithheld, with NI and a known currency."""
    usable = sorted((pe for pe, q in quarters.items() if q["qual"] is not None and q["qual"] <= D), reverse=True)
    if not usable:
        return None, "no_data"
    cutoff = add_months_eom(D, -STALE_MONTHS)
    first_reason = None
    for q0 in usable:
        if q0 < cutoff:                    # every later candidate is older still
            return None, first_reason or "stale"
        window = [add_months_eom(q0, -3 * k) for k in range(4)]
        reason = None
        total = 0.0
        for pe in window:
            q = quarters.get(pe)
            if q is None or q["qual"] is None or q["qual"] > D:
                reason = "gap"
            elif q["withheld"]:
                reason = "withheld"
            elif q["ccy"] is None:
                reason = "ccy"
            elif q["ni"] is None:
                reason = "gap"
            if reason:
                break
            total += q["ni"] * q["rate"]
        if reason is None:
            return total, "ok"
        first_reason = first_reason or reason
    return None, first_reason


# ---------------------------------------------------------------- universe

def universe_at(rows_d: dict, rows_m1: dict, rows_m2: dict) -> list[tuple[str, float]]:
    """Top-N by market cap among 4-letter codes with price > 0, after the stale filter (price equal at D, D-1, D-2).
    rows_*: ticker -> (sec_num, price). Returns [(ticker, mcap)] sorted by mcap desc."""
    out = []
    for t, (sec, px) in rows_d.items():
        if not TICKER_RE.match(t) or not px or px <= 0 or not sec or sec <= 0:
            continue
        p1, p2 = rows_m1.get(t, (None, None))[1], rows_m2.get(t, (None, None))[1]
        if p1 is not None and p2 is not None and px == p1 == p2:
            continue
        out.append((t, sec * px))
    out.sort(key=lambda x: -x[1])
    return out[:TOP_N]


def power(t_eff_years: float) -> float:
    z = IR_FLOOR * sqrt(t_eff_years) - BAR
    return 0.5 * (1 + erf(z / sqrt(2)))


def months_needed() -> int:
    from statistics import NormalDist
    return ceil(12 * ((BAR - NormalDist().inv_cdf(1 - MIN_POWER)) / IR_FLOOR) ** 2)


# ---------------------------------------------------------------- loading

def period_label_to_end(label: str) -> date | None:
    m = re.match(r"^(FY|Q1|H1|Q3)-?(\d{4})$", label.strip())
    if not m:
        return None
    kind, y = m.group(1), int(m.group(2))
    return {"Q1": date(y, 3, 31), "H1": date(y, 6, 30), "Q3": date(y, 9, 30), "FY": date(y, 12, 31)}[kind]


def load_ksei(path=KSEI_CSV):
    by_date: dict[date, dict] = {}
    for x in csv.DictReader(open(path)):
        d = date.fromisoformat(x["date"])
        try:
            sec, px = float(x["sec_num"]), float(x["price"])
        except (TypeError, ValueError):
            continue
        by_date.setdefault(d, {})[x["ticker"]] = (sec, px)
    return by_date


def load_fin(db=FIN_DB, withheld=frozenset(), fyx=None, yahoo=None):
    """ticker -> period_end -> dict(ni, ccy, rate, vendor_r, deadline, withheld). qual is filled by the caller.
    USD quarters convert at Yahoo's USD/IDR month-end close for the period-end month (G0 §3)."""
    fyx = fyx or {}
    yahoo = yahoo if yahoo is not None else load_yahoo()
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = {}
    def rowmap(stmt, cond):
        return {t: ro for t, ro in con.execute(
            f"select ticker, min(row_order) from fin_rows where statement=? and {cond} group by ticker", (stmt,))}
    att = rowmap("income", "account_en like 'Net Income Attributable%'")
    owners = {}
    for t, ro0 in att.items():
        r = con.execute("select min(row_order) from fin_rows where ticker=? and statement='income' and "
                        "account_en='Owners Of The Company' and row_order>?", (t, ro0)).fetchone()
        if r and r[0] is not None:
            owners[t] = r[0]
    eq_s = rowmap("balance", "account_en like 'Total Ekuitas%'")
    eq_q = rowmap("balance", "account_en='Total Equity (Quarter)'")
    eq_d = dict(eq_q)
    for t, ro in rowmap("balance", "account_en='Total Equity'").items():
        if t not in eq_d and t in eq_s and ro > eq_s[t]:      # late-filer layout: derived section after statement
            eq_d[t] = ro
    def values(stmt, rmap):
        out = {}
        for t, ro in rmap.items():
            for pe, v in con.execute("select period_end, value from fin_values where ticker=? and statement=? and "
                                     "row_order=?", (t, stmt, ro)):
                out[(t, pe)] = v
        return out
    ni, es, ed = values("income", owners), values("balance", eq_s), values("balance", eq_d)
    con.close()
    by_t: dict[str, dict] = {}
    for (t, pe_s) in set(ni) | set(es):
        by_t.setdefault(t, {})[date.fromisoformat(pe_s)] = pe_s
    for t, pes in by_t.items():
        known = {}
        for pe, pe_s in pes.items():
            a, b = es.get((t, pe_s)), ed.get((t, pe_s))
            c = classify_currency(a, b)
            known[pe] = c if c else ("AMB" if a and b else None)
        filled = carry_currency(known)
        for pe, pe_s in pes.items():
            ccy = filled[pe] if filled[pe] in ("IDR", "USD") else None
            rate = 1.0 if ccy == "IDR" else yahoo.get((pe.year, pe.month)) if ccy == "USD" else None
            if ccy == "USD" and rate is None:
                ccy = None
            a, b = es.get((t, pe_s)), ed.get((t, pe_s))
            vendor_r = b / a if ccy == "USD" and t in eq_q and a and b else None
            rows.setdefault(t, {})[pe] = {"ni": ni.get((t, pe_s)), "ccy": ccy, "rate": rate, "vendor_r": vendor_r,
                                          "equity": a,     # statement total equity (G1 B/M, ROE sensitivities)
                                          "deadline": deadline_for(pe, fyx.get(t)),
                                          "withheld": (t, pe) in withheld}
    return rows


def load_withheld(path=LATE_CSV):
    out = set()
    for x in csv.DictReader(open(path)):
        pe = period_label_to_end(x["period"])
        if pe:
            out.add((x["ticker"], pe))
    return frozenset(out)


def load_fyx(path=FYX_CSV):
    return {x["ticker"]: x["fy_end"] for x in csv.DictReader(open(path))}


# ---------------------------------------------------------------- run

def load_yahoo(path=YAHOO_CSV):
    out = {}
    for x in csv.DictReader(open(path)):
        d = date.fromisoformat(x["month_end"][:10])
        out[(d.year, d.month)] = float(x["usdidr"])
    return out


def fx_check(fin: dict, yahoo: dict, tol=FX_TOL):
    """Report-only: the vendor's implied USD/IDR rate (total-equity layout) vs the Yahoo month-end close used for
    conversion (G0 §3)."""
    n = off = 0
    worst = []
    for t, qs in fin.items():
        for pe, q in qs.items():
            if q["ccy"] != "USD" or not q.get("vendor_r"):
                continue
            y = yahoo.get((pe.year, pe.month))
            if not y:
                continue
            n += 1
            dev = q["vendor_r"] / y - 1
            if abs(dev) > tol:
                off += 1
                worst.append((round(dev, 4), t, pe.isoformat()))
    worst.sort(key=lambda x: -abs(x[0]))
    return {"usd_periods_checked": n, "beyond_tol": off, "share_beyond_tol": round(off / n, 4) if n else None,
            "tol": tol, "worst": worst[:10]}


def load_new_codes(path=NEW_CODES):
    return frozenset(x.strip() for x in open(path) if x.strip()) if Path(path).exists() else frozenset()


def build(by_date: dict, fin: dict, new_codes=frozenset()):
    dates = sorted(by_date)
    kdate = {(d.year, d.month): d for d in dates}
    for t, qs in fin.items():
        for q in qs.values():
            q["qual"] = first_qualifying(q["deadline"], kdate) if q["deadline"] else None
    forms = [d for d in dates if FIRST_D <= (d.year, d.month) <= LAST_D]
    idx = {d: i for i, d in enumerate(dates)}
    months = []
    for D in forms:
        i = idx[D]
        m1 = by_date[dates[i - 1]] if i >= 1 else {}
        m2 = by_date[dates[i - 2]] if i >= 2 else {}
        uni = universe_at(by_date[D], m1, m2)
        reasons, n_valid, n_usd, n_new = {}, 0, 0, 0
        for t, mcap in uni:
            qs = fin.get(t)
            if not qs:
                reasons["no_ticker"] = reasons.get("no_ticker", 0) + 1
                continue
            ttm, why = ttm_at(D, qs)
            if ttm is None:
                reasons[why] = reasons.get(why, 0) + 1
            elif ttm <= 0:
                reasons["negative"] = reasons.get("negative", 0) + 1
            else:
                n_valid += 1
                n_new += t in new_codes
                n_usd += any(q["ccy"] == "USD" for pe, q in qs.items() if q["qual"] and q["qual"] <= D
                             and pe >= add_months_eom(D, -12))
        months.append({"D": D.isoformat(), "universe": len(uni), "valid": n_valid, "valid_usd": n_usd,
                       "valid_new_codes": n_new, "qualifies": n_valid >= MIN_VALID, "missing": reasons})
    return months


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="{FQ} E/P G0 breadth")
    ap.parse_args(argv)
    if FREEZE_SHA256 is None or not FREEZE.exists() or \
            hashlib.sha256(FREEZE.read_bytes()).hexdigest() != FREEZE_SHA256:
        print("G0 freeze not pinned or changed; refusing to run (breadth stays unseen until the freeze).")
        return 2
    by_date = load_ksei()
    yahoo = load_yahoo()
    fin = load_fin(withheld=load_withheld(), fyx=load_fyx(), yahoo=yahoo)
    new_codes = load_new_codes()
    months = build(by_date, fin, new_codes)
    q = sum(m["qualifies"] for m in months)
    t_eff = q / 12
    pw = power(t_eff)
    coverage = {"new_codes": len(new_codes), "new_codes_with_fin": len(new_codes & set(fin)),
                "valid_name_months_from_new_codes": sum(m["valid_new_codes"] for m in months)}
    res = {"formation_months": len(months), "qualifying_months": q, "t_eff_years": round(t_eff, 3),
           "power": round(pw, 4), "bar": BAR, "ir_floor": IR_FLOOR, "months_needed": months_needed(),
           "stop_rule_fired": pw < MIN_POWER, "freeze_sha256": FREEZE_SHA256,
           "fx_check": fx_check(fin, yahoo), "new_code_coverage": coverage, "months": months}
    stamp = datetime.now(timezone(timedelta(hours=7))).strftime("%Y%m%dT%H%M%S")
    out = HERE / f"G0_RESULT_{stamp}.json"
    out.write_text(json.dumps(res, indent=1))
    print(f"qualifying {q}/{len(months)} months, T_eff {t_eff:.2f}y, power {pw:.1%} "
          f"(need {months_needed()} months) -> stop rule {'FIRED' if pw < MIN_POWER else 'not fired'}; {out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
