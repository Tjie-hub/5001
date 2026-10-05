# ZCODE BRIEF — Broad search v2: everything not yet run, plus probes of new sources

**Issued:** 2026-10-05 by the main session (XPS-13) at the Owner's request ("broaden the test — what is
not run yet, including checks from new sources") · **Roles:** Claude (XPS-13 session) = **planner and
reviewer**; ZCode = executor · **Branch:** `research/new-order-2026-09-30` · **Host:** Windows PC
`tjiejet`, repo `D:\IDX`. Compute and every `git commit` happen in WSL Ubuntu; fetches may run on
either side.
**Supersedes the scope of** `ZCODE_BRIEF_CROSS_ASSET_TRANSMISSION_2026-10-05.md`. That file is kept as
the detailed spec of workstream X1 (§4 below). Its output paths are remapped to `broad_search_v2/x1/`.
**Output dir (the only place you write):** `docs/research_programs/P-M/broad_search_v2/`
**Authority:** census accounting, inventory, source probes and pre-declared screens only. You may not:
- register a hypothesis, open a forward test or consume a family slot;
- edit `DECISION_LOG.md`, `HYPOTHESIS_REGISTRY.md`, `FAILURE_REGISTRY.md`, `EXPERIMENT_LEDGER.jsonl`,
  `broad_search/CENSUS_UPDATE.md` or any frozen protocol;
- touch any forward-test ledger or recorder.

Proposed entries are drafts in your output dir; the Owner decides them.

---

## 0. Mode statement (read this first)

D-065 (a proposal, not yet in force) would close exploratory sweeps "unless the Owner explicitly
re-opens the mode, with a census priced in advance". **The Owner's 2026-10-05 instruction is that
explicit re-opening, for this brief only.** Three conditions come with it:
1. **The census is priced in advance.** W0 must finish before any screen is declared.
2. **Every screen still needs an external prior first** (D-065 §1).
3. **No screen is run if its MDE at the bar exceeds its prior's plausible effect.** The RC-0001
   precedent applies: "not tested, underpowered" is a valid, honest outcome and spends no arm.

## 1. Review gates — you stop at each one and wait

| gate | you deliver | then you STOP until this file exists |
|---|---|---|
| **R1** | W0 + W1 + W2 outputs + `HANDOFF_R1.md` | `broad_search_v2/REVIEW_R1_<date>.md` (planner selects the screens and arm budget) |
| **R2** | predeclarations + drivers committed (frozen, not run) + `HANDOFF_R2.md` | `REVIEW_R2_<date>.md` containing **GO** for each screen |
| **R3** | one run per screen → RESULTs + VERDICTs + `HANDOFF_R3.md` | `REVIEW_R3_<date>.md` (checker re-run of any PASS before it reaches the Owner) |

Review files are written on XPS-13 and reach `D:\IDX` through Syncthing. Do not write them yourself,
and do not treat a chat message as a substitute for one.

## 2. W0 — census reconciliation (BLOCKING; do it first)

**Reviewer finding, 2026-10-05.** The D-062 census (252 → 266 → 270 with XP-001) does **not** include
the 2026-09-25 chart-pattern work. That covers: exhaustion flags (both sides), the order-flow overlay,
the **72-variant confirmed-exhaustion grid**, double top / double bottom (14 + 6 arms), lower-high
rejection (24 tests + 12 LONG mirror), the BBCA/big-4 climax-low study and its pre-2021 OOS, the
same-stock hedge, the EMA200 rejection, the staircase bottom and the parabolic studies. The
deflation audit names none of them. Their drivers sit **untracked** in
`Claude outputs/exhaustion_study_2026-09-25/` (12 files, ~1,350 lines), which is the same failure
class as F-1.

1. **Count the arms** from those scripts and from the results recorded in memory/notes, using the
   D-061 convention: each pre-declared or reported grid cell whose primary statistic was computed
   counts as one arm, and lenses ride inside their arm. Write `CENSUS_RECONCILIATION.md` with one row
   per study. Where the count is uncertain, take the upper bound and say so.
2. **Recompute the exact bar** with `docs/research_programs/deflation_audit/bar_v2.py` at the
   reconciled N. Planner's estimate: N ≈ 420–450 ⇒ **bar ≈ 3.19–3.21** (exact E[max|Z|]: 3.06 @ 270,
   3.19 @ 420, 3.21 @ 450). This bar, plus this brief's own arms, governs every screen below.
3. **Re-read the survivors at the new bar** (D-062 table plus S2): which recorded statistics still
   clear? Report only; change no verdict.
