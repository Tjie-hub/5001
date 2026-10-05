# 05 · news_mentions history extension ({N}) — FEASIBILITY MEMO · 2026-09-30

**Item (D-c #5):** news-mention history is 2026-04 onward only (~5 months at the handoff date);
the proposal is a **forward attention recorder**, not a screen — underpowered by construction
until ~2027-04 (`FAMILY_MAP_v2.md` §F). Scoping memo; **explicitly no action requested.**

## Verdict

**Nothing to acquire — the recorder already exists and accrues.** `news_mentions` (ticker, date,
count, headlines_json) is being populated daily by the existing pipeline (93,492 rows →
2026-09-28 on production per the map; the Windows mirror's stale copy shows 54,217 → 2026-09-22,
consistent with the two-machine DB split). The only "acquisition" left is *time*.

## What this memo contributes (prior + decision framing, no work)

- **Literature prior** (Owner's NotebookLM corpus, "Wisdom of the Crowd", 35 sources, queried
  2026-09-30): IDX-specific studies support an attention *channel* — Google SVI co-movement with
  return co-movement (β = 0.1147, p < 0.01, 418 IDX names), herding → short-term returns
  (β = 0.287, p = 0.007) with explicit crash/bubble-risk caveats, and turnover thresholds on
  IDX80 (speculative turnover ~doubles past +1.15% daily return, ~triples when 21d vol > 2.61%).
  These are cross-sectional/behavioral relations, **not** demonstrated timing signals — and every
  registered broker/flow test on IDX in our own program is null (C-family closed, HYP-PM-0006
  Holm p = 0.6128). Prior: attention data is more likely to explain *when* flow-family nulls
  bite than to be a tradable edge itself.
- **Decision point:** when the window reaches ~12 months (2027-04), a pre-declared screen of
  attention spikes vs own trailing median becomes possible. Until then the item costs nothing and
  earns nothing — leave it accruing.
- **Cheap insurance (note only):** the recorder's retention/coverage is production-side; a
  one-line periodic check that `news_mentions` is still accruing (and a quarterly gap report)
  would protect the 2027-04 decision point. That is ops hygiene, not research work — flagging,
  not doing, per brief scope.

## Effort estimate

- Now: **0** (no action).
- 2027-04 screen readiness: whatever a pre-declared screen normally costs (predeclaration +
  one run + census entry).
