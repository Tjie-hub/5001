# Research Master Plan — v3

# 🔒 ARCHITECTURE BASELINE — FROZEN

**Freeze status:** FROZEN — permanent architectural baseline, superseding v2.
**Drafted:** 2026-07-14
**Ratified & frozen:** 2026-07-14 (owner ratification; see §8 ratification record).
**Supersedes:** Research Master Plan v2 (frozen 2026-07-12), archived at
`docs/archive/RESEARCH_MASTER_PLAN_v2.md`. v2 is retired as the baseline of record;
it remains readable for history only.
**Branch of record:** `ops/hardening-2026-07-10`
**Trigger:** (1) implementation reality since the v2 freeze — Phases C and D are
built, R-10 is closed, Phase E is in flight; (2) an adversarial design review
(2026-07-14) that identified four vulnerabilities in the frozen architecture.

> **What v3 changes and what it does not.** The roadmap keeps **exactly** the
> eight phases A–H — no phase is added, removed, or reordered, so this document
> is a legal *amendment* under v2 change control, not a redesign. v3 does three
> things: (§2) records post-freeze implementation status; (§3) resolves the four
> adversarial findings as amendments **inside** existing phases; (§4–§6) updates
> the phase specs, invariants, and open items accordingly.
>
> **The append-only evidence spine is untouched.** Nothing in v3 alters the
> schema or semantics of `research_runs`, `gate_decisions`, `gate_evidence`,
> `regime_profiles`, or the Phase E evidence tables. v3 changes *enforcement and
> configuration* layers only.

---

## Position in the Research OS

This plan is **Program P0** ("v3 Edge Pipeline") inside the Research OS institutional roadmap.
See [[RESEARCH_OS_MASTER_ROADMAP]] for the institutional roadmap (Layers L0–L8, Programs P0–P6)
and [[RESEARCH_OS_RECONCILIATION]] for the authority rule between this document and that one:
this plan remains canonical and frozen for its own scope — the executed v3 pipeline and its
invariants (§5) — while the Research OS is canonical for institutional and scientific-method
scope. On any conflict about a mechanism already built here, this plan wins; on any conflict
about scientific method or institutional governance, the Research OS wins
([[RESEARCH_OS_RECONCILIATION]] §5).

---

## 1. Roadmap at a glance (status updated 2026-07-14)

| Phase | Name | Status v2 (2026-07-12) | Status v3 (2026-07-14) |
|---|---|---|---|
| **A** | Research Foundation | ✅ Completed | ✅ Completed |
| **B** | Statistical Validation & Audit Resolution | ✅ Completed | ✅ Completed |
| **C** | Statistical Gatekeeper | 🔒 not started | 🟢 **IMPLEMENTED** 2026-07-12 — `research/gatekeeper/`, 8-stage pipeline, REJECT/WATCHLIST/PROMOTE, **exact DSR from the real scan distribution (Phase B proxy retired)**, golden NR7→WATCHLIST, 43 tests. ✅ **Live end-to-end run verified at HEAD (`9db223e`) 2026-07-14** — NR7 Breakout on the 186-ticker liquid corpus (1127 trades) → REJECT at `walk_forward` (BULL consistency 47.96% < 50%), reproducing the 2026-07-12 verdict on refreshed data; decision + 8 stage-evidence rows persisted append-only (run `c967502e`). Completion criteria met. |
| **D** | Market Regime Engine | 🔒 planned | 🟢 **BUILT** 2026-07-12 — `research/regime/`, hierarchical taxonomy (3-regime primary + declarable vol/liq axes), append-only `regime_profiles`, gate_config v2 + widen-only hook. **Key empirical finding: NR7 BULL edge is liquidity-conditional (LOW_LIQ +2.29% vs HIGH_LIQ −0.47%)** — the flat-taxonomy assumption was falsified by data. |
| **E** | Research Knowledge Base | 🔒 planned | ✅ **COMPLETED** 2026-07-14 — plan `2026-07-14-phase-e-research-knowledge-base.md`; all 11 tasks done (config, models, storage, links/failures, ingest, trace, registries, backfill, CLI, fence, receipt-bound `set_status`), committed `fffa6f7`; v3 amendment A1 (Task 11) ratified. |
| **F** | Edge Discovery Framework | 🔒 planned | 🔒 planned — **new hard prerequisite: R-5 physical DB split (§3.3)** |
| **G** | Portfolio Intelligence | 🔒 planned | 🔒 planned |
| **H** | Adaptive Edge Lifecycle | 🔒 planned | 🔒 planned — R-10 prerequisite now **closed** (§2); new prerequisite: signed receipts (§3.4) |

