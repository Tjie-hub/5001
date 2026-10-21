#!/usr/bin/env python3
"""Stockbit quarterly financial statements backfill for the {FQ} value/quality lane (research-side).

Follows docs/research_programs/P-M/data_acquisition/10_STOCKBIT_FIN_HISTORY_PROBE_2026-10-20.md.

Two subcommands:
  fetch  -- for every ticker (live DB + pre-2021 history, delisted included), download the quarterly
            income statement, balance sheet and cash flow (3 GETs per ticker) as raw .json.gz plus a
            manifest line. Resumable: files already on disk are skipped.
  parse  -- offline: turn every raw file into one long SQLite table (no network).

Safety (same discipline as probe_stockbit_fin_history.py):
  * reads .stockbit_token only; never logs in, never calls auto_token, never refreshes the token;
  * opens the production DB read-only and only to list tickers; writes only under OUT_DIR;
  * RATE_DELAY between GETs; stops at once on 401/403 (no re-login); backs off on 429, then stops;
  * refuses weekdays 08:30-19:00 WIB (market, EOD, evening jobs) and 21:50-23:30 every day (jurnal26's
    nightly tape backfill shares the token), unless --force; stops before the token expires and at
    --max-minutes, so a run can be split over several sessions.

Usage (best: Sunday daytime, when the Saturday 21:40 token is valid and nothing else runs):
    cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
    venv/bin/python3 scripts/stockbit_fin_backfill.py fetch --dry-run      # universe + plan, no network
    venv/bin/python3 scripts/stockbit_fin_backfill.py fetch                # the pull (resumable)
    venv/bin/python3 scripts/stockbit_fin_backfill.py parse                # build fin.db from raw files
Options (fetch): --tickers A B C, --limit N (pilot), --max-minutes M (default 170), --force.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import html
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOKEN_FILE = REPO / ".stockbit_token"
LIVE_DB = REPO / "data" / "walkforward.db"
OUT_DIR = Path.home() / "idx_external" / "stockbit_fin"
BASE = "https://exodus.stockbit.com"
WIB = timezone(timedelta(hours=7))
RATE_DELAY = 1.5
STATEMENTS = {"income": 1, "balance": 2, "cashflow": 3}
URL_TMPL = "/findata-view/company/financial?symbol={t}&data_type=1&report_type={r}&statement_type=1"
TICKER_RE = re.compile(r"^[A-Z]{4}$")


def log(msg: str) -> None:
    print(f"[{datetime.now(WIB):%H:%M:%S}] {msg}", flush=True)


# ---------------------------------------------------------------- guards

def read_token() -> str:
    return TOKEN_FILE.read_text(encoding="utf-8").strip()


def token_expiry(token: str) -> datetime | None:
    try:
        p = token.split(".")[1]
        p += "=" * (-len(p) % 4)
        exp = json.loads(base64.urlsafe_b64decode(p)).get("exp")
        return datetime.fromtimestamp(int(exp), tz=timezone.utc) if exp else None
    except Exception:
        return None


def blocked(now: datetime) -> str | None:
    hm = now.hour * 60 + now.minute
    if now.weekday() < 5 and 8 * 60 + 30 <= hm < 19 * 60:
        return "weekday 08:30-19:00 WIB (market / EOD / evening jobs)"
    if 21 * 60 + 50 <= hm < 23 * 60 + 30:
        return "21:50-23:30 WIB (jurnal26 nightly tape backfill uses the same token)"
    return None


# ---------------------------------------------------------------- universe

def universe() -> list[str]:
    """Distinct 4-letter tickers in the live DB's ohlcv table plus the pre-2021 history pickle."""
    names: set[str] = set()
    try:
        con = sqlite3.connect(f"file:{LIVE_DB}?mode=ro", uri=True)
        names |= {r[0] for r in con.execute("SELECT DISTINCT ticker FROM ohlcv")}
        con.close()
    except sqlite3.Error as exc:
        log(f"warning: live DB ticker list failed ({exc}); trying read_raw_ohlcv")
        sys.path.insert(0, str(REPO))
        from data.adjustments import read_raw_ohlcv
        from data.db import transaction
        # transaction(), not a bare `with connect(...)`: the latter never closes
        # the handle (data/db.py docstring; the 2026-10-13 1,012-handle incident).
        with transaction(path=LIVE_DB, read_only=True) as c:
            names |= set(read_raw_ohlcv(c)["ticker"].unique())
    try:
        sys.path.insert(0, str(REPO))
        import pandas as pd
        import research.rulecard.data as rcdata
        names |= set(pd.read_pickle(rcdata.DEFAULT_HIST)["ticker"].unique())
    except Exception as exc:  # pre-2021 history is optional for the universe
        log(f"warning: pre-2021 history ticker list unavailable ({type(exc).__name__}: {exc})")
    return sorted(t for t in names if isinstance(t, str) and TICKER_RE.match(t))


