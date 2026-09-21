# Broker / Investor Order Flow and Equity Returns — Literature Review

**Scope note:** This review is a pre-registration literature foundation for the IDX80 broker-flow
research program. It was compiled independently of this repo's own broker-flow dataset/results and
must not be read as validation of any specific finding from that dataset. It does not recommend a
trading strategy. Evidence tags used throughout: **FACT** (verifiable, non-controversial background),
**SOURCE CLAIM** (a claim attributed to a specific paper, not independently re-derived here),
**EMPIRICAL EVIDENCE** (a specific quantitative result reported in a primary source),
**INFERENCE** (a conclusion drawn here from the cited evidence, clearly mine), **UNKNOWN**
(could not verify — flagged rather than guessed).

---

## 1. Definition / Scope of the Research Question

"Identifying a genuine flow-based edge" here means: establishing whether broker-level buy/sell
order flow (aggregate, foreign, or investor-type-decomposed) carries information that predicts
**future** equity returns, as opposed to merely coinciding with **contemporaneous** returns via a
mechanical price-pressure or accounting identity (flow and same-day return are definitionally
correlated because buying pushes price up). The research question is therefore narrower than "does
flow correlate with price" — it is "does flow observed at time *t*, using only information
available at *t*, forecast returns at *t*+1..*t*+k, after accounting for the multiple-testing and
data-mining risk inherent in scanning many flow definitions and horizons." (INFERENCE — this framing
synthesizes the distinction the literature itself draws between contemporaneous price impact and
return predictability; see §3.3.)

---

## 2. Research Framework

The empirical microstructure literature approaches this question in three layers (INFERENCE, structure
imposed by me on the reviewed material):

1. **Theoretical foundation** — why flow *could* carry information or move price at all (informed
   trading, inventory/liquidity provision, behavioral feedback). §3.1, §3.6.
2. **Reduced-form predictive regressions** — regress forward returns (or reversal) on lagged flow
   measures, at varying horizons and investor-type decompositions, controlling for contemporaneous
   flow/return and known risk factors. §3.2–3.5.
3. **Robustness/bias layer** — the specific failure modes that inflate or fabricate apparent
   predictability (look-ahead bias, survivorship bias, non-PIT universes, multiple testing across
   flow definitions/horizons, and post-publication decay). §5.

A rigorous test in this framework must specify, ex ante: (a) the flow measure and its exact
construction window, (b) the return horizon(s) tested, (c) the investor-type cut if any, (d) the
statistical correction for the number of specifications tried, and (e) whether contemporaneous
correlation is being conflated with predictive power.

---

## 3. Literature Review

### 3.1 Theoretical microstructure foundations (why flow could carry information)

- **Kyle (1985)**, "Continuous Auctions and Insider Trading," *Econometrica* — the canonical model
  of a single informed trader, market maker, and noise traders. Price impact is linear in order
  flow ("Kyle's lambda"); order flow is the channel through which private information is gradually
  incorporated into price. **SOURCE CLAIM** (widely reconfirmed secondary description; I did not
  fetch the original 1985 text directly, only tertiary summaries — treat the *existence and core
  result* of the model as FACT given its ubiquity in the field, but treat any specific numeric
  claim about it as UNKNOWN unless sourced separately).
- **Glosten & Milgrom (1985)**-style adverse-selection models (bid-ask spread as compensation for
  trading against informed order flow) are the standard complementary framework cited alongside Kyle
  in the sources surveyed, but I did not independently fetch or verify a primary Glosten-Milgrom
  source in this pass — **UNKNOWN**, cited here only because it appears repeatedly as the paired
  citation in secondary literature; do not treat any specific claim about it as verified.
- **Grossman & Miller (1988)**, "Liquidity and Market Structure," *Journal of Finance* 43(3),
  617–637 (also NBER WP 2641) — the competing inventory/liquidity-provision framework: market
  makers supply immediacy and are compensated for bearing inventory risk; price impact here need not
  reflect information and can instead be **temporary** (reversing as inventory is unwound).
  **FACT** (publication details verified via direct search of multiple independent listings —
  SSRN, NBER, Wiley/JoF).

**Mechanism split (INFERENCE, synthesizing §3.1):** the literature offers two structurally different
explanations for any observed flow→return relation — (i) **information-based / permanent** (Kyle):
flow predicts future returns because it reveals private information that is only gradually
impounded, or (ii) **inventory/price-pressure / temporary** (Grossman-Miller): flow moves price
because liquidity providers must be compensated, and the effect should partially or fully reverse.
Distinguishing these is precisely the point of a genuine predictability test — see §3.3 and §6.

### 3.2 Aggregate order imbalance and returns

- **Chordia & Subrahmanyam (2004)**, "Order Imbalance and Individual Stock Returns: Theory and
  Evidence," *Journal of Financial Economics* 72(3), 485–518 (working paper version: Anderson
  School, UCLA, Oct 2002; SSRN abstract_id=354122). **EMPIRICAL EVIDENCE**: order imbalances are
  positively autocorrelated (consistent with agents splitting orders over time), and **lagged**
  imbalance positively predicts next-day returns — a "continuing price pressure" effect — but this
  positive lagged relation **reverses sign once contemporaneous imbalance is controlled for**.
  Imbalance-based trading strategies were reported to yield statistically significant returns in
  their sample. **SOURCE CLAIM**: I was not able to re-fetch the exact NYSE sample period, sample
  size, or specific coefficient/t-stat values (SSRN and the direct PDF fetch both failed — 403 /
  binary-PDF extraction failure); those specific numbers are **UNKNOWN** here and should not be
  quoted without a fresh, successful primary-source read.
