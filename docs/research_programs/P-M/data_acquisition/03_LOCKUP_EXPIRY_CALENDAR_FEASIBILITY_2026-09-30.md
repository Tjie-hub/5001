# 03 · Lock-up expiry calendar ({LC}) — FEASIBILITY MEMO · 2026-09-30

**Item (D-c #3):** the supply-shock event itself for the `{LC}` listing-lifecycle family.
`FAMILY_MAP_v2.md` §B: "No lock-up-expiry table (the supply-shock event itself is unobservable);
listing dates are a proxy." Scoping only.

## Verdict

**No structured public source exists — but the relevant N is small enough to curate by hand.**
This is the one D-c item that directly serves a *live* lead: SCREEN-PM-LC-001 (young-listing
avoidance) PASSED its pre-declared rule and D-064 kept the lead open at screen level pending an
exact deflation bar. Lock-up expiry is the mechanism test for that screen: if the avoidance effect
clusters around supply unlock dates, the lead graduates from cohort artifact to mechanism.

## Sources, ranked

1. **Manual curation from IPO prospectuses (e-prospectus PDFs, `idx.co.id`/e-bursa)** — each
   prospectus states the lock-up structure (who is locked, 90/180/365-day tranches) with exact
   dates. There is no published *calendar*, but the primary documents are public and dated.
   For the screenable cohort the N is tiny: **158 liquid listings (adv20 ≥ Rp 5bn at first_bar+90d)
   since 2015** (map §B counts). One working day of PDF reading produces an authoritative table.
2. **Convention-based proxy (IPO date + 180d)** — free and instant from the existing first-bar
   proxy, but it is a *proxy of a proxy*: it fabricates the event date, and IDX lock-ups are not
   uniformly 180d. Use only as a sanity envelope around (1), never as the event itself.
3. **Paid vendor (Refinitiv/Bloomberg IPO calendars)** — partial IDX coverage, no subscription
   provisioned in this environment; only worth it if the family opens for real.
4. **Stockbit/app event feeds** — no lock-up-expiry section observed; behind-auth anyway
   (Owner decision).

## PIT quality

Prospectus-sourced dates are **announcement-era PIT** (the lock-up schedule is known at IPO, so
the expiry date is knowable months ahead — this is one of the rare D-c items where the event is
*forecastable*, which changes what a test can claim: any effect is likely partly priced; the
screen should say whether it measures the pre-expiry drift or the post-expiry overhang release).

## Effort estimate

- Curated table for the 158 liquid listings: **~1 working day** (per-name prospectus lookup,
  ticker, IPO date, lock-up tranches, source URL).
- Optional pre-2021 extension to non-liquid listings: +1–2 days, low marginal value (outside the
  liquid cohort a screen would use).
- Convention proxy only: 0 (derivable from existing tables, but label it proxy-grade).
