# Deployment Checklist

**Status:** STUB — bring-up skeleton (EXEC-001 §15). Filled in as phases deliver the objects it checks (PLAN-001 §10).
**Source:** PLAN-001 §10 "Deployment"

- [ ] Deploy only between EOD completion and NIGHTLY start
- [ ] Schema migrations run by the schema module on startup — never by hand (from Phase 1, P1.E1.S1)
- [ ] `code_version` stamp visible in next manifest (from Phase 1, RunManifest — P1.E5.S1)
- [ ] If feature definitions changed → `feature_version` bump confirmed (from Phase 1, P1.E4.S2)
- [ ] Post-deploy: next run's manifest reviewed

## Known environment dependencies (bring-up)
- `node` must be on `PATH` for `tests/test_value_format.py` and the pre-merge gate script's test-suite check. Not a project dependency — a user-space install is sufficient: `~/.local/node/bin` on `PATH` (see `docs/EXEC-DECISIONS.md` IMPL-DEC-001). No `sudo`/system package required.

## Deployment log
| Date | Release tag | Operator | Notes |
|---|---|---|---|
| — | — | — | — |
