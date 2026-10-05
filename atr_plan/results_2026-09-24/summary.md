# Exit comparison v2 — 2026-09-24 15:10

Data: `data/history_long.db` · 444 tickers · trades 2000-05..2021-07 · min ADV Rp5bn · cost 0.6% (stress 0.8%) · cost filter False

Score = **xs** = net − equal-weight liquid-panel return over the same holding window (removes market + survivorship drift). `rand:` rows = same exits on random entry days.

## 1. Decision

EXIT_BETTER = beats A on xs in ≥70% of years AND 95% block-bootstrap CI of Δxs > 0, both same-bar conventions. BEATS_MKT = avg xs > 0 at 0.8% cost. ABS_PROFIT = avg raw net > 0 at 0.8% cost.

| Strategy | Var | EXIT_BETTER | BEATS_MKT (0.8%) | ABS_PROFIT (0.8%) |
|---|---|---|---|---|
| conservative | B | no | no | no |
| conservative | C | no | no | no |
| momentum | B | no | no | no |
| momentum | C | no | no | **YES** |
| nr7 | B | no | no | no |
| nr7 | C | **YES** | no | **YES** |
| rand:conservative | B | no | no | no |
| rand:conservative | C | no | no | no |
| rand:momentum | B | no | no | no |
| rand:momentum | C | **YES** | no | **YES** |
| rand:nr7 | B | no | no | no |
| rand:nr7 | C | **YES** | no | **YES** |
| rand:vol_weighted | B | no | no | no |
| rand:vol_weighted | C | no | no | **YES** |
| rand:vwap_rev | B | no | no | no |
| rand:vwap_rev | C | no | no | no |
| vol_weighted | B | no | no | no |
| vol_weighted | C | **YES** | no | **YES** |
| vwap_rev | B | no | no | no |
| vwap_rev | C | no | no | no |

## 2. Detail vs A (Δ on xs)

