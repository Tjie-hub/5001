# 00 · Overlap Check — dividend-YIELD LEVEL vs every dividend row in the exclusion index (2026-10-28)

**Question (L1 of `ZCODE_BRIEF_C003_DIVIDEND_YIELD_G0_2026-10-28.md`):** is the proposed arm — TTM
dividends-paid / month-end price, monthly formation, top-200 KSEI-mcap, 209 formations 2009-04→ — a re-skin of
any closed dividend arm? Rows cited from `P-M/search/00_EXCLUSION_INDEX_2026-10-28.md`.

## Every dividend row in the index, and the difference

| Row | What it tested | The difference from the LEVEL sort |
|---|---|---|
| **C4 / HYP-PM-0017 D1** (FAILED F2, D-077) — pre-cum demand: anchored run-up into the ex-date | An **event window** around each ex-date: does price drift UP into a known future calendar point? | The level sort holds a **standing book** keyed on the *trailing* payout rate; it takes no position on any single ex-date, enters/exits only at month ends, and its signal (TTM DPS/P) exists continuously, not in a window. Different estimand (rate premium vs event drift), different formation (monthly vs event-time), different horizon (1m+ vs 5d window). |
| **C4 / HYP-PM-0017 D2** (FAILED F2, D-077) — ex-day tax-clientele capture (yield ≥ 2%) | Capture the ex-day drop itself (+2.00% gross, below bar, decaying) — again **event-time**, holding across one ex-date | Same distinctions; additionally D2's population was *high-yield payers at their ex-date*, this arm's population is *the whole panel ranked by yield every month* — D2 is nested inside the level arm's top quintile only in population, not in construct. The D-077 decay-by-year (2021 +10.3% → 2026 −0.3%) is a statement about the event capture, not about the level premium; the level arm re-risks it over 2009→ with 4× the formations. |
| **F5 / alpha_search_v2 #6** (exploratory POSITIVE, unregistered, debt declared) — dividend yield top-20% | **This is the same construct's origin**, on 2021–26 only, mean/median tests, exploratory | Not a *closed* arm — the prior. The differences from the proposed arm: era extended 2021–26 (59 formations) → 2009–2026 (209); PIT rule now D-111 v3 (the prior used ex-dates strictly before t from corp events — equivalent discipline, different source); the floor/bar stop rule is new. Its multiplicity debt is disclosed in SKEL-C-003 §4 and in the freeze draft; per the brief it is NOT used to choose floor, universe or sign. |
| **D-064 §D ex-date monitor / D-064 issuance adjustment** — infrastructure around ex-dates | Tooling (φ wealth-correction at rights/bonus ex-dates; detection-only monitor) | Not a tested arm at all; this arm *uses* that machinery as data hygiene. |
| Adjacent non-dividend rows that could be confused | **D1** B/M + ROE (null), **D6 {FQ} E/P** (open), **D2** composite issuance (dead), **C6 {CF}** issuance supply (null) | Different fundamentals: payout rate is neither valuation (B/M, E/P), nor profitability (ROE), nor issuance. The FM-over-E/P incremental test is pre-registered in SKEL-C-003 exactly because E/P is the nearest OPEN neighbour, not a closed one. |

## Verdict

**Not a re-skin.** The two failed dividend arms were event-time designs around ex-dates (run-up; drop capture);
this arm risks the standing payout-rate premium on a monthly panel. The one prior of the same construct
(alpha_search_v2 #6) is disclosed as debt, unregistered, and is not evidence per this brief's rules. Proceed to
L2.
