# Phase 8 Provenance Closure Audit

**Date:** 2026-09-03 · **Branch:** `ops/hardening-2026-07-10` · **Scope:** SOURCE AUDIT ONLY
**Subject:** `engine/historical/` — `crabel_orb.v1`, `crabel_open_stretch.v1`, `raschke_nr7.v1`
**Hard boundary honored:** no backtest, no walk-forward, no optimization, no parameter
recommendation, no performance/profitability claim, no strategy ranking was produced.

---

## 0. Sources recovered

| ID | Source | Recovery result |
|---|---|---|
| S1 | Crabel, *Opening Range Breakout* series, **Technical Analysis of Stocks & Commodities** — Part 1 V.6:9 (337–339), Part 2 V.6:10 (366–368), Part 3 V.6:12 (462–465), Part 4 V.7:2 (47–49), Part 5 V.7:4 (119–120), Part 6 V.7:5 (161–163), Part 7 V.7:6 (188–189), Part 8 V.7:7 (208–210) | **Article bodies NOT recovered** (paywalled, store.traders.com). Publisher article records recovered, containing quoted rule language. Series enumeration confirmed: 8 parts, 1988–1989. |
| S2 | Crabel, **Day Trading with Short Term Price Patterns and Opening Range Breakout**, Traders Press, 1990 | **PRIMARY TEXT RECOVERED.** 304-page scan with an Adobe Paper Capture OCR layer, hosted on archive.org. Chapter 1 method statement, book introduction, report/test methodology sections, and the full **Glossary (pp. 281–287)** are legible. |
| S3 | Raschke & Connors, **Street Smarts**, 1995/96 | **PRIMARY TEXT RECOVERED.** Full text, table of contents, Chapters 19 and 20 verbatim. |
| S4 | Sklarew, *Techniques of a Professional Commodity Chart Analyst* | **PRIMARY SOURCE NOT RECOVERED.** Only secondary descriptions of the "Rule of Seven" recovered. |

### 0.1 Witness-quality caveat (must not be concealed)

S2 and S3 are **uncontrolled digital witnesses** — third-party scans/reproductions, not
publisher-controlled editions. S2 additionally carries OCR noise (glossary headwords are visibly
mangled: `~ RAll6E (OR)`, `OPENDC RM«;E BRFAKaJ'l'`). Rule *sentences* extracted below are clean and
internally consistent, and S2's glossary is corroborated by the independent S1 publisher records
(two different Crabel-derived witnesses agree on Stretch and on the opening-range duration band).
Nonetheless:

- Page-level fidelity and edition identity are **not** guaranteed.
- S3's chapter *numbering* is edition-specific (see finding R-1).
- Every "DIRECT PRIMARY" below means *recovered from primary text via an uncontrolled witness*,
  not *verified against a publisher-controlled copy*.

---

## 1. Deliverable table