| Strategy | Var | Same-bar | Years | Win share | Δxs/trade | 95% CI | Δ raw net | bars A→V | xs V @0.8% |
|---|---|---|---|---|---|---|---|---|---|
| conservative | B | stop_first | 22 | 59% | +0.05% | [-0.04%, +0.13%] | +0.27% | 1.4→3.7 | -1.09% |
| conservative | C | stop_first | 22 | 59% | +0.05% | [-0.04%, +0.13%] | +0.27% | 1.4→3.7 | -1.09% |
| momentum | B | stop_first | 21 | 86% | +0.24% | [+0.09%, +0.39%] | +0.92% | 2.5→10.6 | -1.11% |
| momentum | C | stop_first | 21 | 76% | +0.74% | [+0.46%, +1.04%] | +2.45% | 2.5→15.8 | -0.60% |
| nr7 | B | stop_first | 21 | 86% | +0.69% | [+0.50%, +0.90%] | +1.49% | 2.3→11.6 | -1.54% |
| nr7 | C | stop_first | 21 | 90% | +1.23% | [+0.91%, +1.58%] | +2.93% | 2.3→17.0 | -1.00% |
| rand:conservative | B | stop_first | 22 | 68% | +0.08% | [+0.03%, +0.15%] | +0.24% | 1.5→4.0 | -1.04% |
| rand:conservative | C | stop_first | 22 | 68% | +0.08% | [+0.03%, +0.15%] | +0.24% | 1.5→4.0 | -1.04% |
| rand:momentum | B | stop_first | 21 | 43% | -0.04% | [-0.19%, +0.10%] | +0.54% | 3.2→11.9 | -1.27% |
| rand:momentum | C | stop_first | 21 | 76% | +0.53% | [+0.30%, +0.75%] | +1.77% | 3.2→12.6 | -0.69% |
| rand:nr7 | B | stop_first | 21 | 43% | +0.00% | [-0.12%, +0.13%] | +0.74% | 2.6→12.0 | -1.18% |
| rand:nr7 | C | stop_first | 21 | 76% | +0.54% | [+0.36%, +0.73%] | +1.92% | 2.6→13.0 | -0.64% |
| rand:vol_weighted | B | stop_first | 21 | 48% | -0.04% | [-0.20%, +0.12%] | +0.59% | 1.8→11.7 | -1.15% |
| rand:vol_weighted | C | stop_first | 21 | 81% | +0.50% | [+0.24%, +0.76%] | +1.86% | 1.8→12.1 | -0.61% |
| rand:vwap_rev | B | stop_first | 22 | 68% | +0.07% | [+0.00%, +0.14%] | +0.14% | 1.5→4.0 | -1.05% |
| rand:vwap_rev | C | stop_first | 22 | 68% | +0.07% | [+0.00%, +0.14%] | +0.14% | 1.5→4.0 | -1.05% |
| vol_weighted | B | stop_first | 21 | 86% | +0.29% | [+0.12%, +0.47%] | +0.88% | 1.3→10.2 | -1.09% |
| vol_weighted | C | stop_first | 21 | 81% | +1.24% | [+0.84%, +1.64%] | +2.82% | 1.3→14.1 | -0.14% |
| vwap_rev | B | stop_first | 22 | 68% | +0.13% | [+0.01%, +0.25%] | +0.22% | 1.3→3.9 | -1.05% |
| vwap_rev | C | stop_first | 22 | 68% | +0.13% | [+0.01%, +0.25%] | +0.22% | 1.3→3.9 | -1.05% |
| conservative | B | ohlc | 22 | 23% | -0.13% | [-0.22%, -0.05%] | +0.09% | 1.4→3.7 | -1.08% |
| conservative | C | ohlc | 22 | 23% | -0.13% | [-0.22%, -0.05%] | +0.09% | 1.4→3.7 | -1.08% |
| momentum | B | ohlc | 21 | 76% | +0.13% | [-0.01%, +0.28%] | +0.81% | 2.5→10.6 | -1.11% |
| momentum | C | ohlc | 21 | 67% | +0.64% | [+0.36%, +0.93%] | +2.34% | 2.5→15.8 | -0.60% |
| nr7 | B | ohlc | 21 | 62% | +0.16% | [-0.03%, +0.37%] | +0.94% | 2.5→11.6 | -1.53% |
| nr7 | C | ohlc | 21 | 76% | +0.70% | [+0.40%, +1.04%] | +2.38% | 2.5→17.0 | -1.00% |
| rand:conservative | B | ohlc | 22 | 27% | -0.10% | [-0.16%, -0.04%] | +0.06% | 1.5→4.0 | -1.03% |
| rand:conservative | C | ohlc | 22 | 27% | -0.10% | [-0.16%, -0.04%] | +0.06% | 1.5→4.0 | -1.03% |
| rand:momentum | B | ohlc | 21 | 38% | -0.09% | [-0.23%, +0.05%] | +0.50% | 3.2→11.9 | -1.26% |
| rand:momentum | C | ohlc | 21 | 76% | +0.49% | [+0.26%, +0.70%] | +1.72% | 3.2→12.6 | -0.69% |
| rand:nr7 | B | ohlc | 21 | 38% | -0.06% | [-0.19%, +0.06%] | +0.68% | 2.6→12.0 | -1.18% |
| rand:nr7 | C | ohlc | 21 | 71% | +0.48% | [+0.29%, +0.66%] | +1.86% | 2.6→13.0 | -0.64% |
| rand:vol_weighted | B | ohlc | 21 | 33% | -0.17% | [-0.33%, -0.02%] | +0.46% | 1.8→11.7 | -1.15% |
| rand:vol_weighted | C | ohlc | 21 | 67% | +0.37% | [+0.11%, +0.62%] | +1.72% | 1.8→12.1 | -0.61% |
| rand:vwap_rev | B | ohlc | 22 | 27% | -0.12% | [-0.19%, -0.05%] | -0.05% | 1.5→4.0 | -1.05% |
| rand:vwap_rev | C | ohlc | 22 | 27% | -0.12% | [-0.19%, -0.05%] | -0.05% | 1.5→4.0 | -1.05% |
| vol_weighted | B | ohlc | 21 | 57% | -0.00% | [-0.18%, +0.18%] | +0.58% | 1.3→10.2 | -1.09% |
| vol_weighted | C | ohlc | 21 | 71% | +0.95% | [+0.53%, +1.34%] | +2.52% | 1.3→14.1 | -0.14% |
| vwap_rev | B | ohlc | 22 | 45% | -0.12% | [-0.25%, -0.00%] | -0.03% | 1.3→3.9 | -1.04% |
| vwap_rev | C | ohlc | 22 | 45% | -0.12% | [-0.25%, -0.00%] | -0.03% | 1.3→3.9 | -1.04% |

