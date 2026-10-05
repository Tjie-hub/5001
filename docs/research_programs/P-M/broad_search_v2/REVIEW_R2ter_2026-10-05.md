# REVIEW R2-ter — X1 re-freeze rev 4 · 2026-10-05

**Reviewer:** Claude (planner/reviewer, XPS-13) · **Reviewed:** `origin/research/broad-search-v2-zcode`
@ `c8a28aa` (diff from `735721c`). Hashes re-verified from the commit objects: predeclaration
`994f21a9…f47c5` ✔, driver `ea7cf68c…77c05b` ✔, tests `a0c15260…32406` ✔. All three match
`PREDECLARATION_X1_OVERNIGHT.sha256`.

## Decision

R2-DECISION: X1 GO driver_sha256=ea7cf68c99a22cc39d6033dc9c52cde2ee284ee4733396897c33c4534977c05b predeclaration_sha256=994f21a9e8256d35d5b665845bb9fb072e90551062eb97290b3a29e969bf47c5

The GO authorizes **one run** of the rev-4 driver, under the frozen rules (stop rule, the crash-only
re-run rule, census 555 + 6, bar 3.2745). It does **not** authorize reading the holdout (§4).

## 1 · Diff check against REVIEW_R2bis

- **N1 ✔.** `gap_tlkm` is built in `books()` with the same eligibility and construction as `oc_tlkm`.
- **N2 ✔.** SPY takes `build_signal(…, residualize=False)`: raw compounded US-window y, σ from y
  values strictly before p (each value is appended after use), no β, no hedge leg. T1-SPY passes.
- **N3 ✔.** The guard scans every line of every `REVIEW_R2*.md`, skips candidates without two
  64-hex shas, and accepts only a full disk match. T4 passes 4/4, and the accept case resolves to
  the later file as intended.
- **Cleanups ✔.** Leftover dead code in the residualized path (an unused `sig` dict filled in the
  first loop) is harmless and does not block.
- Review-file cherry-picks (`95fbf18`, `339a8f4`) are content-identical to origin.

## 2 · ERRATUM — the "beyond the review" disclosure is wrong; no such change occurred

Predeclaration rev 4, the driver docstring ("EXTRA") and HANDOFF_R2ter all state that rev 3's
`build_signal` used `ys_all = y_map[p][1]` (the session count) and that rev 4 fixed it to
`y_map[p][0]`.

**That is false.** `git show 735721c:…/screen_x1_overnight.py` l.147 reads
`ys_all = np.array([y_map[p][0] for p in pair_sessions])`, and in the rev-4 diff that line is
**unchanged context**. The adjacent, unused line `ks_all = {p: y_map[p][1] …}` was deleted, which is
probably what was misread.

Consequences:
- **No signal change happened.** The EIDO/TLK β regression was correct in rev 3 and is identical
  in rev 4. The disclosure's claim "this changes the EIDO/TLK signal materially" is void.
- The frozen documents carry this incorrect statement. They are **not** re-frozen for it, because it
  is narrative and changes no computation; re-freezing for a comment would only burn another round.
  **This erratum is the correcting record.**
- **Mandatory:** `VERDICT_X1_OVERNIGHT.md` and HANDOFF_R3 must restate this erratum and must **not**
  cite a "rev-3 regression-target bug" anywhere.
- **Process note for ZCode:** verify a claimed defect against the committed object (`git show
  <rev>:<path>`) before you disclose it. A false bug report in a frozen record costs as much trust
  as a missed one.

## 3 · Run instructions

1. Cherry-pick this review file onto `research/broad-search-v2-zcode`. The guard reads it next to
   the driver.
2. Confirm on disk that `sha256sum` of the driver and predeclaration equal the GO line. Then run the
   driver **once**, on the local corpus (end frozen 2026-07-29), through `research/tracking.py`.
3. If it crashes before any arm statistic prints: fix, disclose, and re-run; that needs a new GO
   only if the driver sha changes. Anything after outcomes print is final.
4. Write `VERDICT_X1_OVERNIGHT.md`, in the frozen pass/kill order:
   1. X1-A bar;
   2. X1-B sign;
   3. absorption share;
   4. single-year concentration;
   5. the all-rows lens;
   6. the k = 1 sensitivity;
   7. the X1-C/D and X1-E/F readings;
   8. the economics (overlay value; standalone net of the 0.60% RT and the D-059 modeled cost);
   9. the recorder correlations.

   Then add the erratum (§2), `CENSUS_NOTE.md` (+6 → N = 561, bar 3.2745), and **stop for R3**.
   The stop rule applies: a pass means no refinements and no variants.

## 4 · Holdout (2026-07-30 → latest) — NOT authorized by this GO

The holdout is read **once, at R3, after the in-sample verdict is committed**. It needs data that
does not exist on tjiejet (local corpus ends 2026-07-29), and the XPS-13 must not run a
compute-heavy job. The R3 procedure will be:
- (a) the Owner copies snapshot `walkforward-20261004-213000.db.zst` (sha `8408e91a…b3ba`) to
  tjiejet over Twingate;
- (b) ZCode freezes a small holdout wrapper that **imports** the rev-4 driver's functions unchanged
  and evaluates only 2026-07-30 → snapshot max. Same arms, same estimator, no new parameters. It is
  committed and hash-pinned before the read;
- (c) the reviewer issues a separate hash-bound holdout GO;
- (d) the September EOD-plan timing illustration runs inside that same read.

With ~45 holdout sessions the holdout can only **contradict** a pass (sign flip / collapse); it
cannot confirm one. State this in the verdict.
