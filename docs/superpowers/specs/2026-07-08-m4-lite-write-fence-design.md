# M4-lite — Research-Data Write Fence Design Spec

**Date:** 2026-07-08
**Status:** design approved (amends §10-M4 of
`docs/superpowers/specs/2026-07-07-research-production-separation-design.md`)

## Why the spec's M4 was amended

The original M4 ("move `wf_scores`/`wf_edge`/`backtest_cache` → `research.db`") assumed
production no longer references those tables after M1. Grounding (2026-07-08) found
**~10 production modules read them at runtime**: the scan-loop consistency blacklist
(`wf_scores`), the ungoverned selector path + trade_plan + edge-veto shadow (`wf_edge`),
the AutoTrade quality gate + liquidity/watchlist/strategy_specs (`backtest_cache`),
agent-firm context, and dashboards. A physical split therefore means rewriting the trade
path — exactly what the governing extract-not-rewrite constraint forbids.

**Decision (user, 2026-07-08): M4-lite.** The tables stay in `walkforward.db` but become
formal **research data products**: research writes, production reads, CI enforces the
write side. This completes the separation of *authority* — decisions come from the
registry (M1), code is boundary-clean (M2/M3), writes are fenced (M4) — while deferring
physical storage separation until each reader is individually retired.

## The contract

| Table | Writes | Reads |
|---|---|---|
| `wf_scores` | `research/` only (wf-refresh CLI) | production gates/context/dashboards (unchanged) |
| `wf_edge` | `research/` only, via the DAO `engine/wf_edge.py::save_wf_edge` | production (unchanged) |
| `backtest_cache` | `research/` only (backtest-cache CLI) | production (unchanged) |

`engine/wf_edge.py` is the acknowledged **DAO exception**: it contains the table's
write SQL but its data-write function is only callable from research (rule W2). Its
`ensure_wf_edge_table` (idempotent `CREATE IF NOT EXISTS`) remains usable by readers —
schema-safety, not a data write.

## Enforcement — `tests/test_research_data_fence.py`

Source-scan CI test, same proven pattern as the import boundary (M2) and the
db-centralization guard (3C):

- **W1:** no `INSERT/UPDATE/REPLACE/DELETE/DROP` statement targeting the three tables in
  any production scope (identical scope list to `test_architecture_boundary.py`), with
  DAO allowlist `{engine/wf_edge.py}` and a shrink-only count guard (`len == 1`).
- **W2:** `save_wf_edge(` is not called anywhere in the production scopes (the DAO
  defines it; only `research/` may call it).
- Teeth verified at implementation time by seeding a violation and watching it fail.

Dashboard routes (`routes/`, research-UI) sit outside the production scopes by the same
convention as the import boundary.

## Deferred-retirement path (future, each its own decision — NOT this increment)

- Scan-loop consistency blacklist (`wf_scores`) → registry-artifact freeze or removal
  (Phase-2 already showed per-ticker consistency is statistically hollow).
- AutoTrade quality gate (`backtest_cache`) → registry evidence at promotion time.
- Edge-veto stats (`wf_edge`) → promotion-time frozen stats, if edge-veto ever goes
  enforce.
- When the last reader retires, the physical move to `research.db` becomes the trivial
  operation the original M4 imagined.

## Out of scope

Any reader rewrite; any table move; creating `research.db`; changing what any gate does.

## Definition of done

Fence test green + teeth-verified; original spec §10 table annotated with the amendment;
`registry/SCHEMA.md` documents the three tables' contract; full suite green; merged.