- **China evidence**: a companion literature ("Order imbalance and stock returns: Evidence from
  China") reports that order-imbalance autocorrelation on Chinese exchanges is **qualitatively
  similar** to NYSE, but that predictability magnitude **varies across market structure/trading
  mechanism** — i.e., the effect is not assumed to transport unchanged to a different exchange
  design. **SOURCE CLAIM** (secondary-search-derived; specific numbers UNKNOWN, not independently
  fetched).
- Cross-asset/short-horizon extensions: lagged **cross-asset** order-flow imbalance also has
  forecasting power for future returns, but this effect is concentrated at short horizons and
  **decays rapidly**. **SOURCE CLAIM** (search-derived, exact paper/horizon not independently
  verified — UNKNOWN for specifics).

### 3.3 Contemporaneous vs. predictive (forward) returns — the central methodological distinction

This is the crux the literature is explicit about and that any IDX broker-flow test must not blur:

- **Contemporaneous relation**: order imbalance is significantly, positively associated with
  same-period returns after controlling for volume — this is close to a **mechanical/definitional**
  finding (buying pressure moves price in the period it occurs) and is **not** evidence of an edge.
  **FACT**, in the sense that this contemporaneous correlation is essentially undisputed across the
  literature surveyed.
- **Permanent vs. temporary decomposition**: information-based theory predicts the price impact of
  informed order flow should be **permanent** (only partial adjustment on arrival, with the rest
  revealed as information becomes public); inventory-based theory predicts an eventual **reversal**
  as the fundamental value has not actually changed. **SOURCE CLAIM**, standard framing repeated
  across the microstructure literature searched.
- **True forward predictability**: Chordia-Subrahmanyam's lagged-imbalance effect (§3.2) and
  Kelley-Tetlock's retail result (§3.4) are the strongest examples in this review of flow
  predicting genuinely **future** (not just contemporaneous) returns, at horizons beyond the
  trading day in which the flow was observed.

**INFERENCE**: any IDX test must report the contemporaneous relation separately from, and
explicitly not as a substitute for, a genuine t → t+k forward test; a positive contemporaneous
finding alone should be treated as confirming the accounting mechanism, not as evidence of a
tradeable edge.

### 3.4 Retail / individual investor flow

- **Kelley & Tetlock (2013)**, "How Wise Are Crowds? Insights from Retail Orders and Stock
  Returns," *Journal of Finance* 68(3) (SSRN abstract_id=1668706; NYU Stern / Kellogg working-paper
  copies). **EMPIRICAL EVIDENCE (SOURCE CLAIM, from search-result synthesis — direct PDF fetch
  failed, so treat exact coefficients as UNKNOWN)**: retail **market**-order imbalance predicts
  future stock returns and earnings-surprise direction, indicating individual investors' market
  orders aggregate genuine private information about future cash flows; retail **limit**-order
  imbalance behaves differently (more consistent with liquidity provision) and does not predict news
  tone the way market orders do. Reported predictive horizon: **up to ~20 trading days**, with
  predictability **not reversing** even out to a 60-day horizon (i.e., consistent with an
  information-based, not pure price-pressure, mechanism for the market-order component).
  **SOURCE CLAIM** — I flag this specific "20-day / no reversal at 60-day" figure as reported by
  secondary summaries of the paper, not independently re-derived from the primary text in this pass.
