# ZCODE BRIEF — correction entry, then register C-003, pin its G1, run both G1s once (owner-approved)

**Issued:** 2026-10-29, by Claude (planner role). **Supersedes:** `ZCODE_BRIEF_C003_REGISTRATION_G1_2026-10-28.md`
(issued 10-28 09:46, **not started** — the afternoon went to the pre-open news-timing screen, D-117).
**Repos:** `~/10 Projects/idx-walkforward-5001` (`ops/hardening-2026-07-10`). **Push: HOLD.** Commit locally,
small commits. Systemd one-shot timers only.

## Owner approval
2026-10-28: "**Daftarkan**" — register C-003 (dividend-yield level, family {PY}) **before** the HYP-PM-0023 E/P G1
is run; then the E/P G1 once and the C-003 G1 once. 2026-10-29: "complete all step" — carry it out. Nothing else is
approved: no other registration, no re-run, no rescue, no change to any frozen file, no forward test started.

## What changed since the 10-28 brief (read before N1)
1. **D-117 took the number** the 10-28 brief earmarked. Next free, verified 2026-10-29: **D-118** (correction),
   **D-119** (registration), then consecutive. **HYP-PM-0024** is still next free (registry ends at 0023).
2. **The census in force is 614, not 615.** D-117, `ZCODE_NEWS_TIMING_SCREEN_2026-10-28.md` and `TODO.md` say
   "census unchanged at 615" and quote the bar at 616 (3.300988) — written as if C-003 were already registered.
   It is not: HYPOTHESIS_REGISTRY ends at HYP-PM-0023 (census 614). Bars recomputed 2026-10-29 from the D-064 §C
   integral: **614 → 3.300069, 615 → 3.300529**, 616 → 3.300988. C-003 registers at **615 → bar 3.300529**.
3. **D-117's first root cause is wrong.** app.log shows the 08:00 `news_fetch_premarket` job **completed on 33 of
   37 trading days** 2026-09-08 → 10-28 (misses: 10-12..10-14 during the OHLCV-repair incident, service up after
   08:00; 09-08 is the log-window edge). The 8/119 pre-open dates are explained by the second cause alone:
   `save_news_count`'s `INSERT OR REPLACE` at 17:00 erases the 08:00 rows. Before 09-08 the logs are rotated
   away, so the scheduler cause is "unknown before 09-08", not "fired on 8/119 days".

## Rules (unchanged from 10-28)
- Order is load-bearing: **N0 → N1 → N2 → N3 → N4.** No real-data G1 return of either arm may be computed before
  N2 is committed and pinned (C-003's G1 implementation must be fixed before E/P's outcome is seen).
- D-entries append-only, consecutive, "Approval authority: Owner, <date>". Registry rows appended;
  `FAILURE_REGISTRY.md` only for a FAILED arm. **Never edit an existing entry** — D-117 stays as written; N0
  supersedes the wrong statements.
- Each G1 runs **once**. Sensitivities are reported beside the primary, never substituted. A fail is final.
- Lifecycle: a pass is **not** VALIDATED (needs forward-test evidence via the receipt-bound `set_status()` path);
  record it as passing G1 and stop there. A fail is FAILED with its F-mode (F2 for a prediction failure).
- Research never imports execution modules; production DB read-only via `data.db.connect(read_only=True)`.
  Nothing heavy 21:05–06:30.

## N0. D-118 — correction to D-117 (superseding entry, no edit to D-117)
File `### D-118 · Correction to D-117 — census in force 614 (not 615); pre-open root cause is the 17:00 overwrite`,
Status RECORDED, Date 2026-10-29, Type correction, Approval authority: Owner, 2026-10-29. Three bullets:
- **Census:** D-117's "census unchanged at 615" and its would-be bar "3.300988 at 616" are superseded. The
  census in force on 2026-10-28 was **614** (HYP-PM-0023, D-115; C-003 unregistered). Correct would-be bar:
  3.300529 at 615. D-117's verdict (withdrawn, uncounted, no return read) is unaffected.
- **Root cause:** D-117 cause 1 ("the 08:00 job wrote on 8/119 days … scheduler not up") is superseded: the job
  completed on 33/37 trading days 09-08 → 10-28 (app.log, `grep -a` — logs .3/.5 contain binary bytes and a plain
  `grep` silently skips them). Cause 2 (17:00 `INSERT OR REPLACE`) explains the gap; no scheduler fix is needed.
  Before 09-08: unknown (logs rotated). Stopgap since 10-29: `P-M/news_timing/snapshot_premarket.py` (append-only
  daily copy, first capture `512b82b`, committed 08:33 before the open).