# ---------------------------------------------------------------- fetch

def raw_path(t: str, st: str) -> Path:
    return OUT_DIR / "raw" / t / f"{st}.json.gz"


def done_set() -> set[tuple[str, str]]:
    """(ticker, statement) pairs that need no further request: saved files + recorded 404/empty."""
    out = set()
    for p in (OUT_DIR / "raw").glob("*/*.json.gz"):
        out.add((p.parent.name, p.name.split(".")[0]))
    man = OUT_DIR / "manifest.jsonl"
    if man.exists():
        for line in man.read_text(encoding="utf-8").splitlines():
            try:
                m = json.loads(line)
            except ValueError:
                continue
            if m.get("status") in (404, "empty"):
                out.add((m["ticker"], m["statement"]))
    return out


def count_periods(body) -> tuple[int, str | None, str | None]:
    h = (body or {}).get("data", {}).get("html_report") or ""
    labels = [html.unescape(x).strip() for x in re.findall(r'<th class="periods-list"[^>]*>(.*?)</th>', h, re.S)]
    return len(labels), (labels[0] if labels else None), (labels[-1] if labels else None)


def fetch(args) -> int:
    import requests

    tickers = [t.upper() for t in args.tickers] if args.tickers else universe()
    todo_all = [(t, st) for t in tickers for st in STATEMENTS]
    done = done_set()
    todo = [x for x in todo_all if x not in done]
    if args.limit:
        keep = sorted({t for t, _ in todo})[: args.limit]
        todo = [x for x in todo if x[0] in keep]
    est_min = len(todo) * (RATE_DELAY + 1.0) / 60
    n_done = sum(1 for x in todo_all if x in done)
    log(f"universe {len(tickers)} tickers; {len(todo_all)} requests total, {n_done} already done, "
        f"{len(todo)} to go (~{est_min:.0f} min at {RATE_DELAY}s + ~1s latency)")
    if args.dry_run:
        log(f"first: {todo[:3]} ... last: {todo[-3:]}; output -> {OUT_DIR}")
        return 0

    now = datetime.now(WIB)
    why = blocked(now)
    if why and not args.force:
        log(f"REFUSED: {why}. Best window: Sunday daytime. Or pass --force.")
        return 2
    token = read_token()
    exp = token_expiry(token)
    if exp is not None and exp <= datetime.now(timezone.utc) + timedelta(minutes=10):
        log(f"REFUSED: token expires {exp.astimezone(WIB):%a %H:%M} WIB. Do not log in by hand; "
            "wait for the scheduled refresh (weekdays 08:40, Sat/Sun 21:40).")
        return 2

    (OUT_DIR / "raw").mkdir(parents=True, exist_ok=True)
    man = open(OUT_DIR / "manifest.jsonl", "a", encoding="utf-8")
    sess = requests.Session()
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
               "Origin": "https://stockbit.com", "Referer": "https://stockbit.com/", "Accept": "application/json"}
    t0, n_ok, n_miss, consec_err, code = time.time(), 0, 0, 0, 0
    deadline = t0 + args.max_minutes * 60
    for i, (t, st) in enumerate(todo, 1):
        nowl = datetime.now(WIB)
        if time.time() > deadline:
            log(f"stop: --max-minutes {args.max_minutes} reached; rerun to resume")
            break
        if exp is not None and datetime.now(timezone.utc) > exp - timedelta(minutes=5):
            log("stop: token about to expire; rerun after the next scheduled refresh")
            break
        if blocked(nowl) and not args.force:
            log(f"stop: entered blocked window ({blocked(nowl)}); rerun later to resume")
            break
        url = BASE + URL_TMPL.format(t=t, r=STATEMENTS[st])
        rec = {"ticker": t, "statement": st, "fetched_at": datetime.now(timezone.utc).isoformat()}
        status, body = None, None
        for attempt in range(4):
            try:
                r = sess.get(url, headers=headers, timeout=30)
                status = r.status_code
            except requests.RequestException as exc:
                status = f"neterr:{type(exc).__name__}"
            if status == 429 or (isinstance(status, int) and status >= 500) or isinstance(status, str):
                if attempt == 3:
                    break
                wait = 60 * (2 ** attempt)
                log(f"  {t} {st}: {status}; backing off {wait}s")
                time.sleep(wait)
                continue
            break
        if status in (401, 403):
            log(f"STOP: {status} -- token rejected. Do not re-login now; rerun after the next scheduled refresh.")
            code = 2
            break
        if status == 200:
            try:
                body = r.json()
            except ValueError:
                body = None
            n, first, last = count_periods(body)
            if n == 0:
                rec.update(status="empty")
                n_miss += 1
            else:
                blob = gzip.compress(r.content)
                p = raw_path(t, st)
                p.parent.mkdir(parents=True, exist_ok=True)
                tmp = p.with_suffix(".tmp")
                tmp.write_bytes(blob)
                tmp.replace(p)
                rec.update(status=200, bytes=len(blob), sha256=hashlib.sha256(blob).hexdigest(),
                           n_periods=n, first=first, last=last)
                n_ok += 1
            consec_err = 0
        elif status == 404:
            rec.update(status=404)
            n_miss += 1
            consec_err = 0
        else:
            rec.update(status=status)
            consec_err += 1
            if consec_err >= 5:
                log(f"STOP: 5 consecutive failures (last {status}); rerun later to resume")
                man.write(json.dumps(rec) + "\n")
                code = 1
                break
        man.write(json.dumps(rec) + "\n")
        man.flush()
        if i % 50 == 0:
            log(f"  {i}/{len(todo)} done ({n_ok} saved, {n_miss} missing/empty)")
        time.sleep(RATE_DELAY)
    man.close()
    left = len([x for x in todo_all if x not in done_set()])
    log(f"run end: {n_ok} saved, {n_miss} missing/empty this run; {left} requests still to go")
    return code


