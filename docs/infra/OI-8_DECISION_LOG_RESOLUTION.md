# OI-8 Resolution — Does the Cross-Machine Research Architecture require a Decision Log entry?

**Document type:** Governance determination (point-in-time record)
**Authority:** Principal Enterprise Architect
**Subject:** Open Issue **OI-8** of `docs/infra/CROSS_MACHINE_RESEARCH_ARCHITECTURE_v0.2.md`
**Question:** Does the proposal require an entry in `docs/roadmap/DECISION_LOG.md` because it
advances repository invariant **R-5**?
**Branch:** ops/hardening-2026-07-10 (the only branch carrying the governance corpus)
**Date:** 2026-07-22
**Constraints honoured:** no architecture change, no proposal revision, no implementation, no code,
no scripts. `DECISION_LOG.md` is **not** edited by this document.

---

## 1. Determination (summary)

> **A new Decision Log entry is NOT required at this time. No existing entry should be updated.
> One lightweight cross-reference correction is required in a future v0.3 (deferred).**

The premise embedded in OI-8 — *"because it advances R-5"* — does **not hold on inspection**. The
proposal does not advance, modify, or reopen R-5. R-5 is already fully scoped, owner-decided, and
implementation-planned; the cross-machine proposal is **downstream of and dependent on R-5**, not an
advancement of it. With the triggering premise removed, and on two further independent grounds
(register scope; decision maturity), no Decision Log entry is warranted now.

---

## 2. What R-5 actually is (established from primary sources)

| Fact | Source |
|---|---|
| R-5 = "Physical research/production DB split," bound to **Invariant #1**, **ELEVATED to a hard prerequisite of Phase F**. | `docs/RESEARCH_MASTER_PLAN.md` §3.3c and §5 invariant table (line 278) |
| R-5 was **scoped to Tier-1 only** and **RESOLVED by owner decision on 2026-07-14**: physically split the 8 pure-discovery tables into `data/research.db` via a `connect_research()` seam that `ATTACH`es `walkforward.db` **read-only** as `prod`. | `docs/superpowers/specs/2026-07-14-r5-physical-db-split-scope.md` §6 |
| R-5 has a **complete 10-task TDD implementation plan** already written (seam → migration → rewire → physical fence → ops → cutover runbook). | `docs/superpowers/plans/2026-07-21-r5-tier1-physical-db-split.md` |
| R-5 is **NOT recorded in `DECISION_LOG.md`.** A full-text scan returns zero matches for `R-5`/`physical DB split` there. Its decision lives in the superpowers scoping note. | `docs/roadmap/DECISION_LOG.md` (grep, 2026-07-22) |

**Consequence of the last row:** the repository's *actual, observed practice* is that R-5 —
a Master-Plan invariant and Phase-F blocker — records its architecture decision in a
`docs/superpowers/` scoping note, **not** in the Research-OS Decision Log. The Decision Log's
register (D-001…D-028) is populated by Research-OS **governance, scientific, and OS-architecture**
decisions (taxonomy, program classification, custody model, multiplicity-family scoping), not by
data-plumbing/implementation-scoping decisions. This is the controlling precedent for OI-8.

---

## 3. Relationship between the proposal and R-5 (the core correction)

v0.2 §5.5 states it will *"advance R-5 (physical DB split)."* On inspection that is **imprecise**:

- **R-5's own mechanism already is the pattern the proposal calls its data architecture.** R-5's
  `connect_research()` design — `research.db` as the writable main schema, production `ATTACH`ed
  **read-only** — is exactly the "own writable research DB + read-only production input" the
  cross-machine proposal describes. The proposal does not invent this; it **inherits** it.
- **The proposal's only genuine addition is the machine boundary.** Where R-5 reads production as a
  local read-only `ATTACH`, the cross-machine proposal reads production as a **snapshot pulled to a
  second machine** (WAL-safe online-backup → rsync-over-SSH → read-only). That is an *operational
  elaboration of R-5's consumption path across hosts* — it changes **where** the read-only prod
  input physically sits, not **what** R-5 decides.
