# ZCODE BRIEF — Pilot check, full {FQ} financials pull, PIT draft revision, push

**Issued:** 2026-10-21, by Claude (planner role). Owner: "delegate all task to zcode". **Owner approvals given
2026-10-21:**
- **A1. Full pull:** approved, weekend daytime only, after the pilot passes.
- **A2. Push:** approved for `ops/hardening-2026-07-10` after each item's tests pass.
- **A3. PIT rule:** ZCode proposes; the **owner approves**. Nothing is frozen and no D-entry is written until the
  owner says so.

**Repo:** `~/10 Projects/idx-walkforward-5001` (branch `ops/hardening-2026-07-10`). jurnal26 is not touched.
**Follows:** `ZCODE_BRIEF_FQ_BACKFILL_AND_LC_FILING_2026-10-21.md`. Your report is
`docs/reports/ZCODE_FQ_BACKFILL_LC_FILING_2026-10-21.md`, and your commits `3315e0c..af5d8ad` were checked by Claude:
hashes, D-109/D-110 placement, 57/57 tests, and the risk fix live since the 08:36 restart.

**Rules carried over (all still apply):**
- **No outcome reads on the fundamentals.** No return, factor, spread or IC, and no join to prices. Coverage and parse
  statistics only. This holds after the full pull too, until a frozen PIT rule **and** a {FQ} mechanism D-entry both
  exist.
- **Stockbit token:**
  - Read `.stockbit_token` only; never log in, never run `auto_token.py`.
  - Keep the script's time windows. No `--force` during weekday 08:30–19:00 or 21:50–23:30.
- **Never delete `.playwright_state/`.** It is the saved Stockbit login.
- **Files you must not touch:** `ZCODE_BRIEF_*`/`ZCODE_NOTE_*`, `HANDOFF.md` and the forward ledgers.
- **Restarts:** use only `scripts/safe_restart.sh` (none should be needed).

---

## Y1. Tonight's pilot (2026-10-21, 19:05 WIB, your scheduled run)

1. Confirm it ran.
   - If ZCode was closed and it did not run, run it yourself before 21:50 tonight.
   - If you miss that window too, run it Thursday 2026-10-22 after 19:00. That night's token expires
     2026-10-23 08:40, assuming the 08:40 refresh worked; check with `auto_token.py --check`, which reads only.
2. **Pilot pass criteria**, all required before Y2:
   - every one of the 10 names has the three statements;
   - BTEL and TRAM return their pre-delisting history;
   - the bank layout parses (BBCA, PNBS);
   - no 401, 403 or 429 responses;
   - parse failures are 0, or each one is explained.
3. Fill in the report's pilot table and the full-pull extrapolation, then commit.

## Y2. Full pull — Sunday 2026-10-25 daytime (approval A1)

**Why Sunday:** Saturday daytime has no valid token. Friday's 08:40 token expires Saturday 08:40, and the weekend
refresh runs at 21:40 on Saturday. Sunday daytime uses the Saturday 21:40 token, which is valid to Sunday ~21:40.
jurnal26's nightly tape backfill (21:05 → 06:30) is finished by then.

1. **At start:**
   - check the token's expiry with `auto_token.py --check`;
   - check that no jurnal26 backfill process is running;
   - check free disk space (`df -h ~/idx_external`).
2. **Run** `fetch` with no `--force`, using the default `--max-minutes 170` as the per-session cap. It is
   resumable: if the token or the cap stops it, resume the next allowed window, and never re-login.
3. **Stop and report**, without retrying in a loop, on any of:
   - 401 or 403;
   - a second 429 backoff;
   - more than 5% parse failures.
4. **Then:**
   - run `parse`;
   - pin the raw files and `fin.db` by sha256 in a manifest;
   - write a coverage table: tickers × quarters, how many of the 41 stale or delisted names have history, and bank
     versus non-bank layouts.
5. **Off-SSD copy.** Copy the raw store and manifest to `/mnt/storage2tb/idx-archive/stockbit_fin/` and verify the
   sha256 on both sides. Check `mountpoint -q /mnt/storage2tb` first. Leave the local copy in place.
6. Commit the script/doc changes and the coverage report (not the data). Push (A2).

## Y3. Revise the {FQ} PIT draft (approval A3: propose, don't freeze)

File: `P-M/data_acquisition/11_FQ_PIT_RULE_DRAFT_2026-10-21.md`. Write a revision (v2, same file or a `_v2`
sibling), with one recommendation and its reason per open question:

1. **H1 basis — Claude's finding.** The table's H1 lag of 30 Sep is the *reviewed* deadline plus one month. An issuer
   that publishes only an **audited** H1 has until 30 Sep itself, so the buffer is zero.

   Recommend one of these and say why:
   - (a) set H1's lag to 31 Oct for every issuer;
   - (b) lag by the attestation each issuer actually used, if a field anywhere in the data shows it.

   Give a sample count, if one is knowable, of how many H1s are audited.
2. **Buffer size** (OQ): justify +1 month against late filers. Use observable evidence, e.g. IDX
   late-filing suspension lists or announcements, if they can be reached. **Do not** use returns.
3. **COVID 2020 extensions.** Find the primary texts for the 2020 deadline relaxations (OJK and IDX) and give the
   extended lags for the affected periods.
4. **Restatement check:**
   - pick about 20 issuer-periods, mixing banks, large and small caps, and pre- and post-2015;
   - compare Stockbit's stored values against the originally published statements, using IDX or issuer PDFs you can
     reach;
   - report the difference rate.

   This compares data with data; it reads no outcome. Only do it after Y2's data exists.
5. **IDX texts blocked from this machine** (OQ-3). Record exactly which two texts are missing and what each would
   settle. The owner may fetch them by hand: list the URLs.
6. **End the revision with a "decisions for the owner" list.** Commit and push it. **Do not freeze it, and write no
   D-entry or {FQ} mechanism entry.**

## Y4. Push (approval A2)

Push `ops/hardening-2026-07-10` now, after re-running `pytest -q` on the test files your commits touched and the
four guard suites. That covers the 5 existing commits; push again after Y1, Y2 and Y3. Never force-push. If the
remote has moved, rebase onto it: no merge commits, and nothing of the owner's is lost. If the rebase conflicts,
stop and report.

## Deliverable

Extend `docs/reports/ZCODE_FQ_BACKFILL_LC_FILING_2026-10-21.md`, or add a dated sibling, with:
- Y1: pilot result against each pass criterion;
- Y2: run log, stop reasons, the coverage table, manifest sha256 and the archive-copy verification;
- Y3: the revision path plus the owner decision list;
- Y4: push hashes.

Each item is DONE, BLOCKED (why) or NOT RUN (why).
