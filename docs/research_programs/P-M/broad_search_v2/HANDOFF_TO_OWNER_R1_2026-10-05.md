# HANDOFF TO OWNER — R1 review package · 2026-10-05 (ZCode, tjiejet)

**Everything below is DRAFT work for your review. No registry, ledger, DECISION_LOG, census or
frozen protocol was touched. Nothing was committed — see blocker 1.**

## What is ready for your R1 review

| piece | location |
|---|---|
| **W0 census recount** (245 countable trials from the 2026-09-24/25 pattern studies; bar 3.2501 at N=515; survivor re-reads: **FADE-vs-IHSG 3.13 no longer clears**, FADE-vs-EW 4.4 / T1-D 3.84 / S2 3.66 survive) | `P-M/broad_search_v2/recount/RECOUNT_W0_2026-10-05.md` + `SOURCE_SHA256SUMS_in_place.txt` |
| **W1 inventory** (your 10 seeded ideas: status, priors, data, power, recommendation, ranked) | `P-M/broad_search_v2/W1_INVENTORY_2026-10-05.md` |
| **W2 source probes** (all seven) | `P-M/broad_search_v2/W2_SOURCE_PROBES_2026-10-05.md` |
| **W3 screen sketches** (X1, TS1, CAL1, C3 + IX1 recorder; explicit skip list) | `P-M/broad_search_v2/W3_SCREEN_SKETCHES_2026-10-05.md` |
| **X1 Phase 0 complete**: 7 series + JISDOR acquired & manifested; timing contract; counts/σ/MDE; TLK ADS gate PASS; **all 3 priors verified** (2 as claimed; Gagnon–Karolyi partially — average deviation "economically small 4.9bp", fast mean reversion verified, tails extreme; brief's title corrected) | `P-M/cross_asset/` (MANIFEST.json, TIMING.md, PHASE0_COUNTS.{json,md}, PRIORS_X.md, DRAFT_PREDECLARATION_X1_OVERNIGHT.md, fetch drivers) |

Proposed R1 screen picks (mine, in order): **X1** (spec-ready), **TS1** (cheap, expected-null),
**CAL1** (cheap lens), **C3** (gated behind the 2026-10-19 FADE read) + the **IX1 no-slot
recorder** (free, starts the PIT clock).

## Findings you should see before ruling

1. **The corpus's `open` field is degraded and worsening** — `open == prev_close` on 21–34% of
   mega-cap name-days 2022+ and 47–56% of liquid-panel name-days 2023–2025. Any open→close
   outcome silently includes overnight moves for those rows. X1's draft predeclaration therefore
   restricts the primary outcome to valid-open members (spec deviation #1, needs your approval
   at R2). This likely affects OTHER in-flight work that uses opens — worth a program-wide note.
2. **Discovery halves are survivorship-biased by construction on free data**: 0 of 541 pre-2021
   panel names die before 2026 (Yahoo purges delisted names; memo 07's 54/929 is the older
   history_long corpus, which is absent on this host).
3. **TLK ADS ratio**: the brief's "1 ADS = 20 shares" was stale — 20→40 (Jul-2004 split), →200
   (Sep-2013 split), →**100 (2016-10-26, pure ADS change)**. Gate PASSES: no ratio event appears
   as a return in the acquired series.
4. **JISDOR is publicly downloadable without auth** (the BI page's own XLSX export; 3,236 rows
   2013-05→2026-10) — added as an auxiliary series. The standalone postback driver still needs a
   debug pass (the probe's copy is pinned by sha256 meanwhile).
5. **FTSE Russell has a clean no-auth notices API** (AnnouncedDate/EffectiveDate, ASEAN tags) —
   the IX1 path. MSCI bulk data is registration-gated. Lock-up dates: no public source. Google
   Trends: skip (ToS/429). Wikipedia pageviews: usable from 2015-07 (zero-days omitted).
6. **Suspension archive**: 359 real events 2022-04→2026-07; the other 2,830 rows are data-gap
   artifacts. Pre-2022 suspension history does not exist on free data.

## Blockers needing your ruling (ZCode took no unilateral action)

1. **Mimosa commit gate vs your untracked artifacts.** `Claude outputs/exhaustion_study_…/parabolic_bracket.py`
   and `parabolic_reversal.py` contain `exec(open(...))` which Mimosa flags HIGH ("code
   injection") and which **hard-blocked this session's `git commit`** of unrelated, clean files
   (the cross-asset acquisition). The study artifacts must stay verbatim (frozen evidence), so
   the resolution is yours: (a) relocate `Claude outputs/` out of the scanned tree, (b) accept a
   per-commit override, or (c) authorize excluding that directory from the scan. All session
   outputs are written and synced but **uncommitted**; a single commit after your ruling captures
   everything. Relatedly, the W0 byte-copies of the two `exec()` scripts into the output folder
   are pending (the scanner rejects their content on copy); the other 18 artifacts' checksums are
   recorded in place.
2. **`ZCODE_BRIEF_BROAD_SEARCH_V2_2026-10-05.md` (commit c2a743f) never reached this host** —
   neither the file nor the git object, ~3h after your message. I worked from your message text;
   if Syncthing is paused on either side, a push/pull or manual copy will reconcile layouts (I
   placed W0–W3 under `P-M/broad_search_v2/` by convention — say the word if the brief's output
   dir differs and I'll move them).
3. **Snapshot DB absent**: `walkforward-20261004-213000.db.zst` never arrived, so X1 Phase 0 ran
   on the local `walkforward.db` (ends **2026-07-29**; fingerprint recorded). If you want the
   extra ~10 weeks of confirmation days, the snapshot has to be copied over Twingate first.
4. **NotebookLM ingestion** of the two verified priors can't happen from this host (no Google
   session); PRIORS_X.md carries the verbatim quotes locally. Handoff item for the XPS session.

## State summary (one line each)

- Branch `research/new-order-2026-09-30`; first commit `9025189` (POC pair re-executed and
  reproduced within +3 rows of memo 04) — later commits blocked (blocker 1).
- Bar after W0: **|t| ≥ 3.2501** (N=515); with X1's 6 arms **3.2534** (N=521).
- X1 usable days: A 1,166 / B 2,169 / C 839 / D 1,326 (brief split) / E 1,166 / F 2,174;
  MDE 14–22bp/day per 1σ of signal.
- Waiting on: nothing — Gagnon–Karolyi verification landed (PRIORS_X.md complete, P0-A gate
  passes).
- Next gates: your R1 picks → freeze predeclarations → your R2 review → runs.
