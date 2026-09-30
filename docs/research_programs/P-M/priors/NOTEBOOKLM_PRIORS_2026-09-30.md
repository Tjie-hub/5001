# NotebookLM priors — "Global Stock Market Anomalies and Financial Return Factors" · 2026-09-30

**Notebook:** https://notebook.google.com/notebook/eb0bcc91-f274-4811-a965-440e9fd6f58e
(auto-titled by NotebookLM; created by renaming the Owner's empty "Notebook tanpa judul" per the
Task-1 brief — do not confuse with "Wisdom of the Crowd: Retail Orders and Stock Returns", untouched.)

**Source state (20 entries):** fully imported + queryable: Rouwenhorst full WP (Yale ICF 98-95),
Bali/Cakici/Whitelaw w14804 PDF, Harvey/Liu/Zhu w20592 PDF, Hou/Xue/Zhang w23394 PDF,
Bailey/Lopez de Prado DSR PDF, Novy-Marx author page (x2, one duplicate), Stambaugh/Yu/Yuan NBER
page (x2, one duplicate), PROGRAM_STATE_2026-09-30 (text source: program state for grounding).
**Imported but fetch-FAILED (entry exists, "Info error", zero text):** Li/Wei/Zhang doi,
ScienceDirect Hanauer-Lauterbach, Wiley Ritter abstract, SSRN 205011 / 2050863 / 2156623,
ResearchGate UMA paper, all three idx.co.id PDFs. **Consequence:** every IDX-specific and
abstract-only number below is grounded ONLY in what the imported full texts state; LWZ/UMA/IDX
regulation numbers are planner-supplied and unverified against their PDFs.

**Caveat (Task-1 brief rule):** NotebookLM output is a grounded summary, not a primary source.
Every number carried into a card or memo must be re-checked against the PDF with a page citation
before use. Numbers below carry their source tag: [PDF-verified via NotebookLM extraction] vs
[abstract/planner-supplied, UNVERIFIED].

---

## Query (a) — per-factor effect sizes, samples, t-statistics (as stated in the sources)

