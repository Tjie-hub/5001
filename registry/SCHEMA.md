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
