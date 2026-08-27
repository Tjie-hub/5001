---
paths:
  - "docs/governance/**"
  - "docs/roadmap/**"
  - "docs/research_os/**"
  - "docs/research_programs/**"
  - "docs/RESEARCH_MASTER_PLAN.md"
  - "docs/Phase_A_Scientific_Foundation/**"
  - "research/**"
---

Migrated from `CLAUDE.md` (2026-08-27, /doctor lazy-loading migration) — content unchanged, only
relocated so it loads only when a task touches these paths. See `CLAUDE.md` "Before Starting Any
Task" for when to read this before starting research-governance work.

## Research Governance Corpus

`docs/research_os/`, `docs/governance/`, `docs/roadmap/`, and `docs/research_programs/` together
form the **Institutional Research OS** — an institution-level scientific charter and governance
layer for how trading-strategy research is done here, distinct from (and wrapping) the executed
pipeline in `research/` described in `CLAUDE.md`. **This entire corpus exists only on
`ops/hardening-2026-07-10`** — see `CLAUDE.md` "Before Starting Any Task".

### Layers, Programs, Stages, Gates

`docs/governance/TAXONOMY_AND_NAMING_STANDARD.md` fixes one controlled term per structural axis and
retires "Phase" for OS structure (it survives only inside the proper noun `RESEARCH_MASTER_PLAN.md`,
which predates the standard and is frozen):

| Axis | Term | Numbering | Meaning |
|---|---|---|---|
| Architecture strata of the OS | **Layer** | L0–L8 | What the system is made of |
| A research track | **Program** | P0, P1… | What is being researched |
| Steps in the research pipeline | **Stage** | S1–S10 | How one hypothesis moves literature → knowledge |
| Institutional approval checkpoints | **Gate** | G1–G4 | Who must approve to proceed |
| State of a research object | **Lifecycle State** | (named) | e.g. REGISTERED, VALIDATED |

Layers (`docs/roadmap/RESEARCH_OS_MASTER_ROADMAP.md` §2; names as ratified in
`docs/roadmap/GOVERNANCE_BASELINE_v1.md` §2, the 2026-07-17 baseline):

| Layer | Name | State at 2026-07-17 baseline |
|---|---|---|
| L0 | Governance & Scope | **Frozen** (Phase B Governance freeze) |
| L1 | Scientific Foundation | Certified-ready, **not frozen** — gated on G-8 (independent sign-off) |
| L2 | Research Architecture | Canonical, preserved |
| L3 | Data Ontology | Canonical (ratified), not frozen — RN-4 review pending |
| L4 | Runtime Architecture | Canonical (ratified), not frozen — RN-4 pending |
| L5 | Reference Architecture | Canonical (ratified), not frozen — RN-4 pending |
| L6 | Technology Profiles | Deliberately unauthored |

Programs (`RESEARCH_OS_MASTER_ROADMAP.md` §3): **P0 · v3 Edge Pipeline (NR7 family)** is delivered —
the reference implementation proving the framework produces validated knowledge. **P-M ·
Microstructure Flow** (merged P1+P2, declared family `{I5,I6,I7,I12}`) and **P-A · Auction
Dislocation** (P3, family `{I2,I3,I8}`) are the two active programs as of 2026-07-19
(`docs/research_programs/RESEARCH_PROGRAM.md`, `DECISION_LOG` D-028); each has exactly one
hypothesis registered so far. P4 is current-but-immature (blocked on data-history maturity); P5/P6
are documented Future/Out-of-scope — retained, not deleted.

### The two master roadmaps and how they relate

`docs/RESEARCH_MASTER_PLAN.md` (root-level, frozen v3) and `docs/roadmap/RESEARCH_OS_MASTER_ROADMAP.md`
(the Research OS) coexist by design — reconciled in `docs/governance/RESEARCH_OS_RECONCILIATION.md`:
**the Research OS is the institutional framework; v3 is Program P0, the first Research Program
executed inside it.** v3 is preserved as-is and treated as a reference implementation the OS is
validated against, not rebuilt. Precedence on conflict is in Decision-Making Hierarchy below.

### Canonical, generated, archived, and historical documents

The corpus is explicit about document status — these are different trust levels, not interchangeable:

- **Canonical** — the current, owned, amendable source of truth for its scope (e.g. the six L2 docs
  in `docs/research_os/`, `docs/governance/TAXONOMY_AND_NAMING_STANDARD.md`,
  `docs/roadmap/DECISION_LOG.md`). Carries an `**Owner:**` header field.
