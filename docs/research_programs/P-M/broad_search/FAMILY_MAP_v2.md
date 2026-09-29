# FAMILY_MAP_v2 — broad edge search, phase 0 (2026-09-29)

**Authority:** brief `ZCODE_BRIEF_BROAD_EDGE_SEARCH_2026-09-29.md` §5. Supersedes
`ZCODE_ALPHA_DISCOVERY_FAMILY_MAP_2026-09-10.md` (that map covered broker-flow families; this one
covers the six families the brief opens). **No outcome data was read in phase 0**: every
price-derived number below is a trailing observable (adv20 at an event date, a last close before an
announcement) or a jump-presence count. Evidence: `phase0_counts.py` → `phase0_counts.json`
(snapshot `walkforward-20260928-213012.db`, sha256 `10f9c97f…46c13`).

**Shared facts.** Announcement-stamp PIT audit: `rightissue_created`, `rups_created`,
`tender_created`, `dividend_created` present on 100% of rows; `stocksplit_created` (also carried by
bonus/stock_reverse rows) present but **batch-stamped in old cohorts** (38 rows stamped 2014-09-05,
74 warrants 2025-05-28 = fetch dates); `warrant` has no announcement field at all. The research
price corpus is split-adjusted at source but **not** adjusted for rights/bonus/reverse splits
(RIGHTS_ADJUSTMENT_AUDIT.md §2: 23 of 349 measurable issuance-type ex-dates carry >35% mechanical
jumps; most sub-band drops are still ≈ −30%).

Noise floor / MDE baseline (D-056, measured on this panel): decile-sort monthly σ ≈ 6.5%/mo,
quintile ≈ 4.6%/mo. Event sleeves are comparable or thinner ⇒ at N ≈ 145 months (2013→2024) the
two-sided MDE at the post-census bar (|Z| ≈ 2.86) is **≈ 1.6–2.0%/mo**; at N ≈ 60 (2021+ only)
**≈ 2.4–3.0%/mo**. US-calibrated anomaly effects after the R9 decay haircut (×0.5) are typically
0.2–0.5%/mo — i.e. **every family below is formally underpowered for its US-calibrated effect**.
They are screened anyway because IDX event magnitudes plausibly exceed US composite measures (deep
discounts, mandatory MTOs, the 2021 IPO cohort), because a pre-declared null is a first-class
outcome, and because the census prices every look. This power expectation is stated BEFORE any run;
no verdict may be read as "surprising" in either direction.

---

## A · Corporate-finance events `{CF}` — **SCREEN (S1)**