# ---------------------------------------------------------------- parse

ROW_RE = re.compile(r"(<tr[^>]*>)(.*?)</tr>", re.S | re.I)
CELL_RE = re.compile(r"(<t[dh][^>]*>)(.*?)</t[dh]>", re.S | re.I)
ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')
TAG_RE = re.compile(r"<[^>]+>")
SUFFIX = {"T": 1e12, "B": 1e9, "M": 1e6, "K": 1e3}


def _attrs(tag: str) -> dict:
    return dict(ATTR_RE.findall(tag))


def to_number(s: str | None) -> tuple[float | None, str | None]:
    """'4303879000000.000000' -> 4.30e12; '18,637.07 B' -> 1.8637e13; '0.93%' -> (0.93, '%');
    '(1,234)' -> -1234 (negative in parentheses, the accounting display form — data-raw uses
    signed floats, but the shown-text fallback can meet it); '-'/'n/a' -> None."""
    if s is None:
        return None, None
    x = html.unescape(s).strip().replace(",", "")
    if x in ("", "-", "n/a", "N/A"):
        return None, None
    neg = x.startswith("(") and x.endswith(")")
    if neg:
        x = x[1:-1].strip()
    unit = None
    if x.endswith("%"):
        x, unit = x[:-1].strip(), "%"
    mult = 1.0
    if x and x[-1] in SUFFIX and x[:-1].strip().replace(".", "", 1).lstrip("-").isdigit():
        mult, x = SUFFIX[x[-1]], x[:-1].strip()
    try:
        v = float(x) * mult
        return (-v if neg else v), unit
    except ValueError:
        return None, None


def period_fields(label: str) -> tuple[int | None, int | None, str | None]:
    m = re.match(r"Q([1-4])\s+(\d{4})", label or "")
    if not m:
        return None, None, None
    q, y = int(m.group(1)), int(m.group(2))
    end = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}[q]
    return y, q, f"{y}-{end}"


def parse_report(h: str) -> list[dict]:
    """One dict per (row, period). Main section rows carry data-left/right (nested-set hierarchy) and
    data-raw values; rows after the second header row are Stockbit's derived per-quarter ratios."""
    out, periods, section, order = [], [], "statement", 0
    for tag, body in ROW_RE.findall(h):
        cells = CELL_RE.findall(body)
        if not cells:
            continue
        if cells[0][0].lower().startswith("<th"):
            labels = [html.unescape(TAG_RE.sub("", c)).strip() for _, c in cells[1:]]
            if periods:
                section = "derived"
            periods = labels
            continue
        ra = _attrs(tag)
        span = re.search(r'<span class="acc-name"([^>]*)>', cells[0][1])
        sa = _attrs(span.group(1)) if span else {}
        name_en = html.unescape(sa.get("data-lang-1", "")) or html.unescape(TAG_RE.sub("", cells[0][1])).strip()
        name_id = html.unescape(sa.get("data-lang-0", ""))
        order += 1
        for (ctag, ctext), plabel in zip(cells[1:], periods):
            ca = _attrs(ctag)
            shown = html.unescape(TAG_RE.sub("", ctext)).strip()
            raw = ca.get("data-raw", shown)
            val, unit = to_number(raw)
            if shown.lower() == "n/a":          # data-raw carries 0.0 where the page shows n/a
                val = None
            y, q, pend = period_fields(plabel)
            out.append({"section": section, "row_order": order, "account_en": name_en, "account_id": name_id,
                        "row_left": int(ra["data-left"]) if ra.get("data-left", "").isdigit() else None,
                        "row_right": int(ra["data-right"]) if ra.get("data-right", "").isdigit() else None,
                        "is_head": int("r_head" in ra.get("class", "")), "period": plabel, "year": y,
                        "quarter": q, "period_end": pend, "value_raw": raw, "value": val, "unit": unit})
    return out


