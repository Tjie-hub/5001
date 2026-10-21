#!/usr/bin/env python3
"""Probe: does Stockbit serve *historical* quarterly financials behind our existing token?

Question it answers (STATUS_2026-10-20 / edge-exhaustion review): is there a cheap point-in-time
fundamentals source for the {FQ} value/quality lane, with period history and ideally publication dates,
including delisted names? The 08:50 job only stores today's keystats snapshot, and the month-end
fq_snapshot only builds history forward.

READ-ONLY by design:
  * reads .stockbit_token; never logs in, never calls auto_token, never refreshes the token;
  * never opens the database; writes only under out/ (gitignored);
  * a bounded number of GETs (candidates are tried on BBCA first; only endpoints that answer 200
    are repeated on the other tickers), RATE_DELAY seconds apart;
  * refuses to run on weekdays 08:30-17:40 WIB (token refresh, OHLCV, EOD 16:15, 17:30 retry)
    unless --force.

The candidate endpoint paths are UNVERIFIED guesses at the Stockbit web app's financials API.
If none answers, the fallback is a 2-minute manual capture: open stockbit.com -> a stock ->
Financials tab, DevTools -> Network, copy the request URL of the financial table, then rerun:
    venv/bin/python3 scripts/probe_stockbit_fin_history.py --url '<url with BBCA replaced by {ticker}>'

Usage:
    venv/bin/python3 scripts/probe_stockbit_fin_history.py              # default run
    venv/bin/python3 scripts/probe_stockbit_fin_history.py --dry-run    # list planned calls only
    ... --tickers BBCA ASII BTEL     ... --url '/some/path?symbol={ticker}'   ... --force

Exit codes: 0 HISTORY_FOUND, 1 SNAPSHOT_ONLY / NO_ENDPOINT, 2 refused / token problem.
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.join(REPO, ".stockbit_token")
BASE = "https://exodus.stockbit.com"
WIB = timezone(timedelta(hours=7))
RATE_DELAY = 1.5
MAX_SAVE_BYTES = 5_000_000

# BBCA/TLKM: long-listed large caps. BTEL/TRAM: names yfinance reported as "possibly delisted"
# in app.log on 2026-10-20 -- a cheap test of whether Stockbit keeps history for delisted names.
DEFAULT_TICKERS = ["BBCA", "TLKM", "BTEL", "TRAM"]

# (name, path template). UNVERIFIED guesses; see the module docstring.
CANDIDATES = [
    ("fin_income_q", "/findata-view/company/financial?symbol={ticker}&data_type=1&report_type=1&statement_type=1"),
    ("fin_income_a", "/findata-view/company/financial?symbol={ticker}&data_type=1&report_type=1&statement_type=2"),
    ("fin_balance_q", "/findata-view/company/financial?symbol={ticker}&data_type=1&report_type=2&statement_type=1"),
    ("fin_cashflow_q", "/findata-view/company/financial?symbol={ticker}&data_type=1&report_type=3&statement_type=1"),
    ("ratio_history", "/keystats/ratio/v1/{ticker}?year_limit=10"),
]

QUARTER_RE = re.compile(r"\bQ([1-4])\s?['’]?\s?((?:19|20)?\d{2})\b", re.I)
PERIOD_RE = re.compile(r"\b(\d{1,2}M|FY|TTM|H[12])\s?((?:19|20)\d{2})\b", re.I)
YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")
DATE_RE = re.compile(r"\b((?:19|20)\d{2}-\d{2}-\d{2})\b")
DATE_KEY_RE = re.compile(r"(date|publish|release|announc|filing|report_?time|submitted|period)", re.I)
TH_RE = re.compile(r"<th[^>]*>(.*?)</th>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")


def log(msg: str) -> None:
    print(msg, flush=True)


# ---------------------------------------------------------------- guards

def read_token() -> str:
    try:
        with open(TOKEN_FILE, encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError as exc:
        raise SystemExit(f"REFUSED: cannot read {TOKEN_FILE}: {exc.strerror}")


def token_expiry(token: str) -> datetime | None:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        exp = json.loads(base64.urlsafe_b64decode(payload)).get("exp")
        return datetime.fromtimestamp(int(exp), tz=timezone.utc) if exp else None
    except Exception:
        return None


def in_blackout(now_wib: datetime) -> bool:
    if now_wib.weekday() >= 5:
        return False
    hm = now_wib.hour * 60 + now_wib.minute
    return 8 * 60 + 30 <= hm < 17 * 60 + 40


# ---------------------------------------------------------------- analysis

def _walk(obj, path=""):
    """Yield (key_path, value) for every leaf, and (key_path, None) for every dict key."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else str(k)
            yield p, None
            yield from _walk(v, p)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:5000]):
            yield from _walk(v, f"{path}[]")
    else:
        yield path, obj


