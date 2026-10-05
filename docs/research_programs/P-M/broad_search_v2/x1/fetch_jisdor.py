"""JISDOR acquisition -- brief P0-B: "Add BI's JISDOR only if it can be downloaded
publicly without auth".

Verified 2026-10-05 (source-probe): Bank Indonesia's JISDOR page offers an official
Download (XLSX) postback that works with a plain browser User-Agent, no login, no
CAPTCHA:
  GET  https://www.bi.go.id/en/statistik/informasi-kurs/jisdor/Default.aspx  -> 200
  POST same URL with the page's own ASP.NET tokens (__VIEWSTATE,
       __VIEWSTATEGENERATOR, __EVENTVALIDATION, __REQUESTDIGEST) + date range
       (dd/mm/yyyy) + ButtonExport=Download -> XLSX (Date | Exchange Rates).
Coverage pulled in the probe: 2013-05-20 .. 2026-10-02 (JISDOR starts 2013-05-20;
JISDOR predates the discovery split only from 2013, disclosed in PHASE0_COUNTS).

No SOAP/JSON archive endpoint exists (documented dead ends: .json is a SharePoint
error page; wskursbi.asmx GET returns only the latest 14 rows; SOAP POST is WAF-
blocked). This script uses only http/https to the public www.bi.go.id host.

Run from WSL:  ~/venv-x/bin/python fetch_jisdor.py
Writes data/jisdor.csv and merges its sha256/rows/range into MANIFEST.json.
"""
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
URL = "https://www.bi.go.id/en/statistik/informasi-kurs/jisdor/Default.aspx"
UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")}
# host allow-list per the standing request-safety rule
assert re.match(r"^https://www\.bi\.go\.id(/|$)", URL)


def sha256_of(p: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    s = requests.Session()
    s.headers.update(UA)
    r = s.get(URL, timeout=60)
    r.raise_for_status()
    page = r.text
    tok = {}
    for name in ("__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION",
                 "__REQUESTDIGEST"):
        m = (re.search(r'name="' + re.escape(name) + r'"[^>]*value="([^"]*)"', page)
             or re.search(r'id="' + re.escape(name) + r'"[^>]*value="([^"]*)"', page))
        if not m:
            raise RuntimeError(f"missing ASP.NET token {name}")
        tok[name] = m.group(1)
    gen = re.search(r'name="(ctl00\$ctl\d+\$g_[0-9a-f_]+\$ctl00)\$TextBoxFrom"', page)
    if not gen:
        raise RuntimeError("JISDOR form prefix not found on page")
    pfx = gen.group(1)                           # e.g. ctl00$ctl54$g_xxx$ctl00
    form = {
        "__VIEWSTATE": tok["__VIEWSTATE"],
        "__VIEWSTATEGENERATOR": tok["__VIEWSTATEGENERATOR"],
        "__EVENTVALIDATION": tok["__EVENTVALIDATION"],
        "__REQUESTDIGEST": tok["__REQUESTDIGEST"],
        f"{pfx}TextBoxFrom": "01/01/2013",
        f"{pfx}TextBoxDateTo": datetime.now().strftime("%d/%m/%Y"),
        f"{pfx}ButtonExport": "Download",
        f"{pfx}hdnStatusJisdorExport": "true",
    }
    # FULL postback (no X-MicrosoftAjax / __ASYNCPOST): the async delta frame does
    # not carry the file; the server responds to a full postback with the XLSX.
    h2 = dict(UA)
    h2.update({"Content-Type": "application/x-www-form-urlencoded"})
    r2 = s.post(URL, data=form, headers=h2, timeout=120)
    ct = r2.headers.get("Content-Type", "")
    if "spreadsheetml" not in ct:
        raise RuntimeError(f"export did not return XLSX (Content-Type={ct!r}, "
                           f"status={r2.status_code}, bytes={len(r2.content)}, "
                           f"head={r2.content[:300]!r})")
    xl = pd.read_excel(io.BytesIO(r2.content))   # columns: NO, Date, Exchange Rates
    xl.columns = [str(c).strip().lower() for c in xl.columns]
    dcol = "date" if "date" in xl.columns else xl.columns[1]
    vcol = "exchange rates" if "exchange rates" in xl.columns else xl.columns[-1]
    df = pd.DataFrame({
        "date": pd.to_datetime(xl[dcol], errors="coerce").dt.strftime("%Y-%m-%d"),
        "jisdor": pd.to_numeric(xl[vcol], errors="coerce"),
    }).dropna().sort_values("date").reset_index(drop=True)
    DATA.mkdir(exist_ok=True)
    p = DATA / "jisdor.csv"
    df.to_csv(p, index=False)

    man_p = HERE / "MANIFEST.json"
    man = json.loads(man_p.read_text())
    man["files"]["jisdor.csv"] = {
        "ticker": "JISDOR", "note": ("BI official USD/IDR reference fixing (starts 2013-05-20); "
                                     "public XLSX export of the JISDOR page, no auth "
                                     "(fetch_jisdor.py); PIT-authoritative FX where available"),
        "auto_adjust": False, "rows": int(len(df)),
        "start": str(df["date"].min()), "end": str(df["date"].max()),
        "sha256": sha256_of(p), "source_url": URL,
    }
    man["generated_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    man["notes"].append("jisdor.csv added 2026-10-05 after the public-download probe "
                        "verified no-auth access (brief P0-B conditional satisfied).")
    man_p.write_text(json.dumps(man, indent=1))
    print(f"jisdor rows={len(df)} {df['date'].min()}..{df['date'].max()}")
    print(df.tail(3).to_string(index=False))
    print("WROTE", p)


if __name__ == "__main__":
    main()
