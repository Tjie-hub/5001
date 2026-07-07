# Regime-Conditional Edge Scan — Results

Run: 2026-07-07T16:28:15 | corpus as-of 2026-07-07 | liquid universe 183 tickers | bar +0.50% net, N>=100 (T3), late N>=60 (CV)

## Matrix — pooled net expectancy per (strategy, regime)

| strategy | BULL | SIDEWAYS | BEAR |
|---|---|---|---|
| vol_weighted | -0.63% (N2299,32%) | -1.11% (N3942,27%) | -0.85% (N868,29%) |
| momentum | -0.31% (N1590,32%) | -1.18% (N2700,26%) | -0.69% (N534,31%) |
| vwap_reversion | -0.57% (N363,37%) | -0.94% (N6912,29%) | -0.76% (N3349,31%) |
| conservative | -1.07% (N3260,28%) | -1.24% (N5767,23%) | -1.85% (N530,20%) |
| Volume Profile POC | -1.18% (N201,35%) | -0.95% (N998,34%) | -0.56% (N168,25%) |
| Inside Bar Breakout | +0.41% (N227,37%) | -1.12% (N548,26%) | -1.79% (N154,23%) |
| NR7 Breakout | +1.18% (N346,54%)✓? | -0.84% (N628,32%) | +0.65% (N158,37%) |
| ORB | -1.00% (N736,40%) | -0.85% (N2229,41%) | -0.69% (N366,36%) |
| VWMA Breakout Pullback | -0.40% (N40,35%) | -1.33% (N169,24%) | +0.83% (N17,35%) |
| Swing Trend | +4.53% (N20,35%) | -0.59% (N78,35%) | — |
| Trend Following Breakout | +3.38% (N539,36%) | +2.71% (N396,34%) | — |
| Crash Recovery | — | — | — |
| Panic Rebound | +8.43% (N4,75%) | -4.95% (N5,40%) | -2.31% (N20,50%) |
| Liquidity Sweep | -0.23% (N1408,32%) | -1.23% (N4119,25%) | -0.71% (N1273,30%) |

Legend: ✓✓ CONFIRMED · ✓? PROMISING (thin CV) · blank REJECTED

## CV detail (cells clearing the +0.50%/N>=100 regime bar)

- **NR7 Breakout / BULL** [PROMISING]: cell +1.18% N346 | late +4.72% N6 | early +8.97% | retention 0.53
- **NR7 Breakout / BEAR** [REJECTED]: cell +0.65% N158 | late +0.00% N0 | early +0.00% | retention 0.00
- **Trend Following Breakout / BULL** [REJECTED]: cell +3.38% N539 | late -7.20% N8 | early +5.02% | retention -1.43
- **Trend Following Breakout / SIDEWAYS** [REJECTED]: cell +2.71% N396 | late +0.00% N0 | early +0.00% | retention 0.00

## CONFIRMED candidates (ranked)
- none

## PROMISING candidates (thin CV — SHADOW to gather data)
- NR7 Breakout / BULL: +1.18% net (N346, win 54%)