## 3. Per-trade, same-bar = stop_first (0.6% cost)

| Strategy | Var | Trades | Win% | Avg net | Avg bench | Avg xs | Avg bars | Stopped ≤2 bars |
|---|---|---|---|---|---|---|---|---|
| conservative | A | 32797 | 38% | -0.79% | +0.15% | -0.94% | 1.4 | 58% |
| conservative | B | 32797 | 45% | -0.52% | +0.37% | -0.89% | 3.7 | 13% |
| conservative | C | 32797 | 45% | -0.52% | +0.37% | -0.89% | 3.7 | 13% |
| momentum | A | 21189 | 37% | -0.86% | +0.29% | -1.14% | 2.5 | 46% |
| momentum | B | 21189 | 45% | +0.06% | +0.97% | -0.91% | 10.6 | 6% |
| momentum | C | 21189 | 35% | +1.59% | +1.99% | -0.40% | 15.8 | 5% |
| nr7 | A | 16973 | 27% | -1.40% | +0.62% | -2.03% | 2.3 | 59% |
| nr7 | B | 16973 | 45% | +0.08% | +1.42% | -1.34% | 11.6 | 3% |
| nr7 | C | 16973 | 34% | +1.53% | +2.33% | -0.80% | 17.0 | 2% |
| rand:conservative | A | 32796 | 39% | -0.84% | +0.08% | -0.92% | 1.5 | 56% |
| rand:conservative | B | 32796 | 44% | -0.59% | +0.24% | -0.84% | 4.0 | 10% |
| rand:conservative | C | 32796 | 44% | -0.59% | +0.24% | -0.84% | 4.0 | 10% |
| rand:momentum | A | 21189 | 39% | -0.82% | +0.21% | -1.02% | 3.2 | 40% |
| rand:momentum | B | 21189 | 43% | -0.27% | +0.79% | -1.07% | 11.9 | 4% |
| rand:momentum | C | 21189 | 33% | +0.95% | +1.44% | -0.49% | 12.6 | 3% |
| rand:nr7 | A | 40734 | 38% | -0.79% | +0.19% | -0.98% | 2.6 | 46% |
| rand:nr7 | B | 40734 | 44% | -0.05% | +0.93% | -0.98% | 12.0 | 4% |
| rand:nr7 | C | 40734 | 34% | +1.13% | +1.57% | -0.44% | 13.0 | 3% |
| rand:vol_weighted | A | 14763 | 40% | -0.84% | +0.08% | -0.91% | 1.8 | 52% |
| rand:vol_weighted | B | 14763 | 43% | -0.25% | +0.71% | -0.95% | 11.7 | 5% |
| rand:vol_weighted | C | 14763 | 33% | +1.02% | +1.43% | -0.41% | 12.1 | 3% |
| rand:vwap_rev | A | 24578 | 38% | -0.87% | +0.05% | -0.92% | 1.5 | 57% |
| rand:vwap_rev | B | 24578 | 43% | -0.73% | +0.12% | -0.85% | 4.0 | 10% |
| rand:vwap_rev | C | 24578 | 43% | -0.73% | +0.12% | -0.85% | 4.0 | 10% |
| vol_weighted | A | 14762 | 36% | -0.98% | +0.20% | -1.18% | 1.3 | 61% |
| vol_weighted | B | 14762 | 44% | -0.11% | +0.78% | -0.89% | 10.2 | 6% |
| vol_weighted | C | 14762 | 34% | +1.84% | +1.78% | +0.06% | 14.1 | 5% |
| vwap_rev | A | 24575 | 37% | -0.92% | +0.06% | -0.98% | 1.3 | 60% |
| vwap_rev | B | 24575 | 44% | -0.70% | +0.15% | -0.85% | 3.9 | 11% |
| vwap_rev | C | 24575 | 44% | -0.70% | +0.15% | -0.85% | 3.9 | 11% |