- **The proposal therefore depends on R-5, it does not advance it.** If anything, R-5 is *ahead* of
  the proposal (scoped + planned vs. frozen-for-review).

**Accurate statement (for the future v0.3):** *"This proposal is a cross-machine deployment context
that depends on and extends R-5's Tier-1 split; it does not modify R-5."* This is the one
documentation correction OI-8 surfaces. It is a **v0.3 edit and is deferred** per the standing "do
not create v0.3 yet / architecture frozen" instruction.

---

## 4. Three independent grounds that a new entry is not required

1. **The triggering premise fails.** The proposal does not advance R-5 (§3). The only stated reason
   for an entry is therefore absent.
2. **Wrong register / out of scope.** `DECISION_LOG.md` is the **L0 — Governance & Scope** register
   for Research-OS governance, scientific, and OS-architecture decisions (its own header + scope
   discipline §3). The cross-machine proposal is an **Infrastructure / development-topology**
   artifact: it makes no governance, scientific, or Research-OS-architecture decision; changes no
   invariant definition; touches no multiplicity family, hypothesis lifecycle, evidence model, or
   custody rule. It strengthens Invariants #1 and #6 *in spirit* but alters neither's definition or
   enforcement. R-5's own precedent (§2) confirms infra/implementation scoping is recorded in
   `docs/superpowers/`, not here.
3. **Decision maturity.** The document is explicitly **"REVIEW REQUIRED — DO NOT IMPLEMENT,"** a
   frozen-for-review draft. The Decision Log records **decisions that have been made, with their
   rationale** (ISO/IEC/IEEE 42010 §5.7); it is not a register of proposals under review. Filing an
   entry for an unaccepted draft would be premature and would misuse the register.

---

## 5. Should an existing entry be updated instead?

**No.**

- There is **no existing R-5 entry** in `DECISION_LOG.md` to update (§2).
- R-5's actual decision record (the 2026-07-14 owner decision in the scoping note) is **unchanged**
  by this proposal — the proposal consumes R-5 as-is.
- The Decision Log is **append-only in spirit**; a change is a new, dated, superseding entry, never
  a silent edit. Nothing here warrants even a superseding entry yet.

**Adjacent observation (not an OI-8 action, logged for the owner):** the Decision Log's own scope
discipline (§3) says that where a decision "already carries a full ADR in another canonical
document, this log records a **pointer**, not a copy." R-5 arguably qualifies for a one-line
*pointer* entry to its scoping note — but (a) whether a `docs/superpowers/` spec counts as a
"canonical document" in the corpus sense (Owner-headed) is unsettled, and (b) this concerns **R-5
itself**, not the cross-machine proposal. It is therefore **out of scope for OI-8** and is noted
only so it is not lost.

---

## 6. Additional governance artifacts that must reference the proposal

| Artifact | Action | When | In scope now? |
|---|---|---|---|
| v0.2 → v0.3 §5.5 | Correct wording: "depends on / extends R-5," not "advances R-5"; add explicit cross-reference to the R-5 scoping note + plan as a **hard dependency**. | v0.3 (deferred) | No — architecture frozen; v0.3 not authorised yet |
| `docs/superpowers/specs/2026-07-14-r5-physical-db-split-scope.md` | Optional back-reference noting a downstream cross-machine consumer exists. | Only **if/when** the proposal is accepted | No |
| Hypothesis / Failure / Edge registries | **None.** The proposal implicates no hypothesis, no falsification, and no strategy promotion. | — | — |
| `docs/roadmap/DECISION_LOG.md` | **None now.** See §7 for the deferred trigger. | On acceptance (see §7) | No |

---

## 7. Deferred trigger — when a Decision Log entry *would* become appropriate

