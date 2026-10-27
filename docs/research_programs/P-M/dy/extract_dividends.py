"""C-003 dividend-yield G0 — dividends-paid extraction from fin.db (v1).

Brief: ZCODE_BRIEF_C003_DIVIDEND_YIELD_G0_2026-10-28.md (L2). Point-in-time follows the frozen {FQ} rule
D-111 v3 by IMPORT from the frozen script (no duplication): deadline_for, COVID/BASE_OFFSET, fiscal-year
exceptions, late-filer withholding, USD classification and the Yahoo month-end rate table.

Construct (proposed for the freeze draft, not pinned here):
  payout per fiscal period  = -(sum of parent-dividends-PAID cashflow rows)      [positive = cash out]
  layout per ticker-year    = DISCRETE | CUMULATIVE | UNKNOWN (see classify_layout)
  quarterly series q        = discrete values, or first-differences for cumulative filers
  TTM payout at month t     = sum of q over the four most recent fiscal quarters whose D-111 availability <= t
  yield numerator/denominator uses TOTAL payout / KSEI market cap (price*sec_num) -- no per-share arithmetic.

Coverage mode counts, per year, the share of panel name-months (top-200 KSEI mcap, stale filter -- the D-112
universe rule) with a PIT-available TTM payout. No return is computed or read anywhere in this file.

Usage: venv/bin/python3 extract_dividends.py extract   -> dividends_quarterly_v1.csv + ttm_monthly_v1.csv
       venv/bin/python3 extract_dividends.py coverage  -> coverage_by_year_v1.csv (+ prints)
"""
from __future__ import annotations

import csv
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
FQ_DIR = HERE.parent / "fq"
sys.path.insert(0, str(FQ_DIR))
import g0_fq_ep_breadth as fq  # frozen {FQ} G0: D-111 rule + currency machinery, import only

FIN_DB = fq.FIN_DB
KSEI_CSV = fq.KSEI_CSV
OUT_Q = HERE / "dividends_quarterly_v1.csv"
OUT_TTM = HERE / "ttm_monthly_v1.csv"
OUT_COV = HERE / "coverage_by_year_v1.csv"

# ---- label rules (canonical account_en, Indonesian account_left fallback) ----
# Parent-company cash dividends PAID. Exclusions applied AFTER the include match.
INCLUDE_RE = re.compile(
    r"^(payment(s)? of (cash )?dividen(d|ds|s)?(, .*)?$"      # Payment Of Dividend[, Small...]
    r"|dividend payments?$"
    r"|cash dividend paid$"
    r"|payment of cash dividen[cs] ?.*$"                      # 'Payment Of Cash Dividens ...' typo family
    r"|dividen( kas)?$"                                       # bare vendor label + 'Dividen Kas'
    r"|pembayaran (d[ie]viden|dividen kas|deviden tunai)$"
    r"|pembayaran dividen kepada pemegang saham.*$"
    r"|pembayaran dividen tunai.*$"
    r"|pembagian dividen( kas)?$"
    r")", re.I)
EXCLUDE_RE = re.compile(
    r"non.?(controlling|control|pengendali)|kepentingan non|minorit|nci"
    r"|by (a )?sub|of (a )?sub|of an (in|investment)|from (a )?sub|subsidi|dividends? paid by the:"
    r"|anak perusahaan|entitas anak|asosiasi|associated|joint venture|ventura"
    r"|received|receipt|penerimaan|pendapatan|proceeds|perolehan|dari "
    r"|pajak|tax|uang muka|advance|utang|modal saham|share.?premium|reksa"
    r"|cancellation|untuk kepentingan", re.I)


def row_labels(con) -> list[tuple[str, int, str, str]]:
    """(ticker, row_order, account_en, row_left) for candidate cashflow rows."""
    return list(con.execute(
        "select ticker, row_order, account_en, row_left from fin_rows "
        "where statement='cashflow' and (account_en like '%ividen%' or account_en like '%ividend%' "
        "or row_left like '%ividen%')"))


