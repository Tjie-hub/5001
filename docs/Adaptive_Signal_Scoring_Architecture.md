# Adaptive Signal Scoring Architecture (vNext)

## Problem Statement

The current engine has evolved into a robust multi-strategy platform, but it suffers from **signal starvation**.

Most strategies generate valid opportunities, yet multiple sequential filters eliminate them before they reach the portfolio.

Current pipeline:

```
Strategy
    ↓
Filter 1
    ↓
Filter 2
    ↓
Filter 3
    ↓
Context Gate
    ↓
Flow Gate
    ↓
Walkforward Gate
    ↓
Signal
```

Every gate is binary.

One failed condition rejects the trade completely.

This design maximizes precision but often sacrifices recall, causing many potentially profitable trades to disappear.

The objective is to **increase trade quality without blocking good trades.**

---

## Core Design Philosophy

Replace

```
Pass / Fail
```

with

```
Score → Rank → Allocate
```

Every strategy should first detect opportunities.

The engine then evaluates how attractive each opportunity is rather than asking whether it is perfect.

---

## New Pipeline

```
Market Data
        │
        ▼
15 Strategy Engines
        │
        ▼
Candidate Trades
        │
        ▼
Feature Extraction
        │
        ▼
Edge Scoring Engine
        │
        ▼
Portfolio Ranking
        │
        ▼
Risk Engine
        │
        ▼
Final Trades
```

Instead of filtering opportunities, every module contributes to an overall edge score.

---

## Hard Filters

Only conditions that protect capital should reject trades.

These remain binary.

Examples:

- Insufficient liquidity
- Invalid market data
- Trading halt
- Maximum portfolio exposure exceeded
- Maximum sector exposure exceeded
- Position size below minimum
- Risk exceeds portfolio limit

Hard filters should reject less than 10% of candidates.

Everything else becomes a score.

---

## Soft Factors

The following should no longer reject trades.

Instead they contribute positively or negatively to Edge Score.

### Trend

Instead of

```
MA20 slope > 0.5
```

use

| Condition | Score |
|-----------|-------|
| Slope | +20 |
| Strong slope | +25 |
| Moderate slope | +15 |
| Weak slope | +5 |
| Negative slope | 0 |

### Volume

Instead of

```
Volume Ratio > 1.8
```

use

| Condition | Score |
|-----------|-------|
| VR > 3.0 | +20 |
| VR 2–3 | +16 |
| VR 1.5–2 | +10 |
| VR 1–1.5 | +5 |
| Low volume | 0 |

### Flow

Instead of

```
Positive Flow → PASS
Negative Flow → FAIL
```

use

| Condition | Score |
|-----------|-------|
| Strong accumulation | +25 |
| Moderate accumulation | +18 |
| Neutral | +10 |
| Weak distribution | +2 |
| Heavy distribution | -15 |

Negative flow reduces confidence but does not automatically reject the trade unless portfolio risk rules require it.

### Walkforward Performance

Instead of

```
Consistency >= 50%
```

use

| Condition | Score |
|-----------|-------|
| Consistency > 70% | +25 |
| 60–70% | +20 |
| 50–60% | +15 |
| 40–50% | +10 |
| 30–40% | +5 |
| Below 30% | 0 |

Walkforward becomes a confidence factor instead of a hard gate.

### Market Regime

| Condition | Score |
|-----------|-------|
| Strategy matches regime | +20 |
| Neutral | +10 |
| Slight mismatch | +5 |
| Wrong regime | 0 |

### Sector Strength

| Condition | Score |
|-----------|-------|
| Leading sector | +15 |
| Average | +8 |
| Weak | 0 |

### Relative Strength

| Condition | Score |
|-----------|-------|
| Strong outperformer | +15 |
| Market performer | +8 |
| Weak | 0 |

---

## Edge Score

Every candidate receives a composite score.

Example:

| Factor | Score |
|--------|-------|
| Trend | 20 |
| Flow | 18 |
| Walkforward | 15 |
| Volume | 15 |
| Sector | 12 |
| Relative Strength | 10 |
| Risk Reward | 15 |
| **Total** | **105** |

Instead of asking

```
Pass?
```

the engine asks

```
How good is this trade?
```

---

## Strategy Independence

Strategies should only detect setups.

Example:

**Current:**

```
Momentum
    ↓
Volume
    ↓
Trend
    ↓
ATR
    ↓
Flow
    ↓
Reject
```

**New:**

```
Momentum
    ↓
Candidate
    ↓
Edge Score
```

The strategy no longer owns filtering logic.

This makes every strategy simpler and more reusable.

---

## Unified Candidate Pool

Instead of producing isolated signals

```
Momentum → BBCA
Sweep → BRPT
Panic → TLKM
```

combine them into

**Master Candidate Table**

| Ticker | Strategy | Edge | Flow | Walkforward | Trend | Sector | RR | Volatility | Correlation |
|--------|----------|------|------|-------------|-------|--------|----|------------|-------------|

Every opportunity competes against every other opportunity.

---

## Portfolio Ranking

Sort by **Edge Score descending**

Then apply portfolio constraints.

Example:

- Take Top 5
- Maximum 2 banking stocks
- Maximum 2 coal stocks
- Maximum 8% portfolio heat
- Maximum 25% sector allocation

Ranking is more powerful than filtering.

---

## Benefits

**Current System:**

```
100 candidates
    ↓
10 sequential filters
    ↓
3 trades
```

**New System:**

```
100 candidates
    ↓
Edge Scoring
    ↓
Rank Top 15
    ↓
Risk Engine
    ↓
Top 5 trades
```

Good trades are no longer discarded because of one imperfect indicator.

---

## Design Principle

Every indicator is uncertain.

No single indicator should decide whether a trade exists.

Indicators should contribute evidence.

The engine should aggregate evidence.

---

## Future Architecture

```
                    Market Data
                         │
                         ▼
              ┌─────────────────────┐
              │  Strategy Detection │
              └─────────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ Candidate Generator │
              └─────────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ Feature Extraction  │
              └─────────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │  Edge Score Engine  │
              └─────────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ Portfolio Ranking   │
              └─────────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ Risk Management     │
              └─────────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ Trade Execution     │
              └─────────────────────┘
```

---

## Guiding Principle

> **Strategies should discover opportunities.**
>
> **Scoring should measure opportunity quality.**
>
> **Risk management should decide capital allocation.**
>
> **Only portfolio-level risk should reject trades outright.**

This separation of responsibilities reduces over-filtering, increases signal diversity, and allows strong trades to survive even when one or two indicators are imperfect.
