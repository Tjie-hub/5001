# ZCODE report — {LC} D-entries, Stockbit financials backfill, {FQ} PIT rule draft (2026-10-21)

Brief: `ZCODE_BRIEF_FQ_BACKFILL_AND_LC_FILING_2026-10-21.md`. All commits local; nothing pushed.

---

## Z1. {LC} D-entries — DONE

- **Commit `3315e0c`** — `docs(governance): D-109/D-110 -- …`, 8 files (DECISION_LOG + `P-M/lockup_lc/`
  complete + `09_LOCKUP_PILOT_2026-10-20.md` + `lockup_pilot_2026-10-20.csv`).
- **D-numbers:** D-109 ({LC} opened, mechanism accepted, G0 frozen) and D-110 (G0 stop rule fired,
  WITHDRAWN), appended after D-108 — the log's last number was indeed D-108.
- **Hashes re-verified before filing, quoted in full in the entries:**
  - `G0_FREEZE_LC_LOCKUP_2026-10-20.md` → `03b40527fc136c006e7fae25911c3cdea5cf13bbe873eb733b84470f46811f7e`
  - `g0_lockup_power.py` → `2f5a6ab4d7a89a246236d220f982e9430ffc336a0e11a185eb7dcd98851d0386`
  - Both also pinned in `G0_RESULT_20261020T185556.json`; every draft number (cohort 226, sd 25.3%,
    SE 2.17/2.80%, MDE 11.6%, power 0.49%, stop fired) re-checked against that artifact before filing.
- **Registries:** census stays **613**; no `HYPOTHESIS_REGISTRY.md` row; no `FAILURE_REGISTRY.md` row —
  mirroring exactly what D-094 and D-102 (both WITHDRAWN-before-registration) did and did not do.
  Not filed as FAILED (HYPOTHESIS_LIFECYCLE §3.1).
- No outcome was read at any point; the G0 was not re-run.

## Z2. Stockbit financials backfill — review DONE, tests DONE, dry-run DONE, pilot DONE 5/5 (2026-10-22)

### Review findings (docstring claims vs code)

Claims verified as kept: token read-only usage (no login, no `auto_token`, no refresh — `read_token()`
is the only token access and it never logs the token); production DB opened `mode=ro` for
`SELECT DISTINCT ticker` only (fallback path also read-only); writes only under
`OUT_DIR = ~/idx_external/stockbit_fin` (outside the repo, so the gitignore requirement holds trivially;
the probe outputs under `out/` are covered by `.gitignore` line 36); immediate stop on 401/403 with no
re-login; 429 → 60/120/240 s backoffs ×3, then recorded as an error with the 5-consecutive-error stop;
per-GET stop at token expiry −5 min plus pre-run refusal at <10 min; `--max-minutes` deadline checked
per iteration; the two blocked windows (weekday 08:30–19:00, daily 21:50–23:30) enforced both pre-run
and per-iteration, so a run that crosses into a window stops itself; 1.5 s `RATE_DELAY` between GETs.

Two defects found and fixed in `scripts/stockbit_fin_backfill.py` (both mine to fix, commit `820ff98`):
1. **`to_number` had no negative-parentheses handling.** Verified across all 5 probe fixtures (incl.
   delisted BTEL/TRAM): `data-raw` always carries signed floats or `-`, and no shown value cell uses
   parentheses — so no current data path was affected — but the parser falls back to the shown text
   when `data-raw` is absent, where `(1,234)` would have silently parsed as `None`. Added.
2. **The `universe()` fallback leaked a DB handle:** `with connect(...) as c:` commits/rolls back but
   never closes (the exact pattern `data/db.py`'s docstring warns about; the 2026-10-13 1,012-handle
   incident). Routed through `data.db.transaction`, which closes.

`data.db.connect` question: the script's two direct `sqlite3.connect` calls (live DB read-only in
`universe()`, private `fin.db` under OUT_DIR in `parse()`) are **covered by the existing centralization
exemption** — `tests/test_db_centralization.py` states "research/ and scripts/ are deliberately out of
scope (offline tooling)" and scans only production scopes. No allowlist touched (shrink-only rule held).

### Tests — DONE

