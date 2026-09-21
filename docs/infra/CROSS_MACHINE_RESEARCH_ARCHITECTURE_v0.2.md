# Cross-Machine Ubuntu Research Architecture Proposal

**Version:** v0.2 (Post-Review Draft for Independent Re-Review)
**Status:** REVIEW REQUIRED — DO NOT IMPLEMENT
**Supersedes:** v0.1 (2026-07-22)
**Author:** Owner
**Reviser (this version):** Principal Infrastructure Architect
**Independent review incorporated:** Claude Opus review of v0.1
**Date:** 2026-07-22

> This is an architecture document. Implementation is out of scope until this version has itself
> been independently reviewed. It proposes no source-code changes, no scripts, and no changes
> outside infrastructure architecture. It advances a repository invariant already on record
> (R-5, physical DB split) and must be read alongside `docs/RESEARCH_MASTER_PLAN.md` §5 and
> `CLAUDE.md`.

---

## 0. What Changed From v0.1

v0.1 proposed moving Research to a Windows-hosted WSL2 Ubuntu instance and synchronizing the
workspace between the Production laptop and the Research machine using **Syncthing**, with Git
retained as the nominal source of truth.

The independent review identified that the Syncthing layer was the dominant risk, that it was
**already live and already misconfigured on the Windows machine** (syncing secrets and a 3.2 GB
live WAL-mode SQLite database), and that Git already performs the code-synchronization role
Syncthing was meant to accelerate. v0.2 makes one decisive change:

> **Syncthing is removed from the architecture. Code moves by Git-over-SSH. Data moves by a
> WAL-safe, one-directional Production→Research snapshot. Nothing bidirectional syncs a working
> tree or a live database ever again.**

Everything else in v0.1 (Ubuntu-only, machine separation, per-machine venvs, WSL2 as the Research
host) is retained, several items with added operational constraints.

The **core goal is preserved**: separate Production and Research onto different physical hardware,
keep Ubuntu as the only runtime, and do it while *strengthening* — not weakening — the repository's
reproducibility and separation invariants.

---

## 1. Executive Summary

Production and Research have become two workloads with opposing resource profiles competing on one
laptop, to the point of Linux OOM events. This proposal separates them onto two machines:

- **Production** stays on the Ubuntu laptop, unchanged.
- **Research** runs in **WSL2 Ubuntu** on existing Windows desktop hardware, treated as a headless
  Ubuntu compute node.

The two machines share **one Git repository** as the authoritative source for code. Research
consumes Production's settled market data through an explicit **read-only snapshot**, not a live
share. There is no ambient file synchronization daemon. Reproducibility is protected by a hard rule:
**Research only ever executes from a clean, committed Git state.**

---

## 2. Non-Goals (unchanged from v0.1, reaffirmed)

This proposal does **not**:

- migrate Production to Windows;
- support Windows-native Python execution;
- redesign the Production Engine;
- introduce distributed computing;
- modify application business logic;
- **(v0.2 clarification)** use any filesystem-sync tool (Syncthing/Dropbox/etc.) as a code or
  database transport.

---

## 3. Design Principles

| ID | Principle | Change vs v0.1 |
|----|-----------|----------------|
| P1 | Ubuntu is the only supported runtime. | unchanged |
| P2 | WSL2 Ubuntu is a compute node, **operationally distinct** from bare-metal Ubuntu (memory, filesystem, lifecycle) and configured accordingly. | **hardened** — v0.1's "just another Ubuntu machine" was overstated |
| P3 | Production and Research are operationally isolated (separate hardware, separate DB, separate env). | unchanged |
| P4 | Code moves only through **Git**. There is no second code-sync channel. | **changed** — Syncthing removed |
| P5 | Data moves only through an explicit **one-directional, WAL-safe snapshot** (Production → Research), consumed read-only. | **new / made explicit** |
| P6 | Git is the single source of truth — and therefore the single transport. | **strengthened** |
| P7 | Every machine owns its own venv **and its own `.env`/secrets**; neither is ever synchronized. | **extended to secrets** |
| P8 | Research executes only from a **clean, committed** Git working tree, so `research_runs` provenance is truthful. | **new** — protects Invariant #6 |
| P9 | Replication is not backup; disaster recovery builds on the existing backup + restore-drill, not on any sync mechanism. | **new / made explicit** |

