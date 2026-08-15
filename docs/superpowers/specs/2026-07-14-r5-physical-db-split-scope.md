# R-5 — Physical Research/Production DB Split — Scoping Note

**Date:** 2026-07-14 · **Branch:** ops/hardening-2026-07-10 · **Status:** SCOPING (pre-plan)
**Mandate:** Master Plan v3 §3.3c + Invariant #1 — R-5 elevated from "KEEP OPEN" to a
**hard, blocking prerequisite of Phase F**. Stated goal: *"discovery-volume writes never
contend with the production reader set."*

---

## 1. Current state

One physical DB, `data/walkforward.db` (61 tables), single-writer SQLite (WAL +
30s busy_timeout). All code — production and research — opens it through
`data.db.connect()`. The recurring documented failure mode is write-lock contention.

The write **fence** (`tests/test_research_data_fence.py`) already declares 10
`RESEARCH_TABLES`, but it is a *static code-path check*, not a physical boundary:
research and production still share one file and one writer.

## 2. The tables split into two tiers by their reader/writer graph

| Tier | Tables | Written by | Read by | Volume |
|---|---|---|---|---|
| **1 — pure discovery** | `gate_decisions`, `gate_evidence`, `regime_profiles`, `regime_profile_cells`, `hypotheses`, `hypothesis_links`, `failure_registry`, `research_runs` | research only | **research only** | high-churn (sweep exhaust) — the exact set §3.3c targets |
| **2 — shared contract** | `wf_scores`, `wf_edge`, `backtest_cache` | research **and** production (`engine/wf_edge.py`, `routes/backtest.py`) | production live path (`agent_firm/firm.py`, `scanner.py`, `screener.py`, `routes/backtest.py`, `liquidity.py`, `watchlist.py`, `paper_trade.py`, `edge_enrich.py`) **and** research | bounded (nightly WF job: ~13k/3.8k/33k rows) |

**Tier 1 is only ever touched by research code** → it moves cleanly.
**Tier 2 is the live research↔production interface** → moving it breaks the app
unless the ~9 production reader sites (and 2 cross-boundary writer sites) are first
retired behind a published edge interface. This is the long-deferred "reader
retirements" prerequisite recorded in the Research/Production Separation memory
(M1–M4 done; *"deferred: reader retirements then physical DB split"*).

## 3. Key insight — Tier 1 alone satisfies the Phase F mandate

§3.3c's goal is that **discovery-volume writes** stop contending with the production
reader set. The discovery-volume writes *are* the Tier-1 sweep exhaust (gate
decisions, regime profiles, hypotheses, failure rows). `wf_scores`/`wf_edge` are
bounded nightly-job outputs, **not** sweep volume, and they are the *interface*, not
the churn. Therefore:

> **Moving Tier 1 to a separate physical DB removes the discovery-write contention
> that blocks Phase F. Tier 2 is a separate "edge interface" workstream that does
> NOT block Phase F.**

## 4. Proposed R-5 = Tier 1 physical split (recommended)

1. **New file** `data/research.db` + `RESEARCH_DB_PATH` env (default alongside
   `walkforward.db`). WAL, same connect hardening.
2. **Seam** `research/db.py::connect_research()` — opens `research.db` (main schema)
   and `ATTACH`es `walkforward.db` **read-only** as `prod` for the production reads
   research still needs (`ohlcv`, `corporate_actions`, `idx_tickers` — 9 sites).
   Writes only ever hit the main (research) schema; append-only invariant preserved.
3. **Migrate** the 8 Tier-1 schemas + rows into `research.db` (gate 5+40, regime,
   `research_runs` 15, hypotheses/links/failure), verify counts, then **drop** them
   from `walkforward.db` (a true split, not a shadow copy).
4. **Rewire** research connect points — `research/tracking.py`, `gatekeeper/*`,
   `regime/*`, `knowledge/*` — to `connect_research()`; their `ohlcv` reads go via
   `prod.ohlcv`.
5. **Strengthen the fence** — Tier-1 tables must exist *only* in `research.db`;
   production code must never open `RESEARCH_DB_PATH`. Migrate the existing
   static-fence assertions to the new physical boundary.
6. **Ops** — backup/restore drill + cron must cover the second file.

**Risk:** contained. Tier-1 tables have no production readers, so the live app is
untouched. Main work is the `connect_research()` seam + ATTACH plumbing + migration
+ fence update. TDD-friendly (migration idempotency, ATTACH read-only enforcement,
fence meta-test).

## 5. Deferred to a separate item (NOT a Phase F blocker) — Tier 2 edge interface

Retire the ~9 production readers of `wf_scores`/`wf_edge`/`backtest_cache` behind a
promoted, read-only edge interface (edge registry artifact), then physically move
Tier 2 too. Larger, touches the live selection path, and is the M-series "reader
retirement" work. Scope separately after R-5.

## 6. Decision (owner, 2026-07-14) — RESOLVED

**R-5 = Tier 1 only.** Physically split the 8 pure-discovery tables into
`research.db` via the `connect_research()` + ATTACH-prod-read-only seam (§4). The
Tier-2 edge interface (§5) is deferred as a separate, non-blocking item. This is the
minimal split that satisfies the Phase F prerequisite (§3). Next: write the
implementation plan (TDD, phased: seam → migration → rewire → fence → ops).

**2026-08-15 update:** the implementation plan
(`docs/superpowers/plans/2026-07-21-r5-tier1-physical-db-split.md`, Tasks 1-10) is
code-complete and committed — `connect_research()` seam, verified migration,
opt-in-split rewiring of `tracking.track_run`/`gatekeeper.run_gate`/`regime.cli`/
`knowledge.cli`/`research.jobs`'s cron callers, the physical fence test, and the
manual `scripts/migrate_r5_tier1.py` cutover runbook (dry-run by default) are all in
place and test-covered. **The live `--apply` cutover against the real
`data/walkforward.db` has NOT been run** — the 8 Tier-1 tables still physically live
in `walkforward.db` on this checkout as of this note. Per this document's own §6 and
the plan's post-plan note, `docs/RESEARCH_MASTER_PLAN.md` R-5/Phase F status stays
open until that cutover actually runs and the Task 10 Step 5 verification checklist
passes — that will be a separate, explicit, dated update, not folded into this one.
