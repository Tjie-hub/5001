# VERDICT — exit & position management on the owner's sniper entry (G1, the single run)

**Run:** `RESULT_20261006T142027Z.json` · 2026-10-06 14:20:27 UTC (21:20 WIB) · runtime 156.9 s ·
git `c483886c380377c9b4d8ab196c4306e28f09a141` (`research/exit-study-2026-10`) ·
gate `EXIT_STUDY_G1_APPROVED=1` (owner approval of G0-ter, 2026-10-06).
**Freeze verified at run time AND at commit:** `PREDECLARATION.md` `d722e0f1…40c0`,
`exit_study.py` `2c4f0c92…fab3`, `test_pit_exit_study.py` `516072cd…a7d5` (sidecar, all three OK).
**Data:** fingerprint `f42275e34cb4525d…` (max_date 2026-10-06, 1,101,826 rows) — **identical to
the G0-ter census fingerprint** (the DB did not change between census and G1; zero drift).
**Populations (owner screen ADV20 ≥ Rp 10bn):** E-SN 3,682 fills · E-RND 3,682 matched controls ·
E-BRK 5,141 signals — **exactly the G0-ter census counts** (cross-check passed).

## Headline

- **P4 (swing lot) is the ONLY arm RECOMMENDED over its baseline** by the frozen rule
  (both eras: higher expectancy in R, paired t ≥ 2.0, drawdown guard) — on the sniper entry
  (E1 t **+4.26**, E2 t **+3.25**) **and independently on the random-entry control**
  (E1 +3.23, E2 +3.46). Expectancy E-SN: E1 +0.002R (P0) → **+0.125R** (P4); E2 −0.043R →
  **+0.004R**. Mean net% per trade: E1 +0.20% → +0.76%; E2 −0.21% → +0.32%.
- **All nine other non-baseline arms: NO_RELIABLE_DIFFERENCE.** No arm was flagged harmful
  (X5 came closest on E1 alone: t −2.07, but E2 is +1.43).
- **The owner's current plan (X1: structure stop + resistance target) does not reliably beat
  simply holding 20 sessions (X0):** E1 t −2.00 (slightly WORSE in discovery), E2 t +1.50
  (better, sub-threshold). See the portfolio caveat below for why X0's better per-trade
  averages must not be read as "drop the stop".
- **Does the sniper entry itself add anything (E-SN vs E-RND, paired per arm)?** In E1, yes —
  t +4.23 under X1/P0 management (and +1.68 under X0). In E2 the edge is positive but
  sub-threshold (+1.08). Random-entry controls lose money under the same management in BOTH
  eras (E1 −0.19R, E2 −0.11R under X1); the sniper entry roughly breaks even.
- **Averaging down (P2): no reliable improvement** — E1 t +3.18 but E2 t +1.50; win rate
  unchanged (54.0% → 54.0%), worst-5% tail slightly LESS bad (−17.4% → −16.0%), expectancy
  −0.015R → −0.002R. The small gain is cost-averaging into the stop, not an edge. Details below.

## Reading notes (mechanical caveats on the portfolio columns)

1. **X0 and X2 equal-risk portfolios go BUST** (no stop / a stop looser than the sizing risk):
   equity turns negative mid-era, so their `cagr` is null and `max_dd`/`worst_12m` are
   meaningless magnitudes (e.g. E1 X0 final equity −2.1e8 from 1.0). Any `dd_ok` comparison
   involving X0 or X2 is void. This IS the finding for unstopped variants: the per-trade
   averages look good, the loss tail is unbounded under 1%-risk sizing.