---

## 4. Proposed Architecture

```
                      GitHub / Git remote (authoritative)
                                   │
                 git push/pull (over SSH)      git push/pull (over SSH)
                     ┌─────────────┴──────────────┐
                     │                            │
             Ubuntu Laptop                 Windows Desktop
              (PRODUCTION)                        │
        ┌───────────────────────┐          WSL2 Ubuntu (ext4)
        │ gunicorn (workers=1)  │           (RESEARCH node)
        │ APScheduler           │        ┌────────────────────┐
        │ Telegram poller       │        │ walkforward / bt   │
        │ live scanner          │        │ gatekeeper / regime│
        │ walkforward.db (WAL)  │        │ optimizer / CLI    │
        │ nightly db_backup     │        │ research snapshot  │
        └───────────┬───────────┘        │  (read-only)       │
                    │                    └─────────┬──────────┘
                    │   WAL-safe snapshot (online-backup API)
                    │   pulled on demand via rsync-over-SSH
                    └───────────────────────────────►
                        one-directional: PROD → RESEARCH
```

Key differences from the v0.1 diagram: **Syncthing is gone**; both machines attach to the Git
remote independently; the only Production→Research link is a pull-based data snapshot.

---

## 5. Architecture by Topic

Each subsection states **why it exists, what problem it solves, trade-offs, risks, and
alternatives considered**, per the review requirement.

### 5.1 Git vs Syncthing — code synchronization

**Decision:** Git-over-SSH is the sole code-movement mechanism. Syncthing is retired for this repo.

- **Why:** Git already provides versioned, conflict-explicit, branch-scoped synchronization between
  machines — the exact job Syncthing was assigned. Two mechanisms for the same files is two sources
  of truth.
- **Problem solved:** eliminates (a) `sync-conflict-*` files that can trip CI source-scanners
  (`test_architecture_boundary.py`, `test_secret_hygiene.py`) or be committed by accident; (b)
  `.git/` corruption risk from ever syncing the git directory; (c) the false-provenance failure in
  §5.3.
- **Trade-offs:** loses Syncthing's "ambient, no-command" convenience — a developer must
  `git commit`/`push`/`pull` deliberately. This is a feature here, not a cost.
- **Risks:** developer friction may tempt out-of-band file copying; mitigated by SSH being already
  configured between the machines and by P8 making "commit before you run" a standing rule.
- **Alternatives considered:** Syncthing code-only with `.git/`, secrets, and `data/` excluded
  (rejected — still permits false provenance per §5.3 and adds a daemon for no gain over Git);
  rsync-push of code (rejected — bypasses history/branching, the whole point of Git).

### 5.2 Repository synchronization & workflow

**Decision:** One logical repository, one clone per machine, moved by branch push/pull. No
duplicated repos, no shared mount.

- **Why:** preserves "one logical repository" (v0.1 P5) using Git's native model.
- **Problem solved:** each machine has a self-consistent `.git/` + working tree; no cross-machine
  working-tree races.
- **Trade-offs:** Research must pull before running and push results/commits it wants preserved;
  in-flight uncommitted edits do **not** magically appear on the other machine.
- **Risks:** branch drift between machines; mitigated by treating `master`/the active branch as the
  handoff and by CI parity (§5.9).
- **Alternatives considered:** shared network mount (rejected — SQLite/locking + latency); Syncthing
  (rejected, §5.1).

### 5.3 Research reproducibility

**Decision (P8):** Research jobs execute only from a **clean, committed** Git state. A dirty working
tree is a stop condition for a recorded experiment.

