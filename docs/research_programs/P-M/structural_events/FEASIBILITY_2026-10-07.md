# FEASIBILITY — structural events: counts, point-in-time dates and power only (2026-10-07)

**Authority:** `ZCODE_BRIEF_STRUCTURAL_EVENTS_FEASIBILITY_2026-10-07.md` (eba109b) as overridden by
`ZCODE_NEXT_TASKS_2026-10-07.md` (7ccb15d, Task 2). Serves **D-070** §Decision 4 (the feasibility
gate before any registration). **Branch:** `research/structural-events-feasibility-2026-10`
(from the post-Task-0 hardening tip `a28ec7e`). Numbers from `CENSUS_FEASIBILITY.json`, produced
by `structural_events_census.py` (read-only DB, fixed rules, no sampling).

## Rule 1 — honored: no post-event price was read

Every price query in the census filters `date < decision_date` (strictly before). No return,
price change or excess return after any event's decision date was computed, printed or stored,
for any event, horizon or aggregate. Power is estimated from **pre-event** volatility only: the
daily-return standard deviation over the 60 sessions **ending the day before** the decision date.
Complete-bars fractions count pre-event availability only. `HANDOFF.md` states this explicitly.

## Decision-date conventions (declared; the scheduled public date each class offers)

No class stores a market-announcement date. Per the brief's rule, each class is anchored on a
later date that is itself public in advance:

| class | decision date used | coverage | note |
|---|---|---|---|
| A tender offers | `tender_start` (offer window opens) | 165/165 = 100% | the offer terms are public from the start date |
| B IDX80 reconstitution | `effective_from` | 7/7 periods | announcements are ~1 week ahead; the period notes cite the BEI announcement documents (e.g. Peng-00012/BEI.POP/01-2025, announced 22 Jan 2025 for effective 2025-02-03) — PIT quality medium (approximation) |
| C rights issues | `rightissue_cumdate` | 321/321 = 100% | scheduled cum date, public in advance |
| D dividends | `dividend_cumdate` | 4,763/4,763 = 100% | scheduled cum date, public in advance |
| E splits/bonus/reverse | `stocksplit_cumdate` | 194+82+19 = 100% | scheduled cum date, public in advance |
| F warrants | `wrant_trading_from` | 148/148 = 100% | scheduled trading window start |

RUPS (6,727) excluded — no named forced-flow mechanism. Ownership composition: 2 snapshots —
infeasible historically, **forward-collection candidate only**.

## Prior coverage (searched: HYPOTHESIS_REGISTRY, FAILURE_REGISTRY, DECISION_LOG, docs/research_programs/)

- **C rights issues — ALREADY TESTED.** `SCREEN-PM-CF-001` (S1, D-064 context): the RI and RUPS
  issuance-avoidance grid — every pre-declared cell null (|t| ≤ 1.07; RI·h252·post2021 primary
  −0.635%/mo, t −0.56). **Not counted as new.** D-064's issuance *adjustment* (holder-wealth φ)
  additionally covers rights/bonus/reverse ex-dates as data hygiene.
- **D dividends — partially touched.** D-064's ex-date *monitor* (`check_issuance_windows.py`,
  detection-only; OBS-2026-09-29 BUVA/ENRG) and the same adjustment machinery. **No edge study
  exists.**
- **E splits/bonus/reverse — touched as adjustment only** (D-064 split factors / issuance
  corrections). No edge study.
- **A tender offers — no prior coverage anywhere** (first mention is D-070 itself).
- **B index reconstitution — the IDX80 dataset OBJECT was approved (D-033, broker-flow admission
  path), but the reconstitution passive-flow mechanism is untested.** (The FAILURE_REGISTRY hit
  is the broker-flow data-gap failure, not this mechanism.)
- **F warrants — no prior coverage anywhere.**

## Counts (decision-date year; liquid = ADV20 ≥ Rp 10 bn the day before the decision date)

| class | total | parsed | liquid 2009→ | era split (E1/E2) | multi-event tickers | 60-pre-bars |
|---|---:|---:|---:|---|---:|---:|
| A tender offers | 165 | 165 | **23** | 1 / 22 | 19 (max 5) | 76.4% |
| B IDX80 reconstitution | 7 events (26 adds + 26 removes) | — | 26 added/26 removed | all E2 (2025-02..2026-08) | — | n/a |
| C rights issues | 321 | 321 | **61** | 4 / 57 | 68 (max 8) | 45.2% |
| D dividends | 4,763 | 4,763 | **574** | 14 / 560 | 530 (max 24) | 43.3% |
| E splits | 194 | 194 | **20** | 0 / 20 | 18 (max 2) | 28.9% |
| E bonus | 82 | 82 | **7** | 0 / 7 | 18 (max 4) | 47.6% |
| E reverse splits | 19 | 19 | **0** | 0 / 0 | 1 (max 2) | 10.5% |
| F warrants | 148 | 148 | **4** | 0 / 4 | 3 (max 2) | 12.8% |

