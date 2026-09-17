# P-M PROSPECTIVE VALIDATION PROTOCOL — V1.1 DRAFT (SUPERSEDES V1)

**Status: DRAFT — NOT FROZEN, NOT APPROVED, CAPTURE NOT ACTIVATED.**
**Freeze procedure:** after every `OPEN:` item below is marked `RESOLVED:` and the
owner approves, this document's SHA256 is recorded in the activation manifest;
from that moment any edit is a protocol deviation (§18). Until then this is a
draft for adversarial review.

**V1.1 change log (adversarial protocol review 2026-09-16):**
(1) hypothesis rewritten as H0: θ ≥ 0 vs H1: θ < 0 on the preregistered mean
daily spread θ; Δ* moved out of the hypothesis into a separate ex-ante
economic criterion; success requires BOTH. (2) Power: two explicit options
(A empirical planning-σ with provenance / B no formal power claim) — corpus
estimates computed and disclosed; planning-n under Option A is 1,425–3,062
sessions (infeasible). (3) Capture timing made mechanical; 16:10–18:29 WIB
explicitly admissible. (4) G-7 mapping validation fully specified; hard
pre-activation blocker. (5) Universe freeze hardened (roster file ≠ live query).
(6) Independent-checker role and checklist defined.
**NEW MATERIAL DISCLOSURE (estimand dependence):** the historical observation is
estimand-dependent. Pooled event-level h5 spread (old descriptive statistic):
negative, 4/4 half-years. Preregistered day-weighted daily spread series
(primary estimand, §11): **in-sample mean +0.17%** (298 valid sessions,
discovery corpus). The preregistered primary therefore does NOT show the
historical effect in-sample; the prospective experiment is expected to terminate
in replication failure. This is disclosed so the owner can decide whether to
spend the capture window on a test whose honest prior is unfavorable, or close
the candidate without prospective work. Both are legitimate; neither may be
decided after prospective outcomes are visible.

Program precedents cited (unchanged from V1): HYP-PM-0009/I7 (entry/exit index
convention; F-classification failure rules); HYP-PM-0008 SPEC §4/§13 (PIT
liquidity floor Rp 1e9; 0.60% round-trip friction floor); g1_harness.py (erfc
two-sided NW convention; NW_t(5) lag precedent; COST_RT_FLOOR=0.006);
BRANCH_A_NEW_MECHANISM_AUDIT §8 (X1–X6 exclusions); dataset_b/foundation.py
(split applied-basis detection; ARA/ARB band utilities); DECISION_LOG D-entries
+ registered-run discipline (one registered run, no rescue); data-gap audit
2026-09-14 (vendor payload instability); discovery record SPRINT_2026-09-15
(candidate provenance, adversarial and family kill records).

---

## 1. HYPOTHESIS STATEMENT

- **θ** = the preregistered mean daily h5 veto-minus-control spread (exact
  definition in §11).
- **H0: θ ≥ 0**
- **H1: θ < 0** (one-sided)
- Rejection of H0 in favor of H1 at the frozen α is the statistical component
  of success.

**Δ* (ex-ante replication / economic criterion) = −0.50% (h5, gross).** Δ* is
NOT part of H0/H1. **Success rule: BOTH** (i) one-sided statistical rejection of
H0 at the frozen α, **AND** (ii) point estimate θ̂ ≤ Δ*. If (i) holds but
θ̂ > Δ*, the result is STATISTICAL-ONLY (candidate remains parked, no promotion).
If (ii) holds but (i) does not, the result is UNRESOLVED under the frozen
framework (candidate remains parked; no claim).

**Nature of H1 (declared):** replication of a historical descriptive observation
(family #3 I1 grid, pooled event-level spreads negative 4/4 half-years). NOT an
alpha claim: the historical spread failed incrementality after a liquidity
control (FM +0.27%, t=0.49; absent in the top-ADV tier), and the preregistered
day-weighted estimand shows +0.17% in-sample (disclosure above). No trading
claim is made or implied. **k = 1 candidate; no multiplicity adjustment.** No
second candidate may be added after prospective data are observed.

**Provenance:** discovery record `SPRINT_2026-09-15/` (DISCOVERY_REPORT,
ADVERSARIAL_REPORT §5, FLOW_FAMILY_REPORT §I, INTERACTIONS_FAMILY_REPORT).

## 2. SIGNAL CONSTRUCTION (exact)

- `flow_raw(ticker, session) = Σ_buy(bval) + Σ_sell(sval)` — bval/sval are the
  vendor's SIGNED values in the marketdetectors broker_summary (sval is already
  negative). Mapping status: exact on all complete retained payloads; corpus
  incomplete (see G-7, §5 of the gate).
