# PRIORS_X — verified citations for the {X} overnight-transmission screen · 2026-10-05

Brief gate (P0-A): "All three citations are unverified leads from the planner: confirm each one
exists and says what is claimed before you cite it. If none of the three can be verified with
≥ 10 years of published evidence, stop after Phase 0."

Verification method: author/NBER/institutional/open copies only (ScienceDirect, Wiley and SSRN
bot-walled per the standing rule). Each claim below quotes the source text verbatim with the URL
it came from. Status: 1 of 3 verified; the remaining two verifications are running and this file
is updated as they land (the screen cannot run before all three are dispositioned).

## 1 · Hamao, Masulis & Ng (1990) — VERIFIED ✅

**Citation:** Hamao, Yasushi; Masulis, Ronald W.; Ng, Victor (1990), "Correlations in Price
Changes and Volatility across International Stock Markets", *Review of Financial Studies* 3(2),
pp. 281–307. **No NBER working-paper version exists** (NBER's WP database has no HMN paper;
w3326 belongs to Hayashi–Inoue) — cite the RFS version only.

**Claim in the brief:** "NY → Tokyo/London spillover at the next open (the open-gap channel)."

**Evidence (verbatim, from the freely hosted JSTOR scan of the published article,
finance.martinsewell.com/stylized-facts/volatility/HamaoMasulisNg1990.pdf, OCR re-verified at two
resolutions; abstract identical on EconPapers):**

- Design is exactly the next-open setup: *"Unlike earlier studies, we divide daily close-to-close
  returns into their close-to-open and open-to-close components. This enables us to analyze
  separately the spillover effects of price volatility in foreign markets on the opening price in
  the domestic market and on prices after the opening of trading."*
- Sample: *"daily and intraday stock-price activity over the three-year period, April 1, 1985, to
  March 31, 1988 … daily open and close data from three stock markets: Tokyo, London, and New
  York"* (Nikkei 225, FTSE, S&P 500).
- Open-gap channel, full sample (Table 7 Panel A): *"the most recent open-to-close returns of the
  two foreign markets consistently have positive influences on the opening price in the next
  market to trade"* — **U.S. session → Tokyo open: Φ = .0181, t = 7.69; U.S. session → London
  open: Φ = .3200, t = 13.92**; reverse directions insignificant (Tokyo→London .0304, t = 1.10;
  Japan→U.S. .0027, t = 1.10). Pre-crash subperiod (Panel B): U.S.→Tokyo t = 8.00, U.S.→London
  t = 12.51.
- Sign: positive transmission (a high US return is followed by a high next-open return abroad) —
  the brief's predeclared positive sign for the raw transmission arm matches.

**Verdict: supports "US-session information transmits to the next market's open", with ≥ 30 years
of published standing (RFS 1990).** Caveat carried into the screen: HMN documents transmission
INTO the open — it says nothing about how much survives after the open, which is precisely what
the X1 outcome (open→close) and the absorption share measure.

## 2 · Levy & Lieberman (2013) — VERIFIED ✅ (brief's citation details corrected)

**Correct citation:** Levy, **Ariel**; Lieberman, **Offer** (2013), "Overreaction of country ETFs
to US market returns: Intraday vs. daily horizons and the role of synchronized trading",
*Journal of Banking & Finance* 37(5), pp. 1412–1421, DOI 10.1016/j.jbankfin.2012.03.024.
**The brief's details were wrong in four places** (authors' first names "Ohad/Ori"; subtitle
"intraday prices, trading volume, and volatility" belongs to no indexed version; issue 11,
pp. 4051–4063 wrong). Verified via Crossref, OpenAlex, IDEAS/RePEc, an Internet-Archive snapshot
of the publisher page, and citing papers.

**Claim in the brief:** "country ETFs overreact to US returns during non-synchronous hours; part
of the EIDO residual reverses."

**Evidence (verbatim):**
- Archived publisher abstract: *"during non-synchronized trading hours the S&P 500 index has a
  dominant effect. This effect also exceeds the one that the S&P 500 index has on the underlying
  foreign indices and suggests an overreaction to US market returns when foreign markets are
  closed."*