4. **Driver custody.** Do **not** commit `Claude outputs/` yourself; P0-5 left it as an Owner call.
   Copy the scripts into `broad_search_v2/w0_pattern_drivers/` with a sha256 manifest. If the Owner
   approves at R1, that copy becomes the committed record.
5. Note for the Owner (no action from you): the BBCA/big-4 climax-low pre-2021 OOS (BBCA t 2.36,
   BIG-4 t 2.23) sits far below the reconciled bar and is `{R1}`-correlated with FADE-001. It is
   **not** a screen in this brief.

## 3. W1 — untested inventory (`UNTESTED_INVENTORY.md`)

Build one table for every candidate ever named in `RULE_FIRST_PROTOCOL_2026-09-24.md` §6,
`broad_search/FAMILY_MAP_v2.md`, `data_acquisition/*`, `priors/*` and the seeds below. Columns: id ·
family · status (`never run` / `map-closed` / `underpowered` / `data-blocked` / `forward-only` /
`gated by D-062` / `spent`) · external prior (verified Y/N) · data source · PIT · MDE at the
reconciled bar · independence from §2 of the v1 brief · recommendation.

Seeds the planner already knows are **not run**:

| id | candidate | why it is open | external prior to verify |
|---|---|---|---|
| X1 | US-session → IDX next session: EIDO residual, TLK ADR, SPY (open→close, timing overlay) | new data, never touched | Hamao-Masulis-Ng 1990; Levy-Lieberman 2013; Gagnon-Karolyi 2010 |
| X2 | Commodity overnight → IDX sector names open→close (gold→ANTM/MDKA, oil→MEDC/ELSA, coal→ADRO/PTBA/ITMG, nickel→INCO/NCKL, CPO→AALI/LSIP) | new data; coal/CPO were negative in the POC, so probe proxies | commodity-equity lead-lag (e.g. Driesprong-Jacobsen-Maat 2008 oil; verify) |
| CAL1 | Turn-of-month execution timing (last day + first 3 days) | parked table covered Ramadan only; ToM never assessed | Lakonishok-Smidt 1988; McConnell-Xu 2008 (35 countries) |
| CAL2 | Pre-holiday effect (IDX has ~15 holidays/yr incl. Lebaran) | never assessed; n ≈ 200 events at 2013→ | Ariel 1990; Kim-Park 1994 (intl) |
| IX1 | MSCI/FTSE Indonesia ADD events, announcement → effective (widened C4) | C4 was "forward-only" only for HYP-PA-0001's own events; MSCI/FTSE lists are a **new source** | Harris-Gurel 1986, Shleifer 1986; IDX LQ45/MSCI evidence [V] in RULE_FIRST |
| N1 | Search/page attention spikes (Google Trends, Wikipedia pageviews) | `{N}` was blocked only for `news_mentions`' 5-month depth; these sources go back 2004 / 2015 | Da-Engelberg-Gao 2011 (JF) |
| LC2 | Lock-up expiry supply shock (mechanism test of the `{LC}` lead) | calendar never built; 158 liquid listings, curated by hand | Field-Hanka 2001 |
| C3 | 52-week-high proximity, long | never run; **gated by D-062 until ~2026-10-19 and REGIME-002's first read**; double sort vs trend onset | George-Hwang 2004; Liu-Liu-Ma 2011 |
| TS1 | Suspension/UMA resumption (avoidance) | data-blocked; the archive depth is the open question | weak prior (IDX event study null) — inventory only unless the archive is deep |
| BI1 | BI rate-decision days → banks (timing) | never assessed; ~12 events/yr | verify; likely underpowered — let the MDE decide |

Add anything else you find in the corpus. **Do not seed from memory of past pattern scans**: those
are spent.

## 4. W2 — new-source probes (feasibility + POC, no outcome reads)

One short memo per source in `broad_search_v2/sources/`, in the same format as
`data_acquisition/0x_*.md`: source; access/credentials; ToS stance; date range; gaps; PIT semantics
(when is each value knowable in WIB); a one-run POC with its output captured; effort to productionize.
**Standing rule:** public, no-auth sources only. No logins, CAPTCHA bypass, Cloudflare evasion or
scraping behind auth. If a site blocks, record "blocked" and move on; the Owner rules on it.

