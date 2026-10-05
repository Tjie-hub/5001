# NR7 Edge-Generalization Study — Results

Run: 2026-10-01T15:36:08 | corpus as-of 2026-07-29 | liquid universe 958 tickers | CV boundary 2024-12-23

## T1 — universe pooled (net of round-trip costs)
- exp -1.262%/trade | N 899 | win 29.3% | **FAIL** (bar >= +0.50%, N >= 300)

## T2 — selection / chronological CV
- early-selected tickers: late exp -1.649% | late N 14 | early exp +0.802% | retention -2.05 | **FAIL** (bar >= +0.50%, N >= 150, retention >= 0.50)

## T3 — regime strata
- SIDEWAYS: exp -1.615% | N 507 | win 24.5% | **FAIL** (bar >= +0.50%, N >= 100)
- BEAR: exp -1.549% | N 140 | win 27.1% | **FAIL** (bar >= +0.50%, N >= 100)
- BULL: exp -0.390% | N 252 | win 40.1% | **FAIL** (bar >= +0.50%, N >= 100)

## DECISION: **DO-NOT-WIDEN**

```json
{
  "T1": {
    "exp_pct": -1.2615176179163208,
    "n": 899,
    "win_rate": 29.254727474972192,
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
      "exp_pct": -1.548543513024523,
      "n": 140,
      "win_rate": 27.142857142857142,
      "pass": false
    },
    "BULL": {
      "exp_pct": -0.39007941698559656,
      "n": 252,
      "win_rate": 40.07936507936508,
      "pass": false
    }
  },
  "widen_universe": false,
  "widen_sideways": false,
  "decision": "DO-NOT-WIDEN"
}
```