def label_of(en, left) -> str:
    """The canonical label if the vendor mapped one (en differs from left), else the raw left.
    row_left can be an integer (positional layouts) -- coerce defensively."""
    en, left = str(en or "").strip(), str(left or "").strip()
    return en if en and en.lower() != left.lower() else (left or en)


def is_parent_dividend_paid(label: str) -> bool:
    return bool(INCLUDE_RE.match(label)) and not EXCLUDE_RE.search(label)


def sum_paid_rows(con, rows) -> dict[tuple[str, str], float]:
    """(ticker, period_end_iso) -> -(sum of included row values) -- positive = cash paid out."""
    out: dict[tuple[str, str], float] = {}
    for t, ro, en, left in rows:
        if not is_parent_dividend_paid(label_of(en, left)):
            continue
        for pe, v in con.execute(
                "select period_end, value from fin_values where ticker=? and statement='cashflow' "
                "and row_order=? and value is not null", (t, ro)):
            k = (t, pe)
            out[k] = out.get(k, 0.0) + (-v if v < 0 else v)   # normalize: payout positive
    return out


# ---- layout classification ----
KIND_Q = {"Q1": 1, "Q2": 2, "H1": 2, "Q3": 3, "Q4": 4, "FY": 4}


def parse_period(p: str):
    """'Q1 2026' | 'H1-2026' -> (kind_rank, year) or None."""
    m = re.match(r"^(Q1|H1|Q3|FY|Q2|Q4)[ -]?(\d{4})$", (p or "").strip())
    return (KIND_Q[m.group(1)], int(m.group(2))) if m else None


def classify_layout(periods: dict[str, float]) -> str:
    """DISCRETE if FY < max interim of the same year (BBCA shape); CUMULATIVE if monotone within any year;
    else UNKNOWN."""
    by_year: dict[int, dict[int, float]] = {}
    for p, v in periods.items():
        pr = parse_period(p)
        if pr and v:
            by_year.setdefault(pr[1], {})[pr[0]] = abs(v)
    for y, q in by_year.items():
        fy, interims = q.get(4), [v for k, v in q.items() if k < 4 and v]
        if fy is not None and interims:
            if fy < max(interims):
                return "DISCRETE"
            seq = [q.get(k) for k in (1, 2, 3, 4) if q.get(k)]
            if len(seq) >= 3 and all(a <= b for a, b in zip(seq, seq[1:])):
                return "CUMULATIVE"
    return "UNKNOWN"


def quarterly_series(periods: dict[str, float], layout: str) -> dict[date, float]:
    """period label/value -> period_end date -> discrete quarterly payout (first-diff for CUMULATIVE)."""
    out: dict[date, float] = {}
    if layout == "DISCRETE":
        for p, v in periods.items():
            m = re.match(r"^(Q1|H1|Q3|FY|Q2|Q4)[ -]?(\d{4})$", (p or "").strip())
            if m and v:
                out[_period_end(m.group(1), int(m.group(2)))] = abs(v)
    elif layout == "CUMULATIVE":
        by_year: dict[int, dict[int, float]] = {}
        for p, v in periods.items():
            pr = parse_period(p)
            if pr and v:
                by_year.setdefault(pr[1], {})[pr[0]] = abs(v)
        for y, q in by_year.items():
            prev = 0.0
            for k in (1, 2, 3, 4):
                if q.get(k) is not None:
                    out[_period_end({1: "Q1", 2: "H1", 3: "Q3", 4: "FY"}[k], y)] = q[k] - prev
                    prev = q[k]
    return out


def _period_end(kind: str, year: int) -> date:
    return {"Q1": date(year, 3, 31), "H1": date(year, 6, 30), "Q3": date(year, 9, 30),
            "FY": date(year, 12, 31), "Q2": date(year, 6, 30), "Q4": date(year, 12, 31)}[kind]


# ---- currency + PIT (frozen {FQ} rules, imported) ----