New `tests/test_stockbit_fin_backfill.py`, hermetic (no network; the 401/expiry tests stub `requests`):
parser on the probe's BBCA (bank layout)/TLKM/BTEL/TRAM files — period columns and bounds (BBCA
(2008,1)→(2026,2) 74 q; TLKM (2007,4)→(2026,2) 75 q; BTEL (2007,4)→(2025,3) 72 q; TRAM
(2008,1)→(2019,3) 47 q), Indonesian/English account names from `data-lang-0/1`, IDR values from
`data-raw`, negatives (BTEL COGS Q4-2007 = −382,143,230,938), parentheses unit cases, empty cells
(`-` → None) and the shown-n/a-vs-raw-0.0 override, derived-section split; resumability (`done_set`:
saved files + manifest 404/empty count as done, a 200-without-file does not; dry-run skip counts);
time-window refusal (all boundary minutes) and refusal-before-token-read; 401 stops after exactly one
GET with nothing written; <10-min token refusal before any GET.

**Result line: `27 passed in 0.90s`** (probe-file tests skip cleanly if `out/` is absent). Named guard
suites: `tests/test_architecture_boundary.py`, `tests/test_research_data_fence.py`,
`tests/test_db_centralization.py`, `tests/security/test_secret_hygiene.py` — **`15 passed in 5.48s`**.

### Dry-run — DONE (10:16 WIB)

- **Universe: 959 tickers** (all four-letter; live `ohlcv` 959, pre-2021 history pickle 541 — a strict
  subset, so no pickle-only names).
- **Planned GETs: 2,877** (959 × income/balance/cashflow), 0 already done, estimated ~120 min at
  1.5 s + 1 s latency.
- **Delisted measure: 41 tickers** whose last `ohlcv` bar is >90 days stale as of 2026-10-21 (method:
  last-bar age; e.g. BTEL and TRAM both end 2026-07-17). Note: `idx_tickers.status='inactive'` has 14
  names but none of them are in the pull universe — the 41-staleness count is the honest number here.
  Delisted coverage in the pilot comes from BTEL/TRAM regardless.

### Pilot — DONE 19:05–19:07 WIB (scheduled automation, ran without --force, token valid to 10-22 09:09)

| Ticker | Role | Quarters covered | Accounts (rows) | Failures | Wall time/GET |
|---|---|---|---|---|---|
| BBCA | bank, mega | Q1 2008 → Q2 2026 | 225 | 0 | 1.63 s |
| TLKM | non-bank large | Q4 2007 → Q2 2026 | 229 | 0 | 1.63 s |
| ASII | non-bank large | Q1 2008 → Q2 2026 | 255 | 0 | 1.63 s |
| KIJA | mid cap | Q1 2008 → Q2 2026 | 215 | 0 | 1.63 s |
| TOTO | small cap | Q1 2008 → Q2 2026 | 188 | 0 | 1.63 s |
| PNBS | small regional bank | Q4 2011 → Q2 2026 | 188* | 0 | 1.63 s |
| PGEO | 2023 IPO, no-lock-up | Q4 2019 → Q2 2026 | 179 | 0 | 1.63 s |
| CUAN | 2023 IPO, no-lock-up | Q4 2021 → Q2 2026 | 215 | 0 | 1.63 s |
| BTEL | delisted telco | Q4 2007 → Q3 2025 (delisted) | 195 | 0 | 1.63 s |
| TRAM | delisted small | Q1 2008 → Q3 2019 (delisted) | 237 | 0 | 1.63 s |

Selection used `--tickers` (the 10 deliberate picks below) rather than bare `--limit 10`, because
`--limit` takes the alphabetically first N of the remaining set and would not have covered the
bank/large/small/delisted mix the brief requires. Full-pull extrapolation (after the run, 2026-10-22): 30 GETs / 49 s wall = 1.63 s per GET; 2,847 GETs remaining × 1.63 s ≈ 77 min — one Sunday 09:05 session covers the pull inside the 170-min cap; ≈ 12.0M rows expected.

