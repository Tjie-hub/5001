# R-10 — Registry Lifecycle Enforcement (Design)

**Status:** design approved 2026-07-12 · **Track:** Research Master Plan v2 open item **R-10**
**Prereq:** Phase C gatekeeper (`gate_decisions`), Phase 5 forward tracker (`phase5_tracker.RULE`)
**Deliverable:** spec → plan → **full TDD build**. Read-only w.r.t. trading logic; the only
production file touched is `engine/registry_loader.py` (adds WARN-level validation, changes no
load decision).

## 1. Problem

`engine/registry_loader.py` loads entries whose `status ∈ {APPROVED, SHADOW}` after checking
that **fields exist** — never that the status was **earned**. `status: APPROVED` is a
hand-typed YAML string. `NR7_BULL` governs `approved_universe` today while:
- its manifest records `evidence_summary.shadow: {trades: 0, verdict: pending}` (no forward
  evidence), and
- its own Phase C `gate_decisions` verdict (2026-07-12) is **REJECT at walk_forward**.

This is the **R-10 shadow-approval door**: a promotion with no receipts. Phase D just widened
the post-hoc surface, making this the binding research-integrity risk (see
[[project_phase_d_market_regime_engine]] and the `NR7_BULL_LOWLIQ_v1` pre-registration).

## 2. Decisions locked in brainstorming

| # | Decision | Choice |
|---|---|---|
| 1 | Enforcement posture | **CI-static gate (hard) + runtime WARN (non-breaking)** |
| 2 | Existing NR7_BULL entry | **Grandfather** via shrink-only allowlist + remediation deadline (Phase 5 timebox 2027-01-08) |
| 3 | Deliverable | spec → plan → full TDD build |

## 3. Lifecycle bound to an evidence receipt

A status must be **earned**. The required receipt lives in the entry's **manifest** (immutable,
git-pinned, already the home of `config_hash`/`corpus_snapshot`) so CI verification is hermetic
(no live DB needed).

| Status | Meaning | Required receipt |
|---|---|---|
| CANDIDATE | hypothesis | none (not loaded) |
| **SHADOW** | cleared retrospective gate; accruing forward | `evidence.gate_decision.final_state = PROMOTE_TO_FORWARD_TEST` |
| **APPROVED** | forward bar cleared | the SHADOW PROMOTE **plus** `evidence.forward.verdict = GO` with `n ≥ 15` and `exp_pct ≥ 0.50` |
| SUSPENDED / RETIRED / SUPERSEDED | off | none (not loaded) |

Consequence: the shadow-N=0 door is structurally closed — APPROVED is unreachable without a
forward GO; SHADOW is unreachable without a Phase C PROMOTE. (NR7's Phase C verdict is REJECT, so
under these rules it is neither compliant-APPROVED nor compliant-SHADOW → it is grandfathered
debt, §6.)

## 4. Manifest `evidence:` block (schema addition)

Formalises the existing ad-hoc `evidence_summary`. Added to `registry/SCHEMA.md`.

```yaml
evidence:
  gate_decision:                 # required for SHADOW and APPROVED
    decision_id: <hex>           # gate_decisions.decision_id (provenance)
    final_state: PROMOTE_TO_FORWARD_TEST
    config_hash: <gate_config hash at decision>
    dataset_fingerprint: <corpus fingerprint>
  forward:                       # required for APPROVED only
    verdict: GO
    n: <int>                     # realized forward trades
    exp_pct: <float>             # realized net %/trade
    rule: {min_n: 15, go_exp: 0.50}   # the frozen phase5_tracker.RULE bar it cleared
    as_of: <YYYY-MM-DD>
```

The block is a **self-contained snapshot** (like `config_hash`): CI validates the claim clears
the bar; runtime MAY cross-check against `gate_decisions` / `phase5_tracker` and WARN on drift
(optional, non-breaking).

## 5. Enforcement — two layers

