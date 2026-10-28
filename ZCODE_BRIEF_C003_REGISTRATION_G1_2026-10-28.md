# ZCODE BRIEF — register C-003, build + pin its G1, then run both G1s once (owner-approved)

**Issued:** 2026-10-28, by Claude (planner role). **Repos:** `~/10 Projects/idx-walkforward-5001`
(`ops/hardening-2026-07-10`). **Push: HOLD.** Commit locally, small commits. Systemd one-shot timers only.
Follows `ZCODE_BRIEF_FQ_REGISTRATION_C003_PIN_2026-10-28.md` (M1–M4 done; M5 held for this decision).

## Owner approval (2026-10-28)
"**Daftarkan**" — register C-003 (dividend-yield level, family {PY}) **before** the HYP-PM-0023 E/P G1 is run.
Then run the E/P G1 once and the C-003 G1 once. Nothing else is approved: no other registration, no re-run, no
rescue, no change to any frozen file, no forward test started.

## Rules
- Order is load-bearing: **N1 → N2 → N3 → N4.** No real-data G1 return of either arm may be computed before N2 is
  committed and pinned (C-003's G1 implementation must be fixed before E/P's outcome is seen).
- D-entries append-only, consecutive from the next free number (D-117 if free), "Approval authority: Owner,
  2026-10-28". Registry rows appended; `FAILURE_REGISTRY.md` only for a FAILED arm. Never edit an existing entry.
- Each G1 runs **once**. Sensitivities are reported beside the primary, never substituted. A fail is final.
- Lifecycle: a pass is **not** VALIDATED (needs forward-test evidence via the receipt-bound `set_status()` path);
  record it as passing G1 and stop there. A fail is FAILED with its F-mode (F2 for a prediction failure).
- Research never imports execution modules; production DB read-only via `data.db.connect()`. Nothing heavy
  21:05–06:30.

## N1. Register C-003 as HYP-PM-0024 (check the id is next-free)
1. Registration record `P-M/dy/HYP-PM-0024_REGISTERED.md` from freeze §8 (`G0_FREEZE_DY_DRAFT_2026-10-28.md`, sha
   `2789ab21…`; the file is the FINAL freeze despite its name): hypothesis, sign (positive), universe (top-200 KSEI
   mcap, price ≥ Rp 50), formation (monthly, 209 formations), book (EW top quintile of valid-yield names, ≥ 30
   names, net D-082 cost), **bar per D-064 §C at census 615** (state the number; E/P's frozen bar is not changed —
   non-retroactive), kill rule (t < bar, either half ≤ 0, or FM incremental over E/P/size/Parkinson-60/VOLEX
   t < 2), declared multiplicity debt (alpha_search_v2), and the G0 result (power 48.7% at 0.80%/mo).
2. Add one honest line: "MDE80 at the deflated bar ≈ 1.01%/mo net (the 0.61%/mo in the G0 JSON is the frozen
   report-only 2.487·SE formula, i.e. a plain 5% test)."
3. Registry row + {PY} family line; census **614 → 615**; D-entry for the registration.
Commit: `docs(research): HYP-PM-0024 registered -- {PY} dividend yield one arm, census 615`.

## N2. Build and pin `P-M/dy/g1_dy.py` — synthetic tests only, no real-data run
1. Implements exactly the registered G1: primary one-sided Newey–West t of the net monthly spread (top quintile vs
   the EW liquid book), lags as fixed in the freeze/registration (if not fixed there, use the {FQ} G1's rule and
   say so in the D-entry of N1 — before any run); both halves; the Fama–MacBeth incremental t over E/P, log-size,
   Parkinson-60, VOLEX, using the {FQ} E/P signal built by the frozen {FQ} code (import it, don't re-derive).
2. Refuses to run unless `REG_SHA256` matches `HYP-PM-0024_REGISTERED.md`, all input pins match, and the
   registration exists. Writes a result JSON + log; prints nothing before the pin check passes.
3. Synthetic tests (fake connection / in-memory panels; scanner-safe pattern from `test_extract_dividends.py`):
   known-spread panel → known t; a half ≤ 0 → kill; FM collinear with E/P → incremental t < 2 → kill;
   unpinned → refuses.
4. Pin `REG_SHA256`, record the script sha256 in a short D-entry or in the registration file's pin line.
Commit: `feat(research): HYP-PM-0024 G1 script + tests; refuses until registration pinned (no real-data run)`.

## N3. HYP-PM-0023 ({FQ} E/P) G1 — once
Run `g1_fq_ep.py` once. Record: primary t vs its frozen bar, kill verdict, every sensitivity (B/M, ROE, EW,
−100% delisting row, era split 2021-07, without D-111 covered periods, USD excluded, top-100). Then:
- **Pass** → D-entry "passed G1"; registry status line updated by a superseding row; next stage = forward test,
  **not started** (owner decision).
- **Fail** → FAILED (F2), `FAILURE_REGISTRY.md` row, D-entry.
Commit result JSON + force-added log + the D-entry.

## N4. HYP-PM-0024 (C-003) G1 — once, after N3 is committed
Run `g1_dy.py` once. Same recording as N3. The FM-over-E/P separator runs as frozen whatever N3's verdict was.

## Deliverable
`docs/reports/ZCODE_G1_2026-10-28.md`: N1–N4 each DONE / BLOCKED (why), HYP ids, bars, registration and script
shas, both G1 results in full (primary, halves, FM, sensitivities), verdicts, D-numbers, census, files and commits.
Update the `TODO.md` status block. Plain statement at the top: passed / failed per arm, one line each.