2. **The five P-arms share X1's portfolio numbers exactly** — the frozen portfolio model sees
   only the core entry/stop/exit (single-exit approximation; the P-legs are intra-trade adds).
   Their drawdown guard is therefore trivially satisfied, and the per-trade paired tests are
   the discriminator for position arms. (Verified: identical exits — P4's core exit reasons
   equal X1's trade-for-trade.)
3. MAE columns live in the RESULT (deciles per arm/era); exit-reason mixes are in the RESULT
   `metrics[arm]["reasons"]`.

## Tables (rendered mechanically from the RESULT; no hand transcription)
| metric table | n | mean net% | median net% | expectancy R | win rate | avg win% | avg loss% | mean hold |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| E_SN E1 X0 | 2253 | 0.92% | -0.60% | 0.60 | 48.2% | 11.54% | -8.94% | 20.0 |
| E_SN E1 X1 | 2253 | 0.20% | 0.80% | 0.00 | 54.5% | 5.59% | -6.24% | 6.0 |
| E_SN E1 X2 | 2253 | -0.07% | -4.58% | 0.65 | 43.9% | 11.91% | -9.44% | 16.3 |
| E_SN E1 X3 | 2253 | 1.09% | -4.10% | 0.18 | 29.2% | 17.82% | -5.81% | 16.5 |
| E_SN E1 X4 | 2253 | 0.78% | -1.54% | 0.08 | 33.3% | 9.82% | -3.74% | 6.9 |
| E_SN E1 X5 | 2253 | 0.06% | 0.62% | -0.02 | 54.2% | 4.71% | -5.44% | 4.2 |
| E_SN E1 X6 | 2253 | 0.55% | 2.88% | 0.59 | 75.9% | 6.25% | -17.44% | 22.9 |
| E_SN E1 P0 | 2253 | 0.20% | 0.80% | 0.00 | 54.5% | 5.59% | -6.24% | 6.0 |
| E_SN E1 P1 | 2253 | 0.78% | 0.86% | 0.10 | 54.6% | 6.01% | -5.52% | 6.0 |
| E_SN E1 P2 | 2253 | 0.48% | 0.84% | 0.02 | 54.5% | 5.73% | -5.82% | 6.0 |
| E_SN E1 P3 | 2253 | -0.22% | 0.79% | -0.00 | 54.3% | 5.02% | -6.45% | 6.0 |
| E_SN E1 P4 | 2253 | 0.76% | 0.83% | 0.13 | 54.7% | 6.42% | -6.07% | 6.0 |
| E_SN E2 X0 | 1429 | -0.68% | -2.15% | -0.20 | 42.5% | 16.38% | -13.27% | 19.8 |
| E_SN E2 X1 | 1429 | -0.21% | 0.60% | -0.04 | 53.3% | 7.29% | -8.76% | 5.5 |
| E_SN E2 X2 | 1429 | -1.58% | -6.66% | -0.24 | 38.7% | 17.37% | -13.55% | 17.1 |
| E_SN E2 X3 | 1429 | -1.22% | -5.71% | -0.11 | 22.1% | 22.95% | -8.09% | 14.3 |
| E_SN E2 X4 | 1429 | -0.61% | -2.70% | -0.09 | 28.1% | 11.14% | -5.21% | 5.6 |
| E_SN E2 X5 | 1429 | -0.26% | 0.53% | -0.05 | 52.7% | 6.33% | -7.60% | 3.9 |
| E_SN E2 X6 | 1429 | -0.27% | 2.52% | -0.20 | 72.3% | 8.68% | -23.59% | 22.9 |
| E_SN E2 P0 | 1429 | -0.21% | 0.60% | -0.04 | 53.3% | 7.29% | -8.76% | 5.5 |
| E_SN E2 P1 | 1429 | 0.65% | 0.77% | -0.04 | 53.5% | 7.92% | -7.73% | 5.5 |
| E_SN E2 P2 | 1429 | 0.17% | 0.62% | -0.04 | 53.3% | 7.42% | -8.10% | 5.5 |
| E_SN E2 P3 | 1429 | -0.82% | 0.60% | -0.04 | 53.3% | 6.41% | -9.06% | 5.5 |
| E_SN E2 P4 | 1429 | 0.32% | 0.73% | 0.00 | 53.9% | 7.98% | -8.63% | 5.5 |
| E_RND E1 X0 | 2252 | 0.05% | -0.60% | 0.00 | 46.4% | 11.45% | -9.85% | 20.0 |
| E_RND E1 X1 | 2252 | -0.43% | -2.07% | -0.19 | 46.4% | 5.97% | -5.97% | 6.7 |
| E_RND E1 X2 | 2252 | -0.50% | -5.35% | 0.08 | 41.3% | 12.01% | -9.32% | 16.2 |
| E_RND E1 X3 | 2252 | 0.15% | -4.08% | -0.02 | 26.6% | 16.58% | -5.79% | 15.8 |
| E_RND E1 X4 | 2253 | 0.39% | -1.72% | 0.02 | 28.0% | 10.66% | -3.60% | 6.0 |
| E_RND E1 X5 | 2252 | -0.54% | -1.03% | -0.20 | 45.7% | 5.02% | -5.22% | 4.6 |
| E_RND E1 X6 | 2252 | -0.57% | 2.66% | -0.16 | 72.8% | 6.41% | -19.23% | 25.7 |
| E_RND E1 P0 | 2252 | -0.43% | -2.07% | -0.19 | 46.4% | 5.97% | -5.97% | 6.7 |
| E_RND E1 P1 | 2252 | 0.20% | -1.98% | -0.20 | 46.7% | 6.40% | -5.23% | 6.7 |
| E_RND E1 P2 | 2252 | -0.11% | -2.00% | -0.18 | 46.5% | 6.14% | -5.54% | 6.7 |
| E_RND E1 P3 | 2252 | -0.85% | -2.14% | -0.19 | 46.3% | 5.27% | -6.14% | 6.7 |
| E_RND E1 P4 | 2252 | -0.04% | -1.95% | -0.12 | 46.8% | 6.64% | -5.91% | 6.7 |
| E_RND E2 X0 | 1428 | -1.37% | -3.27% | -0.13 | 39.0% | 16.42% | -12.74% | 19.7 |
| E_RND E2 X1 | 1429 | -0.68% | -2.81% | -0.11 | 45.6% | 7.68% | -7.67% | 6.3 |
| E_RND E2 X2 | 1429 | -1.88% | -6.49% | -0.21 | 37.7% | 16.08% | -12.75% | 17.4 |
| E_RND E2 X3 | 1428 | -0.45% | -5.43% | 0.03 | 22.0% | 24.90% | -7.60% | 14.8 |
| E_RND E2 X4 | 1428 | -0.52% | -2.32% | -0.07 | 26.1% | 10.84% | -4.52% | 4.8 |
| E_RND E2 X5 | 1429 | -0.63% | -0.60% | -0.09 | 46.5% | 6.31% | -6.67% | 4.3 |
| E_RND E2 X6 | 1429 | -1.03% | 2.24% | -0.20 | 68.9% | 7.81% | -20.57% | 24.9 |
| E_RND E2 P0 | 1429 | -0.68% | -2.81% | -0.11 | 45.6% | 7.68% | -7.67% | 6.3 |
| E_RND E2 P1 | 1429 | 0.16% | -2.44% | -0.10 | 46.1% | 8.24% | -6.74% | 6.3 |
| E_RND E2 P2 | 1429 | -0.23% | -2.70% | -0.11 | 45.6% | 7.90% | -7.05% | 6.3 |
| E_RND E2 P3 | 1429 | -1.21% | -2.90% | -0.10 | 45.4% | 6.83% | -7.90% | 6.3 |
| E_RND E2 P4 | 1429 | -0.14% | -2.20% | -0.03 | 46.1% | 8.50% | -7.53% | 6.3 |
| E_BRK E1 X0 | 3128 | 2.54% | 0.13% | 0.35 | 50.4% | 14.42% | -9.55% | 20.0 |
| E_BRK E1 X1 | 3129 | -0.01% | -0.60% | -0.01 | 45.6% | 5.03% | -4.23% | 4.4 |
| E_BRK E1 X2 | 3128 | 0.35% | -4.50% | 0.02 | 44.6% | 10.82% | -8.07% | 10.6 |
| E_BRK E1 X3 | 3129 | 1.49% | -4.29% | 0.18 | 34.8% | 17.27% | -6.93% | 16.1 |
| E_BRK E1 X4 | 3129 | 2.38% | -3.62% | 0.28 | 33.7% | 19.35% | -6.25% | 13.6 |
| E_BRK E1 X5 | 3129 | -0.23% | -0.60% | -0.04 | 43.8% | 4.33% | -3.79% | 3.3 |
| E_BRK E1 X6 | 3128 | 0.27% | 0.51% | 0.02 | 56.7% | 5.34% | -6.36% | 13.2 |
| E_BRK E1 P0 | 3129 | -0.01% | -0.60% | -0.01 | 45.6% | 5.03% | -4.23% | 4.4 |
| E_BRK E1 P1 | 3129 | 0.76% | 0.34% | 0.06 | 54.0% | 4.91% | -4.12% | 4.4 |
| E_BRK E1 P2 | 3129 | 0.34% | -0.60% | 0.00 | 46.0% | 5.26% | -3.85% | 4.4 |
| E_BRK E1 P3 | 3129 | -0.27% | -0.60% | 0.01 | 45.3% | 4.64% | -4.35% | 4.4 |
| E_BRK E1 P4 | 3129 | 0.74% | -0.40% | 0.11 | 46.0% | 6.45% | -4.13% | 4.4 |
| E_BRK E2 X0 | 2011 | -0.28% | -3.58% | -0.04 | 40.0% | 20.99% | -14.48% | 19.9 |
| E_BRK E2 X1 | 2012 | -1.38% | -0.60% | -0.16 | 42.4% | 4.79% | -5.93% | 3.6 |
| E_BRK E2 X2 | 2012 | -1.22% | -6.29% | -0.14 | 37.4% | 13.58% | -10.05% | 9.4 |
| E_BRK E2 X3 | 2010 | -0.33% | -6.19% | -0.05 | 27.5% | 22.16% | -8.85% | 13.1 |
| E_BRK E2 X4 | 2011 | 0.89% | -5.61% | 0.07 | 26.6% | 26.10% | -8.25% | 11.5 |
| E_BRK E2 X5 | 2012 | -1.27% | -0.60% | -0.15 | 41.8% | 4.58% | -5.48% | 2.9 |
| E_BRK E2 X6 | 2012 | -2.02% | 0.21% | -0.22 | 53.1% | 5.17% | -10.16% | 14.1 |
| E_BRK E2 P0 | 2012 | -1.38% | -0.60% | -0.16 | 42.4% | 4.79% | -5.93% | 3.6 |
| E_BRK E2 P1 | 2012 | -0.36% | -0.05% | -0.11 | 49.8% | 5.05% | -5.72% | 3.6 |
| E_BRK E2 P2 | 2012 | -0.91% | -0.60% | -0.15 | 42.8% | 5.13% | -5.44% | 3.6 |
| E_BRK E2 P3 | 2012 | -1.62% | -0.60% | -0.17 | 42.3% | 4.45% | -6.08% | 3.6 |
| E_BRK E2 P4 | 2012 | -0.54% | -0.60% | -0.07 | 43.1% | 6.28% | -5.71% | 3.6 |

Portfolio (equal-risk, 1% risk, max 10 concurrent):
| population | era | arm | CAGR | max DD | worst 12m | n_taken/n_signals | final equity |
|---|---|---|---:|---:|---:|---:|---:|
| E_SN | E1 | X0 | — | -1557981097.7% | -39889054574.2% | 204/2253 | -206213252.87 |
| E_SN | E1 | X1 | 13.67% | -89.2% | -86.8% | 43/2253 | 29.40 |
| E_SN | E1 | X2 | — | -1369017111.6% | -58084380601.6% | 213/2253 | -633182508.88 |
| E_SN | E1 | X3 | 13.57% | -83.5% | -82.5% | 120/2253 | 28.71 |
| E_SN | E1 | X4 | 10.99% | -90.3% | -88.7% | 116/2253 | 15.67 |
| E_SN | E1 | X5 | 13.64% | -89.7% | -87.2% | 44/2253 | 29.19 |
| E_SN | E1 | X6 | 15.37% | -87.4% | -83.7% | 79/2253 | 43.51 |
| E_SN | E1 | P0 | 13.67% | -89.2% | -86.8% | 43/2253 | 29.40 |
| E_SN | E1 | P1 | 13.67% | -89.2% | -86.8% | 43/2253 | 29.40 |
| E_SN | E1 | P2 | 13.67% | -89.2% | -86.8% | 43/2253 | 29.40 |
| E_SN | E1 | P3 | 13.67% | -89.2% | -86.8% | 43/2253 | 29.40 |
| E_SN | E1 | P4 | 13.67% | -89.2% | -86.8% | 43/2253 | 29.40 |
| E_SN | E2 | X0 | — | -47704074119.0% | -340996460116.5% | 373/1429 | -454017397.09 |
| E_SN | E2 | X1 | 2.66% | -76.2% | -64.2% | 40/1429 | 2.00 |
| E_SN | E2 | X2 | — | -150923813731.0% | -249072847728.9% | 340/1429 | -956762413776632576.00 |
| E_SN | E2 | X3 | -0.99% | -96.4% | -79.6% | 296/1429 | 0.77 |
| E_SN | E2 | X4 | — | -141.3% | -432221.8% | 254/1429 | -0.98 |
| E_SN | E2 | X5 | 1.96% | -80.0% | -69.2% | 39/1429 | 1.67 |
| E_SN | E2 | X6 | -1.10% | -75.0% | -55.6% | 42/1429 | 0.75 |
| E_SN | E2 | P0 | 2.66% | -76.2% | -64.2% | 40/1429 | 2.00 |
| E_SN | E2 | P1 | 2.66% | -76.2% | -64.2% | 40/1429 | 2.00 |
| E_SN | E2 | P2 | 2.66% | -76.2% | -64.2% | 40/1429 | 2.00 |
| E_SN | E2 | P3 | 2.66% | -76.2% | -64.2% | 40/1429 | 2.00 |
| E_SN | E2 | P4 | 2.66% | -76.2% | -64.2% | 40/1429 | 2.00 |
| E_RND | E1 | X0 | — | -3860745981.5% | -805310826788.9% | 237/2253 | -8883816999.81 |
| E_RND | E1 | X1 | 15.08% | -81.1% | -75.3% | 32/2253 | 40.73 |
| E_RND | E1 | X2 | — | -4152099669.9% | -106250929917.5% | 210/2253 | -1889236327.75 |
| E_RND | E1 | X3 | 15.35% | -84.1% | -79.0% | 78/2253 | 43.30 |
| E_RND | E1 | X4 | 14.79% | -76.1% | -70.8% | 61/2253 | 38.07 |
| E_RND | E1 | X5 | 14.97% | -81.2% | -75.3% | 32/2253 | 39.71 |
| E_RND | E1 | X6 | 15.12% | -80.7% | -78.0% | 46/2253 | 41.10 |
| E_RND | E1 | P0 | 15.08% | -81.1% | -75.3% | 32/2253 | 40.73 |
| E_RND | E1 | P1 | 15.08% | -81.1% | -75.3% | 32/2253 | 40.73 |
| E_RND | E1 | P2 | 15.08% | -81.1% | -75.3% | 32/2253 | 40.73 |
| E_RND | E1 | P3 | 15.08% | -81.1% | -75.3% | 32/2253 | 40.73 |
| E_RND | E1 | P4 | 15.08% | -81.1% | -75.3% | 32/2253 | 40.73 |
| E_RND | E2 | X0 | — | -217532499078.8% | -315358908019.8% | 137/1429 | -2944525524.67 |
| E_RND | E2 | X1 | 5.35% | -55.0% | -38.2% | 41/1429 | 3.95 |
| E_RND | E2 | X2 | — | -245052021228.4% | -790172148810.3% | 184/1429 | -2842649962.15 |
| E_RND | E2 | X3 | 125.13% | -4183868074.2% | -5542479674.6% | 113/1429 | 1988367559.57 |
| E_RND | E2 | X4 | — | -1336.0% | -2048530187218.5% | 150/1429 | -38069317518.96 |
| E_RND | E2 | X5 | -0.28% | -77.9% | -63.4% | 52/1429 | 0.93 |
| E_RND | E2 | X6 | 0.03% | -76.5% | -62.9% | 43/1429 | 1.01 |
| E_RND | E2 | P0 | 5.35% | -55.0% | -38.2% | 41/1429 | 3.95 |
| E_RND | E2 | P1 | 5.35% | -55.0% | -38.2% | 41/1429 | 3.95 |
| E_RND | E2 | P2 | 5.35% | -55.0% | -38.2% | 41/1429 | 3.95 |
| E_RND | E2 | P3 | 5.35% | -55.0% | -38.2% | 41/1429 | 3.95 |
| E_RND | E2 | P4 | 5.35% | -55.0% | -38.2% | 41/1429 | 3.95 |
| E_BRK | E1 | X0 | — | — | — | 1426/3129 | — |
| E_BRK | E1 | X1 | 14.41% | -89.7% | -83.8% | 23/3129 | 34.86 |
| E_BRK | E1 | X2 | 12.49% | -81.2% | -76.4% | 63/3129 | 22.31 |
| E_BRK | E1 | X3 | 10.67% | -89.5% | -86.8% | 145/3129 | 14.51 |
| E_BRK | E1 | X4 | 9.02% | -82.5% | -79.1% | 172/3129 | 9.77 |
| E_BRK | E1 | X5 | 14.34% | -89.7% | -83.8% | 23/3129 | 34.30 |
| E_BRK | E1 | X6 | 13.97% | -85.6% | -77.4% | 22/3129 | 31.53 |
| E_BRK | E1 | P0 | 14.41% | -89.7% | -83.8% | 23/3129 | 34.86 |
| E_BRK | E1 | P1 | 14.41% | -89.7% | -83.8% | 23/3129 | 34.86 |
| E_BRK | E1 | P2 | 14.41% | -89.7% | -83.8% | 23/3129 | 34.86 |
| E_BRK | E1 | P3 | 14.41% | -89.7% | -83.8% | 23/3129 | 34.86 |
| E_BRK | E1 | P4 | 14.41% | -89.7% | -83.8% | 23/3129 | 34.86 |
| E_BRK | E2 | X0 | — | — | — | 567/2012 | — |
| E_BRK | E2 | X1 | 3.01% | -54.0% | -41.3% | 14/2012 | 2.19 |
| E_BRK | E2 | X2 | 2.72% | -75.4% | -64.2% | 186/2012 | 2.03 |
| E_BRK | E2 | X3 | -0.41% | -78.3% | -52.4% | 373/2012 | 0.90 |
| E_BRK | E2 | X4 | -0.77% | -80.4% | -55.1% | 292/2012 | 0.82 |
| E_BRK | E2 | X5 | 3.01% | -54.0% | -41.3% | 14/2012 | 2.19 |
| E_BRK | E2 | X6 | 3.01% | -54.0% | -41.3% | 14/2012 | 2.19 |
| E_BRK | E2 | P0 | 3.01% | -54.0% | -41.3% | 14/2012 | 2.19 |
| E_BRK | E2 | P1 | 3.01% | -54.0% | -41.3% | 14/2012 | 2.19 |
| E_BRK | E2 | P2 | 3.01% | -54.0% | -41.3% | 14/2012 | 2.19 |
| E_BRK | E2 | P3 | 3.01% | -54.0% | -41.3% | 14/2012 | 2.19 |
| E_BRK | E2 | P4 | 3.01% | -54.0% | -41.3% | 14/2012 | 2.19 |

Paired vs baseline (paired difference t on matched trades, H1: arm > baseline):
| population | era | arm | paired t (R) | mean R diff | n matched |
|---|---|---|---:|---:|---:|
| E_SN | E1 | X1 | -2.00 | -0.59 | 2253 |
| E_SN | E1 | X2 | +0.23 | 0.06 | 2253 |
| E_SN | E1 | X3 | -1.40 | -0.41 | 2253 |
| E_SN | E1 | X4 | -1.73 | -0.51 | 2253 |
| E_SN | E1 | X5 | -2.07 | -0.61 | 2253 |
| E_SN | E1 | X6 | -0.02 | -0.01 | 2253 |
| E_SN | E1 | P1 | +3.13 | 0.10 | 2253 |
| E_SN | E1 | P2 | +3.18 | 0.02 | 2253 |
| E_SN | E1 | P3 | -0.33 | -0.00 | 2253 |
| E_SN | E1 | P4 | +4.26 | 0.12 | 2253 |
| E_SN | E2 | X1 | +1.50 | 0.16 | 1429 |
| E_SN | E2 | X2 | -0.47 | -0.04 | 1429 |
| E_SN | E2 | X3 | +0.89 | 0.09 | 1429 |
| E_SN | E2 | X4 | +1.15 | 0.11 | 1429 |
| E_SN | E2 | X5 | +1.43 | 0.15 | 1429 |
| E_SN | E2 | X6 | -0.08 | -0.01 | 1429 |
| E_SN | E2 | P1 | +0.08 | 0.00 | 1429 |
| E_SN | E2 | P2 | +1.50 | 0.01 | 1429 |
| E_SN | E2 | P3 | +0.79 | 0.01 | 1429 |
| E_SN | E2 | P4 | +3.25 | 0.05 | 1429 |
| E_RND | E1 | X1 | -0.43 | -0.19 | 2253 |
| E_RND | E1 | X2 | +0.34 | 0.08 | 2253 |
| E_RND | E1 | X3 | -0.04 | -0.02 | 2253 |
| E_RND | E1 | X4 | +0.03 | 0.01 | 2253 |
| E_RND | E1 | X5 | -0.46 | -0.20 | 2253 |
| E_RND | E1 | X6 | -0.92 | -0.16 | 2253 |
| E_RND | E1 | P1 | -0.72 | -0.02 | 2253 |
| E_RND | E1 | P2 | +1.91 | 0.01 | 2253 |
| E_RND | E1 | P3 | -0.99 | -0.01 | 2253 |
| E_RND | E1 | P4 | +3.23 | 0.06 | 2253 |
| E_RND | E2 | X1 | +0.10 | 0.02 | 1429 |
| E_RND | E2 | X2 | -0.52 | -0.08 | 1429 |
| E_RND | E2 | X3 | +0.94 | 0.16 | 1429 |
| E_RND | E2 | X4 | +0.36 | 0.06 | 1429 |
| E_RND | E2 | X5 | +0.19 | 0.03 | 1429 |
| E_RND | E2 | X6 | -0.59 | -0.08 | 1429 |
| E_RND | E2 | P1 | +0.32 | 0.01 | 1429 |
| E_RND | E2 | P2 | -0.51 | -0.00 | 1429 |
| E_RND | E2 | P3 | +0.53 | 0.01 | 1429 |
| E_RND | E2 | P4 | +3.46 | 0.08 | 1429 |
| E_BRK | E1 | X1 | -8.03 | -0.37 | 3129 |
| E_BRK | E1 | X2 | -8.31 | -0.33 | 3129 |
| E_BRK | E1 | X3 | -4.65 | -0.17 | 3129 |
| E_BRK | E1 | X4 | -1.92 | -0.07 | 3129 |
| E_BRK | E1 | X5 | -8.69 | -0.39 | 3129 |
| E_BRK | E1 | X6 | -7.15 | -0.34 | 3129 |
| E_BRK | E1 | P1 | +5.18 | 0.08 | 3129 |
| E_BRK | E1 | P2 | +2.18 | 0.01 | 3129 |
| E_BRK | E1 | P3 | +2.77 | 0.02 | 3129 |
| E_BRK | E1 | P4 | +6.01 | 0.13 | 3129 |
| E_BRK | E2 | X1 | -1.97 | -0.12 | 2012 |
| E_BRK | E2 | X2 | -1.89 | -0.11 | 2012 |
| E_BRK | E2 | X3 | -0.18 | -0.01 | 2012 |
| E_BRK | E2 | X4 | +1.90 | 0.11 | 2012 |
| E_BRK | E2 | X5 | -1.86 | -0.11 | 2012 |
| E_BRK | E2 | X6 | -3.00 | -0.18 | 2012 |
| E_BRK | E2 | P1 | +3.45 | 0.05 | 2012 |
| E_BRK | E2 | P2 | +0.90 | 0.01 | 2012 |
| E_BRK | E2 | P3 | -1.62 | -0.01 | 2012 |
| E_BRK | E2 | P4 | +4.92 | 0.09 | 2012 |

Frozen recommendation rule (both eras: expectancy higher AND paired t >= 2.0 AND max DD not worse by >20% relative):
| E_SN arm | verdict | E1 t | E1 expHigher | E1 dd_ok | E2 t | E2 expHigher | E2 dd_ok |
|---|---|---:|---|---|---:|---|---|
| X1 | **NO_RELIABLE_DIFFERENCE** | -2.00 | False | True | +1.50 | True | True |
| X2 | **NO_RELIABLE_DIFFERENCE** | +0.23 | True | True | -0.47 | False | False |
| X3 | **NO_RELIABLE_DIFFERENCE** | -1.40 | False | True | +0.89 | True | True |
| X4 | **NO_RELIABLE_DIFFERENCE** | -1.73 | False | True | +1.15 | True | True |
| X5 | **NO_RELIABLE_DIFFERENCE** | -2.07 | False | True | +1.43 | True | True |
| X6 | **NO_RELIABLE_DIFFERENCE** | -0.02 | False | True | -0.08 | False | True |
| P1 | **NO_RELIABLE_DIFFERENCE** | +3.13 | True | True | +0.08 | True | True |
| P2 | **NO_RELIABLE_DIFFERENCE** | +3.18 | True | True | +1.50 | True | True |
| P3 | **NO_RELIABLE_DIFFERENCE** | -0.33 | False | True | +0.79 | True | True |
| P4 | **RECOMMENDED** | +4.26 | True | True | +3.25 | True | True |
| E_RND arm | verdict | E1 t | E1 expHigher | E1 dd_ok | E2 t | E2 expHigher | E2 dd_ok |
|---|---|---:|---|---|---:|---|---|
| X1 | **NO_RELIABLE_DIFFERENCE** | -0.43 | False | True | +0.10 | True | True |
| X2 | **NO_RELIABLE_DIFFERENCE** | +0.34 | True | True | -0.52 | False | True |
| X3 | **NO_RELIABLE_DIFFERENCE** | -0.04 | False | True | +0.94 | True | True |
| X4 | **NO_RELIABLE_DIFFERENCE** | +0.03 | True | True | +0.36 | True | True |
| X5 | **NO_RELIABLE_DIFFERENCE** | -0.46 | False | True | +0.19 | True | True |
| X6 | **NO_RELIABLE_DIFFERENCE** | -0.92 | False | True | -0.59 | False | True |
| P1 | **NO_RELIABLE_DIFFERENCE** | -0.72 | False | True | +0.32 | True | True |
| P2 | **NO_RELIABLE_DIFFERENCE** | +1.91 | True | True | -0.51 | False | True |
| P3 | **NO_RELIABLE_DIFFERENCE** | -0.99 | False | True | +0.53 | True | True |
| P4 | **RECOMMENDED** | +3.23 | True | True | +3.46 | True | True |

E-SN vs E-RND per arm (does the sniper entry itself add anything; paired on matched controls):
| arm | era | paired t (R) | n matched |
|---|---|---:|---:|
| X0 | E1 | +1.68 | 2253 |
| X0 | E2 | -0.36 | 1429 |
| X1 | E1 | +4.23 | 2253 |
| X1 | E2 | +1.08 | 1429 |
| X2 | E1 | +2.25 | 2253 |
| X2 | E2 | -0.36 | 1429 |
| X3 | E1 | +2.26 | 2253 |
| X3 | E2 | -1.08 | 1429 |
| X4 | E1 | +0.87 | 2253 |
| X4 | E2 | -0.18 | 1429 |
| X5 | E1 | +4.41 | 2253 |
| X5 | E2 | +0.76 | 1429 |
| X6 | E1 | +2.43 | 2253 |
| X6 | E2 | -0.00 | 1429 |
| P0 | E1 | +4.23 | 2253 |
| P0 | E2 | +1.08 | 1429 |
| P1 | E1 | +3.88 | 2253 |
| P1 | E2 | +0.50 | 1429 |
| P2 | E1 | +4.11 | 2253 |
| P2 | E2 | +1.21 | 1429 |
| P3 | E1 | +3.63 | 2253 |
| P3 | E2 | +0.90 | 1429 |
| P4 | E1 | +4.14 | 2253 |
| P4 | E2 | +0.57 | 1429 |

P2 (averaging down) worst-5% tail question vs P0:
| population | arm | worst-5% mean net% | win rate | expectancy R |
|---|---|---:|---:|---:|
| E_SN | P0 | -17.38% | 54.0% | -0.02 |
| E_SN | P2 | -16.00% | 54.0% | -0.00 |
| E_RND | P0 | -16.13% | 46.1% | -0.16 |
| E_RND | P2 | -14.79% | 46.2% | -0.15 |

Year-by-year mean net% (E_SN, owner screen; full per-arm/per-era tables in the RESULT):
| year | X0 | X1 | X2 | X3 | X4 | X5 | X6 | P0 | P1 | P2 | P3 | P4 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2001 | -6.0% | -2.7% | -10.4% | -6.6% | -3.9% | -2.7% | 5.9% | -2.7% | -1.9% | -2.7% | -2.7% | -2.7% |
| 2002 | 6.6% | 0.4% | 1.3% | 5.1% | 2.0% | 1.2% | -4.3% | 0.4% | 0.9% | 0.4% | -0.8% | 0.4% |
| 2003 | 1.4% | 3.2% | 3.2% | 1.5% | -2.0% | -0.5% | 7.6% | 3.2% | 4.0% | 3.7% | 2.3% | 3.2% |
| 2004 | 4.1% | 2.6% | 4.5% | 3.3% | 1.1% | 0.5% | 3.8% | 2.6% | 3.5% | 3.3% | 1.9% | 2.6% |
| 2005 | 0.5% | -0.0% | -0.5% | 2.3% | 0.5% | -0.3% | -0.5% | -0.0% | 0.6% | 0.2% | -0.5% | 0.7% |
| 2006 | 1.5% | 2.4% | 2.3% | 3.0% | -0.1% | 1.6% | 3.5% | 2.4% | 2.8% | 2.6% | 1.8% | 4.3% |
| 2007 | 2.4% | 0.4% | 0.3% | 4.5% | 2.4% | 0.5% | 2.7% | 0.4% | 0.9% | 0.5% | -0.3% | 1.2% |
| 2008 | -3.1% | -0.8% | -3.2% | -2.0% | -1.3% | -0.5% | -9.3% | -0.8% | -0.3% | -0.7% | -1.3% | 1.8% |
| 2009 | 4.4% | 1.2% | 2.4% | 1.0% | 0.4% | 0.8% | 4.1% | 1.2% | 1.7% | 1.4% | 0.8% | 2.7% |
| 2010 | 1.1% | 1.8% | 1.0% | -0.3% | 0.4% | 1.6% | 1.9% | 1.8% | 2.3% | 2.0% | 1.3% | 1.8% |
| 2011 | 1.5% | 0.9% | 0.9% | 2.2% | 0.4% | 0.2% | 2.9% | 0.9% | 1.3% | 1.0% | 0.4% | 0.9% |
| 2012 | 1.5% | 1.1% | 1.5% | 1.3% | 1.7% | 1.1% | 2.9% | 1.1% | 1.5% | 1.2% | 0.6% | 1.4% |
| 2013 | -1.6% | 0.4% | -0.3% | 0.9% | 0.2% | 0.3% | -3.2% | 0.4% | 1.0% | 0.6% | -0.0% | 0.4% |
| 2014 | 2.1% | 0.6% | 1.3% | 0.6% | 0.5% | 0.6% | 2.5% | 0.6% | 1.1% | 0.8% | 0.3% | 1.4% |
| 2015 | -2.2% | -0.8% | -2.6% | -2.1% | -1.3% | -0.7% | -4.5% | -0.8% | -0.3% | -0.5% | -1.0% | 0.6% |
| 2016 | 1.7% | -0.5% | 0.9% | 2.3% | 1.1% | -0.3% | 0.3% | -0.5% | 0.1% | -0.2% | -0.7% | 0.0% |
| 2017 | 0.7% | -1.0% | -0.8% | 0.4% | 1.4% | -0.5% | -0.5% | -1.0% | -0.4% | -0.6% | -1.3% | -0.6% |
| 2018 | -1.3% | -1.2% | -3.3% | -0.8% | -1.7% | -1.2% | -2.9% | -1.2% | -0.8% | -1.0% | -1.5% | -1.2% |
| 2019 | -1.7% | -0.7% | -2.8% | -2.5% | -0.6% | -0.8% | -0.1% | -0.7% | -0.1% | -0.3% | -1.0% | -0.6% |
| 2020 | 6.0% | 1.2% | 2.3% | 7.4% | 7.7% | 1.3% | 1.6% | 1.2% | 1.7% | 1.4% | 0.5% | 2.2% |
| 2021 | 2.9% | 2.7% | 0.5% | 1.6% | 0.3% | 1.8% | 3.4% | 2.7% | 3.6% | 3.0% | 1.7% | 5.1% |
| 2022 | -1.7% | 0.2% | -0.8% | -0.7% | -0.9% | -0.2% | -0.7% | 0.2% | 0.9% | 0.6% | -0.5% | 1.2% |
| 2023 | -2.3% | -1.2% | -2.3% | -1.8% | -1.2% | -1.1% | -2.7% | -1.2% | -0.5% | -0.8% | -1.4% | -1.1% |
| 2024 | -0.2% | -0.4% | -0.5% | -1.4% | 0.1% | 0.2% | -1.3% | -0.4% | 0.2% | -0.2% | -0.9% | 0.1% |
| 2025 | 5.6% | 0.8% | 1.9% | 2.5% | 1.9% | 0.8% | 2.3% | 0.8% | 1.9% | 1.2% | -0.1% | 1.1% |
| 2026 | -7.8% | -2.1% | -7.8% | -6.8% | -3.8% | -2.1% | -1.9% | -2.1% | -1.1% | -1.8% | -2.5% | -2.1% |

\* paired t `n/a` = fewer than 3 matched pairs, or zero-variance differences (the frozen paired_t returns ±inf there; serialized as null).

## Reading the recommendation table

- **P4 (swing lot), the one adoption:** core at the zone top; after a close ≥ entry + 1·ATR,
  a 50% top-up at entry − 0.5·ATR (limit), sold at its own entry + 1.5·ATR (or with the core).
  Mean R advantage vs P0: **+0.123R (E1), +0.048R (E2)**, t +4.26/+3.25 on 2,253/1,429 matched
  trades. It also improves the RANDOM-entry control (E_RND mean net% E1 −0.43% → −0.04%,
  E2 −0.68% → −0.14%; t +3.23/+3.46): the overlay monetizes the pullback-rebound after an
  initial thrust on these liquid names, largely independent of entry quality. That it clears
  the both-eras bar on two entry populations (four thresholds) is the strongest pattern in
  this study.
- **Exit arms:** none of X1..X6 clears the bar vs X0. X1 (the owner's plan) is −2.00/+1.50 —
  the structure stop+target roughly converts the X0 profile (median −0.60%, win 48%) into a
  smaller-swing profile (median +0.80%, win 55%) without changing expectancy reliably.
  X3 (chandelier) and X4 (MA20) cut win rates to 29%/33% for higher averages — no reliable
  expectancy gain. X6 (target-only, no stop) wins 76% of trades in E1 with a −17.4% average
  loss tail and a negative E2; indistinguishable from X0 (t −0.02/−0.08).
- **Era honesty:** E2 (2021-10..2026-09) is a weak regime for this whole entry complex —
  X1's portfolio CAGR 13.7% (E1) vs 2.7% (E2); the E-SN-vs-E-RND entry edge shrinks from
  t +4.23 to +1.08. P4 is the only arm whose E2 expectancy stays at/above zero.
- **E-BRK is reported, never recommended** (frozen): 20-day-high breakouts held 20 sessions
  (X0) made +2.54%/trade in E1 (expR +0.35) and −0.28% in E2 — an observation, not advice.

## The P2 (averaging down) question, answered

Frozen question: does P2 raise expectancy, or only the win rate, with a fatter loss tail?
**Answer: none of the three.** Win rate is unchanged (54.0% → 54.0% E_SN whole-sample);
the worst-5% tail is slightly LESS bad (−17.38% → −16.00%); expectancy improves marginally
(−0.015R → −0.002R) — a cost-averaging artifact of buying 50% more at −1·ATR above the same
stop, and it fails the frozen both-eras rule (E2 t +1.50 < 2.0). **Do not adopt P2.**

## Disclosures

1. **Known parity residue (~5%), no re-freeze.** Planner parity check vs the real jurnal26
   code: 58/61 real setups identical within rounding; 3 differ — **FIMP 2022-10-06,
   EMTK 2025-01-15, TBLA 2023-07-25** — attributable to rounding of group means/levels or the
   5-bar window edge. Recorded here as a known residue per the planner's instruction; the
   freeze was NOT reopened.
2. **Post-run mechanical repair of the RESULT file.** The runner's JSON sanitizer missed
   plain-Python integers, serializing 1,529 integer values as digit-strings. A lossless
   values-only type repair (digit-string → int; keys untouched; zero recomputation) was
   applied to `RESULT_20261006T142027Z.json` after the run. The run itself is unchanged and
   was executed exactly once; `g1_run.py` and `gen_verdict.py` are committed for provenance.
3. **Benign runtime warnings, frozen code:** an All-NaN-slice warning in TR for pre-listing
   stubs, and the CAGR scalar-power warning on the negative X0/X2 curves (documented in
   Reading notes 1).
4. **Multiplicity honesty (PREDECLARATION §9):** 10 non-baseline arms × 2 entry populations ×
   2 eras of paired comparisons; at t ≥ 2.0 roughly one in twenty thresholds false-positives.
   P4 is the only arm clearing all four of its thresholds; the study is exploratory decision
   support for the owner's own trading, NOT a registered claim, consumes no family slot, and
   is not filed in FAILURE_REGISTRY.
5. **Era/population mechanics as frozen:** eras by SIGNAL month (E1 to 2021-09, E2 from
   2021-10, signals after 2026-09 counted out-of-window and never enrolled); 60-session
   arm-independent fill lock; costs 0.15% buy + 0.25% sell + 0.20% slippage round trip;
   conventions C-1..C-10 unchanged through G0 → G0-bis → G0-ter (three freezes, sidecar
   verified at run time and at this commit).

## Provenance

- Command (run once, background, 156.9 s):
  `DB_PATH=… EXIT_STUDY_HIST_PKL=… EXIT_STUDY_SPLITS_PKL=… EXIT_STUDY_G1_APPROVED=1
  venv/bin/python docs/research_programs/P-M/exit_study/g1_run.py`
  (full env in HANDOFF_G1.md; data access read-only — PKLs + `mode=ro` DB for the fingerprint).
- Numbers in this file come from `_verdict_tables.md`, rendered mechanically from the RESULT
  by `gen_verdict.py`; narrative figures were quoted programmatically from the same file.
- G1 is DONE. Per the brief: **no re-runs with changed settings.**

---

# P4 fix and G1-bis (2026-10-07)

**Authority:** brief `ZCODE_BRIEF_EXIT_STUDY_P4_FIX_2026-10-07.md` (owner-approved 2026-10-07)
after planner review of `HANDOFF_G1BIS_STOP.md`. **This addendum SUPERSEDES G1's P4 rows
(trade metrics, paired tests, E-SN-vs-E-RND P4 row) and ALL of G1's portfolio tables above —
they are kept for the record, not deleted. Everything else in G1 stands: the population
machinery, every non-P4 arm, the P2 tail question and the exit-arm conclusions are
bit-identical to the G1 run (gate below).**

The frozen driver's day-loop carried a bottom-of-loop P4 fill block that could only ever fire
on the arming day (the in-step next-session path runs first on any later day), "filling" the
top-up limit at the arming day's own low — a price printed before the arming close that placed
the order (look-ahead) — and booking no buy leg, so the top-up sale booked phantom proceeds.
Per the brief, the block was **deleted** (not fixed) in `exit_study.py::simulate_trade` and
`portfolio_v2.py::simulate_legs`; the frozen rule's own text ("top-up of 50% at entry − 0.5·ATR
**limit, from the next session**", PREDECLARATION §6) already forbade the same-day fill.
Disclosed as **Amendment 2026-10-07** in PREDECLARATION §6, with a same-day regression test in
both test files; re-frozen at commit `006ef6a` (sidecars `PREDECLARATION.md`
`2ccbd25a…e0f2d`, `exit_study.py` `6b29b92c…c2bc`, `test_pit_exit_study.py`
`6ec96c2e…fdadc`; `PORTFOLIO_FIX.sha256` regenerated; pushed before any run).

## The firing-count assertion (why deletion, not booking)

An instrumented throwaway copy of the OLD frozen driver (git `0abe6de`, not committed) was run
over all P4 calls in the three populations (G1's exact trade sets): the bottom block fired
**132 times — E_SN 33, E_RND 29, E_BRK 70 — and all 132 fires were on the arming day**
(`k == armed_day` in every case), exactly matching the G1-bis parity-failure trades. The block
had no legitimate path: it was look-ahead by construction.

## Gates (all passed)

1. **Re-freeze verified** before both runs: amended trio sidecar + mini-freeze sidecar OK.
2. **Data:** fingerprint `f42275e3…` (max_date 2026-10-06, panel pinned as G1-bis does) — zero
   drift; populations re-derived **exactly** G1's: E-SN 3,682 / E-RND 3,682 / E-BRK 5,141.
3. **Non-P4 bit-identity gate (G1FIX):** every non-P4 arm × population — metrics, portfolio,
   paired-vs-baseline, by-year, recommendations, E-SN-vs-E-RND, the P2 tail block —
   **0 mismatches** against `RESULT_20261006T142027Z.json` (canonical-JSON equality). Only the
   P4 rows changed.
4. **Parity gate (G1-bis):** canonical legs vs the frozen simulation on **150,060 trade × arm
   pairs: max |Δnet%| = 0.0** (gate: ≤ 1e-9), 0 exit day/reason mismatches.
5. **Cash and caps (G1-bis):** min cash across all 72 portfolios ≥ −4.4e-16 (float noise;
   every buy is cash-limited) — cash never negative; 20% entry / 30% add caps enforced by the
   min-leg sizing (pinned by `test_portfolio_v2.py`, all 39 tests pass, incl. the two new
   same-day tests).

## Corrected P4 (trade level, G1FIX — `RESULT_G1FIX_20261007T034553Z.json`)

Paired vs P0 on matched trades — G1's recorded rows (superseded) beside the corrected rows:

| population | era | G1 t (superseded) | corrected t | G1 mean R diff | corrected mean R diff | G1 expectancy R | corrected expectancy R | G1 mean net% | corrected mean net% |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| E_SN | E1 | +4.26 | +0.65 | 0.12 | 0.00 | 0.13 | 0.00 | 0.76% | 0.27% |
| E_SN | E2 | +3.25 | -0.13 | 0.05 | -0.00 | 0.00 | -0.04 | 0.32% | -0.15% |
| E_RND | E1 | +3.23 | -2.90 | 0.06 | -0.01 | -0.12 | -0.19 | -0.04% | -0.42% |
| E_RND | E2 | +3.46 | +0.25 | 0.08 | 0.00 | -0.03 | -0.11 | -0.14% | -0.61% |
| E_BRK | E1 | +6.01 | +0.03 | 0.13 | 0.00 | 0.11 | -0.01 | 0.74% | 0.02% |
| E_BRK | E2 | +4.92 | +0.76 | 0.09 | 0.00 | -0.07 | -0.16 | -0.54% | -1.30% |

Full corrected P4 metric rows (every other cell of the G1 metric tables is unchanged):

| metric row | n | mean net% | median net% | expectancy R | win rate | avg win% | avg loss% | mean hold |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| E_SN E1 P4 | 2253 | 0.27% | 0.81% | 0.00 | 54.5% | 5.55% | -6.07% | 6.0 |
| E_SN E2 P4 | 1429 | -0.15% | 0.62% | -0.04 | 53.4% | 7.26% | -8.63% | 5.5 |
| E_RND E1 P4 | 2252 | -0.42% | -1.98% | -0.19 | 46.5% | 5.88% | -5.91% | 6.7 |
| E_RND E2 P4 | 1429 | -0.61% | -2.44% | -0.11 | 45.6% | 7.63% | -7.52% | 6.3 |
| E_BRK E1 P4 | 3129 | 0.02% | -0.54% | -0.01 | 45.7% | 4.98% | -4.14% | 4.4 |
| E_BRK E2 P4 | 2012 | -1.30% | -0.60% | -0.16 | 42.5% | 4.73% | -5.77% | 3.6 |

Reading: once the top-up can only fill from the next session (and books its buy), the swing
lot's advantage disappears everywhere. The stop-report's interim sensitivity (t 2.31/2.32 on
E-SN) still contained the same-day fills — as the brief warned — and the true corrected values
are far lower. On the random-entry control in E1 P4 is mildly WORSE than P0 (t −2.90, one era
only). **P4's statistical leg fails in every population × era** (no cell reaches t ≥ 2.0).

## Portfolio tables (G1-bis — `RESULT_G1BIS_20261007T035639Z.json`, portfolio_v2)

The real-cash portfolio model (20% entry cap, 30% add cap, cash-limited) that G1-bis was
approved to run. These supersede G1's portfolio tables (which modelled no position legs and
no cash limit; their X0/X2 busts were sizing artifacts).

| population | era | arm | CAGR full | CAGR era | max DD | worst 12m | final equity | taken/signals | min cash |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| E_SN | E1 | X0 | 6.63% | 8.49% | -53.5% | -41.9% | 5.439 | 1097/2253 | -0.0000 |
| E_SN | E1 | X1 | 12.25% | 15.79% | -76.5% | -68.6% | 21.071 | 26/2253 | -0.0000 |
| E_SN | E1 | X2 | 3.10% | 3.95% | -66.5% | -62.7% | 2.235 | 412/2253 | -0.0000 |
| E_SN | E1 | X3 | 10.93% | 14.07% | -77.1% | -71.6% | 15.426 | 81/2253 | -0.0000 |
| E_SN | E1 | X4 | 10.05% | 12.93% | -78.6% | -70.8% | 12.523 | 52/2253 | -0.0000 |
| E_SN | E1 | X5 | 12.24% | 15.79% | -76.5% | -68.6% | 21.064 | 28/2253 | -0.0000 |
| E_SN | E1 | X6 | 11.07% | 14.26% | -73.4% | -66.2% | 15.964 | 47/2253 | -0.0000 |
| E_SN | E1 | P0 | 12.25% | 15.79% | -76.5% | -68.6% | 21.071 | 26/2253 | -0.0000 |
| E_SN | E1 | P1 | 12.28% | 15.84% | -76.4% | -68.5% | 21.249 | 30/2253 | -0.0000 |
| E_SN | E1 | P2 | 12.25% | 15.79% | -76.5% | -68.6% | 21.071 | 26/2253 | -0.0000 |
| E_SN | E1 | P3 | 12.25% | 15.80% | -76.5% | -68.6% | 21.087 | 26/2253 | -0.0000 |
| E_SN | E1 | P4 | 12.25% | 15.79% | -76.5% | -68.6% | 21.071 | 26/2253 | -0.0000 |
| E_SN | E2 | X0 | -1.70% | -9.02% | -57.0% | -36.1% | 0.635 | 477/1429 | -0.0000 |
| E_SN | E2 | X1 | 1.21% | 6.84% | -52.0% | -42.5% | 1.374 | 45/1429 | -0.0000 |
| E_SN | E2 | X2 | -2.43% | -12.65% | -55.2% | -35.7% | 0.523 | 436/1429 | -0.0000 |
| E_SN | E2 | X3 | -2.94% | -15.14% | -70.8% | -41.8% | 0.455 | 292/1429 | -0.0000 |
| E_SN | E2 | X4 | 0.00% | 0.00% | -58.6% | -38.5% | 1.000 | 220/1429 | -0.0000 |
| E_SN | E2 | X5 | 1.08% | 6.10% | -53.9% | -42.8% | 1.328 | 38/1429 | -0.0000 |
| E_SN | E2 | X6 | 0.04% | 0.21% | -42.8% | -33.8% | 1.010 | 34/1429 | -0.0000 |
| E_SN | E2 | P0 | 1.21% | 6.84% | -52.0% | -42.5% | 1.374 | 45/1429 | -0.0000 |
| E_SN | E2 | P1 | 1.86% | 10.69% | -54.3% | -43.4% | 1.627 | 44/1429 | -0.0000 |
| E_SN | E2 | P2 | 1.20% | 6.80% | -52.0% | -42.5% | 1.371 | 45/1429 | -0.0000 |
| E_SN | E2 | P3 | 2.02% | 11.63% | -49.6% | -39.6% | 1.695 | 39/1429 | -0.0000 |
| E_SN | E2 | P4 | 1.21% | 6.84% | -52.0% | -42.5% | 1.374 | 45/1429 | -0.0000 |
| E_RND | E1 | X0 | -1.74% | -2.20% | -83.1% | -74.3% | 0.630 | 1275/2253 | -0.0000 |
| E_RND | E1 | X1 | 12.22% | 15.76% | -73.5% | -65.1% | 20.924 | 24/2253 | -0.0000 |
| E_RND | E1 | X2 | 3.13% | 3.99% | -85.1% | -68.4% | 2.257 | 209/2253 | -0.0000 |
| E_RND | E1 | X3 | 10.76% | 13.85% | -69.7% | -62.4% | 14.817 | 58/2253 | -0.0000 |
| E_RND | E1 | X4 | 10.93% | 14.08% | -68.4% | -62.1% | 15.446 | 42/2253 | -0.0000 |
| E_RND | E1 | X5 | 11.92% | 15.37% | -73.1% | -64.8% | 19.521 | 24/2253 | 0.0000 |
| E_RND | E1 | X6 | 12.89% | 16.64% | -77.4% | -71.3% | 24.529 | 32/2253 | 0.0000 |
| E_RND | E1 | P0 | 12.22% | 15.76% | -73.5% | -65.1% | 20.924 | 24/2253 | -0.0000 |
| E_RND | E1 | P1 | 12.31% | 15.88% | -73.6% | -65.2% | 21.381 | 24/2253 | -0.0000 |
| E_RND | E1 | P2 | 12.24% | 15.79% | -73.5% | -65.1% | 21.036 | 24/2253 | -0.0000 |
| E_RND | E1 | P3 | 12.33% | 15.90% | -73.6% | -65.2% | 21.469 | 23/2253 | -0.0000 |
| E_RND | E1 | P4 | 12.27% | 15.82% | -73.6% | -65.2% | 21.174 | 24/2253 | 0.0000 |
| E_RND | E2 | X0 | -1.43% | -7.63% | -68.8% | -46.4% | 0.683 | 489/1429 | -0.0000 |
| E_RND | E2 | X1 | 3.88% | 23.27% | -57.7% | -35.3% | 2.728 | 37/1429 | -0.0000 |
| E_RND | E2 | X2 | -1.09% | -5.87% | -67.3% | -40.9% | 0.748 | 358/1429 | -0.0000 |
| E_RND | E2 | X3 | 0.75% | 4.22% | -43.5% | -28.1% | 1.219 | 74/1429 | -0.0000 |
| E_RND | E2 | X4 | 1.40% | 7.96% | -46.5% | -26.8% | 1.444 | 134/1429 | -0.0000 |
| E_RND | E2 | X5 | 0.52% | 2.92% | -73.1% | -57.7% | 1.148 | 45/1429 | -0.0000 |
| E_RND | E2 | X6 | 0.55% | 3.07% | -73.2% | -59.2% | 1.156 | 33/1429 | -0.0000 |
| E_RND | E2 | P0 | 3.88% | 23.27% | -57.7% | -35.3% | 2.728 | 37/1429 | -0.0000 |
| E_RND | E2 | P1 | 3.31% | 19.60% | -58.3% | -36.1% | 2.359 | 41/1429 | -0.0000 |
| E_RND | E2 | P2 | 3.87% | 23.22% | -57.8% | -35.9% | 2.722 | 37/1429 | -0.0000 |
| E_RND | E2 | P3 | 3.88% | 23.28% | -57.7% | -35.3% | 2.728 | 37/1429 | -0.0000 |
| E_RND | E2 | P4 | 3.88% | 23.27% | -57.7% | -35.3% | 2.728 | 37/1429 | -0.0000 |
| E_BRK | E1 | X0 | — | — | — | — | — | 1187/3129 | -0.0000 |
| E_BRK | E1 | X1 | 11.66% | 15.03% | -74.1% | -65.7% | 18.352 | 15/3129 | 0.0000 |
| E_BRK | E1 | X2 | 11.28% | 14.53% | -78.6% | -72.6% | 16.761 | 60/3129 | 0.0000 |
| E_BRK | E1 | X3 | 8.25% | 10.59% | -67.4% | -60.7% | 8.098 | 140/3129 | -0.0000 |
| E_BRK | E1 | X4 | 6.13% | 7.84% | -72.1% | -68.9% | 4.803 | 168/3129 | -0.0000 |
| E_BRK | E1 | X5 | 11.59% | 14.94% | -74.1% | -65.7% | 18.059 | 15/3129 | -0.0000 |
| E_BRK | E1 | X6 | 11.57% | 14.92% | -74.4% | -65.9% | 17.984 | 15/3129 | -0.0000 |
| E_BRK | E1 | P0 | 11.66% | 15.03% | -74.1% | -65.7% | 18.352 | 15/3129 | 0.0000 |
| E_BRK | E1 | P1 | 11.73% | 15.12% | -74.1% | -65.7% | 18.667 | 15/3129 | 0.0000 |
| E_BRK | E1 | P2 | 11.72% | 15.11% | -74.2% | -65.7% | 18.626 | 15/3129 | 0.0000 |
| E_BRK | E1 | P3 | 11.62% | 14.98% | -74.2% | -65.8% | 18.195 | 15/3129 | 0.0000 |
| E_BRK | E1 | P4 | 11.66% | 15.03% | -74.1% | -65.7% | 18.347 | 15/3129 | 0.0000 |
| E_BRK | E2 | X0 | — | — | — | — | — | 535/2012 | -0.0000 |
| E_BRK | E2 | X1 | 3.12% | 18.42% | -47.3% | -36.9% | 2.250 | 17/2012 | -0.0000 |
| E_BRK | E2 | X2 | -0.28% | -1.50% | -66.4% | -45.9% | 0.930 | 177/2012 | -0.0000 |
| E_BRK | E2 | X3 | -1.03% | -5.55% | -66.4% | -44.6% | 0.760 | 325/2012 | -0.0000 |
| E_BRK | E2 | X4 | -3.37% | -17.21% | -74.6% | -44.9% | 0.404 | 337/2012 | -0.0000 |
| E_BRK | E2 | X5 | 3.12% | 18.42% | -47.3% | -36.9% | 2.250 | 17/2012 | -0.0000 |
| E_BRK | E2 | X6 | 3.13% | 18.49% | -47.3% | -36.8% | 2.256 | 14/2012 | -0.0000 |
| E_BRK | E2 | P0 | 3.12% | 18.42% | -47.3% | -36.9% | 2.250 | 17/2012 | -0.0000 |
| E_BRK | E2 | P1 | 3.16% | 18.66% | -45.7% | -34.8% | 2.272 | 12/2012 | 0.0000 |
| E_BRK | E2 | P2 | 3.12% | 18.42% | -47.3% | -36.9% | 2.250 | 17/2012 | -0.0000 |
| E_BRK | E2 | P3 | 3.12% | 18.42% | -47.3% | -36.9% | 2.250 | 17/2012 | -0.0000 |
| E_BRK | E2 | P4 | 3.12% | 18.42% | -47.3% | -36.9% | 2.250 | 17/2012 | -0.0000 |

Skip/exposure detail (skipped full / cash / tiny, adds skipped, avg gross exposure and
% days at 10 positions over the era) is in the RESULT; the pattern mirrors the table above —
X0/X2-style wide or absent stops fill the book with small trades (up to 412 taken in E_SN E1
X2), the stopped arms are cash-bound most of the time, and E-BRK X0 (no stop on breakouts)
goes bust in both eras — the ruin finding from G1 survives the real-cash model.

Drawdown leg, P4 vs P0:

| population | era | P0 max DD | P4 max DD | P4 deepens DD? |
|---|---|---:|---:|---|
| E_SN | E1 | -76.5% | -76.5% | no |
| E_SN | E2 | -52.0% | -52.0% | no |
| E_RND | E1 | -73.5% | -73.6% | YES |
| E_RND | E2 | -57.7% | -57.7% | no |

With the fix, P4's portfolio is nearly indistinguishable from P0's: a pullback all the way to
entry − 0.5·ATR **after** the arming close is rare, so the top-up almost never fills at all
(E-SN E1: zero top-up fills — P4's portfolio row equals P0's exactly).

## Final recommendation per arm

Frozen rule via `exit_study.recommend()`, fed the **Step 2 statistical leg** (G1FIX
expectancy_R and paired_t_vs_base) and the **Step 3 drawdown leg** (portfolio_v2 max DD), per
the brief. (The recommendation block inside `RESULT_G1BIS_…json` is the mini-freeze's
mechanical carry-over of G1's pre-fix t-statistics and is superseded by this table.)

| E_SN arm | verdict | E1 t | E1 expHigher | E1 dd_ok | E2 t | E2 expHigher | E2 dd_ok |
|---|---|---:|---|---|---:|---|---|
| X1 | **NO_RELIABLE_DIFFERENCE** | -2.00 | False | False | +1.50 | True | True |
| X2 | **NO_RELIABLE_DIFFERENCE** | +0.23 | True | False | -0.47 | False | True |
| X3 | **NO_RELIABLE_DIFFERENCE** | -1.40 | False | False | +0.89 | True | False |
| X4 | **NO_RELIABLE_DIFFERENCE** | -1.73 | False | False | +1.15 | True | True |
| X5 | **NO_RELIABLE_DIFFERENCE** | -2.07 | False | False | +1.43 | True | True |
| X6 | **NO_RELIABLE_DIFFERENCE** | -0.02 | False | False | -0.08 | False | True |
| P1 | **NO_RELIABLE_DIFFERENCE** | +3.13 | True | True | +0.08 | True | True |
| P2 | **NO_RELIABLE_DIFFERENCE** | +3.18 | True | True | +1.50 | True | True |
| P3 | **NO_RELIABLE_DIFFERENCE** | -0.33 | False | True | +0.79 | True | True |
| P4 | **NO_RELIABLE_DIFFERENCE** | +0.65 | True | True | -0.13 | False | True |

| E_RND arm | verdict | E1 t | E1 expHigher | E1 dd_ok | E2 t | E2 expHigher | E2 dd_ok |
|---|---|---:|---|---|---:|---|---|
| X1 | **NO_RELIABLE_DIFFERENCE** | -0.43 | False | True | +0.10 | True | True |
| X2 | **NO_RELIABLE_DIFFERENCE** | +0.34 | True | True | -0.52 | False | True |
| X3 | **NO_RELIABLE_DIFFERENCE** | -0.04 | False | True | +0.94 | True | True |
| X4 | **NO_RELIABLE_DIFFERENCE** | +0.03 | True | True | +0.36 | True | True |
| X5 | **NO_RELIABLE_DIFFERENCE** | -0.46 | False | True | +0.19 | True | True |
| X6 | **NO_RELIABLE_DIFFERENCE** | -0.92 | False | True | -0.59 | False | True |
| P1 | **NO_RELIABLE_DIFFERENCE** | -0.72 | False | True | +0.32 | True | True |
| P2 | **NO_RELIABLE_DIFFERENCE** | +1.91 | True | True | -0.51 | False | True |
| P3 | **NO_RELIABLE_DIFFERENCE** | -0.99 | False | True | +0.53 | True | True |
| P4 | **NO_RELIABLE_DIFFERENCE** | -2.90 | False | True | +0.25 | True | True |

**P4 is NOT recommended. Stated plainly: the swing-lot edge G1 recorded was phantom proceeds
plus look-ahead fills; once both are removed, no arm in this study clears the frozen
both-eras rule in either entry population. A null P4 is the answer.** The rest of G1's
guidance stands unchanged (keep the structure stop for ruin control; do not adopt P2; the
E-SN-vs-E-RND entry comparisons are unchanged bit-for-bit). The P2 worst-5% tail question did
not need re-reporting: its rows are bit-identical to G1 (identity gate).

## Addendum disclosures

1. **Runner-crash transparency (G1FIX).** The G1FIX runner (`g1fix_run.py`, orchestration
   only, not frozen) crashed twice in its own comparison code BEFORE the identity gate ran and
   before any artifact was written: once on a KeyError (it compared the baseline arms X0/P0,
   which `recommend()` does not emit) and once because the E-SN-vs-E-RND loop had not yet been
   restricted to non-P4 arms. Both were bugs in the gate code, not in the study; the study
   computation is deterministic and identical across invocations; the run is counted once and
   completed on the third invocation with the gate intact. Nothing about the run's inputs or
   the frozen code changed between invocations.
2. **The mini-freeze text (PORTFOLIO_FIX.md) still describes the transcription as "including
   the frozen bottom-of-loop P4 fill block"** — historically accurate at mini-freeze time and
   superseded by the Amendment (the mini-freeze was not edited, per the brief's constraint);
   `portfolio_v2.py` and `g1bis_run.py` hashes in the regenerated `PORTFOLIO_FIX.sha256` are
   the amended ones.
3. **The runner-internal recommendation blocks** (in `RESULT_G1BIS_…json`) feed G1's stale
   pre-fix t-statistics per the mini-freeze's frozen wording ("G1's unchanged trade-level
   expectancy_R and paired_t_vs_base") — superseded by the Final-recommendation table above,
   which the brief defines as Step 2 stats + Step 3 drawdown.
4. **E-BRK X0 busts** (both eras) under the real-cash model — same ruin finding as G1's X0/X2
   note; cash itself never goes negative (min ≥ −4.4e-16); the bust is mark-to-market.
5. Practice study, as before: no registry, family-slot, or DECISION_LOG edits; no ~/jurnal26,
   production, or other-branch writes; read-only data throughout.

## Addendum provenance

- Amendment + re-freeze: commit `006ef6a5cbf89385e27cb6eaf07e41f1177e5c7b` (pushed and
  ls-remote-verified BEFORE any run). Firing-count assertion: instrumented throwaway copy of
  the old driver under /tmp (not committed), populations re-derived exactly G1's.
- Step 2: `g1fix_run.py` (committed for provenance) → `RESULT_G1FIX_20261007T034553Z.json`,
  runtime 592.9 s, gate `EXIT_STUDY_G1_APPROVED=1`.
- Step 3: `g1bis_run.py` (mini-frozen, unchanged, hash `f553c276…37c4`) →
  `RESULT_G1BIS_20261007T035639Z.json`, runtime 576.5 s, same gate.
- Addendum tables rendered mechanically from the two RESULT files (throwaway renderer under
  /tmp, G1 practice); narrative authored around them.
- **G1FIX/G1-bis are terminal. Per the brief: commit, push, STOP.**
