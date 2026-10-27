# ZCODE BRIEF — C-003 dividend-yield level: build the G0 (power/coverage only), propose the freeze

**Issued:** 2026-10-27, by Claude (planner role). Owner: "approve and delegate the task for zcode".
**Repos:** `~/10 Projects/idx-walkforward-5001` (`ops/hardening-2026-07-10`). **Push: HOLD.** Commit locally.
**Scheduling:** systemd one-shot timers only. Run after, and independent of, `ZCODE_BRIEF_WEDNESDAY_2026-10-28.md`.

## What the owner approved, and what not (read first)
Approved (recorded in the report, nothing else): **take C-003 (dividend-yield level, `search/cand/SKEL-C-003`) forward
as the next candidate, sequenced after the {FQ} E/P G0**, as ZCode's ranked shortlist recommended.
**Not approved, still the owner's:** registration (HYP id, census 613 → 614), any D-entry, the G0 freeze pin, the
0.80%/mo floor, and the family question (widen {FQ} vs a separate Payout family). The owner's "approve" is not a
substitute for those; propose text for each and wait for an explicit pin.
C-001/C-006 (KSEI foreign / MF-PF share) and C-002 (cap proximity) are **not** part of this brief.

## Rules
- G0 is **coverage + power only**: no post-formation return, spread, t-stat, IR or P/L of any dividend-yield sort may
  be computed or looked at. If a step seems to need one, stop and ask.
- The skeleton cites an in-repo prior (alpha_search_v2, t 2.46–4.11, "multiplicity debt"). That is a prior result,
  not evidence for this arm: do not re-run it, do not re-read its outcomes, and state in the freeze draft that it
  is disclosed debt and not used to choose the floor, universe or sign.
- Frozen stay frozen: {FQ} G0 freeze (sha `e14ab4d9`) and the 10-26 `SHA256SUMS` it pins, PEAD freeze, jurnal26 watchers.
- Production DB read-only via `data.db.connect()`. Research never imports execution modules. Stockbit: token file
  only, no login, stop on 401/403/429, nothing heavy 21:05–06:30.
- Do not edit `HYPOTHESIS_REGISTRY.md`, `FAILURE_REGISTRY.md`, `DECISION_LOG.md`.

## L1. Overlap re-check (before building anything)
D-077 tested dividends as an **event study** (F2); other dividend work sits in the exclusion index. Write a one-page
note `P-M/dy/00_OVERLAP_CHECK_2026-10-28.md`: exactly how the **level** sort (TTM yield, monthly, top-200) differs from
every dividend row in `00_EXCLUSION_INDEX`, citing the entries. If it is a re-skin of a closed arm, say so and stop;
do not proceed to L2.

## L2. Dividends-paid extraction (local compute only)
1. From `fin.db` cash-flow, extract dividends paid per ticker-period, with the **point-in-time** rule of D-111 v3
   (nothing visible before its filing availability; next-trading-day shift D11; off-quarter fiscal years excluded;
   the late-filer list withholds).
2. Handle currency (the USD-reporter magnitude rule already used for {FQ}), splits/rights issues (reuse the {FQ}
   rule, do not invent a new one), and sign conventions. Write the extraction script with synthetic tests
   (pattern of `g0_fq_ep_breadth.py` + its 52 tests).
3. Output a coverage table: dividends-paid line coverage over panel name-months (top-200, ADV ≥ Rp 1bn), by year.

## L3. G0 script + freeze DRAFT (propose-only)
1. `P-M/dy/g0_dy_breadth.py`: refuses to run until a freeze is pinned (sha), verifies every input hash, computes
   only (i) dividends-paid coverage ≥ 60% of panel name-months and (ii) prior-only power at the **proposed** floor
   0.80%/mo using placebo/noise SD, not returns of the sort, over the 209 formations at bar 3.300069 (census 613 + this
   arm). State the exact SD source, as the PEAD/{FQ} G0s did.
2. `G0_FREEZE_DY_DRAFT_2026-10-28.md`: universe, formation, PIT rule, floor, bar, stop rule (floor below 0.60%/mo or
   coverage failure → stop, uncounted), data bindings, and **both** family options with their deflation cost, as
   text for the owner. Do not pin it, do not run the G0.
3. Also draft, as text only: the registration text for the arm (family left blank) and a D-entry proposal.

## L4. Dependency on {FQ} G0 (tonight 17:41)
Read only the **breadth/stop-rule outcome** of the {FQ} E/P G0 once it lands. State in the report whether the FM-over-E/P
separator is measurable (E/P arm alive) or C-003 stands alone (E/P stopped), and how that changes the family option.

## Deliverable
`docs/reports/ZCODE_C003_DY_2026-10-28.md`: L1 verdict, L2 coverage table and test counts, L3 files, the {FQ} G0
dependency line, the open owner decisions (pin, floor, family, registration) listed as questions, files written and
commit hashes. Update the "Current status" block in `TODO.md`. Commit small:
`docs(research): C-003 dividend yield -- <step>`.
