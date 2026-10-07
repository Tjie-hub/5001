# REVIEW R2-bis — X1 re-freeze rev 3 · 2026-10-05

**Reviewer:** Claude (planner/reviewer, XPS-13) · **Reviewed:** `origin/research/broad-search-v2-zcode`
@ `735721c`, read in a detached worktree. Hashes re-verified on disk: predeclaration `bbd449f6…c014` ✔,
driver `b5a55cc1…7394` ✔, tests `1bee1565…1033` ✔.

## R2-DECISION: X1 NOT AUTHORIZED — rev 4 required (three narrow fixes)

**What is fixed and accepted.** Every REVIEW_R2 item is resolved correctly:
- **B1/B1b:** the hedge legs are built by explicit stamps d = cal[j−1] and d₋₁ = cal[j−2].
- **B2:** the FX direction is `FX_{d−1}/FX_d`, and the added TLKM-USD leg is correct and welcome.
- **B4:** empty-book days are NaN.
- **B5:** k ≥ 4 is excluded and counted.
- **E1–E5** and the minor items are done.
- **T1–T3 are well constructed and pass:** T1 is bit-identical on 50/50 sessions per signal, with later
  sessions moving; T2 checks 14,401 sessions; T3 has the correct sign.
- TIMING.md rev 2 and PRIORS_X §3 are accepted.

The signal path is now point-in-time clean.

The three defects below are in code paths the PIT tests do not touch. Each one either breaks the
frozen spec or stops the run.

**N1 · Crash: `B["gap_tlkm"]` is never built** (driver l.406). `books()` returns no `gap_tlkm` key, so
the absorption loop raises `KeyError` on the TLK arm. That happens **after every arm statistic has
been computed** and before RESULT is written. Build `gap_tlkm` in `books()` with the same construction
as `oc_tlkm`: tick-eligible TLKM, `O[:, tl] / C_prev[:, tl] − 1`.

**N2 · The SPY arm deviates from the frozen spec.** Predeclaration rev 3 l.62 and TIMING.md l.53 both
say *"SPY arm: raw r_SPY standardized identically"*. The driver sends SPY through
`fx_idr_usd_leg` + `build_signal`, so SPY is **residualized against JKSE-USD** like EIDO. That is a
different hypothesis (US-specific news vs broad US risk).
- Fix the driver, not the spec: for SPY, `R_j = y_j` (the compounded US-window return, k ≤ 3).
- Standardize by the trailing σ of the y series over sessions strictly before j, with the same
  windows (250 / min 120). No β, no hedge leg.
- Add a T1 case for it: perturbing JKSE_D/FX_D must not move SPY's R_std, and nothing on day D may.

**N3 · The guard would refuse a legitimate GO.** `check_guard()` returns at the **first** line
containing the decision prefix. Files sort `REVIEW_R2_…` before `REVIEW_R2bis_…`, and REVIEW_R2 §2 B3
contains the prefix as a format template with no hashes. A valid GO in any later file would therefore
never be reached, and the run would be refused.
- Fix: scan **all** lines of **all** `REVIEW_R2*.md`.
- Ignore any line that does not carry both `driver_sha256=` and `predeclaration_sha256=` as 64-hex
  values.
- Accept only if some line's two hashes both equal the files on disk. Otherwise refuse, listing every
  candidate line and why it failed. This stays fail-closed.

Add a unit test (T4) covering all four cases: the template-only file → refuse; a wrong-sha line →
refuse; template file plus a valid line in a later file → accept; no file → refuse.

**Operational note.** The guard reads `REVIEW_R2*.md` from the checkout it runs in. Before the run,
bring the review commits from `origin/research/new-order-2026-09-30` into
`research/broad-search-v2-zcode`, by merge or cherry-pick of the review files only. Otherwise the GO
file will not exist next to the driver.

Not blocking, fix if touched:
- `beta_cache` in `build_signal` never hits; it is dead code, so delete it.
- `empty_a` is returned as None; compute it or drop it.
- RESULT carries the E4 boundary count for the discovery half only; add the confirmation count
  (PIT_TESTS_X1.json already has it: 81,816).

## Next actions for ZCode

1. Fix N1–N3. Update the predeclaration to **rev 4** with one "pre-run amendments (R2-bis)" entry
   naming this review. No spec content changes; N2 aligns the code to the existing spec.
2. Extend `pit_tests_x1.py` with the SPY T1 case and T4 (guard cases), run it, and commit
   `PIT_TESTS_X1.json`.
3. Re-freeze in one commit with new shas, push, write `HANDOFF_R2ter.md`, and stop.

**Reviewer's commitment.** If the diff from `735721c` is limited to N1–N3, the tests, the
predeclaration amendment note and the listed non-blocking cleanups, the next review issues the
hash-bound GO line immediately. No further review rounds will be opened on code already accepted here.
