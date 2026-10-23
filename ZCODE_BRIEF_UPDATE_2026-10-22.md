# ZCODE BRIEF UPDATE — 2026-10-22: Y1 pilot moved to a systemd timer; validate it; schedule Sunday off-quota

**Issued:** 2026-10-22 08:55 WIB, by Claude (planner role). Owner: "now update the task for zcode".
**Amends:** `ZCODE_BRIEF_FQ_FULL_PULL_AND_PIT_REVISION_2026-10-21.md` (Y1, Y2 timing). Approvals A1–A3 are unchanged;
A2 (push) still covers **this {FQ} work only**.
Every rule in the 10-21 brief still applies. **Read it first.**

## What happened since your last report (verified by Claude)

| Item | State |
|---|---|
| **Y1 pilot, 10-21 19:05** | **FAILED to start.** Your automation (`automation-1639d2f4…`) fired at 19:05:07. The first model call returned `429 [1310] Weekly/Monthly Limit Exhausted. Your limit will reset at 2026-10-22 14:55:43`, flagged non-retryable, and the turn failed one second in. No GETs and no files: `~/idx_external/stockbit_fin` doesn't exist. Your report still says "NOT RUN YET". |
| T3.6 login move, 21:55 | DONE (`6deaaf0`). The saved login is now at `~/.local/state/idx-walkforward/playwright_state`. |
| Token, 10-22 | The 07:40 refresh worked: a stale capture, then the credential login succeeded, saved 07:41. The 08:10 retry skipped and the 08:30 pre-open check passed. **Valid to about 07:40 on 10-23.** |
| jurnal26 J1/J2 | DONE (`7a41d04`, `5a7795e`, `5c1e3e4`). Local, not pushed: no push approval for jurnal26. |
| 5001 token hardening | `d904430..6deaaf0`, 6 commits. Local, not pushed: no push approval for this brief. |

**The lesson for anything scheduled.** A ZCode automation depends on the Z.ai quota at fire time and doesn't retry
a 429. Any **data-pulling** step must therefore run as an OS job, a systemd user timer, and never inside a model turn.
The model turn only checks the result afterwards.

## U1. Tonight's pilot is already scheduled. Do not run a second one.

Claude created a one-off systemd user timer, **`fq-pilot-20261022`, which fires at 19:05 WIB on 2026-10-22**. It
runs `/tmp/claude-1000/…/scratchpad/fin_pilot.sh`:
1. `auto_token.py --preopen-check`;
2. `fetch --tickers BBCA TLKM ASII KIJA TOTO PNBS BTEL TRAM PGEO CUAN --max-minutes 30`, with no `--force`;
3. `parse`.

It logs to `logs/fin_pilot_20261022.log` (start/end markers and each step's rc).
- Check with `systemctl --user list-timers fq-pilot-20261022.timer`.
- **Do not fetch the pilot yourself while that timer is pending.** The script is resumable, but two runs at once share
  one token and one output dir.
- If the timer is gone or the log shows no `START` by 19:15, run the same three commands yourself before 21:50.

## U2. Validate Y1 after the run (any time after 19:10 tonight, or Friday morning)

Your quota resets at 14:55 today.
1. Read the log, the manifest and `fin.db`. Score each of the five pass criteria from the 10-21 brief (Y1.2):
   - all 3 statements for all 10 names;
   - BTEL and TRAM history present;
   - bank layouts (BBCA, PNBS) parsed;
   - no 401, 403 or 429 responses;
   - parse failures are 0, or each one is explained.
2. Fill in the pilot table and the full-pull extrapolation in `docs/reports/ZCODE_FQ_FULL_PULL_2026-10-21.md`. Replace
   "NOT RUN YET" with the outcome, and record the 10-21 429 failure and this re-run.
3. Commit, then push (A2) after the touched tests pass.
4. **Pilot fails?** Stop, report, and do not arm Sunday.

## U3. Arm Sunday's full pull as an OS job (only if U2 passes)

1. Schedule `fetch` (no `--force`, default `--max-minutes 170`) with a one-off systemd user timer for
   **Sunday 2026-10-25 09:05 WIB**, with output to a dated log. Use a script **under the repo** (e.g. `scripts/`,
   gitignored if needed), not `/tmp`, which can be cleared on reboot.
   - **Pre-flights in the script:** `--preopen-check`, and refusal if a jurnal26 tape backfill process is running.
2. **Second session:** add a 13:00 resume timer that runs only if the first left work undone. The script is resumable.
   Both must finish before ~20:30, clear of jurnal26's 21:05 backfill.
   - **Token check:** the Saturday 21:40 refresh gives a token valid to Sunday ~21:40. Confirm that schedule is still
     installed (`crontab -l`).
3. **Leave the rest to a model turn after the data exists:** `parse`, the sha256 manifest, the coverage table, the
   off-SSD copy to `/mnt/storage2tb/idx-archive/stockbit_fin/` with two-sided verification, and Y3 (PIT v2,
   propose only).
   - Run that turn on Sunday afternoon or Monday, in a fresh ZCode chat, if your quota allows.
4. Record the two timers (unit names, times, script path) in the report.

## Deliverable

Update `docs/reports/ZCODE_FQ_FULL_PULL_2026-10-21.md` with the U2 validation table, the U3 timer details (or why they
weren't armed), and the commit and push hashes.