**Mechanism.** Managers issue equity when the price is high (market timing); the new supply and the
signalling content depress subsequent returns. Long-only form: **avoidance** (never short).
**Prior.** McLean–Pontiff–Watanabe 2009 (41 countries; net share issuance "greater statistical
significance than either size or momentum", driven by post-issuance *under*performance) [V,
RULE_FIRST §6-C2]; magnitude [M] ≈ −8%/yr top-minus-bottom decile ⇒ issuer-vs-rest ≈ −0.3%/mo,
haircut ≈ −0.15%/mo. IDX-specific: rights issues here are dilution *events* (median factor 1.43;
many at deep discounts to fund restructurings) — plausibly ≫ US composite issuance.
**PIT.** `rightissue_created` 100% present, 0.3% weekend stamps; created ≤ ex-date on 89.3%
(late stamps only *delay* a flag — no look-ahead). `rups_created` 100% present, 0% weekend,
no ex-date to violate. Batch-stamp contamination: **0.0%** of rights-issue stamps fall on
≥10-events-per-day dates (unlike splits/warrants) ⇒ rights stamps are per-event.
**Counts (2013→2026-09, announcement-year).** rightissue 315 total / **98 at adv20 ≥ Rp 5bn**
(per-year total[liquid]: 2015 17[3] · 2016 25[10] · 2017 22[7] · 2018 21[3] · 2019 17[2] ·
2020 20[3] · 2021 39[24] · 2022 44[17] · 2023 21[5] · 2024 15[2] · 2025 16[11] · 2026 25[11]);
rups 6,692 / 1,577 liquid — usable only as a *coarse* early-issuance proxy (116/315 = 37% of
rights issues were preceded by a rups within 12 months; **agenda fields are empty on all 6,708
rows**, so approvals cannot be distinguished from routine AGMs).
**Capturability.** Entry at next own-session open after the announcement stamp — fully capturable;
the ex-date sits ~2–3 months later and needs the wealth correction (audit §5).
**Independence from §2.** Event dates are exogenous corporate disclosures, not price-path states —
unlike T1/R1/V. Residual overlap: distressed issuers announce after big drops; measured at run time
as the share of flagged rows within 20 sessions of a 20-day-low breakdown (descriptive count).
**Label proposal:** `{CF}` (new family, owner-decided).
**Data gaps.** No private-placement (PMTHMETD) records; no shares-outstanding history (binary
event proxy, not MPW's continuous measure — say so on any future card); rups agenda empty.

## B · Listing lifecycle `{LC}` — **SCREEN (S2)**

**Mechanism.** IPO glamour pricing + lock-up supply overhang ⇒ young names underperform (Ritter
1991; Loughran–Ritter 1995 [M]). Long-only form: **avoidance of names < 12 months from listing**.
**Prior.** [M] ≈ −2…−4%/yr net-of-market over 3 years ⇒ haircut ≈ −0.1%/mo; IDX 2021-cohort folk
magnitude much larger (not verified). Tier-N by the R3 table unless a published EM replication is
cited at card time.
**PIT.** Listing proxied by first bar in `history_long.db::ohlcv_long`. Coverage artifacts: names
first appearing exactly at the DB corpus start (2021-07-05) or the backfill start are old names
being onboarded, not IPOs — excluded as defects and counted; first bars 2015–2020 (13/13/28/45/44/43
per year) match known IDX IPO activity, 2021 shows 229 (≈90 real IPOs + onboarding).
**Counts.** 621 listings 2015+; adv20 at first_bar+90d ≥ Rp 5bn: **158** (2015 2 · 2016 3 · 2017 3 ·
2018 7 · 2019 9 · 2020 7 · 2021 33 · 2022 26 · 2023 40 · 2024 16 · 2025 11 · 2026 1).
**Capturability.** Entry next own-session open after first bar + eligibility gate ⇒ capturable for
the liquid subset; young names outside it are a fingerprint, not the primary.
**Independence from §2.** **Declared overlap with {V} (VOLEX-001 in flight):** young names are
high-volatility names. Mitigation per brief rule 10: the run reports a trailing-vol-conditioned
descriptive split (does the young-listing effect survive *within* volatility bands?); the screen
verdict carries an explicit "not registrable while correlated with {V} without incremental
evidence" caveat.
**Survivorship direction (rule 8).** 54/929 names end before 2026 ⇒ delisted coverage ≈ 0; the
worst IPOs are missing. For an **avoid-side** arm this biases *against* the effect — conservative;
stated on the card.
**Label proposal:** `{LC}` (new family, owner-decided).
**Data gaps.** No lock-up-expiry table (the supply-shock event itself is unobservable); listing
dates are a proxy, verified only by cohort-shape plausibility.

## C · Trading-status events `{TS}` — **data-blocked, no screen**

`suspension_events`: 3,189 rows but the `classification` field is only {data_gap: 2,830,
suspension: 359}, and the 'suspension' class is **detector-derived and covers 2022+ only**
(2022: 3, 2023: 3, 2024: 14, 2025: 30, 2026: 309; missing_td p25–p90 = 5–6 sessions). There is no
trustworthy historical suspension/resumption table, so no pre-2021 discovery half exists.
The special-monitoring / full-call-auction board has **no table at all**. Proposal: data acquisition
(IDX suspension announcements) + optional forward recorder. **Label proposal:** `{TS}` reserved.

## D · Cross-asset lead `{X}` — **data-blocked (acquisition item), no screen**

No in-house series for TLK ADR, USD/IDR, or coal/CPO proxies (snapshot table census: no fx/macro/
adr tables; ohlcv/ohlcv_long are IDX equities + IHSG only). Even the anchor (overnight TLK) would
require a new external dataset with its own PIT/fetch discipline — an acquisition item, not a
screenable family today. **Label proposal:** `{X}` reserved.

## E · Industry cross-section `{S}` — **not screened (declared {T1}-correlated)**

`ticker_sector` is a single snapshot (780 tickers, 11 sectors + 11 unclassified; no membership
history). Within-industry lead-lag (Hou 2007 [M]) is trend-family-correlated by construction —
the brief requires a double sort against trend onset if screened at all. With {T1} dead at the
deflation bar (D-062) and REGIME-002 in flight, spending census arms here is negative-expected-
value. Parked; re-offer only after REGIME-002's first read. **Label proposal:** `{S}` reserved.

## F · Attention `{N}` — **forward-recorder proposal only, no screen**

`news_mentions`: 93,492 rows, 2026-04-26 → 2026-09-28, 972 tickers (~5 months). Underpowered by
construction. Proposal for the handoff: a daily attention-count recorder (per-ticker count vs its
own trailing median) accruing now so a screen becomes possible ~2027-04. **Label proposal:** `{N}`.

## Sub-families checked and closed at map level

| candidate | why closed |
|---|---|
| A2 tender-offer anchoring | median tender_price vs last close before announcement = **−1.3%** (premium ≈ 0 — Indonesian MTOs price at market, killing the anchor); only 28 events pre-2021 (no discovery half); 40 liquid events total |
| A3 split/reverse-split drift | `stocksplit_created` batch-stamped in old cohorts (38 rows stamped 2014-09-05) ⇒ announcement-date PIT broken for exactly the historical cohort a screen needs; splits are already adjusted at source (no mechanical signal); reverse splits N=19 |
| A4 dividend events | `dividend_created` is after the ex-date on **27.7%** of rows — the stamp is a record/update date, not the announcement; PIT broken |
| A5 EGM agenda | agenda fields empty on 6,708/6,708 rows; only the bare meeting date exists (folded into S1 as the rups proxy arm) |
| warrant issuance | no announcement field on 147/147 rows |

---

## Ranked shortlist

1. **S1 = `{CF}` issuance avoidance** — rightissue + rups event defs, holds {126, 252} own
   sessions. Best prior of the six (Tier-R-adjacent), best PIT, 98 liquid events, event-time
   engine ready, ex-date correction fully specified.
2. **S2 = `{LC}` young-listing avoidance** — first-bar def (2015+, artifacts excluded), holds
   {126, 252}. Second-best power (158 liquid), Tier-N prior, declared {V} overlap with a
   vol-conditioned descriptive split.
3. Everything else: data-blocked (C, X), PIT-broken (A3, A4, A5-agenda, warrants), prior-less
   (A2), correlated (E), or recorder-only (F).

**Data-gap list (acquisition items for the handoff):** private placements (PMTHMETD);
suspension/UMA announcements with PIT dates; lock-up expiry calendar; TLK ADR / USD-IDR / coal-CPO
series; news_mentions history extension; rups agenda content; shares-outstanding history.

**Arms budget.** S1: 2 defs × 2 holds × 2 splits = 8. S2: 1 def × 2 holds × 2 splits = 4, + 2
vol-conditioned descriptive cells = 6. **Total 14 ≤ 24.** Post-census bar: N = 252 + 14 = 266 ⇒
E[max|Z|] = 2.86 (exact value recomputed in the predeclarations).
