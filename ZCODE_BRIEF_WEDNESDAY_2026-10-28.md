# ZCODE BRIEF — Wednesday 2026-10-28: {FQ} G0 close-out, rebalance list verification, scan rerun, 51 missing KSEI codes

**Issued:** 2026-10-27, by Claude (planner role). Owner: "next task for zcode".
**Repos:** `~/10 Projects/idx-walkforward-5001` (`ops/hardening-2026-07-10`) and `~/jurnal26` (`main`).
**Push: HOLD** in both repos until the owner says "push" (fast-forward only). Commit locally.
**Scheduling:** systemd one-shot timers (`systemd-run --user`) only; never ZCode's own automations.

## State at issue (re-verify before acting)
- `zcode-fq-g0-20261027.timer` armed for 17:41 on 10-27; result lands in `P-M/fq/` (`g0_run_2026-10-27.log` is
  gitignored by `*.log`, force-add it).
- Rebalance branches `ops/idx-rebalance-20261102` (5001 `ba3fd29`, jurnal26 `01b0bbb`) are unmerged; the lists came
  from the-signal.id (secondary), not from IDX.
- fin.db has 998 tickers; 51 of the 92 missing KSEI codes are still unresolved.
- Mimosa pre-commit scans failed with `scanner_enobufs` on the 10-27 commits, so those commits carry no security check.

## Rules
- Stockbit: read `.stockbit_token` only, never log in, stop on 401/403/429. Nothing heavy 21:05–06:30.
- Frozen: jurnal26 `bigplayer_watch.py`, `tape.py`, `limit_watch.py`; the {FQ} G0 freeze (sha `e14ab4d9`). G0 is a
  breadth/power check, never a return read.
- D-numbers, HYP-PM-0023 registration, any G1 run and any freeze belong to the owner: propose text, do not file.
- Restart 5001 only via `scripts/safe_restart.sh`, outside market hours.

## K1. {FQ} G0 result (first thing, after the 10-27 17:41 run)
1. Confirm the timer fired once and the script did not refuse (pins, sums file, freeze sha).
2. Report the breadth numbers and whether the stop rule fired against D-112's floor (IDX E/P IR 0.75).
3. Commit the result JSON, CSV and the force-added log: `docs(research): {FQ} E/P G0 breadth run 2026-10-27 -- <fired|passed>`.
4. Fill the blanks in the proposed D-entry template in `ZCODE_TUESDAY_2026-10-27.md` and put it in the new report.
   Do not file it, do not run G1, do not register HYP-PM-0023.
5. If the run refused or crashed: report the exact error, fix only a clear bug with a test, and do not re-run more
   than once.

## K2. Verify the rebalance lists against a primary or second independent source
1. Try to reach Peng-00204/BEI.POP/10-2026 from IDX or a second independent outlet (Kontan, Bisnis, CNBC Indonesia).
   Tag each source [P]/[S].
2. Compare every add/remove with the branch lists in `data/fetcher.py` and jurnal26 `tape_backfill.py`:
   IDX30 +ISAT +PTBA -PGEO -UNVR; LQ45 +SMGR -SCMA; IDX80 +AALI +TINS +TKIM -HEAL -MIKA -SMRA.
3. If the lists agree, say so. If any name differs, amend the branches (tests green) and report the diff.
   Do not merge and do not touch `idx_tickers` before 2026-11-02.

## K3. Security scan rerun
Rerun the Mimosa scan (or the repo's equivalent: `pytest -q tests/security/test_secret_hygiene.py`) over the 10-27
commits (`e14a7f8`..HEAD) in both repos, in smaller batches so it does not hit `ENOBUFS`. Report pass/fail per
commit range. Do not claim a pass for a range that did not complete.

## K4. The 51 unresolved KSEI codes
1. List them and, for each, why it is missing (no Stockbit financials, delisted, rate limit, parse failure).
2. Retry only the codes that failed for a transient reason, once, inside the Stockbit rules above.
3. Report the new fin.db count and the sha256 for a refreshed `SHA256SUMS`; do not overwrite the 10-26 sums file
   that G0 pins.

## K5. New concept (propose-only): what else the {FQ} fundamentals panel could test
The KSEI-complete monthly panel + fin.db (998 tickers) is the only new data of the last month; every price-pattern,
flow, event, index-reconstitution (HYP-PA-0001, F2) and PEAD (power stop) route is already closed. Write
`P-M/fq/FQ_FAMILY_WIDENING_MEMO_2026-10-28.md`, no code run, no returns read:
1. Candidate arms on the same panel and universe: profitability/quality (ROE, gross profitability), book-to-market,
   low asset growth, low leverage. For each: one-line mechanism, why it should survive IDX frictions (monthly
   turnover, top-200 liquidity), and the fin.db fields it needs plus their coverage today.
2. Cross-check every candidate against `HYPOTHESIS_REGISTRY.md` / `FAILURE_REGISTRY.md` / `DECISION_LOG.md`: say if it
   or a close relative was already tested, and cite the entry.
3. Multiplicity cost: family widening is allowed only by a formal governance amendment (never narrowing; invariant
   #12). State how each added arm moves the deflation bar from the current 3.300069 and the prior-only power at the
   D-112 floor, so the owner can see whether a wider family is still powered.
4. Recommend one of: widen now, wait for the E/P G0 result, or open a separate family. Do not file a D-entry or edit
   any registry.

## Deliverable
`docs/reports/ZCODE_WEDNESDAY_2026-10-28.md` (5001): each of K1–K4 as DONE / BLOCKED (why) / NOT RUN (why), the {FQ}
G0 numbers, the proposed D-entry text, files written, and commit hashes of both repos. Update the "Current status"
block in `TODO.md` to match.