- **Decay of retail-order-imbalance predictability**: a more recent reassessment (arXiv working
  paper, "Revisiting Boehmer et al. (2021)," 2024, https://ar5iv.labs.arxiv.org/html/2403.17095)
  compares an original **2010–2015** sample to a **2016–2021** sample using the same retail
  order-imbalance (ROI) methodology. **EMPIRICAL EVIDENCE (verified via direct fetch, 2026-09-01)**:
  in 2016–2021, past ROI "can no longer predict weekly returns on large-cap stocks"; a full-sample
  long-short strategy built on lagged ROI, profitable in 2010–2015, becomes statistically
  insignificant in 2016–2021; for small-cap stocks specifically, one-week alpha fell from 0.437%
  (2010–2015) to 0.143% (2016–2021) — a decline of roughly two-thirds rather than a clean drop to
  zero. Still a working paper, not established as peer-reviewed — treat as lower-confidence than the
  JoF-published Kelley-Tetlock result, but the specific decay numbers above are now independently
  verified, not SOURCE CLAIM. This is directly relevant evidence of **regime/era dependence and
  post-publication decay** (§3.8, §5).

### 3.5 Foreign vs. domestic / institutional vs. retail flow, and herding

- **Ülkü & Weber (2014)**, "Identifying the Interaction between Foreign Investor Flows and Emerging
  Stock Market Returns," *Review of Finance* 18(4), 1541–1581 (fetched directly).
  **EMPIRICAL EVIDENCE**: using intraday daily data from a European emerging market plus comparison
  Asian markets, and a novel "structural conditional correlation" (SCC) methodology to separate
  simultaneous return↔flow interaction from one-directional feedback, the paper finds **significant
  bilateral intraday interaction** between net foreign flow and returns (i.e., the relationship runs
  both ways, contemporaneously) — and that correctly modeling this bilateral interaction **changes**
  conclusions that earlier, simpler studies drew about foreign "positive feedback trading" for some
  Asian markets. It also reports foreigners show a "sluggish response to global information" not
  fully explained by an information disadvantage. **METHODOLOGICAL FLAG (INFERENCE)**: this paper is
  itself a warning against naive lagged-regression designs for flow-return relationships — a
  simultaneity/endogeneity problem exists (flow and return can jointly respond to a common shock, or
  cause each other within the same day), and studies that don't correct for it may over- or
  mis-state "feedback trading" or predictability.
- **Krohn, Sushko & Synsatayakul (2023)**, BIS Working Paper No. 1154, "Foreign investor feedback
  trading in an emerging financial market" (Thailand; FX, fixed income, and equity order-flow data).
  **EMPIRICAL EVIDENCE (verified via BIS's own public abstract page, https://www.bis.org/publ/work1154.htm,
  fetched directly 2026-09-01 — page content is paraphrased by the fetch tool, not a verbatim quote,
  so treat exact wording as approximate though the substance is now primary-sourced, not
  search-derived)**: foreign non-resident trading **reinforces a momentum anomaly** across all three
  asset classes studied; **innovations** in foreign order flow (i.e., the unexpected component, not
  just the level) predict future returns, suggesting information content; local **financial**
  investors follow foreign investors in the same direction but with a lag; local **non-financial**
  investors act as liquidity-providing counterparties. **INFERENCE**: this investor-type
  decomposition (foreign / local-financial / local-non-financial, momentum vs. contrarian role) is a
  directly transferable template for an IDX broker-type decomposition, but the finding is
  Thailand-specific and should not be assumed to generalize to Indonesia without separate testing.
- **Vo (2017)**, "Trading of foreign investors and stock returns in an emerging market: Evidence
  from Vietnam," *International Review of Financial Analysis* 52, 88–93 (fetched directly, abstract
  page). **SOURCE CLAIM**: foreign investors in the Ho Chi Minh City exchange are found to be
  **positive feedback traders** (buy after price rises, sell after price falls) both before and
  after the global financial crisis, and are reported to show some "timing ability." Exact
  coefficients/sample dates were not independently re-derived here (abstract-level only) —
  **UNKNOWN** beyond the qualitative claim.
- **Institutional herding — developed/mixed evidence, method origin**: **Lakonishok, Shleifer &
  Vishny (1992)**, "The Impact of Institutional Trading on Stock Prices," *Journal of Financial
  Economics* 32(1), 23–43; NBER WP 3846 (https://www.nber.org/papers/w3846, **directly fetched and
  verified 2026-09-01** — **FACT**, confirmed via NBER's own public abstract page, not just
  corroborated listings).
  **EMPIRICAL EVIDENCE**: using quarterly holdings of 769 U.S. pension funds (1985–1989), the
  authors find **no evidence of substantial herding or positive-feedback trading** by these
  institutional managers at the individual-stock, quarterly level, **except in small stocks**, and
  no strong cross-sectional link between changes in fund holdings and a stock's abnormal return.
  This is the origin of the "LSV herding measure" used pervasively in later herding studies.
  **INFERENCE**: this is an important **negative/null** result to weigh against the momentum-herding
  findings in emerging markets (Vietnam, Thailand, and the general emerging-market herding
  literature below) — herding effects documented for foreign/institutional investors in emerging
  markets may not be a universal property of "institutions" as a class, but something more specific
  to the emerging-market/foreign-investor context, market structure, or frequency (quarterly LSV vs.
  daily emerging-market studies are not directly comparable).
- **Emerging-market institutional herding, general**: search-derived (not independently fetched)
  evidence describes institutional herding as **more studied in developed markets**, with a smaller
  but growing literature on China, Taiwan, Korea, and India; reported findings include institutional
  positive-feedback (momentum) trading in Taiwan, herding concentrated in **large stocks** in China,
  and momentum trading by mutual funds that "exacerbates" the momentum effect via winner-buying /
  loser-selling. **SOURCE CLAIM**, specifics UNKNOWN pending direct fetch — treat as a pointer to a
  literature to consult further, not as an established quantitative result.
- **Herding by foreign investors and emerging-market equity returns: Evidence from Korea**
  (identified via search, IDEAS/RePEc listing) — surfaced as a directly relevant title but **not
  fetched/verified in this pass**. **UNKNOWN** — flagged for follow-up rather than summarized from
  a search snippet alone.

### 3.6 Mechanisms — summary against the theory in §3.1

| Mechanism | Predicts | Literature support found |
|---|---|---|
| Information-based (Kyle-style informed trading) | Permanent price impact; flow predicts genuinely future returns | Kelley-Tetlock retail market orders (§3.4); Krohn et al. "innovations... predict future returns" claim (§3.5) |
| Inventory / price-pressure (Grossman-Miller) | Temporary impact; reversal after liquidity is restored | Contemporaneous order-imbalance/return correlation (§3.3); theoretical framing repeated across sources, but I found no single paper in this pass isolating a clean IDX-relevant reversal test — **UNKNOWN magnitude/horizon of reversal** |
| Herding / positive-feedback (behavioral) | Momentum-like autocorrelation in flow and returns, foreign/institutional-flow-specific | Vietnam (Vo 2017), Thailand (BIS WP 1154), general EM herding search results (§3.5) — **but explicitly contradicted at the U.S. quarterly-institutional level by Lakonishok-Shleifer-Vishny (1992)** |

