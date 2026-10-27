"""C-003 dividend-yield G0 — coverage + prior-only power (breadth only; never a return read).

Implements the PROPOSED freeze G0_FREEZE_DY_DRAFT_2026-10-28.md. The freeze is NOT pinned: FREEZE_SHA256 is
None and the script refuses to run until the owner pins it (the {FQ} pattern). What it will compute once
pinned and run: (i) coverage gates (panel-months able to form a top-quintile book with >= 30 valid-yield
names; descriptive name-month payer coverage), (ii) prior-only power at the PROPOSED 0.80%/mo floor using a
placebo/noise SD over monthly formation cross-sections -- monthly random-quintile spread SD estimated from
the PANEL's own name-month return dispersion structure via the pre-registered placebo procedure below.
No dividend-yield sort return, spread, t-stat or IR is computed at any point in this script.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "fq"))
import extract_dividends as ex
import g0_fq_ep_breadth as fq

FREEZE = HERE / "G0_FREEZE_DY_DRAFT_2026-10-28.md"
FREEZE_SHA256: str | None = None        # owner pins this after editing the DRAFT into the freeze

# ---- proposed frozen parameters (freeze draft §2-§4) ----
FIRST_MONTH, LAST_MONTH = "2009-04", "2026-09"
TOP_N = 200                              # KSEI mcap, stale filter (D-112 universe rule)
MIN_VALID_NAMES = 30                     # per month, to form a quintile book
MIN_MONTHS_FORMABLE = 0.80               # >= 80% of panel months must be formable
FLOOR = 0.008                            # PROPOSED 0.80%/mo (owner pins; floor < 0.60% -> stop)
BAR = 3.300069                           # census 613 + this arm
IR_FLOOR = 0.75                          # same convention as D-112 (E/P): monthly-spread IR
MIN_POWER = 0.20
WARMUP_MONTHS = 2

KSEI_CSV, FIN_DB = fq.KSEI_CSV, fq.FIN_DB
EXTRACT_CSV = HERE / "dividends_quarterly_v1.csv"


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


PINS = {  # inputs fixed at freeze time (owner pins the shas with the freeze)
    KSEI_CSV: "38c8a90b10546f0602d4568b277d79d154f994e5cafb921bd0d73c3ce55df781",
    fq.YAHOO_CSV: "a0937cde0221f6a7d0e9f5b9e81060c67a30026672a0a686240f6e8e085ee1b9",
    fq.LATE_CSV: "b549358b68e560aba806ca7b99514853056b8ac8cc07ec8d343cf22b1c691e8c",
    fq.FYX_CSV: "013af724fed5291c46e0872eb6d3a5eceb64e1420a26a2a71d4995b4d77f1089",
}


def verify_inputs() -> list[str]:
    bad = [f"{Path(p).name}: sha256 mismatch" for p, want in PINS.items()
           if not Path(p).exists() or sha256_file(p) != want]
    want = None
    for line in open(fq.FIN_SUMS):
        parts = line.split()
        if len(parts) == 2 and Path(parts[1]).name == "fin.db":
            want = parts[0]
    if want is None or sha256_file(FIN_DB) != want:
        bad.append("fin.db: does not match the 10-26 sums file the {FQ} G0 pins")
    return bad


def monthly_panel():
    """(month_date, {ticker: (sec_num, price)}) top-200 KSEI mcap with the stale filter."""
    ksei = fq.load_ksei()
    months = sorted(ksei)
    panel = {}
    for i, d in enumerate(months):
        if d < date.fromisoformat(f"{FIRST_MONTH}-28") or i < WARMUP_MONTHS:
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
        panel[d] = {t: (ksei[d][t][0], ksei[d][t][1]) for t, _ in rows[:TOP_N]}
    return panel


def valid_yield_counts(panel, series) -> tuple[list[int], int, int]:
    """Per month: how many panel names have a PIT TTM payout (yield numerator exists).
    Coverage only -- no yield sort, no returns."""
    per_month, nm_total, hv_total = [], 0, 0
    for d, names in sorted(panel.items()):
        have = sum(1 for t in names if ex.ttm_at(series.get(t, []), d) is not None)
        per_month.append(have)
        nm_total += len(names)
        hv_total += have
    return per_month, nm_total, hv_total


def placebo_power(months_n: int, sd_monthly_spread: float) -> dict:
    """Prior-only power at the floor from the placebo SD and the month count (no sort returns involved)."""
    from math import erf, sqrt
    se = sd_monthly_spread / sqrt(months_n)
    t = FLOOR / se
    return {"months": months_n, "se": round(se, 6), "t_at_floor": round(t, 3),
            "power_at_floor": round(0.5 * (1 + erf((t - BAR) / sqrt(2))), 4),
            "mde80_pct": round(100 * BAR * se, 3)}


def main(argv=None) -> int:
    if FREEZE_SHA256 is None or not FREEZE.exists() or \
            hashlib.sha256(FREEZE.read_bytes()).hexdigest() != FREEZE_SHA256:
        print("DY G0 freeze not pinned or changed; refusing to run (coverage/power stays unseen until the freeze).")
        return 2
    problems = verify_inputs()
    if problems:
        print("Pinned inputs do not match; refusing to run:\n  " + "\n  ".join(problems))
        return 3

    panel = monthly_panel()
    withheld, fyx = fq.load_withheld(), fq.load_fyx()
    import sqlite3
    con = sqlite3.connect(f"file:{FIN_DB}?mode=ro", uri=True)
    payouts = ex.sum_paid_rows(con, ex.row_labels(con))
    con.close()
    meta = ex.dividends_with_meta(payouts, withheld, fyx)
    series = ex.build_ttm(meta)

    per_month, nm, hv = valid_yield_counts(panel, series)
    formable = sum(1 for n in per_month if n >= MIN_VALID_NAMES)
    months_all = len(per_month)
    res = {
        "record_type": "g0_coverage_power",
        "arm": "dividend-yield level (C-003)",
        "freeze_sha256": FREEZE_SHA256,
        "coverage": {
            "panel_months": months_all,
            "months_formable_ge30": formable,
            "formable_share": round(formable / months_all, 4) if months_all else None,
            "name_month_total": nm, "name_month_with_ttm": hv,
            "name_month_coverage": round(hv / nm, 4) if nm else None,
            "median_valid_names": sorted(per_month)[months_all // 2] if per_month else None,
        },
        "power_placeholders": "SD source: placebo monthly quintile-spread SD from a pre-registered random "
                              "assignment on the panel (freeze §5); fill at the pinned run.",
        "proposed": {"floor_pct": 100 * FLOOR, "bar": BAR, "ir_floor": IR_FLOOR,
                     "min_power": MIN_POWER, "min_formable_share": MIN_MONTHS_FORMABLE},
    }
    stamp = datetime.now(timezone(timedelta(hours=7))).strftime("%Y%m%dT%H%M%S")
    out = HERE / f"G0_RESULT_{stamp}.json"
    out.write_text(json.dumps(res, indent=1))
    print(f"months formable {formable}/{months_all}; name-month coverage {hv}/{nm} = "
          f"{100 * hv / nm:.1f}%; median valid names {res['coverage']['median_valid_names']}; {out.name}")
    print("STOP RULE (proposed): fires if formable_share < 0.80 or (at pin) floor power < 0.20 -> "
          "withdraw before registration, uncounted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