- The paper's own p. 1416 (quoted by Benson & Kong 2021, open PDF): *"This overreaction is then
  corrected for at the opening of the following US trading day."*
- Sample: 17 US-listed iShares country ETFs (nine Asian, eight European), 5-minute intraday data,
  per-ETF series starting ~2000 and ending 2010-12 (two independent citing sources agree on 17).
- Independent replications confirm the reversal with their own numbers (Benson & Kong 2021:
  next-day reversal coefficients −0.13 to −0.30 after ≥1% US drops, "for all seven countries";
  Ma 2015 McMaster thesis: Asian ETF overnight return negatively related to the lagged US
  return, "the price reversal effect does exist").

**Verdict: supports the overreaction + partial-reversal prior.** Two caveats carried into the
screen: (a) the paper locates the correction at the **next US open**; for a fully
non-synchronized market (IDX closed the whole US session) our open-to-close operationalization is
our own restatement, not the paper's exact words; (b) **EIDO itself is not in the sample**
(inception Jan 2010 vs sample ending 2010-12) — the IDX prediction is an extrapolation of a
verified mechanism. The paper's own reversal fraction is **not verified** (paywalled), so the
absorption-share prior is directional, not a magnitude forecast.

## 3 · Gagnon & Karolyi (2010) — VERIFIED ✅ (brief's title corrected; claim PARTIALLY supported)

**Correct citation:** Gagnon, Louis; Karolyi, G. Andrew (2010), "Multi-market trading and
arbitrage", *Journal of Financial Economics* 97(1), pp. 53–80, DOI 10.1016/j.jfineco.2010.03.005.
**The brief's title is wrong** ("…arbitrage energy: U.S.-listed international stocks" — no
"energy", no subtitle; verified via Crossref/OpenAlex/IDEAS + archived publisher page). No NBER
WP; the working-paper version is Ohio State Dice Center WP 2004-9 (sample 581 pairs / 39
countries / 1993–2002 vs the published 506 / 35 / 1993–2004 — version-specific numbers flagged).

**Evidence (verbatim, from the archived publisher page and the Dice WP PDF):**
- Published abstract: *"Deviations from price parity average an economically small 4.9 basis
  points, but they are volatile and can reach large extremes."*
- WP: most stocks trade *"within a 20 to 85 basis point band"*; tails reach *"a 66 percent
  premium to an 87 percent discount"* (Infosys / Jilin Chemical).
- Convergence: daily return differentials mean-revert (*"negative and significant mean-reversion
  (θ = −0.55)"*; nearly all pairs' reversion coefficients statistically significant); *"they
  rarely persist for longer than one day"* — but the paper simultaneously documents *"a
  significant degree of persistence"* (deviations can persist up to five days) and that
  deviations are *"positively related to proxies for holding costs that can impede arbitrage."*
  The phrase "arbitrage energy" appears nowhere in the paper.
- Indonesia is in the WP's 39-country sample (1 firm); TLK itself is not mentioned anywhere.

**Verdict: PARTIALLY supports the brief's use.** "ADR–home deviations exist and (mostly)
mean-revert within a day" is verified; "sizeable deviations" is true only in the tails (average
4.9bp); the convergence story carries persistence/holding-cost caveats. For the X1 TLK arm this
reads as: a weak, secondary prior — consistent with TLK being Tier 2 and with expecting any
ADR-vs-home edge to be small and fast-decaying.

## P0-A gate

All three citations verified to exist with ≥10 years of published standing (RFS 1990; JBF 2013;
JFE 2010). **The gate passes — no stop.** Two of three support the brief's claims as stated;
Gagnon–Karolyi is partial (existence + fast mean reversion verified, "sizeable" overstated).
All three corrections (Levy-Lieberman bibliographic details, Gagnon–Karolyi title, no NBER WPs
for HMN/GK) are recorded above and carried into the draft predeclaration's prior section.

## Note on NotebookLM ingestion

The brief asks that verified priors be ingested into the NotebookLM priors notebook. That
notebook was built on the XPS-13 session's Google login (2026-09-30 record) and is not reachable
from this host (no Google session here). PRIORS_X.md above is the equivalent local record with
verbatim quotes; ingestion is a handoff item for the main session.
