# Program-wide deflation audit — 2026-09-28 (D-062)

**Question.** After everything recorded on this corpus, do any in-sample headline statistics
survive a program-wide multiple-testing deflation? Method and script:
`deflation_audit/deflation_audit.py` (method stated in its header, before results; one run;
`RESULT_2026-09-28.json`).

**Census (252 disclosed trials).** Registered hypotheses 8 + G1 arms 3 + pattern scan ~12 +
wedge variants 6 + entry filters 6 + threshold cells 48 + alignment cells 27 (all LIM-7 /
`PATTERN_SCAN_2026-09-17.md`) + discovery sprint ~120 constructions (`DISCOVERY_REPORT_2026-09-15`)
+ universe-screen 6 (D-058) + insider-screen 16 (D-061). This is the honest denominator the
program has owned all along, now written in one place.

**Deflated bar** — E[max |Z|] under the global null at each census depth
(Bailey–López de Prado expected-max form; Gaussian trials):

| depth | bar |
|---|---|
| registered only (N=8) | 1.46 |
| + scans (N=50) | 2.28 |
| + discovery sprint (N=120) | 2.59 |
| **all disclosed trials (N=252)** | **2.84** |

**Headline survival.**

| recorded statistic | \|Z\| | survives deflation at |
|---|---|---|
| FADE failed-breakdown h20, gross vs EW-book (D-057) | 4.4 | **all depths** |
| FADE h20 vs IHSG, calendar-time (D-057, "mixed") | 3.13 | all depths |
| T1 D/EX-2025 raw, next-open vs EW (audit2) | 3.84 | all depths |
| T1 A/EX-2025 raw, close vs IHSG (frozen §3 ref) | 2.98 | all depths |
| Insider E1s ≥1% distributions, h5 ex-2025 (D-061) | 2.74 | dies at full census |
| VOLEX-001 pooled ex-ante | 2.59 | dies at full census |
| T1 ex-2025 **overlap-robust** (D-057) | 1.8 | dies above registered-only |
| Insider E3 director/commissioner (D-061) | 1.41 | dies everywhere |

**Reading.**

1. The only in-sample family that survives program-wide deflation is the **avoidance family**
   (failed breakdown / falling wedge vs the EW book) — and it is already owned by the in-flight
   FWD-PM-FADE-001 forward test. Nothing else recorded — T1 raw included — clears the honest
   bar, and T1's only statistic that clears it (the raw overlapping-hold t) is the one D-057
   already re-read at 1.5–1.8 robust, which dies everywhere. Deflation and the validity audit
   agree from independent directions.
2. **Hansen SPA is recorded as blocked, not skipped**: it needs the per-arm return series, and
   the pattern-arm series are not regenerable from the frozen manifest (review finding F-1,
   2026-09-28 — `ZCODE_REVIEW_V2_FINDINGS_2026-09-28.md`). Restoring the lost drivers
   (`t1/t2`, forward-window columns, limitation-9 audit) is an owner decision; until then the
   deflation bar above is the program's program-wide guard.
3. Consequence for the search: any future candidate must clear ~2.8–3.0 |Z| **after** the
   census grows by its own grid — the practical rule the screens (D-058/D-059/D-061) have
   already been applying at |t| ≥ 3.0.

**Receipts:** `deflation_audit/{deflation_audit.py, RESULT_2026-09-28.json}`;
`EXPERIMENT_LEDGER.jsonl`; D-057 (`AUDIT_2026-09-24_RESULT_VALIDITY.md`); D-061; review F-1.