SCHEMA = """
CREATE TABLE IF NOT EXISTS fin_rows (
  ticker TEXT, statement TEXT, section TEXT, row_order INT, account_en TEXT, account_id TEXT,
  row_left INT, row_right INT, is_head INT, PRIMARY KEY (ticker, statement, section, row_order));
CREATE TABLE IF NOT EXISTS fin_values (
  ticker TEXT, statement TEXT, section TEXT, row_order INT, period TEXT, year INT, quarter INT,
  period_end TEXT, value REAL, unit TEXT,
  PRIMARY KEY (ticker, statement, section, row_order, period)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS fin_files (
  ticker TEXT, statement TEXT, sha256 TEXT, n_values INT, parsed_at TEXT, PRIMARY KEY (ticker, statement));
CREATE VIEW IF NOT EXISTS fin_long AS
  SELECT v.ticker, v.statement, v.section, v.row_order, r.account_en, r.account_id, r.row_left, r.row_right,
         r.is_head, v.period, v.year, v.quarter, v.period_end, v.value, v.unit
  FROM fin_values v JOIN fin_rows r USING (ticker, statement, section, row_order);
"""


def parse(args) -> int:
    files = sorted((OUT_DIR / "raw").glob("*/*.json.gz"))
    if not files:
        log(f"nothing to parse under {OUT_DIR / 'raw'}")
        return 1
    db = sqlite3.connect(OUT_DIR / "fin.db")
    db.executescript(SCHEMA)
    have = dict(((t, s), h) for t, s, h in db.execute("SELECT ticker, statement, sha256 FROM fin_files"))
    n_files = n_rows = 0
    for p in files:
        t, st = p.parent.name, p.name.split(".")[0]
        blob = p.read_bytes()
        sha = hashlib.sha256(blob).hexdigest()
        if have.get((t, st)) == sha:
            continue
        h = (json.loads(gzip.decompress(blob)).get("data") or {}).get("html_report") or ""
        rows = parse_report(h)
        for tbl in ("fin_rows", "fin_values"):
            db.execute(f"DELETE FROM {tbl} WHERE ticker=? AND statement=?", (t, st))
        seen = {}
        for r in rows:
            seen.setdefault((r["section"], r["row_order"]), (r["account_en"], r["account_id"], r["row_left"],
                                                             r["row_right"], r["is_head"]))
        db.executemany("INSERT OR REPLACE INTO fin_rows VALUES (?,?,?,?,?,?,?,?,?)",
                       [(t, st, sec, o, *meta) for (sec, o), meta in seen.items()])
        db.executemany("INSERT OR REPLACE INTO fin_values VALUES (?,?,?,?,?,?,?,?,?,?)",
                       [(t, st, r["section"], r["row_order"], r["period"], r["year"], r["quarter"], r["period_end"],
                         r["value"], r["unit"]) for r in rows])
        db.execute("INSERT OR REPLACE INTO fin_files VALUES (?,?,?,?,?)",
                   (t, st, sha, len(rows), datetime.now(timezone.utc).isoformat()))
        n_files += 1
        n_rows += len(rows)
        if n_files % 200 == 0:
            db.commit()
            log(f"  parsed {n_files} files")
    db.commit()
    tot = db.execute("SELECT COUNT(*), COUNT(DISTINCT ticker) FROM fin_values").fetchone()
    db.close()
    log(f"parsed {n_files} new/changed files ({n_rows} rows); fin.db now {tot[0]} rows, {tot[1]} tickers")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Stockbit quarterly financials backfill")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--tickers", nargs="+")
    f.add_argument("--limit", type=int, default=0)
    f.add_argument("--max-minutes", type=int, default=170)
    f.add_argument("--force", action="store_true")
    f.add_argument("--dry-run", action="store_true")
    sub.add_parser("parse")
    a = ap.parse_args(argv)
    return fetch(a) if a.cmd == "fetch" else parse(a)


if __name__ == "__main__":
    sys.exit(main())