def _norm_year(y: str) -> int:
    y = int(y)
    return y + 2000 if y < 100 else y


def analyse(payload) -> dict:
    quarters, periods, years, dates = set(), set(), set(), set()
    date_keys: dict[str, list] = {}
    table_headers: list[str] = []
    n_tables = 0
    texts = []
    for key_path, value in _walk(payload):
        leaf = key_path.split(".")[-1].replace("[]", "")
        if value is None:
            texts.append(leaf)
            continue
        if DATE_KEY_RE.search(leaf):
            samples = date_keys.setdefault(key_path, [])
            if len(samples) < 3 and str(value) not in samples:
                samples.append(str(value)[:40])
        if isinstance(value, str):
            if "<table" in value.lower():
                n_tables += 1
                heads = [html.unescape(TAG_RE.sub("", h)).strip() for h in TH_RE.findall(value)]
                table_headers.extend(h for h in heads if h)
                texts.append(html.unescape(TAG_RE.sub(" ", value)))
            else:
                texts.append(value)
    blob = " ".join(texts)
    for q, y in QUARTER_RE.findall(blob):
        quarters.add((_norm_year(y), int(q)))
    for p, y in PERIOD_RE.findall(blob):
        periods.add(f"{p.upper()} {y}")
    for y in YEAR_RE.findall(blob):
        years.add(int(y))
    for d in DATE_RE.findall(blob):
        dates.add(d)
    q_sorted = sorted(quarters)
    period_years = sorted({y for y, _ in quarters} | {int(p.split()[-1]) for p in periods})
    history = len(quarters) >= 8 or len(period_years) >= 5
    return {
        "history": history,
        "n_quarters": len(quarters),
        "earliest_quarter": f"Q{q_sorted[0][1]} {q_sorted[0][0]}" if q_sorted else None,
        "latest_quarter": f"Q{q_sorted[-1][1]} {q_sorted[-1][0]}" if q_sorted else None,
        "period_labels_sample": sorted(periods)[:12],
        "period_years": period_years,
        "all_years_span": [min(years), max(years)] if years else None,
        "iso_dates_sample": sorted(dates)[:10],
        "n_iso_dates": len(dates),
        "date_like_keys": dict(list(date_keys.items())[:15]),
        "html_tables": n_tables,
        "table_headers_sample": table_headers[:20],
        "top_level_keys": sorted(payload.keys())[:20] if isinstance(payload, dict) else type(payload).__name__,
    }


# ---------------------------------------------------------------- network

def fetch(session, token: str, url: str):
    import requests  # local import so --dry-run works without the venv

    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Origin": "https://stockbit.com",
        "Referer": "https://stockbit.com/",
        "Accept": "application/json",
    }
    try:
        r = session.get(url, headers=headers, timeout=20)
    except requests.RequestException as exc:
        return None, None, f"{type(exc).__name__}: {str(exc).replace(token, '<token>')[:160]}"
    try:
        body = r.json()
    except ValueError:
        body = None
    return r.status_code, body, (r.text[:160].replace(token, "<token>") if body is None else "")


def build_url(template: str, ticker: str) -> str:
    path = template.replace("{ticker}", ticker)
    return path if path.startswith("http") else BASE + path


