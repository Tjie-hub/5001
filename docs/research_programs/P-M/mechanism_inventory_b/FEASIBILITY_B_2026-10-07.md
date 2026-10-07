# FEASIBILITY B — mechanisms outside corporate actions, classes G–O (2026-10-07)

**Authority:** `ZCODE_BRIEF_MECHANISM_INVENTORY_B_2026-10-07.md` (e1aee99) + amendment 1
(2cec4db: reuse broad_search_v2 probes; class N; census flag) + amendment 2 (ed4b65e: class O).
Serves **D-070** §Decision 4 (feasibility gate before any registration). Companion to Task 2
(`research/structural-events-feasibility-2026-10` @ `1c20f56`, classes A–F).
**Branch:** `research/mechanism-inventory-b-2026-10` (from `a28ec7e`).

## Rule 1 — honored: no post-event price was read

Every price touch in the census is a slice **strictly before** the event's decision date
(pre-event vol = 60 sessions ending the day before; ADV20 = trailing 20 sessions ending the
session before). No return, price change or excess return on/after any decision date was
computed, printed or stored, for any horizon or aggregate; no full-sample return series is ever
materialized. Class O reads no price at or after the decision minute (09:15) in either window.
Class M is stopped on prior coverage and reports only formation-date counts, cross-section size
and pre-formation volatility. `HANDOFF.md` states this explicitly.

## Bars (owner ruling 2026-10-07; census ratified)

Census **N = 595** ratified under the stricter count
(`DECISION_DRAFT_CENSUS_RATIFICATION_2026-10-07.md` @ `2937488`, draft D-071:
270 recorded + 245 pattern studies + 20 double-top + 20 gap-battery + 6 X1 + 6 HYP-PM-0015 +
8 BOS + 20 exit study); bar 3.2912. Each new gate freezes at **595 + its own configurations**;
this inventory reports MDEs at **N = 599 → bar 3.2931 (primary)** and at the **276-count bar
(+ own arms, N = 280 → 3.0713, secondary line only)**. The brief's "276 vs 561" wording is
superseded. HYP-PM-0016 came back NULL at G1 (`b9e5e5b`), closing the price-feature search —
every class below therefore needs a named economic mechanism (D-070 §1).

## Data conventions (declared)

Panel: `research.rulecard.data.load_extended_ohlcv(issuance=True)` (D-053 backfill + DB corpus,
gap-verified split repair, D-064 issuance correction), 2000-03-30 → 2026-10-06, 958 tickers.
Liquid = ADV20 ≥ Rp 10 bn ending the session before the reference date. Pre-event vol = SD of
daily returns over the 60 sessions ending the day before (min 40). Eras: E1 = 2009..2021-09,
E2 = 2021-10..2026. Bars exact two-sided E[max|Z|] (`deflation_audit/bar_v2.py` method).

---

## G — global index rebalances (MSCI / FTSE)

**Mechanism (D-070 class: forced flow / rule constraint).** Passive funds tracking MSCI/FTSE
indices must trade add/delete names at a pre-announced effective date; the flow is mechanical,
price-inelastic and known about two weeks ahead (announcement → effective). This is the cleanest
forced-flow mechanism in the set — and the reason it cannot be tested here is pure data.

**Prior coverage.** Never run as a screen. The corpus object most like it — IDX80
reconstitution — is Task 2's class B (7 events / 26+26 flows since 2025, accepted only behind
the LQ45/IDX30 history acquisition). HYP-PA-0001 (reconstitution closing-auction dislocation,
FAILED F2 2026-08-19) tested a different mechanism on a different event. broad_search_v2 W2 §3:
**FTSE Russell usable no-auth** (notices JSON API: AnnouncedDate/EffectiveDate, ASEAN/GEISAC
tags, per-round CSV attachments); **MSCI blocked** (registration-gated). IX1 was sketched as a
forward recorder because IDX-relevant history is too short. In-corpus: no membership table;
`scheduler/scanner.py:889` `_event_guard_active()` holds ONE hardcoded window (paper_config
event_guard 2026-06-15..24, the MSCI accessibility review) — a config, not a date series.

