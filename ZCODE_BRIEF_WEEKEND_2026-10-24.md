# ZCODE BRIEF — weekend 2026-10-24/25: C5 re-run, PEAD G0 power run, Monday readiness

**Issued:** 2026-10-24, by Claude (planner role). Owner: "next task for zcode".
**Repos:** `~/10 Projects/idx-walkforward-5001` (`ops/hardening-2026-07-10`) and `~/jurnal26` (`main`).
**Push: HOLD** until the owner says "push" (fast-forward only). Commit locally.
**Scheduling:** systemd one-shot timers (`systemd-run --user`) only; never ZCode's own automations.

## Rules
- Stockbit: read `.stockbit_token` only, never log in, stop on 401/403/429. Nothing heavy 21:05–06:30.
- Frozen: jurnal26 `bigplayer_watch.py`, `tape.py`, `limit_watch.py`. No outcome reads on any frozen forward record.
- Production DB: writes only via `data.db.connect()`. Research code never imports execution modules.
- D-numbers and the PEAD registration decision belong to the owner: propose text, do not file.

## G1. C5 auction backfill re-run (jurnal26) — Sunday after 06:40
Background: the 10-23 19:00 run crashed on a wrong DB path (fixed, jurnal26 `5a8e766`), and the Saturday re-run was
refused because the token had expired (Sat refresh is 21:40).
1. Sunday ~06:40, confirm the Saturday 21:40 refresh succeeded (token file mtime, one cheap authenticated GET).
   If it failed, **stop and report**; do not log in from here.
2. Arm a one-shot timer for Sunday 06:45, finishing before the 09:05 full pull:
   `cd ~/jurnal26 && .venv/bin/python auction_watch.py backfill 2026-10-16 2026-10-19 2026-10-20 2026-10-21 2026-10-22`
3. Check `data/auction_reports/` has the five dates and the report reads sensibly (prev close from the 5001 DB,
   IEP/gap, match print, first minutes). Add a test for the DB-path regression if `test_auction_watch.py` lacks one.

## G2. PEAD G0 power run (5001) — Sunday, outside market hours
`docs/research_programs/P-M/pead/` is frozen at `e7e68db`. Run `g0_pead_power.py` per its freeze doc (needs ~1–2 GB RAM;
the box has 7 GB; it refuses during market hours).
- This is the power check, **not** an outcome read: no post-event return may be looked at.
- Expectation from the pre-run arithmetic: power ~2–8% against the 20% minimum, so the stop rule probably fires.
- Report the numbers, whether the stop rule fired, and a **proposed** D-entry text for the owner
  (WITHDRAWN uncounted if it fired, like the 10-16 sector arm and {LC} D-110). Do not file the D-entry.

## G3. Monday 2026-10-26 readiness (do Sunday evening, read-only)
1. The three auction timers (08:50 / 08:59 / 09:02) are enabled; jurnal26 and 5001 services are active.
2. Monday 07:40 token refresh and 08:30 `--preopen-check` are still scheduled; say so explicitly.
3. `GET /api/auction?date=<a backfilled date>` returns the report with the read token
   (`~/.config/autoclaw-idx-monitor/read_token`, never the owner token).
4. Report anything that could stop a first live run at 08:50 (stale token, DB path, timer state).
5. The Monday after-09:35 live check (F3.2 of `ZCODE_BRIEF_IHSG_FALLBACK_AND_FOREIGN_FIELDS_2026-10-23.md`) stays in a
   fresh chat Monday.

## Deliverable
`docs/reports/ZCODE_WEEKEND_2026-10-24.md` (5001): each of G1–G3 as DONE / BLOCKED (why) / NOT RUN (why), the PEAD G0
numbers with the proposed D-entry text, and the commit hashes of both repos.