**INFERENCE**: no single mechanism is universally supported; the literature suggests the correct
mechanism is likely **market-, investor-type-, and frequency-dependent** rather than a single global
truth — which itself argues for testing multiple investor-type and horizon combinations *with*
multiple-testing correction (§5, §6), not picking one mechanism a priori.

### 3.7 Predictive flow-feature construction

Academically, the validated feature constructions found in this review are: (a) **raw signed order
imbalance** (buy volume − sell volume, scaled by total volume or shares), used by Chordia-Subrahmanyam
and the China-evidence paper; (b) **investor-type-decomposed** imbalance (retail market vs. limit,
Kelley-Tetlock; foreign vs. local-financial vs. local-non-financial, Krohn et al.); (c) **lagged /
autocorrelation-exploiting** imbalance, motivated by the documented positive autocorrelation of order
flow itself. I found **no peer-reviewed academic source** in this pass that validates a
"cumulative-volume-delta z-score" style feature specifically — the sources returned for that query
were exclusively retail-trading vendor blogs and TradingView indicator pages (QuantVPS, LobeHub,
TradingView scripts). **FLAG**: this is a **vendor/practitioner-only** construction with **no
academic validation found**; it should not be assumed to carry the same evidentiary weight as the
peer-reviewed imbalance measures above, and should be treated as a candidate feature to test, not a
pre-validated one. **INFERENCE**.

### 3.8 Regime dependence

- **Liquidity-conditional predictability**: short-horizon return predictability from order flow is
  reported to be **diminished when bid-ask spreads are narrower**, and to have **declined over time**
  as tick sizes shrank — i.e., predictability is not stationary even within a single market's own
  history. **SOURCE CLAIM** (search-derived; not independently fetched — UNKNOWN specifics).
- **Volatility-conditional co-movement**: contemporaneous interconnectedness between order flows
  across assets/venues is reported to be **stronger for liquidity-demanding orders during volatile
  periods**, with some strategies flipping to **negative** correlation in extreme events versus
  positive correlation in normal regimes. **SOURCE CLAIM**, UNKNOWN specifics.
- **Era decay**: the retail-order-imbalance 2016–2021 reassessment (§3.4) is the clearest
  single piece of evidence in this review that a previously-published flow-return relationship can
  **weaken to the point of non-profitability** in a later sample — a direct, literature-internal
  demonstration of non-stationarity, not just a generic caution.

### 3.9 Methodological pitfalls specific to this literature

- **Look-ahead bias**: using information not actually knowable at the decision date; produces
  "excessively optimistic" backtest results. **FACT** (standard, uncontested definition, corroborated
  across multiple independent sources).
- **Survivorship bias**: excluding since-delisted names inflates measured historical performance
  because delistings are disproportionately failures. Cited magnitude from search results: **Elton,
  Gruber & Blake (1996)** reportedly found survivorship bias in mutual-fund returns of **~0.9%/year**
  — **SOURCE CLAIM**, not independently re-fetched from the primary source in this pass; treat the
  exact 0.9% figure as UNKNOWN pending direct verification, cited here only because it recurs
  consistently across independent secondary sources.
- **Point-in-time (PIT) universe construction**: the standard fix is to reconstruct, for each
  historical date, the constituent list and fundamentals **as they were actually known at that date**
  (including names that later failed), with realistic reporting lags for any fundamental data.
  **FACT** (methodological consensus, uncontested in sources reviewed).
- **Multiple testing / data snooping**: **Harvey, Liu & Zhu (2016)**, "…and the Cross-Section of
  Expected Returns," *Review of Financial Studies* 29(1), 5–68; NBER WP 20592
  (https://www.nber.org/papers/w20592, **directly fetched and verified 2026-09-01** — **FACT** for
  bibliographic detail). **EMPIRICAL EVIDENCE (verified via NBER's own public abstract, 2026-09-01)**:
  the abstract itself states the conventional significance threshold (t ≈ 2.0) is far too permissive
  given how many factors have already been tried ("hundreds of papers and hundreds of factors"), and
  explicitly recommends "a newly discovered factor needs to clear a much higher hurdle, with a
  t-ratio greater than 3.0" — the **t ≈ 3.0 threshold is now confirmed FACT**, not SOURCE CLAIM. The
  specific **"~316 factors"** count used earlier in this review is **NOT** in the abstract itself
  (only the qualitative "hundreds of factors") — that exact figure stays **UNKNOWN/SOURCE CLAIM**,
  not independently verified against the primary text in this pass, and should not be quoted as a
  precise count without a fresh full-text check. A related, separately-sourced WebSearch result
  (not independently re-verified against a primary text — **SOURCE CLAIM**) describes a
  Benjamini-Yekutieli FDR-based analysis in the paper implying a t-stat hurdle of **3.39** for
  FDR ≤ 1%; treat this specific number the same way — plausible, but unconfirmed against the primary
  paper here. The multiple-testing correction is reported to be **nonlinear**, penalizing
  marginal-Sharpe strategies far more heavily than top-tier ones — **SOURCE CLAIM**, not
  independently re-verified this pass. A related reassessment (search-derived, exact
  authorship of the "27–53% false discovery" figure not independently re-verified here — **UNKNOWN**
  specific paper) reports that of 296 previously "significant" published anomalies, roughly **27–53%
  (80–158)** may be false discoveries once multiple-testing-adjusted, with the estimate likely
  **conservative** because failed, unpublished tests aren't counted (a compounding **publication
  bias**, see below).
