# ZCODE BRIEF — Tuesday 2026-10-27: close out 10-26 (PEAD withdrawal, {FQ} G0 result, 5001 restart check)

**Issued:** 2026-10-27, by Claude (planner role). Owner: "delegate task for zcode".
**Repos:** `~/10 Projects/idx-walkforward-5001` (`ops/hardening-2026-07-10`) and `~/jurnal26` (`main`).
**Push: HOLD** in both repos until the owner says "push" (fast-forward only). Commit locally.
**Scheduling:** systemd one-shot timers (`systemd-run --user`) only; never ZCode's own automations.

## State at issue (from git log + 10-26 reports; re-verify before acting)
- 5001 HEAD `d0fd245` (production signal audit applied). Uncommitted: `P-M/pead/G0_RESULT_20261026T175314.json`,
  `events_pead_20261026T175314.csv` (untracked), `forward_fade` / `forward_regime` `ledger.json` (cron appends).
- PEAD G0 ran 10-26 17:53: **stop rule fired** (506 events / 159 months, SE 0.90%, MDE80 3.74%, power at the 2% floor
  13.9%; holdout 8.2%, recent 1.5%). Not yet filed anywhere.
- {FQ}: D-111 / D-112 on record; E/P G0 frozen (sha `e14ab4d9`). KSEI pull of 92 codes + one G0 run were timed for
  19:05 on 10-26 (`zcode-fq-ksei-pull-20261026`); the outcome is not in the repo.

## Rules
- Stockbit: read `.stockbit_token` only, never log in, stop on 401/403/429. Nothing heavy 21:05–06:30.
- Frozen: jurnal26 `bigplayer_watch.py`, `tape.py`, `limit_watch.py`; `P-M/pead/` freeze; {FQ} G0 freeze. No outcome
  reads on any frozen forward record. G0 is a breadth/power check, never a return read.
- Production DB: writes only via `data.db.connect()`. Research code never imports execution modules.
- D-numbers, HYP-PM-0023 registration, any G1 run and any freeze belong to the owner: propose text, do not file.
- Restart 5001 only via `scripts/safe_restart.sh`, outside market hours (09:00–15:30 WIB), never bare `systemctl`.

## J1. {FQ} E/P G0 — what happened on 10-26 night
1. `journalctl --user -u zcode-fq-ksei-pull-20261026` and the G0 log under `P-M/fq/`: did the pull finish, how many
   of the 92 codes resolved, did G0 run once, did it refuse?
2. If G0 ran: report breadth numbers and whether its stop rule fired, against D-112's floor (IDX E/P IR 0.75).
   Commit the result files. If it did not run, say why and run it once after 17:40 (it refuses during market hours).
3. **Do not run G1 and do not register HYP-PM-0023.** Propose a D-entry text for the G0 outcome, do not file it.

## J2. PEAD withdrawal — paperwork only
1. Commit `G0_RESULT_20261026T175314.json`, `events_pead_20261026T175314.csv` and `g0_run_2026-10-26.log` as
   `docs(research): PEAD G0 power run 2026-10-26 -- stop rule fired`.
2. Draft the **proposed** D-entry text: PEAD long top-SUE quintile WITHDRAWN before registration, uncounted
   (same form as the 10-16 sector arm and {LC} D-110), with the numbers above. Put it in
   `docs/reports/ZCODE_TUESDAY_2026-10-27.md`; do not append it to `DECISION_LOG.md`.
3. Check the HYPOTHESIS_REGISTRY / FAILURE_REGISTRY: confirm PEAD has no registered row, and say so. Do not edit them.

## J3. 5001 restart check after `d0fd245`
1. Is the running process older than `d0fd245`? (`systemctl --user show idx-walkforward -p ActiveEnterTimestamp`
   vs the commit time.) Does `AGENT_FIRM_PROVIDER_ORDER=zai` show in the live process config, and is the Phase-5
   BULL-watch job gone from the scheduler's job list?
2. If stale and outside market hours, restart with `scripts/safe_restart.sh`, then confirm the boot preflight passed
   and the 16:40 EOD and 08:35 premarket jobs are still scheduled. If inside market hours, arm a one-shot timer for
   after 15:45 instead.
3. Run `pytest -q tests/test_architecture_boundary.py tests/security/test_route_policy.py` before and after.

## J4. Auction monitor and index rebalance
1. Auction first-live-day backfill (the 10-26 18:30 job): did it run, exit 0, and does
   `data/auction_reports/2026-10-26*` read sensibly? Also check today's 08:50 / 08:59 / 09:02 fires.
2. Index rebalance 2026-11-02 (carried from H4 of the 10-26 brief): if the IDX announcement is now reachable, prepare
   the IDX30/LQ45/IDX80 change as a commit **not applied to `idx_tickers` before 2026-11-02**, with adds/removes per
   index and a dated one-shot timer or written switch instructions. If still not announced, say so and stop.

## Deliverable
`docs/reports/ZCODE_TUESDAY_2026-10-27.md` (5001): each of J1–J4 as DONE / BLOCKED (why) / NOT RUN (why), the {FQ} G0
numbers, the proposed D-entry texts (PEAD, {FQ} G0), files written, and commit hashes of both repos. Update the
"Current status" block in `TODO.md` to match.