**PIT dates / counts / power.** No events exist in the corpus; nothing to count. Panel risk
summary (NOT event power): 71 quarter-ends, median 71 liquid names, single-name 60-session σ
median 2.76% (IQR 2.05–4.07%). Parameterized MDE at bar 3.2931 (N events, ~4 event-months/yr
assumed): N=50 → 4.06% over 10 sessions independent (8.29% clustered); N=100 → 2.87%; N=200 →
2.03%. Index-add effects in the literature are ~1–3% cumulative over weeks — **marginal even at
N=100, and N is unknown until announcement dates exist.**

**Data gaps.** FTSE notices API scrape (no-auth): 1–2 days effort, PIT-quality
announcement+effective dates, backfill bounded by API paging depth. MSCI: registration-gated,
do not work around.

**Verdict: not a G0 candidate historically. The forward recorder (IX1 shape, FTSE only) is the
actionable item — it costs nothing and starts the PIT clock.**

## H — IPO lock-up expiry

**Mechanism (rule constraint → predictable supply).** Pre-IPO shareholders may not sell for
**8 months after listing** — **POJK No. 25/POJK.04/2017** (Pembatasan Atas Saham yang Diterbitkan
sebelum Penawaran Umum), effective 2017, verified against the state gazette
(peraturan.go.id ojk25-2017bt) and secondary analyses; tiered extensions above thresholds apply.
At expiry, restricted supply becomes sellable — a scheduled, rule-driven supply shock. Listings
before 2017 sat under the older Bapepam-LK regime (exact rule **not verified** — flagged).

**Prior coverage.** broad_search_v2 W1 LC2 / W2 §7: **blocked** — no free structured source for
actual lock-up terms (they live in prospectus PDFs behind the IDX wall). The empirical neighbour
is S2/`SCREEN-PM-LC-001` (D-064): young-listing underperformance PASS at screen level but
era-concentrated, `{LC}` NOT opened — lock-up expiry is the mechanism *behind* that result, so
any H study is **correlated with a recorded pass** and inherits the D-062 review.

