# Recovery Checklist

**Status:** STUB — bring-up skeleton (EXEC-001 §15).
**Source:** PLAN-001 §10 "Recovery"

- [ ] DB restore → fresh-bootstrap guarantee holds (from Phase 1, H-6 fix / P1.E1.S1.T3)
- [ ] Republication determinism re-derives artifacts (from Phase 1, P1.E4.S4)
- [ ] INV-T2 validates registry (from Phase 2+)
- [ ] Positions reconcile via INV-P1 joins (from Phase 2+, WS-E)
- [ ] Lost artifact → republish; hash must match (from Phase 1, ADR §6.1)

Nothing in this checklist is exercisable before Phase 1 ships the schema module and publication pipeline; it stays a stub until then.

## Recovery log
| Date | Trigger | Steps taken | Verified by | Notes |
|---|---|---|---|---|
| — | — | — | — | — |
