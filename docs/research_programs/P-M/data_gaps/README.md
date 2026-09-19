# Data-gap pipeline — how to rebuild the 26-year panel

The extended panel is the reason anything in P-M reached statistical
significance. It is **not** a one-off: rebuild it rather than patching the
5-year panel, and run the steps in this order.

## Pipeline

| # | script | produces | ~time |
|---|---|---|---|
| 1 | `fetch_sector.py` | `sector_map.pkl` — ticker → sector/industry, 98.6% | 13 min |
| 2 | `fetch_history.py` | `hist_pre2021.pkl` (1.41M bars to 2005) + `hist_meta.pkl` | 40 min |
| 3 | `fetch_div_hist.py` | `div_hist.pkl` — 4,690 events to 2000 | 13 min |
| 4 | `fetch_splits.py` | `split_hist.pkl` — 279 events, 202 tickers | 3 min |
| 5 | `ext_panel.py` | `ext_panel.pkl` — 43,136 name-months, 295 months | 5 min |
| 6 | `ext_test.py` | the overlay / dividend results | 2 min |

`fetch_quarterly.py` is retained but **produced nothing usable**: the source only
holds quarterly fundamentals from 2024-12, median 5 observations per ticker.

Bulk outputs are deliberately **not committed** (73MB raw). The scripts are
deterministic against a public source, so regenerate rather than store.

## Five traps, each of which produced a wrong answer before it was caught

1. **Split adjustment must apply to pre-2021 rows ONLY.** The settled DB corpus
   is already back-adjusted — verified by the absence of a price jump at the
   BBCA, HEAL and GOOD split dates. Adjusting the merged series double-counts
   every post-2021 split.

2. **Dividends must NOT be re-adjusted.** The source already puts them on
   today's share basis. Verified on 54 splits with dividends either side: the
   observed pre/post DPS ratio is 0.70 against a median split ratio of 3.66,
   correlation −0.099. Adjusting again inflates pre-split yields precisely on the
   oldest data — the only part the extension adds.

3. **A trailing-window feature at the left edge of a source is TRUNCATED, not
   zero.** Computing a trailing-12m dividend from a table beginning 2021-07
   understates yield for every formation date in the first year. This produced a
   false accusation that `corporate_actions` was missing 2.8% of dividends; it is
   not (see `CORRECTION_2026-09-19.md`). Either exclude a warm-up year or use a
   source whose history predates the panel.

4. **`pgrep -f <name>` matches the shell that WROTE the script.** A chained
   fetch waited 37 minutes on a pattern that matched its own creating shell's
   heredoc. Three instances of this class occurred in one session. Never gate a
   background job on `pgrep` of a string that appears in the launching command.

5. **The tradeability filter is far more selective on old data.** Zero-volume
   rates run 24–43% in 2003–09 and 17–22% in 2014–18 against ~5% post-2021, so
   the strict filter admits 76 of ~200 pre-2021 months. That subset is more
   liquid and more continuously traded than the modern panel — the samples are
   not the same population. Always report results across several filter
   definitions, as `ext_test.py` does.

## What the panel can and cannot answer

**Can:** volatility overlay, dividend yield, and any price/volume factor, over
~16–26 years.

**Cannot:** value, quality, profitability, size — no fundamentals exist before
2021-12, and trap-listed `fetch_quarterly.py` confirms quarterly history is
unavailable from this source at any depth.

## Headline result

Sector-neutral volatility tail-exclusion: **t 4.70 full panel, t 3.48–4.22
out-of-sample** (pre-2021, used in none of the ~140 in-sample trials), effect
stable at **+0.236 to +0.310%/mo** across five tradeability definitions. See
`EXTENDED_PANEL_RESULT_2026-09-19.md`.
