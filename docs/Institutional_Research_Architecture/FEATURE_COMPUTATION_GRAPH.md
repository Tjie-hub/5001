# Feature Computation Graph (FCG)

## 1. Feature as Scientific Object
A feature in the FCG is not merely a variable; it is an immutable, mathematically rigorous scientific object. It represents a specific, isolated measurement of a market microstructure phenomenon.

## 2. DAG Architecture
The FCG operates as a strictly typed Directed Acyclic Graph. Cycles are prohibited. Every node represents a deterministic transformation.

Example Lineage:
Raw Market Data
        ↓
Order Events
        ↓
Microstructure Features
        ↓
Hypothesis Features
        ↓
Experiment Dataset
        ↓
Research Result

## 3. Feature Lineage and Dependencies
Every feature maintains an explicit list of dependencies. If an upstream feature is updated, a new version branch is created; the previous instantiation is frozen to preserve historical experiment reproducibility.

## 4. Version Control
Features are versioned using a semantic scheme linked to the Git commit hash of their implementation. 
Format: `FeatureName_v[Major].[Minor]_[Hash]`

## 5. Reproducibility Requirements
- **Determinism**: The same inputs must yield bit-identical outputs regardless of the hardware architecture.
- **Immutability**: Once a feature is used in a Registered Experiment, its code cannot be altered.
- **Statelessness**: Feature computation nodes must not maintain state across independent execution boundaries.