- **Publication bias**: two forms identified in the sources reviewed — (i) negative results are hard
  to publish, and (ii) replication studies are rarely published in finance/economics relative to
  other fields, unlike the norm elsewhere in science. **SOURCE CLAIM**. Post-publication, several
  studies (Calluzzo, Moneta & Topaloglu; McLean & Pontiff — **SOURCE CLAIM, not independently
  fetched, UNKNOWN specifics**) reportedly find published anomaly premia **decay roughly one-third**
  on average as capital (especially hedge funds) trades to exploit them once public — directly
  relevant to why an in-sample-only literature review must not be treated as proof a flow effect is
  currently live and exploitable.
- **Implementation/look-ahead-specific inflation in adjacent asset classes**: a 2026 corporate-bond
  factor-zoo study (arXiv 2604.07880, title only verified via search — **UNKNOWN** full detail)
  reportedly finds look-ahead bias alone inflated measured momentum-type factor returns by
  **57–100%** and implementation-realism gaps inflated price-based factor alphas by up to **91%**.
  Cited as an illustrative **order of magnitude** for how large these biases can be in adjacent
  literatures, **not** as a number transferable to IDX broker-flow research — **INFERENCE**, flagged
  explicitly as illustrative-only.

### 3.10 Indonesia-specific evidence — what exists and what does not

This sub-topic had the **thinnest and most structurally different** evidence base found in this
review, and the gap matters for scoping the IDX80 program:

- Multiple studies exist on **aggregate/macro foreign portfolio flow ↔ Jakarta Composite Index /
  exchange-rate** relationships (e.g., papers on foreign capital flow and the IDR/USD rate, VAR-based
  Granger-causality work, COVID-period foreign flow and monetary policy response, and a paper
  reporting foreign investors "outperform domestic investors" across ~5 million transactions on the
  Jakarta exchange). These are **SOURCE CLAIMS**, search-derived and not independently fetched in
  this pass — treat all specific findings as UNKNOWN pending direct verification.
- **I found no peer-reviewed academic study in this pass that performs a stock-level, broker-flow
  (order-imbalance-style) predictive-return regression specifically on IDX data**, of the kind
  Chordia-Subrahmanyam or Kelley-Tetlock ran for the U.S., or Vo (2017)/Krohn et al. (2023) ran for
  Vietnam/Thailand. The closest results are (a) macro/aggregate net-foreign-flow studies (not
  broker-level, not necessarily stock-level daily), and (b) machine-learning return-prediction
  studies on Indonesian indices (LQ45) using technical indicators, not flow data. **FLAG — genuine
  literature gap**, not a search failure: I ran targeted queries for "Indonesia individual stock
  foreign net buy daily return," "IDX broker flow predictability," and "Jakarta Composite retail
  order imbalance 2020–2021" and none returned a matching academic study.
- **INFERENCE**: this gap is itself informative for the research program — Indonesia-specific,
  broker-level flow→return predictability is, as far as this review could establish, an **open
  empirical question in the public academic literature**, not a previously-tested-and-confirmed (or
  previously-tested-and-refuted) relationship. Any IDX80 result will be closer to a genuine novel test
  than a replication of an established local finding. This raises the multiple-testing/pre-registration
  bar (§5, §6), not lowers it — an unreplicated, single-market, single-team result is exactly the
  profile Harvey-Liu-Zhu-style false-discovery concerns apply most strongly to.

---

## 4. Evidence for Different Approaches / Mechanisms

See §3.6 table. Summary ranking by evidentiary strength found in this review (INFERENCE, my own
synthesis):

1. **Strongest**: retail market-order imbalance predicting future returns/earnings surprises at
   20-trading-day horizons in the U.S. (Kelley & Tetlock 2013, peer-reviewed JoF) — but with credible
   evidence the effect **decayed** by 2016–2021 in a later reassessment.
2. **Moderate**: foreign-investor momentum/feedback trading and its interaction with local investor
   types in single-country emerging-market studies (Vietnam, Thailand) — each is a single study in a
   single market, not yet a broad cross-market consensus.
3. **Contested/mixed**: institutional herding as a general phenomenon — strong emerging-market
   feedback-trading claims sit alongside a null U.S. quarterly-level result (Lakonishok-Shleifer-Vishny
   1992) for a *different* investor population (U.S. pension funds) and *different* frequency
   (quarterly).
4. **Weakest / unvalidated**: specific engineered features like z-scored cumulative volume delta —
   no academic source found; practitioner/vendor-only.
5. **Absent**: any Indonesia-specific, stock-level, broker-flow predictive-return study.

---

## 5. Common Failure Modes

Consolidated from §3.9, ranked by relevance to this specific research design (INFERENCE):

1. **Conflating contemporaneous correlation with forward predictability** (§3.3) — the single most
   important trap for a flow-based study specifically, since flow and same-day return are almost
   mechanically related.
2. **Multiple testing across flow definitions, investor-type cuts, and horizons without correction**
   (§3.9) — especially acute here because §3.7 and §3.5 show the literature itself has not converged
   on one "correct" flow feature or investor-type cut, creating a large researcher-degrees-of-freedom
   space.
