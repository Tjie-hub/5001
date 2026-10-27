# ZCODE Tuesday 2026-10-27 — status report

Brief: `ZCODE_BRIEF_TUESDAY_2026-10-27.md`. Push is **HOLD** in both repos; everything below is local only.

| Item | Status |
|---|---|
| J1 {FQ} E/P G0 — what happened on 10-26 night | **pull finished (41/92 codes); G0 did NOT run — one-shot armed for 17:41 today** |
| J2 PEAD withdrawal paperwork | **DONE** (result committed `fc418ba`; D-entry text proposed below; registries clean) |
| J3 5001 restart after `d0fd245` | **DONE** — process was 4 days stale; restarted 08:48 via `safe_restart.sh`; one leftover found and fixed (`77ff4ae`) |
| J4.1 Auction backfill + today's fires | **DONE** — backfill wrote the 10-26 report; today's 08:50/08:59/09:02/09:05 fires all exit 0; API read-token check closed |
| J4.2 Index rebalance 2026-11-02 | **DONE (prepared, not applied)** — announcement found; change on branches `ba3fd29` (5001) / `01b0bbb` (jurnal26); switch note below |

## J1. {FQ} E/P G0 — the 10-26 night

1. **KSEI pull finished 19:05–19:12** (`~/idx_external/stockbit_fin/fq_ksei92_2026-10-26.log`): 123 of 276 requests
   saved → **41 of the 92 codes resolved** (153 missing/empty; 51 codes still without data). Parse wrote 248,756
   rows; fin.db now 9,001,748 rows, **998 tickers** (957 before).
2. **G0 never ran.** The 19:05 timer command was fetch + parse + stop-timer only; no G0 invocation was ever armed,
   and nothing in `journalctl` or `P-M/fq/` after 19:12.
3. **Blocker fixed so it can run:** `g0_fq_ep_breadth.py` checks fin.db against
   `~/idx_external/stockbit_fin/SHA256SUMS_2026-10-26.txt` ("written after the 92-code parse") — that file was
   never written, so G0 would have refused (`rc=3`). Written 08:46 in the established format (2,996 lines: full
   raw/ archive + fin.db + manifest; fin.db sha256 `caefb1a2…`). Pin preflight now returns **ALL PINS MATCH**.
