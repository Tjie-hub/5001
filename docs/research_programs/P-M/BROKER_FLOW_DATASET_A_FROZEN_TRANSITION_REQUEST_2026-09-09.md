# Dataset A — FROZEN Transition Request

**Status:** **DRAFT REQUEST — NOT YET APPROVED.** All five F-1…F-5 prerequisites are now closed. This document
requests, and prepares the record for, Dataset A's transition to `FROZEN`. **It does not itself perform that
transition.** No lifecycle field anywhere in the corpus is changed by this document.
**Date:** 2026-09-09 · **Program:** P-M · **Object:** `DS-broker_flow-idx80-nonpit-2025_2026v1` (Dataset A,
DECLARED D-040, FINGERPRINTED D-041)
**Builds on:** `BROKER_FLOW_DATASET_A_FROZEN_GATE_2026-09-09.md`, `..._REGIME_CHARACTERIZATION_2026-09-09.md` —
neither modified.

---

## 1. F-1 through F-5 — final re-verification

| # | Item | Status | Evidence |
|---|---|---|---|
| F-1 | `broker_flow` fingerprint | **Valid, unchanged.** `329b22e49f0ef882b6da031f437e9d87084d2863837ebf8c830de362b7942558` | Spot-checked this session: row count 1,222,713, roster 79, `2026-08-25` count 0 — all identical to computation time |
| F-2 | Formal coverage receipt | **Valid, unchanged.** 30,652 expected / 30,652 accounted / 0 missing | Same spot-check; no drift |
| F-3 | `corporate_actions_applied` | **CLOSED** — zero split events for any Dataset A ticker in-window; question immaterial to this population (137 dividends occurred, irrelevant to lot/price-basis) | `BROKER_FLOW_DATASET_A_FROZEN_GATE_2026-09-09.md` §A |
| F-4 | Consumer-formula audit | **CLOSED** — 6 real formula-consumers found (expanded from the original 4), all correct; no defect | `BROKER_FLOW_DATASET_A_FROZEN_GATE_2026-09-09.md` §B |
| F-5 | `regime_classification` | **CLOSED** — populated via D-042 (Option B), lightweight IHSG-based characterization, not O15 | `BROKER_FLOW_DATASET_A_REGIME_CHARACTERIZATION_2026-09-09.md`, D-042 |

**All five closed. No open F-item remains.**

## 2. CUSTODY / LOCKED requirement — re-confirmed

`RESEARCH_OBJECT_MODEL.md` §3.2: Dataset custody class is **C-FROZEN-ON-USE, "Frozen on fingerprint."** Per
`CUSTODY_MODEL.md` §3.1/§4.1, this means the custody asset-state's frozen condition (the practical content of
`LOCKED`) was triggered **at FINGERPRINTED (D-041)**, not deferred to a separate step. **No additional custody
action is required for O4's FROZEN transition** — already established in
`BROKER_FLOW_DATASET_A_FROZEN_GATE_2026-09-09.md` §D, unchanged by this request.

## 3. Owner action required to formally enter FROZEN

**Nothing further is technically outstanding.** Proposed wording, **not applied**:

> ### D-043 · Dataset A `DS-broker_flow-idx80-nonpit-2025_2026v1` transitioned to FROZEN
> **Status:** [PENDING OWNER APPROVAL] · **Date:** [date] · **Type:** O4 Dataset lifecycle transition · **Approval authority:** Owner
>
> **Decision.** Dataset A enters `FROZEN` ([[RESEARCH_OBJECT_SCHEMA]] §3.4). F-1…F-5 ([[DECISION_LOG]] D-040,
> D-041, and this session's F-3/F-4 closure + D-042's F-5 closure) are all satisfied. The CUSTODY asset-state's
> frozen condition was already triggered at FINGERPRINTED (D-041, per ROM v2.0 §3.2 "Frozen on fingerprint") and
> requires no separate action here. `provenance_hash` remains
> `329b22e49f0ef882b6da031f437e9d87084d2863837ebf8c830de362b7942558`, unchanged.
>
> **Not authorized by this transition:** hypothesis registration or empirical testing — each remains gated on
> [[HYPOTHESIS_LIFECYCLE]] G1 and requires its own future decision. Amendment after FROZEN is prohibited per
> [[RESEARCH_OBJECT_SCHEMA]] §3.4 Ownership ("Amend after freeze: prohibited") — any future correction is a new
> Dataset version, per Versioning ("Immutable on fingerprint. A revised dataset is a new Dataset").
>
> **Files changed:** this entry · `BROKER_FLOW_DATASET_ADMISSION_DRAFT_2026-09-09.md` §G (FROZEN row) ·
> `BROKER_FLOW_DATASET_A_FROZEN_TRANSITION_REQUEST_2026-09-09.md` (status annotation only).
>
> **Related:** D-040, D-041, D-042 · `BROKER_FLOW_DATASET_A_FROZEN_GATE_2026-09-09.md` ·
> `BROKER_FLOW_DATASET_A_REGIME_CHARACTERIZATION_2026-09-09.md`.

**To formally enter FROZEN, the Owner needs to do exactly one thing: explicitly instruct that this transition be
recorded** (e.g., "Approve and record D-043"). No further evidence, receipt, or investigation is required first.

## 4. Worktree note

This document is the only new file this step produced beyond D-042/the characterization artifact (already
recorded). No other file, code, or DB write occurred.
