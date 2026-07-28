# Failure Library Schema

**Version:** 1.0 · **Status:** Canonical · **Canonical Status:** Permanent repository document · **Layer:** L2 / L8 — Knowledge Repository
**Owner:** Chief Research Officer · **Last Updated:** 2026-07-15 · **Supersedes:** — (initial version)
**Realized in v3:** `failure_registry` (append-only) ([[RESEARCH_OS_RECONCILIATION]] §4)
**Scientific basis:** [[01_SCIENTIFIC_FOUNDATION]] R12 (negative evidence is evidence), §5.3 (falsification modes F1–F9), R1 (Duhem–Quine attribution — the reason `invalid_assumptions` is structured). Library completeness is a precondition of assumption A7

## 1. Purpose
The Failure Library is the institutional repository of falsified hypotheses and failed experiments. Preserving negative results is critical to prevent redundant research, map the boundaries of market efficiency, and mitigate publication bias within the institution.

## 2. Schema Definition

- **failure_id**: Unique UUID for the failure record.
- **hypothesis_ref**: The ID of the Research Hypothesis Object that was tested.
- **mechanism_ref**: The ID of the underlying Economic Mechanism.
- **experiment_ref**: The ID of the specific Experiment Object that yielded the negative result.
- **failure_reason**: Categorical classification (e.g., Insufficient Signal-to-Noise, PBO Exceeded, Destroyed by Transaction Costs, Look-Ahead Bias Discovered).
- **invalid_assumptions**: A structured narrative detailing which a priori assumptions proved false in the empirical data.
- **lessons_learned**: Institutional takeaways to improve future mechanism design or feature engineering.
- **related_features**: List of Feature IDs that proved non-predictive in this specific context.
- **archived_date**: Timestamp of institutional commit.
