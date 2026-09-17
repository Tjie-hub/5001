# P-M PROSPECTIVE VALIDATION PROTOCOL — V1 DRAFT (FOR OWNER/CRO REVIEW)

**Status: DRAFT — NOT FROZEN, NOT APPROVED, CAPTURE NOT ACTIVATED.**
**This document becomes the frozen protocol only after (a) every CRO/OPEN item is
resolved, (b) the owner approves it, and (c) its SHA256 is recorded in the
activation manifest. Any edit after freezing is a protocol deviation and must be
logged append-only.**

Program precedents cited: HYP-PM-0009/I7 registration (entry/exit index
convention, F-classification failure rules); HYP-PM-0008 SPEC §4/§13 (PIT
liquidity floor Rp 1e9; 0.60% round-trip friction floor; sensitivity rules);
g1_harness.py (erfc two-sided NW convention; COST_RT_FLOOR=0.006; NW_t(5) lag
precedent at k=5); BRANCH_A_NEW_MECHANISM_AUDIT §8 (X1–X6 exclusions);
dataset_b/foundation.py (split applied-basis detection; ARA/ARB band utilities);
DECISION_LOG D-entries + registered-run discipline (one registered run, no
rescue); data-gap audit 2026-09-14 (vendor payload instability; capture
service motivation); discovery record SPRINT_2026-09-15 +
ADVERSARIAL/FAMILY reports (candidate provenance and its known failures).

---

## 1. HYPOTHESIS STATEMENT

**H1 (primary, one-sided replication):** For Indonesian equities in the
prospective capture universe, on days where a stock rises at least +3%
(close-to-close, suspension-clean) AND the platform net-flow z-score (trailing
60 admitted sessions, shift 1) is ≤ −1 ("platform outflow into strength"), the
mean forward 5-session return is LOWER than on matching up-move days with
flow-neutral platform flow (|z| < 0.5), by at least the pre-registered minimum
effect size Δ* = −0.50% (h5, gross of costs; cost sensitivity reported, not
gated).

**Nature of H1 (declared per owner instruction):** this is a REPLICATION
hypothesis of a historical descriptive observation (family #3 I1 grid: 4/4
half-year negative spreads at all six threshold cells). It is NOT an alpha
claim: the historical spread FAILED incrementality after a liquidity control
(FM +0.27%, t=0.49) and was absent in the top-ADV tier. The prospective test
asks whether the descriptive pattern persists out-of-sample; no trading claim
is made or implied.

**Provenance of the candidate:** discovery record
`SPRINT_2026-09-15/` (DISCOVERY_REPORT, ADVERSARIAL_REPORT §5, FLOW_FAMILY_REPORT
§I). Candidate is the ONLY parked item from the completed program (families 1–5
CLOSED/DEAD, family 6 DEAD). **k = 1 candidate; no multiplicity adjustment
applies.** No second candidate may be added after prospective data are observed.

## 2. SIGNAL CONSTRUCTION (exact)

- Platform net flow per (ticker, session):
  `flow_raw = Σ_buy(bval) + Σ_sell(sval)` where bval/sval are the SIGNED vendor
  values in the marketdetectors broker_summary (sval is already negative).
  **Mapping validation status: formula confirmed EXACT on all retained Dataset B
  payloads with complete broker rows (4/4 non-degenerate cases in the 2026-09-16
  spot check), but 295/300 sampled retained payloads have empty/partial rows
  (documented vendor refetch instability). Full-corpus validation is GATE G-7
  (mandatory, currently FAIL).**
- `nbz(ticker, session) = (flow_raw − mean60) / std60` over the trailing 60
  admitted sessions of that ticker, shift(1), min 20 non-empty sessions.
- Up-move day: `ret1 = close(t)/close(t−1) − 1 ≥ +0.03` (adjusted per §9).
- Veto cell: up-move day AND nbz ≤ −1.0.
- Control cell: up-move day AND −0.5 < nbz < +0.5 (flow-neutral).
- Mid band [−1.0, −0.5] and positive side are excluded from the contrast
  (declared; mirrors the historical construction).
- `rv` (participation) and regime variables are NOT part of H1 (they were the
  instruments that killed incrementality; they appear only in the pre-declared
  heterogeneity secondary, §12).

## 3. UNIVERSE AND PIT MEMBERSHIP

- Capture universe: the ticker roster frozen in
  `prospective_validation/universe_frozen.csv` at activation (generated from
  `idx_tickers` WHERE status='active' on the activation date). **No roster edits
  after activation**; newly listed/delisted names are captured only if in the
  frozen roster and admitted by §5. This is the honest fix for the historical
  canvas's survivorship structure (zero dropouts).
- Membership is PIT: a (ticker, session) observation exists iff the payload was
  captured for it; no backfill from vendor history is used in the prospective
  cohort (§4).
