# Cross-Machine Ubuntu Research Architecture

**Version:** 1.0
**Status:** ✅ APPROVED ARCHITECTURE BASELINE — **FROZEN**
**Document class:** Architecture Design Document (ADD) — canonical architecture specification
**Owner:** Owner (Principal Enterprise Architect, custodian)
**Supersedes:** v0.1 (2026-07-22, draft), v0.2 (2026-07-22, post-review draft)
**Review lineage:** Initial Proposal → Independent Architecture Review (Claude Opus) →
Architecture Revision v0.2 → ADD Quality Review → Governance Review (OI-8 resolved)
**Effective date:** 2026-07-22
**Branch of record:** `ops/hardening-2026-07-10` (sole carrier of the governance corpus)

> **Reading note.** This document is **self-contained**: it requires no prior version to be read.
> The architecture is **frozen**. Only documentation may change from here; any change to a decision
> requires a **new, approved ADR** (see §17 Frozen Architecture Statement). Observations that would
> require an architecture change are recorded in §15 *Future Architecture Revisions*, never applied
> inline.

---

## Table of Contents

1. Executive Summary
2. Architecture Context
3. Problem Statement
4. Goals & Success Criteria
5. Non-Goals / Out of Scope
6. Assumptions
7. Constraints
8. Architecture Principles
9. Architecture Overview (Context, Deployment, Data-Flow, Operational diagrams)
10. Architecture by Topic
11. Security Considerations
12. Operational Considerations
13. Scalability, Capacity & Disaster Recovery
14. Architecture Decision Records (ADR-001 … ADR-010)
15. Future Architecture Revisions
16. Open Issues
17. Frozen Architecture Statement
18. Implementation Roadmap (phases only)
19. Traceability Matrix
20. Revision Summary (v0.2 → v1.0)
21. Approval Checklist
- Appendix A — Review Resolution History
- Appendix B — Immediate Remediation Finding (live exposure)
- Appendix C — Glossary / Terminology
- Appendix D — References
- Appendix E — Governance Traceability

---

## 1. Executive Summary

Production and Research have become two workloads with opposing resource profiles competing on a
single Ubuntu laptop, to the point of Linux out-of-memory (OOM) events. This architecture separates
them onto two machines while keeping **Ubuntu as the only supported runtime**:

- **Production** remains on the Ubuntu laptop, unchanged.
- **Research** runs in **WSL2 Ubuntu** on existing Windows desktop hardware, treated as a headless
  Ubuntu compute node.

The two machines share **one Git repository** as the single authoritative source for code, moved by
**Git-over-SSH**. Research consumes Production's settled market data through an explicit
**one-directional, WAL-safe, read-only Research data snapshot** — never a live share and never a
bidirectional file sync. Reproducibility is protected by a standing rule: **Research executes only
from a clean, committed Git state.** No always-on filesystem-synchronization daemon exists in this
architecture.

The design directly resolves the resource-contention problem (physical machine separation),
preserves and *strengthens* the repository's existing research/production separation and
reproducibility invariants, and reuses primitives the repository already has (SSH, the SQLite
online-backup API, the dataset-fingerprint provenance ledger, and the CI write-fence).

---

## 2. Architecture Context

**Current state (before this architecture).** A single Ubuntu laptop runs both:

- the **Production Engine** — a long-running service (gunicorn, single worker; APScheduler; a
  Telegram poller; the SQLite writer for `data/walkforward.db`; the live IDX market scanner; health
  monitoring), whose objective is stability, predictability, and continuous uptime; and
- the **Research Engine** — walk-forward backtests, the statistical gatekeeper, regime analysis,
  feature engineering, parameter optimization, and experiment execution, whose objective is
  throughput and high CPU/RAM utilization.

These two profiles are in direct tension on one host. As the historical dataset grows every trading
day, Research increasingly consumes CPU, RAM, and disk I/O; investigation confirmed Linux OOM events
that terminated the developer's editor while Production continued to run. Production and Research now
contend for the same finite resources.

**Target state (this architecture).** Research is relocated to a second physical machine — a WSL2
Ubuntu node on existing Windows hardware — leaving the Production laptop uncontended. Code is shared
through one Git repository over SSH; Research data arrives as a periodic read-only snapshot. See §9
for the system-context, deployment, data-flow, and operational diagrams.

