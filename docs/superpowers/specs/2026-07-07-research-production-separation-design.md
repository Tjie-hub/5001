# Research / Production Separation — Architecture Design Spec

**Date:** 2026-07-07
**Role:** Principal Quant Systems Architect brief — architectural refactor only
**Governing constraint:** **extract-not-rewrite** — move research out; production modules, imports, and behavior stay untouched except the one arrow inversion (§4).
**Status:** design approved by user (with Approval Manifest + Compatibility additions), pending spec review

---

## 0. The core inversion

Today's structural defect in one line: `_edge_selectable` (scheduler/scanner.py) reads
`wf_edge` — a research output — **live at scan time**. Research writes directly into the
production decision path; there is no promotion step.

```
TODAY:   research jobs ──write──▶ wf_edge ◀──read live── production selector
TARGET:  research ──evidence──▶ [PROMOTION = git commit] ──▶ registry/ ◀──read at startup── production
```

Everything in this document is packaging around inverting that one arrow.

Design principle (from the brief): *Research is allowed to fail. Production is not.
Research creates strategies. Production only executes approved strategies.*

---

## 1. High-level architecture

```
┌─────────────────────────── RESEARCH PLATFORM (batch, no daemon) ──────────────────────────┐
│  hypotheses → prototypes → backtest → walk-forward → robustness (split-half/per-ticker/   │
│  non-overlap) → OOS protocol (nr7_study thresholds) → candidate                            │
│  modules: research/walkforward_multi, nr7_study, regime_edge_scan, optimizer,             │
│           backtest_roller, portfolio_backtest, fastmover_study, studies/                  │
│  store:   research.db (wf_scores, wf_edge, backtest_cache)  — production never reads it   │
└───────────────────────────────┬────────────────────────────────────────────────────────────┘
                                │ candidate + evidence
                                ▼
                 ╔══════════ PROMOTION (explicit git commit / PR) ══════════╗
                 ║  registry/edge_registry.yaml   (immutable versioned)     ║
                 ║  registry/manifests/<ID>_v<N>.yaml  (approval manifest)  ║
                 ║  registry/artifacts/<ID>_v<N>_*.json (frozen universe…)  ║
                 ╚═══════════════════════════╤═══════════════════════════════╝
                                             │ read ONCE at startup, schema+compat validated
                                             ▼
┌─────────────────────────── PRODUCTION ENGINE (deterministic daemon, :5001) ────────────────┐
│  load approved registry → generate signals (checkers) → regime gate → flow gate →          │
│  edge veto → agent firm → risk/sizing → SHADOW harness (ft_*) / paper / live →             │
│  monitoring, heartbeat, fail-open alarms, audit trail                                      │
│  NEVER: walk-forward, expectancy calc, ranking, parameter search                           │
└───────────────────────────────┬────────────────────────────────────────────────────────────┘
                                │ shadow ledger (ft_*) + trade outcomes
                                └───────────▶ read by RESEARCH as promotion/decay evidence

┌─────────────────────────── DATA PLATFORM (shared floor, write-once) ───────────────────────┐
│  data/ — ohlcv (5y raw, is_final), stockbit flow bars, trading calendar, reconcile,        │
│  corporate actions, token mgmt. ONLY data/ writes market data; both sides read.            │
│  Shared libraries: engine/strategies (definitions), engine/exits (ONE kernel — parity      │
│  is a Phase-1B invariant), engine/regime_filter, data/db.connect.                          │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Folder / project structure (monorepo, enforced boundaries)

Production stays where it is; research is what moves.

```
idx-walkforward-5001/
├─ app.py, start.sh                 # production entrypoint (UNCHANGED)
├─ scheduler/                       # production jobs ONLY (research jobs removed in M3)
├─ engine/                          # production engine + SHARED libs:
│   ├─ strategies.py                #   shared: strategy definitions (both sides import)
│   ├─ exits/                       #   shared: THE one exit kernel (parity invariant)
│   ├─ regime_filter.py             #   shared: regime model
│   ├─ registry_loader.py           #   NEW (production): parse+validate registry at startup
│   └─ … (checkers, agent_firm, liquidity, heartbeat, fail_open_alarm — production)
├─ monitor.py, paper_trade.py       # production execution (UNCHANGED)
├─ forward_testing/                 # SHADOW validation harness (production-side, registry-driven)
├─ data/                            # data platform (shared; already centralized by Phase 3C)
├─ research/                        # NEW — moved: walkforward_multi, nr7_study, optimizer,
│   │                               #   backtest_roller, portfolio_backtest, fastmover_study,
│   ├─ studies/                     #   regime_edge_scan + one-off study scripts
│   └─ cli.py                       #   batch entrypoints (cron-able); NO daemon
├─ registry/
│   ├─ edge_registry.yaml           # the ONLY research→production interface
│   ├─ manifests/                   # approval manifests, one per promoted version
│   ├─ artifacts/                   # frozen universe snapshots, wf outputs, config hashes
│   └─ SCHEMA.md                    # registry + manifest field contract
└─ tests/
    └─ test_architecture_boundary.py  # CI guard (pattern proven by Phase-3C hygiene test)
