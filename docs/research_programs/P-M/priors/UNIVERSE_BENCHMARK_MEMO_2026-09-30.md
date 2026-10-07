# UNIVERSE + BENCHMARK MEMO — one declared research universe · 2026-09-30

**Revision (2026-09-30, research consolidation):** the panel below replaces the one further
down this file — same universe rule, same window, rebuilt with (a) true cap weights from
`factor_zoo/data/fund_shares.pkl` instead of the stale Yahoo-fundamentals proxy, and (b) prices
loaded through the sanctioned split-adjusted path (`data.loaders._load_ohlcv_bulk(adjusted=True)`,
audit R-1) rather than whatever produced the impossible NAIK/TRUE numbers below. **NOT**
issuance-corrected per D-064 — see the "why the numbers changed" table for why. See
`build_c4_panel.py` / `build_c4_contributions.py` (this directory) for the rebuild scripts.

**Question (C3):** two incompatible universes were in circulation — broad ADV≥Rp1bn EW at
+30.5%/yr (POWER_MEMO v1, since shown look-ahead-inflated) vs VOLEX top-200 EW ≈ IHSG −6.7pp
(XP-001). Pick ONE tradeable universe, define its base, and answer: is the EW-vs-IHSG gap a few
mega-caps or broad?

## Pick: (a) VOLEX-001 top-200 by ADV60

| criterion | (a) top-200 by ADV60 | (b) IDX80 PIT |
|---|---|---|
| history | **59 months** (full corpus) | **19 months** (2025-01+; no pre-2025 membership exists) |
| capacity | 200 most-traded names; ADV60 ≥ Rp 1bn floor | 80 names, similar liquidity profile |
| spread | liquid names, tick-size friction lowest in market | same class |
| survivorship | inherits corpus caveat (unmeasured) | inherits + index reconstitution PIT only from 2025 |
| rule status | already the XP-001/VOLEX-001 universe — zero new convention | would fork the XP-001 record |

**(a) wins on history alone** — an era test is impossible in 19 months (the IDX80 addendum
already demonstrated this). Rule, stated exactly: *each month-end t, among names with a real
print (volume>0 at t), ADV60 ≥ Rp 1bn, close ≥ Rp 50 — take the top 200 by ADV60; monthly
rebalance; C1 tradeability (entry real print; carry frozen positions to next real print; −95%
mechanical-drop screen).*

## Base: true cap-weighted over the universe (2026-09-30 rebuild)

Caps = close(t) × PIT shares outstanding from `factor_zoo/data/fund_shares.pkl` (verified:
778/780 covered tickers show genuinely varying share counts over 2020-06..2026-09 — real
point-in-time data, not a repeat of the old Yahoo-fundamentals staleness). Coverage: 545 of the
top-200 names had a share count at the panel's first formation month (2021-08), rising to 780
tickers covered repo-wide by the last (2026-07) as the source series fills in.
Weights are formed **at month-end t using data through t only**; the return attributed to that
formation is the **forward** month t→t+1 — measuring the same month a universe was selected with
is a look-ahead/return-chasing bug (an earlier draft of this rebuild had exactly that bug; caught
because EW/CW came out strongly *positive* against a strongly negative, IHSG-corroborated
baseline — see `build_c4_panel.py`'s docstring/comments for the full account).

**Not issuance-corrected per D-064.** That mechanism is fully coded
(`data/adjustments.py: load_issuance_events`/`correct_issuance`) but its data table
(`corporate_action_events`) is empty on **the Windows machine's DB copy** (data ends 2026-07-29,
pre-D-064) — verified directly, read-only, 2026-09-30, against that copy specifically. This is
**not** a claim about the Dell/real production system, which the Owner is checking separately.
A live repopulation attempt against the Windows copy failed: its cached Stockbit token is expired
(401) and that machine's `auto_token.log` shows auto-refresh failing since at least 2026-09-22
(`REFRESH_FAILED ... action=manual_intervention_required`) — a pre-existing infra issue on that
copy specifically, not something fixed here, and not necessarily true of the Dell. Regular stock
**splits are still applied** (the sanctioned `data.loaders._load_ohlcv_bulk(adjusted=True)` path,
audit R-1, unaffected by the gap — see "why the numbers changed" below for exactly which code
this is and where it landed). Per Owner direction this rebuild falls back to the **standing
interim rule already adopted in
D-065_PROPOSAL_v2 §2**: rows below −95% in a single month are excluded from EW/CW means and
reported separately. In this rebuild **zero rows** triggered that screen (see "why the numbers
changed" below for why) — the screen stays in the code as a safety net, not because it fired.

## Yearly returns (2026-09-30 rebuild, true CW, NOT issuance-corrected)

| year | EW | CW | IHSG | months |
|---|---|---|---|---|
| 2021 (Sep–) | +1.86% | +3.78% | — | 4 (partial) |
| 2022 | −20.92% | −3.48% | +4.09% | 12 |
| 2023 | −14.32% | +9.49% | +6.16% | 12 |
| 2024 | −4.33% | +0.67% | −2.65% | 12 |
| 2025 | +46.12% | +11.33% | +22.13% | 12 |
| 2026 (–Jul) | −31.15% | −38.87% | −29.45% | 7 |
| **FULL (60 mo, ann.)** | **−7.85%/yr** | **−5.65%/yr** | **+0.10%/yr** | 60 |

IHSG figures recomputed on the same month-end calendar as a cross-check: they land within ~1-2pp
of the prior panel's IHSG column every year (e.g. 2021 +8.43% here matches the old table's
+8.43% exactly; 2025 +22.13% vs old +21.63%), which is the validation signal that the rebuild's
date/return machinery is sound — the divergence is specifically in the EW/CW columns.