**5a. CI-static (hard) — `tests/test_registry_lifecycle.py`** (mirrors the `test_research_data_fence.py`
allowlist pattern). For each `edge_registry.yaml` entry with `status ∈ {SHADOW, APPROVED}`:
- load its manifest; assert `evidence.gate_decision.final_state == PROMOTE_TO_FORWARD_TEST`;
- if APPROVED, also assert `evidence.forward.verdict == GO ∧ n ≥ min_n ∧ exp_pct ≥ go_exp`;
- bars are read from `phase5_tracker.RULE` + `gate_config` (no magic numbers);
- entries in the grandfather allowlist are exempt (§6);
- **any non-allowlisted violation fails the build.**

**5b. Runtime WARN (non-breaking) — `engine/registry_loader.py`.** A new pure helper
`validate_evidence(entry, manifest, rule)` returns a list of violation reasons. In
`load_registry`, a SHADOW/APPROVED entry that fails validation and is **not** grandfathered
**still loads** but:
- emits `fail_open_alarm("edge_registry", "<ident> lifecycle-unverified — <reason>", notify=False)`
  (reusing the existing WARN channel), and
- is counted in the returned dict as `violations` and surfaced by `startup_summary`
  (`n_violations`) and `announce_registry`.

No load/skip decision changes — the entry set the app governs is identical to today.

## 6. NR7_BULL grandfather + remediation

```python
# engine/registry_loader.py — shrink-only; new violations are NOT added here, they fail CI.
_LIFECYCLE_DEBT = {
    ("NR7_BULL", 1): {
        "reason": "APPROVED 2026-07-04 under the pre-Phase-C generalization bar; "
                  "Phase C gate=REJECT and shadow N=0. Governs on legacy grounds.",
        "remediation": "Phase 5 forward test (phase5_tracker); deadline 2027-01-08.",
        "deadline": "2027-01-08",
    },
}
```

- CI: allowlisted → exempt from the hard failure, **but** a dated assertion
  (`test_grandfathered_debt_not_past_deadline`) starts **failing after 2027-01-08** if the entry
  is still non-compliant → forces a demote/review at the Phase 5 timebox.
- Runtime: grandfathered entries log at INFO ("known lifecycle debt") and are counted separately
  (`n_debt`) from live violations.
- The debt set is **shrink-only** (documented in-code, like `_ROUTES_WRITE_DEBT`): entries may be
  removed as they remediate, never added.

## 7. Testing (TDD)

`tests/test_registry_lifecycle.py` + loader unit tests:
- SHADOW entry whose manifest lacks a PROMOTE gate_decision → CI check FAILS.
- APPROVED entry with a PROMOTE but no forward GO → FAILS.
- APPROVED entry with PROMOTE + forward `{GO, n≥15, exp≥0.50}` → PASSES.
- APPROVED entry with forward `{GO, n=10}` (below min_n) → FAILS.
- The real `NR7_BULL` entry → would FAIL, but is exempted by the allowlist (assert exemption
  applies to it and to nothing else).
- A *new* fabricated non-compliant entry not in the allowlist → FAILS (proves the door is shut).
- `test_grandfathered_debt_not_past_deadline`: for each debt entry, assert `today < deadline`
  (fails automatically once the deadline passes).
- Loader unit: `validate_evidence` returns the right reasons; `load_registry` still returns the
  same `entries` for a non-compliant non-grandfathered entry but with it counted in `violations`;
  `startup_summary` reports `n_violations` / `n_debt`.
- Full `pytest` green; the real registry loads today with `n_violations = 0`, `n_debt = 1`
  (NR7_BULL), governance unchanged.

## 8. Non-goals

- No change to any load/skip decision or to `approved_universe` membership (non-breaking).
- No new promotion *authoring* automation — humans still author entries; this only *verifies* them.
- No demotion of NR7_BULL in this build (grandfathered; the deadline test enforces the timebox).
- No change to Phase C, Phase 5, or trading logic.

## 9. Follow-ups

- When the Phase 5 forward test resolves NR7_BULL, either populate a compliant `evidence.forward`
  block (if GO) or demote (if NO-GO) and remove it from `_LIFECYCLE_DEBT`.
- Optional runtime cross-check of the manifest receipt against live `gate_decisions` /
  `phase5_tracker` (drift detection) — deferred; the snapshot is authoritative for CI.
