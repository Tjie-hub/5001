# Dataset A — DECLARED Transition Request

**Status:** **DRAFT REQUEST — NOT YET APPROVED.** This document requests, and prepares the record for, Dataset
A's transition to `DECLARED` (O4 lifecycle, [[RESEARCH_OBJECT_SCHEMA]] §3.4). **It does not itself perform that
transition.** No lifecycle field anywhere in the corpus is changed by this document; the admission draft's own
Governance Checklist (§G) still reads "DECLARED: NOT ACTIONED" until the Owner acts on §4 below.
**Date:** 2026-09-09 · **Program:** P-M · **Object:** `DS-broker_flow-idx80-nonpit-2025_2026v1` (Dataset A)
**Builds on:** [[DECISION_LOG]] D-032…D-039 · `BROKER_FLOW_DATASET_A_DECLARED_READINESS_2026-09-09.md` — neither
is modified by this document.

---

## 1. Gate closure summary — R-1…R-10

| # | Receipt | Status | Closed by |
|---|---|---|---|
| R-1 | Persisted Owner authorization receipt | **CLOSED** | D-038 — D-032+D-033 ruled sufficient |
| R-2 | Backfill completion receipt | **CLOSED** | D-035 — FULLY RECONCILED, exact accounting identity |
| R-3 | Pinned IDX80 roster + hash | **CLOSED** | This session — 79 tickers, SHA-256 `7d4eb1004e7d1e83153eede9a5d4e458ab5298ac1a4a4d7fa301f095f665eee0` |
| R-4 | Production boundary verification receipt | **CLOSED** | This session — Dataset-A-exact-scoped row/date/ticker/exclusion check |
| R-5 | Lot-sign evidence receipt | **CLOSED** | This session — DB-VERIFIED, Dataset-A-exact-scoped |
| R-6 | P1/P2 provenance resolution receipt | **CLOSED** | D-034 — resolved by splitting, structural PK/gap-gating argument |
| R-7 | CRO `capability_class` receipt | **CLOSED** | D-037 — Available Today, informed-flow/adverse-selection proxy |
| R-8 | Updated `DATA_FEASIBILITY_STUDY` | **CLOSED** | This session's Phase 2 correction (broker_flow span, `~3.5mo → ~20mo`) |
| R-9 | Dataset ID / registry ruling | **CLOSED** | H-5 — interim non-canonical ID accepted |
| R-10 | Decision persistence | **CLOSED** (working-tree tier) | D-032…D-039, all present in `DECISION_LOG.md`; same tier D-033 already treated as sufficient |

**All ten closed. No open R-item remains.**

## 2. Lifecycle-interpretation and micro-decision closure

| Item | Resolution |
|---|---|
| DECLARED vs REGISTERED (D-1) | **D-036** — orthogonal axes (Option B). DECLARED does not require a fingerprint; fingerprinting stays gated at `FINGERPRINTED`. |
| `capability_class` (D-2) | **D-037** — Available Today, informed-flow/adverse-selection proxy. |
| R-1 sufficiency (D-3) | **D-038** — D-032+D-033 sufficient, no separate artifact. |
| `asset_class` at DECLARED | **D-039** — existing PROPOSED value sufficient, no separate ratification required. |

## 3. O4 field snapshot at the DECLARED gate

| Field | Value at DECLARED | Deferred to |
|---|---|---|
| `dataset_id` | `DS-broker_flow-idx80-nonpit-2025_2026v1` (interim, non-canonical — H-5) | Registry issuance — later, non-blocking |
| `asset_class` | "IDX equities, IDX80 universe (fixed backfill-time roster — not PIT membership)" (PROPOSED, sufficient — D-039) | Ratification/refinement — later gate, if required |
| `resolution` | Daily, broker-level; one row per (ticker, trade_date, broker_code, side) | — (VERIFIED, final) |
| `regime_classification` | Not assigned | `FROZEN` (F-5) |
| `provenance_hash` | Not computed | `FINGERPRINTED` (F-1) |
| `capability_class` | Available Today, informed-flow/adverse-selection proxy | — (APPROVED, final — D-037) |
| `fidelity_limit` | Cannot distinguish: historical IDX80 membership as-known-then; P1/P2 row provenance by inspection; `lot=0 ∧ lot_value>0` semantics; cause of 2026-08-25 gap | — (final at DECLARED; may be refined, not blocking) |
| `proxy_for` | Informed-flow / adverse-selection proxy (not true OFI) | Final mechanism-level assignment — later, at hypothesis binding |
| `point_in_time` | NO for any index-composition-dependent interpretation (VERIFIED via R-3 roster-timestamp receipt) | — (final) |
| `corporate_actions_applied` | Not established | `FROZEN` (F-3) |
| `custody_partition` | Not assigned | Later governance act, not pre-DECLARED |

No field required at `DECLARED` is missing or blocking. Every field deferred to a later gate is deferred by an
explicit, named rule (F-1/F-3/F-5, or a governance act inherently later than DECLARED), not by omission.

## 4. Owner action required to formally enter DECLARED

**Nothing further is technically outstanding.** If the Owner approves this request, the action that would
formally complete the transition is a new DECISION_LOG entry recording it — proposed wording below, **not
applied by this document**:

> ### D-040 · Dataset A `DS-broker_flow-idx80-nonpit-2025_2026v1` transitioned to DECLARED
> **Status:** APPROVED · **Date:** [date] · **Type:** O4 Dataset lifecycle transition · **Approval authority:** Owner
>
> **Decision.** Dataset A enters `DECLARED` ([[RESEARCH_OBJECT_SCHEMA]] §3.4), all ten §J.1 receipts (R-1…R-10,
> [[DECISION_LOG]] D-032…D-039) and the four lifecycle/field micro-decisions (D-036…D-039) having closed with no
> remaining blocker, per `BROKER_FLOW_DATASET_A_DECLARED_TRANSITION_REQUEST_2026-09-09.md`.
>
> **Not authorized by this transition:** FINGERPRINTED, FROZEN, hypothesis registration, or empirical testing —
> each remains gated on its own separate prerequisites (F-1…F-5, [[HYPOTHESIS_LIFECYCLE]] G1) and requires its
> own future decision.
>
> **Files changed:** this entry · `BROKER_FLOW_DATASET_ADMISSION_DRAFT_2026-09-09.md` §G (DECLARED row updated
> from "NOT ACTIONED" to "DECLARED, [date]") · `BROKER_FLOW_DATASET_A_DECLARED_TRANSITION_REQUEST_2026-09-09.md`
> (status annotation only). No code, DB, schema, fingerprint, or freeze operation performed.
>
> **Related:** D-032…D-039 · `BROKER_FLOW_DATASET_A_DECLARED_READINESS_2026-09-09.md`.

**To formally enter DECLARED, the Owner needs to do exactly one thing: explicitly instruct that this transition
be recorded** (e.g., "Approve and record D-040" or equivalent). No further evidence, receipt, or investigation
is required first, per §1–§3 above.

## 5. What DECLARED does not authorize (unchanged, carried forward)

FINGERPRINTED, FROZEN, hypothesis registration, empirical testing, or any production/data/schema modification.
Each remains gated on its own separate, not-yet-satisfied prerequisites (F-1…F-5).

## 6. Worktree note

This document and `docs/roadmap/DECISION_LOG.md` (D-039) are the only files touched by this turn. Neither is
committed. No lifecycle field was changed anywhere in the repository by this document.