## 3. Per-trade, same-bar = ohlc (0.6% cost)

| Strategy | Var | Trades | Win% | Avg net | Avg bench | Avg xs | Avg bars | Stopped ≤2 bars |
|---|---|---|---|---|---|---|---|---|
| conservative | A | 32797 | 44% | -0.60% | +0.15% | -0.75% | 1.4 | 53% |
| conservative | B | 32797 | 45% | -0.51% | +0.37% | -0.88% | 3.7 | 12% |
| conservative | C | 32797 | 45% | -0.51% | +0.37% | -0.88% | 3.7 | 12% |
| momentum | A | 21189 | 39% | -0.75% | +0.29% | -1.04% | 2.5 | 45% |
| momentum | B | 21189 | 45% | +0.07% | +0.97% | -0.91% | 10.6 | 6% |
| momentum | C | 21189 | 35% | +1.59% | +1.99% | -0.40% | 15.8 | 5% |
| nr7 | A | 16973 | 38% | -0.85% | +0.65% | -1.50% | 2.5 | 45% |
| nr7 | B | 16973 | 45% | +0.09% | +1.42% | -1.33% | 11.6 | 3% |
| nr7 | C | 16973 | 34% | +1.53% | +2.33% | -0.79% | 17.0 | 2% |
| rand:conservative | A | 32796 | 44% | -0.65% | +0.08% | -0.73% | 1.5 | 51% |
| rand:conservative | B | 32796 | 44% | -0.59% | +0.24% | -0.83% | 4.0 | 10% |
| rand:conservative | C | 32796 | 44% | -0.59% | +0.24% | -0.83% | 4.0 | 10% |
| rand:momentum | A | 21189 | 39% | -0.77% | +0.21% | -0.98% | 3.2 | 39% |
| rand:momentum | B | 21189 | 43% | -0.27% | +0.79% | -1.07% | 11.9 | 4% |
| rand:momentum | C | 21189 | 33% | +0.95% | +1.44% | -0.49% | 12.6 | 3% |
| rand:nr7 | A | 40734 | 39% | -0.72% | +0.19% | -0.91% | 2.6 | 45% |
| rand:nr7 | B | 40734 | 44% | -0.05% | +0.93% | -0.98% | 12.0 | 4% |
| rand:nr7 | C | 40734 | 34% | +1.13% | +1.57% | -0.44% | 13.0 | 3% |
| rand:vol_weighted | A | 14763 | 43% | -0.71% | +0.08% | -0.78% | 1.8 | 49% |
| rand:vol_weighted | B | 14763 | 43% | -0.25% | +0.71% | -0.95% | 11.7 | 5% |
| rand:vol_weighted | C | 14763 | 33% | +1.02% | +1.43% | -0.41% | 12.1 | 3% |
| rand:vwap_rev | A | 24578 | 44% | -0.68% | +0.05% | -0.73% | 1.5 | 52% |
| rand:vwap_rev | B | 24578 | 43% | -0.73% | +0.12% | -0.85% | 4.0 | 10% |
| rand:vwap_rev | C | 24578 | 43% | -0.73% | +0.12% | -0.85% | 4.0 | 10% |
| vol_weighted | A | 14762 | 43% | -0.68% | +0.20% | -0.88% | 1.3 | 54% |
| vol_weighted | B | 14762 | 44% | -0.11% | +0.78% | -0.89% | 10.2 | 6% |
| vol_weighted | C | 14762 | 34% | +1.84% | +1.78% | +0.06% | 14.1 | 5% |
| vwap_rev | A | 24575 | 44% | -0.66% | +0.06% | -0.72% | 1.3 | 53% |
| vwap_rev | B | 24575 | 44% | -0.69% | +0.15% | -0.84% | 3.9 | 11% |
| vwap_rev | C | 24575 | 44% | -0.69% | +0.15% | -0.84% | 3.9 | 11% |