## 1. Value Factor
"Emerging Markets (Rouwenhorst, 1998):"
"Sample: 1,705 firms across 20 emerging markets (IFC EMDB dataset), 1987–1997"
.
"Book-to-Market (B/M): Equal-weighting stocks across all 20 markets yields a High minus Low B/M excess return of +0.72% per month (~9.00% per annum) with a"
"-statistic of 3.82"
. Weighting countries equally yields +0.93% per month, with a
"-statistic of 4.00"
. (Fama & French's 1998 value-weighted 17-EM sample from 1987–1995 reported an annual B/M premium of 16.91%,
"-statistic = 3.06)"
.
"Earnings-to-Price (E/P): Equal-weighting across all 20 markets yields +0.60% per month (~7.44% per annum) with a standard error of 0.13% ("
"-statistic = 4.46)"
. (Fama & French 1998 reported 4.04% per annum,
"-statistic = 0.58)"
.
"Indonesia-Specific (Rouwenhorst, 1990–1997): High minus Low B/M yields +1.11% per month ("
"-statistic = 1.74); High minus Low E/P yields +1.18% per month ("
"-statistic = 2.11)"
.
"US Market & Replication (Hou, Xue & Zhang, 2017):"
"Sample: US stock universe using NYSE breakpoints and value-weighted returns, Jan 1967 – Dec 2014 (576 months)"
.
"Book-to-Market (Bm): High minus Low B/M decile average return = +0.59% per month ("
"-statistic = 2.84);"
"-factor alpha = +0.18% per month ("
"-statistic = 1.15)"
.
"Cash Flow-to-Price (Cp): Average High-Low return = +0.49% per month ("
"-statistic = 2.47)"
.
"Replication Overview: 37 out of 68 value-versus-growth anomaly variables are statistically insignificant at the 5% level ("
) when microcap biases are removed
.
"Benchmark Comparison (Harvey et al., 2016 / Fama & French, 1996): US HML (1963–1997) mean = +0.41% per month ("
"-statistic = 3.28); International B/M across 12 developed markets (1975–1995) mean = +0.50% per month ("
"-statistic = 3.13)"
.
## 2. Size Factor
"Emerging Markets (Rouwenhorst, 1998):"
"Sample: 20 emerging markets, 1982–1997"
.
"Small minus Big (S–B): Emerging markets average excess return = +0.70% per month ("
"-statistic = 3.09)"
.
"Indonesia-Specific (Rouwenhorst, 1990–1997): Small minus Big (S–B) = -0.46% per month ("
"-statistic = -0.77)"
.
"US & Europe Comparisons: US Size (SMB, 1963–1997) mean = +0.23% per month ("
"-statistic = 1.62); European Size across 12 countries (1979–1995) mean = +0.29% per month ("
"-statistic = 3.67)"
.
"US Market & Replication (Hou, Xue & Zhang, 2017):"
"Market Equity (Me): High minus Low market equity (Big minus Small) = -0.28% per month ("
"-statistic = -1.12), showing that the size anomaly is statistically insignificant under NYSE breakpoints and value-weighted returns"
. Microcaps comprise 60% of stock count but only 3.3% of total market capitalization; equal-weighting microcaps artificially inflates reported size premia
.
## 3. Quality Factor
"Li, Wei & Zhang's Indonesia Premia: The provided sources do not contain any paper or numbers by Li, Wei & Zhang for quality premia [Explicitly Unstated]."
"US Market & Replication (Hou, Xue & Zhang, 2017):"
"Sample: NYSE breakpoints, value-weights, 1967–2014"
.
"Gross Profits-to-Assets (Gpa, Novy-Marx 2013): High minus Low decile = +0.38% per month ("
"-statistic = 2.62);"
"-factor alpha = +0.18% per month ("
"-statistic = 1.24)"
.
"Fundamental F-score (Piotroski 2000 / Fq1): High minus Low quarterly F-score = +0.58% per month ("
"-statistic = 2.47);"
"-factor alpha = +0.13% per month ("
"-statistic = 0.58)"
.
"Replication Overview: 77 out of 103 intangibles/quality-related variables fail to replicate at the 5% level"
.
## 4. Profitability Factor
"Li, Wei & Zhang's Indonesia Premia: The provided sources do not contain any paper or numbers by Li, Wei & Zhang for profitability premia [Explicitly Unstated]."
"US Market & Replication (Hou, Xue & Zhang, 2017):"
"Sample: NYSE breakpoints, value-weights, 1967–2014"
.
"Return on Equity (Roe1): High minus Low decile = +0.69% per month ("
"-statistic = 3.07);"
"-factor alpha = -0.03% per month ("
"-statistic = -0.27)"
.
"Operating Profits-to-Book Equity (Ope, Fama-French 2015 RMW): High minus Low decile = +0.25% per month ("
"-statistic = 1.20, insignificant at 5% level)"
.
"Operating Profits-to-Lagged Equity (Ole): High minus Low decile = +0.07% per month ("
"-statistic = 0.37, insignificant)"
.
"Cash-based Operating Profitability (Cop, Ball et al. 2016): High minus Low decile = +0.63% per month ("
"-statistic = 3.44);"
"-factor alpha = +0.69% per month ("
"-statistic = 4.77)"
.
"Replication Overview: 46 out of 79 profitability variables fail to replicate at"
.
## 5. Momentum Factor
"Emerging Markets (Rouwenhorst, 1998):"
"Sample: 20 emerging markets, 1982–1997, 6-month prior return ranking, 6-month holding period (excluding extreme top/bottom 5% outliers)"
.
"Winner minus Loser (W–L):"
"Equal-weighting stocks across all 20 markets: +0.39% per month ("
"-statistic = 2.35)"
.
"Country-equal-weighted: +0.58% per month ("
"-statistic = 3.78)"
.
Winners outperformed Losers in 17 out of 20 countries (Wilcoxon test
)
.
"Indonesia-Specific (Rouwenhorst, 1991–1997): Winner minus Loser (W–L) = -0.24% per month ("
"-statistic = -0.63)"
.
"US & Europe Comparisons: US Momentum (1980–1995) mean = +0.64% per month ("
"-statistic = 3.02); European Momentum (1980–1995) mean = +0.67% per month ("
"-statistic = 6.33)"
.
"Li, Wei & Zhang's Indonesia Result: Not present in sources [Explicitly Unstated]."
"US Market & Replication (Hou, Xue & Zhang, 2017):"
"Prior 6-Month Returns (R6): High minus Low decile = +0.82% per month ("
"-statistic = 3.49) at 6-month horizon; +0.55% per month ("
"-statistic = 2.90) at 12-month horizon"
.
"Replication Overview: 20 out of 57 momentum variables fail to replicate at"
.
## 6. Low-Volatility / Risk Factors
"Emerging Markets (Rouwenhorst, 1998):"
"Beta (High minus Low Beta): All 20 markets average = -0.03% per month ("
"-statistic = -0.16); Cross-country average = -0.08% per month ("
"-statistic = -0.40), demonstrating no return premium for high-beta stocks"
.
"Indonesia-Specific Beta: High minus Low Beta = +0.87% per month ("
"-statistic = 1.21)"
.
"US Market & Idiosyncratic Volatility (Bali, Cakici & Whitelaw, 2009/2011):"
"Sample: NYSE/AMEX/NASDAQ stocks, July 1962 – December 2005"
.
"Univariate Idiosyncratic Volatility (IVOL): Value-weighted High minus Low IVOL decile return = -0.93% per month ("
"-statistic = -3.23); 4-factor alpha difference = -1.33% per month ("
"-statistic = -5.09)"
.
"Equal-Weighted IVOL: High minus Low return difference = +0.37% per month ("
"-statistic = 1.09, insignificant)"
.
"Reversal After Controlling for MAX: When controlling for MAX (lottery demand), equal-weighted High minus Low IVOL return difference becomes positive: +0.98% per month ("
"-statistic = 4.88); 4-factor alpha difference = +0.95% per month ("
"-statistic = 4.76)"
. Fama-MacBeth regression slope on IVOL controlling for MAX = +0.39 (
"-statistic = 4.69)"
.
"Replication (Hou, Xue & Zhang, 2017):"
"Fama-French 3-Factor IVOL (Ivff1): High minus Low decile = -0.51% per month ("
"-statistic = -1.62) at 1-month horizon; -0.33% ("
"-statistic = -1.11) at 6-month; -0.18% ("
"-statistic = -0.62) at 12-month (insignificant under NYSE breakpoints)"
.
"Frazzini-Pedersen (2014) Beta: High minus Low decile = **~ -0.20% per month** ("
"-statistic < 1.0)"
.
"Blitz, Pang & van Vliet's EM Effect Size: Not present in sources [Explicitly Unstated]."
## 7. MAX / Lottery-Demand Factor
"Bali, Cakici & Whitelaw (2009/2011):"
"Sample: NYSE/AMEX/NASDAQ stocks, July 1962 – December 2005 (522 months)"
.
"Single-Day MAX (MAX(1)):"
"Value-Weighted Raw Return Difference (Decile 10 High MAX minus Decile 1 Low MAX): -1.03% per month ("
"-statistic = -2.83)"
.
"Value-Weighted 4-Factor Alpha Difference: -1.18% per month ("
"-statistic = -4.71)"
.
"Equal-Weighted Raw Return Difference: -0.65% per month ("
"-statistic = -1.83)"
.
"Equal-Weighted 4-Factor Alpha Difference: -0.66% per month ("
"-statistic = -2.31)"
.
"Multi-Day MAX (MAX(5) - Average of 5 Highest Daily Returns):"
"Value-Weighted Raw Return Difference: -1.23% per month ("
"-statistic = -2.93)"
.
"Value-Weighted 4-Factor Alpha Difference: -1.32% per month ("
"-statistic = -4.07)"
.
"Fama-MacBeth Cross-Sectional Regressions:"
"Univariate slope on MAX: -0.0434 ("
"-statistic = -2.92)"
.
"Full specification with 6 controls (Beta, Size, BM, Momentum, Reversal, Illiquidity): slope on MAX = -0.0662 ("
"-statistic = -6.62)"
.
"Full specification with MAX, MIN, IVOL + 6 controls: slope on MAX = -0.0901 ("
"-statistic = -6.22)"
.
"Replication in Hou, Xue & Zhang (2017):"
"Maximum Daily Return (Mdr1): High minus Low decile = -0.34% per month ("
"-statistic = -1.14) at 1-month horizon; -0.17% ("
"-statistic = -0.62) at 6-month; -0.07% ("
"-statistic = -0.24) at 12-month (insignificant under NYSE breakpoints)"
.
## 8. Short-Side / Arbitrage & Investor Sentiment Effects
"Stambaugh, Yu & Yuan (2011 NBER / 2012 JFE):"
"Sample & Setting: Explores a broad set of cross-sectional stock anomalies in US equity markets under sentiment fluctuations and short-sale impediments"
.
"Key Findings:"
Long-short anomaly strategies are significantly more profitable following high levels of market-wide sentiment
.
The short leg of each strategy (overpriced stocks subject to short-sale constraints) drives this profitability and is significantly higher following high sentiment
.
Investor sentiment exhibits no relation to returns on the long legs
.
"-statistics / Numerical Premia: The available source abstracts and citations describe these qualitative findings, but do not report explicit numerical percentage premia or"
"-statistics for the short/long legs"
.
## 9. IPO Long-Run Underperformance & Lockup Expiration
"Ritter's IPO Long-Run Underperformance: Loughran & Ritter (1995) and Chopra, Lakonishok & Ritter (1992) are cited in the literature reference lists"
", but the provided sources do not report explicit percentage return magnitudes or"
"-statistics for Ritter's IPO long-run underperformance [Explicitly Unstated]."
"Field & Hanka's Lockup Expiration: Not present in the provided sources [Explicitly Unstated]."
## 10. Summary of Missing Source Information
Li, Wei & Zhang's specific Indonesia factor study (though Rouwenhorst provides Indonesia-specific numbers for value, size, momentum, beta, and turnover
", and"
logs an internal IDX factor-tilt book excess return of +15.3pp/yr,
"-stat = 2.48)"
;
Hanauer & Lauterbach's EM cross-section study;
Blitz, Pang & van Vliet's EM low-volatility study;
Ritter's IPO underperformance percentage figures/
"-statistics;"
Field & Hanka's lockup expiration abnormal returns/volume.

---

## Query (b) — evidence standards for short / low-power samples

## 1. -Statistic Hurdle & Multiple-Testing Corrections
"1."
"-Statistic Hurdle & Multiple-Testing Corrections"
"Harvey, Liu & Zhu (HLZ, 2016):"
The
"Hurdle & Logic: HLZ demonstrate that the traditional significance threshold of"
(corresponding to
for a single hypothesis test) is mathematically invalid in asset pricing because hundreds of factors have been tested on the same historical CRSP/Compustat dataset
. HLZ document 316+ published factors and estimate through a structural model that researchers have attempted between 1,300 and 2,000+ factors when accounting for hidden/unpublished tests
. Under widespread data mining and publication bias, a threshold of
generates massive false positive rates
. HLZ establish that a newly discovered factor today must clear a minimum
"-statistic hurdle of"
(corresponding to
)
.
"Multiple Testing Frameworks:"
"Family-Wise Error Rate (FWER): Using Bonferroni or Holm sequential adjustments to control the probability of making even a single false discovery yields"
"-statistic cutoffs between 3.78 and 4.01"
.
"False Discovery Rate (FDR): Using the Benjamini, Hochberg & Yekutieli (BHY) procedure (controlling FDR at 5% while accounting for unobserved missing tests"
) establishes a minimum hurdle of 3.18
. HLZ project that as factor production continues, the required
"-bar will continue rising toward 4.0"
.
"Hou, Xue & Zhang (HXZ, 2017):"
"Position & Empirical Findings: HXZ endorse and apply HLZ’s"
cutoff across their replication library of 447 anomaly variables
. At the conventional
level, 64% (286 out of 447) of published anomalies fail to show statistically significant return spreads when microcaps are mitigated using NYSE breakpoints and value-weighted returns
. When imposing HLZ's
bar, the failure rate rises to 85% (380 out of 447)
.
"Mechanism Behind False Discoveries: While HXZ agree with HLZ that"
"-hacking is widespread, HXZ argue that the primary driver of reported false anomalies in prior literature is microcap distortion"
. Microcaps account for 61% of stock count but only 3.3% of total market capitalization; weighting them heavily via equal-weighted returns, NYSE-Amex-NASDAQ breakpoints, or Fama-MacBeth regressions artificially inflates reported
"-statistics and return spreads"
.
## 2. Expected Post-Publication & Out-of-Sample Decay
"McLean & Pontiff (2016) (analyzed in HLZ 2016 & HXZ 2017):"
"Out-of-Sample Decay: Anomaly return predictability declines by 26% out-of-sample (in the post-sample period after data collection ends but prior to academic publication) due to statistical bias and backtest overfitting"
.
"Post-Publication Decay: Anomaly return predictability declines by 58% post-publication as a combined result of statistical bias, investor learning, and arbitrage capital entering the trade"
.
"Selection Bias in Decay Estimates: HLZ point out that McLean & Pontiff dropped 10 out of their initial 82 anomalies because they could not replicate the in-sample performance"
. Because those 10 non-replicable anomalies suffered a 100% decay rate, the true average post-publication decay across the full universe of published anomalies is even higher than 58%
.
## 3. Trading-Cost & Implementability Adjustments
"Novy-Marx & Velikov (2016 / 2023) (cited in portfolio profile & replication surveys):"
"Implementability Filters: Trading friction and transaction costs severely attenuate or eliminate published anomaly profits in practice, particularly for high-turnover strategies"
.
"Turnover Stratification: Low-turnover factors (such as value and gross profitability) easily survive transaction costs, whereas high-turnover anomalies (such as short-term reversal, idiosyncratic volatility, and microcap illiquidity measures) see their return spreads completely erased once market impact and bid-ask spreads are accounted for"
.
## 4. The Deflated Sharpe Ratio (DSR)
"Bailey & Lopez de Prado (2014):"
"What DSR Corrects For:"
"Selection Bias & Backtest Overfitting: Corrects for the \"winner's curse\" of picking the maximum observed Sharpe ratio out of"
attempted trials on the same dataset
.
"Non-Normality of Returns: Corrects for return distribution skewness and kurtosis, which artificially inflate standard Sharpe ratio estimates in short samples"
.
"Required Inputs:"
": Number of independent trials attempted (or implied independent trials"
^
derived via correlation or information-theoretic entropy)
.
"V[{"
^
"}]"
": Variance of the Sharpe ratio estimates across all tested trials"
.
": Sample length / track record length (number of returns observations)"
.
^
": Skewness of the selected strategy's returns distribution"
.
^
": Kurtosis of the selected strategy's returns distribution"
.
^
": Estimated Sharpe ratio of the selected strategy"
.
"Optimal Stopping Guidance: Recommends applying the"
(~37%) optimal choice rule (secretary problem) by sampling 37% of theoretically justifiable strategy configurations to establish a baseline before selecting the top performer, minimizing false positive risks
.
## 5. Guidance on Minimum Sample Length & Short/Low-Power Samples
"Harvey, Liu & Zhu (2016):"
"Sample Length Standard: HLZ calibrate their baseline structural model to"
months (20 years) of data
. They note that standard asset pricing studies typically require 15 to 50 years of monthly data to establish statistical power
. In short or low-power samples, noise dominates, and the required
"-statistic cutoff must be adjusted upward significantly to prevent random sample flukes from being misclassified as factor discoveries"
.
"Bailey & Lopez de Prado (2014):"
"Minimum Track Record Length (MTRL): DSR explicitly penalizes short samples through the"
factor in its test statistic numerator
. For instance, a backtested daily Sharpe ratio of 2.5 over 5 years (
days) is rejected at the 95% confidence level if
trials were run, but would pass if
trials were run
.
"IDX Quantitative Research Program Framework:"
Emphasizes a census-adjusted discovery bar of
", Minimum Detectable Effect (MDE) discipline per test, mandatory post-publication decay haircuts, and formal trial-count corrections via the Deflated Sharpe Ratio"
.
"💡 Next Step: Would you like me to build a custom Python script or interactive dashboard to compute the Deflated Sharpe Ratio (DSR) and"
"-statistic cutoffs for your own backtested strategy return series?"