- `nbz = (flow_raw − mean60) / std60` over the trailing 60 admitted sessions of
  that ticker, shift(1), min 20 non-empty sessions.
- Up-move day: `ret1 = close(t)/close(t−1) − 1 ≥ +0.03` (adjusted per §9).
- Veto cell: up-move day AND nbz ≤ −1.0. Control cell: up-move day AND
  −0.5 < nbz < +0.5. Mid band [−1.0, −0.5] and the positive side are excluded
  from the contrast (declared).
- `rv`/regime variables are not part of H1; they appear only in the §12
  heterogeneity secondary.
- Platform flow is never end-investor identity; freq is never a denominator.

## 3. UNIVERSE AND PIT MEMBERSHIP

**universe_frozen.csv (hardened definition):** a write-once roster file
generated ONCE at activation time T0 by the exact query
`SELECT ticker FROM idx_tickers WHERE status='active' ORDER BY ticker`, with
`T0_UTC`, `T0_WIB`, row count, and SHA256 recorded in the activation manifest.

Post-T0 treatment (all mechanical, no judgment):
- **IPOs after T0:** NOT added. The roster is immutable.
- **Delistings after T0:** ticker remains in the roster; its sessions simply
  produce no admissible observations (dead names cannot satisfy §5/§8).
- **Suspensions:** handled by the §9 exclusion rule, not the roster.
- **Status changes after T0** (active→inactive etc.): IGNORED. The frozen file
  is the roster; the live `idx_tickers` table is never re-queried for the
  experiment.
- **Renames / corporate actions:** observations belong to the frozen ticker
  code. A code that IDX renames after T0 is not re-added under the new code.
- **No post-T0 roster edit is possible:** the gate re-verifies the file's
  SHA256 against the activation manifest before any analysis run; any mismatch
  is a §18 deviation.

## 4. REQUIRED DATA FIELDS AND SEMANTICS

Captured payload (raw, content-addressed): `broker_summary.brokers_buy[].{bval,
blot, freq, type, netbs_broker_code}`, `brokers_sell[].{sval, slot, ...}`,
`data.from/to` echo, `bandar_detector.*` (retained, unused by H1). Manifest per
attempt: status, http_status, date_echo_match, truncation_suspected,
response_sha256, captured_at_utc, tz_session. Analysis side: adjusted daily
OHLCV from production `ohlcv` (is_final=1; split basis per foundation.py;
dividends added to ex-day returns); suspension windows from `suspension_events`.
flow units: vendor Rp (signed); freq never a denominator; platform flow ≠
end-investor identity.

## 5. CAPTURE CUTOFF AND ADMISSIBILITY (mechanical)

- **Operational target (non-binding):** capture run at EOD ≥ 18:30 WIB, after
  the production cron.
- **Earliest admissible capture time:** ≥ 16:10 WIB on the session's own
  calendar day. Captures in the 16:10–18:29 WIB window ARE ADMISSIBLE — the
  18:30 target is an operational preference, not an admissibility bound.
- **Late-capture tolerance:** through the session's T+5 WIB day, only if all
  manifest conditions hold (terminal SUCCESS/EMPTY, `date_echo_match = 1`,
  `truncation_suspected = 0`, attempt fields complete).
- Admissibility consumes ONLY: calendar, frozen roster, and manifest/payload
  fields (date echo, row completeness, timestamps). No price/return field may
  enter admissibility (verified by gate test T-2/G-3).

## 6. ENTRY TIMING

Entry at `close(t+1)` (I7 registered convention; exit index = i+1+k; k=1 means
exit i+2). Signal is fully determined at session t's close.

## 7. HOLDING PERIODS

Primary: h5 (5 sessions). Secondary (descriptive, non-decision): h1, h2, h3,
h10, h20.

## 8. LIQUIDITY / PRICE CONSTRAINTS

Entry-day tradability: `volume(t+1) > 0`. Analysis-time liquidity floor:
trailing-60 median traded value ≥ Rp 1e9 (HYP-PM-0008 §4). No price-level
constraint (adding one post-discovery would redefine the candidate; CRO may
adopt one only BEFORE freeze as a documented O-item).

## 9. EXCLUSIONS (both contrast cells, identically)

(a) suspension-window sessions and ±20-session proximity; (b) ARA/ARB band
contact days (foundation.ara_arb); (c) corporate actions via the applied-basis
convention; split-in-window events excluded; (d) missing flow → observation
dropped symmetrically; (e) missing entry-day trading → dropped; (f) historical
minute-data concepts (fixture/integrity zone) do not apply.

## 10. TRANSACTION-COST ASSUMPTION