| probe | sources to try | key PIT question |
|---|---|---|
| P-X | yfinance `EIDO`, `TLK`, `SPY`, `EEM`, `USDIDR=X`; BI **JISDOR** public download | US-close→WIB mapping; the 214-day USDIDR gap |
| P-CMD | yfinance `GC=F`, `CL=F`, `BZ=F`, `HG=F`; coal (`MTF=F` / other Yahoo coal tickers — probe); nickel (probe); CPO proxies via Bursa plantation equities (`2445.KL`, `5285.KL`) and `BTU` | settlement vs last-trade timestamp; futures roll handling |
| P-IX | MSCI and FTSE public index-review press releases/PDFs (Indonesia adds/deletes, 2013→); IDX index-review announcements **only if reachable without bypass** | announcement datetime (WIB) vs effective date; overlap with HYP-PA-0001's event set |
| P-ATT | Wikimedia pageviews REST API (official, 2015-07→; id/en articles per issuer); Google Trends via `pytrends` (**unofficial: check ToS and stay rate-limit-polite; if unclear, stop and flag**) | weekly vs daily granularity; Trends re-normalization per request (look-ahead trap) |
| P-TS | IDX suspension/UMA announcement archive depth (public pages only) | does it reach 2015–2020? |
| P-CAL | IDX trading/holiday calendar 2010→ (from our corpus's session dates + public holiday lists); BI board-meeting dates (public BI site) | holidays known in advance: yes; confirm each source date |
| P-LU | Lock-up dates for the 158 liquid listings from public prospectuses (e-ipo.co.id / IDX listing pages), **only if public no-auth**; sample 20 first and report the hit rate | prospectus date ≤ listing date |

## 5. W3 — screen menu (the planner selects at R1; you predeclare only what R1 approves)

For every candidate in the inventory with a verified prior, a usable source and an MDE below its
plausible effect, draft (do **not** commit or run) a one-page screen sketch: rule, estimand, ≤ 2
horizons, split (pre-2021 = discovery-as-replication, 2021-07→latest = confirmation), benchmarks (LW
base book **and** IHSG, per D-065 §3), arms, kill rule, MDE. Expected shape:

- **X1:** 6 arms, as specified in the v1 brief §3.
- **X2:** a commodity composite per sector → sector book open→close, 2 halves. Keep it to ≤ 4 arms,
  so pool the sectors instead of running one arm per commodity.
- **CAL1 / CAL2:** execution-timing overlays (no extra turnover), 2 arms each.
- **IX1:** announcement→effective drift, 2 arms. **Exclude every event within ±5 sessions of a
  HYP-PA-0001 review date**, so the post-hoc subgroup cannot confirm itself.
- **N1 / LC2:** 2 arms each, only if the probes produce ≥ 10 years (N1) or a curated calendar (LC2).

**Total budget for this brief: ≤ 30 arms.** The planner will probably approve 3–5 screens. Every
estimate is reported gross and net. Use D-059 modeled cost; timing overlays report the per-trade
saving instead. Long-only; an anti-edge is an avoidance filter only.

## 6. Hard rules

All twelve rules of `ZCODE_BRIEF_BROAD_EDGE_SEARCH_2026-09-29.md` §4 bind by reference: predeclare
then run; multiplicity; PIT; price loading through `load_extended_ohlcv(issuance=True)` with the flag
recorded; costs; long-only; inference (Newey-West/clustered, per-date headline); survivorship;
reproducibility via `research/tracking.py` + the F-1 rule; correlation (D-062); the **stop rule**; and
read-only production data. Plus:
- **Corpus:** XPS-13 snapshot `walkforward-20261004-213000.db.zst` (sha256
  `8408e91a3a77fddf9bfe88c443d284f6e1190761aa986c850e4e35aaad4db3ba`), if the Owner has copied it. If
  not, use the local `D:\IDX` copy, with its fingerprint and `max(date)` recorded in every RESULT.
- **Year-by-year breakdown is mandatory in every RESULT.** A verdict carried by one calendar year is
  at most "era-concentrated, not opened" (the D-064 S2 precedent).
- Do not run the P1 research-DB cutover. If `research/tracking.py` cannot write cleanly, stop and
  report; that outranks every screen.
- One run per frozen screen. A crash before outcomes print may be re-run, with disclosure. Anything
  after that is a new arm and needs a new R2 GO.

## 7. Timing

- **R1 by ~2026-10-12.** W0 comes first and is small. W2 probes are about a day each; start with
  P-X, P-CMD, P-CAL and P-IX.
- **R2 by ~2026-10-19.** This lines up with the D-062 window, so C3 becomes eligible then.
- **R3 by ~2026-10-31.**
- VOLEX/FADE/REGIME maturities from mid-October take the box first if needed.

## 8. What "done" looks like

- A reconciled census with an honest bar.
- One inventory table of everything never run, each with a reason.
- A feasibility memo per new source.
- 3–5 screens, each predeclared, reviewed and run once, with verdicts a checker has reproduced.

The likely outcome is mostly nulls or "real but not capturable", one or two recorder proposals, and
an inventory that shows the remaining search space is genuinely small. That is a successful result.