### Why the numbers changed

| what changed | old value/behavior | new value/behavior | why it matters |
|---|---|---|---|
| Cap weights | Yahoo fundamentals, top-10 = 74-86% of universe (flagged implausible) | `fund_shares.pkl`, PIT-verified | CW no longer ≈ EW (see below) — the old "weighting isn't the story" conclusion doesn't hold under true weights |
| CW vs EW | CW ≈ EW every year (gap 0.0-0.1pp) | CW and EW diverge materially (e.g. 2023: EW −14.3% vs CW +9.5%, a 23.8pp gap) | true cap weight concentrates in resilient large caps (BBCA, BBRI, TPIA) that the old stale-share proxy didn't properly isolate |
| Full-period FULL row | EW −11.25%/yr, CW −10.21%/yr | EW −7.85%/yr, CW −5.65%/yr | still negative vs IHSG, but materially less negative once true CW and correct split-adjustment are both applied |
| Formation-vs-return timing | not stated explicitly | explicit: universe formed at t (data through t), return measured t→t+1 | the naive same-month version of this rebuild produced EW/CW of **+17%/+20%/yr** — a look-ahead bug now documented as a worked example in `build_c4_panel.py` |
| "Impossible" contributor numbers (NAIK −13,200%, TRUE −163pp) | present, flagged as mechanical-drop artifacts, "not evidence" | **gone** — same tickers now show NAIK −63%, TRUE −95% cumulative over the full window, plausible | **not a new fix.** The sanctioned split-adjusted read (`data/loaders.py: _load_ohlcv_bulk`/`load_ohlcv_df`, via `data/adjustments.py: adjust_ohlcv`) already existed and was already correct — introduced `507a428` ("corporate-action split adjustment in research loading path, audit R-1, P0"), refined `f82da6a` ("gap-verified split adjustment") and `f46f33d` (moved the raw read into the adjustment authority), all predating this session. This rebuild's script simply calls that path (`_load_ohlcv_bulk(adjusted=True)`). Per POWER_MEMO's own Method note, the OLD panel's numbers came from an unsaved one-off heredoc — it was never committed, so there is no buggy commit to point to; the most defensible reading is that script didn't go through the sanctioned path, not that the sanctioned path itself was wrong. No production-code fix is being claimed or needed here. |
| −95% single-month screen | fired routinely (basis for "contaminated, not evidence" caveat) | fired **zero** times in this rebuild | consistent with the split-adjustment finding above: most of what the screen used to catch is now handled upstream by correct adjustment |

## Top contributors (2026-09-30 rebuild — real, not "indicative")

