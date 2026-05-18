# LQ45 Walk-Forward Report

_Generated: 2026-05-18 from `wf_scores` (run 2026-05-15 16:00, data through 2026-05-15)_
_Coverage: 45 / 45 LQ45 tickers × 10 strategies = 450 ticker-strategy pairs_
_Window: 12mo train / 3mo test, 4 walk-forward windows per ticker_

---

## 1. Strategy popularity — which strategy wins most often across LQ45

| Strategy | Tickers Won | % of LQ45 |
|---|---:|---:|
| vol_weighted | 10 | 22% |
| ORB | 8 | 18% |
| Volume Profile POC | 7 | 16% |
| conservative | 6 | 13% |
| Inside Bar Breakout | 6 | 13% |
| NR7 Breakout | 4 | 9% |
| momentum | 2 | 4% |
| vwap_reversion | 1 | 2% |
| Swing Trend | 1 | 2% |
| **Trend Following Breakout** | **0** | **0%** |

**Takeaway:** Top 5 strategies (`vol_weighted`, `ORB`, `Volume Profile POC`, `conservative`, `Inside Bar Breakout`) account for **37/45 (82%)** of LQ45 winners. `Trend Following Breakout` never wins on any LQ45 ticker — candidate for removal or universe-specific use only.

---

## 2. Best strategy per ticker (ranked by weighted_score)

| Ticker | Best Strategy | Score | Cons % | Avg Return % | Sharpe |
|---|---|---:|---:|---:|---:|
| ISAT | ORB | 0.971 | 50.0 | 0.55 | 0.43 |
| MBMA | vol_weighted | 0.942 | 75.0 | 1.56 | 0.49 |
| BRPT | conservative | 0.937 | 75.0 | 3.54 | 1.38 |
| GOTO | ORB | 0.930 | 25.0 | 0.07 | -0.02 |
| INCO | vol_weighted | 0.930 | 50.0 | 2.18 | 0.79 |
| ADMR | vol_weighted | 0.927 | 50.0 | 0.47 | 0.35 |
| MDKA | conservative | 0.927 | 75.0 | 1.98 | 1.47 |
| EXCL | ORB | 0.925 | 50.0 | 0.95 | 0.94 |
| ICBP | vol_weighted | 0.921 | 25.0 | 0.14 | 0.04 |
| BRIS | Volume Profile POC | 0.915 | 25.0 | 0.01 | 0.06 |
| AMMN | vol_weighted | 0.912 | 25.0 | -0.30 | -0.19 |
| SIDO | vol_weighted | 0.909 | 25.0 | 0.46 | -0.62 |
| ACES | vol_weighted | 0.908 | 25.0 | -0.14 | 0.01 |
| PGEO | Volume Profile POC | 0.907 | 75.0 | 1.74 | 1.42 |
| ESSA | ORB | 0.905 | 50.0 | -0.13 | -0.27 |
| ANTM | ORB | 0.900 | 50.0 | 1.66 | 1.29 |
| BBNI | NR7 Breakout | 0.900 | 25.0 | 0.45 | 0.60 |
| MAPI | vwap_reversion | 0.900 | 25.0 | 0.25 | 0.51 |
| PTBA | Inside Bar Breakout | 0.900 | 25.0 | 0.32 | 0.67 |
| UNTR | Volume Profile POC | 0.900 | 50.0 | 0.35 | 1.33 |
| UNVR | Volume Profile POC | 0.900 | 25.0 | 0.32 | 0.61 |
| PGAS | Inside Bar Breakout | 0.899 | 50.0 | 0.43 | 0.21 |
| CPIN | conservative | 0.896 | 50.0 | 0.29 | 0.67 |
| BBRI | vol_weighted | 0.895 | 50.0 | -0.08 | -0.38 |
| MAPA | conservative | 0.891 | 50.0 | -0.26 | -0.55 |
| TLKM | NR7 Breakout | 0.882 | 50.0 | 0.14 | -0.63 |
| ITMG | momentum | 0.869 | 50.0 | 0.48 | 0.26 |
| ASII | Volume Profile POC | 0.863 | 25.0 | -0.15 | -0.14 |
| BMRI | NR7 Breakout | 0.863 | 25.0 | -0.14 | -0.59 |
| BBTN | momentum | 0.862 | 50.0 | 0.01 | 0.19 |
| JSMR | Inside Bar Breakout | 0.838 | 25.0 | 0.18 | 0.62 |
| MEDC | ORB | 0.837 | 25.0 | -0.51 | -0.40 |
| AKRA | Volume Profile POC | 0.833 | 25.0 | -0.51 | -0.54 |
| ADRO | Inside Bar Breakout | 0.823 | 50.0 | 0.03 | 0.03 |
| CTRA | ORB | 0.821 | 25.0 | -0.18 | 0.05 |
| AMRT | vol_weighted | 0.805 | 25.0 | -0.47 | -0.85 |
| JPFA | Volume Profile POC | 0.800 | 25.0 | 0.82 | 0.61 |
| SMGR | Inside Bar Breakout | 0.800 | 25.0 | 0.21 | 0.67 |
| KLBF | vol_weighted | 0.757 | 25.0 | -0.83 | -0.67 |
| INKP | conservative | 0.739 | 50.0 | -0.18 | -0.80 |
| TOWR | Inside Bar Breakout | 0.703 | 25.0 | 0.35 | -1.49 |
| BBCA | NR7 Breakout | 0.675 | 0.0 | 0.00 | 0.00 |
| INDF | Swing Trend | 0.675 | 0.0 | 0.00 | 0.00 |
| SMRA | ORB | 0.665 | 25.0 | -1.12 | -0.92 |
| ARTO | conservative | 0.664 | 0.0 | -1.01 | -1.50 |