Dependency chain unchanged: `A → B → C → D → E → F → G → H`, single runtime
loop H→C. All v2 §4 and §6 content carries forward verbatim.

---

## 2. Post-freeze delta log (the "new found")

Recorded per v2 §13 (no silent divergence — every post-freeze fact is logged here):

1. **Phase C implemented** (2026-07-12, TDD, on `ops/hardening-2026-07-10`).
   The v2 §8 mandate is satisfied in code: DSR is computed from the complete
   distribution of actual scan Sharpes; the 42-cell proxy is retired. DSR is
   PASS/WATCH-only (never hard-fails a candidate on its own). **Closed
   (2026-07-14):** the gate ran end-to-end on the live corpus at HEAD
   (`9db223e`) — NR7 Breakout, 186 liquid tickers, 1127 trades → REJECT at
   `walk_forward` (BULL consistency 47.96% < 50%), reproducing the 2026-07-12
   verdict on refreshed data (dataset_fingerprint `fcc867cb…`); the decision +
   8 stage-evidence rows are persisted append-only (run `c967502e`). Phase C's
   completion checklist is satisfied.
2. **Phase D built** (2026-07-12). The regime taxonomy is hierarchical rather
   than the v2-sketched flat 3×2×2 grid: a 3-class primary (BULL/BEAR/SIDEWAYS)
   with volatility/liquidity axes *declared per-strategy* rather than imposed
   globally. Empirical justification: the liquidity axis is not decorative —
   it flips the sign of the flagship edge. A pre-registered follow-up hypothesis
   (`NR7_BULL_LOWLIQ_v1`, prereg 2026-07-12) exists for the BULL∧LOW_LIQ sub-cell.
3. **R-10 closed** (2026-07-12). Registry lifecycle enforcement is live:
   APPROVED/SHADOW registry states are CI-hard bound to a manifest evidence
   receipt (SHADOW ⇒ Phase C PROMOTE receipt; APPROVED ⇒ additionally a Phase 5
   GO receipt). `NR7_BULL` is grandfathered via a shrink-only `_LIFECYCLE_DEBT`
   list with deadline 2027-01-08. Invariant #10's known exception is now fenced.
4. **Phase E in flight** (2026-07-14). Three new append-only tables
   (`hypotheses`, `hypothesis_links`, `failure_registry`); the only mutable
   surface is `hypotheses.status/notes` via the `set_status()` gateway.
5. **Adversarial design review received** (2026-07-14) — four findings, §3.

---

## 3. The four adversarial findings and their v3 resolutions

An external adversarial review challenged the frozen architecture on four
fronts. Each finding was verified against the actual mathematics and code
before acceptance; two were accepted as stated, two were accepted in spirit but
redirected to the correct mechanism. Each resolution below names the phase it
amends and the **rejected alternative**, so the reasoning survives.

### 3.1 Finding V3-1 — Multiplicity scaling ("death spiral") — *amends Phase C*

**Claim:** as the Knowledge Base accumulates trials forever, the DSR/FWER
penalty grows unboundedly and eventually nothing can pass the gate.

**Verified assessment:** the hurdle grows as `√(2·ln N)` — going from N=100 to
N=50,000 moves it from ≈2.33 to ≈3.9 null-Sharpe units; doubling it needs
N≈10⁸. There is **no mathematical death spiral** at realistic trial counts.
The *real* risk is mis-scoped families: pooling all history into one global
family taxes every future claim with unrelated garbage.

**Resolution (Phase C amendment, gate_config change):**
- **(a) Family scoping by data epoch and feature space, never wall-clock.**
  The multiplicity family key is `(dataset_fingerprint lineage, feature_space_hash)`
  where `feature_space_hash` fingerprints the primitive set (indicators,
  entry/exit family, universe). Trials accumulate within their family key
  **forever**. A 2028 hypothesis on a new feature space is a new family — it is
  not taxed by 2026 garbage in an unrelated space. The family definition used
  is recorded **in the evidence bundle** of every decision, so family scoping
  is itself auditable and cannot be silently gerrymandered.