```

**Boundary rules (CI-enforced, the guard test):**
1. No module outside `research/` may import `research/`.
2. `research/` may never import execution modules (`scheduler`, `monitor`, `paper_trade`, `forward_testing`, `app`).
3. Both sides may import the shared floor: `data/`, `engine/strategies`, `engine/exits`, `engine/regime_filter`.
4. Production may not open `research.db`; research may not write `walkforward.db` production tables (enforced by review + the DB split in M4).

---

## 3. Component responsibilities

| Component | Owns | Must never |
|---|---|---|
| **Production engine** | registry load+validation, signal generation from APPROVED/SHADOW strategies, regime/flow/agent gates, risk & sizing, paper/live execution, SHADOW harness, monitoring/heartbeat/alarms, audit log | compute expectancy, rank strategies, run walk-forward, search parameters, read research.db |
| **Research platform** | hypothesis studies, backtests, walk-forward, robustness kit (split-half, per-ticker, non-overlapping windows), OOS protocol, decay monitoring, candidate assembly (registry entry + manifest + artifacts) | trade, write production tables, hold scheduler slots, import execution code |
| **Registry** | the promotion contract: what is approved, at which version, for which regimes/universe, compatible with what | contain mutable state; be written by any process (humans/PRs only) |
| **Data platform** | market data acquisition, corpus integrity (calendar, reconcile, is_final), token lifecycle | strategy logic of any kind |
| **Shared libs** (`engine/strategies`, `engine/exits`, `engine/regime_filter`) | single definitions used identically by backtest and execution — the Phase-1 parity guarantee | diverge per side (no research-only forks of the kernel) |

---

## 4. Data flow

```
 data/ (scraper 16:15 EOD authority, yfinance reconcile, flow 20:15)
   │ writes ohlcv / flow / calendar
   ├────────────────────────────► research/  (reads corpus; writes research.db ONLY)
   │                                  │
   │                                  │ candidate: registry entry + manifest + artifacts
   │                                  ▼
   │                          PROMOTION COMMIT (PR + CI)
   │                                  │
   ▼                                  ▼
 production engine ◄──── registry_loader (startup: schema check → compat check → freeze)
   │  signals → gates → SHADOW(ft_*) / paper / live
   │
   ├── ft_* shadow ledger ────────► research/ (reads as SHADOW-stage evidence + decay watch)
   └── trade audit trail ─────────► research/ (reads for realized-vs-expected analysis)