**Full pull AUTHORISED (A1, owner 2026-10-21): Sunday 2026-10-25 daytime only, after the pilot passed 5/5** (executed by the `fq-pilot-20261022` systemd timer 2026-10-22 19:05, 30/30 HTTP 200, 125,192 rows, 0 parse failures; the 10-21 19:05 ZCode automation attempt died on a Z.ai 429 quota error before any GET). Armed as two one-off systemd timers (see `docs/reports/ZCODE_FQ_FULL_PULL_2026-10-21.md` §Y2). *PNBS caveat: parses fully but its stored rows are the generic (non-bank) template — the coverage table's bank split keys on Interest Income presence.*

## Z3. {FQ} PIT rule draft — DONE (draft only)

`docs/research_programs/P-M/data_acquisition/11_FQ_PIT_RULE_DRAFT_2026-10-21.md` — status
**DRAFT — owner review**. No freeze, no D-entry, no mechanism entry; no outcome read.

Content: the three OJK regimes inside 2007–2026 (Kep-36/PM/2003 → Kep-346/BL/2011 / Peraturan X.K.2
[primary text verified, ojk.go.id] → POJK 14/POJK.04/2022 [verified]; annual = end of month-3 audited,
semi-annual = month-1/2/3 by attestation, quarterly = exchange-level only), the IDX I-E layer
(Kep-00087/BEI/12-2025, effective 12 Dec 2025; quarterly unaudited due end of following month), the
proposed conservative lags (Q1 → usable 31 May, H1 → 30 Sep, Q3 → 30 Nov, FY → 30 Apr; +1 month
buffer, reasons stated), the restatement limit (values as stored, not as first reported) with a
≈20-case cross-check plan, and open questions **OQ-1..OQ-6** for the owner (buffer size, H1
attestation basis, two primary texts still to pull — idx.co.id blocks this box, the 2020 COVID
relaxations, the cross-check go-ahead, the freeze path).

## Z4. Uncommitted files — DONE

- **Committed (mine):**
  - `1e0af2e` — pre-open market-risk fix: `ihsg_move` now counts only the date's own IHSG bar
    (provisional intraday still counts), pre-open alerts label the previous session's move as such and
    it never sets a shock floor; `engine/risk_alert.py`, `engine/risk_score.py`, `scheduler/scanner.py`,
    `tests/test_risk_live_event.py`. Tests: 15/15 in the file, 65 passed across `-k risk`. (5001 runs
    from the working tree, so this fix has been live since 2026-10-21 morning; no restart needed.)
  - `ef51c7b` — `scripts/probe_stockbit_fin_history.py` + `10_STOCKBIT_FIN_HISTORY_PROBE_2026-10-20.md`
    (the 10-20 probe work unit, referenced by the backfill).
  - `820ff98` — `scripts/stockbit_fin_backfill.py` + `tests/test_stockbit_fin_backfill.py` (Z2 review
    fixes + tests; see above).
- **Left alone (not mine / do-not-touch):** `ZCODE_BRIEF_P0_P1_GROUND_TRUTH_2026-09-30.md`,
  `ZCODE_BRIEF_P3_EXECUTION_MODEL_FIX_2026-09-30.md`, `ZCODE_BRIEF_P4_EVIDENCE_HONESTY_2026-09-30.md`,
  `ZCODE_NOTE_MIMOSA_CORRECTION_AND_REDIRECT_2026-09-30.md`,
  `docs/research_programs/P-M/ZCODE_BRIEF_DATA_ACQUISITION_SCOPING_2026-09-30.md` (mode-only changes),
  `HANDOFF.md`, `ZCODE_BRIEF_FQ_BACKFILL_AND_LC_FILING_2026-10-21.md`,
  `ZCODE_BRIEF_POST_MSCI_HARDENING_2026-10-16.md`, and the three forward ledgers
  (`forward_exclusion`, `forward_fade`, `forward_regime` — live J4 recorder output, +~2,600 lines).

## Notes

- The Mimosa pre-commit hook returned an incomplete scan (`scanner_enobufs`, its known failure mode
  here) on the Z1 commit; per its compatible-policy message the commits proceeded without a
  project-safety claim being made.
- Nothing was pushed; `.playwright_state/` untouched; no login or `auto_token.py` run at any point;
  `--force` never used; no new table in `data/walkforward.db`; the backfill wrote only under
  `~/idx_external/stockbit_fin`.