- Liquidity eligibility at ANALYSIS time (not admissibility): trailing-60
  median traded value ≥ Rp 1e9 (program floor, HYP-PM-0008 §4), computed from
  prospective prices only.

## 4. REQUIRED DATA FIELDS AND SEMANTICS

Captured payload (raw, content-addressed): `broker_summary.brokers_buy[].{bval,
blot, freq, type, netbs_broker_code}`, `brokers_sell[].{sval, slot, ...}`,
`data.from/to` echo, `bandar_detector.*` (retained for completeness, not used by
H1). Manifest per attempt: status, http_status, date_echo_match,
truncation_suspected, response_sha256, captured_at_utc, tz_session. Analysis
side: adjusted daily OHLCV from production `ohlcv` (is_final=1), split basis per
foundation.py convention, dividends added to ex-day returns; suspension windows
from `suspension_events`. **flow field units: vendor Rp (signed); never freq as
denominator (program rule); platform flow ≠ end-investor identity.**

## 5. CAPTURE CUTOFF AND ADMISSIBILITY

- A (ticker, session) observation is ADMISSIBLE iff the manifest shows a
  terminal SUCCESS/EMPTY attempt with `captured_at_utc` on the session's own
  calendar day at ≥ 16:10 WIB (post-close) and ≤ the session's T+5 WIB day
  (late-capture tolerance), AND `date_echo_match = 1`, AND
  `truncation_suspected = 0`. Late/duplicate/failed captures are logged, never
  substituted by vendor refetches.
- Capture cadence (proposed, CRO-open): EOD ≥ 18:30 WIB after the production
  cron, one pass per admitted session (admitted sessions = `trading_calendar`
  ∩ no holiday), sessions-file generated mechanically from the calendar
  (addresses the DESIGN-vs-code calendar gap).
- **No outcome-dependent field may enter admissibility:** admissibility consumes
  only calendar, roster, and manifest/payload fields (verified by gate test T-2).

## 6. ENTRY TIMING

Entry at the close of session t+1 (`close(t+1)`), per the I7 registered
convention (HYP-PM-0009; EXP-PM-0009/R2 index-fix note: exit index = i+1+k —
k=1 means exit i+2). The signal (§2) is fully determined at session t's close;
entry one full session later is conservative and PIT-safe.

## 7. HOLDING PERIODS

Primary: h5 (5 sessions). Secondary (non-primary, descriptive only): h1, h2, h3,
h10, h20, reported with the same estimator but carrying no decision weight.

## 8. LIQUIDITY / PRICE CONSTRAINTS