| Item | Historical Rule | Primary Evidence | Status | Implementation Consequence |
|---|---|---|---|---|
| **C-1** NR7 definition | "a daily range that is narrower than the previous six days **compared individually** to the day in question" | S2 Glossary, p. 285 | **DIRECT PRIMARY** | `nr7.py` window (t−6…t, compare set = previous six) is correct. Citation must move from the 1988 article to the 1990 book. |
| **C-2** NR7 tie handling | "**narrower than** … compared individually" — an equal range is not narrower | S2 Glossary, p. 285 | **DIRECT PRIMARY** | Resolves unresolved item #8. `TiePolicy.STRICT_LESS` is the primary-supported policy; `TiePolicy.MIN_INCLUSIVE` (`<=`) **contradicts** primary text and must not be selectable for a historical run. |
| **C-3** NR7 → next-session ORB | "The ORB is effective after inside days … and for that matter after any day that has a daily range less than the previous six days (NR7) whether an inside day or not"; "the ORB the following day in each case provides an excellent entry" | S2 Ch. 1 | **DIRECT PRIMARY** | Confirms setup-day-never-trades / execute-at t+1. No change. |
| **C-4** Stretch formula & lookback | "The Stretch is determined by looking at the previous ten days and averaging the sum of the differences between the open for each day and the closest extreme to the open on each day" | S2 Ch. 1; corroborated verbatim in S1 Parts 7 & 8 records | **DIRECT PRIMARY** | `stretch.py` mean of `min(|O−H|,|O−L|)`, lookback 10, is correct. |
| **C-5** Stretch window anchor day | "the **previous** ten days" — anchor day never named | S2 Ch. 1 | **ENGINE CONVENTION — SOURCE-INSUFFICIENT** | Current window t−9…t (inclusive of setup day, exclusive of execution day) is the reading consistent with computing the Stretch before the execution open. Keep, but relabel from "recovered" to convention. |
| **C-6** ORB entry mechanics | "a buy stop is placed that amount above the high of the opening range and a sell stop is placed the same amount below the low of the opening range" | S2 Ch. 1 + Glossary p. 284 | **DIRECT PRIMARY** | `crabel_orb.v1` entry is correct. |
| **C-7** Protective stop | "The first stop that is traded is the position and the other stop is used as a protective stop" | S2 Ch. 1 + Glossary p. 284 | **DIRECT PRIMARY** | `protective_for()` is correct. |
| **C-8** **Opening-range duration** | "**OPENING RANGE (OR) — is the first thirty seconds of trade of each trading day**" | S2 Glossary, p. 285. Corroborated by S1 Parts 7 & 8: "the range of prices that occur in first 30 seconds to 5 minutes of trading" | **DIRECT PRIMARY** | Resolves unresolved item #1. `opening_range_minutes: int` **cannot express 30 seconds**. The docstring claim "Crabel experimented 5/10/15 minutes by liquidity" is unsourced and is contradicted by both witnesses; remove it. |
| **C-9** Definition of the open | "OPEN is the first trade registered in the time period under consideration" | S2 Glossary, p. 284 | **DIRECT PRIMARY** | No change. |
| **C-10** Session boundaries | Not stated generally. Only an incidental stock-index remark ("open to 1:30") in the PIONEER RANGE entry | S2 Glossary, p. 285 | **PRIMARY SOURCE NOT RECOVERED.** | `SessionDefinition` stays a required engine parameter. Current handling is correct. |
| **C-11** **Deterministic Crabel exit** | "the number of days into the trade (**zero indicates an exit on the close the same day of entry, five indicates an exit on the close five days after the entry**)"; "an exit on the close of the same day of entry"; "**no stops were used on the tests**" | S2, report methodology (Inside Day report and Tables A–H) | **DIRECT PRIMARY** (for the book's own research protocol) | Resolves unresolved item #3. MOC-after-N-sessions is *not* merely an engine convention — it is the primary-documented test protocol, N ∈ {0…5}. But `ExitConvention` requires `moc_hold_sessions >= 1` and **cannot express N = 0**, which is the book's baseline case. Also the protocol runs **without** a protective stop; the bracket kernel always applies one. |
| **C-12** Discretionary trading exit | "the objective of these entry techniques is to establish a position for a two to three day run, but this can be considered only if a substantial profit is realized by the end of the session" | S2 Ch. 1 | **PRIMARY SOURCE NOT RECOVERED.** (guidance, not a mechanical rule) | Unchanged; current provenance wording is accurate. |
| **C-13** Break-even timing | "In general stops should be moved to break even within one hour after entry. A market that displays greater tendency to trend should be given less than an hour" | S2 Ch. 1 | **DIRECT PRIMARY** (intraday statement) | Daily-bar mapping remains **ENGINE CONVENTION — SOURCE-INSUFFICIENT**. `BreakevenPolicy` docstring is accurate as written. |
| **C-14** Simultaneous / both-side trigger | "Stops were not used and **if the market traded both above and below the opening range the given amount, a buy and a sell could be registered**" | S2, Inside Day report | **DIRECT PRIMARY** (for the test protocol: both sides register, no OCO) | Resolves unresolved item #7 *for the test protocol only*. Intra-session ordering for the Ch.1 OCO trading rule is still unstated → `AmbiguityPolicy` remains an engine convention. A "both register" mode is required to replicate Crabel's own tests. |
| **C-15** Gap-through-stop fill | No fill rule stated anywhere. S2's GAP glossary entry is a *pattern* definition, not a fill convention | S2 (exhaustive search) | **PRIMARY SOURCE NOT RECOVERED.** | `GapPolicy` correctly remains an engine convention. |
| **C-16** **ORB vs constant-distance / open-based variant** | "Opening range breakout is defined as a trade taken at a predetermined amount **off the open**… when I introduce this trading concept in Chapter One I use a mathematical technique, called the stretch… In later testing you will notice that **I use a constant value off the open rather than the stretch point**. Experience has shown this to be a better method." Tests use "Open plus 16 tics… Open minus 16 tics" | S2 Introduction + report methodology | **DIRECT PRIMARY** | Crabel documents **two** constructions and explicitly distinguishes them: (a) **Stretch off the opening range** (Ch. 1 trading method); (b) **constant tick value off the open** (the book's test method). See A2 finding below. |
| **A2-1** `crabel_open_stretch.v1` = Open ± **Stretch** | Not stated. The primary text pairs the open anchor with a **constant value**, not with the Stretch, and presents them as alternatives | S2 Introduction | **PRIMARY SOURCE NOT RECOVERED.** | A2 as implemented is a **synthesis of two separate primary constructions**, not a recovered rule. **Keep Tier B** (per mandate). Its `historical_rules` entry "Buy = Open + Stretch; Sell = Open − Stretch" must be demoted out of `historical_rules`. The historically attested open-anchored variant is Open ± *constant tick value*. |
| **A2-2** A2 attributed to the 1990 book | The 1990 primary text was recovered and does **not** state Open ± Stretch; open-anchored entry is however attested in S1 Part 5 ("a trade taken at a predetermined amount above or below the **opening price**") | S1 Part 5 record; S2 | **PRIMARY SOURCE NOT RECOVERED.** (for the composite rule) | Citation currently says "full text not recovered" — that is now false; the text *was* recovered and does not support the rule. Provenance must be corrected to say so. |
| **R-1** Street Smarts chapter attribution | TOC: Ch. 16 = **"NEWS"**; Ch. 19 = **"RANGE CONTRACTION"** (p. 109); Ch. 20 = **"HISTORICAL VOLATILITY MEETS TOBY CRABEL"** (p. 115) | S3 TOC + chapter bodies | **DIRECT PRIMARY** | `raschke_nr7.v1` cites "Chapters 16 and 20". **Chapter 16 is about news trading and contains no setup.** Citation must become Chapters 19 and 20. |
| **R-2** The Raschke rule set is **ID/NR4**, not NR7 | Ch. 19 rules 1–5 are stated for "an ID/NR4"; Ch. 20's setup is "either an inside day or an NR4 day" plus a 6/100-day historical-volatility ratio under 50% | S3 Ch. 19, Ch. 20 | **DIRECT PRIMARY** | The numbered rule set the implementation encodes belongs to **ID/NR4**, not to NR7. |
| **R-3** NR7 in Street Smarts | The *only* NR7 passage: "One of the simplest concepts which I use regularly is Toby's NR7. This represents the narrowest range of the last seven days. I automatically use this as a **filter to switch to a breakout mode** the day following an NR7. This means that I will not try to countertrend trade. Instead, I will try and enter the market in the direction it is moving." | S3, end of Ch. 19 | **DIRECT PRIMARY** — and it establishes a **negative**: Street Smarts contains **no NR7 entry/stop/exit rule set** | `raschke_nr7.v1` is a **transfer** of the ID/NR4 mechanics onto the NR7 setup. Its `ProvenanceTier.TIER_A_DIRECT` claim is **not supported**. NR7 is also explicitly attributed by Raschke to Crabel ("Toby's NR7"). |
| **R-4** One-tick entry | "The next day only, place a **buy-stop one tick above** and a **sell-stop one tick below** the ID/NR4 bar" | S3 Ch. 19 rule 2; Ch. 20 rule 3 | **DIRECT PRIMARY** (for ID/NR4) | Entry geometry is correct — but is primary for ID/NR4, not NR7. |
| **R-5** Stop **and reversal** | "if we are filled on the buy side, enter an additional sell-stop one tick below the ID/NR4 bar. This means that if the trade is a loser, not only will we get stopped out with a loss, **we will reverse and go short**"; Ch. 20: "This additional sell-stop is done on the **entry day only, and expires on the close of this day**" | S3 Ch. 19 rule 3; Ch. 20 rule 4 | **DIRECT PRIMARY** | **Implementation contradicts primary evidence.** `engine/historical/` contains **no reversal logic at all** (grep for `revers` returns zero hits), and no same-day expiry of the opposite stop. The recovered rule is stop-**and-reverse**, not a plain protective stop. |
| **R-6** Raschke exit | "**If the position is not profitable within two days and you have not been stopped out, exit the trade MOC (market on close.)**" | S3 Ch. 19 rule 5 | **DIRECT PRIMARY** | Resolves unresolved item #4 **in part**. The provenance claim "no deterministic mechanical exit for ID/NR7 is recovered" is **incorrect**: a conditional two-day MOC time stop is specified. |
| **R-7** Raschke trailing stop | "Trail a stop to lock in accrued profits" (Ch. 19 rule 4); "I will stay in the position as long as it continues to move in my favor. Usually though, I am out within one to four days" (Ch. 20) | S3 | **PRIMARY SOURCE NOT RECOVERED.** (no mechanical trail specified) | Any trailing mechanism remains an engine convention. |
| **R-8** ID / NR4 / NR7 relationship | "An NR4 is a trading day with the narrowest daily range of the last four days. An inside day has a higher low than the previous day's low and a lower high than the previous day's high. Combining the two conditions sets up an ID/NR4 day." Crabel: "NR4 — narrower than the previous three days compared individually"; "NR7 — narrower than the previous six days compared individually" | S3 Ch. 19; S2 Glossary p. 285 | **DIRECT PRIMARY** | The two books agree. N in NR*N* counts the day itself. `setup_lookback: 7` with a six-day compare set is correct. |
| **R-9** Tick-size definition | "one tick" = the instrument's minimum price increment; no era-specific definition is needed for the rule to be well-formed | S3 Ch. 19/20 | **DIRECT PRIMARY** (rule); the numeric value is an **exchange/instrument fact**, not a historical unknown | The provenance line "Instrument tick-size definition for '1 tick': PRIMARY SOURCE NOT RECOVERED." **overstates the gap**. Unresolved item #5 should be reclassified as an instrument parameter. |
| **S-1** Sklarew lineage | Neither primary text mentions **Sklarew** or the **Rule of Seven** (0 occurrences in either full text). The Rule of Seven is described in secondary sources as a *price-objective projection* method (multipliers 7/5, 7/4, 7/3), unrelated to range contraction | S2, S3 exhaustive search; S4 secondary only | **PRIMARY SOURCE NOT RECOVERED.** (Sklarew's own text) — but the Phase 8 negative finding is **strengthened** | **Phase 8 finding MAINTAINED.** Crabel's primary text defines NR7 himself, with no attribution to Sklarew; Raschke attributes NR7 to Crabel. Do not resurrect the lineage. |

---

## A. Rules now proven by direct primary evidence

Newly closed by this audit (previously carried as unresolved or as unsourced assertions):

1. **Opening-range duration = the first thirty seconds of trade** (S2 Glossary). Contemporaneous
   S1 records widen this to a **30-second–5-minute** band. *(Was unresolved item #1.)*
2. **NR7 tie handling is settled by the definition itself** — "narrower than … compared
   individually" excludes equality. *(Was unresolved item #8.)*
3. **Crabel's deterministic exit exists in primary text**: exit on the close, N days after entry,
   N ∈ {0…5}, with **no stops** in the test protocol. *(Was unresolved item #3.)*
4. **Simultaneous triggering in Crabel's test protocol**: both a buy and a sell may register; no
   OCO is applied there. *(Was unresolved item #7, partially.)*
5. **Raschke's exit is partly specified**: not profitable within two days and not stopped out →
   exit MOC. *(Was unresolved item #4, partially.)*
6. **Raschke's stop is a stop-and-reverse**, with the reversal order living on the entry day only
   and expiring at that day's close.
7. **The Raschke rule set is an ID/NR4 rule set**, and **Street Smarts contains no NR7 rule set** —
   NR7 appears there only as a breakout-mode bias filter attributed to Crabel.
8. **Crabel distinguishes ORB-off-the-opening-range (Stretch) from constant-value-off-the-open**,
   and states the latter is what the book's tests use.

Already-claimed rules that this audit **confirms** against primary text: NR7 definition (C-1),
NR7→next-session ORB (C-3), Stretch formula and 10-day lookback (C-4), ORB entry construction
(C-6), opposing-stop-becomes-protective-stop (C-7), break-even-within-one-hour (C-13),
one-tick entry geometry (R-4), ID/NR4/NR7 relationship (R-8).

## B. Rules still source-insufficient

`PRIMARY SOURCE NOT RECOVERED.`

- Historical **session boundaries** for the traded market/era (C-10).
- **Gap-through-stop fill behavior** (C-15) — searched exhaustively in S2; no fill convention exists.
- **Crabel's discretionary trading exit** as a mechanical rule (C-12) — only "two to three day run"
  guidance. *(The book's* test *exit is recovered; his* trading *exit is not.)*
- **Raschke's trailing-stop mechanism** (R-7).
- **`crabel_open_stretch.v1`'s composite rule "Open ± Stretch"** (A2-1) — the primary text pairs the
  open anchor with a *constant value*, and pairs the Stretch with the *opening range*.
- **Intra-session trigger ordering** for Crabel's Ch.1 OCO trading rule on daily bars (C-14).
- **Sklarew's primary text** (S-1) — the negative finding nonetheless holds and is strengthened.
- **The full 1988 S&C article bodies** (S1) — recovered only as publisher records; every rule the
  1988 series would have supported is independently recovered from S2.

## C. Engine conventions that may remain configurable

These are engine choices, **not** historical rules, and must stay declared, hashed, and never
presented as historically proven:

- `GapPolicy` (fill-at-open vs cancel) — C-15.
- `AmbiguityPolicy` for the Ch.1 OCO trading rule on daily bars — C-14.
- `SessionDefinition` (session_start / session_end) — C-10.
- `BreakevenPolicy` **daily-bar mapping** of the intraday one-hour statement — C-13.
- **Stretch window anchor day** (t−9…t) — C-5. *Newly reclassified from "recovered" to convention.*
- Any **trailing-stop** mechanism for System B — R-7.
- Cost application to PnL only, raw-basis trigger geometry, rejection telemetry, rule-identity
  hashing — all engine scaffolding, correctly labelled today.

## D. Required implementation changes

Listed **only** where the current implementation contradicts recovered primary evidence or asserts
provenance it does not have. No change here is motivated by convention or by what would be more
usual.

**D-1 — `raschke_nr7.v1` provenance tier is unsupported.** Street Smarts states no NR7 rule set
(R-3). The encoded mechanics are ID/NR4 mechanics (R-2). Either (a) implement `raschke_id_nr4.v1`
against the actually-recovered Ch. 19 rule set and demote the NR7 variant to a declared,
non-primary transfer, or (b) keep the NR7 variant but drop `TIER_A_DIRECT` and record the transfer
explicitly. It cannot stay Tier A as written.

**D-2 — `raschke_nr7.v1` citation is wrong.** "Chapters 16 and 20" → **Chapters 19 and 20**;
Chapter 16 is "News" (R-1).

**D-3 — Missing stop-and-reverse.** Primary rule 3 is a reversal, and the reversal order expires at
the entry day's close (R-5). There is no reversal logic in `engine/historical/` at all. Either
implement it or declare the omission as a deliberate deviation from the recovered rule.

**D-4 — "No deterministic exit recovered" is false for System B.** Rule 5 (not profitable within
two days → exit MOC) must move from `unrecovered_items` into `historical_rules` (R-6).

**D-5 — `crabel_orb.v1` cites a source that does not carry the rules.** The Tier A citation is the
1988 S&C Part 1 article, whose body was **not** recovered; NR7 and the NR7→ORB linkage are recovered
from the **1990 book**. Add S2 as the primary citation for C-1/C-2/C-3.

**D-6 — Unsourced claim in `crabel_orb.py`.** "Crabel experimented 5/10/15 minutes by liquidity" has
no primary support and is contradicted by two independent witnesses (30 seconds; 30 s–5 min).
Remove it, and replace the "Opening-Range duration: PRIMARY SOURCE NOT RECOVERED" line with the
recovered definition (C-8).

**D-7 — `opening_range_minutes: int` cannot express the recovered OR.** A 30-second opening range
is not representable in whole minutes (C-8). The parameter must carry sub-minute resolution, or the
system must declare that it runs a deliberately non-historical OR duration.

**D-8 — `ExitConvention` cannot express the primary test protocol.** `moc_hold_sessions >= 1`
excludes N = 0, the book's baseline same-day exit; and the protocol uses **no protective stop**
while the bracket kernel always installs one (C-11, C-14). A faithful replication mode is required.

**D-9 — `TiePolicy.MIN_INCLUSIVE` contradicts the primary definition** (C-2). It may remain in the
codebase only as an explicitly ahistorical legacy-parity mode; it must not be selectable for a run
claiming historical fidelity.

**D-10 — `crabel_open_stretch.v1` provenance overstates and misstates.** "Buy = Open + Stretch" is
not a recovered rule (A2-1) and must leave `historical_rules`; the citation's "full text not
recovered" is now false — the text was recovered and does not support the composite (A2-2). Tier B
is **retained**, per mandate and now for a documented reason.

**D-11 — Overstated gap in System B.** "Instrument tick-size definition for '1 tick': PRIMARY
SOURCE NOT RECOVERED." should be reclassified as an exchange/instrument parameter (R-9).

**D-12 — Record the witness-quality caveat** (§0.1) in the provenance objects: recovery is from
uncontrolled scans, not publisher-controlled editions.

Not required, and deliberately not recommended: any change to the NR7 window, the Stretch formula,
the ORB entry construction, the protective-stop mechanic, the raw-vs-adjusted data basis, or the
`stored_raw` limitation disclosure. All of those survive the audit intact.

## E. Backtest readiness decision

**HOLD.**

The provenance gate moved substantially — six previously unresolved items are now closed by direct
primary evidence, and the two books were recovered in full-text form. But three material
*historical-rule* ambiguities remain open, and two of them are contradictions rather than gaps:

1. `raschke_nr7.v1` implements a rule set that its cited source does not state for NR7 (D-1, D-2),
   and omits the reversal that source does state (D-3). A backtest today would measure a composite
   whose provenance label is wrong.
2. `crabel_orb.v1` cannot represent the recovered opening range (30 seconds) or the recovered test
   protocol (N = 0, no stops) (D-7, D-8), so a run would silently substitute engine conventions for
   rules that are now known.
3. `crabel_open_stretch.v1` encodes a composite the recovered primary text distinguishes into two
   different constructions (D-10).

Additionally, the `stored_raw` limitation stands: signal geometry is only genuinely raw for
post-rebuild history, and a 30-second opening range is not constructible from the corpus at all
without sub-minute intraday data. That is a data-availability blocker for System A independent of
provenance.

**Historical-source completeness gate: substantially advanced, NOT CLOSED.**
**Backtest gate: HOLD.**

---

## Appendix — Correction record (2026-09-03, same day)

The D-items above were implemented. This appendix records what changed, so the
audit and the code cannot drift apart.

| D-item | Resolution |
|---|---|
| D-1 | `raschke_id_nr4.v1` implemented (`engine/historical/raschke_id_nr4.py`) against Ch. 19 rules 1-5 + Ch. 20 rule 4, Tier A. `raschke_nr7.v1` demoted to the new `ProvenanceTier.TIER_T_TRANSFER` and must declare `adaptations` (enforced at registration). |
| D-2 | Citations corrected to Chapters 19 and 20 on both Raschke systems. |
| D-3 | `ReversalPolicy.ENTRY_DAY_ONLY` implemented in `runner.py`; the reversed leg is a separate `HistoricalTrade` recording `reversal_expiry="entry_session_close"`. Not available to the Crabel configs. |
| D-4 | `ExitKind.MOC_IF_UNPROFITABLE_AFTER_N_SESSIONS`; rule 5 moved into `historical_rules`. |
| D-5 | `crabel_orb.v1` now cites the recovered 1990 book as primary; the S&C series is labelled corroborating-only, bodies not recovered. |
| D-6 | The "5/10/15 minutes by liquidity" claim is deleted. |
| D-7 | `opening_range_minutes: int` → `opening_range_seconds: int`; `RECOVERED_OPENING_RANGE_SECONDS = 30`. `tick_opening_range_provider` takes `source_resolution_seconds` and returns `OpeningRangeUnavailable("insufficient_intraday_resolution")` rather than widening the window. |
| D-8 | `moc_hold_sessions >= 0` (N = 0 = entry-session close); `ProtectiveStopMode.NONE_TEST_PROTOCOL` rests no stop and records `stop_level_raw = None`. |
| D-9 | `HISTORICAL_TIE_POLICIES` / `is_historical_tie_policy`; `STRICT_LESS` is the default on every historical config; `MIN_INCLUSIVE.__doc__` states it is ahistorical legacy parity. |
| D-10 | "Open ± Stretch" moved from `historical_rules` to `adaptations`; the stale "full text not recovered" citation removed; Tier B retained. |
| D-11 | Tick size reclassified as an exchange/instrument parameter on both Raschke systems. |
| D-12 | `HistoricalProvenance.witness` is mandatory; every spec carries `UNCONTROLLED_WITNESS`. |

Two model changes were needed to express the corrections without lying by
omission, and both are enforced at registration:

- `HistoricalProvenance.adaptations` — rules the engine runs that **no** primary
  source states. `TIER_B` and `TIER_T` cannot register with it empty.
- `HistoricalProvenance.discretionary_guidance` — recovered author *advice*
  ("a two to three day run"). It is primary text, so it is not an unrecovered
  item; it is not executable, so it is not a historical rule.

Rule identity moved to `hist-identity-v2`: `nr7_tie_policy` → `setup_tie_policy`
(ID/NR4 and NR7 are different setups), plus `protective_stop_mode` and
`reversal_policy` as required fields. Every historical id therefore changes —
deliberately, because the rules they identify are now stated more precisely.

**The backtest gate decision in section E is unchanged by this appendix.** The
implementation contradictions it cited are resolved; the data-availability
blocker it also cited is not, and is restated in the correction report.
