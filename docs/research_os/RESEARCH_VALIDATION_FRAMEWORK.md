# Research Validation Framework

**Version:** 1.1 · **Status:** Canonical · **Canonical Status:** Permanent repository document · **Layer:** L2 / L7 — Validation
**Owner:** Chief Research Officer · **Last Updated:** 2026-07-15 · **Supersedes:** v1.0 (2026-07-15) — **minor amendment per [[DECISION_LOG]] D-022: §0 added. §1–§3 are unchanged.**
**Realized in v3:** `research/gatekeeper` — the 8-stage pipeline is this framework's **executable realization, not a parallel design** ([[RESEARCH_OS_RECONCILIATION]] §4, §6). Multiplicity family scoping = v3 Invariant #12. **`gate_decisions` + `gate_evidence` realize Experiment and Evidence Custody** ([[CUSTODY_MODEL]] §6–§7)
**Scientific basis:** [[01_SCIENTIFIC_FOUNDATION]] §7 (§3's mechanism-primacy rule is R18, argued at §7.1–§7.4), §4.2 (evidence tiers E0–E7), §2.1 (severity), **§2.4 + R6 (custody)**

## 0. Custody precondition (amendment — D-022)

> **Validation presupposes custody. A validation performed over a partition whose custody state is unknown validates an unknown.**

Per [[01_SCIENTIFIC_FOUNDATION]] §2.4, *"unenforced custody produces a system whose evidential state cannot be known even by its own operators."* Every gate below therefore carries a precondition it did not previously state:

- **The out-of-sample partition must have been released under a Custody Receipt, once, for the hypothesis under test** — [[CUSTODY_MODEL]] §5.4, **CU-5** (`ordinal` = 1).
- **Absent that receipt, the OOS result is not weak evidence. Its custody state is unknown**, and per §2.4 an unknown custody state makes the evidential state unknown — which is **DG9**, not a discount.

**This does not change §1–§3, and it does not change the gatekeeper.** `research/gatekeeper` already records `dataset_fingerprint`, `git_commit`, `seed`, `candidate_hash`, `config_hash` and writes append-only `gate_decisions` + `gate_evidence` — **a correct and complete realization of Evidence Custody, formalized rather than redesigned** ([[CUSTODY_MODEL]] §7.2). What it does not yet receive is a **custody-released partition**, because Dataset Custody does not exist ([[CUSTODY_MODEL]] §5.1, **G-9**).

> **The framework's honest current state: the most rigorously validated component in the institution is certifying inputs the institution cannot vouch for** ([[CUSTODY_MODEL]] §7.3). This section records that; it does not repair it. Repair is **RFC-1**.

**§3's Replication requirement is unchanged and is grounded in [[01_SCIENTIFIC_FOUNDATION]] §8.3: conclusion-invariance, not bit-identity** — see [[REPLICATION_STANDARD]] §1 and gap **G-7**.

## 1. Statistical Validation
- **Significance Testing**: Standard p-value thresholds are insufficient. All results require strict out-of-sample confirmation.
- **False Discovery Rate (FDR) Control**: Mandatory application of the Benjamini-Hochberg procedure or equivalent to adjust for multiple testing across the hypothesis space.
- **Deflated Sharpe Ratio (DSR)**: Required to adjust the expected performance of a mechanism for the number of trials and the variance of the trials.
- **Probability of Backtest Overfitting (PBO)**: Combinatorially symmetric cross-validation (CSCV) must be applied to quantify the risk that the mechanism is a statistical artifact.

## 2. Market Validation
- **Transaction Cost Modeling**: Mechanisms must demonstrate significance net of institutional-grade friction models (exchange fees, routing costs).
- **Liquidity Impact**: The capacity of the mechanism must be quantified. At what volume does market impact consume the inefficiency?
- **Regime Stability**: The mechanism must be tested across high-volatility, low-volatility, high-volume, and low-volume regimes to ensure it is not an artifact of a specific macro environment.
- **Decay Measurement**: Empirical measurement of the mechanism's half-life over time.

## 3. Scientific Validation
- **Economic Explanation**: A mechanism is invalid, regardless of statistical significance, if it cannot be explained by fundamental market micro-economics (e.g., latency, inventory, asymmetry).
- **Replication**: An independent researcher must be able to recreate the findings using only the Hypothesis Object and the methodology documentation.
- **Novelty Assessment**: The contribution must be evaluated against the existing Accepted Knowledge Base to ensure it is a distinct phenomenon, not a derivative of a known factor.