Entry-day tradability: `volume(t+1) > 0`. Analysis-time liquidity floor:
trailing-60 median traded value ≥ Rp 1e9 (HYP-PM-0008 §4). No price-level
constraint (the historical canvas had none; a price floor would change the
candidate's definition — CRO may add one only BEFORE freeze).

## 9. EXCLUSIONS

Inherited from program precedent, applied identically to both contrast cells:
(a) suspension-window sessions and ±20-session proximity (adversarial-pass
standard); (b) ARA/ARB auto-rejection-band contact days (foundation.ara_arb
utilities); (c) corporate actions: events handled by the applied-basis
convention (foundation.detect_unapplied_splits; dividends added to ex-day
returns); split-in-window events EXCLUDED (adversarial standard); (d) missing
flow (NaN) → signal undefined, observation dropped from BOTH cells symmetrically;
(e) missing entry-day trading → dropped; (f) the v002 fixture/integrity-zone
concepts do not apply (no historical minute data used).

## 10. TRANSACTION-COST ASSUMPTION

0.60% round-trip floor (HYP-PM-0008 §13 S6; memo §8; g1 COST_RT_FLOOR), applied
to net-of-cost SECONDARY reporting only. The primary endpoint is the gross
SPREAD between two contemporaneous long portfolios (both pay the same floor), so
costs do not gate H1; a candidate may only inform a FILTER, whose economics are
reported net at 40/50/60bp as sensitivity (non-gating).

## 11. PRIMARY ENDPOINT

Daily spread series: for each session t with ≥1 veto event AND ≥1 control event,
`s_t = mean h5(veto events) − mean h5(control events)` (entry close t+1).
Primary statistic: mean(s) over the analysis window, tested one-sided
H0: mean(s) ≥ 0 vs H1: mean(s) < 0 at α = 0.05 **[α: CRO/OPEN — proposed]**,
with the additional requirement that the point estimate ≤ Δ* = −0.50%
**[Δ*: CRO/OPEN — proposed; historical point estimate ≈ −1.0%, halved ex ante to
discount selection]**. Both conditions must hold for replication.

## 12. SECONDARY ENDPOINTS (non-primary, descriptive)

h1/h2/h3/h10/h20 spreads; liquidity-tercile heterogeneity (top/mid/bottom ADV —
pre-declared because the historical effect was mid-cap concentrated; a
significant effect confined to the top tier would be NEW, not replication);
net-of-cost economics at 40/50/60bp; event counts and coverage rates; bandar_
detector payload completeness. Secondaries carry no decision weight and are
reported after the primary is executed, in the same report.

## 13. ESTIMATOR AND HAC SPECIFICATION

Mean(s) with Newey-West HAC standard errors, lag = 5 (matching the C7 NW_t(5)
precedent for 5-day overlapping horizons; g1_harness erfc two-sided convention
adapted to a one-sided test at α). The one-sided p = Φ(t) where t = mean/SE_HAC.
No covariate adjustments in the primary; the pre-declared robustness FM
regressions (controls: ret1, ret5z, volume z, ADV tercile, flow level) are
SECONDARY descriptive output only — H1 does not depend on them, and their
historical failure is part of the record.

## 14. MINIMUM SAMPLE / FEASIBILITY GATE

Analysis executes only when ALL hold: (a) ≥ 180 admitted sessions with both
contrast cells non-empty [σ(s) assumed ≤ 2.5%; power ≈ 80% at Δ*=−0.50%,
one-sided α=0.05 → ~155 sessions; margin added — **σ, α, power, Δ*: CRO/OPEN**];
(b) ≥ 200 distinct veto events; (c) ≥ 600 distinct control events; (d) ≥ 50
distinct tickers per cell. If the sample gate is not met by 2027-12-31, the
experiment terminates as INFEASIBLE (no claim either way).

## 15. STOPPING RULE

The primary test runs EXACTLY ONCE, when §14 is first satisfied. Interim
inspection of s_t for tuning, dashboarding of effect size, or early stopping is
FORBIDDEN. Coverage/operational monitoring (capture success rates only) is
permitted and expected.

## 16. FAILURE RULE

If H1 is not replicated (either p ≥ α or point estimate > Δ*), the candidate is
classified **FAIL (replication failure) — terminal**, following the I7/C7
F-classification convention; no re-specification, no stratum shopping, no
rescue. If the sample gate fails by the horizon date: INFEASIBLE, no claim.

## 17. MISSING / INCOMPLETE CAPTURE

Outages are logged (run_log + a dated outage note). Missing cells are missing;
no vendor-refetch backfill may enter the prospective cohort; imputation of
flow is forbidden. If capture coverage falls below 70% of intended cells for
more than 5 consecutive admitted sessions, a protocol deviation record is
opened; ≥ 3 such deviations trigger an owner review before continuing.

## 18. PROTOCOL DEVIATIONS

Any deviation (edit to frozen artifacts, cadence change, roster exception,
outage beyond §17, admissibility exception) is recorded append-only in
`prospective_validation/deviation_log.md` with UTC+WIB timestamps and reason.
Deviations never delete or rewrite history; the analysis report must list all
deviations.

## 19. REPRODUCIBILITY REQUIREMENTS

Frozen artifacts at activation: (i) this protocol (SHA256 recorded);
(ii) `universe_frozen.csv`; (iii) `prospective_capture.py` code_sha256 (already
hashed per run); (iv) analysis script hash, fixed before the primary run;
(v) activation manifest binding (i)–(iv) with UTC/WIB timestamps. Raw payloads
content-addressed; manifest append-only; the primary analysis must run from the
frozen analysis script via the program's fail-closed provenance wrapper
(`g1_harness/provenance.py` precedent) and record its output verbatim.

## 20. FORBIDDEN AFTER OUTCOMES ARE VISIBLE

(1) adding/changing thresholds, windows, cells, or the control band;
(2) adding/removing candidates or reclassifying failures;
(3) changing exclusions, costs, entry/exit, or estimator/HAC lag;
(4) post-hoc strata beyond §12; (5) re-running the primary under any variation;
(6) retroactive cohort redefinition; (7) tuning capture cadence in response to
signal behavior; (8) any inferential language about endpoints not pre-declared;
(9) selective reporting of subperiods; (10) silent protocol edits (must be
deviation-logged per §18).

---

## CRO / OWNER-OPEN ITEMS (exhaustive)

| # | Item | Proposed (not frozen) |
|---|---|---|
| O-1 | α (proposed 0.05 one-sided) | owner |
| O-2 | Δ* MDE (proposed −0.50%) | owner |
| O-3 | σ(s) assumption & power target (proposed 2.5% / 80%) | CRO |
| O-4 | minimum sample triple (proposed 180 sessions / 200 veto / 600 control) | CRO |
| O-5 | capture cadence & cutoff (proposed EOD ≥18:30 WIB; admissibility ≥16:10 WIB) | owner |
| O-6 | universe roster source & freeze procedure | owner |
| O-7 | G-7 signal-mapping full-corpus validation acceptance threshold (proposed: exact-match ≥99% conditional on complete rows) | CRO |
| O-8 | deviation-log format & audit cadence (proposed weekly coverage report) | CRO |
| O-9 | independent checker identity (must not be the author of this document) | owner |
| O-10 | token/credential operational risk handling for capture uptime | owner |