A Decision Log entry (or, matching R-5's precedent, a `docs/superpowers/` scoping note) becomes
appropriate **only if both** conditions are met later:

1. The architecture is **accepted for implementation** (status leaves "DO NOT IMPLEMENT"); **and**
2. Implementation is found to **change how a Research-OS invariant is *enforced*** — specifically, if
   cross-machine operation makes the **physical** separation of research and production a stated
   enforcement mechanism of **Invariant #1** (today enforced by the CI import-boundary scan + the
   in-progress R-5 physical split). A change to *how an invariant is enforced* is a Research-OS
   architecture decision and belongs in the register as a **pointer** entry.

If neither the enforcement of an invariant nor a Research-OS governance/scientific rule changes,
the correct home remains a `docs/superpowers/` infrastructure spec, and the Decision Log stays
silent — consistent with R-5's own treatment.

---

## 8. Conditional draft entry — NOT TO BE FILED YET

Provided **only** so the record is ready if §7's trigger fires. **This is a draft; it must not be
added to `DECISION_LOG.md` while the architecture is frozen-for-review.** The next free ID after the
current maximum (**D-028**) is **D-029**.

> ### D-029 · Cross-machine Research node — physical separation as an Invariant #1 enforcement extension
> **Status:** DRAFT — NOT ACCEPTED (do not file until the architecture leaves "DO NOT IMPLEMENT"
> and is confirmed to change Invariant #1 *enforcement*) · **Date:** TBD (date of acceptance) ·
> **Type:** Architectural (Infrastructure) — *pointer entry, not a copy*
> **Context:** Production and Research contended for one host to the point of OOM. The
> Cross-Machine Ubuntu Research Architecture relocates Research to a WSL2 Ubuntu node and feeds it a
> WAL-safe, one-directional, read-only Production→Research snapshot over Git-over-SSH. It extends
> R-5's Tier-1 `connect_research()` (research.db writable + production read-only) across a machine
> boundary. Full rationale, alternatives, and trade-offs are held in the proposal, not copied here.
> **Decision:** Recognise the accepted cross-machine topology as an **operational extension of R-5**
> and, to the extent it makes physical host separation a stated enforcement of **Invariant #1**,
> record that enforcement change by pointer.
> **Rationale:** 42010 §5.7 — an architecture decision that changes how an invariant is enforced
> must carry recorded rationale; the register records the pointer, the proposal owns the detail.
> **Alternatives considered:** single-host continuation (rejected — contention/OOM); Windows-native
> Python (rejected — two runtimes); Syncthing-based sync (rejected in the proposal's own review —
> false provenance, secret/DB-corruption risk). *Full alternatives live in the proposal + its Opus
> review; not restated here.*
> **Consequences:** R-5 remains the load-bearing table split; this entry adds a physical-host
> dimension to Invariant #1's enforcement story. Reproducibility (Invariant #6) is strengthened via
> the proposal's "clean committed state" rule.
> **Related ADRs:** proposal ADR-001, ADR-004, ADR-005 · **Related Invariants:** #1, #6, R-5
> **Related Architecture Proposal:** `docs/infra/CROSS_MACHINE_RESEARCH_ARCHITECTURE_v0.x.md`
> **Cross References:** `docs/superpowers/specs/2026-07-14-r5-physical-db-split-scope.md` ·
> `docs/superpowers/plans/2026-07-21-r5-tier1-physical-db-split.md` · `docs/RESEARCH_MASTER_PLAN.md`
> §3.3c, §5

---

## 9. Effect on OI-8 and on the freeze question

- **OI-8 is RESOLVED:** no Decision Log entry required now; no existing entry to update; the only
  action is a deferred v0.3 wording correction (§3, §6) and a conditional, unfiled draft (§8).
- **Freeze recommendation:** the OI-8 resolution introduces **no architecture change** — it is
  purely a governance/traceability finding. It therefore **does not disturb the freeze.** See the
  chat-level recommendation accompanying this document.

---

*End of OI-8 resolution. Governance determination only. `DECISION_LOG.md` is deliberately left
unmodified.*