0.60% round-trip floor (HYP-PM-0008 §13 S6; g1 COST_RT_FLOOR), applied to
net-of-cost secondary reporting only. The primary endpoint is a gross SPREAD
between two contemporaneous long portfolios; costs do not gate H1. Filter
economics reported net at 40/50/60bp as non-gating sensitivity.

## 11. PRIMARY ENDPOINT (estimand, exactly)

Daily spread series: for each session t with ≥1 veto event AND ≥1 control event,
`s_t = mean h5(veto events entered t+1) − mean h5(control events entered t+1)`.
θ = mean(s_t) over the analysis window.

**Estimand disclosure (material):** the pooled event-weighted spread in the
discovery corpus was ≈ −1.3% (4/4 halves), but the day-weighted series θ̂ was
**+0.17%** in-sample (298 valid sessions). The preregistered estimand is the
day-weighted series — the version a daily-traded book actually experiences.
The prospective experiment is therefore expected, under the in-sample evidence,
to terminate in replication failure. This is disclosed, not hidden.

**PRIMARY TEST (exactly once):** one-sided t-test of H0: θ ≥ 0 vs H1: θ < 0 at
frozen α [O-1], with Newey-West HAC lag 5 (C7 NW_t(5) precedent; erfc family
conventions), PLUS the economic criterion θ̂ ≤ Δ* = −0.50% [O-2]. Success =
BOTH. Otherwise see §16.

## 12. SECONDARY ENDPOINTS (non-primary, descriptive)

h1/h2/h3/h10/h20 spreads; pooled event-level spread (reported explicitly as the
non-preregistered estimand whose historical value motivated the candidate);
ADV-tercile heterogeneity; net-of-cost economics at 40/50/60bp; coverage rates;
payload completeness. Secondaries carry no decision weight.

## 13. ESTIMATOR AND HAC SPECIFICATION

Mean(s_t) with Newey-West HAC SEs, lag 5. One-sided p = Φ(t), t = mean/SE_HAC.
No covariate adjustments in the primary. The pre-declared FM robustness
regressions (controls: ret1, ret5z, volume z, ADV tercile, flow level) are
secondary descriptive output only.

## 14. MINIMUM SAMPLE / FEASIBILITY — TWO OPTIONS (CRO/OWNER choose before freeze)

**Empirical planning inputs computed from the discovery corpus (provenance:
daily spread series s_t, 298 valid sessions, suspension-clean base, 2025-01..
2026-09; limitations: in-sample, fat-tailed, n=298, the same data H1 will be
tested on prospectively — NOT an independent estimate):**
- sd(s_t) = 11.13%; MAD-σ = 7.59%; 5%-winsorized sd = 8.76%; θ̂ = +0.17%.

**OPTION A — formal power claim with empirical planning-σ (CRO must approve the
σ choice and its provenance):** at α=0.05 one-sided, power 80%, Δ*=−0.50%:
required sessions ≈ 1,425 (MAD-σ) to 3,062 (raw sd) — i.e. **6–12+ years:
infeasible**. Under Option A the honest conclusion is that the experiment as
parameterized cannot be powered; choosing A means choosing NOT to run (or
re-parameterizing Δ* upward, e.g. Δ*=−1.5% ⇒ ~159–339 sessions, feasible but
only detectable if the prospect effect is as large as the pooled historical
estimate).

**OPTION B — no formal power claim; operational feasibility gate only:** the
primary runs once at the §14 operational minimum (≥180 valid sessions, ≥200
veto events, ≥600 control events, ≥50 tickers) with the explicit pre-registered
warning: **a non-rejection under Option B cannot distinguish "no effect" from
"underpowered"** and supports only a CONTINUE-or-CLOSE decision on the parked
observation — never a confirmatory claim.

The chosen option, and if A the σ and re-parameterized Δ*, must be recorded in
the activation manifest. **[O-11: choose A or B; A-σ and Δ* if A.]**

## 15. STOPPING RULE

The primary test runs EXACTLY ONCE, when §14 is first satisfied. Interim effect
inspection, dashboards of s_t, or early stopping are FORBIDDEN. Operational
capture monitoring (coverage/success rates only) is permitted.

## 16. FAILURE RULE

Non-replication (p ≥ α, or θ̂ > Δ*, or both) ⇒ candidate classified **FAIL
(replication failure) — terminal** per the I7/C7 F-classification convention;
no re-specification, no stratum shopping, no rescue. Sample gate unmet by
2027-12-31 ⇒ INFEASIBLE, no claim either way.

## 17. MISSING / INCOMPLETE CAPTURE

