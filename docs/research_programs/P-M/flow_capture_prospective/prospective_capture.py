#!/usr/bin/env python3
"""Prospective raw-response capture service for Stockbit flow data (P-M).

Captures the VENDOR'S RAW RESPONSE per (ticker, session) into an immutable,
content-addressed, append-only store, with a full request/response audit
manifest, checkpoint/resume, completeness markers, and deterministic
reconstruction. DESIGN.md documents the architecture and the audit findings
that motivate it.

ISOLATION GUARANTEE: this module writes ONLY under
flow_capture_prospective/store/. It never touches walkforward.db,
research.db, Dataset B, or any frozen store. The vendor adapter is
lazy-imported so that tests run fully offline with a fake fetcher.

NOT SCHEDULED: activation is an explicit owner action (DESIGN.md §7).
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import sqlite3
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(HERE, "store")
TZ_SESSION = "Asia/Jakarta"
VENDOR_LIMIT = 150          # per-side row cap used by production practice
MAX_ATTEMPTS = 4
BACKOFF_S = (20.0, 40.0, 60.0, 80.0)

# --------------------------------------------------------------------- types


@dataclass
class RawResponse:
    """Exact bytes plus the request/response metadata we are allowed to keep."""
    ticker: str
    session: str
    http_status: int
    body: bytes                    # exact body bytes (uncompressed identity)
    url_host: str = ""
    url_path: str = ""
    requested_from: str = ""
    requested_to: str = ""
    returned_from: str = ""
    returned_to: str = ""
    error: str = ""


# --------------------------------------------------------------- raw parsing

def parse_body(body: bytes) -> dict:
    """Pure function: exact response bytes -> normalized structure.

    Shape (verified against the retained Dataset B raw_responses):
      {"message": ..., "data": {"from": YYYY-MM-DD, "to": YYYY-MM-DD,
       "broker_summary": {"symbol", "brokers_buy": [...], "brokers_sell": [...]},
       "bandar_detector": {...}}}
    Each broker row carries netbs_broker_code / blot|slot / bval|sval /
    netbs_buy_avg_price|netbs_sell_avg_price / type / freq.
    """
    obj = json.loads(body.decode("utf-8"))
    data = obj.get("data") or {}
    bs = data.get("broker_summary") or {}
    rows = []
    for side, key in (("BUY", "brokers_buy"), ("SELL", "brokers_sell")):
        for r in (bs.get(key) or []):
            rows.append({
                "ticker": r.get("netbs_stock_code"),
                "trade_date": r.get("netbs_date"),
                "broker_code": r.get("netbs_broker_code"),
                "side": side,
                "lot": r.get("blot") if side == "BUY" else r.get("slot"),
                "value": r.get("bval") if side == "BUY" else r.get("sval"),
                "avg_price": (r.get("netbs_buy_avg_price") if side == "BUY"
                              else r.get("netbs_sell_avg_price")),
                "investor_type": r.get("type"),
                "freq": r.get("freq"),
            })
    return {"returned_from": data.get("from"), "returned_to": data.get("to"),
            "n_rows": len(rows), "rows": rows,
            "bandar_present": bool(data.get("bandar_detector"))}


def rebuild_rows(body: bytes) -> list[dict]:
    """Deterministic reconstruction of broker rows from raw bytes."""
    return parse_body(body)["rows"]


# ----------------------------------------------------------------- manifest

MANIFEST_DDL = """
CREATE TABLE IF NOT EXISTS capture_manifest (
  ticker TEXT NOT NULL, session_date TEXT NOT NULL,
  status TEXT NOT NULL, attempt INTEGER NOT NULL,
  http_status INTEGER, url_host TEXT, url_path TEXT,
  requested_from TEXT, requested_to TEXT,
  returned_from TEXT, returned_to TEXT,
  date_echo_match INTEGER, n_rows INTEGER, truncation_suspected INTEGER,
  response_sha256 TEXT NOT NULL, response_bytes INTEGER NOT NULL,
  raw_object TEXT NOT NULL, captured_at_utc TEXT NOT NULL,
  tz_session TEXT NOT NULL, error TEXT,
  PRIMARY KEY (ticker, session_date, attempt)
);
CREATE TABLE IF NOT EXISTS run_log (
  run_id TEXT PRIMARY KEY, started_at_utc TEXT, finished_at_utc TEXT,
  code_sha256 TEXT, config_digest TEXT,
  cells_intended INTEGER, cells_attempted INTEGER,
  cells_success INTEGER, cells_empty INTEGER, cells_failed INTEGER,
  host TEXT, note TEXT);