def dividends_with_meta(payouts, withheld=frozenset(), fyx=None, yahoo=None):
    """(t, period_end) -> {payout_idr, deadline, withheld}. USD tickers convert at the period-end month rate."""
    fyx, yahoo = fyx or {}, yahoo if yahoo is not None else fq.load_yahoo()
    ccy = _ticker_currency()
    out = {}
    for (t, pe_s), v in payouts.items():
        pe = date.fromisoformat(pe_s)
        c = ccy.get(t)
        rate = 1.0 if c == "IDR" else (yahoo.get((pe.year, pe.month)) if c == "USD" else None)
        if rate is None:
            continue
        out[(t, pe_s)] = {"payout_idr": v * rate, "ccy": c, "rate": rate,
                          "deadline": fq.deadline_for(pe, fyx.get(t)),
                          "withheld": (t, pe) in withheld}
    return out


_CURRENCY_CACHE: dict[str, str | None] = {}


def _ticker_currency(db=FIN_DB) -> dict[str, str | None]:
    """Ticker -> 'IDR'|'USD'|None via the {FQ} magnitude rule (statement vs vendor-derived equity)."""
    if _CURRENCY_CACHE:
        return _CURRENCY_CACHE
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    def rm(cond):
        return {t: ro for t, ro in con.execute(
            f"select ticker, min(row_order) from fin_rows where statement='balance' and {cond} group by ticker")}
    eq_s, eq_q = rm("account_en like 'Total Ekuitas%'"), rm("account_en='Total Equity (Quarter)'")
    def val(t, ro):
        r = con.execute("select value from fin_values where ticker=? and statement='balance' and row_order=? "
                        "and value is not null limit 1", (t, ro)).fetchone()
        return r[0] if r else None
    out: dict[str, str | None] = {}
    for t in set(eq_s) | set(eq_q):
        a, b = (val(t, eq_s[t]) if t in eq_s else None), (val(t, eq_q[t]) if t in eq_q else None)
        out[t] = fq.classify_currency(a, b)
    con.close()
    _CURRENCY_CACHE.update(out)
    return _CURRENCY_CACHE


# ---- TTM + coverage ----

def build_ttm(meta: dict) -> dict[str, list[tuple[date, float, date | None, bool]]]:
    """ticker -> [(period_end, quarterly_payout_idr, deadline, withheld)], quarterly-differenced, sorted.

    Quarterly payouts come from the per-ticker layout classification (DISCRETE values as-is; CUMULATIVE
    first-differenced); UNKNOWN layouts keep only FY entries as their annual flow."""
    per_ticker: dict[str, dict[str, float]] = {}
    for (t, pe_s), m in meta.items():
        per_ticker.setdefault(t, {})[_period_label_of(pe_s)] = m["payout_idr"]
    out: dict[str, list[tuple[date, float, date | None, bool]]] = {}
    for t, periods in per_ticker.items():
        layout = classify_layout(periods)
        q = quarterly_series(periods, layout) if layout != "UNKNOWN" else {
            _period_end("FY", int(k.split()[-1])): abs(v) for k, v in periods.items() if k.startswith("FY")}
        items = []
        for pe, v in q.items():
            m = meta.get((t, pe.isoformat()))
            if m:
                items.append((pe, v, m["deadline"], m["withheld"]))
        items.sort()
        out[t] = items
    return out


def ttm_at(series: list[tuple[date, float, date | None, bool]], t: date,
           stale_days: int = 456) -> float | None:
    """Trailing payout: sum over the four fiscal periods with period_end within 12m of the NEWEST
    period whose D-111 deadline <= t (anchored on disclosure, not on t -- annual payers keep a
    valid rate during filing-lag months). None if nothing available or the newest period is
    staler than stale_days (15 months)."""
    ok = [(pe, v) for pe, v, dl, wh in series if not wh and dl is not None and dl <= t]
    if not ok:
        return None
    newest = max(pe for pe, _ in ok)
    if (t - newest).days > stale_days:
        return None
    lo = date(newest.year - 1, newest.month, newest.day)   # strict: excludes the year-before period
    return sum(v for pe, v in ok if lo < pe <= newest)