- **Frozen** — canonical *and* closed to further change except by a dated, explicit amendment
  (`docs/RESEARCH_MASTER_PLAN.md` v3; Phase B Governance as a whole). Canonical does not imply
  frozen: several L3–L5 docs are canonical but explicitly not frozen, pending independent review.
- **Generated / point-in-time records** — audits, reviews, certificates, decision entries; carry an
  `**Authority:**` header instead of `**Owner:**`, and are superseded rather than edited (e.g. most
  of `docs/roadmap/` besides the roadmap and decision log themselves: `PHASE_A_FREEZE_CERTIFICATE.md`,
  `RED_TEAM_REVIEW_2026-07-15.md`, `ARB_ADJUDICATION_2026-07-15.md`, `GOVERNANCE_AUDIT_REPORT.md`).
- **Archived / superseded / withdrawn** — retained for history, not current guidance:
  `docs/archive/RESEARCH_MASTER_PLAN_v2.md` (superseded by v3), `docs/archive/REFERENCE_ARCHITECTURE_DRAFT.md`
  (superseded), `docs/archive/EXECUTION_SEMANTICS.md` (withdrawn). Nothing is deleted on
  supersession (`docs/roadmap/GOVERNANCE_BASELINE_v1.md` §7).
- **Historical decisions** — `docs/roadmap/DECISION_LOG.md` is append-only in spirit: corrected only
  by a new, dated, superseding entry, never a silent edit; a decision whose justifying premise is
  later refuted becomes void, not grandfathered.

### Registries — four distinct, don't conflate them

| Registry | Location | Tracks | Write discipline |
|---|---|---|---|
| **Edge Registry** | `registry/edge_registry.yaml` + `registry/manifests/*.yaml` | Production-facing: which strategies are `APPROVED`/`SHADOW` and loadable by `engine/registry_loader.py` | Receipt-bound to gatekeeper evidence (R-10); code-level artifact, not a doc |
| **Hypothesis Registry** | `docs/research_programs/HYPOTHESIS_REGISTRY.md` | Every hypothesis across active programs, its family, status, frozen record | Append-only in spirit — status advances by a superseding record, never a silent edit |
| **Failure Registry** | `docs/research_programs/FAILURE_REGISTRY.md` | Falsified hypotheses / failed experiments, by F-mode (F1–F9) | Append-only and immutable (HL-1, R12) — never edited or deleted |
| **Experiment ledger** | `research_runs` table (`research/tracking.py`) + `docs/research_programs/P-*/experiments/<ID>/` | Every experiment run: run_id, dataset fingerprint, environment, results | Append-only DB row + a frozen per-experiment doc bundle (MANIFEST / EVIDENCE_PACKAGE / CLOSE_OUT_REPORT) |

Live state as of 2026-07-19/21: **HYP-PM-0001** (P-M) is **FAILED** (mode F2, prediction failure —
`docs/research_programs/P-M/experiments/EXP-PM-0001/`); it stays counted in the P-M family
permanently — a failure never reduces the family denominator. **HYP-PA-0001** (P-A) is
**REGISTERED**; its experiment has not yet executed.

### Research lifecycle

A hypothesis moves (`docs/research_os/HYPOTHESIS_LIFECYCLE.md` §3):
`DRAFT → REFINING → REGISTERED` (frozen, counted in its family) `→ IN_TESTING → VALIDATED | FAILED`,
with `WITHDRAWN` / `RETIRED` / `DECAYED` / `SUPERSEDED` / `VOID` as terminal states that are
explicitly **not failures** — conflating them with FAILED is documented as corrupting the
institution's own self-diagnostic (the distribution of F1–F9 failure modes across the Failure
Registry). Evidence is tiered on three independent axes (`docs/research_os/EVIDENCE_MODEL.md`):
**evidence class** K1–K7 (theoretical / literature / observational / experimental / replicative /
forward / adversarial — each with an absolute, non-aggregable ceiling on the tier it can ever
support), **evidence tier** E0–E7, **confidence** C0–C4, and **reproducibility** X0–X4.

### Evidence-first philosophy

Stated specifically enough in the corpus to be more than generic best practice:

- **Research produces knowledge; capital consumes it — never the reverse.** "The reverse dependency
  is prohibited" (`docs/Phase_A_Scientific_Foundation/01_SCIENTIFIC_FOUNDATION.md` §0.1). The Program's four binding
  tie-breakers, in order (`docs/research_programs/RESEARCH_PROGRAM.md` §1): **evidence over
  documentation, experiments over architecture, reproducibility over speed, statistical validity
  over backtest performance.**
