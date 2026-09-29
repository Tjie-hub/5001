# VERDICT — SCREEN-PM-CF-001 (`{CF}` issuance avoidance) · **FAIL (null)**

**Run:** one shot, 2026-09-29 (`RESULT_S1_20260929T043417Z.json`; run_id recorded in
`research.db::research_runs`, kind `broad_search_screen_s1_cf_issuance`, git `0029123`+
predeclaration `b26d7d0b…`). Panel: snapshot `walkforward-20260928-213012` (sha `10f9c97f…`),
2,500,859 rows through 2026-09-16, FORU dropped from 2026-09-14 (8 rows).

## Primary cell (pre-declared): RI · hold 252 · confirmation half · corrected · gross

- **−0.635 %/mo, t = −0.56, 62 valid months** → |t| 0.56 ≪ 2.857 ⇒ **screen FAIL (null)** under
  the frozen rule. Checks: FILL-1 PASS (63/63 order-clean), ID-1 PASS (share 7.1e-5).

## Every pre-declared cell (each = one arm; raw lens rides inside the same arm)

| arm | events | valid mo | mean %/mo (corr) | t (corr) |
|---|---|---|---|---|
| RI · h126 · pre2021 | 34 | 68 | +1.112 | +0.80 |
| RI · h126 · post2021 | 63 | 57 | −1.473 | −1.07 |
| RI · h252 · pre2021 (discovery) | 34 | 82 | **+1.114** | **+1.01** |
| **RI · h252 · post2021 (PRIMARY)** | 63 | 62 | **−0.635** | **−0.56** |
| RUPS · h126 · pre2021 | 170 | 22 | −0.126 | −0.14 |
| RUPS · h126 · post2021 | 1,366 | 63 | −0.122 | −0.35 |
| RUPS · h252 · pre2021 | 170 | 29 | −0.263 | −0.39 |
| RUPS · h252 · post2021 | 1,366 | 63 | −0.235 | −0.84 |

No cell in the grid reaches |t| ≥ 1.10 on either lens. The raw lens is within 0.03%/mo of the
corrected lens everywhere (the 10 gap-verified wealth corrections — audit in the RESULT — did the
work; the mechanical ex-drop is not what the screen was measuring). vs-IHSG on the primary:
−0.33 %/mo, t −0.27 (null). Placebo not triggered (|t| < bar). Net observability: the mirror-overlay
net is ≈ 0 for RI; for RUPS h252 post it is −4.2 %/mo — pure turnover cost at 1,366 events, no edge
to pay for it with.

## Reading

1. The announcement-stamp screen finds **no issuance drift in either direction** at the census bar.
   The discovery half even carries the *wrong* sign (+1.1 %/mo, t 1.0) — pre-2021 rights issuers
   slightly outperformed — so the Tier-R same-sign gate would have failed any post-2021 pass anyway.
2. Consistent with the R5 power statement: a US-calibrated haircut effect (~−0.15 %/mo) was always
   an order of magnitude below this sample's MDE; the IDX dilution-event magnitude hypothesis is
   not supported either.
3. The `{CF}` issuance lead **closes at screen level**; a re-open is a new screen id (D-061
   precedent). Proposed FAILURE_REGISTRY-style note is in the handoff.

**Arms added to the census by this screen: 8** (see CENSUS_UPDATE.md).