# ---------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tickers", nargs="+", default=DEFAULT_TICKERS)
    ap.add_argument("--url", action="append", default=[], help="extra endpoint template with {ticker}")
    ap.add_argument("--force", action="store_true", help="ignore the 08:30-17:40 WIB weekday guard")
    ap.add_argument("--dry-run", action="store_true", help="print planned calls; no network, no files")
    args = ap.parse_args(argv)

    tickers = [t.upper() for t in args.tickers]
    candidates = list(CANDIDATES) + [(f"custom{i + 1}", u) for i, u in enumerate(args.url)]
    now = datetime.now(WIB)

    if args.dry_run:
        log(f"DRY RUN {now:%Y-%m-%d %H:%M} WIB; blackout now: {in_blackout(now)}")
        log(f"baseline: {build_url('/keystats/{ticker}', tickers[0])}")
        for name, tpl in candidates:
            log(f"  {name:15s} {build_url(tpl, tickers[0])}")
        log(f"then only 200-answering endpoints on: {', '.join(tickers[1:])}")
        return 0

    if in_blackout(now) and not args.force:
        log(f"REFUSED: {now:%a %H:%M} WIB is inside the weekday 08:30-17:40 guard "
            "(token refresh / OHLCV / EOD 16:15 / 17:30 retry). Run after 17:40, or pass --force.")
        return 2

    token = read_token()
    exp = token_expiry(token)
    if exp is not None and exp <= datetime.now(timezone.utc):
        log(f"REFUSED: token expired at {exp.astimezone(WIB):%Y-%m-%d %H:%M} WIB. Do NOT log in "
            "by hand during trading hours; the 08:40 weekday (21:40 Sat/Sun) refresh renews it.")
        return 2

    import requests

    stamp = now.strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(REPO, "out", f"stockbit_fin_probe_{stamp}")
    os.makedirs(out_dir, exist_ok=True)
    session = requests.Session()
    results = []

    def call(name: str, ticker: str, url: str) -> dict:
        status, body, note = fetch(session, token, url)
        row = {"endpoint": name, "ticker": ticker, "url": url, "status": status, "note": note}
        if status == 200 and body is not None:
            raw = json.dumps(body, ensure_ascii=False)
            if len(raw) <= MAX_SAVE_BYTES:
                with open(os.path.join(out_dir, f"{ticker}__{name}.json"), "w", encoding="utf-8") as fh:
                    fh.write(raw)
            row["bytes"] = len(raw)
            row["analysis"] = analyse(body)
        results.append(row)
        a = row.get("analysis") or {}
        log(f"  {ticker:5s} {name:15s} -> {status}"
            + (f"  history={a.get('history')} quarters={a.get('n_quarters')} "
               f"earliest={a.get('earliest_quarter')} tables={a.get('html_tables')}" if a else
               (f"  {note}" if note else "")))
        time.sleep(RATE_DELAY)
        return row

    log(f"Stockbit financials-history probe {now:%Y-%m-%d %H:%M} WIB -> {out_dir}")
    base = call("keystats", tickers[0], build_url("/keystats/{ticker}", tickers[0]))
    if base["status"] in (401, 403):
        log("STOP: token rejected (401/403). Do not re-login now; the next scheduled refresh renews it.")
        verdict, code = "NO_ACCESS", 2
    elif base["status"] != 200:
        log(f"STOP: baseline keystats answered {base['status']}; not probing further.")
        verdict, code = "NO_ACCESS", 2
    else:
        live = []
        for name, tpl in candidates:
            row = call(name, tickers[0], build_url(tpl, tickers[0]))
            if row["status"] == 200:
                live.append((name, tpl))
        for ticker in tickers[1:]:
            for name, tpl in live:
                call(name, ticker, build_url(tpl, ticker))

        hist = [r for r in results if (r.get("analysis") or {}).get("history")]
        if hist:
            best = max(hist, key=lambda r: r["analysis"]["n_quarters"])
            a = best["analysis"]
            date_keys = sorted({k.split(".")[-1].replace("[]", "") for k in a["date_like_keys"]})[:6]
            delisted = {r["ticker"]: (r["status"], (r.get("analysis") or {}).get("n_quarters"))
                        for r in results if r["ticker"] in ("BTEL", "TRAM") and r["endpoint"] == best["endpoint"]}
            verdict, code = "HISTORY_FOUND", 0
            log(f"\nVERDICT: HISTORY_FOUND via {best['endpoint']} ({best['ticker']}): {a['n_quarters']} quarters, "
                f"{a['earliest_quarter']} .. {a['latest_quarter']}; date-like keys: {date_keys or 'none'}; "
                f"delisted test: {delisted or 'not reached'}")
            log("Next: check the date-like fields in summary.json -- period labels alone mean the statutory-lag "
                "PIT design (06_PIT_FUNDAMENTALS_FEASIBILITY); real publication dates mean true PIT.")
        else:
            any_live = [r for r in results if r["status"] == 200 and r["endpoint"] != "keystats"]
            verdict, code = ("SNAPSHOT_ONLY" if any_live else "NO_ENDPOINT"), 1
            log(f"\nVERDICT: {verdict}. None of the guessed endpoints returned period history.")
            log("Next: 2-minute DevTools capture of the Financials-tab request on stockbit.com, then rerun with "
                "--url '<that URL with the ticker replaced by {ticker}>'.")

    summary = {"run_at_wib": now.isoformat(), "verdict": verdict, "tickers": tickers,
               "candidates": [c[0] for c in candidates], "results": results}
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)
    log(f"summary: {os.path.join(out_dir, 'summary.json')}")
    return code


if __name__ == "__main__":
    sys.exit(main())