**Note:** `weighted_score` weights consistency + sharpe + return. A high score doesn't always mean positive avg_return — tickers like AMMN, ACES, BBRI, KLBF, INKP have high scores but negative returns (low downside relative to peers). Re-rank by `avg_return_pct` below.

---

## 3. Top 15 ticker × strategy combos by avg return

| Rank | Ticker | Strategy | Avg Return % | Score | Cons % | Sharpe |
|---:|---|---|---:|---:|---:|---:|
| 1 | BRPT | conservative | 3.54 | 0.937 | 75.0 | 1.38 |
| 2 | BRPT | momentum | 3.17 | 0.887 | 75.0 | 1.23 |
| 3 | BRPT | vol_weighted | 2.36 | 0.791 | 75.0 | 0.69 |
| 4 | INCO | vol_weighted | 2.18 | 0.930 | 50.0 | 0.79 |
| 5 | MDKA | conservative | 1.98 | 0.927 | 75.0 | 1.47 |
| 6 | MBMA | Inside Bar Breakout | 1.78 | 0.667 | 25.0 | 0.67 |
| 7 | PGEO | Volume Profile POC | 1.74 | 0.907 | 75.0 | 1.42 |
| 8 | ANTM | ORB | 1.66 | 0.900 | 50.0 | 1.29 |
| 9 | MBMA | vol_weighted | 1.56 | 0.942 | 75.0 | 0.49 |
| 10 | BRPT | Inside Bar Breakout | 1.22 | 0.402 | 25.0 | 0.92 |
| 11 | BRPT | ORB | 1.10 | 0.398 | 25.0 | 0.96 |
| 12 | ANTM | momentum | 1.01 | 0.705 | 50.0 | 0.07 |
| 13 | PGEO | Inside Bar Breakout | 1.00 | 0.521 | 25.0 | 0.67 |
| 14 | INCO | ORB | 0.98 | 0.470 | 25.0 | -0.18 |
| 15 | EXCL | ORB | 0.95 | 0.925 | 50.0 | 0.94 |