```json
{
  "vol_weighted": {
    "BULL": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": -0.628655306832043,
      "n": 2299,
      "win_rate": 31.57894736842105,
      "late_exp": -0.9558111265214336,
      "late_n": 160,
      "early_exp": 1.4088408176224694,
      "retention": -0.6784379857296019
    },
    "SIDEWAYS": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": -1.112511705899787,
      "n": 3942,
      "win_rate": 27.270421106037546,
      "late_exp": -1.1691599894312896,
      "late_n": 331,
      "early_exp": 1.252920255497248,
      "retention": -0.933147967160355
    },
    "BEAR": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": -0.8455678061604677,
      "n": 868,
      "win_rate": 29.493087557603687,
      "late_exp": -3.7833924817362345,
      "late_n": 16,
      "early_exp": 2.1498965723157624,
      "retention": -1.7598020902284388
    }
  },
  "momentum": {
    "BULL": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": -0.3102852103061482,
      "n": 1590,
      "win_rate": 32.20125786163522,
      "late_exp": 0.43449458454035833,
      "late_n": 114,
      "early_exp": 1.8493806110704243,
      "retention": 0.23494059683521404
    },
    "SIDEWAYS": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": -1.1787118229698408,
      "n": 2700,
      "win_rate": 26.14814814814815,
      "late_exp": -1.6680595975594832,
      "late_n": 181,
      "early_exp": 0.9162691032125942,
      "retention": -1.8204909362445862
    },
    "BEAR": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": -0.6891579583276374,
      "n": 534,
      "win_rate": 31.46067415730337,
      "late_exp": 2.9678214142762505,
      "late_n": 1,
      "early_exp": 0.2695696969684056,
      "retention": 11.009477132083166
    }
  },
  "vwap_reversion": {
    "BULL": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": -0.5715764611109536,
      "n": 363,
      "win_rate": 36.63911845730028,
      "late_exp": 0.7563716639087052,
      "late_n": 7,
      "early_exp": 1.389833415690001,
      "retention": 0.5442174978453764
    },
    "SIDEWAYS": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": -0.9433871169511989,
      "n": 6912,
      "win_rate": 29.12326388888889,
      "late_exp": -1.1260502257352383,
      "late_n": 751,
      "early_exp": 0.7435685612037193,
      "retention": -1.5143865468334783
    },
    "BEAR": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": -0.7610990240091009,
      "n": 3349,
      "win_rate": 31.29292326067483,
      "late_exp": -0.28784904054692706,
      "late_n": 290,
      "early_exp": 1.011926693999216,
      "retention": -0.2844564159181575
    }
  },
  "conservative": {
    "BULL": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": -1.0669320141649206,
      "n": 3260,
      "win_rate": 27.73006134969325,
      "late_exp": -0.5527056215234463,
      "late_n": 195,
      "early_exp": 1.2966063733940454,
      "retention": -0.42627094302850244
    },
    "SIDEWAYS": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": -1.2373089946029492,
      "n": 5767,
      "win_rate": 23.478411652505635,
      "late_exp": -1.4188536707429849,
      "late_n": 178,
      "early_exp": 0.6013038947936069,
      "retention": -2.359628272871899
    },
    "BEAR": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": -1.851105328543686,
      "n": 530,
      "win_rate": 20.0,
      "late_exp": -1.2049987303593905,
      "late_n": 3,
      "early_exp": 0.29771295445864254,
      "retention": -4.047518632672686
    }
  },
  "Volume Profile POC": {
    "BULL": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": -1.1819422242055126,
      "n": 201,
      "win_rate": 35.32338308457712,
      "late_exp": 0.0,
      "late_n": 0,
      "early_exp": 0.0,
      "retention": 0.0
    },
    "SIDEWAYS": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": -0.9450060472315507,
      "n": 998,
      "win_rate": 33.567134268537075,
      "late_exp": -1.5834288633275175,
      "late_n": 37,
      "early_exp": 0.774338478588137,
      "retention": -2.0448794772727905
    },
    "BEAR": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": -0.5596521781557873,
      "n": 168,
      "win_rate": 25.0,
      "late_exp": 0.0,
      "late_n": 0,
      "early_exp": 0.0,
      "retention": 0.0
    }
  },
  "Inside Bar Breakout": {
    "BULL": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": 0.40850178908932555,
      "n": 227,
      "win_rate": 37.44493392070485,
      "late_exp": 0.0,
      "late_n": 0,
      "early_exp": 0.0,
      "retention": 0.0
    },
    "SIDEWAYS": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": -1.119780764207246,
      "n": 548,
      "win_rate": 25.912408759124087,
      "late_exp": 0.0,
      "late_n": 0,
      "early_exp": 1.7122330225811424,
      "retention": 0.0
    },
    "BEAR": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": -1.7941976615288349,
      "n": 154,
      "win_rate": 22.727272727272727,
      "late_exp": 0.0,
      "late_n": 0,
      "early_exp": 0.0,
      "retention": 0.0
    }
  },
  "NR7 Breakout": {
    "BULL": {
      "state": "PROMISING",
      "regime_pass": true,
      "exp_pct": 1.1813689100341802,
      "n": 346,
      "win_rate": 54.04624277456647,
      "late_exp": 4.717150824138847,
      "late_n": 6,
      "early_exp": 8.965474576695453,
      "retention": 0.5261462495694815
    },
    "SIDEWAYS": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": -0.8350565943908529,
      "n": 628,
      "win_rate": 31.84713375796178,
      "late_exp": -0.11060213425508983,
      "late_n": 10,
      "early_exp": 1.054472516409082,
      "retention": -0.10488858887639495
    },
    "BEAR": {
      "state": "REJECTED",
      "regime_pass": true,
      "exp_pct": 0.652629902056925,
      "n": 158,
      "win_rate": 37.34177215189873,
      "late_exp": 0.0,
      "late_n": 0,
      "early_exp": 0.0,
      "retention": 0.0
    }
  },
  "ORB": {
    "BULL": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": -1.002504834783995,
      "n": 736,
      "win_rate": 39.80978260869565,
      "late_exp": -0.9191559993505275,
      "late_n": 28,
      "early_exp": 1.9965407125815726,
      "retention": -0.46037428315801177
    },
    "SIDEWAYS": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": -0.8507170354840013,
      "n": 2229,
      "win_rate": 40.5114401076716,
      "late_exp": -1.2463296161986563,
      "late_n": 261,
      "early_exp": 1.3239436854281303,
      "retention": -0.9413766083227508
    },
    "BEAR": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": -0.6858762960042124,
      "n": 366,
      "win_rate": 36.0655737704918,
      "late_exp": 0.0,
      "late_n": 0,
      "early_exp": 0.0,
      "retention": 0.0
    }
  },
  "VWMA Breakout Pullback": {
    "BULL": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": -0.3968243404640789,
      "n": 40,
      "win_rate": 35.0,
      "late_exp": 0.0,
      "late_n": 0,
      "early_exp": 0.0,
      "retention": 0.0
    },
    "SIDEWAYS": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": -1.3273879760032927,
      "n": 169,
      "win_rate": 24.2603550295858,
      "late_exp": 0.0,
      "late_n": 0,
      "early_exp": 0.0,
      "retention": 0.0
    },
    "BEAR": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": 0.8269116725518153,
      "n": 17,
      "win_rate": 35.294117647058826,
      "late_exp": 0.0,
      "late_n": 0,
      "early_exp": 0.0,
      "retention": 0.0
    }
  },
  "Swing Trend": {
    "BULL": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": 4.5285081305960775,
      "n": 20,
      "win_rate": 35.0,
      "late_exp": 0.0,
      "late_n": 0,
      "early_exp": 0.0,
      "retention": 0.0
    },
    "SIDEWAYS": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": -0.5906638371498111,
      "n": 78,
      "win_rate": 34.61538461538461,
      "late_exp": 0.0,
      "late_n": 0,
      "early_exp": 0.0,
      "retention": 0.0
    }
  },
  "Trend Following Breakout": {
    "BULL": {
      "state": "REJECTED",
      "regime_pass": true,
      "exp_pct": 3.3815469782531555,
      "n": 539,
      "win_rate": 35.62152133580705,
      "late_exp": -7.1960119082547065,
      "late_n": 8,
      "early_exp": 5.0195588625974095,
      "retention": -1.4335944861359937
    },
    "SIDEWAYS": {
      "state": "REJECTED",
      "regime_pass": true,
      "exp_pct": 2.711499236221338,
      "n": 396,
      "win_rate": 33.83838383838384,
      "late_exp": 0.0,
      "late_n": 0,
      "early_exp": 0.0,
      "retention": 0.0
    }
  },
  "Crash Recovery": {},
  "Panic Rebound": {
    "BULL": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": 8.429033697070153,
      "n": 4,
      "win_rate": 75.0,
      "late_exp": 0.0,
      "late_n": 0,
      "early_exp": 0.0,
      "retention": 0.0
    },
    "SIDEWAYS": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": -4.947229992901553,
      "n": 5,
      "win_rate": 40.0,
      "late_exp": 0.0,
      "late_n": 0,
      "early_exp": 0.0,
      "retention": 0.0
    },
    "BEAR": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": -2.305062820511081,
      "n": 20,
      "win_rate": 50.0,
      "late_exp": 0.0,
      "late_n": 0,
      "early_exp": 0.0,
      "retention": 0.0
    }
  },
  "Liquidity Sweep": {
    "BULL": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": -0.22983599003015198,
      "n": 1408,
      "win_rate": 31.605113636363637,
      "late_exp": 0.21752094042294132,
      "late_n": 106,
      "early_exp": 2.708871487870431,
      "retention": 0.0802994683937349
    },
    "SIDEWAYS": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": -1.2257405906768273,
      "n": 4119,
      "win_rate": 25.34595775673707,
      "late_exp": -1.4048426279009443,
      "late_n": 368,
      "early_exp": 1.520951491679746,
      "retention": -0.9236603768009916
    },
    "BEAR": {
      "state": "REJECTED",
      "regime_pass": false,
      "exp_pct": -0.7090929952908013,
      "n": 1273,
      "win_rate": 29.772191673212884,
      "late_exp": -0.6026637373872611,
      "late_n": 124,
      "early_exp": 2.023111038405348,
      "retention": -0.29788959970397444
    }
  }
}
```
