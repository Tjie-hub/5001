# ZCODE BRIEF — `{X}` cross-asset overnight transmission: acquire, then ONE pre-registered screen

**Issued:** 2026-10-05 by the main session (XPS-13) at the Owner's request ("set a new finding edge on
ZCode") · **Branch:** `research/new-order-2026-09-30` · **Host:** Windows PC `tjiejet` — repo
`D:\IDX`, **compute and every `git commit` from WSL Ubuntu** (scripts are never committed from the
Windows side — exec-bit discipline, per the data-acquisition handoff). Fetches may run on either side.
**Output dir (the only place you write):** `docs/research_programs/P-M/cross_asset/`
**Authority:** acquisition + screen only. You may not register a hypothesis, open a forward test,
consume a family slot, or edit `DECISION_LOG.md`, `HYPOTHESIS_REGISTRY.md`, `FAILURE_REGISTRY.md`,
`EXPERIMENT_LEDGER.jsonl`, `CENSUS_UPDATE.md` or any frozen protocol. Draft proposed entries in your
output dir; the Owner decides them.

---

## 0. Mission and why this family

Every in-house family is spent, null or in flight (see `broad_search/FAMILY_MAP_v2.md` §2 and D-064).
The data-acquisition scoping (`data_acquisition/HANDOFF_…_2026-09-30.md`) ranked `{X}` **#1**:
it is the only lane with a working free data path (TLK ADR 1995→, USD/IDR, IHSG via yfinance), and
nothing in our null set ever touched cross-asset transmission. Any day without the series is
overnight data lost for good.

The question is narrow: **does information priced in the US session after the IDX close (the US-listed
Indonesia basket EIDO, the TLK ADR, the broad US market) predict the IDX session that follows, and is
that prediction still capturable *after* the IDX open?** A clean null is a full success.

**The framing that makes this worth running at all is the execution-timing overlay.** A day-trade
built on an overnight signal is dead on arrival: 0.60% round trip versus effects of a few bp/day.
But using the signal only to choose **when** to execute a trade that is already decided costs no
extra round trip. "Buy at the open or at the close?" and "sell at the open or at the close?" add no
turnover, stay long-only, and the saving is the whole edge. That is the primary use. A standalone
strategy is reported only as an observability lens.

## 1. Read first (in this order)

1. `data_acquisition/04_CROSS_ASSET_SERIES_FEASIBILITY_2026-09-30.md` — your own POC, PIT notes, the
   214-day USDIDR=X gap, and the ADR ratio caveat. **The POC pair (`fetch_crossasset_poc.py` +
   `SAMPLE_OUTPUT_crossasset_poc.json`) was never committed.** Commit both from WSL first, in this
   brief's first commit.
2. `priors/D-065_PROPOSAL_2026-09-30.md`. It is a proposal and not yet in force, but **this brief
   complies with it voluntarily**: prior first, tradeability rule, one pre-registered test per
   hypothesis, LW base book plus IHSG as co-benchmark. If the Owner rejects D-065, nothing here
   loosens.
3. `priors/POWER_BENCHMARK_MEMO_2026-09-30.md` (MDE geometry) and
   `priors/NOTEBOOKLM_PRIORS_2026-09-30.md` (the priors shelf; which sources ingest and which are
   bot-walled).
4. `docs/roadmap/DECISION_LOG.md` **D-062 … D-064**. D-064 §C gives the exact two-sided bar
   (**3.06 at N = 266**), and D-064 §D covers `issuance=True`.
5. `broad_search/` is **the template**: PREDECLARATION + `.sha256` committed before the run → script
   → RESULT json → VERDICT. Also read `broad_search/CHECKER_REVIEW_2026-09-29.md`: the defects it
   found (era concentration, an untested independence claim, the wealth-correction rule) are exactly
   what the next checker will look for.

## 2. Phase 0 — acquisition + prior verification (no outcome data may be read)

**P0-A · Prior verification (D-065 §1: "no prior, no test").** Use the author/NBER/institutional
copies; ScienceDirect, Wiley and SSRN are bot-walled. Ingest these into the priors notebook and quote
sign, magnitude, sample and t from the sources themselves. **All three citations are unverified
leads from the planner: confirm each one exists and says what is claimed before you cite it.**
- Hamao, Masulis & Ng (1990), *RFS*: NY → Tokyo/London spillover at the next open (the open-gap
  channel).
- Levy & Lieberman (2013), *J. Banking & Finance*: country ETFs overreact to US returns during
  non-synchronous hours. **This predicts that part of the EIDO residual reverses**, so it is the
  prior for the sign *and* for the capturability doubt.
- Gagnon & Karolyi (2010), *JFE*: ADR–home-market price deviations and their convergence (the TLK arm).

If none of the three can be verified with ≥ 10 years of published evidence, **stop after Phase 0**
and report the series acquisition alone. The data still has recorder value.