3. **Non-PIT universe / look-ahead bias** in broker-flow and ticker-universe construction (§3.9) —
   directly relevant given this repo's own noted P2 data-quality exclusion (held as unresolved
   background per this review's scope, not evaluated here).
4. **Survivorship bias** in the ticker universe used for any backtest built on this literature's
   findings (§3.9).
5. **Endogeneity/simultaneity between flow and return** (§3.5, Ülkü & Weber) — naive lagged
   regressions can mistake a jointly-caused contemporaneous relationship for one-directional
   predictability.
6. **Regime non-stationarity / era decay** (§3.4, §3.8) — a relationship validated in one sample
   period is not guaranteed to hold in another, even within the same market.
7. **Publication bias in the reference literature itself** (§3.9) — this review draws on published,
   surviving findings; the base rate of *unpublished, failed* flow-predictability tests is unknown
   by construction, which should temper prior confidence in any single positive finding cited here.

---

## 6. Practical Validation Methodology (per the literature's own standards)

Synthesized requirements (INFERENCE, built directly from §3.3–3.9, not from this repo's own methods):

1. Specify the flow feature, its construction window, and the return horizon(s) **ex ante**, before
   looking at outcome data (pre-registration).
2. Report the **contemporaneous** flow-return relationship **separately** from any lagged/forward
   test, and do not present the former as evidence of an edge.
3. Test for **reversal** at longer horizons to help distinguish information-based (permanent) from
   inventory-based (temporary) mechanisms (§3.1, §3.6).
4. If testing multiple investor-type decompositions (foreign/domestic, institutional/retail) and/or
   multiple horizons, apply an explicit multiple-testing correction (e.g., Harvey-Liu-Zhu-style
   higher t-stat bar, or a formal FDR/Bonferroni-style procedure) rather than reporting the best of
   several unadjusted specifications (§3.9).
5. Use a strictly point-in-time universe and flow dataset — no information available only in
   hindsight (§3.9); this repo's own P2 exclusion is the kind of constraint this requirement is
   meant to enforce, though this review does not evaluate that specific issue.
6. Test for **regime/era dependence** explicitly — split-sample or rolling-window re-estimation, not
   a single full-sample coefficient — given the documented decay of comparable effects elsewhere
   (§3.4, §3.8).
7. Where possible, benchmark against a **null/placebo** flow construction (e.g., randomly permuted
   investor-type labels) to calibrate how much apparent predictability could arise from the
   researcher-degrees-of-freedom space alone.

---

## 7. Relevance to IDX / Broker-Flow Research (structural, not data-specific)

- The literature offers a validated **general template** — signed order imbalance, investor-type
  decomposition, lagged predictive regressions with contemporaneous controls — that is directly
  adaptable to a broker-flow dataset (§3.2, §3.4, §3.5, §3.7).
- The clearest **transferable design choices** are Kelley-Tetlock's market-vs-limit-order split
  (§3.4) and Krohn et al.'s foreign/local-financial/local-non-financial three-way split (§3.5), both
  of which produced differentiated (not uniform) results by investor type — suggesting an
  undifferentiated "total broker flow" feature is likely to be a weaker test than an investor-type
  decomposed one, if IDX broker categories support such a split. **INFERENCE**.
- The **absence** of any Indonesia-specific stock-level broker-flow study (§3.10) means this
  research, if conducted rigorously, would be a genuine first test in this literature for this
  market — which argues for *treating it with the same skepticism the literature applies to any
  single, first, unreplicated finding* (§3.9, §5), not for treating a positive result as
  self-evidently credible because "no one has found this exists here yet."
- The documented **era-decay** of a structurally similar U.S. finding (§3.4) is a direct caution
  against assuming any historically-fit relationship, IDX or otherwise, will remain stable
  out-of-sample without explicit regime testing (§6).

This review deliberately does not comment on whether any of this generalizes to this repo's actual
collected broker-flow dataset or its 31,178-ticker-day sample — that is an empirical question for a
separate, later analysis phase, not this literature-review deliverable.

---

## 8. Open Research Questions

1. Is there **any** stock-level, broker/foreign-flow predictive-return relationship in IDX data, and
   if so, at what horizon — this review found no prior published answer either way (§3.10).
2. Does an investor-type decomposition (foreign vs. domestic institutional vs. domestic retail, if
   IDX broker codes support this) produce differentiated results the way Kelley-Tetlock's
   market/limit split and Krohn et al.'s three-way split did (§3.4, §3.5), or is IDX flow more
   homogeneous?
3. Is any observed IDX relationship information-based (permanent, no reversal) or inventory-based
   (temporary, reverses) — per the mechanism split in §3.1/§3.6?
4. Is IDX flow predictability, if it exists, **regime-dependent** (bull/bear, high/low liquidity) as
   suggested generically by §3.8, and specifically as documented for a structurally similar effect
   in the U.S. retail literature (§3.4)?
5. What is the appropriate multiple-testing correction given the number of flow-definition ×
   horizon × investor-type combinations this program is likely to explore (§3.9, §6)?
6. Does the "P2" data-quality exclusion (held as unresolved background in this review) materially
   change eligible sample composition in a way that could itself introduce a form of survivorship or
   selection bias — a question for the empirical-analysis phase, not this literature review.

---

## 9. Recommended Next Experiments

(Sequenced as literature-informed *candidate* Phase A/B/C tests — not a commitment, and not run in
this review. See §10 for the mapping table.)

1. **Phase A — contemporaneous baseline**: confirm the mechanical contemporaneous flow-return
   relationship exists in IDX data (expected, low-informational-value control, per §3.3) before any
   predictive claim is entertained.
2. **Phase A — naive lagged predictive test**: total broker net-flow at t predicting return at
   t+1..t+k for a small number of pre-registered horizons (e.g., 1, 5, 20 days, mirroring
   Kelley-Tetlock's horizons in §3.4), with reversal checked out to a longer horizon.
3. **Phase B — investor-type decomposition**: repeat Phase A split by broker/investor-type category
   (foreign vs. domestic, and by broker category if a retail/institutional proxy exists in IDX
   broker data), per §3.5/§3.7's differentiated-effect precedent.
4. **Phase B — regime split**: re-estimate Phase A/B across volatility and/or bull/bear regimes,
   given §3.8's evidence of regime-dependent predictability magnitude.
5. **Phase C — multiplicity-corrected synthesis**: apply an explicit multiple-testing correction
   across the full grid of flow definitions × horizons × investor-type cuts × regimes tested in
   Phases A/B, following the Harvey-Liu-Zhu logic in §3.9, before any result is treated as evidence
   of a genuine edge.

---

## 10. Sources

Primary/verified via direct fetch or corroborated bibliographic detail across independent listings:

- Kyle, A.S. (1985). "Continuous Auctions and Insider Trading." *Econometrica* 53(6), 1315–1335.
  (Existence/core result treated as FACT given ubiquity; not independently re-fetched this pass.)
- Grossman, S.J. & Miller, M.H. (1988). "Liquidity and Market Structure." *Journal of Finance*
  43(3), 617–637. Also NBER Working Paper No. 2641. https://www.nber.org/papers/w2641
- Chordia, T. & Subrahmanyam, A. "Order Imbalance and Individual Stock Returns: Theory and
  Evidence." *Journal of Financial Economics* 72(3), 485–518 (2004). Working paper (Oct 2002):
  https://www.anderson.ucla.edu/documents/areas/fac/finance/36-00.pdf ·
  SSRN: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=354122 · RePEc/IDEAS:
  https://ideas.repec.org/a/eee/jfinec/v72y2004i3p485-518.html (re-attempted 2026-09-01: RePEc/IDEAS
  page has no abstract, "No abstract is available for this item," full text is
  ScienceDirect-subscription-only; still could not verify the specific lagged-imbalance /
  sign-reversal claim against a primary source. Bibliographic details — volume/issue/pages — are now
  FACT, directly confirmed via RePEc; the substantive finding stays SOURCE CLAIM/UNKNOWN.)
- Kelley, E.K. & Tetlock, P.C. (2013). "How Wise Are Crowds? Insights from Retail Orders and Stock
  Returns." *Journal of Finance* 68(3), 1229–1265. SSRN: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1668706
  · Working paper: https://www.stern.nyu.edu/sites/default/files/assets/documents/uat_024411.pdf ·
  RePEc/IDEAS: https://ideas.repec.org/a/bla/jfinan/v68y2013i3p1229-1265.html (re-attempted
  2026-09-01: RePEc/IDEAS page confirms bibliographic details only — "No abstract is available for
  this item," full text subscription-only; the ~20-trading-day / no-60-day-reversal predictive
  horizon claim remains SOURCE CLAIM/UNKNOWN, not independently verified against a primary source
  in either pass.)
