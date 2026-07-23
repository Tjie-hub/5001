# EXEC-001 — Production Engine v2 Implementation Execution Protocol

**Status:** ACTIVE — engineering operating manual
**Date:** 2026-07-23
**Authority chain (descending, each subordinate to the one above):**
1. `Audit/PRODUCTION_ENGINE_AUDIT_2026-07-22.md` — evidence (FROZEN)
2. `docs/ADR-001-v2-Frozen-Baseline.md` — architecture (FROZEN; Freeze Matrix §14 authoritative)
3. `docs/PLAN-001-Implementation-Master-Plan.md` — program (FROZEN structure; §16 ADR-candidate register and task decomposition are its designated living sections)
4. **This document** — execution protocol (living; amended by dated changelog entries at the bottom, never silently)

A conflict between documents is resolved upward: EXEC yields to PLAN yields to ADR yields to evidence. This document governs *how* work is done; it may never change *what* is built or *in what order*.

**Operator model:** single-operator platform. PLAN-001 §11's role lanes are binding here: **Eng** (builds), **Arch** (guards frozen surfaces, dispositions classifications and ADR-candidates), **QA** (verifies evidence, owns gates), **Ops** (runs the system). Same human; a sign-off is valid only if written explicitly as the signing role, and §4 (Review Process) defines how role separation is simulated honestly.

**No code in this document.**

---

## 1. Engineering Rules (mandatory)

Numbered for citation in reviews (“violates ER-4”). Each rule names its enforcement mechanism — a rule without enforcement is a wish.

| # | Rule | Enforcement |
|---|---|---|
| ER-1 | **One workstream in flight per phase lane.** At most one active workstream on the critical path at a time; parallel work only from PLAN-001 §4's explicit parallelizable list. | Dashboard (§14) shows WIP; >1 critical-path WS in `active` = protocol violation |
| ER-2 | **No implementation outside PLAN-001.** Every unit of work is a PLAN task (`Pp.Ee.Ss.Tt`) or a task added through Change Control (§7). Untasked work is reverted, not adopted retroactively. | Commit trailer check (ER-3); reviewer checklist §5.4 |
| ER-3 | **Every commit traces to a task.** Commit message carries `Task: Pp.Ee.Ss.Tt` and the task's trace tag `[§n / AP-n / INV-xx / finding]`. One task may span commits; one commit never spans tasks. | Pre-merge gate script G-EVID (§6); rejected at review otherwise |
| ER-4 | **No architecture change without a superseding ADR.** Anything touching an ADR §14 FROZEN surface stops; file `ADR-CAND-nnn` in PLAN-001 §16. There is no “amendment” shortcut — ADR governance permits only a superseding ADR that names ADR-001 v2 and states what breaks. | Arch-lane review item §5.2; quality gate QG-6 |
| ER-5 | **No parameter change without a ParameterSet version.** Tunable values change only via `create_parameter_set_version` (operator command, §8.8 ADR); never by editing config/constants. During a shadow window, tolerance/threshold changes void the window (PLAN-001 condition 4). | Grep for new literals in review §5.1; manifest stamps expose drift |
| ER-6 | **No schema change without migration documentation.** Every DDL change is an entry in the single schema module's ordered migration list plus a line in `docs/ops/MIGRATIONS.md` (`{id, tables, reason, task, reversible?}`). Hand-run DDL is an incident. | Quality gate QG-4; fresh-DB bootstrap test must stay green |
| ER-7 | **Settled-history mutation only via the Correction Protocol** (§7.4 ADR). Direct UPDATE/DELETE on corpus history, artifacts, targets, events, or decision records is a defect of audit class, regardless of intent. | Code review §5.1; append-only tests; INV-A1/T2 checkers |
| ER-8 | **Wrap, don't rewrite, validated logic.** Legacy strategy checkers, exit kernel, edge scoring move as libraries (P8 preservation). A rewrite where a wrap suffices is scope creep (PLAN-001 R-04/R-09). | Golden parity tests mandatory before the wrap merges |
| ER-9 | **Evidence before completion.** A task without its §3 evidence bundle is `in-progress`, whatever the code state. | QA-lane sign-off; gate script G-EVID |
| ER-10 | **Deferred ADRs are out of scope.** Building toward ADR-003..008 beyond their named seams is reverted (PLAN-001 §4). | Trace-tag validity check — no PLAN task exists for them |
| ER-11 | **Frozen sequencing is not reorderable for convenience.** Specifically: Correction Protocol → C-1 ruling → adapter constants; ADR-002 inside Phase 1. | Phase-gate checklists §6; PLAN-001 conditions 1–2 |
| ER-12 | **Thinness check on every merge.** New dependency, daemon, framework, or plugin point beyond the three registration points (scouts/evaluators/policies) requires Arch-lane justification in the PR description or is rejected. | Review checklist §5.2 [AP-12, AN-9] |