- **Construct defect for any re-freeze:** the crawl query `"<ticker> saham"` matches tickers that are common words.
  10-29 pre-open: PADA 14, LABA 9, BANK 6, DATA 3 = 32/107 headlines (30%) are not about the issuer (e.g. LABA →
  "Laba Per Saham Algoma Steel"). A re-frozen event must require the ticker code as a whole word in the headline.
Commit: `docs(governance): D-118 -- correction to D-117 (census 614; 17:00 overwrite is the root cause; ticker-word matches)`.
Also fix the two derived documents **by a dated note appended at their end** (they are reports, not registries):
`ZCODE_NEWS_TIMING_SCREEN_2026-10-28.md` and the TODO line (Claude already updated TODO on 10-29 — verify only).

## N1. Register C-003 as HYP-PM-0024 (D-119)
1. Registration record `P-M/dy/HYP-PM-0024_REGISTERED.md` from freeze §8 (`G0_FREEZE_DY_DRAFT_2026-10-28.md`, sha
   `2789ab21…` — verify the sha before using it; the file is the FINAL freeze despite its name): hypothesis, sign
   (positive), universe (top-200 KSEI mcap, price ≥ Rp 50), formation (monthly, 209 formations), book (EW top
   quintile of valid-yield names, ≥ 30 names, net D-082 cost), **bar per D-064 §C at census 615 = 3.300529**
   (E/P's frozen bar 3.300069 is not changed — non-retroactive), kill rule (t < bar, either half ≤ 0, or FM
   incremental over E/P/size/Parkinson-60/VOLEX t < 2), declared multiplicity debt (alpha_search_v2), and the
   G0 result (power 48.7% at 0.80%/mo).
2. One honest line: "MDE80 at the deflated bar ≈ 1.01%/mo net (the 0.61%/mo in the G0 JSON is the frozen
   report-only 2.487·SE formula, i.e. a plain 5% test)."
3. Registry row + {PY} family line; census **614 → 615**; D-119 for the registration.
Commit: `docs(research): HYP-PM-0024 registered -- {PY} dividend yield one arm, census 615 (D-119)`.

## N2. Build and pin `P-M/dy/g1_dy.py` — synthetic tests only, no real-data run
1. Implements exactly the registered G1: primary one-sided Newey–West t of the net monthly spread (top quintile vs
   the EW liquid book), lags as fixed in the freeze/registration (if not fixed there, use the {FQ} G1's rule and
   say so in D-119 — before any run); both halves; the Fama–MacBeth incremental t over E/P, log-size,
   Parkinson-60, VOLEX, using the {FQ} E/P signal built by the frozen {FQ} code (import it, don't re-derive).
2. Refuses to run unless `REG_SHA256` matches `HYP-PM-0024_REGISTERED.md`, all input pins match, and the
   registration exists. Writes a result JSON + log; prints nothing before the pin check passes.
3. Synthetic tests (fake connection / in-memory panels; scanner-safe pattern from `test_extract_dividends.py`):
   known-spread panel → known t; a half ≤ 0 → kill; FM collinear with E/P → incremental t < 2 → kill;
   unpinned → refuses.
4. Pin `REG_SHA256`, record the script sha256 in the registration file's pin line.
Commit: `feat(research): HYP-PM-0024 G1 script + tests; refuses until registration pinned (no real-data run)`.

## N3. HYP-PM-0023 ({FQ} E/P) G1 — once
Run `g1_fq_ep.py` once (verify its pins first; it refuses otherwise). Record: primary t vs its frozen bar
3.300069, kill verdict, every sensitivity (B/M, ROE, EW, −100% delisting row, era split 2021-07, without D-111
covered periods, USD excluded, top-100). Then:
- **Pass** → next free D-entry "passed G1"; registry status line updated by a superseding row; next stage =
  forward test, **not started** (owner decision).
- **Fail** → FAILED (F2), `FAILURE_REGISTRY.md` row, D-entry.
Commit result JSON + force-added log + the D-entry.

## N4. HYP-PM-0024 (C-003) G1 — once, after N3 is committed
Run `g1_dy.py` once. Same recording as N3. The FM-over-E/P separator runs as frozen whatever N3's verdict was.

## Deliverable
`docs/reports/ZCODE_G1_2026-10-29.md`: N0–N4 each DONE / BLOCKED (why), HYP ids, bars, registration and script
shas, both G1 results in full (primary, halves, FM, sensitivities), verdicts, D-numbers, census, files and commits.
Update the `TODO.md` status block. Plain statement at the top: passed / failed per arm, one line each.
