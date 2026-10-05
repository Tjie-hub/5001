# 01 · Private placements (PMTHMETD, {CF}) — FEASIBILITY MEMO · 2026-09-30

**Item (D-c #1):** private-placement records — the missing half of the `{CF}`
corporate-finance-events family. The corpus's `corporate_action_events` carries
rightissue/bonus/stock_reverse/stocksplit/dividend; PMTHMETD (IDX's negotiated-placement
corporate action) has **no records at all** (`FAMILY_MAP_v2.md` §A data gaps). Scoping only.

## Verdict

**No free bulk/scriptable source.** This is a point-in-time *disclosure* dataset that exists as
per-event announcement documents, not as a downloadable table. The honest paths are manual
curation (small N, genuinely tractable) or Owner-authorized access work. Do **not** build a
backfill pipeline against a source that hasn't been confirmed.

## Sources, ranked by confidence

1. **IDX's own disclosure system (`idx.co.id`)** — every PMTHMETD has an announcement document
   with a stamp date (good PIT), but retrieval is per-event PDF/document search; no bulk export,
   no API. Confidence the data *exists* there: high. Confidence it is *scriptable without auth*:
   low → **Owner decision needed before any scrape** (site terms).
2. **Manual curation via IDX disclosure search** — for the only cohort a screen would use anyway
   (adv20 ≥ Rp 5bn), event counts are small: the rights-issue census ran ~98 liquid events
   2013→2026; private placements on liquid names are plausibly a few hundred rows. A curated CSV
   for 2021+ (discovery era) is a **pilot-day** job, not a pipeline.
3. **Stockbit-adjacent access** — `.env` carries working Stockbit credentials (auto_token.py
   headless refresh), so authenticated *access* exists in this environment; but pulling
   corporate-action history behind auth is a **scrape-behind-auth decision reserved to the
   Owner** (same posture as the scoping brief's ground rules). Not attempted.
4. **Aggregators (emiten.com, IDN Financials, news archives)** — partial, unstructured, PIT
   quality unverified. Last resort only.
5. **Paid vendor** — would work but no subscription is provisioned; only worth it if the family
   survives screening.

## Context on urgency

`{CF}`'s *other* half just closed null at screen level: SCREEN-PM-CF-001 (rights-issue
issuance avoidance) FAILED (D-064, t −0.56 primary). Private placements are a different event
(deeper discount, negotiated, stronger dilution-signal prior in EM literature), so the null does
not close this item — but it does lower its expected value relative to the a-priori #1 slot the
handoff gave it.

## Effort estimate

- Manual pilot (2021+ liquid cohort): **4–8 h**, produces a curated CSV with announcement-date
  PIT, fit for a pre-declared screen.
- Full backfill 2013+ by hand: 2–4 days.
- Automated IDX scrape: 3–5 days build + ongoing maintenance, **blocked on Owner ToS ruling**.