---

## 2. Branch Strategy

**Model: trunk-based with short-lived task branches.** Rationale: single operator, additive phases, resume-oriented rollback — long-lived branches would decouple the shadow comparisons from what's actually merged.

- **`main`** — always releasable; always green on the pre-merge gate suite (§6). The production scheduler runs only tagged releases (below), never raw `main`.
- **Task branches** — `p<phase>/<epic>-<story>-<task>-<slug>`, e.g. `p1/e2-s2-t1-c1-ruling`. One task per branch; branch life measured in days, not weeks. Delete after merge.
- **No phase branches, no develop branch.** Phases are marked by tags, not branches — phases are additive by design (ADR §13), so trunk carries them safely.

**Merge policy:**
- Merge to `main` only via the full pre-merge checklist (§13 of PLAN-001) + gate script pass (§6 here). Squash-merge preferred (one task = one revertible commit on `main`); merge commit allowed when the task's internal history is itself evidence (e.g., a Correction executed in steps).
- No self-merge inside the same working session as the last commit — see cold review, §4.
- `main` red = merge freeze for everything except the fix for what made it red.

**Review policy:** every merge passes the §4 process — no exceptions for “trivial” changes (the audit's H-8 was a trivial change).

**Rollback policy (code-level):**
- Task-level: `git revert` of the squash commit — always possible because one task = one commit on `main`.
- Release-level: redeploy the previous tag; schema migration list is append-only and forward-compatible by construction (ER-6), so a code rollback never requires a schema rollback.
- Data-level: **never git** — data corrections happen only via the Correction & Supersession Protocol (ER-7).
- Phase-level: PLAN-001 frozen levers — Phases 1–3 additive-disable; Phase 4 rehearsed flip-back with legacy unwired in-tree one release.

**Release tagging:**
- `v2.<phase>.<n>` for deployable increments (e.g., `v2.1.3` = third release during Phase 1).
- Annotated milestone tags at each gate: `gate/phase-0` … `gate/phase-3`, `cutover`, `stabilization-complete`. The tag annotation names the sign-off document (§6).
- The tag deployed to production is recorded as `code_version` in every RunManifest (ADR §6.4) — the audit trail from a decision back to a commit is: DecisionRecord → manifest → tag → commit.

---

## 3. Implementation Workflow & Evidence Requirements

### 3.1 Task lifecycle (mandatory sequence)

```
Task (from PLAN-001, with trace tag)
  ↓ 1. PREP      — read the traced ADR section + audit finding; write the task card (§8: intent, evidence list, rollback lever)
  ↓ 2. IMPLEMENT — on the task branch; commits trail Task: + trace tag (ER-3)
  ↓ 3. SELF-REVIEW — same session: diff read top-to-bottom against checklist §5.1; fix before proceeding
  ↓ 4. TEST      — the task's NAMED tests (PLAN-001 §7 matrix) written/updated and green locally
  ↓ 5. REGRESSION — full suite + audit-finding regression class green; gate script §6 run locally
  ↓ 6. DOCUMENT  — migration entry (if schema), ops checklist delta (if operator-facing), decision entries (§8)
  ↓ 7. APPROVAL  — cold review (§4) as reviewer role; QA-lane evidence check (§3.2)
  ↓ 8. MERGE     — squash to main; branch deleted
  ↓ 9. GATE UPDATE — dashboard (§14) task→done with evidence link; phase-gate checklist item ticked if applicable
```

Steps may not be reordered; step 7 may not occur in the same working session as step 2's last commit (cold-review rule, §4).

### 3.2 Evidence bundle (per task — QA-lane checks this, not the code)

Stored under `docs/evidence/P<phase>/<task-id>/` (small text artifacts; large outputs referenced by path + hash). **A task is complete only when its bundle exists** (ER-9).

| Evidence | Required when | Form |
|---|---|---|
| Test output | always | named-test run log: suite name, pass count, duration |
| Regression run | always | full-suite output; the task's audit-finding regression tests called out |
| Gate-script output | always | G-* results (§6) |
| Logs | task touches a run/stage | relevant run-report or manifest excerpt showing the behavior |
| Replay output | WS-C/E/G/K tasks (PLAN-001 §7) | re-derivation/replay result incl. hash match statement |
| Migration output | any schema change | migration id, before/after schema diff, fresh-DB bootstrap test result |
| Correction record | any settled-history change | the Correction row(s): scope, reason, before-summary, corpus_version bump |
| Shadow comparison | Phase 2–3 tasks touching compared surfaces | divergence-ledger delta: rows added/closed by this task |
| Benchmark | task on a hot path (publication stage, EOD pass) | before/after duration for the affected stage |
| Screenshot | operator-facing output changed (Telegram/report rendering) | rendered output capture |
| Documentation delta | operator-facing or contract-changing | link to the docs/ops file section changed |
| Decision entries | any §8-classifiable event occurred | IDs of entries filed |

---

## 4. Review Process (single-operator honest review)

Review independence cannot be bought with headcount here; it is simulated with **time, role, and tooling separation**:

1. **Cold review rule:** approval (step 7) happens no sooner than the next working session after the last implementation commit — minimum one sleep or one full run-cycle (an EOD/NIGHTLY boundary) between writing and approving. The reviewer reads the diff *from the checklist, not from memory of writing it*.
2. **Role declaration:** the review is written as the reviewer role (“As Arch-lane, checked items §5.2: …”). A review that reads like the author defending the code is void — rewrite it as findings.
3. **Tool-assisted second reader:** run an automated code review (e.g., `/code-review` on the branch) before cold review; its findings are dispositioned line-by-line in the PR description (fixed / rejected-with-reason). Rejected findings without reasons void the review.
4. **High-risk surfaces get a third pass:** anything touching Authority order-of-authority, INV enforcement, Correction execution, state-machine guards, or the cutover flip gets an additional review pass **against the ADR text itself** (read §9/§10/§7.4 side-by-side with the diff), not just the checklist.
5. **Gate sign-offs** (§6) are stronger: written as the role, dated, in the gate document, citing the evidence bundles by path — a gate sign-off that cites no evidence is invalid.

---

## 5. Review Checklists

### 5.1 Code review (Eng-lane, every merge)
- [ ] Diff does only what the task card says; no drive-by changes (split them into tasks)
- [ ] Commit trailer: `Task:` + trace tag present and valid (ER-3)
- [ ] No new literals for tunables — values come from ParameterSet (ER-5)
- [ ] No direct SQL against decision-plane objects; registry/authority APIs only [AP-11]
- [ ] No UPDATE/DELETE paths on append-only objects (ER-7)
- [ ] Error paths: entry-side fail-closed, exit-side fail-open [AP-3, AN-5]
- [ ] Every consumer output carries provenance (as-of date, verdict) [AN-10]
- [ ] Matches surrounding code idiom; dead code deleted, not commented out

### 5.2 Architecture compliance (Arch-lane)
- [ ] No FROZEN surface (ADR §14) altered or worked around (ER-4)
- [ ] Single-writer preserved for every touched table/object [AP-1, INV-G3]
- [ ] No logic in scheduler or renderers [AN-4, §12]
- [ ] No new plugin point, framework, daemon, or dependency without justification (ER-12) [AP-12, AN-9]
- [ ] No second path toward position creation [AN-1, AN-2]
- [ ] Invariant checks live only in their owning module [AN-7]
- [ ] If a conflict surfaced: ADR-CAND filed, work stopped on the conflicting part only

### 5.3 ADR compliance (Arch-lane, high-risk surfaces — §4 rule 4)
- [ ] Diff read side-by-side with the traced ADR section; semantics match the frozen text, not a paraphrase
- [ ] Frozen enums/orders verbatim (state names, archive reasons, verdict table, order of authority §9.2, command verbs §8.8)
- [ ] OPEN-latitude choices recorded as IMPL-DEC entries (§8), not silently embedded

### 5.4 PLAN compliance (QA-lane)
- [ ] Task exists in PLAN-001 (or was added via §7 change control with changelog entry)
- [ ] Task's phase is the current phase; no forward-phase work smuggled in (ER-2)
- [ ] Sequencing constraints honored (ER-11)
- [ ] Deferred-ADR scope untouched (ER-10)

### 5.5 Testing (QA-lane)
- [ ] Named tests from PLAN-001 §7 matrix exist for this task and are green
- [ ] Audit-finding regression tests unaffected or extended, never weakened/deleted (pre-Phase-4)
- [ ] New failure mode introduced by this code has a failing-fixture test
- [ ] Determinism suite green if WS-D/E/F touched; replay suite green if WS-C/E/G/K touched

### 5.6 Documentation (QA-lane)
- [ ] Migration entry if schema touched (ER-6)
- [ ] Ops checklist delta if operator-facing behavior changed
- [ ] Module contract note updated if a cross-module interface changed
- [ ] Decision entries filed for anything §8-classifiable

### 5.7 Migration/Correction (Arch + QA lanes, any settled-history or schema task)
- [ ] Executed via Correction Protocol with complete record (ER-7)
- [ ] corpus_version bumped; affected dates marked for republication
- [ ] Before-summary captured; research notified via digest line
- [ ] Reversal path stated (superseding Correction), not assumed

### 5.8 Rollback readiness (QA-lane, every merge)
- [ ] Task revertible as one commit (squash) with no orphaned schema/data
- [ ] If a flag/stage was enabled: the disable lever named in the task card and tested once
- [ ] For Phase-3+ tasks: flip-back procedure unaffected, or its doc updated

---

## 6. Quality Gates (automatic stop conditions)

Implemented as a **pre-merge gate script** (local; also run by CI if/when configured — see Final Answer condition 2). Any failure = merge blocked; on `main`, any failure = merge freeze (ER-2 branch policy).

| ID | Stop condition | Scope |
|---|---|---|
| QG-1 | Any failed test in the full suite (legacy 1,193 + v2) | every merge |
| QG-2 | Replay failure: artifact re-derivation hash mismatch, Authority replay verdict mismatch, renderer re-run diff | merges touching WS-C/E/G/K; nightly in Phases 1+ |
| QG-3 | Determinism mismatch: same artifact + version vector → differing nominations/evaluations/verdicts | merges touching WS-D/E/F; nightly in Phases 2+ |
| QG-4 | Schema drift: DB schema ≠ schema-module output, or DDL change without migration entry (ER-6) | every merge |
| QG-5 | Missing evidence bundle for a task marked done (ER-9) | gate update step |
| QG-6 | Frozen-surface diff: change under a FROZEN §14 area without a superseding ADR reference | every merge (Arch-lane + grep heuristics) |
| QG-7 | Shadow divergence beyond tolerance, or any ledger row in `unexplained` older than 2 sessions | Phases 2–3, nightly |
| QG-8 | Invariant checker failure (INV-G1/G2/T2/D1/R1/P1/A1) in NIGHTLY | Phases 1+ — halts phase progress until dispositioned |
| QG-9 | Grep-audit failure: position creation outside Authority (AN-2), unwired capability (AN-8), raw-table read in decision plane post-P3 (AP-2), new plugin point (AN-9) | every merge from the phase each audit arms |
| QG-10 | Parameter literal introduced outside ParameterSet (ER-5) | every merge |
| QG-11 | Regression-test deletion/weakening for a live audit finding | every merge pre-Phase-4 |
| QG-12 | Session-window contamination: tolerance/threshold ParameterSet change mid-shadow-window | Phases 2–3 — voids the window counter (PLAN-001 §9.2) |

Stop-condition handling: fix forward on a branch; `main` stays frozen; the event gets a DEF entry (§8); if the stop reveals a design conflict → ADR-CAND, not a workaround (ER-4).

---

## 7. Change Control

Decision criteria — walk this ladder top-down; first match wins:

| Situation | Route | Record |
|---|---|---|
| Choice within OPEN latitude (ADR §14: DDL form, serialization, formats, stage micro-order, retry counts, file paths, param *values*) | **Normal implementation** | IMPL-DEC entry (§8); no doc change |
| Tunable value change | **ParameterSet version** via operator command — never a code/doc change | version stamped in manifests; digest line |
| Task decomposition refinement, task addition/split within a phase's frozen scope, checklist/evidence adjustments | **PLAN-001 update** — allowed only in its living sections (task decomposition, §16 register); dated changelog entry in PLAN-001 | PLAN changelog + dashboard |
| Phase scope/sequence, gate criteria weakening, workstream purpose change | **Not permitted by PLAN update.** Requires Arch-lane escalation → treated as ADR-candidate if it implies a frozen-surface conflict, else rejected | ADR-CAND or rejection note |
| Implementation impossible/contradictory under a FROZEN ADR surface | **ADR-candidate** (PLAN-001 §16): work stops on the conflicting tasks only; candidate carries conflict, section, evidence, proposed disposition | ADR-CAND entry |
| Candidate accepted as a real architecture change | **New superseding ADR** (ADR-00x) that names ADR-001 v2 and states what breaks — there is no in-place amendment path (ADR governance) | new ADR document; PLAN impact assessed as a PLAN changelog entry |
| Anything marked “Due/Trigger” in ADR §15 (Deferred ADRs) whose trigger fires | **New ADR on its own number** (ADR-002..008) — scheduled, not a conflict | the deferred ADR document |

**Never routes:** editing ADR-001 v2 text; editing the Audit; retro-editing PLAN-001 frozen structure; “temporary” frozen-surface bypasses (AN-2 explicitly forbids even temporary ones).

---

## 8. Decision Log (implementation decisions & issues)

One append-only file `docs/EXEC-DECISIONS.md` (chronological, one entry per event) — distinct from the *trading* Decision Log (ADR §9.4), which is a runtime object. Entry types:

| Type | Prefix | When | Required fields | Disposition path |
|---|---|---|---|---|
| Implementation decision | `IMPL-DEC-nnn` | an OPEN-latitude choice with consequences (serialization format, index design, stage split) | context, options considered, choice, reversibility | closed at write; revisit only via new entry |
| Architectural issue | `ARCH-ISS-nnn` | friction with the ADR that is *not yet* a conflict (ambiguity, underspecification within OPEN margins) | section, ambiguity, interim reading | resolved as IMPL-DEC, or escalates to ADR-CAND |
| Defect | `DEF-nnn` | any QG stop, invariant failure, shadow `v2-defect`, or escaped bug | detection, root cause, fix task id, regression test name | closed when regression test green on main |
| Technical debt | `DEBT-nnn` | knowingly-deferred quality issue (allowed only with a scheduled payoff task) | what, why deferred, payoff task, deadline phase | closed by payoff task; debt with no payoff task is rejected at review |
| ADR candidate | `ADR-CAND-nnn` | frozen-surface conflict (ER-4) | lives in **PLAN-001 §16** (not here); EXEC-DECISIONS carries a pointer entry | superseding ADR or closure with reasons |

Rules: entries are never edited (append a correcting entry); every DEF from a QG stop is mandatory, not optional; the dashboard (§14) counts open entries by type; a phase gate cannot close with open DEFs against that phase (§6 checklists).

---

## 9. Daily Engineering Cycle

Anchored to the run schedule (WIB) because the system's own runs generate the day's evidence:

| Slot | Activity | Lane |
|---|---|---|
| Morning (pre/at PREMARKET 08:15) | **Ops check** (daily checklist, PLAN-001 §10): last NIGHTLY report, watchdog, invariant line. Phases 2–3: skim overnight harness output | Ops |
| Mid-morning | **Planning (15 min):** pick/confirm today's single task (ER-1); write/refresh the task card; check dashboard | QA |
| Core block | **Implementation** on the task branch; tests written with the code, not after | Eng |
| Post-EOD (after 16:05 run) | **Shadow review (Phases 2–3, mandatory ritual):** disposition today's divergence-ledger rows same-day — PLAN-001 R-10 mitigation; aging `unexplained` rows trip QG-7 | Arch |
| Late | **Documentation + evidence:** bundle assembly for anything finished; decision entries; status update to dashboard | QA |
| Next session | **Cold review + merge** of yesterday's completed task (§4) | reviewer role |

Weekly: ledger-aging review, open-DEF/DEBT review, dashboard snapshot into the phase gate file. The cycle produces at most ~1 merged task/day by construction — that is intended; PLAN-001's calendar floor is session-gated, not typing-gated.

---

## 10. Completion Criteria (objective)

- **Task:** evidence bundle exists (§3.2) + merged on `main` + gate script green + dashboard updated. Nothing else counts — “works on my branch” is `in-progress`.
- **Workstream:** PLAN-001 §6 acceptance criteria all demonstrably met (each criterion mapped to an evidence bundle or CI check); its §7 test matrix fully green in the gate suite; its §8 migration-map rows at target state; zero open DEFs attributed to it.
- **Phase:** PLAN-001 §15 frozen gate + engineering criteria met; §6 checklist here fully ticked; three-lane sign-off written in `docs/evidence/P<n>/GATE.md` citing bundles; milestone tag pushed; next phase decomposed.
- **Program:** PLAN-001 Phase-4 exit (deletion inventory executed post-grace, 30-day stabilization clean, quarterly replay passed once, retrospective + all ADR-CANDs dispositioned).
- **Production readiness (= go-live eligibility):** Phase-3 gate closed + PLAN-001 §14 Go-Live Checklist items 1–4 pre-satisfied + rehearsal report on file + rollback triggers posted. Readiness is a state certified by the QA lane in writing, not a feeling.

---

## 11. Escalation Process

Single operator ⇒ escalation is **between role lanes and time horizons**, with forced stop-and-write:

1. **Eng blocked <2h** (tooling, test flake): fix inline; note in task card.
2. **Eng blocked >2h or 2 failed approaches:** stop; write an ARCH-ISS or DEF entry *before* trying a third approach — the write-up usually resolves it or reveals it's a conflict.
3. **Suspected frozen-surface conflict:** immediate stop on that task; ADR-CAND filed; switch to a parallelizable task (PLAN-001 §4 list). Never “prototype through” a frozen surface to see.
4. **Gate cannot be met** (criterion unreachable, window keeps resetting): QA-lane writes a gate-blocker memo in the gate file: criterion, evidence of attempts, options (extend window / fix class of defects / ADR-CAND). Durations are OPEN — extending time is always preferred over thinning a gate.
5. **Live incident (Phases 3–4):** Ops checklist (PLAN-001 §10 incident response) governs; engineering work freezes until the incident has a DEF entry; if within Phase-4 stabilization, check §9.6 rollback triggers first.
6. **External escalation:** none exists — which is why rules 2–4 force writing: the written record is the substitute for a colleague.

---

## 12. Rollback Rules (consolidated)

| Layer | Mechanism | Constraint |
|---|---|---|
| Commit/task | `git revert` of squash commit | always available (branch policy §2) |
| Release | redeploy previous `v2.x.y` tag | schema migrations are forward-compatible append-only; never roll schema back |
| Parameter | new ParameterSet version restoring prior values | never edit; the bad version stays in history, referenced by the manifests that used it |
| Data/corpus | superseding Correction (§7.4 ADR) | never git, never UPDATE; lineage mandatory |
| Artifacts | supersession with lineage | INV-A1: no deletion of decision-referenced artifacts |
| Registry/decisions | none — append-only by design | wrong verdicts are superseded-by-reference (`override_veto`); state errors surface via INV-T2 and are fixed by *commands*, not surgery [AP-11] |
| Stage/feature | disable lever named in the task card (§5.8) | Phases 1–3 are additive by frozen design |
| Cutover | rehearsed flip-back; legacy unwired in-tree one release | triggers in PLAN-001 §9.6; flip-back is an incident, gets a DEF entry |

---

## 13. Documentation Requirements

Living set (all under `docs/` unless noted); each has one owner-lane and an update trigger:

| Document | Owner | Updated when |
|---|---|---|
| `EXEC-DECISIONS.md` | QA | any §8 event |
| `PLAN-001` §16 + changelog | Arch | ADR-CANDs; task decomposition changes |
| `ops/MIGRATIONS.md` | Eng | any schema change (ER-6) |
| `ops/` checklists (daily/deploy/rollback/incident/recovery/monitoring/audit) | Ops | any operator-facing behavior change; exercised-date recorded each use |
| `evidence/P<n>/<task>/` bundles + `GATE.md` | QA | task completion; phase gates |
| Module contract notes (per module header or `docs/contracts/`) | Eng | cross-module interface changes |
| ADR-002 (Phase 1) and any superseding ADRs | Arch | per Change Control §7 |
| Divergence ledger | Arch | every shadow session (system-written; classifications human-written) |
| Dashboard `EXEC-STATUS.md` | QA | daily status slot (§9) |

Rule: documentation lag is debt — a DEBT entry with a payoff task, or the task isn't done (ER-9 includes the doc delta).

---

## 14. Engineering Dashboard

One flat file, `docs/EXEC-STATUS.md`, regenerated/updated daily (QA lane). No tooling beyond text until it hurts (AP-12 discipline applies to process too). Sections:

1. **Program position:** current phase; days into it; session counters (X/10 or X/≥20) with the date the counter last reset and why.
2. **WIP:** the active task (singular, ER-1) + any parallel-list tasks in flight; each with branch name and state (impl / cold-review-pending / evidence-pending).
3. **Gate progress:** current phase's §6 checklist with ticked/unticked counts and the blocking items named.
4. **Quality state:** last gate-script run result; QG stops this week; open DEF/DEBT/ARCH-ISS/ADR-CAND counts (with IDs).
5. **Shadow state (Phases 2–3):** ledger rows by classification; `unexplained` age max; today's dispositioned count.
6. **Ops state:** last run statuses per run type; invariant checker line; watchdog age.
7. **Next up:** the next 3 tasks in critical-path order.

The dashboard is derivative — it cites manifests, ledger, and evidence paths; it is never the primary record of anything.

---

## 15. Final Execution Checklist (protocol bring-up, before Phase 0 work starts)

- [ ] This document, PLAN-001, ADR-001 v2, and the Audit committed together; authority chain header verified
- [ ] Git hygiene: `main` protected by convention (no direct commits — task branches only); commit-trailer format agreed (ER-3)
- [ ] Pre-merge gate script created (runs: full test suite, schema-drift check, grep-audits appropriate to phase, evidence-presence check) — **this is the one tooling deliverable this protocol adds**, and it is a Phase-0 task added to PLAN-001 via change control (PLAN changelog entry)
- [ ] `docs/EXEC-DECISIONS.md`, `docs/ops/MIGRATIONS.md`, `docs/EXEC-STATUS.md`, `docs/evidence/` skeletons created
- [ ] Ops checklists from PLAN-001 §10 stubbed as files (filled as phases deliver them)
- [ ] Cold-review rule understood and calendarized (merge slot ≠ build slot, §9)
- [ ] Phase-0 task cards written for P0.E1/P0.E2 with evidence lists
- [ ] Dashboard initialized with Phase 0 gate checklist
- [ ] Legacy test suite (1,193) runs green locally — the baseline the gate script protects

---

## 16. Phase Gate Checklists (expanded from PLAN-001 §15)

Every item mandatory; a phase cannot close with any unticked item; sign-offs per §4 rule 5.

**Gate 0 (tag `gate/phase-0`):**
- [ ] Every P0 task merged with evidence bundle
- [ ] Zero imported-but-unregistered jobs (grep-audit output filed) [H-1/H-2/AN-8]
- [ ] VPIN block demonstrated (test evidence) [H-8]
- [ ] Absolute DB path + identity logging (startup log filed) [H-7]
- [ ] Date guards live (test evidence) [M-5, H-3-min]
- [ ] Legacy baseline declaration written and dated
- [ ] Pre-merge gate script operational (bring-up item, §15)
- [ ] Three-lane sign-off in `evidence/P0/GATE.md`

**Gate 1 (tag `gate/phase-1`):**
- [ ] 10-session artifact counter complete; per-session operator flag confirmations filed
- [ ] Unit invariants green over full history (run output filed) [C-1 regression]
- [ ] C-1 ruling doc committed; Correction #1 record cited; **order verified from Correction records** (protocol before ruling — ER-11)
- [ ] Correction #2 (CA basis) record cited; split-parity test green [C-2]
- [ ] ADR-002 committed and wired (finality tests green) — hard blocker
- [ ] Fresh-DB bootstrap evidence [H-6]; Clock lint clean; seed-inventory diff ∅ (PLAN condition 3 discharged)
- [ ] NIGHTLY on DAG; resume matrix evidence; sentinel-on-success verified [M-6]
- [ ] Certifier: failing-fixture evidence per check; verdict truth-table test green
- [ ] Harness self-test (seeded divergence detected) filed
- [ ] Zero open DEFs against Phase 1; ADR-CAND register reviewed
- [ ] Three-lane sign-off in `evidence/P1/GATE.md`

**Gate 2 (tag `gate/phase-2`):**
- [ ] Divergence ledger: zero `unexplained`, zero open `v2-defect`; every terminal row carries Arch-lane sign-off
- [ ] Difference-explanation report generated from ledger queries and filed (the FROZEN gate artifact)
- [ ] INV-G1 + INV-T2 nightly-green across the shadow window (checker outputs filed)
- [ ] §10 transition matrix + fold-property test evidence
- [ ] Evaluator golden-parity evidence per wrapped checker
- [ ] Every operator verb exercised once in test context (command + emitted OperatorEvent filed)
- [ ] Phase-2 tolerance ParameterSet version identified; no mid-window changes (QG-12 log clean)
- [ ] Zero open DEFs against Phase 2; three-lane sign-off in `evidence/P2/GATE.md`

**Gate 3 (tag `gate/phase-3`):**
- [ ] ≥20-session counter complete; counter-reset history explained in the gate file
- [ ] Ledger clean (as Gate 2) + **R2 sign-off explicitly written** (Arch lane) — the FROZEN requirement
- [ ] All PLAN-001 §9.5 promotion criteria itemized with evidence (invariants green all sessions; PASS/VETO completeness runs; ops checklists exercised incl. deliberate resume + every command verb)
- [ ] AP-2 grep-audit: zero raw-table reads in decision plane (output filed); AN-2 audit in gate script
- [ ] EOD/PREMARKET/INTRADAY manifests filed for a representative session; legacy cron chain shows superseded jobs unregistered
- [ ] Authority-refusal demonstrated (deliberate-rerun evidence)
- [ ] Cutover rehearsal report on file (incl. rollback executed)
- [ ] Zero open DEFs against Phase 3; three-lane sign-off in `evidence/P3/GATE.md`

**Gate 4 / program close (tags `cutover`, `stabilization-complete`):**
- [ ] Go-Live Checklist (PLAN-001 §14) executed line-by-line, initialed, filed
- [ ] 30-day stabilization log: zero rollback-trigger events, or each with a closed DEF
- [ ] Deletion inventory executed post-grace; AN-8 grep-audit output filed
- [ ] Quarterly replay audit passed once (evidence filed)
- [ ] Retrospective + all ADR-CAND dispositions filed
- [ ] Three-lane sign-off in `evidence/P4/GATE.md`

---

## 17. Final Answer

**Is the project now fully specified for implementation?**

## YES WITH CONDITIONS

The specification stack is complete and closed: evidence (Audit) → architecture (ADR-001 v2, frozen) → program (PLAN-001, traced task graph with gates) → execution (this protocol: rules, workflow, evidence, reviews, gates, change control, escalation, rollback). No execution question of the form “what do I do next, how do I prove it, and who says it's done” lacks an answer.

The remaining conditions — none of which is a specification gap in the documents themselves:

1. **Inherited empirical/operational conditions (PLAN-001 §17, unchanged):** C-1 ruling as Correction #1 in sequence; ADR-002 inside Phase 1; complete ParameterSet seed inventory; per-window tolerance freezes. All scheduled; Gate-1/Gate-2 checklists above discharge them mechanically.
2. **Gate-script bring-up (execution tooling):** the pre-merge gate script (§6, §15) is the single piece of automation this protocol depends on and does not yet exist. It is added to Phase 0 via change control. Until it runs, QG enforcement is manual-checklist only — acceptable for Phase 0's trivial tasks, not beyond. **Condition: gate script operational before Gate 0 closes.**
3. **Discipline conditions (irreducible for a single operator):** the cold-review rule (§4) and role-lane sign-off honesty are enforced by protocol, not mechanism — the same class of condition the ADR itself flagged for AP-12 thinness. The mitigations (time separation, tool-assisted second reader, evidence-citing sign-offs) are the strongest available without a second human; they cannot make the condition vanish.

**Remaining execution ambiguity: none identified beyond these.** Condition 2 resolves inside Phase 0; condition 1 resolves by end of Phase 1; condition 3 is permanent and managed, not resolvable. On Gate-1 closure, the program's answer stack becomes: architecture YES (ADR's own clause), plan YES (PLAN-001 clause), execution YES except the permanent, explicitly-managed single-operator discipline caveat.

---

*Changelog: 2026-07-23 — v1, initial protocol.*