- Ülkü, N. & Weber, E. (2014). "Identifying the Interaction between Foreign Investor Flows and
  Emerging Stock Market Returns." *Review of Finance* 18(4), 1541–1581.
  https://academic.oup.com/rof/article/18/4/1541/1606457 (fetched directly — highest-confidence
  source in this review; not re-fetched in the 2026-09-01 QA pass, no change.)
- Vo, X.V. (2017). "Trading of foreign investors and stock returns in an emerging market: Evidence
  from Vietnam." *International Review of Financial Analysis* 52, 88–93.
  https://ideas.repec.org/a/eee/finana/v52y2017icp88-93.html (fetched directly, abstract-level; not
  re-fetched in the 2026-09-01 QA pass, no change.)
- Krohn, I., Sushko, V. & Synsatayakul, W. (2023). "Foreign investor feedback trading in an emerging
  financial market." BIS Working Paper No. 1154. https://www.bis.org/publ/work1154.htm
  (**directly fetched and verified 2026-09-01** — BIS's own public abstract page confirms the
  foreign/local-financial/local-non-financial three-way decomposition and the momentum-reinforcement
  finding; upgraded from SOURCE CLAIM to EMPIRICAL EVIDENCE, see §3.5. Page content reached via the
  fetch tool's paraphrase, not a verbatim quote — treat exact wording as approximate.)
- Lakonishok, J., Shleifer, A. & Vishny, R.W. (1992). "The Impact of Institutional Trading on Stock
  Prices." *Journal of Financial Economics* 32(1), 23–43. NBER WP 3846:
  https://www.nber.org/papers/w3846 (**directly fetched and verified 2026-09-01** — NBER's own
  public abstract page confirms 769 pension funds, 1985–1989, no substantial herding except in small
  stocks; upgraded to fully-confirmed FACT/EMPIRICAL EVIDENCE, see §3.5.)