Honesty note: the thin E1 (2009..2021-09) liquid counts are partly the **60-pre-bars/data
coverage** constraint (43-76% of events have a full pre-event window; reverse splits 10.5%) and
partly the ADV20 floor. The liquid universe is E2-dominated in every class — the era-flip risk
D-070 documents applies here too.

## Power (pre-event 60-session daily vol only; MDE = t_bar·σ_d·√h/√n; median σ_d per class)

| class | median σ_d (daily) | n liquid | MDE 10 sessions independent | month-clustered |
|---|---:|---:|---:|---:|
| A tender offers | 3.83% | 23 | **7.7%** | 4.2% |
| B IDX80 reconstitution | (per-event vol not the binding constraint) | 26 flows | — | — |
| C rights issues | 3.52% | 61 | 4.4% | 3.2% |
| D dividends | 2.36% | 574 | **0.95%** | **1.63%** |
| E splits | 2.95% | 20 | 6.4% | 2.7% |
| E bonus | 3.67% | 7 | 13.4% | 4.6% |
| E reverse | 3.06% | 0 | — | 6.8% |
| F warrants | 3.92% | 4 | 18.9% | 4.8% |

One line per class, at 10 sessions: **A**: detectable ≥ 7.7% (4.2% month-clustered) — weak.
**B**: 26 flows across 7 events — power is count-limited, not vol-limited. **C**: 4.4% (3.2%) —
marginal, and already null-tested. **D**: detectable ≥ 0.95% (1.63% clustered) — the only class
with workable power. **E splits**: 6.4% (2.7%); **E bonus**: 13.4%; **E reverse**: no liquid
events — all weak. **F**: 18.9% — infeasible. (5- and 20-session figures in
`CENSUS_FEASIBILITY.json`: independent MDE scales as √h, clustered as √h over month-clusters.)

## Data gaps and fillability (no fetching done now)

1. **LQ45 / IDX30 / IDX80 history before 2025** — the same Wayback route that produced
   `idx80_*` (BEI Pengumuman XLSX via web.archive.org; the notes document the working recipe and
   its Cloudflare caveat). Effort: one acquisition script per index, roughly 1–2 days each,
   bounded by archive availability. This is the single highest-leverage gap: it would multiply
   class B's ~26 flows several-fold and add pre-2025 PIT-anchored events.
2. **Tender-offer table starts 2015** (165 events, 2015–2026): earlier tenders would need a
   second source (IDX/OJK announcements); effort: unbounded — treat as out of reach for now.
3. **60-pre-bars gaps** (43–76% per class): delisted-then-covered tickers and pre-2021 price
   history; partially fillable from the same corpus (no new source identified).
4. **Ownership composition**: 2 snapshots — forward-collection candidate only (per the brief).
5. **Announcement dates** are not stored for any class (only scheduled dates): fillable for B
   (the notes already cite announcement documents) and partially for A/C/D/E by re-scraping
   announcement timestamps — effort: 1–2 days per class, medium value (tightens PIT).

## Recommendation (ranked, with reasons)

1. **A — tender offers (take to G0, pooled cross-sectional design).** The strongest forced-flow
   mechanism in the set: a mandatory/voluntary offer price is a hard floor with a contractual
   convergence deadline (tender_end), so the spread is arbitrage-bounded rather than predictive —
   exactly the mechanism class D-070 wants. 100% PIT-date coverage on a stored public date. The
   weakness is power (23 liquid events, MDE10 ≈ 4.2–7.7%): only a pooled design with the
   arbitrage-spread effect size named up front is worth registering; single-pattern event
   studies are dead on arrival (D-070's own low-power finding).
2. **D — dividend ex-dates (take to G0, pooled, strictly predeclared).** The only class with
   workable power (574 liquid events; MDE10 ≈ 0.95–1.63%): pre-ex demand / post-ex supply with
   tax-clientele segmentation. Prior coverage is partial (D-064's monitor is detection-only; no
   edge study), so it counts as new — but the pooled design must predeclare the clustering
   (530 multi-event tickers; events cluster by month and by earnings season) and the era risk
   (560 of 574 liquid events are E2).
3. **B — index reconstitution (conditional).** Clean mechanism (mechanical passive buys/sells at
   a known effective date) but only 7 events / ~52 flows since 2025 — infeasible alone. Take it
   to G0 **only after** the LQ45/IDX30 history is sourced (gap 1), pooled across indices and
   years.
4. **C — rights issues: skip** (S1 already tested the class null; a new design would need a
   materially different mechanism statement to justify a fresh registration).
5. **E — splits/bonus/reverse: skip** (mechanism weak and contested; power poor — 0–20 liquid
   events; D-064 adjustment machinery already handles the data-hygiene need).
6. **F — warrants: skip** (4 liquid events, 12.8% pre-bar coverage, no PIT structure beyond
   trading windows; forward-collection candidate only).

**Named for predeclared G0: A (tender offers) and D (dividend ex-dates)** — A for mechanism
strength, D for power; both pooled cross-sectional per D-070 §Decision 5. B stays parked behind
the index-history acquisition.

*No post-event price was read in producing this document (see HANDOFF.md).*