- **(b) Effective-N, not raw N.** Correlated trials (e.g., 5,000 GP sweeps over
  neighbouring parameters) are discounted to an effective independent count,
  Kish-style: `N_eff = N / (1 + (N−1)·ρ̄)` over the trial-return correlation
  matrix (extends the variance term DSR already carries). Raw N remains in the
  evidence bundle alongside N_eff.
- **(c) Loosening safeguard.** Any family redefinition or move from raw-N to
  N_eff that *lowers* a hurdle is a **major gate_config version bump requiring
  a documented amendment**, and never applies retroactively: an already-REJECTED
  decision stays REJECTED (append-only); a candidate may only be re-run through
  the gate as a **new** decision under the new config version.

**Rejected alternative — the reviewer's proposed N-decay half-life:** a
wall-clock decay on historical trials is a **data-snooping amnesia knob**. The
optimal attack is: run garbage, wait out the half-life, re-mine the same space
against a reset hurdle. Time-based multiplicity decay is **prohibited** in this
architecture (new invariant #12, §5).

### 3.2 Finding V3-2 — Chronological OOS gate ("regime blindness") — *amends the frozen forward-test rule + Phase 5 usage*

**Claim:** a 6-calendar-month forward test is regime-sampled by luck. A
strategy overfit to one regime can be promoted on a lucky uninterrupted run of
that regime and then blow up on the first transition.

**Verified assessment:** **accepted as stated.** Phase D's own finding (the
NR7 edge flips sign across the liquidity axis) proves edges here are
regime-conditional; a purely chronological window is the wrong sampling frame.

**Resolution (forward-test rule v2 — the promotion bar is regime-stratified
and the promotion itself is regime-scoped):**
- **(a) Pooled bar unchanged:** N ≥ 15 trades, ≥ +0.50%/trade, 6-month timebox.
- **(b) Per-regime validation floors (draft defaults, ratify before freeze):**
  regime cell `r` is *validated* iff `N_r ≥ 8` and `expectancy_r ≥ +0.25%/trade`.
- **(c) Regime-scoped promotion:** GO promotes the strategy **only for the set
  of regimes it validated**. Unobserved or unvalidated regimes remain SHADOW.
  The Phase D regime engine **fences live capital at runtime**: no live signal
  outside the validated regime set. Promotion scope can only *narrow* relative
  to the claim, never widen.
- **(d) Coverage replaces the calendar as the binding constraint:** "six months
  of pure RECOVERY" no longer promotes a strategy for all weather — it promotes
  a RECOVERY-scoped strategy, or nothing, exactly matching the evidence earned.
  A single-bucket "concentration guard" is thereby structural rather than a
  bolt-on ratio test.
- **(e) Grandfather clause:** the live NR7 forward test was pre-registered
  under rule v1 and **completes under rule v1** — changing an OOS rule mid-test
  is itself a form of snooping. Rule-v2 regime *scoping* still applies at
  promotion time, because scoping is a deployment constraint that narrows,
  never a test-outcome change.

**Rejected alternative — the reviewer's "must pass OOS in *all* claimed
regimes before promotion":** PANIC may not occur for years; gating on live
observation of every regime re-creates Finding V3-1's ossification through the
back door. Scoped promotion deploys exactly the evidence held — no less, and
critically no more.

### 3.3 Finding V3-3 — Research velocity ("CI friction asphyxiation") — *amends Phase E granularity + Phase F prerequisites + R-5*

**Claim:** with all research tables behind a CI fence, a 5,000-trial automated
sweep implies 5,000 synchronous CI handshakes, so researchers will bypass the
system ("shadow tests").

**Verified assessment:** **wrong mechanism, right instinct.** The write fence
(`tests/test_research_data_fence.py`) is a *static code-path check* that runs
on commits — research-domain code writes research tables freely at runtime with
zero CI involvement. There is no per-row handshake. The *actual* wall is
single-writer SQLite contention on `walkforward.db` (this repo's documented
recurring failure mode) plus a granularity error waiting to happen.

