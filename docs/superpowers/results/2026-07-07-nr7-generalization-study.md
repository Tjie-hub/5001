# NR7 Edge-Generalization Study — Results

Run: 2026-09-30T15:25:50 | corpus as-of 2026-07-29 | liquid universe 958 tickers | CV boundary 2024-12-23

## T1 — universe pooled (net of round-trip costs)
- exp -1.298%/trade | N 899 | win 29.0% | **FAIL** (bar >= +0.50%, N >= 300)

## T2 — selection / chronological CV
- early-selected tickers: late exp -1.649% | late N 14 | early exp +0.802% | retention -2.05 | **FAIL** (bar >= +0.50%, N >= 150, retention >= 0.50)

## T3 — regime strata
- SIDEWAYS: exp -1.615% | N 507 | win 24.5% | **FAIL** (bar >= +0.50%, N >= 100)
- BEAR: exp -1.560% | N 140 | win 26.4% | **FAIL** (bar >= +0.50%, N >= 100)
- BULL: exp -0.515% | N 252 | win 39.7% | **FAIL** (bar >= +0.50%, N >= 100)

## DECISION: **DO-NOT-WIDEN**

```json
{
  "T1": {
    "exp_pct": -1.2983436215767723,
    "n": 899,
    "win_rate": 29.032258064516128,
    "pass": false
  },
  "T2": {
    "late_exp": -1.6485240360436397,
    "late_n": 14,
    "early_exp": 0.8022357312048003,
    "retention": -2.0549122557379498,
    "pass": false
  },
  "T3": {
    "SIDEWAYS": {
      "exp_pct": -1.6154008552326802,
      "n": 507,
      "win_rate": 24.45759368836292,
      "pass": false
    },
    "BEAR": {
      "exp_pct": -1.5595844344571423,
      "n": 140,
      "win_rate": 26.428571428571427,
      "pass": false
    },
    "BULL": {
      "exp_pct": -0.5153208784545613,
      "n": 252,
      "win_rate": 39.682539682539684,
      "pass": false
    }
  },
  "widen_universe": false,
  "widen_sideways": false,
  "decision": "DO-NOT-WIDEN"
}
```
