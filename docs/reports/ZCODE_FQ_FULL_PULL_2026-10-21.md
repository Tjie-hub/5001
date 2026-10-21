# ZCODE report — full {FQ} pull, pilot check, PIT revision, push (2026-10-21 → 2026-10-25)

Brief: `ZCODE_BRIEF_FQ_FULL_PULL_AND_PIT_REVISION_2026-10-21.md` (owner approvals A1 full pull ·
A2 push · A3 propose-only PIT). Companion to `ZCODE_FQ_BACKFILL_LC_FILING_2026-10-21.md`.
All rule carry-overs held: no outcome reads on the fundamentals, token file read-only, no login,
no `auto_token.py` except its read-only `--check` where the brief names it, no `--force`, no restart.

---

## Y4. Push — DONE (2026-10-21 10:59 WIB)

- Test gate re-run before pushing (files the 5 commits touched + the four guard suites):
  `tests/test_risk_live_event.py`, `tests/test_stockbit_fin_backfill.py`,
  `tests/test_architecture_boundary.py`, `tests/test_research_data_fence.py`,
  `tests/test_db_centralization.py`, `tests/security/test_secret_hygiene.py` —
  **57 passed in 3.90s** (same count the planner verified).
- Remote had not moved (0 behind). Fast-forward push, no force:
  `ede89c7..af5d8ad  ops/hardening-2026-07-10 -> ops/hardening-2026-07-10`;
  `git ls-remote` confirms origin at **af5d8ad**.
- Pushed set: `3315e0c` (D-109/D-110), `1e0af2e` (pre-open risk fix), `ef51c7b` (probe + doc),
  `820ff98` (backfill + tests), `af5d8ad` (PIT draft + first report).
- Pre-flight for Y2 done 10:59: `/mnt/storage2tb` mounted (453G free), local `/` 111G free,
  `~/idx_external/stockbit_fin` not yet created (the pilot creates it tonight).

## Y1. Tonight's pilot — NOT RUN YET (scheduled; window 19:00–21:50 WIB)

- The 19:05 WIB automation (`automation-1639d2f4`) runs the 10-name fetch + parse and fills the
  pilot table in the companion report. A 19:20 WIB validation automation (`automation-1639d2f4`
  follow-up, this session) confirms it ran — or runs it itself before 21:50 — then checks the five
  pass criteria, updates the "full pull NOT authorised" line for A1, commits and pushes.
- **Pass criteria (to be recorded here):** (1) all 10 names × 3 statements; (2) BTEL/TRAM
  pre-delisting history; (3) bank layout parses (BBCA, PNBS); (4) no 401/403/429; (5) parse
  failures 0 or each explained. — pending.

## Y2. Full pull — NOT RUN YET (scheduled Sunday 2026-10-25 09:05 WIB, approval A1)

- Per-session cap `--max-minutes 170`; resumable within allowed windows; stop-and-report (no retry
  loop) on 401/403, a second 429 backoff, or >5% parse failures. Then parse, sha256 pin manifest,
  coverage table (tickers × quarters, the 41 stale/delisted names, bank vs non-bank layouts),
  off-SSD copy to `/mnt/storage2tb/idx-archive/stockbit_fin/` with two-sided sha256 verification.
  Commit (code/docs only, not data) and push. — pending; will record run log, stop reasons,
  coverage table, manifest sha256, archive verification.

## Y3. PIT draft revision v2 — NOT RUN YET (after Y2's data exists)

- Will cover: H1 audited-vs-reviewed lag recommendation (with any knowable audited-H1 sample count),
  +1-month buffer justification from late-filing evidence, COVID-2020 primary texts and extended
  lags, the ≈20 issuer-period restatement check against original filings (data-with-data only),
  the blocked-texts record with URLs, and a decisions-for-the-owner list. Propose only — no freeze,
  no D-entry, no {FQ} mechanism entry. Commit and push. — pending.