**PIT dates.** Event date = first panel bar + 8 calendar months → first session on/after
(S2's first-bar proxy). Two declared weaknesses: (a) the statutory clock runs from the
registration statement's effective date, which precedes listing — the proxy is early by days to
weeks; (b) first-bar ≠ listing for backfill edges — 181 onboarding artifacts excluded (first bar
== corpus start 2021-07-05 or backfill start), pre-2017 listings carry the unverified-rule flag.

**Counts.** 542 listings since 2009 → 541 unlock events with data; **86 liquid unlock events**
(39 E1 / 47 E2), 63 event-months. Survivorship: the corpus holds names still listed at scrape
time (registry-disclosed limitation), so delisted-IPO expiries are missing — bias optimistic.

**Power.** Median pre-event σ 3.13% (IQR 2.20–4.56%). At bar 3.2931: **detectable ≥ 3.52% over
10 sessions independent (4.11% month-clustered)**; at 3.0713: 3.28%/3.83%. Field–Hanka-type
expiry effects are ≈ −1…−3% cumulative — **at or below MDE.**

**Verdict: skip. Underpowered AND the event dates are blocked (no PIT unlock dates) AND
correlated with the recorded {LC} pass. The owner vendor/IDX-direct decision that would unlock
LC2 would also unlock this — parked behind it.**

## I — suspension / resumption, Papan Pemantauan Khusus

**Mechanism (forced flow / rule constraint).** A halted name cannot be exited by mandates that
must liquidate (funds, margin); at resumption those forced exits meet pent-up liquidity
demand in a full-call-auction price-discovery window. Direction follows the mandate mix, not a
price pattern — a liquidity-provision/forced-flow mechanism.

**Prior coverage.** broad_search_v2 W1 TS1 / W2 §5: 359 real `suspension` events 2022-04+,
**expected underpowered** — this census confirms with numbers. Dataset B's gap classifier
documented that the recorded label cannot certify cleanliness. B4 (HYP-PM-0009): board
placement (Pemantauan Khusus) **unidentifiable in-corpus** — ABSENT here too.

**PIT dates and the taint finding.** `classification` and `gap_pct` are **outcome-tainted**:
`engine/suspension_detector.py` computes `gap_pct = (resume_open − last_close)/last_close` and
labels `suspension` when |gap| ≥ 10%. Per the brief only `last_normal_date`/`resume_date` (+
`missing_td`) are used in statistics; the recorded label is used only as a disclosed,
outcome-conditioned population filter. A **price-free** re-split is computed from
session-presence breadth (dataset_b rule: ticker-specific iff <50% of PIT-liquid peers also
absent on the missing sessions):

| population | rows | liquid resumptions | median σ | MDE10 @3.2931 indep / clustered |
|---|---:|---:|---:|---|
| all rows (upper bound incl. collection gaps) | 3,189 | 514 | 3.81% | 1.75% / 8.47% |
| recorded `suspension` label (label outcome-conditioned) | 359 | 87 | 5.94% | 6.63% / 25.24% |
| breadth ticker-specific (price-free) | 1,571 | 246 | 5.63% | 3.74% / 13.10% |

The remaining **1,618 episodes have no observable missing session** — their missing dates are
absent from the panel's session axis entirely, the market-wide/infra signature; they are not
resumption events by construction. All populations are E2-only (2022-04+; no pre-2021 history),
22 event-months.

**Power.** Clustering is what kills this class: 5–24× MDE inflation across populations. At the
bar, the best (upper-bound) population detects ≥ 8.47% over 10 sessions clustered; resumption
effects of that size would be visible to the eye on charts.

**Verdict: skip — TS1's expected verdict confirmed: underpowered at the bar in every population,
announcement-quality unverifiable (no IDX notices in-corpus), board data absent. A descriptive
first read of the archive remains available but is not a registered study.**

## J — earnings announcements (PEAD)

**Mechanism.** Investors under-react to new information in filings; the drift after
surprise is the classic risk-premium/attention story. It needs **point-in-time filing dates**.

**Prior coverage.** factor_zoo FUNDAMENTALS_ADDENDUM (2026-09-18): annual fundamentals acquired
(yfinance), every classic fundamental factor NULL on mean and median; size reversed; **restated
(not PIT) values** — a disclosed unfixable limitation.

**Inventory.** `stockbit_keystats`: 9,781 rows, 110 fetch dates **2026-04-10 → 2026-10-07**,
972 tickers — ratio snapshots with no period ends and no filing dates; ~6 months deep.
`fund_annual.pkl`: 2,217 rows / 552 tickers, period_end 2021-12-31 → 2026-06-30, **period ends
only, restated**. `data_gaps/scripts/fetch_quarterly.py` exists but its output
`fund_quarterly.pkl` is **ABSENT** — the brief's "2,908 quarterly observations" is **not
locatable in the repo; discrepancy recorded**. No PIT filing dates exist anywhere.

**Verdict: historically infeasible — mark as such.** Forward collection needs IDX financial-
statement **publication dates** (the exchange publishes per-company release schedules): a daily
scraper of the IDX/OJK announcement pages (idx.co.id is Cloudflare-blocked per v2 W2; the OJK
route or a commercial aggregator would need an owner decision), effort ~2–3 days to stand up +
one epoch of accumulation before any test. Until then J stays closed.

## K — calendar / institutional flow

**Mechanism.** Scheduled payroll/pension/mutual-fund inflows concentrate at month turns;
quarter/year-end window dressing by local funds front-loads order flow into the last sessions.
These are flow-timing mechanisms, not price patterns — but they are also the classic
data-mining zoo, so **exactly 2 windows are predeclared here and no window scan was run**
(no alternative offset was computed; anything beyond these 2 windows is a new census entry).

**PIT.** Trivially calendar — known forever.

**Counts and power** (EW liquid-book pre-window σ ≈ 1.06% both windows):

| window | definition | instances 2009+ (E1/E2) | MDE @3.2931, 10 sessions |
|---|---|---|---:|
| W1 turn-of-month | last session of month + first 3 of next | 213 (152/61) | **0.76%** (≈ 76 bp) |
| W2 quarter-end | last 5 sessions of Mar/Jun/Sep/Dec | 71 (51/20) | **1.33%** |

Both windows' MDEs at the secondary bar are within ~4% lower. W1 and W2 share 71 sessions
(quarter-end months) — the overlap is disclosed, not pooled away.

**Reading.** v2 CAL1 placed the turn-of-month literature effect at ~5–15 bp/day; over W1's
4-session window that is 20–60 bp cumulative — **below the 53 bp (4-session) MDE except at the
top of the range.** W2 at 71 instances detects only ≥1.87% over 20 sessions — decorative.

**Verdict: marginal — not a G0 candidate on its own.** If the owner wants it anyway, W1 pools
into ONE predeclared arm (v2's CAL1 pooled shape, N≈2,400 days, MDE ≈ 21 bp/day) as an
**execution-timing lens** (X1-overlay question: does the book buy cheaper inside the window?),
never as a family test. Lebaran/THR was **not** computed: no holiday archive exists in-corpus
and hardcoding recalled dates was judged too error-prone for a frozen inventory — it needs the
official IDX holiday calendar (small effort, backfillable) and would be a THIRD window (new
census entry).

## M — pooled cross-sectional short-term reversal — **STOPPED**

Covered/correlated, per the brief's stop: the mechanism (liquidity provision for absorbing
imbalance) is claimed by **Price-Reversal {R1,R2}** — HYP-PM-0012 / FWD-PM-FADE-001 and
HYP-PM-0014 / FWD-PM-BANK-001 are REGISTERED and **in forward test** (D-052, D-066-B); the
short-horizon flow-conditioned reversal was NO-GO'd at discovery (M2x, 2026-08-21); factor_zoo's
1-week reversal died in robustness (lottery-ticket illusion); and **D-062 bars any correlated
registration** while those tests are in flight. Allowed items only, reported:
**920 weekly formation dates** (660 E1 / 260 E2), median cross-section **72** liquid names,
pre-formation EW-book σ median **1.05%** (IQR 0.87–1.53%). No portfolio return exists in this
census.

## N — global commodity & geopolitical conditions → IDX exporter sectors

**Mechanisms (both stated for the D-entry draft).**
(a) **Cash-flow pass-through with slow diffusion** — commodity prices drive the earnings of IDX
exporters (coal, oil & gas, gold, nickel, CPO); local investors under-react over weeks, not
overnight. X2 tested the *overnight* version and was never run (sketch-only; coal/CPO blocked);
this class is the weekly/monthly version.
(b) **Geopolitical-risk premium** — in escalation regimes energy and gold names act as a hedge
while importers/consumer names carry the risk (GPR-conditional tilt).

**Prior coverage.** Never run (v2 W1 X2 = sketch-only). Correlation caveats for D-062: energy
names are high-volatility, so a commodity tilt overlaps the {V} (VOLEX-001) factor — the D-entry
must show vol-independence or accept the bar. X1 (US overnight → IDX) **ran and FAILED null
(t −0.30)** — a prior that tempers expectations for the fast end of the transmission but does
not cover the monthly diffusion.

**Mapping (`ticker_sector`, industry level, declared):** coal = Energy/Thermal Coal + Basic
Materials/Coking Coal (33); oil_gas = Energy O&G E&P/Drilling/Equipment/Refining (19); gold =
Gold + Other Precious Metals (6); copper_nickel = Other Industrial Metals & Mining + Aluminum
(21); cpo = Consumer Defensive/Farm Products (36; includes non-CPO agri — disclosed ambiguity).

**Counts and power** (monthly month-end rebalances 2009+: **214** = 153 E1 + 61 E2; PIT-liquid
book, pre-formation 60-session σ, bar 3.2931, MDE over a 21-session month):

| bucket | mapped | rebalances with ≥3 liquid | median book σ | MDE 20d (10d) |
|---|---:|---:|---:|---:|
| coal | 33 | 208 | 2.14% | **2.18%** (1.54%) |
| oil_gas | 19 | 138 | 2.14% | 2.68% (1.89%) |
| copper_nickel | 21 | 198 | 1.85% | **1.94%** (1.37%) |
| cpo | 36 | 202 | 1.78% | **1.85%** (1.31%) |
| gold | 6 | 36 | 2.84% | 6.97% — underpowered |

**Signal legs (probed, logged — the one permitted network fetch; `PROBE_LOG_N.json`):**
GPR (Caldara–Iacoviello) `.xls` export, 1,521 monthly rows, 1900-01 → **2026-09**, includes
**GPRC_IDN** (Indonesia country series) and threat/acts splits; **PIT lag: latest month 2026-09
vs today 2026-10-07 → ~1 month; a month-end M rebalance may use GPR through M−1 only** (exact
publication day to verify at G0). yfinance no-auth: GC=F, CL=F, NG=F, HG=F all 2000-08+;
NICK.L 2008-01+; BTU 2017-04+ (equity proxy). **Coal index (Newcastle/API2) and CPO futures have
no free no-auth source** (v2 W2 §2 confirmed) — globalcoal.com's historical NEWC page is the one
candidate (manual export, ToS unknown; ~1 day probe) — the coal bucket keeps BTU as proxy until
then.

**Verdict: the strongest new class in this inventory — pass.** Pooled monthly, mechanism-first,
signal data in hand, PIT lag declared, honest coal/CPO gap. Power says the effect must be
≥ ~1.9–2.2% per month in coal/copper_nickel/cpo books to clear the bar — commodity-driven
monthly sector dispersions reach that in trending regimes, but this is a power statement, not a
prior. **One caveat to carry into any G0: the vol-correlation with VOLEX (D-062).**

## O — opening-auction order imbalance (minute bars)

**Mechanism (liquidity provision).** IDX opens with a pre-opening call auction (08:45–08:59).
When opening orders are imbalanced, liquidity providers fade the imbalance and the price
reverses after the open — a liquidity-provision mechanism, not a breakout pattern. Local
evidence: the v2 A-OPEN audit found exactly the auction-clearing signature — unchanged-open
rates exceed the diffusive benchmark because **the pre-opening call clears AT the previous
close when imbalance is small**. The PBFJ (1995) Indonesian intraday study found reversals
dominating continuations at the open; the US ORB literature (Zarattini–Aziz–Barbon;
Gao–Han–Li–Zhou) finds the opposite (momentum), and a 2026 independent ORB replication found it
gross-positive but **net zero**. Which applies to IDX: the auction-clearing evidence and the
PBFJ reversal result are the applicable priors; the US ORB momentum prior assumes continuous
quoting that IDX's call-open does not provide, and its net-zero replication already discounts it.

**Prior coverage.** Crypto ORB (port 5002) is a separate market — not counted. broad_search_v2
A-OPEN (audit; opens genuine). HYP-PM-0009 (I7, intraday execution timing on
`stockbit_flow_bars` v004 cohort) FAILED F2 — the same instrument at a different estimand; the
D-050 no-power-claim constraint does not transfer here but the null tempers the family.
D-059: the 0.60% RT floor is materially understated by fee+tax reality (~0.4% before impact).

**Data.** Frozen store `data/frozen/stockbit-flow-bars-v002/` (sha `fa7f07b3…`, 2025-01-02 →
2026-04-27, 77.5M minute rows, 958-ticker scope; read-only, production host). Live
`stockbit_flow_bars` continues 2026-04-28 → onward. **Cumulative check (this census,
deterministic sample, lots only):** buy_lot/sell_lot/buy_freq/sell_freq are nondecreasing
within the day — cumulative as the planner suspected; **per-minute flow = first differences.**

**Seen-window disclosure.** The planner has read descriptive statistics on 2025-01 → 2026-04-28
IDX30 (volatility profile, first-15-minute range shares 41% median, high-in-first-15 46.7% vs
low 33.8% — weakly directional). **2025-01 → 2026-04-28 is therefore SEEN for class O; any
future test's confirmation sample starts 2026-04-28 (live DB).**

**Imbalance proxy (declared).** The 09:00 bar is cumulative-from-day-start, so it *is* the
first-minute flow, including the opening-auction print: `imbalance₀ = (buy_lot − sell_lot) /
(buy_lot + sell_lot)` at 09:00, known by 09:01. The store starts at 09:00 — **no pre-open
indicative price or auction imbalance exists anywhere in-corpus**; the proxy is the best legal
substitute. Pre-open auction data would need a new feed (owner decision).

**Power (pre-09:15 only; no price at/after 09:15 read in either window).** From the frozen
store: **44,217 liquid ticker-days** (ADV20 ≥ 10 bn) across 309 sessions; cumulative-lots
verification 60/60 clean; **98.2%** of liquid ticker-days have a computable 09:00 imbalance
(median |imbalance₀| = **41.3%** — IDX opens are heavily imbalanced); pre-09:15 minute σ
median **0.445%** (IQR 0.30–0.68%), with a **48.6% flat-minute share** disclosed (carried
prices dilute σ; the iid minute scaling is optimistic on top of that). MDE at bar 3.2931:
45-minute horizon (09:15→10:00) **0.05% of price independent-n / 0.56% date-clustered**;
to close (275 min) **0.12% / 1.38%**. The independent-n figures are not decision-relevant —
44k ticker-days are ~309 date clusters, and clustering is what any test bears. Costs: IDX RT
fees+tax ≈ 0.4%, tick 0.31–1.32% of price on mid names; **only 2.5% of liquid ticker-days
have one tick ≤ 0.2% of price.** Against 0.56–1.38% clustered MDEs and ≥0.4% round trips +
tick, **the class is not tradable as a standalone intraday book.** The preferred framing is
**execution timing** (the owner's existing entries — sniper limits, EOD-plan buys — choosing
when in the first hour to execute, at no extra round trip; X1's overlay logic, noting X1
itself returned NULL).

**Clean window.** **109** live sessions since 2026-04-28 (panel calendar; the live table
has no trade_date index and a production full scan was skipped). At ~21 sessions/month, a
confirmation sample accumulates quickly in ticker-days but only ~1 date-cluster per session —
date clustering is the binding constraint, and the seen window cannot be recovered for
confirmation.

**Verdict: not a G0 candidate. Forward-collection candidate only, execution-timing framing,
clean sample accumulating since 2026-04-28.**

---

## Mechanism D-entry drafts (DRAFT ONLY — number D-0xx at filing; nothing filed)

Per `ZCODE_BRIEF_SNIPER_G0_REVISION_2026-10-07.md` §Task 2: "Task 3's combined ranking produces
those drafts" — A and D are the owner-accepted G0 pair; N is this inventory's recommendation as
the next class. B's draft is conditional on the index-history acquisition.

### Draft — Tender offers (Task 2 class A)
**Mechanism:** a tender offer is a rule constraint that sets a hard, contractual price floor
with a convergence deadline (offer close): the discount to offer price is an arbitrage spread
bounded by deal risk, not a price prediction. **Direction:** long offered names below the offer
price; the spread converges to zero at close or widens with deal-break risk. **Costs:** pooled
calendar-time book, ADV20 ≥ Rp 10 bn names only, 0.60% RT floor + D-059 modeled cost — the
spread at entry must clear the floor by construction of the eligibility rule. **Falsification:**
if the pooled spread net of cost does not converge (mean ≤ 0 with the frozen bar), or losses
concentrate in withdrawn deals the rule failed to exclude ex ante, the mechanism is refuted.
**Multiplicity:** joins the census with its own arms at filing (N = 595 + own).

### Draft — Dividend ex-dates (Task 2 class D)
**Mechanism:** forced flow around a scheduled corporate action: pre-ex demand from
dividend-capture and yield buyers meets post-ex supply, with Indonesian retail tax
asymmetries (withholding on gross dividends) segmenting who holds through the ex-date.
**Direction:** pre-declared from the tax-clientele split; the pooled design predeclares
event-month clustering (530 multi-event tickers) and the era risk (560 of 574 liquid events
E2). **Costs:** 0.60% RT floor against a declared per-event gross effect; only the pooled
portfolio is tested. **Falsification:** pooled post-ex excess ≤ 0 or sign flip across halves
at the frozen bar kills the class; the D-064 ex-date monitor (detection-only) continues
regardless.

### Draft — Commodity pass-through / GPR risk premium (class N)
**Mechanism:** commodity prices drive the near-term earnings of IDX exporter books, and local
price discovery diffuses the news over weeks (under-reaction), so the trailing 4–12-week
commodity return tilts the matching sector book at the next monthly rebalance; separately, in
geopolitical-escalation regimes energy/gold books carry a hedge premium (GPR overlay, used
through its declared ~1-month publication lag). **Direction:** long the sector book after a
favorable commodity trailing return / in elevated GPR regimes; short-side never (long-only
tilt vs the EW book). **Costs:** monthly rebalance, turnover-capped, 0.60% RT + D-059 modeled
cost; tilt names are liquid (ADV20 ≥ Rp 10 bn). **Falsification:** if the pooled tilted book's
monthly excess vs the EW book is ≤ 0 at the frozen bar across both eras, or the effect is
absorbed by the {V} volatility factor (D-062 check), the pass-through mechanism is refuted.
**Coverage honesty:** coal uses the BTU equity proxy from 2017-04 (no free API2/CPO index);
gold is 6 mapped names only. **Multiplicity:** N = 595 + own arms at filing.

### Draft (conditional) — IDX index reconstitution (Task 2 class B)
**Mechanism:** mechanical passive buys/sells at a pre-announced effective date. Held behind the
LQ45/IDX30 history acquisition (Task 2 gap 1); 7 events / ~52 flows today is not testable.
File only after sourcing multi-year constituent history; then pool across indices and years.

---

*No post-event price was read in producing this document (see HANDOFF.md). Numbers:
`CENSUS_FEASIBILITY_B.json` from `census_feasibility_b.py` (the one census script).*
