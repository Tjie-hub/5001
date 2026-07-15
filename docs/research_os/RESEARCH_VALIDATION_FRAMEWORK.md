# Research Validation Framework

**Version:** 1.0 · **Status:** Canonical · **Canonical Status:** Permanent repository document · **Layer:** L2 / L7 — Validation
**Owner:** Chief Research Officer · **Last Updated:** 2026-07-15 · **Supersedes:** — (initial version)
**Realized in v3:** `research/gatekeeper` — the 8-stage pipeline is this framework's **executable realization, not a parallel design** ([[RESEARCH_OS_RECONCILIATION]] §4, §6). Multiplicity family scoping = v3 Invariant #12
**Scientific basis:** [[01_SCIENTIFIC_FOUNDATION]] §7 (§3's mechanism-primacy rule is R18, argued at §7.1–§7.4), §4.2 (evidence tiers E0–E7), §2.1 (severity)

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
