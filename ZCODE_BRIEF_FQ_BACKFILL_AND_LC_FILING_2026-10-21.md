# ZCODE BRIEF — File the {LC} entries, pilot the Stockbit financials backfill, draft the {FQ} PIT rule

**Issued:** 2026-10-21, by Claude (planner role, owner's request "resume prompt to zcode for next task") ·
**Repos:** `~/10 Projects/idx-walkforward-5001` (branch `ops/hardening-2026-07-10`); jurnal26 is not touched ·
**Follows:** your 2026-10-20 work: `P-M/lockup_lc/` (G0 stop rule fired), `P-M/data_acquisition/09_LOCKUP_PILOT…`,
`10_STOCKBIT_FIN_HISTORY_PROBE…` (HISTORY_FOUND), `scripts/stockbit_fin_backfill.py` (written, never run).
The 10-16 post-MSCI hardening brief is done (`b279b59`); do not reopen it.

**Rules that apply to every item:**
- **No outcome reads.**
  - Do not compute any return, factor score, spread or IC on the fundamentals.
  - Do not join them to prices.
  - Coverage and parse statistics only.
  - {FQ} has no mechanism D-entry and no frozen PIT rule yet. Anything read now would be another searched pattern
    (D-070 §1).
- **Do not push.**
- **Files and repos you must not touch:**
  - `ZCODE_BRIEF_*`, `ZCODE_NOTE_*` and `HANDOFF.md`;
  - the forward ledgers (`P-M/forward_*/ledger.json`);
  - the jurnal26 repo.
- **Never delete `.playwright_state/`.** It is `auto_token.py`'s saved Stockbit login. A cleanup removed it on
  10-20, and the 10-21 08:40 token refresh failed: Stockbit was down until the owner re-logged at 09:10.
- **Stockbit token use:**
  - Read `.stockbit_token` only; never log in and never run `auto_token.py`.
  - Keep the script's own time windows: weekdays 08:30–19:00 and 21:50–23:30 daily are refused.
  - Never pass `--force` during market hours.
- **Restarts:** 5001 runs from the working tree. Nothing here should need a restart; if something does, use only
  `scripts/safe_restart.sh`.
- **DB and tables:** open the production DB read-only. Add no new table to `data/walkforward.db`; the backfill
  writes only under its own `OUT_DIR`.

---

## Z1. File the two {LC} D-entries (do first — they are ready)

Source: `docs/research_programs/P-M/lockup_lc/DECISION_DRAFT_LC_2026-10-20.md`.

1. Check the log's last number. It is **D-108**, filed 2026-10-21 for a jurnal26 alert change, after your draft was
   written. So the entries are **D-109** ({LC} opened, mechanism accepted, G0 frozen) and **D-110** (G0 stop rule
   fired, WITHDRAWN). Append them after D-108, in the log's current style.
2. Before filing, re-verify both hashes and quote them in full in D-109/D-110:
   - `sha256sum G0_FREEZE_LC_LOCKUP_2026-10-20.md` = `03b40527fc136c00…`
   - `sha256sum g0_lockup_power.py` = `2f5a6ab4d7a89a24…`

   If either differs, stop and report. Do not re-run the G0.
3. **Registries:**
   - Withdrawn before registration means uncounted: the census stays at **613**, with no HYPOTHESIS_REGISTRY row.
   - Do **not** file it as FAILED (HYPOTHESIS_LIFECYCLE §3.1).
   - Mirror exactly what the D-094 and D-102 precedents did, or did not do, in `FAILURE_REGISTRY.md` and the census
     line.
4. **Commit** the log plus `P-M/lockup_lc/` and `P-M/data_acquisition/09_LOCKUP_PILOT_2026-10-20.md` +
   `lockup_pilot_2026-10-20.csv`, as `docs(governance): D-109/D-110 -- …`.

## Z2. Stockbit financials backfill: review, test, dry-run, 10-ticker pilot

Script: `scripts/stockbit_fin_backfill.py`. Probe output to reuse as test fixtures:
`out/stockbit_fin_probe_20261020_183349/`.

1. **Review the safety claims in the docstring against the code**, and fix any claim the code doesn't keep:
   - the DB is opened read-only, for the ticker list only;
   - writes go only under `OUT_DIR`, and `OUT_DIR` is gitignored;
   - it stops on 401/403, backs off then stops on 429, and stops before token expiry and at `--max-minutes`;
   - the time windows hold.
2. **Tests** (new `tests/test_stockbit_fin_backfill.py`, hermetic, no network):
   - the HTML-table parser on the probe's BBCA (bank layout), TLKM, BTEL and TRAM files: period columns, Indonesian
     account rows, IDR values, negative numbers in parentheses, and empty cells;
   - resumability: files already on disk are skipped;
   - the time-window refusal;
   - 401 stops the run.

   Run the new file plus `tests/test_architecture_boundary.py`, `tests/test_research_data_fence.py`,
   `tests/test_db_centralization.py` and `tests/security/test_secret_hygiene.py`.
   - **`data.db.connect`:** if the script opens SQLite outside `data/db.py`, either route it through
     `data.db.connect` or confirm the existing allowlist covers `scripts/`.
   - **Shrink-only allowlists:** do not add to any of them.
3. **`fetch --dry-run`**: report the universe size, how many delisted tickers it holds, and the planned GET count.
4. **Pilot:** `fetch --limit 10` tonight (2026-10-21) **after 19:00 and before 21:50 WIB**. Today's token is valid
   to 10-22 09:09. Then run `parse`. Pick the 10 to cover a bank, a non-bank large cap, a small cap, and at least two
   delisted names (BTEL, TRAM).
5. **Report** per ticker: quarters covered, accounts parsed, failures, and wall time per GET. Add the
   extrapolated full-pull time.
6. **The full pull is NOT authorised.** It is ~3,000 GETs on our token and waits on the owner's ToS call
   (probe doc, Next steps 1). Run it only if the owner says so in writing, and then only on a weekend daytime.

## Z3. Draft (do not freeze) the {FQ} point-in-time rule

The probe found no filing dates, so PIT must use the statutory-lag design (`06_PIT_FUNDAMENTALS_FEASIBILITY`).

1. Find the current OJK/IDX deadlines for quarterly, half-year (reviewed or not) and annual (audited) reports of
   IDX issuers, from primary sources. Cite each regulation by number, article and date. If the rule changed inside
   2008–2026, give each regime's dates.
2. Propose the conservative lag per period type, as the deadline plus a buffer. State the buffer and why.
3. Name the restatement limit (values as stored now, not as first reported), with a plan to cross-check a small
   sample against original filings.
4. Write it as `P-M/data_acquisition/11_FQ_PIT_RULE_DRAFT_2026-10-21.md`, status **DRAFT — owner review**. No
   freeze, no D-entry, no mechanism entry.

## Z4. Uncommitted files you didn't name

The working tree has uncommitted changes to `engine/risk_alert.py`, `engine/risk_score.py`,
`scheduler/scanner.py` and `tests/test_risk_live_event.py`, plus `scripts/probe_stockbit_fin_history.py`.
- **Yours:** finish, test and commit them with their own message.
- **Not yours:** list them in the deliverable and leave them alone.

## Deliverable

One report, `docs/reports/ZCODE_FQ_BACKFILL_LC_FILING_2026-10-21.md`, covering:
- the Z1 commit hash and D-numbers used;
- the Z2 review findings and fixes, the test result line, the dry-run numbers, and the pilot table with the
  full-pull extrapolation;
- the Z3 draft path and its open questions for the owner;
- Z4 as committed or left alone.

Each item is DONE, BLOCKED (why) or NOT RUN (why). Commit locally; do not push.