**P0-B · Series.** Fetch with yfinance into `cross_asset/data/*.csv`. Write one manifest
(`MANIFEST.json`) recording the source, fetch UTC, yfinance version, `auto_adjust` setting, row
count, date range and sha256 of every file. Commit the CSVs; they are small.
- `EIDO` (iShares MSCI Indonesia, US-listed since 2010-05): total-return-adjusted closes. This is the
  primary signal leg.
- `TLK` (NYSE ADR): adjusted closes. **List every ADS-ratio change date** and confirm that no ratio
  change shows up as a return. The POC memo says 1 ADS = 20 ordinary shares; verify it and its
  history.
- `SPY`: adjusted closes (broad-US arm).
- `USDIDR=X`: locate and explain the 214-day gap. **Add BI's JISDOR only if it can be downloaded
  publicly without auth**; if not, say so and leave it. No logins, no CAPTCHA, no scraping behind
  auth (standing rule).
- `^JKSE` is **alignment only**. IDX prices for the book come from our corpus (rule 4).

**P0-C · Calendar + timing contract (`TIMING.md`).** WIB = ET + 11 (EDT) / + 12 (EST); state the DST
handling. Write an explicit diagram covering IDX day *d* (09:00–16:00 WIB), US session *d*
(≈ 20:30 WIB *d* → 03:00/04:00 WIB *d*+1), and IDX day *D* = the next IDX session. **Contract: every
signal input carries a timestamp ≤ 08:45 WIB on day D.** IDX prices that enter the signal are
`close(d)` or earlier. Handle these cases:
- US holiday ⇒ no signal.
- IDX holiday ⇒ the signal spans every US session between the two IDX closes; predeclare the
  aggregation.
- Half-days and the IDX session-hour changes (Ramadan, 2020 COVID hours): list them.

**P0-D · Counts, power and the corpus.** No conditioning on any signal is allowed in this step.
- Count usable (signal, outcome) days per split. Discovery-as-replication = 2010-05 → 2021-06
  (`ohlcv_long`); confirmation = 2021-07 → latest.
- The unconditional σ of the LW-book and TLKM open→close returns may be read here. Use it, together
  with the counts alone, to compute the MDE at the bar for each arm and record it.
- **Open-price quality pre-2021.** Check `data_acquisition/07_OHLCV_PRE2021_FEASIBILITY_2026-09-30.md`
  and measure `open == close`, `open == prev close` and zero-volume shares per year. If pre-2021
  opens are unreliable, the discovery half becomes **descriptive only**; predeclare that now, not
  after the run.
- State the delisted coverage of `ohlcv_long` (survivorship, brief-standard rule).

## 3. Phase 1 — ONE predeclaration, ≤ 6 arms, then one run

`PREDECLARATION_X1_OVERNIGHT.md` + `.sha256`, committed **before** any outcome read. It fixes:

**Signal.** `R_D = r_EIDO[US close(d−1) → US close(d)] − β̂_d · r_JKSE,USD[close(d−1) → close(d)]`
(the IDX-close-to-close return in USD terms). `β̂_d` is a rolling 250-session OLS that uses only pairs
ending ≤ d. Standardize by the trailing-250 σ of R (PIT). The TLK arm uses the same construction with
TLK and TLKM (USD-converted). The SPY arm is the raw `r_SPY[US close(d−1) → US close(d)]`, standardized
the same way. **Predeclared sign: positive for every arm** (US-session information leads the next
IDX session).

**Outcome (primary) = open(D) → close(D)**: the capturable leg. **Lens (rides inside its arm, not an
arm):** the gap `close(d) → open(D)`. Report the *absorption share* = gap slope ÷ (gap slope +
open→close slope).

**Book.** LW (cap-proxy) liquid universe with adv20 ≥ Rp 5bn, formed with information ≤ d. Apply the
D-065 §2 tradeability rule: `volume > 0` on day D, and no carry-forward rows. Benchmarks: the LW book
itself and IHSG (open→close from our corpus if available; otherwise state which source and why).
Prices come through `research.rulecard.data.load_extended_ohlcv(issuance=True)`, with `issuance=True`
recorded in params. No hand-rolled `SELECT … FROM ohlcv` (CI fails it).

**Arms (6; census +6):**

| arm | signal → outcome | split | role |
|---|---|---|---|
| X1-A | EIDO residual → LW book open→close | 2021-07 → latest | **PRIMARY** |
| X1-B | same | 2010-05 → 2021-06 | replication (sign must match) |
| X1-C | TLK residual → TLKM open→close | 2021-07 → latest | single-name, Tier 2 |
| X1-D | same | 2010-05 → 2021-06 | replication |
| X1-E | SPY → LW book open→close | 2021-07 → latest | broad-risk comparator |
| X1-F | same | 2010-05 → 2021-06 | replication |

**Estimator.** Time-series slope of the outcome on standardized `R_D`, with a Newey-West t (5 lags).
The headline is per-day. Also report tercile means (bottom / middle / top) and their year-by-year
breakdown. Year-by-year is mandatory: era concentration is what downgraded S2.

