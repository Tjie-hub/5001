# Schema Migrations Log

**Owner lane:** Eng (EXEC-001 §13)
**Rule:** every DDL change gets a row here, in addition to its entry in the single schema module's ordered migration list (EXEC-001 ER-6). Hand-run DDL is an incident (EXEC-001 §10 Incident response). Append-only; migrations are forward-compatible by construction, never rolled back (EXEC-001 §12).

No schema module exists yet — it is a Phase 1 deliverable (PLAN-001 P1.E1.S1: "one idempotent schema module: CREATE + ordered ALTER migration list per table, executed at startup"). This file is a bring-up skeleton (EXEC-001 §15) and stays empty until P1.E1.S1 lands.

| id | tables | reason | task | reversible? |
|---|---|---|---|---|
| — | — | — | — | — |
