# W1 · INVENTORY — every idea never run, with status, prior, data, power · 2026-10-05

Companion to the W2 probe memos (`W2_SOURCE_PROBES_2026-10-05.md`) and the W3 sketches
(`W3_SCREEN_SKETCHES_2026-10-05.md`). Bar context: after the W0 recount the working bar is
**|t| ≥ 3.25** (census 515 + arms; exact values recomputed per screen at freeze).
Power column = MDE of the sketch's primary at the pre-declared N and unconditional σ
(.bp/day per 1σ of signal, or per-event where event-study). All ten ideas were checked against
the broad-search v1 spent-list (`FAMILY_MAP_v2.md` §2, D-061/D-064): **none has ever been run.**

| id | idea | status | published prior (sign, magnitude, standing) | data path (W2 verdict) | power at the 3.25 bar | recommendation |
|---|---|---|---|---|---|---|
| **X1** | US session (EIDO/TLK/SPY) → next IDX session | **P0 COMPLETE this session**: 7 series + JISDOR acquired+manifested, TIMING contract, counts/σ/MDE, TLK ADS gate PASS, priors 2/3 verified; DRAFT predeclaration ready | Hamao-Masulis-Ng 1990 RFS ✓ (US→next-open t 7.7–13.9); Levy-Lieberman 2013 JBF ✓ (overreaction + next-open correction; magnitudes unverified); Gagnon-Karolyi pending | **no-auth, done** (yfinance + BI JISDOR) | MDE 14–22bp/day per 1σ at N 839–2,174; primary 1,166 days | **RUN** (detailed spec; Owner gates R1/R2) |
| X2 | Overnight commodities → matching IDX sectors | never run; data probed | none verified in-corpus (corpus silent); commodity-equity spillover literature not ingested | gold/oil/copper/gas free (2000+); nickel proxy NICK.L (2008+); **coal & CPO — the IDX-relevant ones — have no free source** (KOL/FCPO=F empty) | sector books thinner; per-sector N ~4,000 book-days, σ ~1.5–2% → MDE ≥ 20bp/1σ; likely underpowered for sector-specific effects | SKETCH-ONLY, gold→miners / oil→energy subset; declare partial-coverage honestly |
| CAL1 | Turn-of-month execution timing | never run | Turn-of-month effect canonical in US (Ariel 1987; Lakonishok–Smidt 1988); EM/IDX standing unverified | corpus only (no new source) | outcome = open→close vs close→open by day-of-month bucket; N ≈ 1,166 valid-open days per bucket-class; detects ≥ ~15–20bp/day | SKETCH (cheap, 2 arms; execution-timing framing like X1's overlay) |
| CAL2 | Pre-holiday effect | never run | Ariel 1990, French 1980 (US); IDX not established | corpus + holiday calendar (timeanddate limited; IDX blocked) | ~250–300 pre-holiday days over 16y → MDE ≥ ~40–50bp — **underpowered alone at the bar** | SKIP as standalone; keep as a descriptive line only |
| IX1 | MSCI/FTSE index additions (new source) | never run (HYP-PA-0001 tested corpus-proxy reconstitution: FAILED; add-side forward-only per C4) | Index-addition drift documented (S&P/MSCI studies; Greenwood 2005 JFE) — not yet ingested | **FTSE Russell: USABLE no-auth** (JSON notices API, AnnouncedDate+EffectiveDate, ASEAN/GEISAC tags); MSCI: files exist per-URL but no crawlable EM listing without registration | few IDX events per review round; screen underpowered; recorder is the right shape | PROBE→**forward recorder** (no-slot) + screen only if ≥~40 PIT-annotated events |
| N1 | Google Trends / Wikipedia attention | never run; news_mentions only 2026-04+ | Da–Engelberg–Gao 2011 (SVI predicts short-horizon reversal/returns) — not ingested | **Wikipedia pageviews: USABLE no-auth** (daily from 2015-07; zero-days omitted — needs calendar join); Google Trends: **SKIP** (no API, 429s, ToS) | IDX-name coverage on Wikipedia thin for small caps → breadth collapses; likely underpowered | PROBE only; defer unless id.wikipedia coverage for ≥100 liquid names is demonstrated |
| LC2 | Lock-up expiry (mechanism of young-listing underperformance) | never run | Field–Hanka 2001 JF (blocked source; volume + abnormal returns at expiry) — not ingested | **BLOCKED** — no structured public source (idx.co.id Cloudflare; e-bursa dead/squatted; idnfinancials has no lock-up fields) | — | Data-gap item only; Owner vendor/IDX-direct decision would unlock it |
| C3 | 52-week high | never run | George–Hwang 2004 JF (nearness to 52w high cross-section) — not ingested | corpus ✓ | N ≈ 3,300 valid-open days 2021-07→2026-07; MDE ~15bp/1σ per decile-spread — feasible | **SKETCH NOW, RUN ONLY AFTER FADE-001 first maturity (~2026-10-19)** — D-062: 52w-high is {T1}-correlated; nothing correlated registers before the read |
| TS1 | Suspension/UMA resumption | never run ({TS} scoped in v1 as "no table"; the table exists) | resumption/halt price-discovery literature; no IDX-specific number in-corpus | **corpus ✓**: 359 real suspension events 2022-04-28→2026-07-17 (2,830 additional rows are `data_gap` artifacts, not suspensions); pre-2022 absent | 359 events, ~72/yr, date-clustered; event-study MDE ~0.5–1%/20d at the bar — marginal; pre-2022 events would double N but don't exist here | SKETCH (feasible now; expect "underpowered at the bar" to be the honest verdict) |
| BI1 | BI rate-decision days → banks | never run | policy-announcement drift unsettled in EM; needs a surprise proxy (no free IDR consensus) | BI-RDG decision dates public for recent years (BI-Rate table, no auth); **surprise measurement infeasible free** | calendar-only version N ≈ 60–70 decision days → MDE ≥ 50bp — underpowered; confounded by global moves | SKETCH (low priority); skip unless a PIT surprise proxy appears |

## Ranking for the R1 screen pick (my recommendation, 3–5 expected)

1. **X1** — full spec ready, priors verified, data acquired; the only idea with a complete
   predeclaration draft.
2. **TS1** — data in hand, event-study sketch cheap; expected underpowered but the null is
   informative (first read of the suspension archive).
3. **CAL1** — near-zero marginal cost (same panel as X1), documented US prior; the execution-
   timing framing matches the program's capturability discipline.
4. **C3** — sketch now, gated behind the 2026-10-19 FADE read; strongest published prior of the
   set that the corpus can actually test.
5. (optional) **IX1-recorder** — not a screen: a no-slot forward recorder on FTSE notices; costs
   nothing and starts the clock.

Underpowered / blocked: CAL2, BI1, N1 (as screens), LC2, X2-coal/CPO — report and hold.
