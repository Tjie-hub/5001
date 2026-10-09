"""Parse KSEI monthly Balancepos files into one long CSV of equity holdings by investor type.

Source: https://web.ksei.co.id/archive_download/holding_composition (public, monthly).
Columns per row: date, ticker, sec_num (listed shares), price, then share counts for
local/foreign x {IS insurance, CP corporate, PF pension, IB financial inst, ID individual,
MF mutual fund, SC securities co, FD foundation, OT other}.
PIT note: a month-end file is published after month end (the 2026-09-30 zip is stamped
2026-10-01 06:00), so research must treat it as known from the next session at the earliest.
"""
import csv
import io
import sys
import zipfile
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
TYPES = ["IS", "CP", "PF", "IB", "ID", "MF", "SC", "FD", "OT"]
OUTCOLS = ["date", "ticker", "sec_num", "price"] + [f"L_{t}" for t in TYPES] + ["L_total"] \
    + [f"F_{t}" for t in TYPES] + ["F_total", "file", "zip_stamp"]


def rows(zpath):
    with zipfile.ZipFile(zpath) as z:
        for info in z.infolist():
            stamp = datetime(*info.date_time).isoformat()
            text = z.read(info).decode("latin-1")
            for r in csv.reader(io.StringIO(text), delimiter="|"):
                if len(r) < 25 or r[0] == "Date" or r[2].strip().upper() != "EQUITY":
                    continue
                d = datetime.strptime(r[0].strip().title(), "%d-%b-%Y").date().isoformat()
                nums = [x.strip().replace(",", "") or "0" for x in r[3:25]]
                yield [d, r[1].strip()] + nums + [zpath.name, stamp]


def main():
    out = HERE / "ksei_equity_holdings.csv"
    n = 0
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(OUTCOLS)
        for z in sorted(HERE.glob("BalanceposEfek*.zip")):
            for r in rows(z):
                w.writerow(r)
                n += 1
    print(f"{out.name}: {n} rows")


if __name__ == "__main__":
    sys.exit(main())
