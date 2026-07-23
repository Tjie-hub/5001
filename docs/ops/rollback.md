# Rollback Checklist (deployment-level)

**Status:** STUB — bring-up skeleton (EXEC-001 §15).
**Source:** PLAN-001 §10 "Rollback (deployment-level)"; consolidated mechanism table at EXEC-001 §12.

- [ ] Revert release (redeploy previous `v2.x.y` tag)
- [ ] Verify: startup migration list is append-only so schema rolls forward-compatibly — schema is never rolled back
- [ ] Verify manifest `code_version` reverted
- [ ] If artifacts were published by the bad release: supersede via Correction Protocol — never delete (EXEC-001 ER-7)

Full layer-by-layer rollback table (commit/task, release, parameter, data/corpus, artifacts, registry/decisions, stage/feature, cutover) lives at EXEC-001 §12 — this file covers only the deployment layer's operator steps.

## Rollback log
| Date | Trigger | Layer | Operator | Notes |
|---|---|---|---|---|
| — | — | — | — | — |
