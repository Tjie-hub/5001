# ZCODE report — weekend brief 2026-10-24 (G1–G3)

Brief: `ZCODE_BRIEF_WEEKEND_2026-10-24.md`. Push: HOLD (owner's "push" only; fast-forward only).

## G1. C5 auction backfill re-run (jurnal26) — **DONE** (Sunday 2026-10-25, 12:33–~13:10 WIB)

- **Late start, not the 06:45 slot:** the session began at 12:31. The token was valid to 21:40 (`auto_token.py --check`:
  9.1 h left, API test valid; no login, no refresh), the FQ full pull was finished and no tape backfill was running,
  so the run stayed clear of the 21:05–06:30 window.
- **Run:** one-shot systemd timer `c5-backfill-20261025` (12:33:12) ran
  `auction_watch.py backfill 2026-10-16 2026-10-19 2026-10-20 2026-10-21 2026-10-22` — `Result=success`,
  exit 0, no 401/403/429, no "page failed" lines. Log `~/jurnal26/logs/c5_backfill_20261025.log`.
- **Output:** `~/jurnal26/data/auction_reports/` has all five dates. Each report lists 26–27 names; prev close comes
  from the 5001 DB. Sanity: 10-16 (MSCI day) has 12 names matched at the ARB floor (−14–15 % vs prev); the count falls to
  11 / 2 / 0 / 1 on 10-19 … 10-22. IEP reads "n/a (not recorded)" as designed. INDR is absent on 10-22 (no trades
  returned, no page failure — not investigated).
- **Label check:** "matched at the ARB floor" fires when the match is within 1 % of the floor (`auction_watch.py:346`,
  `ALERT_ARB_NEAR`), so TLKM 1,780 vs floor 1,770 on 10-19 is intended behaviour, only loosely worded.
- **Test:** `test_auction_watch.py` had no DB-path regression. Added
  `test_backfill_prev_close_reads_the_5001_db_next_to_the_token`; it fails on the old `parents[1]` lookup and passes on
  the fix. File: 19 passed. jurnal26 commit `d117c61` (local).

## G2. PEAD G0 power run — **NOT RUN** (not started in this session)

## G3. Monday 2026-10-26 readiness — **NOT RUN** (due Sunday evening, read-only). Seen in passing: the three auction
timers (08:50 / 08:59 / 09:02) are enabled for Mon 10-26; the rest of G3 is unchecked.