**Relationship to existing repository work.** This architecture **depends on and extends** the
repository's **R-5 (physical research/production DB split)** workstream — it does **not** originate,
advance, or modify it. R-5 is defined in `docs/RESEARCH_MASTER_PLAN.md` §3.3c / §5 (Invariant #1),
was **scoped to Tier-1 and resolved by owner decision on 2026-07-14**
(`docs/superpowers/specs/2026-07-14-r5-physical-db-split-scope.md`), and has a complete
implementation plan (`docs/superpowers/plans/2026-07-21-r5-tier1-physical-db-split.md`). R-5's own
mechanism — a writable `research.db` with production `ATTACH`ed **read-only** — is the data-access
pattern this architecture inherits and carries across a machine boundary. The governance
relationship is settled in **Appendix E** and the OI-8 resolution
(`docs/infra/OI-8_DECISION_LOG_RESOLUTION.md`).

---

## 3. Problem Statement

| ID | Problem | Evidence / origin |
|----|---------|-------------------|
| PR-1 | Production and Research contend for CPU, RAM, and disk I/O on one laptop. | Observed contention under heavy research load. |
| PR-2 | Research cannot scale independently; larger datasets demand more from the same machine that runs Production. | Dataset grows every trading day. |
| PR-3 | Heavy Research execution raises memory pressure, risking OOM-killer activation, degraded desktop responsiveness, and interrupted development. | Confirmed Linux OOM event (editor terminated). |
| PR-4 | Continuous historical-data growth will worsen contention over time. | Structural, not incidental. |
| PR-5 | A live Syncthing folder was replicating **secrets** and a **3.2 GB live WAL database**, creating secret-leak and DB-corruption exposure. | Independent review, confirmed on disk (Appendix B). |
| PR-6 | Synchronizing an uncommitted working tree between machines silently breaks the "git commit == executed code" guarantee that research provenance depends on. | Independent review (reproducibility Invariant #6). |

---

## 4. Goals & Success Criteria

### 4.1 Goals

| ID | Goal |
|----|------|
| G1 | Separate Production from Research. |
| G2 | Keep Ubuntu as the only supported runtime. |
| G3 | Avoid maintaining multiple operating-system targets. |
| G4 | Leverage existing Windows hardware without introducing Windows-native Python. |
| G5 | Provide a single logical development workflow. |
| G6 | Allow multiple agents/tools (e.g. Claude Code and z.ai) to operate on one synchronized repository. |
| G7 | Reduce Production resource contention. |
| G8 | Improve long-term scalability. |

### 4.2 Success Criteria (measurable expression of the goals)

| ID | Success criterion | Satisfies |
|----|-------------------|-----------|
| SC-1 | The Production laptop shows **zero OOM events** during a full research batch run. | G1, G7, PR-1/3 |
| SC-2 | Research runs on the second machine with **no runtime dependency on Production being idle**. | G1, G2, G7 |
| SC-3 | Both machines run the **same Ubuntu semantics**; `pytest -q` passes identically on each with no platform-specific modification. | G2, G3 |
| SC-4 | **No Windows-native Python** is introduced anywhere. | G3, G4 |
| SC-5 | A research result is **reproducible from its recorded git commit + dataset fingerprint**, because runs execute only from a clean committed state. | G5, PR-6 |
| SC-6 | Code moves between machines **solely via Git**; no secret and no live database is ever replicated by a sync tool. | G5, G6, PR-5 |
| SC-7 | Research throughput scales by adding/upgrading the Research node **without touching Production**. | G8, PR-2/4 |

---

## 5. Non-Goals / Out of Scope

**Non-Goals** — deliberately *not pursued* by this architecture:

- Migrating Production to Windows.
- Supporting Windows-native Python execution.
- Redesigning the Production Engine.
- Introducing distributed computing.
- Modifying application business logic.
- Using any filesystem-sync tool (Syncthing/Dropbox/etc.) as a code or database transport.

**Out of Scope** — *not covered by this document* (belongs to separate artifacts):

- Implementation steps, scripts, or configuration files (implementation documents are separate — §17).
- The R-5 Tier-1 split's own implementation (owned by its scoping note + plan; this ADD only
  consumes it).
- The Tier-2 "edge interface" reader-retirement workstream (deferred separately per the R-5
  scoping note §5).
- High-availability / hot-standby Production (not proposed here; see §15).

---

## 6. Assumptions

These load-bearing assumptions are stated so they can be audited; if one proves false, revisit the
affected decision.

| ID | Assumption |
|----|------------|
| AS-1 | Passwordless SSH between the two machines is available (or can be provisioned) as the Git and snapshot transport. |
| AS-2 | The Windows desktop hardware exists and can host a WSL2 Ubuntu instance with sufficient CPU/RAM for research batches. |
| AS-3 | The Research workload is **CPU/RAM-bound batch** work, not latency-sensitive or inbound-serving — so periodic (not real-time) data freshness is acceptable. |
| AS-4 | A single human/agent edits a given file at a time; concurrent multi-machine edits are resolved through Git branches, not ambient sync. |
| AS-5 | Production remains the sole writer of `data/walkforward.db`; Research never needs to write Production tables. |
| AS-6 | The governance corpus and this architecture live on `ops/hardening-2026-07-10`; `master` does not yet carry them. |
| AS-7 | R-5 (Tier-1 physical DB split) is available or will land, providing the `research.db` + read-only-prod pattern this architecture consumes. |

---

## 7. Constraints

| ID | Constraint | Source |
|----|------------|--------|
| CN-1 | Ubuntu is the only supported runtime; no second OS target. | G2/G3, P1 |
| CN-2 | Production gunicorn must run **exactly one worker** (embedded scheduler + single SQLite writer). | `gunicorn.conf.py`; `test_config_validation.py` |
| CN-3 | All SQLite access goes through the repository's hardened `connect()` entry points (WAL + busy_timeout); no direct `sqlite3.connect()` in production code. | `data/db.py` |
| CN-4 | Research code may not import execution modules and production code may not import `research.*`; production may not write research-owned tables. | `test_architecture_boundary.py`, `test_research_data_fence.py` |
| CN-5 | Secrets (`.env`, `.stockbit_token`) must be mode 600 and are gitignored; startup aborts if group/world-readable. | `config.py` startup validation |
| CN-6 | All timestamps are WIB (Asia/Jakarta, UTC+7). | Repository-wide |
| CN-7 | This document authorizes no implementation, scripts, source, infrastructure, or deployment change. | This release's mandate |

---

## 8. Architecture Principles

*(Previously "Design Principles"; renamed for ADD-standard vocabulary. Decisions unchanged.)*

| ID | Principle |
|----|-----------|
| P1 | Ubuntu is the only supported runtime. |
| P2 | WSL2 Ubuntu is a compute node, **operationally distinct** from bare-metal Ubuntu (memory, filesystem, lifecycle) and configured accordingly. |
| P3 | Production and Research are operationally isolated — separate hardware, separate database, separate environment. |
| P4 | Code moves only through **Git**. There is no second code-sync channel. |
| P5 | Data moves only through an explicit **one-directional, WAL-safe Research data snapshot** (Production → Research), consumed read-only. |
| P6 | Git is the single source of truth — and therefore the single code transport. |
| P7 | Every machine owns its own virtual environment **and its own secrets**; neither is ever synchronized. |
| P8 | Research executes only from a **clean, committed** Git state, so provenance in `research_runs` is truthful. |
| P9 | Replication is not backup; disaster recovery builds on the existing backup + restore-drill, not on any sync mechanism. |

---

## 9. Architecture Overview

### 9.1 System Context Diagram (C4-L1)

```
        ┌─────────────┐        commits / reviews        ┌──────────────────────┐
        │   Owner /    │────────────────────────────────▶│  Git remote (GitHub) │
        │  operator    │                                  │  authoritative code  │
        └──────┬───────┘                                  └───────────┬──────────┘
               │ operates                    git push/pull (SSH)      │ git push/pull (SSH)
        ┌──────▼───────────────┐                          ┌───────────▼──────────┐
        │  PRODUCTION           │   Research data          │  RESEARCH             │
        │  (Ubuntu laptop)      │   snapshot (read-only) ─▶│  (WSL2 Ubuntu node)   │
        │  live trading engine  │                          │  batch research       │
        └───┬───────────┬───────┘                          └───────────────────────┘
            │           │
      ┌─────▼────┐  ┌───▼────────┐
      │ Stockbit │  │ Telegram   │   (external systems — Production only)
      │  API     │  │  alerts    │
      └──────────┘  └────────────┘
```

### 9.2 Deployment View

```
                      Git remote (authoritative)
                                 │
              git push/pull (SSH)     git push/pull (SSH)
                  ┌──────────────┴───────────────┐
                  │                              │
          Ubuntu Laptop                   Windows Desktop
           (PRODUCTION)                          │
     ┌───────────────────────┐            WSL2 Ubuntu (ext4)
     │ gunicorn (workers=1)  │             (RESEARCH node)
     │ APScheduler           │          ┌────────────────────┐
     │ Telegram poller       │          │ walkforward / bt   │
     │ live scanner          │          │ gatekeeper / regime│
     │ walkforward.db (WAL)  │          │ optimizer / CLI    │
     │ nightly db_backup     │          │ research.db (R-5)  │
     └───────────┬───────────┘          │ + read-only prod   │
                 │                       │   snapshot         │
                 │  WAL-safe snapshot    └─────────┬──────────┘
                 │  (online-backup API), pulled via rsync-over-SSH
                 └──────────────────────────────────►
                     one-directional: PRODUCTION → RESEARCH
```

### 9.3 Data Flow Diagram

```
   PRODUCTION                                           RESEARCH (WSL2)
   ──────────                                           ───────────────
   walkforward.db (WAL, live)
        │
        │ (1) online-backup API  →  consistent snapshot file
        ▼
   snapshot (settled OHLCV + corporate_actions)
        │
        │ (2) rsync-over-SSH (pull)     ───────────────▶  snapshot opened READ-ONLY
        │                                                        │
                                                                 │ (3) research reads input
   Git remote ◀─(A) push code──┐                                 ▼
        │                       │                        research.db (WRITABLE, R-5 Tier-1)
        └──(B) pull code────────┴──────────────────────▶ research-owned tables written here
                                                                 │
   (C) human-gated promotion (Edge Registry, over Git) ◀─────────┘
```

Directionality is strict: **market data flows Production → Research only**; code flows through the
Git remote both ways; **promotion of a validated edge flows back to Production solely by the
human-gated Edge Registry over Git** — never by a data sync.

### 9.4 Operational / Decision Flow

```
 edit (either machine)
    → git commit → git push
        → git pull (other machine)
            → [Research only] pull Research data snapshot
                → run ONLY from a clean, committed state (P8)
                    → commit results/artifacts to preserve
                        → human-gated promotion via Edge Registry (P3, unchanged)
```

---

## 10. Architecture by Topic

Each topic states **why it exists, the problem it solves, trade-offs, risks, and alternatives
considered.** These are the frozen decisions; the ADRs in §14 are their register form.

### 10.1 Git vs Syncthing — code synchronization
**Decision:** Git-over-SSH is the sole code-movement mechanism; no filesystem-sync daemon is used.
- **Why / problem:** Git already provides versioned, branch-scoped, conflict-explicit
  synchronization — the job a sync tool was meant to accelerate. Two mechanisms for the same files
  are two sources of truth. Eliminates `sync-conflict-*` files that could trip CI source-scanners or
  be committed, `.git/` corruption risk, and the false-provenance failure (§10.3).
- **Trade-offs:** loses "ambient, no-command" convenience; a developer must commit/push/pull
  deliberately — intended here.
- **Risks:** friction may tempt out-of-band copying; mitigated by SSH already being available (AS-1)
  and by P8.
- **Alternatives considered:** sync-tool code-only with exclusions (rejected — still permits false
  provenance, adds a daemon for no gain); rsync-push of code (rejected — bypasses history/branching).

### 10.2 Repository synchronization & workflow
**Decision:** One logical repository, one clone per machine, moved by branch push/pull; no
duplicated repos, no shared mount.
- **Why / problem:** preserves "one logical repository" using Git's native model; each machine keeps
  a self-consistent `.git/` + working tree, so there are no cross-machine working-tree races.
- **Trade-offs:** Research must pull before running and push results to preserve them.
- **Risks:** branch drift; mitigated by treating the active branch as the handoff and by CI parity
  (§12).
- **Alternatives considered:** shared network mount (rejected — SQLite locking + latency); sync tool
  (rejected, §10.1).

### 10.3 Research reproducibility
**Decision (P8):** Research executes only from a **clean, committed** Git state; a dirty working tree
is a stop condition for a recorded experiment.
- **Why / problem:** `research/tracking.py` records a git commit per run; reproducibility Invariant
  #6 requires *commit == the bytes that ran*. Moving uncommitted changes between machines could make
  the recorded commit fail to reproduce the executed code — provenance that is silently false, which
  is worse than none.
- **Trade-offs:** exploratory "just run it" iterations must be committed first or marked untracked;
  slightly slower loop.
- **Risks:** a run is executed dirty anyway. This is a **documentary invariant** in v1.0; hardening
  it into a runtime guard is OI-3.
- **Alternatives considered:** capture a working-tree diff alongside the commit (deferred, OI-3);
  do nothing (rejected — breaks Invariant #6).

### 10.4 Research data snapshot (SQLite)
**Decision (P5):** Production emits a **WAL-safe consistent snapshot** via the SQLite online-backup
API (the mechanism present as `scripts.db_backup`); Research pulls it via rsync-over-SSH and opens it
**read-only**. Live `.db`/`-wal`/`-shm` files are never synced.
- **Why / problem:** WAL-mode SQLite is three coupled files; copying them independently mid-checkpoint
  corrupts the database. The online-backup API yields one transactionally consistent file safely
  while writers are active.
- **Trade-offs:** Research data is as fresh as the last snapshot — correct for walk-forward/backtest
  work, which should run against a settled, pinned corpus.
- **Risks:** multi-GB transfer cost; mitigated by rsync deltas and an explicit cadence (OI-2).
- **Alternatives considered:** `VACUUM INTO` (acceptable variant); live-file copy/rsync of a WAL DB
  (rejected — corruption); streaming replication (deferred — over-engineered for a batch feed).

### 10.5 Database architecture (depends on / extends R-5)
**Decision:** Production remains the sole writer of `walkforward.db`. Research operates on a
**read-only snapshot** of the settled OHLCV corpus + `corporate_actions`, plus its **own** writable
research database for research-owned tables — the **R-5 Tier-1 pattern**, carried across the machine
boundary.
- **Why / problem:** the repository has one `walkforward.db` with a CI-enforced logical write-fence
  (`test_research_data_fence.py`). R-5 already makes that fence physical (writable `research.db` +
  production `ATTACH`ed read-only). This architecture **consumes** that pattern; the only difference
  is that the read-only production input arrives as a **cross-machine snapshot** rather than a local
  read-only attach.
- **Data-flow direction:** strictly Production → Research. Promotion back to Production remains the
  human-gated Edge Registry over Git — never a DB sync.
- **Trade-offs:** two DB files on the Research node (read-only input snapshot + writable research DB).
- **Risks:** the split must keep `test_research_data_fence.py` meaningful across the boundary (OI-1,
  owned by R-5).
- **Alternatives considered:** one shared DB over the network (rejected — locking); a client/server
  DB for research (deferred — large change).
- **Governance note:** this is a **dependency on R-5, not an advancement of it** — see §2 and
  Appendix E; OI-8 is resolved with no Decision Log entry required.

### 10.6 Secrets management
**Decision (P7):** `.env` and `.stockbit_token` are **excluded from every transport**, provisioned
per-machine, held at **mode 600**. Consolidated detail in §11.
- **Why / problem:** the repository's startup validation aborts on group/world-readable secrets and
  requires 600; a sync tool would both leak the token to a second machine and likely break the mode.
  (The live pre-existing violation is recorded in Appendix B.)
- **Trade-offs:** each machine is provisioned with its own secrets manually — correct for security.
- **Alternatives considered:** encrypted secret sync / vault (deferred, OI-6).

### 10.7 Environment isolation
**Decision (P7):** Per-machine `venv/` (never synced) and per-machine `.env` (never synced). Research
defaults to **agent-firm off** and **Telegram alerting off**, with `DB_PATH` pointing at the
snapshot / research DB; Production keeps live settings.
- **Why / problem:** `config.py` is the single `.env` reader; the mode flags legitimately differ
  between a live and a research box. Sharing env would fire live alerts from research runs or consume
  the shared agent-firm quota window.
- **Trade-offs:** two config files; drift possible — mitigated by keeping `.env.example` authoritative
  for shape (committed) while values stay per-machine, and by CI parity (§12).
- **Alternatives considered:** one shared `.env` (rejected); orchestrated env injection (deferred).

### 10.8 WSL2 operational baseline
**Decision (P2):** Keep WSL2 as the Research host, treated as a tuned VM, not bare-metal:
1. **Memory** bounded via `.wslconfig` (`memory=`, `processors=`, `swap=`). The OOM class of failure
   is **relocated, not eliminated** — under pressure the *guest* Linux OOM killer fires inside the
   VM (killing the research job, not the desktop); this is an accepted, deliberate outcome.
2. **Filesystem:** repo and all DB files live on the **WSL2-native ext4 path**, never `/mnt/c`
   (SQLite over the `/mnt` 9P/DrvFs boundary is slow and has known locking/corruption behavior).
3. **Lifecycle:** systemd-in-WSL2 enabled for long-running jobs; the Windows host configured not to
   sleep during runs; awareness that WSL2 halts when its last process exits.
4. **Clock:** guest clock can skew on resume; time-sync on resume is required (WIB provenance).
- **Why / problem:** these are the concrete ways WSL2 differs from bare-metal for a memory-bound
  batch workload; leaving them implicit reintroduces contention inside an unbounded VM.
- **Trade-offs:** WSL2 management overhead — the accepted cost of using existing hardware.
- **Alternatives considered:** a dedicated/native Linux box (deferred — no hardware on hand; see
  §15/OI-7); dual-boot (rejected — cannot run simultaneously); cloud runner (deferred — cost + egress
  of a multi-GB corpus).

### 10.9 Line-ending & CI parity discipline
**Decision:** A `.gitattributes` policy (`* text=auto`, `*.sh text eol=lf`) keeps shell scripts LF
across the Windows/WSL2/Ubuntu boundary; CI parity assumes the repo lives on **ext4 inside WSL2**
(not `/mnt/c`), and CPU-count differences can affect parallel-test behavior.
- **Why / problem:** protects "both environments behave identically." *(Authoring `.gitattributes`
  is implementation and is out of scope for this ADD; it is recorded here and in §18 as a required
  outcome, not performed.)*

---

## 11. Security Considerations

Consolidated from §10.6/§10.7 and Appendix B so a reviewer can audit security in one place.

- **Secrets never transit any sync channel.** `.env` and `.stockbit_token` are gitignored,
  excluded from any file transport, and provisioned **per machine** at **mode 600** (CN-5). A sync
  tool would both leak the Stockbit token to a second host and break the 600 mode that Production
  startup validation requires.
- **No live secret propagation.** Because there is no ambient sync (P4/P6), a secret change on one
  machine does not silently appear on the other; provisioning is deliberate.
- **Least-privilege Research environment.** Research defaults to agent-firm off and Telegram
  alerting off (§10.7), so a research batch cannot emit live alerts, place trades, or consume the
  shared agent-firm quota window.
- **Production data reaches Research read-only.** The snapshot is opened read-only (P5) and, under
  R-5, production is `ATTACH`ed read-only — there is no writable path from Research to Production
  data.
- **Boundary integrity preserved.** The research/production import boundary and write-fence (CN-4)
  remain CI-enforced; this architecture strengthens their physical expression without altering their
  definitions.
- **Transport security.** Code and snapshot both move over SSH (AS-1).
- **Standing finding.** A pre-existing live exposure (secrets + a 3.2 GB live WAL DB under a running
  Syncthing folder) is documented in **Appendix B** as a precondition to remediate; it predates and
  is independent of this architecture.

---

## 12. Operational Considerations

- **Development workflow:** Git-mediated end to end (§9.4). Research pulls code and the data
  snapshot, runs from a clean committed state, and commits artifacts to preserve.
- **Promotion path (unchanged):** Research → Production promotion remains solely the human-gated
  Edge Registry over Git; this architecture adds no new promotion channel.
- **CI parity:** both machines must run `pytest -q` identically with no platform-specific
  modification (SC-3); parity assumes the ext4-native repo location (§10.9).
- **Snapshot operation:** Production emits the WAL-safe snapshot on a defined cadence; Research pulls
  on demand (cadence/size settled in OI-2).
- **WSL2 provisioning checklist (operational, not implementation):** bounded `.wslconfig`,
  ext4-native repo path, systemd enabled, host-sleep disabled during runs, clock-sync on resume
  (§10.8).
- **Operational readiness:** ownership, monitoring, and the restore-drill cadence (§13) must be in
  place before the Research node is relied upon.

---

## 13. Scalability, Capacity & Disaster Recovery

### 13.1 Scalability & capacity
- Research scales on separate hardware without touching Production (SC-7). Larger scale is addressed
  by upgrading or replacing the Research node (see §15/OI-7 for the dedicated-node evolution).
- Capacity dimensions to plan at the architecture level: Research-node memory ceiling (bounded by
  `.wslconfig`), the growing corpus snapshot size and its transfer cost, and disk budget for two DB
  files on the Research node. Concrete figures are an implementation/operations concern (OI-2).

### 13.2 Disaster recovery (P9)
- DR builds on the **existing** nightly `scripts.db_backup` (online-backup API, WAL-safe,
  integrity-checked) + the **weekly restore drill** (`scripts.db_restore`) that already defines a
  good backup. **No sync mechanism is part of DR** — replication propagates deletion/corruption
  instantly and is not a backup.
- **Roles:** the Production laptop is the **system of record** for live-only tables (paper trades,
  `provider_events`, the `research_runs` ledger); its loss is covered by restoring the latest
  *verified* backup onto replacement hardware. The Research node is near-stateless — reproducible
  from a committed commit + a re-pulled snapshot — so its loss costs only in-flight compute.

---

## 14. Architecture Decision Records

> **Status:** all ADRs are **ACCEPTED** and **FROZEN** as of this baseline. Decisions are preserved
> verbatim in substance from v0.2; v1.0 adds Principle/Goal/Open-Issue back-links (documentation
> only). Changing any ADR requires a new, approved ADR (§17).

**ADR-001 — Separate Production and Research onto different physical machines**
Decision: Production stays on the Ubuntu laptop; Research moves to WSL2 Ubuntu on the Windows
desktop. · Serves: G1, G7 / PR-1..4 · Principles: P1, P3 · Status: ACCEPTED (FROZEN).
Alternatives: single laptop (rejected — contention/OOM); dedicated Linux box (deferred — no
hardware); cloud (deferred — cost/egress). Rationale: physical separation is what resolves the
contention problem, independent of the sync mechanism.

**ADR-002 — Git-over-SSH is the sole code transport; no filesystem-sync daemon**
Decision: code moves only via Git. · Serves: G5, G6 / PR-5, PR-6 · Principles: P4, P6 · Status:
ACCEPTED (FROZEN). Alternatives: sync-tool code-only with exclusions (rejected — false provenance,
added daemon for no gain); rsync of code (rejected — no history/branching). Rationale: Git already
performs cross-machine code sync with history, branching, and explicit conflicts; a second channel
is a second source of truth.

**ADR-003 — Research executes only from a clean, committed Git state**
Decision: a tracked research run requires a clean working tree at a known commit. · Serves: G5 /
PR-6 · Principles: P8 · Open Issue: OI-3 (runtime enforcement) · Status: ACCEPTED (FROZEN;
documentary invariant). Alternatives: record a working-tree diff (deferred); no rule (rejected —
breaks Invariant #6). Rationale: makes `research_runs` provenance truthful.

**ADR-004 — Production→Research data via WAL-safe read-only snapshot**
Decision: ship a consistent snapshot (online-backup API / `VACUUM INTO`), pulled by rsync-over-SSH,
opened read-only. · Serves: G1, G8 / PR-1, PR-5 · Principles: P5 · Open Issue: OI-2 · Status:
ACCEPTED (FROZEN). Alternatives: live-file copy/rsync of a WAL DB (rejected — corruption); streaming
replication (deferred). Rationale: WAL DBs cannot be copied file-wise while live; research should run
on a settled, pinned corpus.

**ADR-005 — Consume the R-5 physical DB split; preserve the CI write-fence**
Decision: Research holds a read-only input snapshot + a separate writable research DB; Production
remains sole writer of `walkforward.db`. · Serves: G1 / PR-1 · Principles: P3, P5 · Open Issue: OI-1
(owned by R-5) · Status: ACCEPTED (FROZEN). Alternatives: one shared DB over the network (rejected —
locking); Postgres for research (deferred). Rationale: makes the logical write-fence physical across
the machine boundary. **Note:** depends on R-5; does not modify it (§2, Appendix E).

**ADR-006 — Secrets excluded from all transport, per-machine, mode 600**
Decision: `.env`/`.stockbit_token` never synced; provisioned per machine at 600. · Serves: G4 / PR-5
· Principles: P7 · Constraint: CN-5 · Status: ACCEPTED (FROZEN). Alternatives: encrypted secret sync
/ vault (deferred, OI-6). Rationale: sync would leak secrets and violate the 600 startup requirement.

**ADR-007 — Per-machine environment isolation**
Decision: separate venv and `.env` per machine; Research defaults alerting/agent-firm off. · Serves:
G2, G4 · Principles: P7 · Status: ACCEPTED (FROZEN). Alternatives: shared env (rejected); orchestrated
injection (deferred). Rationale: prevents research runs from firing live alerts or consuming shared
quota.

**ADR-008 — WSL2 operational baseline (bounded memory, ext4, systemd, no-sleep, clock sync)**
Decision: treat WSL2 as a tuned VM per §10.8. · Serves: G2, G4, G7 / PR-3 · Principles: P2 · Open
Issue: OI-7 · Status: ACCEPTED (FROZEN). Alternatives: native/dedicated Linux box (deferred);
dual-boot (rejected). Rationale: WSL2 ≠ bare-metal for memory-bound batch work; an unbounded VM
recreates the OOM problem.

**ADR-009 — DR builds on existing backup + restore drill; replication ≠ backup**
Decision: keep nightly online backup + weekly restore drill as the DR spine; no sync in DR. · Serves:
G1, G8 · Principles: P9 · Status: ACCEPTED (FROZEN). Alternatives: treat sync as backup (rejected);
hot standby (deferred, §15). Rationale: sync propagates deletion/corruption instantly; the repo
already has a verified backup story.

**ADR-010 — Line-ending & CI-parity discipline**
Decision: adopt a `.gitattributes` LF policy for `.sh`; pin the ext4-native repo location for CI
parity. · Serves: G2, G3 / SC-3 · Principles: P1, P2 · Status: ACCEPTED (FROZEN; authoring the file
is implementation, out of scope). Alternatives: rely on editor config (rejected — not enforced).
Rationale: prevents CRLF breakage of shell scripts across the OS boundary.

---

## 15. Future Architecture Revisions

Observations that *would* require an architecture change are recorded here — **not applied** — per
the frozen-architecture rule. Each needs a new, approved ADR before any action.

- **FR-1 — Dedicated always-on Research node.** A sleep-prone Windows desktop is imperfect for
  multi-hour jobs (AS-2, OI-7). A future revision may replace the WSL2 node with a dedicated,
  always-on Linux machine. *Would change deployment → new ADR required.*
- **FR-2 — Research datastore beyond SQLite.** If snapshot size/throughput outgrows SQLite, a future
  revision may introduce a client/server research datastore. *Would change database strategy → new
  ADR required.*
- **FR-3 — Streaming/continuous data replication.** If research freshness requirements tighten beyond
  periodic snapshots, streaming replication may be reconsidered. *Would change data strategy → new
  ADR required.*
- **FR-4 — Runtime enforcement of clean-committed-state (OI-3).** Promoting P8 from a documentary
  invariant to a runtime guard in the research entry points. *Behavior change → ADR + implementation
  design required.*
- **FR-5 — High-availability Production.** A hot-standby Production for instant failover (beyond
  restore-from-backup). *Would change deployment/DR → new ADR required.*
- **FR-6 — Tier-2 edge-interface split.** The deferred R-5 §5 reader-retirement workstream, if pulled
  into this architecture's scope. *Owned by R-5 today; a scope change → coordinate with R-5 + ADR.*

---

## 16. Open Issues

| ID | Open issue | Owner / gate | Status |
|----|------------|--------------|--------|
| OI-1 | Keep `test_research_data_fence.py` meaningful under a two-DB (read-only snapshot + writable research DB) topology. | R-5 workstream | Open — gates ADR-005 realization |
| OI-2 | Research-data-snapshot cadence, retention, transfer method, and acceptable staleness (corpus 3.2 GB, growing). | Ops | Open |
| OI-3 | Enforce P8 "clean committed state" as a runtime guard vs. keep documentary. | Research eng | Open (see FR-4) |
| OI-4 | Mark throwaway/exploratory runs so they are clearly not part of the append-only `research_runs` ledger. | Research eng | Open |
| OI-5 | Confirm Research→Production promotion remains solely the human-gated Edge Registry over Git. | Governance | Open (confirmation) |
| OI-6 | Whether a later encrypted-at-rest / vault mechanism is warranted for secrets. | Security | Open |
| OI-7 | Whether a sleep-prone desktop is acceptable long-term, or argues for a dedicated node. | Architecture | Open (see FR-1) |
| OI-8 | Whether this proposal requires a Decision Log entry (it advances R-5). | Governance | **RESOLVED** — no entry required; see Appendix E / `OI-8_DECISION_LOG_RESOLUTION.md` |

---

## 17. Frozen Architecture Statement

- **Architecture decisions are frozen.** Every decision in §10 and every ADR in §14 is an
  APPROVED, FROZEN baseline as of 2026-07-22.
- **Future changes require a new ADR.** No decision, technology, deployment, workflow, Git strategy,
  database strategy, WSL2 strategy, or governance decision may change except through a new
  Architecture Decision Record that is proposed, reviewed, and approved. Observations pointing at
  such change are parked in §15, not applied.
- **Documentation improvements remain allowed.** Clarifications, corrections, added diagrams,
  glossary/reference expansion, and reorganization that do **not** alter a decision may be made to
  this document without a new ADR.
- **Implementation documents are separate artifacts.** This ADD authorizes no implementation,
  scripts, source, infrastructure, or deployment change. Implementation is carried by separate
  documents (e.g. the R-5 scoping note + plan, and any future implementation plan for this
  architecture), which reference — but are not part of — this baseline.

---

## 18. Implementation Roadmap (phases only — no steps)

> Ordering guidance for a *future* implementation effort. This ADD authorizes none of it.

- **Phase 0 — Contain the live exposure** (Appendix B precondition): stop secrets and the live DB
  from syncing; correct secret permissions.
- **Phase 1 — Establish Git-over-SSH as the sole code path**; retire any filesystem-sync for this
  repo; confirm the branch-based workflow.
- **Phase 2 — Stand up the WSL2 Research node** to the §10.8 baseline (bounded memory, ext4-native
  repo, systemd, no-sleep host, clock sync, independent venv + per-machine `.env`).
- **Phase 3 — Define and operate the Research data snapshot** (WAL-safe emission + read-only
  consumption); settle OI-2.
- **Phase 4 — Realize the R-5 physical DB split consumption** once OI-1 is resolved and the
  write-fence test is proven to remain meaningful.
- **Phase 5 — Reproducibility hardening** (OI-3/OI-4).
- **Phase 6 — Governance & operational close-out**; re-run independent review against the system as
  built.

---

## 19. Traceability Matrix

Problem → Goal → Principle → ADR → Open Issue → Governance Artifact.

| Problem | Goal | Principle | ADR | Open Issue | Governance Artifact |
|---------|------|-----------|-----|-----------|---------------------|
| PR-1 contention/OOM | G1, G7 | P3 | ADR-001, ADR-005 | OI-1 | `RESEARCH_MASTER_PLAN` §5 Inv #1; R-5 scoping note |
| PR-2 no independent scaling | G8 | P3 | ADR-001 | OI-7 | `RESEARCH_MASTER_PLAN` §3.3c |
| PR-3 memory pressure/OOM | G7 | P2 | ADR-008 | OI-7 | — (ops) |
| PR-4 dataset growth | G8 | P5 | ADR-004 | OI-2 | R-5 plan (`2026-07-21-...`) |
| PR-5 secret + live-DB exposure | G4 | P7, P9 | ADR-004, ADR-006, ADR-009 | OI-6 | `config.py` startup validation; `scripts.db_backup`/`db_restore` |
| PR-6 false provenance | G5 | P4, P6, P8 | ADR-002, ADR-003 | OI-3, OI-4 | `RESEARCH_MASTER_PLAN` §5 Inv #6; `research/tracking.py` |
| (separation integrity) | G1 | P3 | ADR-005 | OI-1, OI-5 | `test_research_data_fence.py`; `test_architecture_boundary.py`; R-5 scoping note §6; `OI-8_DECISION_LOG_RESOLUTION.md` |
| (Ubuntu-only parity) | G2, G3 | P1, P2 | ADR-010 | — | `test_config_validation.py` (CN-2) |

Every ADR resolves to at least one Problem and Goal; no ADR is orphaned. R-5 governance linkage is
detailed in Appendix E.

---

## 20. Revision Summary (v0.2 → v1.0)

Documentation-only changes; **no architecture, ADR, or decision was altered.**

1. **Self-containment:** added a full **Problem Statement** (§3) and **Architecture Context** (§2);
   the document no longer requires reading v0.1/v0.2.
2. **New framing sections** added per the ADD Quality Review: **Assumptions** (§6), **Constraints**
   (§7), **Success Criteria** (§4.2), consolidated **Security Considerations** (§11), **Operational
   Considerations** (§12), **Scalability/Capacity/DR** (§13), **Glossary** (Appendix C),
   **References** (Appendix D), **Governance Traceability** (Appendix E).
3. **Reorganization** to the recommended TOC: standing content raised into the body; the **Review
   Resolution Matrix** and **Immediate Remediation Finding** moved to **Appendices A and B**.
4. **Diagrams:** added a **System Context** diagram (§9.1), an isolated **Data Flow** diagram (§9.3),
   and an **Operational/Decision Flow** (§9.4); the v0.2 diagram is retained and relabeled as the
   **Deployment View** (§9.2).
5. **Terminology normalized:** "Design Principles" → **Architecture Principles**; a single canonical
   term **"Research data snapshot"**; **Non-Goals / Out of Scope** unified (§5).
6. **De-duplicated explanations:** the live-exposure fact is now stated authoritatively **once** in
   Appendix B and referenced elsewhere; the Syncthing-removal rationale lives in §10.1 with ADRs
   citing it rather than restating.
7. **Traceability upgraded:** the v0.2 goals table is replaced by a full **Problem→Goal→Principle→
   ADR→Open Issue→Governance Artifact** matrix (§19); ADRs gained Principle/Goal/OI back-links.
8. **OI-8 resolved & the one wording correction applied:** §2/§10.5 now state the architecture
   **depends on / extends R-5** rather than "advances" it, per the OI-8 governance determination;
   OI-8 marked RESOLVED (§16).
9. **Governance scaffolding:** added the **Frozen Architecture Statement** (§17), **Future
   Architecture Revisions** (§15), **Approval Checklist** (§21), and Owner/status/version metadata.
10. **Status/versioning:** renamed to **Cross-Machine Ubuntu Research Architecture, Version 1.0**,
    **APPROVED ARCHITECTURE BASELINE**.

---

## 21. Approval Checklist (governance sign-off)

| # | Item | ✓ |
|---|------|---|
| 1 | All prior reviews complete (Independent Review, v0.2 revision, ADD Quality Review, OI-8 governance). | ☐ |
| 2 | Every v0.2 architecture decision preserved unchanged; no new technology, deployment, workflow, Git, DB, WSL2, or governance decision introduced. | ☐ |
| 3 | Document is self-contained (Problem Statement + Architecture Context present; no need to read prior versions). | ☐ |
| 4 | Required framing sections present: Assumptions, Constraints, Success Criteria, Security, Operational, Scalability/DR, Glossary, References. | ☐ |
| 5 | Diagrams present: System Context, Deployment, Data Flow, Operational Flow. | ☐ |
| 6 | Traceability matrix complete; no orphaned ADR. | ☐ |
| 7 | OI-8 resolved and reflected; R-5 stated as a dependency, not an advancement. | ☐ |
| 8 | Frozen Architecture Statement present; future-change process (new ADR) stated. | ☐ |
| 9 | Future Architecture Revisions section captures deferred/change-requiring observations. | ☐ |
| 10 | No implementation, scripts, source, infrastructure, or deployment change introduced by this release. | ☐ |
| 11 | Appendix B live-exposure remediation acknowledged as a precondition (tracked, not performed here). | ☐ |
| 12 | Owner sign-off: __________________________  Date: ____________ | ☐ |

---

## Appendix A — Review Resolution History

The independent review of v0.1 produced ten findings; all were accepted (one — WSL2 — partially, in
that the critique was accepted but WSL2 retained with constraints). Their resolutions are now the
frozen decisions in §10/§14. Summary:

| Finding | Resolution in this baseline |
|---------|-----------------------------|
| Live secrets + 3.2 GB WAL DB syncing | Appendix B (precondition); ADR-006; §11 |
| Sync-over-Git-tree breaks reproducibility | P8; ADR-003; §10.3 |
| Git already is the code sync; sync tool is risk-for-no-gain | ADR-002; §10.1 |
| Peer-DB model wrong; one file + write-fence; R-5 dependency | ADR-005; §10.5; Appendix E |
| WSL2 ≠ bare-metal (partial) | ADR-008; §10.8 (retained with constraints) |
| Replication ≠ backup; DR under-specified | ADR-009; §13.2 |
| Secrets omission; per-machine + 600 | ADR-006; §11 |
| Missing `.gitattributes`/line-endings | ADR-010; §10.9 |
| CI parity (ext4, CPU count) | §10.9; §12 |
| Recommended Git-over-SSH + snapshot; drop sync | Adopted as the baseline (§9–§10) |

## Appendix B — Immediate Remediation Finding (live exposure)

A pre-existing exposure, **independent of and predating** this architecture, confirmed on disk on
`D:\IDX`:

- The Syncthing ignore policy (`.stignore`) excluded caches/venv but **not** `.env`,
  `.stockbit_token`, `data/*.db`, or `logs/`.
- `.env` and `.stockbit_token` were mode **644** (require 600); `data/walkforward.db` was **~3.2 GB
  with live `-wal`/`-shm`** and being replicated.

**This is a finding + precondition, not implementation.** Before any build-out (Roadmap Phase 0):
stop secrets and the live DB from syncing, and correct the secret files to mode 600. The commands to
do so are implementation and are deliberately not included here.

## Appendix C — Glossary / Terminology

*(For repository-wide terms, see `CLAUDE.md` "Repository Terminology".)*

| Term | Meaning |
|------|---------|
| Production Engine | The live IDX trading service on the Ubuntu laptop (gunicorn, scheduler, scanner, Telegram, SQLite writer). |
| Research node | The WSL2 Ubuntu compute host for batch research. |
| Research data snapshot | The one-directional, WAL-safe, read-only copy of Production's settled OHLCV + `corporate_actions`, consumed by Research. |
| WAL | SQLite Write-Ahead Logging mode; a live DB is three coupled files (`.db`/`-wal`/`-shm`). |
| Online-backup API | SQLite's mechanism for a consistent snapshot while writers are active (`scripts.db_backup`). |
| Write-fence | The CI test asserting production never writes research-owned tables (`test_research_data_fence.py`). |
| R-5 | The repository's physical research/production DB split workstream (Tier-1), on which this architecture depends. |
| WSL2 | Windows Subsystem for Linux v2 — a lightweight VM running a real Ubuntu kernel. |
| WIB | Asia/Jakarta time, UTC+7 — all timestamps. |
| Edge Registry | The human-gated research→production strategy handoff contract. |
| Clean committed state | A Git working tree with no uncommitted changes at a known commit (precondition for a tracked research run). |

## Appendix D — References

- `docs/RESEARCH_MASTER_PLAN.md` §3.3c, §5 (Invariants #1, #6; R-5 elevation)
- `docs/superpowers/specs/2026-07-14-r5-physical-db-split-scope.md` (R-5 scope + owner decision)
- `docs/superpowers/plans/2026-07-21-r5-tier1-physical-db-split.md` (R-5 implementation plan)
- `docs/roadmap/DECISION_LOG.md` (Research-OS decision register; latest ID D-028)
- `docs/infra/OI-8_DECISION_LOG_RESOLUTION.md` (OI-8 governance determination)
- `docs/infra/CROSS_MACHINE_RESEARCH_ARCHITECTURE_v0.2_ADD_QUALITY_REVIEW.md` (ADD quality review)
- `tests/test_research_data_fence.py`, `tests/test_architecture_boundary.py`,
  `tests/test_config_validation.py` (CI-enforced invariants)
- `scripts/db_backup.py`, `scripts/db_restore.py` (backup + restore drill)
- `research/tracking.py` (dataset fingerprint + provenance ledger)
- `CLAUDE.md` (repository operating manual + terminology)
- v0.1 / v0.2 of this document (superseded; retained for history)

## Appendix E — Governance Traceability

- **R-5 relationship:** this architecture **depends on and extends** R-5; it does **not** advance,
  originate, or modify it. R-5's definition (`RESEARCH_MASTER_PLAN` §3.3c/§5), Tier-1 owner decision
  (scoping note §6, 2026-07-14), and implementation plan are unchanged by this ADD.
- **OI-8 determination:** **no `docs/roadmap/DECISION_LOG.md` entry is required** for this
  architecture, on three grounds — the "advances R-5" premise is inaccurate (it is a dependency),
  the Decision Log is the Research-OS governance register (this is Infrastructure), and the document
  is a frozen-for-review baseline rather than an accepted-and-enacted decision. R-5 itself is
  recorded in a `docs/superpowers/` spec, not the Decision Log — the controlling precedent. Full
  reasoning: `docs/infra/OI-8_DECISION_LOG_RESOLUTION.md`.
- **Deferred trigger:** a Decision Log *pointer* entry (draft **D-029**, held unfiled in the OI-8
  resolution §8) becomes appropriate **only if** this architecture is later accepted for
  implementation **and** is found to change how **Invariant #1** is *enforced*.
- **Invariants engaged (strengthened, not modified):** #1 (research/production separation) and #6
  (reproducibility).

---

*End of Architecture Design Document v1.0 — APPROVED ARCHITECTURE BASELINE. Documentation-only
release. No implementation, scripts, source, infrastructure, or deployment change is authorized by
it. Architecture is frozen; future changes require a new, approved ADR.*