## 4. Portfolio (realized P&L, max 5 positions, same-bar = ohlc, 0.6% cost)

Benchmark EW liquid panel, same span: CAGR +12.68% · Sharpe 0.56 · Max DD -70.38%

| Strategy | Setup | Trades | CAGR | Sharpe (monthly) | Max DD |
|---|---|---|---|---|---|
| vol_weighted | A fixed, 20% notional | 8884 | -45.16% | -3.43 | -100.00% |
| vol_weighted | B, 20% notional | 1914 | -6.26% | -0.05 | -92.49% |
| vol_weighted | C, 20% notional | 1550 | +16.56% | 0.62 | -85.52% |
| vol_weighted | D = C + ATR sizing | 1550 | +10.04% | 0.75 | -46.66% |
| momentum | A fixed, 20% notional | 7696 | -39.53% | -1.10 | -100.00% |
| momentum | B, 20% notional | 2114 | -1.14% | 0.13 | -86.97% |
| momentum | C, 20% notional | 1516 | +21.83% | 0.72 | -68.14% |
| momentum | D = C + ATR sizing | 1516 | +10.62% | 0.75 | -34.82% |
| vwap_rev | A fixed, 20% notional | 12795 | -56.42% | -4.70 | -100.00% |
| vwap_rev | B, 20% notional | 5066 | -36.70% | -1.62 | -99.99% |
| vwap_rev | C, 20% notional | 5066 | -36.70% | -1.62 | -99.99% |
| vwap_rev | D = C + ATR sizing | 4981 | -19.31% | -1.64 | -98.98% |
| conservative | A fixed, 20% notional | 13643 | -56.67% | -4.80 | -100.00% |
| conservative | B, 20% notional | 5649 | -26.56% | -1.39 | -99.85% |
| conservative | C, 20% notional | 5649 | -26.56% | -1.39 | -99.85% |
| conservative | D = C + ATR sizing | 5601 | -19.69% | -1.59 | -99.00% |
| nr7 | A fixed, 20% notional | 7076 | -46.90% | -3.02 | -100.00% |
| nr7 | B, 20% notional | 1817 | -2.26% | 0.03 | -93.72% |
| nr7 | C, 20% notional | 1369 | +12.86% | 0.59 | -64.73% |
| nr7 | D = C + ATR sizing | 1369 | +7.33% | 0.65 | -29.67% |
| rand:vol_weighted | A fixed, 20% notional | 8865 | -44.79% | -3.60 | -100.00% |
| rand:vol_weighted | B, 20% notional | 1892 | -2.76% | 0.09 | -89.46% |
| rand:vol_weighted | C, 20% notional | 2174 | +12.22% | 0.55 | -67.40% |
| rand:vol_weighted | D = C + ATR sizing | 2174 | +8.62% | 0.72 | -28.75% |
| rand:momentum | A fixed, 20% notional | 7228 | -42.76% | -2.70 | -100.00% |
| rand:momentum | B, 20% notional | 1959 | -1.56% | 0.12 | -82.27% |
| rand:momentum | C, 20% notional | 2401 | +7.58% | 0.37 | -84.35% |
| rand:momentum | D = C + ATR sizing | 2401 | +4.94% | 0.41 | -56.65% |
| rand:vwap_rev | A fixed, 20% notional | 13340 | -57.81% | -5.16 | -100.00% |
| rand:vwap_rev | B, 20% notional | 5567 | -29.84% | -1.18 | -99.95% |
| rand:vwap_rev | C, 20% notional | 5567 | -29.84% | -1.18 | -99.95% |
| rand:vwap_rev | D = C + ATR sizing | 5532 | -18.33% | -1.39 | -98.59% |
| rand:conservative | A fixed, 20% notional | 14706 | -58.35% | -5.29 | -100.00% |
| rand:conservative | B, 20% notional | 5527 | -27.51% | -1.06 | -99.90% |
| rand:conservative | C, 20% notional | 5527 | -27.51% | -1.06 | -99.90% |
| rand:conservative | D = C + ATR sizing | 5515 | -17.11% | -1.28 | -98.09% |
| rand:nr7 | A fixed, 20% notional | 10051 | -50.57% | -3.57 | -100.00% |
| rand:nr7 | B, 20% notional | 2061 | -0.82% | 0.16 | -79.67% |
| rand:nr7 | C, 20% notional | 2775 | +3.41% | 0.25 | -91.17% |
| rand:nr7 | D = C + ATR sizing | 2775 | +1.93% | 0.21 | -68.96% |