**Pass rule (primary).** X1-A slope > 0 with **|t| ≥ the exact two-sided bar after your 6 arms
join**: N = 270 (D-065 notes XP-001's 4 arms) + 6 = 276. Recompute it with
`docs/research_programs/deflation_audit/bar_v2.py` and write the number into the predeclaration
before the run (≈ 3.07). Also required: X1-B has the same sign, and the absorption share is < 0.8.

**Kill rules.**
- X1-A below the bar ⇒ FAIL (null).
- X1-B has the opposite sign ⇒ FAIL.
- Absorption share ≥ 0.8 with an insignificant open→close slope ⇒ **"real but not capturable"**.
  That verdict counts as a FAIL for trading, but record the information finding.
- Any single calendar year carrying more than half of the primary's t ⇒ the verdict is at most
  "era-concentrated, not opened" (the D-064 S2 precedent).

**Economics (reported, not gating).**
1. **Timing-overlay value.** On bottom-tercile days, deferring a planned buy from open to close saves
   −E[open→close | bottom]. On top-tercile days, deferring a planned sell saves E[open→close | top].
   Express it in bp per affected trade, and the share of trading days affected. Name the IDX
   **pre-closing call auction** as the close-fill mechanism and its realistic fill assumption; do not
   assume a free close print. Run the same calculation on last month's EOD-trade-plan entry list as
   an illustration only (read-only, from the snapshot).
2. **Standalone observability.** A top-tercile open→close long, net of the 0.60% RT floor and D-059
   modeled cost. It is expected to fail; say so if it does.

**Correlation (D-062).** The signal is exogenous to IDX price paths, so overlap with FADE-001,
REGIME-002 and VOLEX-001 is expected to be small. Measure it anyway: report the correlation of `R_D`
with each recorder's daily entry count. Declare it; do not assume it.

## 4. Hard rules (unchanged from the broad-search brief, which is binding by reference)

All twelve of `ZCODE_BRIEF_BROAD_EDGE_SEARCH_2026-09-29.md` §4 apply, especially: predeclare then run;
PIT; costs gross and net; long-only; **stop rule** (a pass ⇒ stop, no refinement, no variants);
reproducibility (every driver committed next to its RESULT; every run through `research/tracking.py`
with run_id, git sha and dataset fingerprint; the D-063 F-1 rule); read-only on production data.
Specific to this host:
- **Corpus.** Preferred: the XPS-13 snapshot `walkforward-20261004-213000.db.zst` (sha256
  `8408e91a3a77fddf9bfe88c443d284f6e1190761aa986c850e4e35aaad4db3ba`, integrity ok). The Owner
  copies it over Twingate; P1-5 has no automatic path. Decompress it, verify the sha and
  `PRAGMA integrity_check`, then record its fingerprint. If the Owner has not copied it, the local
  `D:\IDX\data\walkforward.db` is acceptable. In that case record its fingerprint and `max(date)` and
  say so in every RESULT. **Never raw-copy a live DB.**
- **Do not run the P1 research-DB cutover as part of this brief.** If `research/tracking.py` cannot
  write cleanly because P1 is half-done on WSL, stop and report it. That outranks the screen.
- **Budget: 6 arms, one run.** A crash before outcomes print may be re-run; disclose it. A re-run
  after outcomes print is a new arm and needs the Owner's approval.

## 5. Deliverables (in order)

**Phase 0:** `PRIORS_X.md` (verified citations, or "unverified, stopped"), `data/` + `MANIFEST.json`,
`fetch_cross_asset.py`, `TIMING.md`, `PHASE0_COUNTS.md` (counts, σ, MDE per arm, open-quality table,
survivorship line). Commit before Phase 1.
**Phase 1:** the predeclaration + sha, committed; `screen_x1_overnight.py` committed in the same freeze
commit; then the one run → `RESULT_X1_<utc>.json`.
**Phase 2:** `VERDICT_X1_OVERNIGHT.md`, `CENSUS_NOTE.md` (+6 arms and the new bar; a proposed append
to `broad_search/CENSUS_UPDATE.md`, not executed), and `HANDOFF_CROSS_ASSET_<date>.md` containing:
proposed (not recorded) DECISION_LOG text; a proposed FAILURE_REGISTRY-style note if the result is
null; and **a separate recommendation on a forward EIDO/TLK/SPY/USDIDR recorder**, which is worth
running whatever the verdict.

**Timing.** Phase 0 by ~2026-10-12; Phases 1–2 by ~2026-10-26. The VOLEX/FADE maturities from
mid-October take priority if they need the box.

## 6. What "done" looks like

Four series acquired with a manifest and an honest gap report. A timing contract a checker can
audit. Verified priors, or an honest stop. One predeclared 6-arm screen with a verdict, a capturability
split and year-by-year stability, all regenerable from committed code. Most likely outcome: the
information is real but mostly absorbed at the open, so the result is "real but not capturable",
plus a recorder proposal. That is a fine result.