**High-conviction names (multiple strategies converge with positive returns):**
- **BRPT** — 5 of 10 strategies positive (top 1, 2, 3, 10, 11). Strongest edge across LQ45.
- **INCO** — 2 strategies in top 15 (vol_weighted #4, ORB #14).
- **MBMA** — 2 strategies in top 15 (Inside Bar Breakout #6, vol_weighted #9).
- **ANTM** — 2 strategies in top 15 (ORB #8, momentum #12).
- **PGEO** — 2 strategies in top 15 (Volume Profile POC #7, Inside Bar Breakout #13).

Sector overlap: BRPT, INCO, MBMA, MDKA, ANTM, PGEO are **mining/commodities** — the LQ45 edge during this window concentrates in that sector.

---

## 4. Worst 15 ticker × strategy combos — avoid these pairs

| Ticker | Strategy | Avg Return % | Score | Cons % | Sharpe |
|---|---|---:|---:|---:|---:|
| ARTO | momentum | -3.06 | 0.200 | 0.0 | -2.91 |
| MAPA | vol_weighted | -2.90 | 0.100 | 0.0 | -2.90 |
| ESSA | vol_weighted | -2.60 | 0.303 | 25.0 | -2.52 |
| MEDC | vol_weighted | -2.40 | 0.394 | 25.0 | -2.36 |
| ESSA | conservative | -2.38 | 0.268 | 25.0 | -2.80 |
| UNVR | vol_weighted | -2.37 | 0.116 | 0.0 | -2.74 |
| ARTO | vol_weighted | -2.00 | 0.301 | 0.0 | -2.20 |
| AKRA | ORB | -1.96 | 0.147 | 0.0 | -2.20 |
| UNVR | ORB | -1.95 | 0.492 | 25.0 | -2.52 |
| ADMR | conservative | -1.94 | 0.138 | 0.0 | -2.02 |
| BBNI | ORB | -1.94 | 0.225 | 0.0 | -1.99 |
| PGEO | momentum | -1.91 | 0.299 | 25.0 | -1.20 |
| INKP | vol_weighted | -1.88 | 0.237 | 0.0 | -1.90 |
| AKRA | vol_weighted | -1.85 | 0.128 | 0.0 | -2.60 |
| UNVR | conservative | -1.82 | 0.128 | 0.0 | -3.03 |

**Pattern:** `vol_weighted` and `conservative` strategies, despite being top winners overall, blow up hard on consumer staples (UNVR), distribution (AKRA), and choppy mid-caps (ARTO, MAPA, ESSA, MEDC). The "best per ticker" approach matters — never blind-apply one strategy LQ45-wide.

---

## 5. Decision framework — next steps

### 5a. Core strategies to keep (covers 82% of LQ45 wins)
1. **vol_weighted** — best for mining/large caps (MBMA, INCO, ADMR, ICBP, ESSA, SIDO, ACES, AMMN, BBRI, AMRT, KLBF)
2. **ORB** — best for telco/utilities (ISAT, EXCL, GOTO, ESSA, ANTM, MEDC, CTRA, SMRA)
3. **Volume Profile POC** — best for staples/cyclicals (BRIS, PGEO, UNTR, UNVR, ASII, AKRA, JPFA)
4. **conservative** — best for mining/property (BRPT, MDKA, CPIN, MAPA, INKP, ARTO)
5. **Inside Bar Breakout** — best for utility/property (PTBA, PGAS, JSMR, ADRO, SMGR, TOWR)

### 5b. Candidates for removal / re-investigation
- **Trend Following Breakout** — 0 wins. Either tune or drop.
- **Swing Trend** — only wins on INDF, with score 0.675 and 0 returns. Likely zero trades — verify.
- **NR7 Breakout** — 4 wins but 3 of them (BBCA, TLKM, BMRI) have ≤0 return. Marginal.

### 5c. High-conviction trade candidates (next paper trade cycle)
Pairs where score ≥ 0.9 AND avg_return ≥ 1.0 AND consistency ≥ 50%:
1. **BRPT × conservative** (3.54%, 75% cons, 1.38 sharpe)
2. **MDKA × conservative** (1.98%, 75% cons, 1.47 sharpe)
3. **PGEO × Volume Profile POC** (1.74%, 75% cons, 1.42 sharpe)
4. **ANTM × ORB** (1.66%, 50% cons, 1.29 sharpe)
5. **MBMA × vol_weighted** (1.56%, 75% cons, 0.49 sharpe)

These are the 5 ticker-strategy pairs to bias paper-trading toward.

### 5d. Should we add Minervini VCP?
- Existing `Swing Trend` and `conservative` already capture VCP-adjacent trend-on-low-volume setups.
- `Trend Following Breakout` had 0 LQ45 wins — pure trend-following alone doesn't beat vol-weighted/consolidation breakouts on this universe.
- **Recommendation:** Implement VCP as strategy #11, but A/B against `conservative` on BRPT/MDKA/MBMA first — those are the cases where VCP should shine.

---

## Files generated

| File | Contents |
|---|---|
| `out/wf_lq45_report.md` | This consolidated report |
| `out/wf_lq45_best.md` | Best strategy per ticker, ranked by score |
| `out/wf_lq45_strategy_popularity.md` | Strategy win-count across LQ45 |
| `out/wf_lq45_all_pairs.md` | Full 450-row ticker × strategy dump |

Sync these to Windows `D:\IDX\out\` for offline review.
