# Market Inefficiency Research Pipeline

**Version:** 1.0 · **Status:** Canonical · **Canonical Status:** Supporting reference — canonical logic lives in [[RESEARCH_OPERATING_MODEL]] ([[PHASE_A_ARCHITECTURE_REVIEW]] R7) · **Layer:** L2
**Owner:** Research Architect · **Last Updated:** 2026-07-15 · **Supersedes:** — (initial version)
**Realized in v3:** partial — `research/gatekeeper` realizes S7–S8 ([[RESEARCH_OS_RECONCILIATION]] §4). Stages S1–S2, S9–S10 have no v3 realization
**Scientific basis:** [[01_SCIENTIFIC_FOUNDATION]] §7.3 — the S2→S3→S6 ordering *is* the mechanism-first argument made procedural: the mechanism must be authored blind to the result. S2's micro-economics gate is falsification mode F1 (§5.3)

## 1. Flow Diagram

Literature Discovery
        ↓
Mechanism Identification
        ↓
Hypothesis Registration
        ↓
Data Preparation
        ↓
Feature Construction
        ↓
Experiment Execution
        ↓
Statistical Validation
        ↓
Robustness Testing
        ↓
Peer Review
        ↓
Knowledge Promotion

## 2. Stage Definitions

### Stage 1: Literature Discovery
- **Input**: Academic papers, market structure working groups, exchange rule changes.
- **Process**: Extraction of core concepts into Literature Cards.
- **Output**: Instantiated Literature Card Object.
- **Validation criteria**: Peer verification of the interpretation of the source text.

### Stage 2: Mechanism Identification
- **Input**: Literature Cards, empirical observations.
- **Process**: Abstracting the core causal economic relationships.
- **Output**: Economic Mechanism Object.
- **Validation criteria**: Must not violate the fundamental laws of market micro-economics.

### Stage 3: Hypothesis Registration
- **Input**: Economic Mechanism Object.
- **Process**: Formal specification of testable predictions.
- **Output**: Research Hypothesis Object (Status: REGISTERED).
- **Validation criteria**: Must be falsifiable; validation criteria must be established ex-ante.

### Stage 4: Data Preparation
- **Input**: Research Hypothesis Object.
- **Process**: Mapping required data to institutional Dataset Objects.
- **Output**: Bound Dataset Object.
- **Validation criteria**: Cryptographic verification of data immutability.

### Stage 5: Feature Construction
- **Input**: Dataset Object, Mathematical formulations.
- **Process**: Implementation within the Feature Computation Graph (FCG).
- **Output**: Feature Definition Objects.
- **Validation criteria**: Bit-identical reproducibility across redundant compute nodes.

### Stage 6: Experiment Execution
- **Input**: Hypothesis Object, Feature Definitions, Dataset Object.
- **Process**: Standardized execution of the testing methodology.
- **Output**: Experiment Object.
- **Validation criteria**: Execution completes without errors and logs all deterministic seeds.

### Stage 7: Statistical Validation
- **Input**: Experiment Object outputs.
- **Process**: Automated suite of statistical tests (FDR, PBO).
- **Output**: Validation Report Object (Draft).
- **Validation criteria**: Must strictly exceed pre-registered thresholds in the Hypothesis Object.

### Stage 8: Robustness Testing
- **Input**: Validation Report Object (Draft).
- **Process**: Stress testing under transaction cost assumptions, varying latency, and simulated market impact.
- **Output**: Validation Report Object (Finalized).
- **Validation criteria**: Mechanism effect must survive institutional friction models.

### Stage 9: Peer Review
- **Input**: Full Lineage (Hypothesis → Validation Report).
- **Process**: Adversarial review by the Validation Reviewer and CRO.
- **Output**: Final Gate Decision.
- **Validation criteria**: Consensus on economic causality and methodological rigor.

### Stage 10: Knowledge Promotion
- **Input**: Passed Validation Report.
- **Process**: Archival into the institutional ontology.
- **Output**: Accepted Knowledge Object (or Failure Library Entry).
- **Validation criteria**: Complete lineage traceability is confirmed by the OS.