Outages logged (run_log + dated outage note). Missing cells stay missing; no
vendor-refetch backfill enters the prospective cohort; imputation forbidden.
Coverage < 70% of intended cells for > 5 consecutive admitted sessions ⇒
deviation record; ≥ 3 deviations ⇒ owner review before continuing.

## 18. PROTOCOL DEVIATIONS

Append-only `prospective_validation/deviation_log.md`, UTC+WIB timestamps,
reason, discoverer. Deviations never rewrite history; the analysis report lists
all deviations.

## 19. REPRODUCIBILITY REQUIREMENTS

Frozen at activation (activation manifest binds all, with UTC/WIB timestamps):
(i) this protocol's SHA256; (ii) `universe_frozen.csv` + SHA256; (iii)
`prospective_capture.py` code_sha256 (already recorded per run); (iv) frozen
analysis-script hash (fixed before the primary run); (v) G-7
`mapping_validation_report.json` + SHA256. Primary analysis runs via the
fail-closed provenance wrapper (`g1_harness/provenance.py` precedent); output
recorded verbatim.

## 20. FORBIDDEN AFTER OUTCOMES ARE VISIBLE

(1) changing thresholds/windows/cells/control band; (2) adding/removing
candidates or reclassifying failures; (3) changing exclusions, costs,
entry/exit, estimator/HAC lag; (4) post-hoc strata beyond §12; (5) re-running
the primary under any variation; (6) retroactive cohort redefinition;
(7) cadence changes in response to signal behavior; (8) inferential language
about non-predeclared endpoints; (9) selective subperiod reporting;
(10) silent protocol edits.

## G-7 SIGNAL-MAPPING VALIDATION — FULL SPECIFICATION (hard pre-activation blocker)

- **Validation population:** ALL retained rows of
  `dataset_b/store/DATASET_B_BROKER_FLOW_STORE_v1.sqlite::raw_responses`
  (30,880 rows, 386 sessions; no sampling — deterministic full corpus).
- **Classification per cell:** UNPARSEABLE (JSON/gzip error) | EMPTY (0 rows AND
  date_echo_match=1) | INCOMPLETE (≥1 row missing its side's value field:
  bval for BUY, sval for SELL) | EVALUABLE (≥1 row, all rows carry values).
- **Expected formula:** `computed = Σ_buy(bval) + Σ_sell(sval)` (sval signed).
- **Comparison target:** production `stockbit_flow.net_value` for the same
  (ticker, session); cells without a production row are reported as NO-TARGET
  (excluded from the match rate, counted).
- **Tolerance:** |computed − net_value| / max(1, |net_value|) ≤ 0.005 (both are
  integer-Rp aggregates; tolerance covers string-float serialization only).
- **Pass threshold:** exact-match rate ≥ 99% among EVALUABLE cells that have a
  production target, AND the EVALUABLE share of the corpus is reported. If the
  EVALUABLE share is < 50%, G-7 additionally FAILS on coverage and the mapping
  must be re-specified (never silently tolerated).
- **Output artifact:** `prospective_validation/mapping_validation_report.json`
  (deterministic: full corpus, sorted keys/cells, canonical JSON, counts +
  pass rate + per-class histograms), plus `.sha256`.
- **Independent verification:** the checker re-runs the same frozen validator
  script and MUST reproduce a byte-identical report (determinism is part of the
  check). **No prospective collection starts before G-7 PASS.**

## CRO / OWNER-OPEN ITEMS

| # | Item | Proposed | Status |
|---|---|---|---|
| O-1 | α (one-sided) | 0.05 | OPEN |
| O-2 | Δ* economic criterion | −0.50% | OPEN |
| O-11 | Power OPTION A (formal; infeasible at Δ*=−0.50%) or OPTION B (no power claim; operational gate + uninformative-null warning) | B | OPEN |
| O-3 | σ for Option A if chosen (corpus: sd 11.13% / MAD 7.59% / winsor 8.76%) | n/a under B | OPEN |
| O-4 | operational minimum sample (180 sessions / 200 veto / 600 control / 50 tickers) | as stated | OPEN |
| O-5 | capture cadence & cutoff (EOD ≥18:30 target; admissible ≥16:10; T+5 tolerance) | as stated | OPEN |
| O-6 | universe roster source/freeze procedure (T0 snapshot query fixed in §3) | as stated | OPEN |
| O-7 | G-7 acceptance threshold (≥99% conditional; EVALUABLE share ≥50%) | as stated | OPEN |
| O-8 | deviation-log format & weekly coverage audit | as stated | OPEN |
| O-10 | token/credential uptime handling for capture | — | OPEN |
| O-12 | estimand decision: proceed with the day-weighted primary despite its +0.17% in-sample disclosure, or close the parked candidate now without prospective work | proceed | OPEN |
