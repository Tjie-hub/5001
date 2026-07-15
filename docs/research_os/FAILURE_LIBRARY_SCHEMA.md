# Failure Library Schema

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
