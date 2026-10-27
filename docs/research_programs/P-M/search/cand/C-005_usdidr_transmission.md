# C-005 · USDIDR transmission: FX-regime × currency-exposure rank

**Status: PROPOSE-ONLY. Data PARTIAL — classification quality is the gating question.**

## 1. Mechanism
Rupiah depreciation raises the local value of USD-linked revenues and USD cash, and strains USD-debt issuers.
With a floating USDIDR and monthly KSEI/price panels, conditioning a long-only book on the FX regime exploits a
macro transmission channel (M4.4 flow / M3.1) that is rule-free but structural: the exposures are accounting
facts (reporting currency, revenue currency), not price patterns. Persistent because IDX macro hedging is thin
and retail-dominated flow underreacts to FX moves.

## 2. Falsifiable prediction
State: USDIDR monthly Δ (Yahoo month-end, 216 months verified 2008-12→2026-10). Book: after a top-quintile
depreciation month, hold the top-quintile USD-reporting names (or USD-cash-heavy) vs the EW liquid book for 1m;
reverse condition for appreciation. Pass: conditional spread ≥ 0.60%/mo net, t ≥ 3.30, both halves. Kill:
unconditional-on-FX performance of the same legs is indistinguishable (the FX condition adds nothing), or either
half ≤ 0.

## 3. Data
FX: `~/idx_external/fx/usdidr_month_end_yahoo_2026-10-26.csv` (216 rows — full depth, verified). Currency
exposure: **partial.** Known today: 108 USD reporters via the {FQ} magnitude check (fin.db); revenue-currency
split and USD-debt per name are NOT in fin.db. Proxy ladder: (i) USD-reporter flag (108 names, coarse — includes
exporters AND offshore holding structures); (ii) commodity-sector proxy via the 82/959 sector map (CPO/coal/
nickel names — thin); (iii) acquisition: IDX financial-statement notes (Stockbit call volume: ~2 requests ×
959 tickers ≈ one evening within the existing rules) for revenue-currency disclosure — legality: public
filings, no login scraping. Prices: 2009→ via backfill+KSEI.

## 4. Counts and prior-only power
Conditional design halves the sample: ~40-45 formation months per FX state (216/5… realistically 209/5 ≈ 42 per
quintile state). Rank SE on 42 months ≈ 1.5%/mo → MDE80 ≈ 3.7%/mo — **UNDERPOWERED at plausible FX-transmission
effects (0.5–1.5%/mo)**; power at 1.0%/mo ≈ 15%. Verdict: **UNDERPOWERED as a quintile-state design.** A
continuous FX-beta FM cross-section (monthly regressions, 209 months pooled) restores SE ≈ 0.7%/mo on the
interaction term — power at 1.0%/mo ≈ 40%: marginal. Recommend the FM form if pursued.

## 5. Non-overlap proof
Nearest rows: **C3/C7** (breadth/intensity STATES — flow states, not FX); **A10** market-stress reversal (an
IHSG-level event, FAILED — this is an FX conditioning, and A10's failure was about reversal, not transmission);
**B6 C2** (foreign vs local brokers — agents, not currency). No prior arm used any macro series.

## 6. Cost / capacity
Monthly, small legs (~20-40 names), turnover ~0.3 in FX-stated months only; no event execution. The D-059
friction test applies at entry.

## 7. Distinctness from the live book
Formation calendar shared with {FQ} (monthly) but signal source (FX × accounting) unrelated to E/P — correlation
should be low; FM incremental still mandatory. Vs T1 forward test: no overlap.

**Note:** if the owner wants this family, the honest sequence is (1) decide on the classification acquisition,
(2) FM-form G0. As-is: NOT recommended this cycle (classification gap + power).