**Resolution:**
- **(a) Granularity law (Phase E amendment):** one automated sweep = **one**
  `research_run` + one cell-matrix artifact — *not* 5,000 `hypotheses` rows and
  *not* 5,000 `failure_registry` rows. The Hypothesis Library spine is for
  **pre-registered hypotheses**; mining exhaust lives in the run artifact, and
  a sweep that dies contributes **one aggregate, fingerprinted failure row**.
  This is the reviewer's "commit the final cryptographic aggregate" — adopted.
- **(b) Batch transactions:** research writers must wrap sweep persistence in a
  single transaction (no per-row commits inside loops).
- **(c) R-5 elevated (Phase F prerequisite):** the physical research/production
  DB split moves from "KEEP OPEN" to a **hard, blocking prerequisite of
  Phase F**. Discovery-volume writes never contend with the production reader
  set. (R-7 parallel-WF wiring remains the throughput companion item.)

### 3.4 Finding V3-4 — Human override of `set_status()` — *amends Phase E + Phase H prerequisites*

**Claim:** the mutable `status` label lets a sufficiently senior human invoke
`set_status(..., "VALIDATED")` and override the statistical gatekeeper.

**Verified assessment:** partially mitigated already — the **capital-facing**
layer (edge registry) is R-10 receipt-bound, so a Phase E label flip alone
moves no capital; and `check_status_consistency` flags VALIDATED-over-REJECT —
but only *advisorily*. The residual hole is real: the label layer itself will
accept an evidence-free promotion-track status.

**Resolution:**
- **(a) Receipt-bound status transitions (Phase E, implemented as plan
  Task 11):** transitions into the promotion track are structurally gated —
  `set_status(→FORWARD_TESTING)` **requires** a linked `gate_decisions` receipt
  with `final_state = PROMOTE`; `set_status(→VALIDATED)` requires the PROMOTE
  receipt **plus** a forward-test receipt reference. A mismatch raises; the
  binding is recorded as a `hypothesis_links` row + notes entry. Initial-status
  backdoors are closed (`record_hypothesis` rejects gated initial statuses),
  with a shrink-only `_STATUS_DEBT` grandfather list mirroring the R-10
  pattern (sole member: `NR7_BULL_LOWLIQ_v1`, seeded FORWARD_TESTING by
  backfill under its 2026-07-12 pre-registration).
- **(b) Signed receipts (Phase H prerequisite):** the gatekeeper signs each
  decision (HMAC/Ed25519 over `decision_id · candidate_hash · config_hash ·
  dataset_fingerprint · final_state`) with a key **not held by researchers**;
  receipt-consuming gateways verify the signature. An executive override must
  then forge a signature, not edit a label.
- **(c) Honest ceiling (governance, not code):** anyone with merge rights over
  the CI allowlist can ultimately defeat any software gate. The enforceable
  promise is **dual control + attribution**: gate-runner identity ≠
  registry-flipper identity, and every transition lands in the append-only
  `audit_events` ledger. Software converts a silent override into a signed,
  logged, attributable act — that is the maximum honest claim.

---

## 4. Amended phase specs (deltas only — v2 §5 otherwise carries forward)

- **Phase C (amended):** gate criteria gain family scoping by
  `(dataset epoch, feature_space_hash)` and effective-N discounting (§3.1);
  family definition recorded in every evidence bundle; loosening = major
  config version + documented amendment, never retroactive. Status:
  implemented; completion pends the live end-to-end corpus run.
- **Forward-test rule (amended to v2 of the rule):** pooled bar unchanged;
  adds per-regime floors, regime-scoped promotion, runtime regime fencing
  (§3.2). Active NR7 test grandfathered under rule v1.
- **Phase E (amended):** granularity law (§3.3a); batch-transaction rule
  (§3.3b); receipt-bound status transitions as Task 11 (§3.4a).
- **Phase F (amended prerequisites):** C, D, E **and R-5 physical DB split**;
  sweep persistence must follow the granularity law and batch rule; the
  in-memory staging buffer for exploratory sweeps is a Phase F deliverable.
- **Phase H (amended prerequisites):** C, D, E (R-10 ✅ closed) **and signed
  receipts** (§3.4b).

---

## 5. Architecture invariants (v2 table + two additions)

Invariants 1–10 carry forward from v2 §9 with these status updates:
#10 forward-test evidence — **ENFORCED** (R-10 closed; NR7_BULL debt fenced,
deadline 2027-01-08). #8 rejected-hypothesis preservation — lands with Phase E
completion (in flight).

