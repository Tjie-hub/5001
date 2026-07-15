# Research Object Model

**Version:** 1.0 · **Status:** Canonical · **Canonical Status:** Permanent repository document · **Layer:** L2 — Research Architecture
**Owner:** Research Architect · **Last Updated:** 2026-07-15 · **Supersedes:** — (initial version)
**Realized in v3:** `research/knowledge` (hypotheses, `hypothesis_links`, receipt-bound `set_status`) · `research/regime` (`regime_profiles`) · edge registry ([[RESEARCH_OS_RECONCILIATION]] §4)
**Scientific basis:** [[01_SCIENTIFIC_FOUNDATION]] §3 (world ontology — distinct from this artifact ontology), §5.2 (hypothesis admissibility)

## 1. Definition
The Research Object Model establishes the strict schemas for all scientific entities within the institution. 

## 2. Core Objects

### Research Hypothesis Object
- **hypothesis_id**: Unique UUID for the hypothesis.
- **mechanism**: The structural or behavioral market inefficiency being investigated.
- **economic_rationale**: Theoretical explanation of why the inefficiency exists and persists.
- **prediction**: The expected empirical observation if the mechanism is active.
- **null_hypothesis**: The baseline state if the market is perfectly efficient with respect to the mechanism.
- **alternative_hypothesis**: The statistically measurable deviation from efficiency.
- **required_data**: Array of dataset references (e.g., Daily OHLCV, Intraday Signed Flow, Broker Summary, Trade Prints). Dataset authority is [[DATA_FEASIBILITY_STUDY]] §4 — the binding scope constraint; `required_data` must resolve to capabilities classified there as *Available Today* or *Obtainable Later*.
- **validation_criteria**: Pre-registered thresholds for significance and effect size.
- **status**: Current state (e.g., REGISTERED, IN_TESTING, VALIDATED, FAILED).

### Literature Card
- **card_id**: Unique identifier.
- **source**: DOI, ArXiv ID, or Journal citation.
- **identified_mechanisms**: List of mechanisms proposed by the authors.
- **empirical_claims**: Specific data-backed claims to be reproduced.
- **limitations**: Boundary conditions of the paper's findings.

### Economic Mechanism
- **mechanism_id**: Unique identifier.
- **classification**: Taxonomy category (e.g., Inventory Risk, Asymmetric Information, Liquidity/Price-Impact Compensation). The taxonomy is [[01_SCIENTIFIC_FOUNDATION]] §3.4 (classes M1–M6).
- **causal_graph**: DAG representing the interaction of market participants.
- **half_life_estimate**: Theoretical duration of the inefficiency before arbitrage correction.

### Dataset Object
- **dataset_id**: Unique identifier.
- **asset_class**: Target universe.
- **resolution**: Granularity (e.g., Daily bar, 1-minute bar, Tick). Attainable resolutions are enumerated in [[DATA_FEASIBILITY_STUDY]] §3–§4.
- **regime_classification**: Market conditions during the sample period.
- **provenance_hash**: Cryptographic hash of the raw data files for reproducibility.

### Experiment Object
- **experiment_id**: Unique identifier.
- **hypothesis_ref**: Link to the target Hypothesis Object.
- **feature_set_ref**: Link to the specific version of the Feature Computation Graph used.
- **in_sample_period**: Dates used for parameter calibration.
- **out_of_sample_period**: Dates used for validation.
- **methodology**: Statistical procedures utilized.

### Feature Definition
- **feature_id**: Unique identifier.
- **mathematical_formulation**: LaTeX representation of the feature.
- **code_reference**: Pointer to the implemented logic in the repository.
- **dependencies**: Upstream features or raw data elements.

### Validation Report
- **report_id**: Unique identifier.
- **experiment_ref**: Link to the evaluated experiment.
- **statistical_metrics**: Output of PBO, Deflated Sharpe, etc.
- **reviewer_notes**: Qualitative assessment by the Validation Reviewer.
- **decision**: Pass/Fail outcome.

### Failure Library Entry
- **failure_id**: Unique identifier.
- **hypothesis_ref**: Link to the failed hypothesis.
- **falsification_reason**: Primary driver of failure (e.g., Data Mining, Regime Shift, Transaction Costs).
- **lessons_learned**: Institutional insight gained.

### Accepted Knowledge Object
- **knowledge_id**: Unique identifier.
- **mechanism_ref**: Link to the underlying mechanism.
- **validation_ref**: Link to the passing validation report.
- **decay_monitor_id**: Link to the live process tracking the ongoing validity of the mechanism.
