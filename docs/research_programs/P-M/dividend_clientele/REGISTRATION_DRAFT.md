# REGISTRATION DRAFT — HYP-PM-0017, dividend clientele D1/D2 (G0-frozen; DO NOT FILE)

> Draft only. This branch does not edit `HYPOTHESIS_REGISTRY.md`, `FAILURE_REGISTRY.md` or
> `DECISION_LOG.md`. The registry row and the D-entry below are filed by the owner at G0 approval,
> under the next free D-number (expected **D-076**; the brief's "expected D-075" is stale — D-075
> is taken by market-stress reversal).

## Proposed registry row

| field | value |
|---|---|
| id | HYP-PM-0017 |
| family | **{SE} Structural-event forced flow** (NEW family, opened at this registration — D-028, PG-3) |
| statement | Cash-dividend clientele flows: D1 pre-cum demand (run-up into the cum date) and D2 ex-day tax clientele (the ex drop < the dividend; capture ≥ 2%-yield events net of tax and cost) |
| arms | D1, D2 (exactly two; no horizon grid, no yield grid) |
| benchmark | total-return EW liquid book (ADV20 ≥ Rp 10bn PIT); Parkinson-60-decile-matched control |
| primary statistic | min(month-mean t, two-way cluster t by cum month × ticker), per arm |
| bar | 3.2950 — `bar_v2.e_max_abs_z(603)`, frozen at G0 (census ledger 601 + 2 arms; D-071 §2) |
| halves | cum ≤ 2023-12-31 (in effect 2021-07..) and cum ≥ 2024-01-01 — both means > 0 |
| data | walkforward snapshot `a2d7e675…` / fingerprint `9c26e0df2fdd4e4b…` (2026-10-08, `CENSUS_G0.json`) |
| population | 562 liquid events (2021-07..2026-09); D1 n = 547; D2 n = 324 (yield ≥ 2%) |
| G0 | branch `research/dividend-clientele-2026-10`, PREDECLARATION.sha256 sidecar, census counts-only |
| falsification | D-073: pooled mean ≤ 0 / below bar / half sign-flip; D2 only gross of tax or top-tercile only |

## Proposed D-entry text (draft)

### D-076 (expected) · HYP-PM-0017 (dividend clientele) registered in {SE}, G0 frozen

**Status:** (to be RECORDED at owner approval) · **Type:** Registration + G0 freeze ·
**Approval authority:** owner approval of the 2026-10-08 G0 (this branch).

- **Why admitted.** D-073 accepts the dividend-clientele mechanism (pre-cum demand; ex-day tax
  clientele) under D-070 §1; this is the first {SE} registration.
- **Family/multiplicity.** New family {SE}, slot 1 (D-028, PG-3). Census: D-075 census-note
  ledger **601** + this registration's **2** arms = **603**; frozen primary bar **3.2950** (exact
  `e_max_abs_z(603)` = 3.294959). Bars computed under earlier counts are reported as a secondary
  line only (D-071 §2).
- **Study (frozen).** PREDECLARATION.md (this branch, sha256 sidecar): populations D1 = AGM/
  dividend_created-anchored liquid events with 3–10-session windows (n = 547; anchor = the earlier
  of the latest `rups_date` 1–90 calendar days before cum and a non-artefact `dividend_created`;
  artefact = created ≥ exdate or a created date shared by > 50 rows) and D2 = yield ≥ 2% events
  (n = 324; tercile edges frozen at G0); outcomes against the total-return EW liquid book net of
  the 0.60% round trip; Parkinson-60-decile-matched control; primary t = min(month, two-way
  cluster); both-halves > 0 at cum ≤ 2023-12-31 / ≥ 2024-01-01; D2 must pass at the 0.9 factor and
  not only in the top tercile.
- **Freeze.** G0 = this branch's PREDECLARATION + drivers + PIT tests + `CENSUS_G0.json`
  (counts only: 4,762 dividend rows → 4,758 merged events → 2,614 cum-not-session (2,603 pre-panel,
  the 5001 corpus starts 2021-07-05) → 562 liquid; no outcome was read).
- **G1.** One run, `DIVIDEND_G1_APPROVED=1`, snapshot + fingerprint verified pre-outcome; RESULT /
  VERDICT / HANDOFF, then STOP. Nulls are predeclared useful (D-073 honest prior).
- **Forward test.** Only if an arm passes: new liquid dividends after the G1 date, frozen rules,
  recorded at cum and ex; host = the D-064 ex-date monitor lineage, owner-gated.