## 5. Exit reasons (% of trades, same-bar = ohlc)

|                     |   eod |   gap_stop |   gap_tp |   max_hold |   stop |   time |   tp |   trail |
|:--------------------|------:|-----------:|---------:|-----------:|-------:|-------:|-----:|--------:|
| conservative/A      |     0 |          3 |        3 |          0 |     54 |      0 |   41 |       0 |
| conservative/B      |     0 |          4 |        6 |          0 |     25 |     39 |   26 |       0 |
| conservative/C      |     0 |          4 |        6 |          0 |     25 |     39 |   26 |       0 |
| momentum/A          |     0 |          6 |        5 |          1 |     54 |      0 |   34 |       0 |
| momentum/B          |     0 |          8 |        6 |         21 |     37 |      0 |   28 |       0 |
| momentum/C          |     0 |          5 |        0 |          3 |     25 |      0 |    0 |      66 |
| nr7/A               |     0 |          8 |        5 |          0 |     54 |      0 |   33 |       0 |
| nr7/B               |     0 |          8 |        7 |         24 |     34 |      0 |   27 |       0 |
| nr7/C               |     0 |          5 |        0 |          3 |     21 |      0 |    0 |      70 |
| rand:conservative/A |     0 |          3 |        3 |          0 |     52 |      0 |   41 |       0 |
| rand:conservative/B |     0 |          4 |        5 |          0 |     21 |     48 |   22 |       0 |
| rand:conservative/C |     0 |          4 |        5 |          0 |     21 |     48 |   22 |       0 |
| rand:momentum/A     |     0 |          8 |        6 |          1 |     52 |      0 |   32 |       0 |
| rand:momentum/B     |     0 |          8 |        6 |         27 |     35 |      0 |   24 |       0 |
| rand:momentum/C     |     0 |          3 |        0 |          3 |     14 |      0 |    0 |      80 |
| rand:nr7/A          |     0 |          7 |        6 |          1 |     54 |      0 |   33 |       0 |
| rand:nr7/B          |     0 |          8 |        7 |         28 |     33 |      0 |   24 |       0 |
| rand:nr7/C          |     0 |          3 |        0 |          3 |     14 |      0 |    0 |      80 |
| rand:vol_weighted/A |     0 |          3 |        3 |          0 |     54 |      0 |   40 |       0 |
| rand:vol_weighted/B |     1 |          5 |        3 |         27 |     38 |      0 |   26 |       0 |
| rand:vol_weighted/C |     1 |          2 |        0 |          2 |     14 |      0 |    0 |      81 |
| rand:vwap_rev/A     |     0 |          3 |        3 |          0 |     53 |      0 |   41 |       0 |
| rand:vwap_rev/B     |     0 |          4 |        5 |          0 |     22 |     48 |   21 |       0 |
| rand:vwap_rev/C     |     0 |          4 |        5 |          0 |     22 |     48 |   21 |       0 |
| vol_weighted/A      |     0 |          1 |        1 |          0 |     56 |      0 |   42 |       0 |
| vol_weighted/B      |     0 |          4 |        2 |         20 |     41 |      0 |   31 |       0 |
| vol_weighted/C      |     1 |          2 |        0 |          2 |     26 |      0 |    0 |      69 |
| vwap_rev/A          |     0 |          2 |        2 |          0 |     53 |      0 |   42 |       0 |
| vwap_rev/B          |     0 |          5 |        5 |          0 |     23 |     45 |   22 |       0 |
| vwap_rev/C          |     0 |          5 |        5 |          0 |     23 |     45 |   22 |       0 |

Notes: entries identical across variants (strict pairing). Random control enters at next open (also for nr7, whose real entry is a buy-stop). Mean-reversion C = B. Portfolio uses raw net.