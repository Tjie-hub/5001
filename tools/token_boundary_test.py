#!/usr/bin/env python3
"""Controlled test that the token-refresh chain survives a REAL expiry boundary.

WHY THIS EXISTS
---------------
The 2026-08-20 bounded soak validated throughput, rate limits, crash-consistency
and resume, but could not test token refresh: the token was valid throughout.
A ~157h full backfill needs 6-7 successful unattended re-auths, so this is the
largest untested dependency before that run is approved.

WHAT IT EXERCISES
-----------------
    ensure_valid_token()
      -> verify_token()                     (detects the expired bearer)
      -> _auto_login_fallback()
           -> auto_token.auto_refresh()     (Playwright session replay)
           -> auto_token.credential_login() (fallback)
      -> resumed fetch_flow() succeeds with the new token

READ-ONLY: fetch_flow() is a plain GET + parse. This script performs NO database
writes and computes no OFI / cont_k / hypothesis statistic. The only state it can
change is .stockbit_token itself, and only via the production refresh path --
which persists atomically and only after verifying the new token, so a failed
refresh leaves the existing file untouched.

HOW TO RUN IT (timing matters)
------------------------------
The point is to hold an *in-memory* token across the moment it expires. Start
BEFORE expiry and run past it:

    # token expires 08:40 WIB; cron also refreshes .stockbit_token at 08:40
    PYTHONPATH=. ./venv/bin/python tools/token_boundary_test.py \
        --until 08:50 --check-every 60

Starting AFTER 08:40 proves nothing: the process would simply load the already
refreshed file at startup and never enter the fallback path.
"""
import argparse
import os
import sys
import time
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _ts():
    return datetime.now().strftime("%H:%M:%S")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--until", required=True,
                    help="HH:MM local wall-clock time to stop (e.g. 08:50)")
    ap.add_argument("--check-every", type=int, default=60,
                    help="seconds between verify_token() probes")
    ap.add_argument("--ticker", default="BBCA", help="probe ticker for fetch")
    ap.add_argument("--date", default="2025-01-07",
                    help="historical session used for the resumed-fetch probe")
    args = ap.parse_args()

    os.chdir(ROOT)
    from stockbit_fetcher import (  # noqa: E402
        ensure_valid_token, verify_token, fetch_flow,
    )
    from flow_filter import _parse_bars  # noqa: E402

    stop_h, stop_m = (int(x) for x in args.until.split(":"))

    token = ensure_valid_token()
    if not token:
        print(f"[{_ts()}] ABORT: no valid token at start")
        return 1
    print(f"[{_ts()}] START token_tail=...{token[-8:]}")

    refreshed = False
    expiry_detected_at = None
    probes = 0

    while True:
        now = datetime.now()
        if (now.hour, now.minute) >= (stop_h, stop_m):
            print(f"[{_ts()}] STOP: reached --until {args.until}")
            break

        probes += 1
        ok = verify_token(token)
        print(f"[{_ts()}] probe#{probes} verify_token={ok}")

        if not ok:
            if expiry_detected_at is None:
                expiry_detected_at = now
                print(f"[{_ts()}] EXPIRY DETECTED -- entering refresh chain")
            new = ensure_valid_token()
            if not new:
                print(f"[{_ts()}] REFRESH FAILED -- chain did not recover")
                return 2
            changed = new != token
            token = new
            refreshed = True
            print(f"[{_ts()}] REFRESH OK token_changed={changed} "
                  f"token_tail=...{token[-8:]}")

            # Prove the resumed fetch actually works with the new token.
            res = fetch_flow(token, args.ticker, args.date)
            nbars = len(_parse_bars(res["_raw_data"])) if res else 0
            print(f"[{_ts()}] RESUMED FETCH {args.ticker} {args.date} "
                  f"ok={res is not None} bars={nbars}")
            if not res:
                print(f"[{_ts()}] FAIL: fetch did not resume after refresh")
                return 3
            print(f"[{_ts()}] PASS: full refresh chain verified")
            return 0

        time.sleep(args.check_every)

    if not refreshed:
        print(f"[{_ts()}] INCONCLUSIVE: token never expired during the window "
              f"(probes={probes}). Re-run spanning the real expiry moment.")
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
