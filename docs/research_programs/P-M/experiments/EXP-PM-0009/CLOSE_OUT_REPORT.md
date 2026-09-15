# EXP-PM-0009 — Close-Out Report (governance closeout)

> Post-execution governance closeout for the single registered execution of **HYP-PM-0009**, performed
> on Owner instruction 2026-09-15. Scope limited to: receipt verification, artifact preservation,
> append-only registry/decision-record updates, integrity checks. **No rerun, no parameter change, no
> variant, no rescue analysis, no explanation-seeking analysis.**

## 1 · Receipt verification — R2 is the single valid registered execution

- `results.json` → `run_id: EXP-PM-0009/R2`, `run_utc: 2026-09-15T01:41:30Z`, in-script integrity gate
  **19/19 PASS** (prereg sha `d19dfd0f…`, cohort `e1375264…fba`, candidate spec `76a96545…`, calendars
  `5012be23…`/`a7a4eedf…`, ledger 82,814 MECE — all re-verified inside the run).
- Executor self-hash in `results.json.provenance.script_sha256` (`d2e7a9a2…`) matches the on-disk
  script byte-for-byte.
- Primary: θ_primary = +0.0337% · NW HAC t (lag 5) = 0.1102 · two-sided p = 0.912223 · 64 daily
  observations (6 skipped dates counted) · θ_net sensitivity = −0.5663% (sensitivity only).
- Classification recorded exactly once, in-script and in `MANIFEST.md`: **FAIL (F2 · prediction failure)**.
- Repository provenance: registration commit `e0e3f91`; `HYP-PM-0009_REGISTERED.md` clean at execution
  time; cohort store hash re-verified post-execution, unchanged.

## 2 · Artifact preservation (unchanged from run time)

| Artifact | Role | Disposition |
|---|---|---|
| `run_exp_pm_0009.py` | executor (sha `d2e7a9a2…`) | preserved unchanged |
| `results.json` | R2 full results + provenance | preserved unchanged |
| `execution.log` | R2 run transcript | preserved unchanged |
| `MANIFEST.md` | execution receipt (12 items) | preserved unchanged |
| `execution_r1_INVALID_defect.log` | R1 defect transcript | preserved verbatim as INVALID history |
| `results_r1_INVALID_defect.json` | R1 defect record | preserved verbatim as INVALID history |

## 3 · R1 → R2 implementation-defect record (implementation correction only)

R1 (2026-09-15T01:39:02Z) aborted as **INVALID**: the exit-leg index was computed as `eff[i+k]`, which
for the primary k=1 equals the **entry** session, so `fwd_return = close(t+1)/close(t+1) − 1 ≡ 0` —
the registered estimand (`close(t+2)/close(t+1) − 1`) was never evaluated (θ exactly 0.000000,
NW_t = NaN). The correction changed **only the index arithmetic** so the code computes the already-frozen
formula (exit `eff[i+1+k]`; X6 consecutivity guard and CA window extended consistently). Deterministic
cross-check: R2's k=1 arm reproduces R1's accidentally-shifted k=2 arm exactly (θ 0.0337%, t 0.1102,
p 0.912223) — same numbers, confirming a pure one-session shift. **No substantive registered field
(hypothesis, H0/H1, endpoint, cohort, exclusions, estimator, thresholds, timing windows, inference,
decision rule) was changed at any point**; the frozen block hash `d19dfd0f…` verifies unchanged after
execution and after closeout.

## 4 · Registry / decision-record updates made (append-only)

| File | Change |
|---|---|
| `FAILURE_ENTRY.md` (this directory) | **NEW** — T7 receipt `FAIL-PM-0009` (immutable) |
| `CLOSE_OUT_REPORT.md` (this file) | **NEW** — closeout record |
| `docs/research_programs/FAILURE_REGISTRY.md` | appended row **FAIL-PM-0009**; F-mode table F2 count 3 → 4; denominator N=5 → N=6; notes bullet |
| `docs/research_programs/HYPOTHESIS_REGISTRY.md` | HYP-PM-0009 row → **FAILED (F2) 2026-09-15**; notes bullet extended with the executed outcome; family ledger cell annotated; Last-updated → 2026-09-15 |
| `docs/research_programs/EXPERIMENT_LEDGER.jsonl` | appended one `record_type: hypothesis` record for HYP-PM-0009 / EXP-PM-0009 |
| `docs/roadmap/DECISION_LOG.md` | appended **D-051** — execution outcome + classification + closeout |

`HYP-PM-0009_REGISTERED.md` was **not modified** (house convention: REGISTERED records stay untouched
post-execution; outcome lives in the registry/ledger/failure docs).

## 5 · Interpretation constraints carried into the record

- **"Non-rejection is not evidence of absence."** I7 carries **no power claim** (D-050); recorded in the
  failure entry, the ledger record, and D-051. Must never be reported or used as evidence of absence.
- **R7 PIT provenance limitation retained** in every record (verification, not availability; 200/200
  source spot-check matches).
- θ > 0 but indistinguishable from zero: inside the composite H0 as a non-rejection, never a reversed finding.

## 6 · Known gaps / governance notes

- `research.db.failure_registry` was **not** written — consistent with post-EXP-PM-0003 precedent (the
  docs-side ledger is the record of note; the DB gap for FAIL-PM-0003 remains open). Owner may direct a
  DB backfill separately; not done here to keep the closeout docs-only and append-only.
- No `EVIDENCE_PACKAGE.md` (C2 refutation product, R12) was generated — outside the enumerated closeout
  scope; available on Owner direction.

## 7 · Terminal status

**HYP-PM-0009: FAIL — F2 · prediction failure. Terminal (HL-3).** Counted permanently in
P-M {I5, I6, I7, I12} (X8). Continuation only via T12 supersession — a new registration consuming its
own slot. Next action is **Owner-level**: selection of the next already-authorized research candidate,
if one exists. Nothing further is authorized on I7.
