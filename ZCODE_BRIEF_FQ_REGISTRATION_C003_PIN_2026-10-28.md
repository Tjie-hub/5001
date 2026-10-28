# ZCODE BRIEF — {FQ} E/P registration, C-003 freeze pin, then the single E/P G1 (owner-approved)

**Issued:** 2026-10-28, by Claude (planner role). **Repos:** `~/10 Projects/idx-walkforward-5001`
(`ops/hardening-2026-07-10`). **Push: HOLD.** Commit locally, small commits. Systemd one-shot timers only.

## Owner approval (2026-10-28) — exactly what it covers
Owner: "Approved recomend — delegate to zcode", with two explicit choices:
1. **{FQ}: register E/P alone** (HYP-PM-0023, census 613 → 614). B/M and ROE stay **G1 sensitivities only**. **No
   later widening of {FQ} with a valuation or profitability arm** (B/M, ROE, gross profitability, RNOA, CF/P): their
   G1 sensitivities will have been read, so a post-G1 arm would be outcome-conditioned. This supersedes K5's
   "widen after G1" recommendation (`FQ_FAMILY_WIDENING_MEMO_2026-10-28.md` §4).
2. **C-003 dividend yield: pin the freeze before the E/P G1 is read; dividends only** (no buyback / net-payout
   variant). Proposed defaults: floor 0.80%/mo, separate family **{PY}** (draft §6 Option B).
Also approved as recommended: **file the PEAD withdrawal D-entry** and the **{FQ} G0 D-entry**.
**Not approved here:** C-003 registration (owner decides after its G0), any other registration, any G1 other than
HYP-PM-0023's, any change to frozen files.

## Rules
- D-entries: append-only to `docs/roadmap/DECISION_LOG.md`, consecutive numbers from the next free one (D-113 if
  still free — check), each carrying "Approval authority: Owner, 2026-10-28". Never edit an existing entry.
- Registries: `HYPOTHESIS_REGISTRY.md` gains rows by appending/superseding only; `FAILURE_REGISTRY.md` untouched
  unless a G1 FAILS. Follow the HYP-PM-0022 / D-105 precedent for the registration record and any
  `research.knowledge` status write (the `set_status()` gateway; never VALIDATED without a forward-test receipt).
- Order is load-bearing: **no E/P G1 return may be computed before M3 below is resolved.**
- G0/G1 scripts keep their own guards (market hours, pins). Run each once. Stockbit: token only, no login.
- Research never imports execution modules; production DB read-only via `data.db.connect()`.

## M1. File the two pending D-entries
1. **PEAD withdrawal** — text from `docs/reports/ZCODE_TUESDAY_2026-10-27.md` §J2.2 (WITHDRAWN before
   registration, uncounted; no registry row).
2. **{FQ} E/P G0 passed** — text from `P-M/fq/DECISION_PROPOSAL_FQ_G0_2026-10-28.md` (pins and numbers already
   verified), number filled in.
Commit: `docs(governance): D-1xx/D-1xx -- PEAD G0 withdrawal; {FQ} E/P G0 passed`.

## M2. Register HYP-PM-0023 ({FQ} E/P, one arm)
1. Write the registration record (precedent: HYP-PM-0022 / D-105): hypothesis, sign (positive), universe,
   formation, bar 3.300069 at N = 614, G1 kill rule and pre-declared sensitivities exactly as frozen in
   `G0_FREEZE_FQ_EP_2026-10-26.md` §6 and D-112. Add the owner's no-widening clause (approval item 1) verbatim.
2. Append the `HYPOTHESIS_REGISTRY.md` row and update the P-M/{FQ} family line; census 613 → **614**.
3. D-entry recording the registration (family {FQ} = one arm; no-widening clause; census 614).
4. Pin `REG_SHA256` in `g1_fq_ep.py` to the registration record's sha256. **Do not run G1 yet.**
Commit: `docs(research): HYP-PM-0023 registered -- {FQ} E/P one arm, census 614`.

## M3. C-003: pin the freeze, run its G0 once
1. Turn `P-M/dy/G0_FREEZE_DY_DRAFT_2026-10-28.md` into the final freeze: dividends only; floor 0.80%/mo; family
   {PY} (Option B); **liquidity gate (b) price ≥ Rp 50 only** — same universe basis as the E/P arm (no ADV gate,
   no 2021-07 era break), which keeps the FM-over-E/P separator like-for-like. Remove the Option A text and the
   buyback mention except one line: "C-009 buyback: UNDERPOWERED standalone; not folded in (owner 2026-10-28)."
2. Pin its sha256 in `g0_dy_breadth.py::FREEZE_SHA256`. D-entry: {PY} family opened + C-003 G0 freeze pinned
   (freeze sha, script sha, input pins; census unchanged at 614).
3. Run the C-003 G0 **once** (coverage gates + placebo-SD power only, no returns), when its guard allows.
   - **Stop rule fires** → D-entry WITHDRAWN before registration, uncounted. M3 is resolved; go to M5.
   - **Passes** → commit the result, write a proposed registration text, and **STOP**: report to the owner for the
     C-003 registration go/no-go. **M5 waits** for that decision (so C-003's registration is not chosen after
     seeing E/P's G1).

## M4. Buyback
Mark C-009 in `search/02_RANKED_SHORTLIST_2026-10-28.md` as "UNDERPOWERED — not folded into C-003 (owner
2026-10-28)". No registry or D-entry (never registered). The IDX announcement pull stays an open owner item.

## M5. HYP-PM-0023 G1 — once, only after M3 is resolved
Run `g1_fq_ep.py` once (its guard verifies `REG_SHA256`). Report the primary result against bar 3.300069, the
kill rule verdict, and every pre-declared sensitivity — never substituted for the primary. Record the outcome per
the lifecycle (pass → next stage per `HYPOTHESIS_LIFECYCLE.md`, not VALIDATED; fail → FAILED with F-mode +
`FAILURE_REGISTRY.md` row + D-entry). If M3 ended at "passes", do not run M5; say so.

## Deliverable
`docs/reports/ZCODE_FQ_REGISTRATION_2026-10-28.md`: M1–M5 each DONE / STOPPED-FOR-OWNER / NOT RUN (why), D-numbers
filed, registration sha, C-003 freeze sha and G0 numbers, G1 result if run, files and commit hashes. Update the
`TODO.md` status block and the census figure wherever the TODO cites it.
