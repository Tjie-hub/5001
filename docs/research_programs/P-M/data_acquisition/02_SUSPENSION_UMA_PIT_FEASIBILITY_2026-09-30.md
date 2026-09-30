# 02 · Suspension/UMA announcements with PIT dates ({TS}) — FEASIBILITY MEMO · 2026-09-30

**Item (D-c #2):** point-in-time suspension/UMA disclosure dates. Current state
(`FAMILY_MAP_v2.md` §C): `suspension_events` has 3,189 rows but only 359 classified `suspension`,
detector-derived, **2022+ only** (3/3/14/30/309 across 2022–2026); the special-monitoring /
full-call-auction board has **no table at all**. No pre-2021 discovery half is possible today.
Scoping only.

## Verdict

**Two very different jobs hiding in one item.** (a) A *forward* recorder for suspension/UMA
announcements is cheap, public, no-auth — quick win with permanent time value. (b) A *historical
backfill* to enable a pre-2021 discovery half is uncertain and likely manual; do not promise it.

## Sources, ranked

1. **IDX announcements page (public, no auth)** — suspension ("penangguhan") and UMA
   ("Unusual Market Activity" / pemantauan khusus) notices are published as dated announcements on
   `idx.co.id`. Forward-recording from today needs no credentials and no scraping behind auth.
   Depth of the public *archive* (does it reach 2015–2020?) is the one open question — verify
   before promising any backfill.
2. **Detector table as validation set** — the 359 detector-derived `suspension` rows (2022+) are
   exactly what a recorder's output should be reconciled against; free QA, no acquisition needed.
3. **Stockbit news/events feed** — accessible in principle (credentials provisioned), but
   behind-auth pull = Owner decision; offers no pre-2021 history either.
4. **KSEI/OJK** — no known historical suspension table published in scriptable form.

## Literature prior (Owner's NotebookLM corpus, "Wisdom of the Crowd", 35 sources)

Queried 2026-09-30: an IDX event study (ETD UGM thesis on UMA announcements + broker/domicile
code closures) found **no statistically significant CAAR/TVA differences** around UMA events, and
the corpus is **explicitly silent** on directional post-UMA/post-suspension return predictability
(direction, horizon, effect size). The literature prior for a tradable `{TS}` edge is therefore
weak-to-null — this item's main value is *risk-side* (avoidance/anti-edge framing like {R1}, or
holding-window censoring), not a new long edge. Say this on any future card.

## Effort estimate

- Forward recorder (announcements → PIT table, daily): **0.5–1 day**; starts accruing immediately.
  Note: new recorder ≠ frozen-protocol edit, but the D-b standing-guard discussion shows recorder
  changes get Owner sign-off — flag it in the brief rather than wiring silently.
- Archive-depth verification: 0.5 day.
- Historical backfill (if archive proves deep enough + Owner approves scrape): 1–3 days;
  otherwise manual curation of liquid-name events only.