def main(argv=None) -> int:
    mode = (argv or sys.argv[1:])[0] if (argv or sys.argv[1:]) else ""
    withheld = fq.load_withheld()
    fyx = fq.load_fyx()
    con = sqlite3.connect(f"file:{FIN_DB}?mode=ro", uri=True)
    payouts = sum_paid_rows(con, row_labels(con))
    con.close()
    meta = dividends_with_meta(payouts, withheld, fyx)

    if mode == "extract":
        per_ticker: dict[str, dict[str, float]] = {}
        for (t, pe_s), v in payouts.items():
            per_ticker.setdefault(t, {})[_period_label_of(pe_s)] = v
        with open(OUT_Q, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["ticker", "period_end", "period_label", "layout", "quarterly_payout_idr",
                        "ccy", "deadline", "withheld"])
            for t, periods in sorted(per_ticker.items()):
                layout = classify_layout(periods)
                q = quarterly_series(periods, layout)
                for pe in sorted(q):
                    m = meta.get((t, pe.isoformat()), {})
                    w.writerow([t, pe.isoformat(), _label_at(periods, pe), layout,
                                round(q[pe], 0), m.get("ccy", ""), m.get("deadline", ""), m.get("withheld", "")])
        print(f"extract: {OUT_Q.name} rows={sum(len(v) for v in per_ticker.values())} "
              f"tickers={len(per_ticker)} layouts=D/C/U "
              f"{sum(classify_layout(p)=='DISCRETE' for p in per_ticker.values())}/"
              f"{sum(classify_layout(p)=='CUMULATIVE' for p in per_ticker.values())}/"
              f"{sum(classify_layout(p)=='UNKNOWN' for p in per_ticker.values())}")
        return 0

    if mode == "coverage":
        ksei = fq.load_ksei()
        months = sorted(ksei)
        # panel per month: top-200 KSEI mcap, stale filter (D-112 rule)
        panel: dict[date, set[str]] = {}
        for i, d in enumerate(months):
            if i < 2:
                continue
            m1, m2 = months[i - 1], months[i - 2]
            rows = []
            for t, (sec, px) in ksei[d].items():
                if not fq.TICKER_RE.match(t) or not sec or not px or px <= 0:
                    continue
                p1 = ksei[m1].get(t, (None, None))[1]
                p2 = ksei[m2].get(t, (None, None))[1]
                if p1 is not None and p2 is not None and px == p1 == p2:
                    continue
                rows.append((t, sec * px))
            rows.sort(key=lambda x: -x[1])
            panel[d] = {t for t, _ in rows[: fq.TOP_N]}
        series = build_ttm(meta)
        by_year: dict[int, list[int]] = {}
        for d, names in panel.items():
            have = sum(1 for t in names if ttm_at(series.get(t, []), d) is not None)
            by_year.setdefault(d.year, []).append((1, len(names), have))
        with open(OUT_COV, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["year", "panel_name_months", "with_pit_ttm", "coverage_pct"])
            for y in sorted(by_year):
                nm = sum(x[1] for x in by_year[y])
                hv = sum(x[2] for x in by_year[y])
                w.writerow([y, nm, hv, round(100 * hv / nm, 1) if nm else None])
                print(f"{y}: {hv}/{nm} = {100 * hv / nm:.1f}%" if nm else f"{y}: -")
        tot_nm = sum(len(v) for v in panel.values())
        tot_hv = sum(1 for d, names in panel.items() for t in names
                     if ttm_at(series.get(t, []), d) is not None)
        print(f"TOTAL: {tot_hv}/{tot_nm} = {100 * tot_hv / tot_nm:.1f}%")
        return 0

    print(__doc__)
    return 1


def _period_label_of(pe_s: str) -> str:
    """period_end iso -> 'KIND YEAR' label (Q1/H1/Q3/FY by month)."""
    d = date.fromisoformat(pe_s)
    return f"{ {3: 'Q1', 6: 'H1', 9: 'Q3', 12: 'FY'}.get(d.month, '?') } {d.year}"


def _label_at(periods: dict, pe: date) -> str:
    return {3: "Q1", 6: "H1", 9: "Q3", 12: "FY"}.get(pe.month, "?")


if __name__ == "__main__":
    sys.exit(main())
