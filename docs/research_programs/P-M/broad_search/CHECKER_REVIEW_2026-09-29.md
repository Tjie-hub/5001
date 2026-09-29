# CHECKER REVIEW — broad edge search (ZCode, commits `9131d56` → `0029123` → `1abaa52`)

**Reviewer:** main session (XPS), acting as planner/checker at the Owner's request · **Date:** 2026-09-29
**Scope:** process integrity, reproducibility, estimator validity and robustness of the S2 PASS.
**Disclosure:** §3's diagnostics are further looks at the primary cell's *own* monthly series. They
add no flags, cells or arms, and they are descriptive only. They do not change the frozen verdict;
they inform the Owner's next decision.

## 1. Process — PASS

| Check | Result |
|---|---|
| Freeze before run | predeclarations + drivers committed 11:32:10 WIB (`0029123`); S1 ran 11:34, S2 11:36 |
| Predeclaration hashes | S1 `b26d7d0b…`, S2 `e282f313…` match their `.sha256` files |
| Post-freeze drift | `0029123..1abaa52` only **adds** results/docs; no predeclaration or driver changed |
| Script identity | `screen_s2_listings.py` sha `577534e8…` = the RESULT's `script_sha256` |
| **Reproduction** | independent re-run of the committed functions on the same snapshot (`10f9c97f…`): **−2.4475 %/mo, t −3.6557, 62 valid months, flag counts 441/215/226** — identical |
| Estimator | `run_event_months` is a **calendar-time portfolio** (daily mean of open positions − book, compounded per month). Monthly observations do not overlap, so the plain t is legitimate |
| Listing proxy | the 142 confirmation-half flags are real listings (BUKA, GOTO, CMRY, MTEL, PGEO, CUAN, NCKL, MBMA, AMMN, BREN, …). One demerger listing (AADI), not an IPO: immaterial |
| CI / fences | boundary, db-centralization, data-fence and price-read guards pass (38/38) |

## 2. Findings

**C-1 (material to the next decision) — the S2 effect is era-concentrated and has decayed.**
Primary monthly excess vs IHSG by calendar year (the book series is not stored; the IHSG series
tracks it, t −3.21 vs −3.66):

| year | months | mean %/mo | t |
|---|---|---|---|
| 2021 | 5 | −10.57 | −6.45 |
| 2022 | 12 | −3.67 | −3.48 |
| 2023 | 12 | −3.07 | −2.90 |
| 2024 | 12 | −0.28 | −0.20 |
| 2025 | 12 | −2.08 | −0.92 |
| 2026 | 9 | +1.24 | +0.56 |

- Drop 2021 alone → t −2.32 (**below** the bar). 2023 onward → −1.20, t −1.35. The last 33 months
  average ≈ −0.5 %/mo, which is null.
- Newey-West (lag 3) on the IHSG series → t −2.76.
- The discovery half is −1.26, t −1.29 at h252, and **−0.07, t −0.06 at h126**. It carries the sign
  but not the effect.
- Reading: most of the PASS is the 2021–23 IDX IPO-boom unwind, a regime artifact in F5 terms. A
  durable listing-lifecycle effect is not supported. The frozen verdict stands (the rule was met);
  what it licenses is weaker than a Rule Card.

**C-2 — the {V}-independence claim is unsupported as stated.** "Flat across volatility bands" rests
on the two cells that ran on the pooled window instead of the confirmation half (the disclosed
deviation), with t −1.83 and −1.73. That shows no contradiction; it does not show independence.
Under D-062, any registration needs a proper test: correlate the YOUNG sleeve's monthly excess with
VOLEX-001's high-vol-decile excess, plus a double sort on the confirmation half, **predeclared**.

**C-3 — economics are small.** Book-level uplift from avoiding the sleeve, net of 0.60% RT:
**+0.15 %/mo** (`net_mean`). The −2.45 %/mo is the sleeve's excess, not the book's gain.

**C-4 — the program-wide deflation bar is lenient by about 0.2 (methodology, pre-existing).**
`deflation_audit.py` uses the one-sided Bailey–López de Prado approximation Φ⁻¹(1−1/N) for a
**two-sided** |Z|. Exact E[max|Z|] for N iid standard normals: **3.04 at N=252, 3.06 at N=266**
(recorded 2.84 / 2.8575).
- S2 (3.66) still clears.
- D-062's FADE avoidance family: vs EW-book 4.4 clears easily; vs IHSG calendar 3.13 clears
  narrowly.
- Nothing recorded as dead comes back to life.
- The fix needs a superseding DECISION_LOG entry, not an edit.

**C-5 — hygiene.** `bs_common.py:69` opens the snapshot with `__import__("sqlite3").connect(...)`. That
bypasses `data.db.connect` in a form the static scan cannot see (docs/ is not scanned anyway).
Read-only and snapshot-only, so there is no validity impact. It should use
`connect(path=SNAP, read_only=True)` like the module's other two loaders. The frozen driver is **not**
edited; the fix applies to future drivers.

**C-6 — minor.** The handoff's draft D-064 carries "Status: RECORDED" text. It is correctly a draft
inside the handoff, and the recorded entry is written by the main session on an Owner ruling.

## 3. Checker verdict

- **Screens:** S1 FAIL (null) — confirmed. S2 PASS under its frozen rule — **confirmed and
  reproduced**.
- **Recommendation:** record both verdicts (D-064) with C-1..C-4 attached, and **do not open `{LC}` or
  draft RC-0003 now**. The pass is carried by 2021–23 and is null for about 33 months, the book
  economics are ~0.15 %/mo, and the {V} independence is untested.
- A lead worth keeping costs nothing: a prospective, no-slot observability recorder for new liquid
  listings. It can never be judged before ≥48 months, so it is effectively a shelf with a
  thermometer.
- Correct the census bar to the exact two-sided value by a superseding entry.
