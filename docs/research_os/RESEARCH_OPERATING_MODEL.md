# Research Operating Model

**Version:** 1.0 · **Status:** Canonical · **Canonical Status:** Permanent repository document · **Layer:** L2 — Research Architecture
**Owner:** Chief Research Officer · **Last Updated:** 2026-07-15 · **Supersedes:** — (initial version)
**Realized in v3:** partial — research/production data fence (`tests/test_research_data_fence.py`); R-10 receipt-bound lifecycle enforcement. No single v3 component realizes the roles/gates model ([[RESEARCH_OS_RECONCILIATION]] §4)
**Scientific basis:** [[01_SCIENTIFIC_FOUNDATION]] §2.4 (custody states), §2.2 (asymmetric burden), §5.2 (G1 admissibility). **Known limitation:** LIM6 / ADR-L1-007 — §5–§6 presuppose ≥3 distinct humans; the institution has one

## 1. Purpose
This document defines the operationalization of the Market Microstructure & Market Inefficiency Research Charter. It establishes the governing system that ensures all research activities remain aligned with the core tenets: mechanism discovery over signal mining, scientific validation over performance chasing, and reproducibility over complexity.

## 2. Research Lifecycle
The institutional research lifecycle is a deterministic progression of knowledge creation, ensuring that every finding is structurally sound before advancing to production.

1. **Ideation & Literature Review**: Identification of theoretical mechanisms.
2. **Hypothesis Formulation**: Formalizing the mechanism into a testable proposition.
3. **Data Acquisition & Engineering**: Sourcing and preparing high-fidelity microstructure data.
4. **Feature Engineering (FCG)**: Constructing reproducible primitives in the Feature Computation Graph.
5. **Experiment Execution**: Running standardized statistical tests against out-of-sample data.
6. **Validation & Review**: Peer and committee review against strict rejection criteria.
7. **Knowledge Archival**: Committing to the Accepted Knowledge Base or the Failure Library.

## 3. Research Object Model (Overview)
All research entities are treated as immutable programmatic objects with strict schemas. This prevents "tribal knowledge" and ensures absolute reproducibility. Every object references its parent lineage, maintaining an unbroken chain of provenance from literature to accepted knowledge.

## 4. Research Workflow
The workflow is a Directed Acyclic Graph (DAG) of tasks. No stage may commence until the prior stage has passed its automated and manual validation gates. 

## 5. Roles and Responsibilities

- **Chief Research Officer (CRO)**: Owns the research charter, final arbiter of Accepted Knowledge, and ensures programmatic adherence to scientific standards.
- **Research Architect**: Designs and maintains the Research Operating System, the Feature Computation Graph, and the lineage tracking infrastructure.
- **Quant Researcher**: Authors hypotheses, designs experiments, interprets causal mechanisms, and documents findings. Prohibited from accessing out-of-sample data during the formulation phase.
- **Data Engineer**: Maintains the high-frequency market data pipelines, guarantees data fidelity, and implements the lowest-level market adapters.
- **Validation Reviewer**: An independent adversarial role responsible for attempting to falsify the candidate hypothesis and auditing reproducibility.

## 6. Research Approval Gates
Progression through the lifecycle is guarded by strict institutional gates:
- **Gate 1: Hypothesis Registration**: Requires CRO or delegate approval of the scientific rationale before any empirical testing begins.
- **Gate 2: Code Review**: Asserts that feature logic and experiment design are deterministic and adhere to the Institutional Research Grammar.
- **Gate 3: Statistical Validation**: Automated check against FDR, PBO, and Deflated Sharpe thresholds.
- **Gate 4: Peer Defense**: The researcher must defend the economic causality of the mechanism in an institutional forum.

## 7. Discovery → Confirmation → Accepted Knowledge Pipeline
- **Discovery**: Unconstrained exploratory environment on a designated in-sample dataset.
- **Confirmation**: Constrained, out-of-sample empirical testing strictly bounded by the registered hypothesis.
- **Accepted Knowledge**: Irreversible commitment of the validated mechanism to the institutional repository.
