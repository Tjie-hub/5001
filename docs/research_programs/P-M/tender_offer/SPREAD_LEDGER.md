# SPREAD LEDGER — tender-offer floor (HYP-PM-0018 draft, D-074 stop rule) · 2026-10-09

**The stop rule fired (12 eligible events < 20): there is NO G1.** This ledger is the
deliverable D-074 prescribes for the stopped branch: **pre-entry facts only** — no return, no
price after any entry close, no book value is computed, printed or stored anywhere in this
file. All facts are known at the entry close (the session before `tender_start`); adj offer =
`tender_price / f_cum(entry)` (basis rule frozen in `PREDECLARATION.md` §2). Cost = the D-059
modelled round trip at the name's ADV20 (`cost_liquidity/cost_by_adv.py` @ 7e039ee).

## The frozen population (12 eligible events)

| # | ticker | start | end | entry close | adj offer | spread | true-ADV20 | cost | window (sessions) |
|---|--------|-------|-----|------------:|----------:|-------:|-----------:|-----:|------:|
| 1 | OASA | 2022-02-08 | 2022-03-09 | 141.55 | 224.0 | 58.24% | Rp 1.97bn | 4.84% | 20 |
| 2 | TBIG | 2022-06-22 | 2022-07-22 | 2,940 | 3,200 | 8.84% | Rp 68.3bn | 1.94% | 23 |
| 3 | TOWR | 2022-08-04 | 2022-09-02 | 1,210 | 1,300 | 7.44% | Rp 103bn | 1.06% | 21 |
| 4 | SMMT | 2023-11-23 | 2023-12-22 | 1,260 | 1,306 | 3.65% | Rp 2.97bn | 1.31% | 22 |
| 5 | TBIG | 2023-12-14 | 2024-01-12 | 2,100 | 2,300 | 9.52% | Rp 9.42bn | 1.77% | 19 |
| 6 | SILO | 2024-08-05 | 2024-09-03 | 2,730 | 2,850 | 4.40% | Rp 4.41bn | 1.77% | 22 |
| 7 | ANJT | 2025-08-26 | 2025-09-24 | 1,780 | 1,813 | 1.85% | Rp 1.81bn | 1.23% | 21 |
| 8 | MMLP | 2025-11-25 | 2025-12-24 | 565 | 580 | 2.65% | Rp 2.80bn | 1.68% | 22 |
| 9 | SGRO | 2026-01-21 | 2026-02-19 | 7,700 | 7,903 | 2.64% | Rp 8.26bn | 1.83% | 20 |
| 10 | IATA | 2026-04-22 | 2026-06-03 | 91 | 99 | 8.79% | Rp 14.0bn | 4.30% | 25 |
| 11 | MAPI | 2026-06-18 | 2026-07-17 | 1,500 | 1,550 | 3.33% | Rp 96.4bn | 1.29% | 22 |
| 12 | MTEL | 2026-07-03 | 2026-07-10 | 494 | 515 | 4.25% | Rp 18.6bn | 3.61% | 6 |

Median spread 4.32% (mean 9.63%, range 1.85–58.24%); median window 21.5 sessions (6–25);
median cost 1.80%; all events have `tender_percentage` < 99 (max observed anywhere in the data
is 90.0 → ALL are partial offers under the frozen ≥ 99 cut). Every entry is 2022 → 2026 — the
5001 price panel (2021-07-05+) structurally excludes the 2015–2021 offers (34 windows entirely
pre-coverage + 1 malformed KEJU), counted at waterfall stage S1.

## Near-misses at the cost floor (S8: spread > 0 and liquid, but < 0.60% + D-059 cost)

| ticker | start | spread | true-ADV20 | cost | floor needed | miss |
|--------|-------|-------:|-----------:|-----:|-------------:|-----:|
| COCO | 2022-01-26 | 1.59% | Rp 3.44bn | 3.23% | 3.83% | 2.2pp |
| KETR | 2026-07-09 | 3.56% | Rp 18.6bn | 3.70% | 4.30% | 0.7pp |
| LINK | 2022-08-30 | 1.05% | Rp 10.6bn | 1.01% | 1.61% | 0.6pp |
| LUCY | 2022-06-21 | 2.58% | Rp 1.48bn | 3.94% | 4.54% | 2.0pp |
| PALM | 2022-09-01 | 3.03% | Rp 2.42bn | 3.88% | 4.48% | 1.5pp |
| PTRO | 2022-08-25 | 1.90% | Rp 20.9bn | 1.32% | 1.92% | 0.02pp |
| RANC | 2021-11-16 | 1.59% | Rp 2.61bn | 2.55% | 3.15% | 1.6pp |
| RSGK | 2021-12-21 | 1.47% | Rp 5.33bn | 1.67% | 2.27% | 0.8pp |
| TRJA | 2024-01-12 | 1.08% | Rp 1.10bn | 2.77% | 3.37% | 2.3pp |

PTRO-2022 is the basis rule made visible: raw offer 3,118 on an entry close of 306 (stored
basis) with a 1:10 split after the window — rescaled to 311.8 it is a sane 1.90% spread that
misses the floor by 0.02pp. Without the rescale it would have been misread as a 10× "spread".

## Why there is no G1 (power view, pre-event facts only)

MDE at n = 12 = bar 3.2978 × median window-scaled pre-entry σ 9.14% / √12 = **8.70%**, while
the median spread itself is **4.32%** — even a book where every event converged fully to the
offer could not clear the bar at this n. The stop is power-correct, not merely count-correct.

## What is NOT here (by rule)

No outcome of any event — no close at or after any `tender_start`, no convergence ratio, no
acceptance bound, no book. The forward recorder (HANDOFF_G0 §recorder; owner-gated) is where
future convergence facts will live, DOOH first (offer 148, window 2026-10-05 → 11-03, excluded
here as unsettled).

*— ZCode, 2026-10-09; facts from `CENSUS_G0.json` (snapshot a2d7e675…, fingerprint 9c26e0df…)*
