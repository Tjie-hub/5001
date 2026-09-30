# POWER MEMO — can the local panel confirm the literature priors? · 2026-09-30

**Panel:** factor-zoo construction (ADV60 ≥ Rp 1bn, price ≥ Rp 50, month-end snapshots,
59 months 2021-07→2026-09), **ex-frozen rows and volume>0 at entry AND exit** (the tradeability
rule proposed in D-065 §2), computed on the 2026-09-30 DB copy · 19,248 name-months, 58 calendar
months, 51 usable book months after warm-up. Books: hi52 (52-week-high proximity) sorted monthly;
(i) top-⅓ tercile tilt, (ii) top-20% concentrated. Book returns are gross of costs (turnover cost
≈ 0.6–2.9pp/yr at the observed 0.39/mo turnover; the TE and MDE rows are cost-insensitive).
Numbers only — method notes at the bottom.

## 1. Realized tracking error vs equal-weight universe

| book | book %/yr | EW universe %/yr | realized excess | t | TE (monthly) | TE (annualized) |
|---|---|---|---|---|---|---|
| hi52 top-20% | +28.37 | +30.53 | **−2.16 pp/yr** | −0.30 | 4.712% | **16.32%** |
| hi52 top-⅓ tercile | +20.56 | +30.53 | **−9.97 pp/yr** | −1.33 | 4.019% | **13.92%** |

Read: a hi52 tilt carries 14–16%/yr of tracking error against the EW universe; the realized
tradeable excess over the sample is ~zero-to-negative. (The unfiltered FINDINGS figure of
+15.30pp/yr is not comparable: it excludes nothing frozen, ignores exit-side volume, and nets
costs against a slightly different universe.)

## 2. Prior sizes and whether 60 local months can see them

MDE over T=60 months = t_bar × σ_TE × √12 / √60 (%/yr). Months needed = (t_bar × σ_TE / α_m)².
Two TE columns (top-20 / tercile); the verdict is identical, tercile shown where it differs.

| effect | prior size (source, see §3) | MDE %/yr @60mo: t=1.65 | t=2.00 | t=2.8575 | t=3.46 | months to detect prior: t=1.65 | t=2.00 | t=2.8575 | t=3.46 | local data can confirm? |
|---|---|---|---|---|---|---|---|---|---|---|
| value — IDX | 0.37%/mo (Li, Wei & Zhang 2023)¹ | 12.0 (10.3) | 14.6 (12.5) | 20.9 (17.8) | 25.3 (21.5) | 441 (321) | 649 (472) | >60y (>60y) | >60y (>60y) | **NO** — not at any bar |
| size — IDX | 0.28%/mo (LWZ)¹ | 12.0 (10.3) | 14.6 (12.5) | 20.9 (17.8) | 25.3 (21.5) | >60y (>60y) | >60y (>60y) | >60y | >60y | **NO** |
| quality — IDX | 0.26%/mo (LWZ)¹ | 12.0 (10.3) | 14.6 (12.5) | 20.9 (17.8) | 25.3 (21.5) | >60y (650) | >60y (>60y) | >60y | >60y | **NO** |
| profitability — IDX | 0.24%/mo (LWZ)¹ | 12.0 (10.3) | 14.6 (12.5) | 20.9 (17.8) | 25.3 (21.5) | >60y (>60y) | >60y | >60y | >60y | **NO** |
| momentum — IDX | not significant (LWZ)¹ | — no prior size to detect — | | | | | | | | n/a |
| value — EM | 0.72%/mo (Rouwenhorst 1999, EM EW, t 3.82)² | 12.0 (10.3) | 14.6 (12.5) | 20.9 (17.8) | 25.3 (21.5) | 117 (85) | 171 (125) | 350 (254) | 513 (373) | **NO** — needs 10–43y |
| size — EM | 0.70%/mo (Rouwenhorst 1999, t 3.09)² | 12.0 (10.3) | 14.6 (12.5) | 20.9 (17.8) | 25.3 (21.5) | 123 (90) | 181 (132) | 370 (269) | 542 (395) | **NO** |

¹ Li, Wei & Zhang premia are **planner-supplied and NOT verified against the PDF** — the paper
   could not be imported into the NotebookLM corpus (paywalled fetch failure); page-level
   citation pending. Verified status required before any card cites them.
² Rouwenhorst numbers are from the imported full-text working paper (Yale ICF 98-95) and were
   extracted with per-page citations by NotebookLM; the Indonesia-specific rows it reports
   (B/M +1.11%/mo t 1.74; E/P +1.18%/mo t 2.11; S−B −0.46%/mo t −0.77, 1990–1997) are consistent
   with the planner's framing but carry the same verification caveat before card use.

## 3. Verdict (one line per effect)

- Every literature prior (3–9%/yr in alpha terms) is **below the 60-month MDE at every bar
  except t=1.65 on the tercile book for the EM value/size priors (MDE 10.3%)** — and even there
  the required windows are 85–132 months, i.e. 7–11 years of clean data that do not exist.
- The only effect sizes the local 60-month panel can detect at the census bar (t 2.8575) are
  ≥ ~18–21%/yr — larger than any published equity factor premium; anything that small that
  "clears" locally is more plausibly a residual artifact than a factor.
- Implication feeding D-065 §1: external priors must carry the weight; local tests can only
  **fail to reject**, never confirm, at these TEs.

## Method (for reproduction)

- Panel rebuilt from `ohlcv` (is_final=1) with the zoo filters; features at month-end t, return
  t→t+1; frozen rows removed by requiring `volume>0` at both t and t+1; books = top-20% / top-⅓
  by hi52 among eligible names, ≥60 names and ≥10 picks per month else skip; EW universe = mean
  of the same eligible cross-section; TE = std(book − EW) monthly.
- MDE and months-needed are analytic (Gaussian), two-sided t bars as listed; the 2.8575 bar is
  the program's census-adjusted discovery bar (N=266), 3.46 the Bonferroni-92 bar from
  `FINDINGS_2026-09-18.md`.
