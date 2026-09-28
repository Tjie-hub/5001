# VERDICT — SCREEN-PM-INS-001 (insider-event screen)

**SCREEN FAIL (null).** 2026-09-28, one run (`RESULT_20260928T035303Z.json`, script sha256 in the
result). Pre-declared primary: **E1 accumulation (stake change ≥1%), hold 20, ex-2025, gross** —
readable at 78 valid months (≥ 48 gate), **primary −0.758%/mo, t = −0.98, 52.6% months positive**.
|t| = 0.98 < 3.0 ⇒ the insider accumulation lead **closes at screen level**. Placebo not triggered
(primary not positive). No family slot consumed; a re-open is a new screen id.

## All 16 cells (gross monthly excess, day-weighted calendar-time vs EW liquid book)

| cell | events | months | prim %/mo | t | pos% |
|---|---|---|---|---|---|
| E1 h5 full | 8,796 | 97 | +0.02 | 0.02 | 54.6 |
| E1 h5 ex2025 | 5,916 | 76 | −0.41 | −0.44 | 51.3 |
| E1 h20 full | 8,796 | 98 | −0.17 | −0.26 | 58.2 |
| **E1 h20 ex2025 (PRIMARY)** | **5,916** | **78** | **−0.76** | **−0.98** | **52.6** |
| E2 h5 full | 4,698 | 97 | +0.66 | 0.52 | 53.6 |
| E2 h5 ex2025 | 2,704 | 76 | +0.41 | 0.26 | 50.0 |
| E2 h20 full | 4,698 | 97 | +0.92 | 0.95 | 54.6 |
| E2 h20 ex2025 | 2,704 | 77 | +0.59 | 0.50 | 51.9 |
| E3 h5 full | 1,513 | 71 | +3.31 | 1.33 | 56.3 |
| E3 h5 ex2025 | 617 | 50 | +4.21 | 1.22 | 58.0 |
| E3 h20 full | 1,513 | 81 | +2.32 | 1.49 | 56.8 |
| E3 h20 ex2025 | 617 | 61 | +2.86 | 1.41 | 55.7 |
| E1s h5 full | 6,923 | 97 | −1.82 | −2.29 | 40.2 |
| E1s h5 ex2025 | 4,500 | 76 | −2.41 | −2.74 | 38.2 |
| E1s h20 full | 6,923 | 97 | −1.26 | −1.94 | 43.3 |
| E1s h20 ex2025 | 4,500 | 77 | −1.78 | −2.36 | 42.9 |

## Recorded observations (descriptive; per the pre-declaration none of these gate)

- **E3 (director/commissioner BUYs)** points the classic direction (+2.9%/mo ex-2025 at h20) but at
  t 1.2–1.5 on 617 events it is far from the bar and would need years of forward testing to decide
  (harness C-MIXED). Arithmetically its cost is negligible at this turnover (~10 events/mo against a
  book of hundreds ⇒ ≲0.06%/mo at the 0.60% round trip), i.e. the shortfall is inference, not cost.
- **E1s (≥1% insider distribution)** is negative everywhere — insider big SELLs are followed by
  underperformance, h5 ex-2025 at −2.41%/mo, t −2.74, 76 months. Below the bar and not the primary;
  it repeats the program-wide avoidance direction (now from a new instrument), and any pursuit is
  **owner-gated** and would correlate with {R1}/FADE-001 (registered, first closure ~2026-10-19).
- **The `net`/`net_t` columns in the RESULT are MIS-SPECIFIED as a "long sleeve net of cost"
  lens**: `uplift_net` is the D-060 engine's deployment-scaled overlay net, which reads the
  avoidance overlay, not the flagged long book (hence positive where gross is negative). The
  pre-declared verdict was gross and stands; treat those columns as the mirror overlay's net only.

## Data record

Defects as pre-declared: 812 BUY sign-inconsistencies dropped; 40 SELL rows with previous ≤ 0 /
non-negative change dropped; 45 events mapped outside the panel; 126 flagged rows outside the entry
window [2018-01-01, 2026-09-16]. Panel: 1,575,448 rows, final bars through 2026-09-25. Zero exact
duplicate rows; event_id not unique (unused). PIT convention: flag on the first own session after
the transaction, entry two own sessions later (T+1 disclosure latency defused; intraday residual
accepted as a limitation).

**Consequence:** the last unscanned in-house dataset is now read. The "no tradeable long edge"
record gains one more closed door; nothing is registered; the three forward tests remain the only
deciders.