| # | New invariant | Status |
|---|---|---|
| 11 | **No capital-facing status transition without a verifiable evidence receipt.** Promotion-track labels (FORWARD_TESTING, VALIDATED) and registry states (SHADOW, APPROVED) bind to gate/forward receipts; advisory checks may warn, but the transition gateway must structurally reject. | MANDATED (Task 11 + R-10 ✅; signed receipts pending, Phase H) |
| 12 | **Multiplicity families are scoped by data epoch and feature space — never decayed by wall-clock time.** Historical trials are never forgotten; they are *scoped*. Any change that lowers a statistical hurdle is a documented, versioned, non-retroactive amendment. | MANDATED (Phase C config amendment, §3.1) |

---

## 6. Open items (v2 §11 updated)

| Item | Condition | Gates | v2 status | v3 status |
|---|---|---|---|---|
| R-6 residual | Exact DSR from real scan distribution | C | designed into C | ✅ **CLOSED** (Phase C impl 2026-07-12) |
| R-10 | Evidence-gated registry lifecycle in loader | Inv. #10, H | KEEP OPEN | ✅ **CLOSED** (2026-07-12; debt deadline 2027-01-08) |
| R-5 | Physical research/production DB split | Inv. #1 | KEEP OPEN | **ELEVATED — hard prerequisite of Phase F** (§3.3c) |
| R-7 | Parallel walk-forward wiring (2.03×) | C scan cost, F volume | KEEP OPEN | KEEP OPEN |
| **V3-1** | Family scoping + effective-N in gate_config (versioned, non-retroactive) | C | — | OPEN (design in §3.1) |
| **V3-2** | Forward-test rule v2: per-regime floors + scoped promotion + runtime regime fence | Phase 5 boundary, D | — | OPEN (design in §3.2; NR7 grandfathered) |
| **V3-3** | Granularity law + batch writes; staging buffer in F | E, F | — | PARTIALLY OPEN (law stated; buffer is an F deliverable) |
| **V3-4** | Receipt-bound `set_status` (Task 11); signed receipts | E, H | — | OPEN (Task 11 specced in the Phase E plan) |

---

## 7. Verdict framing carried into v3

The adversarial review's summary — "biased toward safety at the expense of
velocity and chronological reality" — is accepted **half-way**. The two
chronological assumptions (raw-N multiplicity pooling, calendar-window OOS)
were genuine architectural debt and are resolved above. The velocity critique
was a plumbing problem (SQLite contention + record granularity), not an
architectural one, and is resolved without weakening a single gate. The safety
bias on capital-facing paths is **deliberate and retained**.

---

## 8. Ratification record (owner)

Ratified by the owner on **2026-07-14**. Each decision below is now part of the
frozen baseline; further change requires a dated §13-style amendment.

- [x] **§3.1 family-scoping + effective-N** ratified, including **invariant #12**
  (multiplicity families scoped by data epoch + feature space, never wall-clock
  decayed).
- [x] **Forward-test rule v2 defaults ratified as drafted:** `N_r ≥ 8` and
  `expectancy_r ≥ +0.25%/trade` per validated regime cell (§3.2b). These are the
  frozen values; no strategy has yet run through rule v2, so a change before
  first use is a normal amendment, not a mid-test rule change.
- [x] **NR7 grandfather clause confirmed** (§3.2e): the live NR7 forward test
  completes under rule v1; rule-v2 regime *scoping* applies only at promotion.
- [x] **R-5 elevation confirmed** (§3.3c): the physical research/production DB
  split is a hard, blocking prerequisite of Phase F.
- [x] **Phase E plan Task 11** (receipt-bound `set_status`) approved and
  **implemented** (commit `fffa6f7`, 2026-07-14).
- [x] **Baseline promoted:** this file is FROZEN v3 and is now the canonical
  `docs/RESEARCH_MASTER_PLAN.md`; v2 retired to
  `docs/archive/RESEARCH_MASTER_PLAN_v2.md`.

**Change control (inherited from v2 §13):** this frozen baseline changes only by
an explicit, dated amendment to this file. The roadmap is not redesigned; no
phase is added or removed. The append-only evidence spine is never altered.

*End of Research Master Plan v3 — ARCHITECTURE BASELINE — FROZEN 2026-07-14.*