4. **One-shot `zcode-fq-g0-20261027` armed for 17:41 WIB today** (same pattern as yesterday's PEAD run): runs
   `g0_fq_ep_breadth.py`, tees to `P-M/fq/g0_run_2026-10-27.log`, writes `P-M/fq/G0_RESULT_<stamp>.json`.
   The result files are **not committed yet** — commit them after the run and read the numbers there. No G1 run,
   no HYP-PM-0023 registration (owner go required).
5. **Proposed D-entry text (template — numbers land at 17:41; do not file):**

   > ### D-1xx · {FQ} E/P value G0 — [stop rule fired / passed]
   > **Status:** RECORDED · **Date:** 2026-10-27 · **Type:** G0 breadth/power · **Approval authority:** the frozen
   > stop rule (`G0_FREEZE_FQ_EP_2026-10-26.md`, sha `e14ab4d9…`; precedents D-087, D-094, D-097, D-102, D-110).
   > - **Run.** Once, 2026-10-27 17:41 WIB (timer `zcode-fq-g0-20261027`). Freeze sha verified; all five pinned
   >   inputs + fin.db sums verified before the run. [FILL: qualifying_months / formation_months, T_eff years,
   >   power vs the 20% minimum, stop rule verdict.]
   > - **Inputs.** fin.db @ sha `caefb1a2…` (998 tickers, post 92-code parse), KSEI monthly files, D-111 rule v3.
   > - **[If fired →]** Status: **WITHDRAWN** before registration, uncounted (never registered; no
   >   HYPOTHESIS_REGISTRY row). New-code coverage: 41 of 92 resolved codes enter the universe as data allows.

## J2. PEAD withdrawal — paperwork

1. **Committed `fc418ba`** — `docs(research): PEAD G0 power run 2026-10-26 -- stop rule fired`:
   `G0_RESULT_20261026T175314.json`, `events_pead_20261026T175314.csv`, `g0_run_2026-10-26.log`
   (force-added past the blanket `.gitignore` `*.log` rule, as the brief names it).
2. **Proposed D-entry text** (mirror of D-110; the D-number and the filing belong to the owner):

   > ### D-1xx · PEAD long top-SUE quintile G0: stop rule fired — WITHDRAWN before registration (uncounted)
   > **Status:** RECORDED · **Date:** 2026-10-26 · **Type:** G0 stop + withdrawal · **Approval authority:** the
   > frozen stop rule (`G0_FREEZE_PEAD_2026-10-23.md`; precedents D-087, D-094, D-097, D-102, D-110).
   > - **Run.** Once, 2026-10-26 17:53 WIB. Script `g0_pead_power.py` sha256 `ed589c6c…`; freeze sha `004fce27…`
   >   verified; snapshot `/mnt/storage2tb/idx-archive/wf_snapshot_20260929/walkforward-20260928-213012.db`
   >   rehashed (`db48e8d8…`).
   > - **Cohort.** 3,037 earnings rows → 2,788 usable est/rep; 2,391 eligible events after universe/liquidity
   >   filters; **506 top-SUE-quintile events over 159 months** (holdout 347 events / 112 months; recent 159 / 47).
   > - **Stop rule: FIRED.**
   >
   >   | Measure | Value |
   >   |---|---|
   >   | Per-event placebo sd | 17.4% |
   >   | SE over months | 0.90% |
   >   | MDE at 80% power | 3.74% |
   >   | Power at the 2.0% floor | **13.9%**, against the 20% minimum |
   >
   >   Reported, not the stop metric: holdout power 8.2%, recent 1.5%. Distinctness checks all passed (no flag vs
   >   hi52 / park60 / log_mcap / t1) — the arm is withdrawn on power alone.
   > - **Status: WITHDRAWN.** Never registered, so it is not counted. The census is unchanged and no
   >   HYPOTHESIS_REGISTRY row is added.
3. **Registries checked, not edited:** `HYPOTHESIS_REGISTRY.md` and `FAILURE_REGISTRY.md` each contain **zero**
   PEAD mentions — no registered row exists, consistent with "withdraw before registration".

## J3. 5001 restart check after `d0fd245`

1. **Stale confirmed:** `ActiveEnterTimestamp` 2026-10-22 16:20 vs commit 2026-10-26 14:35 — the audit changes
   were not live. Restarted **08:48:08 WIB** (outside market hours) via `scripts/safe_restart.sh`:
   `preflight OK: 53 jobs registered`, health OK, service active, `version dev-fc418ba`.
2. **Jobs verified in the boot log:** EOD Trade Plan 16:40 ✓, Premarket Firm 08:35 ✓, Forward-Test 18:30 ✓.
3. **Phase-5 BULL-watch: gone from the scheduler** (no `_add_job` registration anywhere; `run_phase5_bull_watch`
   stays importable per the commit). **One leftover found:** the boot *banner* line
   "📡 PHASE 5 BULL-WATCH: 17:10" survived `d0fd245` and the fresh boot printed it — misleading, since the job no
   longer exists. Removed in **`77ff4ae`** (takes effect at the next restart; the current process printed it once
   at 08:48 boot, cosmetic only). Health shows `job_count: 53`.
4. **`AGENT_FIRM_PROVIDER_ORDER=zai`:** present in `.env`; the app loads it at import
   (`config.py:16 load_dotenv(_BASE / ".env")`), so the live workers have it (a `/proc/<pid>/environ` check does
   not apply to dotenv-loaded vars). Positive boot-log confirmation will appear as
   `provider router built: mode=auto order=['zai']` on the first firm call (the router is built lazily; not yet
   in today's journal as of 09:15).
5. **pytest** `tests/test_architecture_boundary.py tests/security/test_route_policy.py`: **6 passed before and
   6 passed after** the restart.

## J4.1. Auction monitor — backfill and today's fires

1. The 10-26 18:30 backfill **ran and exited cleanly** (18:32:26, 8.0s CPU); `data/auction_reports/2026-10-26.md`
   exists and reads sensibly — 25 names, sensible prev/matched/auction-lots/09:15/09:30 fields, and Monday's
   re-check numbers appear verbatim (ARNA 2,786 / BMTR 2,527 / TOWR 5,580 auction lots). IEP is "n/a (not
   recorded)" — correct, since the 08:50 iep reads crashed that day.
2. **Today (10-27) all fires clean:** iep 08:50 Finished, match 08:59 Finished, post 09:02 and 09:05 Finished —
   first fully clean live day; the 09:30 post run will render today's report per the new wiring.
3. **API (Monday H1.5, closed):** `GET /api/auction?date=2026-10-26` with the read token via the `X-Token`
   header → **200** with the full report; without a token → **401**. (A `Bearer` header is *not* the app's
   scheme — it 401s too, which is correct.)

## J4.2. Index rebalance 2026-11-02 — prepared, not applied

**Announcement found** (the Monday "not yet announced" no longer holds): **Peng-00204/BEI.POP/10-2026**, issued
**26 Oct 2026**, effective **2 Nov 2026 – 29 Jan 2027** (BISNIS-27/MNC36/SMinfra18/IDXESGL run to 30 Apr 2027).
Source: the-signal.id (full lists, announcement number), corroborated by Kontan/Bisnis/invezgo 26-Oct coverage.
idx.co.id remains unreachable from this machine (owner-browser list item).

| Index | Adds | Removes |
|---|---|---|
| IDX30 | ISAT, PTBA | PGEO, UNVR |
| LQ45 | SMGR | SCMA |
| IDX80 | AALI, TINS, TKIM | HEAL, MIKA, SMRA |

(SCMA leaves LQ45 but **stays in IDX80**. Weight notes: BBRI cut to the 15% IDX30 cap and BBCA at it; in IDX80
BBCA/BBRI/BMRI at the 9% cap.)

**Prepared on branches (not merged; idx_tickers flags untouched — the 3 Aug–30 Oct sets stay live):**
- 5001 `ops/idx-rebalance-20261102` = **`ba3fd29`**: `data/fetcher.py` lists + header, test docstring; shape test
  2 passed; programmatic set-diff against HEAD verified exactly the six adds / five removes above.
- jurnal26 `idx-rebalance-20261102` = **`01b0bbb`**: `tape_backfill.py` IDX30 + the dated pin in
  `test_tape_backfill.py` (it asserted the July signature "DEWA in, PTBA out"); 5 passed.

**Switch instructions — Monday 2026-11-02, before 08:50 WIB (or Sunday evening; outside market hours).**
Written instructions rather than a one-shot timer: both trees are HOLD-push, carry uncommitted cron ledger
appends, and an unattended `git merge` on a dirty tree is riskier than a five-step checklist.

1. 5001: `git checkout ops/hardening-2026-07-10 && git merge ops/idx-rebalance-20261102`
   (cherry-pick `ba3fd29` if the branch has diverged).
2. Update `idx_tickers` flags in place, saving the old ones first (the `91cc4bb` pattern): dump
   `ticker,in_idx30,in_lq45,in_idx80` to `~/scratch/idx_tickers_flags_before_2026-11-02.json`, then set the flags
   from `data.fetcher`'s new IDX30/LQ45/IDX80 (writes only via `data.db.connect()`).
3. `scripts/safe_restart.sh`; confirm health `version` = new HEAD and `job_count` 53.
4. jurnal26: `git checkout main && git merge idx-rebalance-20261102`; the one-shot timers import fresh each run,
   but `jurnal26.service` (Flask, port 5004) imports the module at boot — restart it too
   (`systemctl --user restart jurnal26`) outside market hours.
5. Run `pytest -q tests/test_index_constituent_lists.py` (5001) and `test_tape_backfill.py` (jurnal26) after.

## Files and commits (all local; push HOLD)

- 5001 `ops/hardening-2026-07-10`: `fc418ba` (PEAD G0 outputs), `77ff4ae` (stale banner fix), this report +
  TODO.md update (this commit). Branch `ops/idx-rebalance-20261102`: `ba3fd29`.
- jurnal26 `main`: unchanged today; branch `idx-rebalance-20261102`: `01b0bbb`. (`logs/` untracked, as before.)
- Outside the repos: `~/idx_external/stockbit_fin/SHA256SUMS_2026-10-26.txt` written (2,996 lines); one-shot timer
  `zcode-fq-g0-20261027` armed for 17:41.
- `forward_fade` / `forward_regime` `ledger.json` cron appends remain uncommitted by design (10-26 09:30/09:35).

## Open after this report

1. 17:41 {FQ} G0 result → commit `G0_RESULT_*.json` + `g0_run_2026-10-27.log`, fill the D-1xx template above.
2. {FQ} registration (HYP-PM-0023) + any G1 — separate owner go (D-112).
3. PEAD D-entry above — owner files or amends.
4. 2026-11-02 switch per §J4.2.
5. Push decision for both repos (HOLD; 5001 now 20 ahead, jurnal26 8 ahead).
