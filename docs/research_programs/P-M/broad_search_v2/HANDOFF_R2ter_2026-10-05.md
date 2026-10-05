# HANDOFF_R2ter — rev 4 re-freeze complete · 2026-10-05 (ZCode)

**Branch:** `research/broad-search-v2-zcode` (pushed). **No driver ran.** Review files
(`REVIEW_R2_2026-10-05.md`, `REVIEW_R2bis_2026-10-05.md`, the minute-bar receipts and the EOD-plan
input) were cherry-picked from `origin/research/new-order-2026-09-30` onto the branch (commits
`95fbf18`, `339a8f4`) so the GO file exists next to the driver at run time.

## Frozen package (rev 4)

| artifact | sha256 |
|---|---|
| `x1/PREDECLARATION_X1_OVERNIGHT.md` (rev 4) | `994f21a9e8256d35d5b665845bb9fb072e90551062eb97290b3a29e969bf47c5` |
| `x1/screen_x1_overnight.py` (rev 4 driver) | `ea7cf68c99a22cc39d6033dc9c52cde2ee284ee4733396897c33c4534977c05b` |
| `x1/pit_tests_x1.py` (+ `PIT_TESTS_X1.json`) | `a0c15260ea89f200582bc21f0b74666e1ab566116a895fe366ae6488e5ac2406` |

The GO line for R2-ter, when the reviewer issues it, must read:

```
R2-DECISION: X1 GO driver_sha256=ea7cf68c99a22cc39d6033dc9c52cde2ee284ee4733396897c33c4534977c05b predeclaration_sha256=994f21a9e8256d35d5b665845bb9fb072e90551062eb97290b3a29e969bf47c5
```

(the N3 guard now scans every line of every `REVIEW_R2*.md`, ignores template candidates without
both 64-hex shas, and requires a full match against the files on disk — fail-closed).

## Fix-by-fix confirmation (REVIEW_R2bis §N1–N3 + non-blocking)

- **N1** — `books()` builds `gap_tlkm` (tick-eligible TLKM, `open(D)/close(d) − 1`, same
  construction as `oc_tlkm`); the absorption loop can no longer hit the KeyError.
- **N2** — SPY arm is the **raw compounded US-window return standardized by the trailing σ of the
  y series** (250 / min 120), no β, no hedge leg — code aligned to the unchanged spec. **T1-SPY
  proves it**: under the full perturbation battery (JKSE_D/FX_D/TLKM open(D)/close(D) ±5%),
  SPY's R_std is bit-identical on 50/50 sessions AND **zero later SPY sessions move**
  (`spy_not_residualized: true`) — a residualized arm would have moved.
- **N3** — `check_guard` scans all lines of all `REVIEW_R2*.md`; candidates without both 64-hex
  shas are ignored; acceptance requires a full disk match; refusals list every candidate line and
  why it failed. **T4** covers the four required cases and passes: template-only → refuse;
  wrong-sha → refuse (with `match=False` candidate listing); template file + valid line in a later
  file → **accept** (found at `REVIEW_R2bis_2026-10-05.md:2` in the synthetic case); no file →
  refuse.
- **Non-blocking cleanups** — dead `beta_cache` deleted; `empty_a` computed (both empty-book
  counts disclosed in the RESULT); the driver's E4 disclosure now carries the confirmation-half
  boundary count (81,816; discovery 116,119) matching the test output.

## Beyond N1–N3 — disclosed prominently (reviewer attention required)

During the N2 rewrite, one further rev-3 defect surfaced that T1–T3 could not catch and the
review did not list: **`build_signal` set the regression target to `y_map[p][1]` — the session
count k — instead of `y_map[p][0]`, the US return** (`ys_all`). The β̂ regression for EIDO/TLK was
therefore fit against a near-constant target (garbage slopes; the signal degenerated toward the
raw US return). Rev 4 sets the target to the US return, which is what the spec has always said
("OLS of the US leg on the hedge leg"). This changes the EIDO/TLK signal materially and is the
reason the rev-4 diff exceeds N1–N3; it is a pre-run amendment made before any outcome read, so
the census stays 555 + 6 (bar 3.2745 unchanged).

## PIT tests — RUN AND PASS (output committed)

- **T1**: 50/50 bit-identical per signal under the full perturbation battery (now with the
  corrected regression target).
- **T1-SPY (N2)**: `spy_not_residualized: true`.
- **T4 (N3)**: all four guard cases pass as specified.
- **T2**: 14,401 sessions, all stamps < D, all US closes ≤ 08:45 WIB. **T3**: correct signs in
  both leg variants.

## Stop

ZCode stops here. Per the reviewer's commitment, a diff limited to N1–N3, the tests, the
predeclaration amendment note and the listed cleanups receives the hash-bound GO line
immediately — the diff additionally contains the disclosed `ys_all` fix above, which the reviewer
should confirm before issuing the R2-ter GO.
