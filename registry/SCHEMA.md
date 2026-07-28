# Edge Registry Schema (v1)

Spec: `docs/superpowers/specs/2026-07-07-research-production-separation-design.md` §6.

## edge_registry.yaml — list of entries

| field | type | req | notes |
|---|---|---|---|
| id | str | ✓ | `<FAMILY>_<REGIME-SCOPE>`, stable across versions |
| version | int | ✓ | immutable once status leaves CANDIDATE |
| status | enum | ✓ | CANDIDATE, SHADOW, APPROVED, SUSPENDED, RETIRED, SUPERSEDED |
| strategy_fn | str | ✓ | key into STRATEGY_FUNCS / checker dispatch |
| regimes | list | ✓ | regime-map bands the strategy may trade |
| universe_artifact | path | ✓ | frozen ticker JSON, relative to registry/ |
| risk_category | str | ✓ | descriptive |
| owner | str | ✓ | |
| approved | date | ✓ for APPROVED/SHADOW | |
| manifest | path | ✓ for APPROVED/SHADOW | approval manifest, relative to registry/ |
| requires | map | ✓ | data_schema, exit_kernel, regime_model, engine_version (ints) |
| changelog | str | ✓ | |

## Loading rules (engine/registry_loader.py)

- Only APPROVED and SHADOW load. Other statuses are ignored (lifecycle, not error).
- Missing required field, unreadable artifact, or any `requires` value ≠ the engine's
  `ENGINE_VERSIONS` ⇒ entry SKIPPED + fail-open alarm; engine continues with the rest.
- Production reads the registry ONCE at startup and logs its hash + counts.
- Engine-side `ENGINE_VERSIONS` are bumped whenever semantics change (corpus schema,
  exit kernel, regime model, engine contract); the bump's PR must state which registry
  entries it invalidates. A bump mechanically forces re-validation of stale approvals.

## Immutability & promotion

Promotion/suspension/rollback = git commit (PR + CI + manual merge). Never edit an
approved entry — supersede it with a new version. Each APPROVED/SHADOW version carries an
approval manifest binding: walkforward output, frozen universe, report, config hash,
code commit, corpus snapshot.

## Research data products (M4-lite, 2026-07-08)

`wf_scores`, `wf_edge`, `backtest_cache` live in `walkforward.db` but are research
data products: **only `research/` writes them** (CI-enforced by
`tests/test_research_data_fence.py`; DAO exception `engine/wf_edge.py`, whose
`save_wf_edge` is research-only by rule W2). Production may read them (legacy gates,
dashboards); each such reader's retirement toward registry-artifact evidence is a
future, separate decision. `ensure_wf_edge_table` (idempotent CREATE) stays usable by
readers — schema-safety, not a data write.

## Lifecycle evidence (R-10 enforcement)

A `SHADOW`/`APPROVED` entry must carry a verifiable receipt in its manifest. `SHADOW` needs a
Phase C PROMOTE `gate_decision`; `APPROVED` also needs a Phase 5 forward `GO` clearing the
frozen bar (`min_n=15, go_exp=0.50`). Enforced by `tests/test_registry_lifecycle.py` (CI, hard)
and `engine/registry_loader.validate_evidence` (runtime WARN, non-breaking). Pre-R-10 entries
may be grandfathered in `registry_loader._LIFECYCLE_DEBT` (shrink-only, with a remediation
deadline).

    evidence:
      gate_decision: {decision_id, final_state: PROMOTE_TO_FORWARD_TEST, config_hash, dataset_fingerprint}
      forward:        # APPROVED only
        {verdict: GO, n, exp_pct, rule: {min_n: 15, go_exp: 0.50}, as_of}
