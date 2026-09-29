# CENSUS_UPDATE — broad edge search arms join the D-062 census (2026-09-29)

**Added arms: 14** (≤ 24 budget; brief rule 2). Counting convention = the insider-screen
precedent (D-061): every pre-declared grid cell whose primary statistic was computed is one arm;
the raw lens, net observability, per-date headline, vs-IHSG lens and the triggered placebo ride
inside their arm and are not separate trials (each is a re-lens of the same cell's primary).

| screen | arms | cells |
|---|---|---|
| SCREEN-PM-CF-001 (`{CF}` issuance) | 8 | RI/RUPS × h126/h252 × pre2021/post2021 |
| SCREEN-PM-LC-001 (`{LC}` young listings) | 6 | YOUNG × h126/h252 × pre2021/post2021 + 2 vol-conditioned descriptive |

**New census depth: N = 252 + 14 = 266.** Recomputed expected-maximum bar
(Bailey–López de Prado form, γ = 0.5772, identical to `deflation_audit/deflation_audit.py`):

| census | N | bar |
|---|---|---|
| D-062 recorded | 252 | 2.8402 |
| **this update** | **266** | **2.8575** |
| if a `{LC}` Rule Card were later registered and its grid added (~+1) | 267 | 2.8587 |

The pre-declared pass bar (2.857) was set at exactly this value **before both runs**; the
SCREEN-PM-LC-001 primary (|t| 3.66) clears the updated bar with margin, and SCREEN-PM-CF-001's
best cell (|t| 1.10) dies at every depth.

Survival re-check at N = 266: nothing changes in the D-062 table — FADE h20 gross-vs-EW (4.4) and
T1 raw overlapping-hold (3.84, itself re-read at 1.5–1.8 robust by D-057) keep their recorded
statuses; VOLEX (2.59), insider E1s (2.74) stay dead. The new survivor is **SCREEN-PM-LC-001's
primary at |Z| 3.66** (and vs-IHSG 3.21, above the bar) — a screen-level survivor, not a registered
statistic; promotion is an Owner decision (handoff).

**Registry hygiene (proposed, not executed — the brief forbids registry edits from this search):**
one EXPERIMENT_LEDGER.jsonl line per screen (exploratory_screen, canonical ids
SCREEN-PM-CF-001 / SCREEN-PM-LC-001, predeclaration shas `b26d7d0b…` / `e282f313…`, run ids in
`research.db::research_runs`), and D-064 recording both verdicts + the census update. Draft text
in `HANDOFF_BROAD_SEARCH_2026-09-29.md`.