"""


def manifest_connect(store: str) -> sqlite3.Connection:
    os.makedirs(os.path.join(store, "runs"), exist_ok=True)
    c = sqlite3.connect(os.path.join(store, "manifest.sqlite"))
    c.executescript(MANIFEST_DDL)
    return c


def terminal(c: sqlite3.Connection, ticker: str, session: str) -> bool:
    row = c.execute("SELECT status FROM capture_manifest WHERE ticker=? AND "
                    "session_date=? ORDER BY attempt DESC LIMIT 1",
                    (ticker, session)).fetchone()
    return bool(row and row[0] in ("SUCCESS", "EMPTY"))


# -------------------------------------------------------------- capture core

def capture_cell(c: sqlite3.Connection, store: str, ticker: str, session: str,
                 fetch) -> str:
    """Capture one (ticker, session). Returns terminal status. Checkpoint-safe."""
    if terminal(c, ticker, session):
        return "SKIP"
    # attempts are numbered per cell ACROSS runs (checkpoint/resume never
    # reuses an attempt number — the manifest PK is (ticker, session, attempt))
    prev = c.execute("SELECT MAX(attempt) FROM capture_manifest "
                     "WHERE ticker=? AND session_date=?",
                     (ticker, session)).fetchone()[0]
    first_attempt = (prev or 0) + 1
    last_err = ""
    for attempt in range(first_attempt, first_attempt + MAX_ATTEMPTS):
        try:
            resp: RawResponse = fetch(ticker, session)
        except Exception as e:  # noqa: BLE001 — recorded, retried, never hidden
            last_err = repr(e)[:300]
            time.sleep(BACKOFF_S[min(attempt - 1, len(BACKOFF_S) - 1)])
            continue
        body_sha = hashlib.sha256(resp.body).hexdigest()
        parsed = parse_body(resp.body)
        date_echo = int(parsed["returned_from"] == resp.requested_from
                        and parsed["returned_to"] == resp.requested_to) \
            if (resp.requested_from and parsed["returned_from"]) else 0
        trunc = int(parsed["n_rows"] >= 2 * VENDOR_LIMIT)
        status = ("FAILED" if resp.http_status != 200 or last_err
                  else "EMPTY" if parsed["n_rows"] == 0 and date_echo
                  else "SUCCESS")
        rel = os.path.join("raw", f"session={session}", f"ticker={ticker}",
                           f"{body_sha}.json.gz")
        abs_obj = os.path.join(store, rel)
        os.makedirs(os.path.dirname(abs_obj), exist_ok=True)
        # write-once: refuse to overwrite ANY existing raw object
        if os.path.exists(abs_obj):
            existing = gzip.open(abs_obj, "rb").read()
            if hashlib.sha256(existing).hexdigest() != body_sha:
                raise RuntimeError(f"immutability violation: object exists with "
                                   f"different content {abs_obj}")
        else:
            fd = os.open(abs_obj, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
            with os.fdopen(fd, "wb") as f:
                f.write(gzip.compress(resp.body, mtime=0))
        c.execute("INSERT OR ABORT INTO capture_manifest VALUES "
                  "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (ticker, session, status, attempt, resp.http_status,
                   resp.url_host, resp.url_path,
                   resp.requested_from, resp.requested_to,
                   parsed["returned_from"], parsed["returned_to"],
                   date_echo, parsed["n_rows"], trunc,
                   body_sha, len(resp.body), rel,
                   datetime.now(timezone.utc).isoformat(), TZ_SESSION,
                   resp.error or last_err))
        c.commit()
        if status in ("SUCCESS", "EMPTY"):
            return status
        last_err = f"http {resp.http_status}"
        time.sleep(BACKOFF_S[min(attempt - 1, len(BACKOFF_S) - 1)])
    c.execute("INSERT OR ABORT INTO capture_manifest VALUES "
              "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (ticker, session, "FAILED", first_attempt + MAX_ATTEMPTS, None,
               "", "", session, session, None, None, 0, 0, 0,
               "0" * 64, 0, "", datetime.now(timezone.utc).isoformat(),
               TZ_SESSION, last_err or "attempts exhausted"))
    c.commit()
    return "FAILED"


def capture_run(store: str, cells, fetch, note: str = "") -> dict:
    """Run a capture campaign over (ticker, session) cells with checkpoints."""
    c = manifest_connect(store)
    code_sha = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
    run_id = f"RUN-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{code_sha[:12]}"
    intended = len(cells)
    counts = {"SUCCESS": 0, "EMPTY": 0, "FAILED": 0, "SKIP": 0}
    for ticker, session in cells:
        counts[capture_cell(c, store, ticker, session, fetch)] += 1
    config = json.dumps({"max_attempts": MAX_ATTEMPTS,
                         "vendor_limit": VENDOR_LIMIT,
                         "tz_session": TZ_SESSION}, sort_keys=True)
    digest = hashlib.sha256(config.encode()).hexdigest()
    c.execute("INSERT OR REPLACE INTO run_log VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
              (run_id, datetime.now(timezone.utc).isoformat(),
               datetime.now(timezone.utc).isoformat(), code_sha, digest,
               intended, counts["SUCCESS"] + counts["EMPTY"] + counts["FAILED"],
               counts["SUCCESS"], counts["EMPTY"], counts["FAILED"],
               os.uname().nodename, note + f" skipped={counts['SKIP']}"))
    c.commit()
    run_manifest = {"artifact": "PROSPECTIVE_CAPTURE_RUN_MANIFEST",
                    "run_id": run_id, "code_sha256": code_sha,
                    "config_digest": digest, "cells_intended": intended,
                    "counts": counts, "note": note}
    run_dir = os.path.join(store, "runs", run_id)
    os.makedirs(run_dir, exist_ok=True)
    path = os.path.join(run_dir, "run_manifest.json")
    with open(path, "w") as f:
        json.dump(run_manifest, f, indent=1, sort_keys=True)
    with open(path + ".sha256", "w") as f:
        f.write(hashlib.sha256(open(path, "rb").read()).hexdigest() + "\n")
    c.close()
    return run_manifest


# ------------------------------------------------------------ vendor adapter

VENDOR_HOST = "exodus.stockbit.com"


def _assert_public_host(host: str) -> None:
    """SSRF guard: https-only scheme, exact host pin, resolve and refuse any
    private/loopback/link-local/reserved/non-global address. Returns nothing;
    use pin_validated_resolution() to bind the request to the validated IPs."""
    import ipaddress
    import socket
    if host != VENDOR_HOST:
        raise ValueError("host not pinned to " + VENDOR_HOST)
    for info in socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP):
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or not ip.is_global):
            raise ValueError("resolved address is not public: " + str(ip))


class pin_validated_resolution:
    """Context manager that pins socket resolution of VENDOR_HOST to the
    addresses just validated by _assert_public_host, closing the TOCTOU
    DNS-rebinding window between validation and connection. TLS/SNI still
    use the hostname, so certificate verification is unaffected."""

    def __enter__(self):
        import socket
        validated = socket.getaddrinfo(VENDOR_HOST, 443, proto=socket.IPPROTO_TCP)
        self._orig = socket.getaddrinfo

        def pinned(host, port, *args, **kwargs):
            if host == VENDOR_HOST:
                return validated
            return self._orig(host, port, *args, **kwargs)

        socket.getaddrinfo = pinned
        return self

    def __exit__(self, *exc):
        import socket
        socket.getaddrinfo = self._orig
        return False


def vendor_fetch(ticker: str, session: str) -> RawResponse:
    """Real adapter: mirrors the validated Dataset B capture request verbatim
    (same marketdetectors endpoint, params, auth, limit=150) and keeps the
    EXACT response body bytes — the thing production fetch_flow discards.
    Credentials come from the repo-root .stockbit_token file the owner's own
    tooling uses. Needs network; never imported by the offline selftest."""
    import requests  # noqa: PLC0415
    if not (ticker.isascii() and ticker.isalnum() and ticker.isupper()
            and len(ticker) <= 10):
        raise ValueError("invalid ticker token: " + repr(ticker))
    _assert_public_host(VENDOR_HOST)
    base = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
    token = open(os.path.join(base, ".stockbit_token")).read().strip()
    url = f"https://{VENDOR_HOST}/marketdetectors/{ticker}"
    params = {"transaction_type": "TRANSACTION_TYPE_NET",
              "market_board": "MARKET_BOARD_REGULER",
              "investor_type": "INVESTOR_TYPE_ALL",
              "limit": VENDOR_LIMIT,
              "from": session, "to": session}
    headers = {"Authorization": "Bearer " + token,
               "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                             "AppleWebKit/537.36",
               "Origin": "https://stockbit.com",
               "Referer": "https://stockbit.com/"}
    # URL is https + a constant pinned host + an A-Z0-9 ticker (validated
    # above); resolution is pinned to the addresses _assert_public_host just
    # validated, so the connection cannot be rebinding-redirected.
    with pin_validated_resolution():
        r = requests.get(url, params=params, headers=headers, timeout=15,
                         allow_redirects=False)
    return RawResponse(ticker=ticker, session=session,
                       http_status=r.status_code, body=r.content,
                       url_host=VENDOR_HOST,
                       url_path="/marketdetectors/" + ticker,
                       requested_from=session, requested_to=session)


# ------------------------------------------------------------------ selftest

def _fake_fetch(ok_tickers):
    """Offline fetcher: 200 for ok_tickers, 500 otherwise; deterministic body.
    EMPTYV returns a date-echo-matched response with zero broker rows."""
    def fetch(ticker: str, session: str) -> RawResponse:
        if ticker not in ok_tickers:
            return RawResponse(ticker, session, 500, b'{"message":"err"}',
                               "fake.host", "/fake", session, session,
                               error="vendor 500")
        rows = {"brokers_buy": [], "brokers_sell": [], "symbol": ticker}
        if ticker != "EMPTYV":
            rows["brokers_buy"] = [
                {"netbs_stock_code": ticker, "netbs_date": session.replace("-", ""),
                 "netbs_broker_code": "AA", "blot": "100", "bval": "1000000",
                 "netbs_buy_avg_price": "100.0", "type": "Lokal", "freq": "2"}]
        body = json.dumps({"message": "ok", "data": {
            "from": session, "to": session,
            "broker_summary": rows, "bandar_detector": {}}}).encode()
        return RawResponse(ticker, session, 200, body, "fake.host", "/fake",
                           session, session)
    return fetch


def selftest() -> int:
    import shutil
    import tempfile
    global BACKOFF_S
    BACKOFF_S = (0.0, 0.0, 0.0, 0.0)   # offline selftest: no real backoff sleeps
    tmp = tempfile.mkdtemp(prefix="pcap_selftest_")
    try:
        cells = [("BBCA", "2026-01-05"), ("TLKM", "2026-01-05"),
                 ("FAIL", "2026-01-05"), ("EMPTYV", "2026-01-05")]
        fetch = _fake_fetch({"BBCA", "TLKM", "EMPTYV"})
        m1 = capture_run(tmp, cells, fetch, "selftest run1")
        assert m1["counts"] == {"SUCCESS": 2, "EMPTY": 1, "FAILED": 1, "SKIP": 0}, m1
        # checkpoint: rerun is a no-op except the previously failed cell retries
        m2 = capture_run(tmp, cells, fetch, "selftest run2")
        assert m2["counts"]["SKIP"] == 3 and m2["counts"]["FAILED"] == 1, m2
        # manifest accounting: 3 terminal cells x 1 attempt each; the failing
        # cell records MAX_ATTEMPTS attempts + 1 exhaustion row, per run
        c = manifest_connect(tmp)
        before = c.execute("SELECT COUNT(*) FROM capture_manifest").fetchone()[0]
        c.close()
        assert before == 3 * 1 + 2 * (MAX_ATTEMPTS + 1), before
        # deterministic reconstruction: same raw bytes -> same rows, twice
        import glob
        obj = glob.glob(os.path.join(tmp, "raw", "session=2026-01-05",
                                     "ticker=BBCA", "*.json.gz"))[0]
        body = gzip.open(obj, "rb").read()
        assert rebuild_rows(body) == rebuild_rows(body)
        assert rebuild_rows(body)[0]["broker_code"] == "AA"
        # EMPTY cell classified via date echo, zero rows
        obj_e = glob.glob(os.path.join(tmp, "raw", "session=2026-01-05",
                                       "ticker=EMPTYV", "*.json.gz"))[0]
        assert parse_body(gzip.open(obj_e, "rb").read())["n_rows"] == 0
        print("selftest: ALL CHECKS PASS "
              f"(run1={m1['counts']}, run2={m2['counts']})")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["selftest", "capture"])
    ap.add_argument("--session", help="trading session YYYY-MM-DD")
    ap.add_argument("--sessions-file", help="one session per line")
    ap.add_argument("--tickers-file", help="one ticker per line")
    ap.add_argument("--store", default=STORE)
    ap.add_argument("--use-vendor", action="store_true",
                    help="enable the real vendor adapter (network + creds)")
    args = ap.parse_args()
    if args.command == "selftest":
        return selftest()
    if not args.use_vendor:
        raise SystemExit("capture requires --use-vendor (owner activation; "
                         "see DESIGN.md §7)")
    sessions = ([args.session] if args.session else
                [l.strip() for l in open(args.sessions_file) if l.strip()])
    tickers = [l.strip() for l in open(args.tickers_file) if l.strip()]
    cells = [(t, s) for s in sessions for t in tickers]
    print(json.dumps(capture_run(args.store, cells, vendor_fetch,
                                 f"sessions={len(sessions)} tickers={len(tickers)}"),
                     indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
