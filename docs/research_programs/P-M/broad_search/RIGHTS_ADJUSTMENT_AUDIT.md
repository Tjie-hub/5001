# RIGHTS_ADJUSTMENT_AUDIT — brief phase 0 (2026-09-29)

**Question (brief §5).** How many ex-rights, bonus or reverse-split dates fall inside the formation
or holding windows recorded in the FADE-001, VOLEX-001 and REGIME-002 ledgers — and does an
unadjusted ex-date drop plausibly create or kill a signal? **Read-only, counts only, no returns.**
No ledger was touched. Driver: `phase0_counts.py` (committed next to this file); snapshot
`walkforward-20260928-213012.db` sha256 `10f9c97f…46c13`, integrity_check ok.

## 1 · Recorded windows and hits

| ledger | recorded windows | ex-dates inside a window |
|---|---|---|
| FWD-PM-REGIME-002 | 18 (2026-09-17 … 2026-09-28) | **0** |
| FWD-PM-FADE-001 | 0 (`trades: []` — first append due ~2026-10-19) | 0 (none exist) |
| FWD-PM-VOLEX-001 | 0 (first maturities ~2026-10-15) | 0 (none exist) |

Prospective exposure, 2026-09-17 → 2026-09-28 (the forward tests' active window so far): **0**
ex-dates of any rightissue/bonus/stock_reverse/stocksplit event in the whole corpus.

**Answer to the headline question: currently immaterial — 0 recorded windows contain an ex-date.**
If the answer had been material, this finding would have outranked every screen; it does not arise.

## 2 · Is the corpus actually unadjusted at these ex-dates? (counts of jumps, not returns)

The research price corpus applies **splits only** (`data/adjustments.py`; D-063 settled that FORU's
×19.5 discontinuity stands unadjusted in the raw corpus). Counting 1-session moves beyond the
±35% SPLIT_BAND within [ex−1, ex+1] in the merged research panel (2013+ events with measurable
prices):

| event type | ex-dates 2013+ (ex ≤ 2026-09-16) | measurable in panel | corpus carries a >35% jump |
|---|---|---|---|
| rightissue | 315 | 273 | **17** |
| bonus | 71 | 66 | **4** |
| stock_reverse | 12 | 10 | **2** |
| stocksplit | 167 | 138 | 3 (splits are adjusted at source; residual) |

Reading: the mechanical ex-rights drop is **real and mostly BELOW the ±35% detection band**
(median rights factor 1.43 ⇒ a ≈ −30% zero-NPV drop), so SPLIT_BAND/bigmove21 eligibility guards
catch only the largest events (17 rights + 4 bonus + 2 reverse = 23). The corpus *does* carry
unadjusted mechanical drops on issuance-type ex-dates; the exposure is structural, not current.

## 3 · Plausibility per forward test (reasoning from the counts; no outcome read)

- **FADE-001 (failed-breakdown fade).** An ex-rights day prints a large drop that can open below
  the prior-20-session low and close there — i.e. an ordinary *breakdown*, which FADE would fade
  long. Fading a mechanical −30%…−95% repricing is not an edge; it is arithmetic. With 153 rights
  ex-dates 2021+ and ~80 signals/month across the liquid book, a future h20 window will eventually
  span one. The recorder's per-signal rows would be contaminated on those names.
- **REGIME-002 (ATR-trailed trend).** A mechanical drop collapses the ATR trail and exits a live
  position at a fake loss (kills an edge spuriously), or fakes an onset afterwards. 0 hits so far.
- **VOLEX-001 (volatility exclusion).** Trailing vol windows spanning an ex-date are inflated by
  the mechanical drop; the exclusion bucket would wrongly include/exclude names around it.

## 4 · Recommended standing guard (proposed, owner-decided — not acted on)

Every recorder (FADE h20 windows, REGIME holds, VOLEX formations) should **censor/flag any window
spanning a same-ticker `rightissue`/`bonus`/`stock_reverse` ex-date from `corporate_action_events`**
(the 23 >35%-jump events are the acute subset; sub-band factors ≈ −30% are still material). This is
a proposed entry for the handoff, not a change to any frozen protocol.

## 5 · Inventory carried forward to the screens (brief rule 4 compliance)

- rights issues: 315 events 2013+ with `rightissue_created` (announcement stamp) present on 100%;
  `rightissue_factor` (m − 1 = ratio new/old) and `rightissue_price` (subscription) available ⇒ the
  wealth-corrected return across ex is computable per event: ret = (m·P_ex − c)/P_before − 1.
- bonus: 82 events (factor via `stocksplit_factor`, c = 0). reverse splits: 19 events (factor < 1,
  c = 0). Splits are already adjusted at source — no correction needed, verified by the jump counts.
- `rightissue_adj_factor` (vendor per-event adjustment factor) is populated on only 43/317 rows —
  unusable as a primary source; the ratio/price fields above are the correction basis.