- **Why:** `research/tracking.py` records a git commit per run; Invariant #6 ("every experiment
  reproducible") requires *commit == the bytes that ran*. v0.1's Syncthing would move uncommitted
  changes between machines, so the recorded commit could silently fail to reproduce the executed
  code — provenance that is quietly false, which is worse than none in an institution whose top
  tie-breaker is reproducibility over speed.
- **Problem solved:** guarantees the `research_runs` ledger, dataset fingerprint, and git commit
  together actually reconstruct any experiment.
- **Trade-offs:** exploratory "just run it to see" iterations must either be run as explicitly
  untracked/throwaway or be committed first; slightly slower loop.
- **Risks:** a researcher runs a tracked job dirty anyway. This is a **documentary/process
  invariant** in v0.2 (like several research-governance invariants), not yet a code gate; hardening
  it into a runtime check is listed in Open Issues (OI-3).
- **Alternatives considered:** capture a working-tree diff/hash alongside the commit (partial
  mitigation, deferred — noted in Open Issues); do nothing (rejected — breaks Invariant #6).

### 5.4 SQLite snapshot strategy

**Decision (P5):** Production emits a **WAL-safe consistent snapshot** using the SQLite online-backup
API (the mechanism already present as `scripts.db_backup`). Research pulls the snapshot via
rsync-over-SSH and opens it **read-only**. Live `.db` / `-wal` / `-shm` files are never synced.

- **Why:** WAL-mode SQLite is three coupled files; replicating them independently while a checkpoint
  is in flight corrupts the database. The online-backup API produces a single transactionally
  consistent file safely while writers are active.
- **Problem solved:** removes the corruption vector of v0.1 (and of the *currently live* Syncthing
  config, which is replicating a 3.2 GB live WAL DB right now).
- **Trade-offs:** Research data is as fresh as the last snapshot, not real-time. For walk-forward /
  backtest workloads this is correct — research should run against a *settled, pinned* corpus, not a
  moving target.
- **Risks:** snapshot transfer of a multi-GB file is slow/costly if done naively; mitigated by
  rsync deltas and an explicit cadence rather than continuous copy.
- **Alternatives considered:** `VACUUM INTO` (acceptable variant of the same idea); file copy of the
  live DB (rejected — corruption); `rsync` of the raw `.db` while live (rejected — same); Litestream/
  streaming replication (deferred — over-engineered for a batch research feed).

### 5.5 Database architecture

**Decision:** Advance repository invariant **R-5 (physical DB split)** logically. Production remains
the single writer of `walkforward.db`. Research operates on a **read-only snapshot** of the settled
OHLCV corpus + `corporate_actions`, plus its **own** research-owned database for research-owned
tables.

- **Why:** the real repo has **one** `walkforward.db` with a **CI-enforced logical write-fence**
  (`test_research_data_fence.py`) separating research-owned tables (`wf_scores`, `wf_edge`,
  `backtest_cache`, `gate_decisions`, `gate_evidence`, `regime_profiles`,
  `regime_profile_cells`, `hypotheses`, `hypothesis_links`, `failure_registry`) from production
  tables. v0.1's invented peer files `production.db` / `research.db` did not match this; but the
  *intent* maps onto R-5, which CLAUDE.md/§5 records as **still open**.
- **Problem solved:** makes the logical fence physical across the machine boundary — Research
  literally cannot write Production tables because it holds a read-only input snapshot and a
  separate research DB.
- **Data-flow direction:** strictly **Production → Research**. Research *consumes* settled OHLCV +
  corporate actions (its fingerprinted input per `research/tracking.py`); it never feeds Production.
  Promotion back to Production remains the existing human-gated Edge Registry path, over Git — not a
  DB sync.
- **Trade-offs:** two DB files on the Research node (read-only input snapshot + writable research
  DB); slightly more moving parts than one file.
- **Risks:** the existing CI write-fence assumes a single DB; a physical split must not silently
  bypass or weaken it. Any code enabling a second DB path is out of scope here and must, when
  proposed, keep `test_research_data_fence.py` green. Flagged in Open Issues (OI-1).
- **Alternatives considered:** keep one shared DB accessed over the network (rejected — SQLite
  locking across machines); full client/server DB e.g. Postgres for research (deferred — large
  change, revisit only if snapshot size/throughput demands it).

### 5.6 Secrets management

**Decision (P7 extended):** `.env` and `.stockbit_token` are **excluded from every transport**,
provisioned per-machine, and held at **mode 600**. This is a v0.2 **precondition**, because the
current live Syncthing config violates it.

- **Why / live finding:** the review confirmed on disk that `.stignore` does **not** exclude
  `.env`, `.stockbit_token`, `data/*.db`, or `logs/`, and that `.env`/`.stockbit_token` are mode
  **644**. The repo's startup validation aborts on group/world-readable secrets and requires 600.
  The current setup can both **leak the Stockbit token** to a second machine and **break Production
  startup** if that machine ever becomes Production.
- **Problem solved:** contains secret exposure; keeps per-machine config authority with `config.py`.
- **Trade-offs:** each machine must be provisioned with its own secrets manually (no propagation).
  Correct for security; minor operational cost.
- **Risks:** a machine is provisioned with the wrong scope of key (e.g. Research holds a live
  Telegram/Stockbit token it shouldn't). Mitigated by §5.7 (Research runs with alerting/agent-firm
  off by default).
- **Alternatives considered:** encrypted secret sync (deferred — adds tooling; not needed for two
  machines); a secrets manager/vault (deferred — over-scoped for now).

### 5.7 Environment isolation

**Decision (P7):** Per-machine `venv/` (never synced), per-machine `.env` (never synced). Research
defaults to **agent-firm off, Telegram alerting off, `AUTH_MODE` as appropriate**, `DB_PATH`
pointing at the read-only snapshot / research DB. Production keeps live settings.

- **Why:** `config.py` is the single `.env` reader; the mode flags (`AUTH_MODE`, `SECTORS_APP_MODE`,
  `EDGE_SCORE_MODE`, `AGENT_FIRM_*`) legitimately differ between a live and a research box. Sharing
  env would cross live alerting/trading wires into research runs.
- **Problem solved:** prevents a research batch from emitting Telegram alerts, consuming the shared
  agent-firm 5-hour quota window, or touching live-only surfaces.
- **Trade-offs:** two config files to maintain; drift possible. Mitigated by keeping `.env.example`
  authoritative for *shape* (committed) while values stay per-machine.
- **Risks:** config drift causing "works on Research, not Production." Mitigated by CI parity (§5.9).
- **Alternatives considered:** one shared `.env` (rejected — §5.6/§5.7 reasons); env injected by an
  orchestrator (deferred).

### 5.8 WSL2 operational considerations

**Decision (P2 hardened):** Keep WSL2 as the Research host, but treat it as a tuned VM, not
bare-metal. Baseline requirements (architecture-level, not implementation):

1. **Memory** governed by a `.wslconfig` (bounded `memory=`, `processors=`, `swap=`). The OOM class
   of failure is **relocated, not eliminated** — under pressure the *guest* Linux OOM killer fires
   inside the VM, killing the research job rather than the desktop. This is an accepted, deliberate
   outcome.
2. **Filesystem:** repo and all DB files live on the **WSL2-native ext4 path** (e.g.
   `~/idx-walkforward-5001`), never under `/mnt/c`. SQLite over the `/mnt` 9P/DrvFs boundary is slow
   and has known locking/corruption behavior.
3. **Lifecycle:** systemd-in-WSL2 enabled so long-running research jobs survive; the Windows host
   configured not to sleep/hibernate during research runs; awareness that WSL2 halts when its last
   process exits.
4. **Clock:** WSL2 guest clock can skew from the host on resume; relevant because all timestamps are
   WIB and land in the provenance ledger. Time sync on resume is required.

- **Why:** these are the concrete ways WSL2 ≠ bare-metal Ubuntu for a memory-bound batch workload.
- **Problem solved:** prevents the "we moved OOM into an unbounded VM," slow-I/O, and
  job-dies-on-sleep failure modes.
- **Trade-offs:** WSL2 management overhead (the one disadvantage v0.1 already listed), now made
  explicit and bounded.
- **Risks:** operator forgets `.wslconfig`/sleep settings → contention returns inside the VM.
  Documented as a provisioning checklist item (out of scope to script here).
- **Alternatives considered:** a native second Ubuntu box / dual-boot (rejected in v0.1 —
  dual-boot can't run simultaneously; a dedicated Linux box is the cleanest but assumes hardware not
  on hand); cloud research runner (deferred — cost + data-egress of a multi-GB corpus).

### 5.9 Development workflow

**Decision:** The workflow is Git-mediated end to end:

```
edit (either machine) → git commit → git push
        → git pull (other machine) → (research: pull data snapshot) → run from clean state
        → commit results/artifacts intended to persist → push → human-gated promotion (Edge Registry)
```

- **Why:** matches P4/P6/P8; the promotion path back to Production is the existing Edge Registry
  handoff, over Git, human-gated — never an automatic sync.
- **Problem solved:** one deterministic path; no ambient movement of code or data.
- **Trade-offs / risks / alternatives:** as in §5.1–5.3.

### 5.10 Disaster recovery

**Decision (P9):** DR builds on the **existing** nightly `scripts.db_backup` (online-backup API,
WAL-safe, integrity-checked) + the **weekly restore drill** (`scripts.db_restore`) that already
defines "a good backup." No sync mechanism is part of DR.

- **Why:** a replication/sync tool propagates `rm`, truncation, and corruption **instantly** to the
  other node — it is replication, not backup. The repo already has a verified backup story.
- **Roles:** the Production laptop is the **system of record** for live-only tables (paper trades,
  `provider_events`, the `research_runs` ledger). Its loss is covered by restoring the latest
  *verified* backup onto replacement hardware. The Research node is near-stateless: reproducible
  from a committed Git commit + a re-pulled data snapshot; its loss costs only in-flight compute.
- **Trade-offs:** no instant failover; recovery = restore-from-backup, which is already drilled.
- **Risks:** backups not tested = no backups; mitigated by the *existing* restore drill remaining
  mandatory.
- **Alternatives considered:** Syncthing/replication as "backup" (explicitly rejected); a hot
  standby Production (deferred — out of scope, larger HA project).

### 5.11 Line endings & CI parity

**Decision:** Add a `.gitattributes` policy (`* text=auto`, `*.sh text eol=lf`) so shell scripts
(`start.sh`, `scripts/*.sh`) keep LF across the Windows/WSL2/Ubuntu boundary; state that CI parity
assumes the repo lives on **ext4 inside WSL2** (not `/mnt/c`) and that CPU-count differences can
affect any parallel-test behavior.

- **Why:** there is currently no `.gitattributes`; a Windows editor touching a `.sh` file can inject
  CRLF and break execution on Ubuntu.
- **Problem solved:** protects "both environments behave identically" (v0.1 CI expectation).
- **Note:** authoring `.gitattributes` is an implementation act and is therefore **out of scope for
  this document** — it is recorded here as a required v0.2 outcome and in the roadmap, not performed.

---

## 6. Architecture Decision Log (ADRs)

> Status legend: **Proposed** = awaiting the independent re-review this document is written for.

**ADR-001 — Separate Production and Research onto different physical machines**
- **Decision:** Production stays on the Ubuntu laptop; Research moves to WSL2 Ubuntu on the Windows
  desktop.
- **Status:** Proposed.
- **Alternatives:** single laptop (rejected — contention/OOM); dedicated Linux box (deferred — no
  hardware on hand); cloud (deferred — cost/egress).
- **Rationale:** physical separation is what actually resolves the OOM/contention problem; it is
  independent of the sync mechanism.

**ADR-002 — Retire Syncthing; Git-over-SSH is the sole code transport**
- **Decision:** Remove Syncthing from the architecture for this repo. Code moves only via Git.
- **Status:** Proposed (supersedes the v0.1 Syncthing design).
- **Alternatives:** Syncthing code-only with exclusions (rejected — false provenance, added daemon
  for no gain); rsync of code (rejected — no history/branching).
- **Rationale:** Git already performs cross-machine code sync with history, branching, and explicit
  conflicts; a second channel is a second source of truth.

**ADR-003 — Research executes only from a clean, committed Git state**
- **Decision:** A tracked research run requires a clean working tree at a known commit.
- **Status:** Proposed (documentary invariant; runtime enforcement deferred — OI-3).
- **Alternatives:** record a working-tree diff alongside the commit (deferred); no rule (rejected —
  breaks Invariant #6).
- **Rationale:** makes `research_runs` provenance truthful; protects reproducibility Invariant #6.

**ADR-004 — Production→Research data via WAL-safe read-only snapshot**
- **Decision:** Ship a consistent snapshot (online-backup API / `VACUUM INTO`), pulled by rsync-
  over-SSH, opened read-only by Research.
- **Status:** Proposed.
- **Alternatives:** live-file copy/rsync of a WAL DB (rejected — corruption); streaming replication
  (deferred — over-engineered).
- **Rationale:** WAL-mode DBs cannot be safely copied file-wise while live; research should run on a
  settled, pinned corpus anyway.

**ADR-005 — Advance R-5 (physical DB split), preserving the CI write-fence**
- **Decision:** Research holds a read-only input snapshot + a separate writable research DB;
  Production remains the sole writer of `walkforward.db`.
- **Status:** Proposed (touches an open invariant; must keep `test_research_data_fence.py` green —
  OI-1).
- **Alternatives:** one shared DB over the network (rejected — locking); Postgres for research
  (deferred).
- **Rationale:** makes the existing logical write-fence physical across the machine boundary.

**ADR-006 — Secrets excluded from all transport, per-machine, mode 600**
- **Decision:** `.env`/`.stockbit_token` never synced; provisioned per machine at 600.
- **Status:** Proposed — **and an immediate remediation** of the live exposure (§7).
- **Alternatives:** encrypted secret sync / vault (deferred).
- **Rationale:** current config leaks secrets and violates the repo's 600 startup requirement.

**ADR-007 — Per-machine environment isolation**
- **Decision:** Separate venv and `.env` per machine; Research defaults alerting/agent-firm off.
- **Status:** Proposed.
- **Alternatives:** shared env (rejected); orchestrated env injection (deferred).
- **Rationale:** prevents research runs from firing live alerts or consuming shared agent-firm quota.

**ADR-008 — WSL2 operational baseline (bounded memory, ext4, systemd, no-sleep, clock sync)**
- **Decision:** Treat WSL2 as a tuned VM per §5.8.
- **Status:** Proposed.
- **Alternatives:** native/dedicated Linux box (deferred); dual-boot (rejected).
- **Rationale:** WSL2 ≠ bare-metal for memory-bound batch work; unbounded WSL2 recreates the OOM
  problem inside a VM.

**ADR-009 — DR builds on existing backup + restore drill; replication ≠ backup**
- **Decision:** Keep nightly online backup + weekly restore drill as the DR spine; no sync in DR.
- **Status:** Proposed.
- **Alternatives:** treat sync as backup (rejected); hot standby (deferred).
- **Rationale:** sync propagates deletion/corruption instantly; the repo already has a verified
  backup story.

**ADR-010 — Line-ending and CI-parity discipline**
- **Decision:** Adopt `.gitattributes` LF policy for `.sh`; pin ext4-native repo location for CI
  parity.
- **Status:** Proposed (authoring the file is implementation — out of scope here).
- **Alternatives:** rely on editor config (rejected — not enforced).
- **Rationale:** prevents CRLF breakage of shell scripts across the OS boundary.

---

## 7. Immediate Remediation (precondition, not implementation)

The review found a **live exposure** that predates and is independent of this proposal. It is called
out here because v0.2 should not be reviewed as purely future-facing while the risk is active. These
are decisions/preconditions; the actual edits are implementation and are **not performed in this
document**:

1. The currently running Syncthing folder on `D:\IDX` is replicating **secrets** (`.env`,
   `.stockbit_token`, mode 644) and a **3.2 GB live WAL database** (`data/walkforward.db` +
   `-wal`/`-shm`). Both must stop before any further build-out.
2. Until Syncthing is retired (ADR-002), at minimum its ignore policy must exclude `.env`,
   `.stockbit_token`, `data/`, and `logs/`, and the secret files must be corrected to mode 600.

This section is a **finding + required precondition**, deliberately stated without commands or
scripts.

---

## 8. Review Resolution Matrix

| # | Review Finding | Decision | Reason | Action Taken in v0.2 |
|---|----------------|----------|--------|----------------------|
| 1 | Syncthing already syncing secrets + 3.2 GB live WAL DB (live exposure) | **Accept** | Confirmed on disk: `.stignore` omits `.env`/`.stockbit_token`/`data/`; secrets at 644; DB 3.2 GB with live WAL. Real corruption + leak risk. | §7 Immediate Remediation; ADR-006; P7 extended to secrets. |
| 2 | Syncthing over a Git working tree breaks reproducibility (Invariant #6) | **Accept** | Moving uncommitted changes makes recorded git commit ≠ executed code; provenance becomes silently false. | P8; ADR-003; §5.3. Runtime enforcement deferred to OI-3. |
| 3 | Git already is the cross-machine code sync; Syncthing adds risk for no gain | **Accept** | Git provides versioned, branch-scoped, conflict-explicit sync over already-configured SSH. | ADR-002; P4/P6; §5.1–5.2. Syncthing removed. |
| 4 | DB model wrong (one file + write-fence, not peer DBs); flow is one-directional; touches R-5 | **Accept** | Repo has one `walkforward.db` + CI write-fence; R-5 (physical split) is on record as open; research consumes settled OHLCV one-way. | ADR-004/005; §5.4–5.5. Peer-DB framing replaced; R-5 named. |
| 5 | WSL2 is not "just another Ubuntu machine" for a memory-bound workload | **Partially Accept** | Correct that memory/filesystem/lifecycle differ and OOM only relocates; but WSL2 remains a valid, low-cost host given hardware on hand — so keep it *with constraints* rather than abandon it. | P2 hardened; ADR-008; §5.8 baseline (memory bound, ext4, systemd, no-sleep, clock). |
| 6 | Syncthing is replication, not backup; DR under-specified | **Accept** | Sync propagates deletion/corruption instantly; repo already has online backup + weekly restore drill. | ADR-009; P9; §5.10. |
| 7 | Secrets omission in v0.1 exclude-list; must be per-machine + 600 | **Accept** | Startup aborts on group/world-readable secrets; sync breaks perms across OS boundary. | ADR-006; §5.6; §7. |
| 8 | Missing `.gitattributes`/line-ending discipline across OS boundary | **Accept** | No `.gitattributes` today; CRLF can break `start.sh`/`scripts/*.sh` on Ubuntu. | ADR-010; §5.11. (Authoring the file is implementation — out of scope.) |
| 9 | CI parity caveats (ext4 not `/mnt/c`, CPU count) | **Accept** | Filesystem/CPU differences can change test behavior. | §5.8/§5.11 pin ext4-native repo location. |
| 10 | Recommended alternative: Git-over-SSH + snapshot; drop Syncthing | **Accept** | It meets G1–G8, removes the entire Syncthing failure class, and reuses existing repo primitives (SSH, online backup, dataset fingerprint, write-fence). | Adopted as the v0.2 baseline architecture (§4–5). |

No findings were rejected. One (#5) is Partially Accepted: the *critique* of WSL2 is accepted in
full, but the *implication* to abandon WSL2 is not — WSL2 is retained with the §5.8 constraints
because the hardware and Ubuntu-only goal make it the lowest-complexity option available now.

---

## 9. Open Issues (unresolved architectural questions)

- **OI-1 — Physical DB split vs the CI write-fence.** `test_research_data_fence.py` presumes a
  single DB. How does a two-DB (read-only input snapshot + writable research DB) topology keep that
  test meaningful and green? Requires a design that the fence explicitly understands. *(Blocks any
  R-5 implementation.)*
- **OI-2 — Snapshot cadence & size.** At 3.2 GB and growing daily, what is the right snapshot
  frequency, retention, and transfer method (rsync delta vs periodic full)? What is the acceptable
  staleness for research inputs?
- **OI-3 — Enforcing "clean committed state" (P8).** Should this stay a documentary invariant or
  become a runtime guard in the research entry points (refuse to record a run from a dirty tree)?
  If a guard, where does it live without breaching the research/production boundary?
- **OI-4 — Untracked exploratory runs.** How are throwaway/exploratory research runs marked so they
  are clearly *not* part of the append-only `research_runs` evidence ledger?
- **OI-5 — Promotion path unchanged?** Confirm that Research→Production promotion remains solely the
  human-gated Edge Registry over Git, with no new data channel introduced by this split.
- **OI-6 — Secrets provisioning method.** Manual per-machine provisioning is assumed; is an
  encrypted-at-rest mechanism or vault warranted later, or is manual sufficient for two machines?
- **OI-7 — WSL2 host reliability.** Is a sleep-prone desktop acceptable for multi-hour research
  jobs, or does this argue for a dedicated always-on Linux box as the eventual target (ADR-001
  alternative)?
- **OI-8 — Governance placement.** Does this infrastructure architecture need an entry in
  `docs/roadmap/DECISION_LOG.md` (it advances R-5), and should it be reconciled against
  `docs/RESEARCH_MASTER_PLAN.md` §5 invariants formally?

---

## 10. Implementation Roadmap (high-level phases only — no steps)

> Phases are ordering guidance for a *future* implementation effort. This document authorizes none
> of them.

- **Phase 0 — Contain the live exposure.** Stop secrets and the live DB from syncing; correct secret
  permissions. (Precondition; §7.)
- **Phase 1 — Establish Git-over-SSH as the sole code path.** Retire Syncthing for this repo; confirm
  branch-based workflow between machines.
- **Phase 2 — Stand up the WSL2 Research node to the §5.8 baseline.** Bounded memory, ext4-native
  repo, systemd, no-sleep host, clock sync, independent venv + per-machine `.env`.
- **Phase 3 — Define and operate the Production→Research snapshot.** WAL-safe snapshot emission +
  read-only consumption; settle OI-2 (cadence/size).
- **Phase 4 — Advance R-5 physical DB split.** Only after OI-1 is resolved and the write-fence test
  is proven to remain meaningful.
- **Phase 5 — Reproducibility hardening.** Resolve OI-3/OI-4 (clean-state enforcement, untracked-run
  marking).
- **Phase 6 — Governance close-out.** Record the decision where governance requires it (OI-8);
  re-run the independent review against the operating system as built.

---

## 11. Traceability to Original Goals

| Goal (v0.1) | Met in v0.2? | How |
|---|---|---|
| G1 Separate Production/Research | Yes | Different physical machines (ADR-001). |
| G2 Ubuntu-only runtime | Yes | P1; WSL2 Ubuntu only (ADR-008). |
| G3 Avoid multiple OS targets | Yes | No Windows-native Python; Ubuntu semantics both sides. |
| G4 Use Windows hardware w/o Windows Python | Yes | WSL2 hosts Ubuntu. |
| G5 Single logical workflow | Yes | Git-mediated end to end (§5.9). |
| G6 Claude Code + z.ai on one repo | Yes | Same Git repo, branch-scoped — without a shared synced mount. |
| G7 Reduce Production contention | Yes | Research load leaves the Production laptop entirely. |
| G8 Long-term scalability | Partially | Research scales on separate hardware now; larger scale → OI-7 (dedicated/always-on node) and OI-2 (snapshot at scale). |

---

*End of v0.2. This document is for independent re-review. No implementation, scripts, or source
changes are authorized by it.*
