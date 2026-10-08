# VERDICT — HYP-PM-0017 (dividend clientele D1/D2), G1 · 2026-10-08

**One frozen run** (`RESULT_20261008T085015Z.json`, gate `DIVIDEND_G1_APPROVED=1`, snapshot
`a2d7e675…` / fingerprint `9c26e0df…` verified pre-outcome, bar **3.2968** at N = 607).
n = 547 (D1) / 324 (D2) — identical to the G0 census populations.

## D1 — pre-cum run-up: **FAIL (all three conditions)**

| condition | number | verdict |
|---|---|---|
| Strength: mean > 0 **and** primary t ≥ 3.2968 | mean **−0.5119%**; primary t **−1.9007** (two-way cluster −1.9007, month −0.9273) | **FAIL** (mean ≤ 0 and far below bar) |
| Both halves > 0 | half 1 (2021-07..2023-12) **−0.3163%** (n 223); half 2 (2024-01→) **−0.6467%** (n 324) | **FAIL** (both negative) |
| Parkinson-60-decile control > 0 | **−0.4384%** (n 534 defined) | **FAIL** |
| (n/a: D2-only conditions) | — | — |

## D2 — ex-day capture: **FAIL (strength and halves; controls pass)**

| condition | number | verdict |
|---|---|---|
| Strength: mean > 0 **and** primary t ≥ 3.2968, at the **0.9 tax factor** | mean **+1.3310%**; primary t **+1.8093** (two-way cluster +1.8093, month +2.0229) | **FAIL** (positive but far below bar) |
| Both halves > 0 | half 1 **+3.6652%** (n 128); half 2 **−0.1934%** (n 196) | **FAIL** (sign flip across the halves) |
| Parkinson-60-decile control > 0 | **+1.3786%** (n 320 defined) | PASS |
| Not top-tercile-only | lower two terciles mean **+0.2095%** > 0 (t1 +0.0860%, t2 +0.3330%, t3 +3.5738%) | PASS (thin: capture concentrates in the top tercile) |
| Gross-of-tax row (report) | gross mean **+1.9958%** | reported |

## Overall verdict under D-073's falsification rules: **NULL — FAILED**

- **D1 is falsified outright**: the pooled mean is ≤ 0 (−0.51%) and below the frozen bar. There
  is no pre-cum run-up in liquid IDX dividends 2021-07..2026-09; the average event LOSES
  0.51% over its 3–10-session window (win rate 42.2%) against a total-return EW book.
- **D2 is null and hits a second falsification clause**: the pooled mean (+1.33% net of the
  0.9 tax and 0.60% cost) sits below the frozen bar (t +1.81 vs 3.2968) **and flips sign
  across the halves** (+3.67% in 2021-23 → −0.19% in 2024→; the year table decays monotonically
  to negative: 2021 +10.30%, 2022 +1.87%, 2023 +4.71%, 2024 +0.37%, 2025 −0.55%, 2026 −0.30%).
  D2 is NOT "positive only gross of the tax" and NOT top-tercile-only — the clientele direction
  (drop-ratio median 0.6947, IQR 0.4385–0.8553: the ex-drop averages ~69% of the dividend)
  is visible but has decayed to ~zero in the last two years and never clears the bar.
- No arm proceeds to a forward test (PREDECLARATION §8). D-063's ex-date monitor stays
  detection-only. Family {SE} keeps its slot; the census counted the 2 arms regardless of
  outcome (X8).
- Honest-prior check (D-073): "D1 is likely null" — confirmed. "D2 is the real test" — it was,
  and it fails the bar with an era flip, consistent with the program's recurring decay pattern.