- **Reproducibility is constitutive, not a nice-to-have** (ADR-L1-005) — conclusion-invariance,
  tracked mechanically via `research/tracking.py`'s order-independent dataset fingerprint and
  captured environment provenance.
- **Mechanism-first is a gate, not a preference** (ADR-L1-003) — a pattern without a proposed causal
  mechanism is evidence class K3 at best; "statistical significance without a mechanism" is
  explicitly inadmissible (`EVIDENCE_MODEL.md` rule U10, violates P2).
- **Underpowered corroboration is zero evidence, not weak evidence** — "corroboration from a test
  that could not have refuted the hypothesis carries zero evidential weight" (rule R2) — and
  **realized profit is not evidence at all** (rule U1: "both fortune and error produce returns").
- **Attack your own claims before the market does, and keep failures as carefully as successes**
  (rule R12) — the Failure Registry is append-only and immutable by the same discipline that
  protects the Hypothesis Registry; a refutation is treated as a first-class product, not a defect.
- **Research/production separation is an evidence-integrity mechanism, not only a code-quality one**
  — per invariants 1–5 in `CLAUDE.md`'s Repository Invariants, its purpose is to guarantee production
  never discovers, optimizes, or promotes strategies on its own, so every live strategy traces back
  to a human-gated, evidence-backed decision.
- **Production stability is prioritized over feature velocity**, by a consistent repo-wide pattern
  rather than one stated maxim: every new capability ships behind a `shadow`/`enforce` (or
  `off`/`shadow`/`enforce`) mode — `AUTH_MODE`, `EDGE_SCORE_MODE`, `SECTORS_APP_MODE` all follow it
  — so it can observe and log before it can ever block or change behavior; `gunicorn.conf.py`
  refuses a second worker rather than risk double-run scheduler jobs; a nightly backup "is not
  considered good until" its weekly restore drill has actually passed; `config.validate_config()`
  fails startup closed rather than run with silently-missing config.

## Decision-Making Hierarchy

When repository documents or mechanisms appear to conflict, the corpus states its own precedence
rules explicitly — use them in this order rather than guessing:

1. **A CI-enforced test is ground truth over any document's claim about the same fact.** The
   corpus's own `DECISION_LOG` §5 records multiple cases where a canonical document's status claim
   (e.g. "folder structure migrated ✅") was found false against the actual repository state —
   documents self-report, tests verify. If a doc and a test disagree, trust the test and flag the
   doc as stale.
2. **On a conflict about a mechanism already built and frozen in `docs/RESEARCH_MASTER_PLAN.md` v3,
   v3 wins.** On a conflict about scientific method or institutional governance, the Research OS
   wins. Neither plan's phase/layer numbering is imported into the other.
   (`docs/governance/RESEARCH_OS_RECONCILIATION.md` §5.)
3. **`docs/governance/TAXONOMY_AND_NAMING_STANDARD.md` is the controlled-vocabulary authority.**
   Every other document must use its terms with exactly its meanings.
4. **An operating-layer document defers to the standard it instantiates.**
   `docs/research_programs/RESEARCH_PROGRAM.md` states this of itself: it "introduces no normative
   content... where this document and a standard appear to conflict, the standard wins, and the
   conflict is a defect to be reported, not resolved here." Treat other thin operating instances
   (e.g. `OBJECTIVES_2026H2.md`) the same way.
5. **`docs/roadmap/DECISION_LOG.md` is the register of record** for governance/architecture
   decisions. A decision is authoritative once accepted there; it changes only via a new, dated,
   superseding entry — never a silent edit.
6. **`docs/roadmap/GOVERNANCE_BASELINE_v1.md` is the official snapshot of governance state** as of
   the Phase B freeze (2026-07-17). Measure any claim about what is frozen/canonical/open against it
   before an older or narrower document.
7. **"Canonical" does not mean "frozen" or "beyond question."** A canonical-but-not-frozen document
   (most of L3–L5, and L1 itself) is still the best current source, but carries a named open
   condition (independent review/sign-off) — surface that condition rather than treating the
   document as settled.

## Research jobs

Never run from production; see `CLAUDE.md` Architecture → Research package.

```bash
python -m research.cli wf-refresh       # walk-forward scores + wf_edge
python -m research.cli backtest-cache   # dashboard/quality-gate cache
python -m research.cli roller           # monthly window roller
python -m research.knowledge.cli ...    # hypothesis registration/tracing (docs/research_os/RESEARCH_PROTOCOL.md)
```
