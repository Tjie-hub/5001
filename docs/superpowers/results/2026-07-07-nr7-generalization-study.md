# NR7 Edge-Generalization Study — Results

Run: 2026-07-07T14:54:16 | corpus as-of 2026-07-07 | liquid universe 189 tickers | CV boundary 2024-12-23

## T1 — universe pooled (net of round-trip costs)
- exp -0.001%/trade | N 1129 | win 39.4% | **FAIL** (bar >= +0.50%, N >= 300)

## T2 — selection / chronological CV
- early-selected tickers: late exp +1.621% | late N 129 | early exp +2.626% | retention 0.62 | **FAIL** (bar >= +0.50%, N >= 150, retention >= 0.50)

## T3 — regime strata
- SIDEWAYS: exp -0.821% | N 625 | win 31.8% | **FAIL** (bar >= +0.50%, N >= 100)
- BEAR: exp +0.653% | N 158 | win 37.3% | **PASS** (bar >= +0.50%, N >= 100)
- BULL: exp +1.181% | N 346 | win 54.0% | **PASS** (bar >= +0.50%, N >= 100)

## DECISION: **DO-NOT-WIDEN**

```json
{
  "T1": {
    "exp_pct": -0.0013039726843129457,
    "n": 1129,
    "win_rate": 39.41541186891054,
    "pass": false
  },
  "T2": {
    "late_exp": 1.6213563176921229,
    "late_n": 129,
    "early_exp": 2.626166019212821,
    "retention": 0.6173853084041182,
    "pass": false
  },
  "T3": {
    "SIDEWAYS": {
      "exp_pct": -0.8213461640918557,
      "n": 625,
      "win_rate": 31.84,
      "pass": false
    },
    "BEAR": {
      "exp_pct": 0.652629902056925,
      "n": 158,
      "win_rate": 37.34177215189873,
      "pass": true
    },
    "BULL": {
      "exp_pct": 1.1813689100341802,
      "n": 346,
      "win_rate": 54.04624277456647,
      "pass": true
    }
  },
  "widen_universe": false,
  "widen_sideways": false,
  "decision": "DO-NOT-WIDEN"
}
```
