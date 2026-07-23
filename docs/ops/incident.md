# Incident Response Checklist

**Status:** STUB — bring-up skeleton (EXEC-001 §15).
**Source:** PLAN-001 §10 "Incident response"

Classify first, then act:
- [ ] **Data-plane** (bad/missing data → the Certifier should have caught it): if not, file check-gap + Correction (from Phase 1, WS-B/WS-C)
- [ ] **Decision-plane** (wrong verdict → Decision Record has full provenance): replay it (from Phase 2+, WS-E/WS-G)
- [ ] **Process** (run died → resume semantics): Authority-refusal rule if records exist (from Phase 1 stub, enforced Phase 3 — P1.E5.S3)

Rule (always applies, all phases): operator interventions **only** via command verbs (ADR §8.8, AP-11). Direct SQL against the database is itself an incident, not a fix.

Live-incident rollback triggers (Phase 3–4 only) are listed at PLAN-001 §9.6 — not reproduced here to avoid a second source of truth; read them there.

## Incident log
| Date | Class | Detection | Root cause | DEF id | Closed |
|---|---|---|---|---|---|
| — | — | — | — | — | — |