Contribution = full-universe true-CW weight (all tickers with `fund_shares.pkl` coverage, not
only the top-200 — IHSG's own constituents include large caps that miss the ADV60 liquidity cut)
× forward monthly return, summed per year. This is a **proxy for IHSG's own official
free-float weights**, which this repo does not hold — read as "heaviest movers in our best
cap-weight reconstruction," not an audited index-attribution number.

| year | top positive (pp) | top negative (pp) | negative names inside top-200 (majority of the year)? |
|---|---|---|---|
| 2021 (partial) | BBRI +1.82, TLKM +1.35, ASII +0.77, BMRI +0.56 | BUKA −0.85, EMTK −0.62, BRIS −0.58, ARTO −0.54 | yes, all four |
| 2022 | BBCA +2.19, BBRI +1.76, BMRI +0.92, AMRT +0.77 | **GOTO −2.53, ARTO −2.19**, BBHI −0.93, EMTK −0.88 | yes, all four |
| 2023 | BREN +3.87, AMMN +2.88, TPIA +2.20, BBRI +1.24 | ADRO −0.52, UNVR −0.51, BYAN −0.40, MDKA −0.38 | **BREN and AMMN: no** (2/12 and 5/12 months in top-200 — too newly liquid to clear the ADV60 floor most of the year despite already being cap-weight-heavy); TPIA/BBRI: yes |
| 2024 | BREN +2.59, TPIA +1.89, PANI +1.59, AMMN +1.36 | **BBRI −2.16**, TLKM −1.10, UNVR −0.57, BRPT −0.34 | yes, all four |
| 2025 | DCII +4.01, MORA +1.95, BRPT +1.94, IMPC +1.46 | BBCA −1.65, BYAN −1.16, AMMN −1.13, BMRI −0.54 | DCII/MORA/BYAN: no (not top-200 liquid); BBCA/AMMN/BMRI: yes |
| 2026 (–Jul) | SMMA +0.31, CASA +0.17, ADRO +0.14, BDMN +0.13 | **BREN −6.48, TPIA −3.17**, BBCA −1.46, CUAN −1.38 | yes, all four |

GOTO/ARTO (2022) and BBRI (2024) reproduce the prior POWER_BENCHMARK_MEMO's findings closely
(that memo: GOTO −4.21pp, ARTO −1.60pp, BBRI −2.79pp — different magnitude under the old "LW"
weight proxy, same names, same sign, same years). BREN/TPIA emerge as new dominant movers in
2023-2026 under true CW that the old proxy underweighted.

## Answer (C4, two layers): broad underperformance, heavyweight-set magnitude

**Layer 1 — the median stock, within the top-200 universe each year:**

| year | median stock return | vs IHSG |
|---|---|---|
| 2022 | −8.24% | vs +4.09% |
| 2023 | −7.32% | vs +6.16% |
| 2024 | −5.27% | vs −2.65% |
| 2025 | +16.12% | vs +22.13% |
| 2026 (–Jul) | −24.44% | vs −29.45% |

The **typical member of the universe underperforms IHSG in 4 of 5 full years** (2022-2024, and
loses less badly than IHSG in the 2026 crash). This is broad, not an artifact of a few names —
it is the median, half the universe did worse.

**Layer 2 — the 2-4 heavyweights that set each year's *exact* CW-vs-IHSG gap size:** the table
above. Every year has a small, named set of movers that account for most of the CW aggregate's
swing (GOTO+ARTO ≈ 4.7pp of 2022's gap; BREN+TPIA ≈ 9.6pp of 2026's; BBRI alone ≈ 2.2pp of 2024's).

**Reconciling the prior memos' conflicting BROAD-vs-CONCENTRATED claims — both were partly right,
about different things:**
1. **Broad is true of the typical member** (layer 1): most stocks in the universe genuinely lag
   IHSG most years, so "the universe underperforms" is not a mega-cap illusion.
2. **Concentrated is true of the aggregate's exact magnitude** (layer 2, matching
   POWER_BENCHMARK_MEMO's original 2a finding): the CW number moving −5 vs −17pp in a given year
   is substantially set by 2-4 named stocks, not a smooth distribution.
3. Those heavyweights are **mostly inside the top-200 ADV60 universe** — the exceptions (BREN,
   AMMN in 2023; DCII, MORA, BYAN in 2025) are cap-weight-heavy names that hadn't yet cleared the
   liquidity bar, not evidence of "a different market" from the declared universe.
4. **CW is the correct base, not EW** — CW is less negative than EW every year (true cap weight
   concentrates in the more resilient large caps), so an EW-only read overstates how bad the
   typical *capital allocation* into this universe actually was, even though it correctly shows
   how bad the typical *name* was. D-065 §3's "CW of the declared universe" pick stands, now on
   real weights.
5. IHSG remains a **weak base for this universe** (full period CW −5.65%/yr vs IHSG +0.10%/yr,
   −5.75pp/yr gap) but the mechanism is now precisely attributable, year by year, rather than
   asserted as either purely broad or purely mega-cap.

---

## [Pre-consolidation panel, 2026-09-30 — superseded by the rebuild above]

The panel below is retained for provenance only; do not cite it going forward.

Caps = close(t) × last-known shares outstanding (Yahoo fundamentals fetch, 99.9% name-month
coverage; annual-stale between updates). **Caveat:** top-10 cap weight computes to 74–86% of the
universe — implausibly high (stale/adjusted-share mismatch vs split-adjusted closes); treat CW
weights as approximate.

| year | EW | CW | IHSG |
|---|---|---|---|
| 2021 (Jul–) | −3.78% | −4.64% | +8.43% |
| 2022 | −17.78% | −16.11% | +3.31% |
| 2023 | −12.12% | −13.91% | +6.34% |
| 2024 | −3.94% | +1.05% | −1.78% |
| 2025 | +28.45% | +25.78% | +21.63% |
| 2026 (–Sep) | −65.12% | −62.60% | −26.76% |
| **FULL (57 mo)** | **−11.25%/yr** | **−10.21%/yr** | **+1.42%/yr** |

Name-level contributions in this panel were contaminated by unadjusted corporate-action drops:
single-name cumulative returns like NAIK −13,200% or TRUE −163pp were impossible as price paths.
The 2026-09-30 rebuild above traces this to a split-adjustment defect in whatever produced this
panel, not primarily to the (still-unavailable) D-064 rights/bonus correction.