## From the second run (17ec02e)

The second agent independently created a second notebook for the same brief:
https://notebook.google.com/notebook/3d4faa92-9382-48c0-9ce9-ec425596dcac (now marked
SUPERSEDED in-notebook; this notebook is canonical). Unique content from it:

- **Sources ingested there, not here:** McLean & Pontiff working-paper PDF (FMG,
  fmg.ac.uk — direct primary source, vs this notebook's HLZ-critique route), Bailey & López de
  Prado DSR author PDF (davidhbailey.com), Stambaugh/Yu/Yuan NBER w16898 page, HXZ NBER w23181.
  11 fetch failures recorded (SSRN/Wiley/OUP/ScienceDirect/ResearchGate bot-walls; all three
  idx.co.id PDFs rejected) — consistent with this notebook's experience.
- **BCW weighting result surfaced by query (relevant to every EW book here):** in Bali,
  Cakici & Whitelaw, the MAX lottery effect (VW −1.03%/mo, t −2.83) and the IVOL risk effect
  (VW alpha −1.33%/mo, t −5.09) **cancel under equal-weighting** (IVOL flips sign: +0.37%/mo,
  t 1.09 EW). An EW book's factor exposures are therefore not the published VW ones — priors
  transfer as sign hypotheses only.
- Setup note: the failed-fetch entries in that notebook carry "Info error" markers and were
  left un-deleted there as the failure record; per the reconciliation instruction this
  notebook (eb0bcc91) is the single canonical one.