```

Read/write matrix: production **reads** registry + market data, **writes** its own state
(signals, trades, ft_*). Research **reads** market data + production ledgers, **writes**
research.db + promotion PRs. Nothing else crosses.

---

## 5. Promotion workflow (pipeline → mechanics)

```
Idea → Prototype → Backtest → Walk-Forward → Robustness → OOS protocol
     → CANDIDATE (registry entry drafted, status: CANDIDATE — production ignores)
     → SHADOW    (promotion commit #1: production generates+ft-tracks, NEVER trades)
     → [shadow period: realized ledger vs backtest expectancy, read by research]
     → APPROVED  (promotion commit #2: eligible for paper/live execution)
     → SUSPENDED / RETIRED / SUPERSEDED (kill-switch or lifecycle end)
```

Every arrow after CANDIDATE is an **explicit git commit** (PR + CI + manual merge — the
repo's existing workflow). No automatic promotion, no exceptions. The SHADOW stage runs on
production rails under registry control (status drives the harness), reusing the existing
`ft_*` engine unchanged — this reuses the codebase's proven shadow/enforce idiom.

---

## 6. Edge Registry specification

`registry/edge_registry.yaml` — list of immutable versioned entries:

```yaml
- id: NR7_BULL
  version: 1
  status: APPROVED            # CANDIDATE|SHADOW|APPROVED|SUSPENDED|RETIRED|SUPERSEDED
  strategy_fn: "NR7 Breakout"           # key into STRATEGY_FUNCS / checker dispatch
  regimes: [BULL_MODERATE, BULL_STRONG]
  universe_artifact: artifacts/NR7_BULL_v1_tickers.json   # FROZEN at approval (replaces
                                                          # live wf_edge reads — the inversion)
  risk_category: breakout-long
  owner: tjie
  approved: 2026-07-04
  manifest: manifests/NR7_BULL_v1.yaml
  requires:                   # COMPATIBILITY (user addition #2)
    data_schema: 1            # post-2A raw-basis corpus
    exit_kernel: 1            # post-1B unified kernel semantics
    regime_model: 1           # detect_regime BULL/BEAR/SIDEWAYS + ADX sub-band
    engine_version: 1         # post-Phase-3 engine
  changelog: "v1 — initial approval after Phase-2 recompute + generalization study"
```

**Compatibility mechanics.** Production advertises its own versions as constants
(`ENGINE_VERSIONS = {data_schema, exit_kernel, regime_model, engine_version}`), bumped
whenever semantics change (e.g., a 1B-style kernel change ⇒ `exit_kernel: 2`). At startup
the loader compares each entry's `requires` with the engine's versions:
- **Incompatible entry → NOT loaded + fail-open alarm** (Telegram + log, per-strategy
  fail-closed; the engine continues with the remaining compatible strategies).
- This *automates* the Phases-1/2 lesson: an approval is only valid for the semantics it
  was validated on. A kernel bump mechanically invalidates stale approvals and forces
  re-validation — no more silently-stale wf_scores.

**Approval Manifest** (user addition #1) — `registry/manifests/NR7_BULL_v1.yaml`,
committed atomically with the promotion, immutable:

```yaml
approval:
  strategy: NR7_BULL
  version: 1
  approved_by: tjie            # future: Research Committee
  approval_date: 2026-07-04
  decision: "APPROVED for BULL regimes only — see report"
artifacts:
  walkforward: artifacts/NR7_BULL_v1_wf.json          # the WF/OOS numbers as-of approval
  universe: artifacts/NR7_BULL_v1_tickers.json         # frozen ticker set
  report: docs/superpowers/results/2026-07-07-nr7-generalization-study.md
  config_hash: <sha256 of strategy params + thresholds at approval>
  code_commit: <repo SHA of the research run>
  corpus_snapshot: {as_of: 2026-07-07, ohlcv_rows: 1041262, is_final_only: true}
evidence_summary:
  oos: {exp_net_pct: 1.18, n_trades: 346, win_pct: 54.0, windows: 16}
  robustness: {split_half: pass, per_ticker: pass, non_overlap: n/a}
  shadow: {from: 2026-07-04, trades: 0, verdict: pending}
```

Six months later, "why was NR7_v1 approved?" is answered by opening one file whose every
referenced artifact is pinned in git.

---

## 7. Versioning policy

- An `(id, version)` pair is **immutable once its status leaves CANDIDATE**. Any change —
  parameters, universe, regimes, thresholds — is a **new version** (`NR7_BULL v2`) with its
  own manifest; the old version's status → `SUPERSEDED`.
- Production **pins exact versions**; it never auto-upgrades. Moving live from v1→v2 is
  itself a promotion commit.
- Engine-side `ENGINE_VERSIONS` constants follow the same discipline: bump on any semantic
  change to corpus schema, exit kernel, regime model, or engine contract; the bump's PR
  must state which registry entries it invalidates.
- Strategy IDs are `<FAMILY>_<REGIME-SCOPE>` (`NR7_BULL`), stable across versions.

---

## 8. Deployment workflow

1. Research completes the pipeline; assembles entry + manifest + artifacts.
2. **Promotion PR**: registry diff only. CI runs (a) registry schema validation,
   (b) compatibility check against current `ENGINE_VERSIONS`, (c) boundary test,
   (d) full suite.
3. Manual merge (repo disallows auto-merge — existing policy).
4. Prod checkout pulls; **restart in a quiet slot** (existing deploy idiom).
5. Startup: loader logs + Telegrams the loaded state —
   `registry @<git-hash>: N approved, M shadow, K skipped-incompatible`. The audit trail
   records exactly which registry hash every trading day ran on.

## 9. Rollback workflow

- **Rollback = `git revert` of the promotion commit + restart.** No data surgery.
- Open positions under a reverted/suspended strategy: **manage-to-exit** — no new entries;
  existing positions run their registered exit policy to completion (never orphaned,
  never force-closed by rollback itself).
- Emergency kill (market event): commit `status: SUSPENDED` (single-line change) +
  restart; same manage-to-exit semantics. Both paths leave a git-native audit record.

---

## 10. Migration plan (strangler — each phase independently shippable, suite green, prod behavior identical)

| Phase | Content | Proof of no behavior change |
|---|---|---|
| **M1 — the inversion** | Create `registry/` with `NR7_BULL v1` capturing today's exact live config (frozen ticker artifact = current `wf_edge>0` set; manifest referencing the existing study; `requires` seeded at all-1s). Add `engine/registry_loader.py` + `ENGINE_VERSIONS`. Switch the selector's NR7 path from live `wf_edge` reads to the frozen artifact. | Freeze == current DB state ⇒ selector output byte-identical; conformance + full suite green; startup banner shows the same one approved strategy. |
| **M2 — move research out** | `git mv` research modules → `research/`; fix their imports; add `tests/test_architecture_boundary.py` to CI. Production files untouched except deleted imports of moved modules (which only research jobs used). | Full suite + boundary test green; production deployable identical. |
| **M3 — scheduler purge** | Remove `refresh_wf_scores` (Fri 16:00) + `backtest_roller` from APScheduler; expose as `research/cli.py` batch commands (cron-able, run manually post-M1 since their output no longer feeds production live). | Scheduler job list diff shows only research jobs removed; heartbeat/monitors unchanged. |
| **M4 — DB split** | **AMENDED 2026-07-08 → M4-lite** (see `specs/2026-07-08-m4-lite-write-fence-design.md`): grounding found ~10 production readers, so the physical move would rewrite the trade path. Implemented instead: write-fence CI test (only `research/` writes `wf_scores`/`wf_edge`/`backtest_cache`; DAO exception `engine/wf_edge.py`). Physical split deferred until each reader is individually retired. | Fence test green + teeth-verified; contract documented in `registry/SCHEMA.md`; suite green. |
| **M5 (deferred)** | Repo split when scale demands (>1 operator, >1 asset class). Layout makes it `git filter-repo` mechanical. | n/a — explicitly out of scope now. |

**Sequencing rationale:** M1 alone delivers ~80% of the institutional value (promotion
gate + audit + reproducibility) with the smallest diff; M2–M4 are hygiene that hardens it.
At every phase the production engine keeps all Phase 1–3 guarantees (parity kernel, cost
authority, fail-open alarms, heartbeat, DB lock hardening).

## Out of scope (explicitly)

- Any rewrite of scanner/monitor/paper/exits logic; any strategy or threshold change.
- New research features (Monte Carlo etc. are future research-platform work, not this refactor).
- Multi-asset/multi-exchange abstractions — the layout supports them later; nothing is built now (YAGNI).
- Repo split (M5 deferred).
