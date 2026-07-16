# Microstructure Research Roadmap

**Status:** Reference — supporting/living, not canonical law ([[MIGRATION_PLAN]] §2) · **Layer:** —
(pre-dates the P0–P6 Program taxonomy; not a Program definition — see [[RESEARCH_OS_MASTER_ROADMAP]]
§3 for canonical Program P5/P6 scope)

## I. LOB Imbalance / Order Flow Imbalance
- **Research questions**: To what extent does cross-sectional order flow imbalance predict short-term mid-price transitions? How do stochastic cancelations impact predictive validity?
- **Required datasets**: High-resolution L3 (Limit Order Book) data, Full depth-of-book updates, Trade prints.
- **Candidate measurements**: Volume-weighted OFI, Cancel-to-Trade ratios, Queue position dynamics.
- **Experiments**: Regression of forward returns on contemporaneous and lagged OFI vectors across varying liquidity regimes.
- **Success criteria**: Identification of a statistically significant, causal link between observable imbalance and subsequent price discovery, surviving false discovery rate corrections.

## II. Auction Dislocation
- **Hypotheses**: Information asymmetries during opening and closing auctions create transient price dislocations that mean-revert in continuous trading. Market-on-Close (MOC) order imbalances are structurally predictable via continuous session inventory analysis.
- **Data requirements**: Exchange auction imbalance messages, pre-open/pre-close indicative match prices, historical continuous session order flow.
- **Testing framework**: Event-study methodology centered on auction crosses; cross-sectional analysis of dislocation magnitude versus index inclusion/exclusion events.
- **Validation gates**: Transaction cost analysis must demonstrate that the dislocation exceeds the spread and market impact required to execute the corrective trade.

## III. Liquidity Vacuum
- **Regime detection**: Identification of sudden, non-linear withdrawals of resting liquidity (flash crashes, micro-crashes) preceding large fundamental price shifts.
- **Liquidity stress indicators**: Order book density variance, bid-ask spread expansion velocity, frequency of swept levels.
- **Decay analysis**: Measurement of the half-life of liquidity vacuums and the speed of market maker replenishment.
- **Research challenges**: Disentangling informed trading from mechanical risk-limit breaches by algorithmic market makers; severe non-stationarity in the data generation process.