- Harvey, C.R., Liu, Y. & Zhu, H. (2016). "…and the Cross-Section of Expected Returns." *Review of
  Financial Studies* 29(1), 5–68. NBER WP 20592: https://www.nber.org/papers/w20592 (**directly
  fetched and verified 2026-09-01** — NBER's own public abstract confirms the t>3.0 significance
  threshold recommendation verbatim; the abstract does NOT state an exact factor count — only
  "hundreds of papers and hundreds of factors" — so the "~316 factors" figure used earlier in this
  review, and the separately-sourced "3.39 FDR hurdle" figure, remain SOURCE CLAIM/UNKNOWN, not
  verified against the primary text this pass. Corrected from an earlier misidentified SSRN link
  (abstract_id=2345489, which is a different "Backtesting" paper) to the correct NBER working-paper
  record.)
- "Revisiting Boehmer et al. (2021)" (2024 working paper on arXiv, retail order-imbalance
  predictability, original sample 2010–2015 vs. later sample 2016–2021).
  https://ar5iv.labs.arxiv.org/html/2403.17095 (**directly fetched and verified 2026-09-01** —
  confirms large-cap predictability disappears and the full-sample long-short strategy becomes
  statistically insignificant in 2016–2021; small-cap one-week alpha specifically falls from 0.437%
  to 0.143%. Upgraded from SOURCE CLAIM to EMPIRICAL EVIDENCE, see §3.4. Still an arXiv preprint, not
  established as peer-reviewed.)
- Elton, E.J., Gruber, M.J. & Blake, C.R. (1996) — survivorship bias in mutual fund returns,
  ~0.9%/year figure. **UNKNOWN** — cited only via recurring secondary reference, not independently
  fetched or verified in this pass either; not attempted in the 2026-09-01 QA pass (lower priority
  than the five claims explicitly listed for re-verification).

Secondary / vendor / unverified (explicitly flagged, not to be cited as evidence of an edge):

- TradingView scripts, QuantVPS blog, LobeHub skill listing on order-flow imbalance / cumulative
  volume delta z-scores (§3.7) — practitioner/vendor content, no peer review, no academic validation
  found for this specific feature construction.
- Various Indonesia macro-foreign-flow news/journal search snippets (§3.10) — not independently
  fetched; listed as pointers for potential follow-up, not as verified findings.

**Explicit gap**: no source was found, fetched, or verified in this pass for a peer-reviewed,
stock-level, broker-flow predictive-return study specific to the Indonesia Stock Exchange (§3.10).

---

## Research-to-Empirical-Test Map

| Literature finding / hypothesis | Proposed test | Expected horizon | Expected mechanism | Expected heterogeneity | Multiplicity control |
|---|---|---|---|---|---|
| Contemporaneous order imbalance ↔ same-day return (§3.3) | Phase A baseline: contemporaneous regression | Same day (t) | Mechanical / price-pressure | Low — expected near-universal | N/A (control, not a discovery test) |
| Lagged aggregate order imbalance predicts next-day return, reverses after controlling for contemporaneous flow (Chordia-Subrahmanyam, §3.2) | Phase A: lagged total-flow regression, 1-day horizon, with contemporaneous control | 1 day | Price-pressure continuation (temporary) | Low-moderate | Pre-registered horizon; report alongside Phase B multiplicity-adjusted result |
| Retail/individual-type market-order flow predicts future returns up to ~20 days, no reversal at 60 days (Kelley-Tetlock, §3.4) | Phase B: investor-type-decomposed regression, 1/5/20-day horizons, plus 60-day reversal check | 1–20 days, reversal check to 60 days | Information-based (permanent) | High by investor type (market vs. limit order proxy, if constructible from IDX data) | Bonferroni/FDR across horizon × type grid |
| Foreign investor momentum/feedback trading, local-investor-type differentiated response (Vo 2017; Krohn et al. 2023, §3.5) | Phase B: foreign vs. domestic decomposition, lagged regression | 1–5 days (feedback-trading horizons reported in sources) | Herding / positive-feedback (behavioral) | High by foreign vs. domestic, and by domestic sub-type if available | Same grid-level FDR as above |
| Institutional herding is null at U.S. quarterly frequency but reported at emerging-market daily frequency (LSV 1992 vs. §3.5 EM studies) | Phase B: frequency-sensitivity check — re-run investor-type test at daily vs. weekly aggregation | Daily vs. weekly | Frequency-dependent — test, don't assume | Moderate — frequency itself is the heterogeneity axis | Treat as a robustness arm, not a new discovery claim |
| Liquidity/volatility-conditional predictability (§3.8) | Phase B: regime-split re-estimation (bull/bear, high/low volatility or spread) | Same horizons as the parent test, split by regime | Regime-dependent inventory/liquidity effect | High by regime | Regime splits add to the multiplicity grid — must be pre-registered, not post-hoc |
| Era decay of a structurally similar effect (§3.4, §3.8) | Phase B/C: split-sample re-estimation across the available IDX sample window | Full-sample vs. sub-period | Non-stationarity | By sample sub-period | Report all sub-periods, not just the best-fitting one |
| Multiple testing inflates false-discovery rate across factor/strategy studies generally (Harvey-Liu-Zhu, §3.9) | Phase C: apply an explicit multiplicity correction (higher t-stat bar or FDR) across the full set of Phase A/B specifications tested | N/A — applies across all horizons/types/regimes above | N/A — statistical correction, not a market mechanism | N/A | This IS the multiplicity control for the whole program |
