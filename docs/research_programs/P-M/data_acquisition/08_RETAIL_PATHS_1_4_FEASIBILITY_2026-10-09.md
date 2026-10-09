# Retail-trader paths 1–4: data acquisition and feasibility (2026-10-09)

**Status:** feasibility only. No returns, forward returns or event outcomes were read, so no census arm
is consumed (D-071). No hypothesis is registered and DECISION_LOG is untouched.
**Why:** after D-070 closed the price-pattern search, a web survey of IDX retail-trader evidence surfaced
four mechanism-led paths that weren't in the 09-30 scoping memos (01–07).
**Data location:** `~/idx_external/` (outside the repo). Nothing was written to `walkforward.db`.

## Summary

| # | Path | Mechanism (D-070 class) | Data now | Backtest window | Blocker left |
|---|---|---|---|---|---|
| 1 | Retail-broker order imbalance | liquidity provision to retail demand | in hand (`broker_flow`) | 2025-01 → now (96 names); 2026-04 → now (~830 names) | breadth backfill before 2026-04 (owner op) |
| 2 | Retail ownership share and flow (KSEI) | retail lottery overpricing / retail inflow | **acquired**: 211 months 2009-03 → 2026-09 | 2009 → now, monthly | publication-date PIT rule; denominator choice |
| 3 | Margin-list inclusion / exclusion (+ short-sell list from 2026-10) | institutional / rule constraint (leverage access) | pilot: 2 monthly lists | 2019 → now if curated | monthly list curation (~90 lists) |
| 4 | Special-monitoring board (notation X, full call auction) | rule constraint (trading mechanism) | recorder started: snapshot 2026-10-09 | forward only | no downloadable history; needs a daily cron |

Ranking: **2 first** (the only path with a long, complete PIT-able history in hand), then **1** (ready
now on a short window), then **3** (curation work), then **4** (forward recorder only).

## Path 1 — retail-broker order imbalance

- **Mechanism:**
  - Retail traders' aggregated orders are noise demand. Whoever absorbs it is paid in subsequent returns.
  - Literature: Kaniel, Saar and Titman 2008 (retail net buying, then positive returns); Barber, Odean and
    Zhu 2009 (herded retail buying, then reversal at longer horizons); Kelley and Tetlock 2013;
    Boehmer, Jones, Zhang and Zhang 2021.
  - **The sign is the open question, and it must be pre-declared at G0.**
- **Why this is not FAIL-PM-0007:**
  - FAIL-PM-0007's market-wide broker net is identity-attenuated, because every buy has a sell.
  - A *group* net isn't. Retail-group net / gross per stock-day has mean +0.003 and **sd 0.204** over
    118,315 stock-days.
  - FAIL-PM-0003 (adverse selection) used the same dataset, so a G0 must show the signal is distinct
    from its I7 construction.
- **Frozen classification (proposed), set with no outcome data:**
  - **Formation window:** 2025-01-02 → 2025-03-31, BUY side. That window is then excluded from any test.
  - **Rule:** value per trade ≤ Rp 6M.
  - **The rule gives XL 2.27M, XC 2.45M, YP 4.99M, PD 5.13M, KK 5.81M.** The next broker is YB at
    6.88M, with every other broker at ≥ 7.6M.
  - These five are also the online-retail platforms named in public lists: Stockbit, Ajaib, Mirae,
    IPOT and Phillip.
  - Their share of gross value in the 96-name panel is 10–17% a month.
  - Caveat: retail traders using bank-owned brokers (CC, NI, …) are invisible to this rule, so the
    signal is "online-retail" imbalance, not all-retail.
- **Coverage:** `broker_flow`:
  - 2025-01 → 2026-03: 96–99 tickers (the liquid panel)
  - from 2026-04: 830–870 tickers
  - 418 sessions in total
  - The volume-basis break (2026-07-06) doesn't apply, since broker lots are regular-market only.
- **Breadth backfill started 2026-10-09:** research-side only, never touching walkforward.db.
  - `~/idx_external/broker_flow/backfill.py`, running detached: 764 tickers, 211,767 ticker-days from
    2025-01-02 → 2026-03-31.
  - **Throttle incident:** the first run, at 0.15 s spacing, drew empty (throttled) marketdetectors
    replies after about 1,500 calls. Recovery came within minutes (14:06).
    - Now: off-hours only (22:30–08:00 and weekends), 1 call/s, and an empty reply backs off 60/180/600 s
      before it's recorded.
    - Nightly cron 22:30 under `flock`. About 62 off-hours, roughly one week.
  - It is resumable: error lines are dropped and retried on the next run, and never filled.
  - Vendor limit: the top 25 brokers per side.
- **G0 brief staged:** `ZCODE_BRIEF_RETAIL_BROKER_IMBALANCE_G0_2026-10-09.md`. Path 2's brief is
  `ZCODE_BRIEF_RETAIL_OWNERSHIP_KSEI_G0_2026-10-09.md`.

## Path 2 — KSEI retail ownership (acquired)

- **Source:** KSEI public archive (Balancepos, holding composition), one zip per month-end:
  `https://web.ksei.co.id/Download/BalanceposEfekYYYYMMDD.zip`.
  - No login. Fetched politely, with one request at a time.
- **Coverage:** 211 months, 2009-03-31 → 2026-09-30, with **no gaps** (2008 is not in the archive).
  - 141,543 equity stock-months; 433 tickers in 2009, 1,009 in 2026.
- **Fields:**
  - Per stock: listed shares and price.
  - Share counts for local/foreign × {IS insurance, CP corporate, PF pension, IB financial institution,
    **ID individual**, MF mutual fund, SC securities co, FD foundation, OT other}.
- **Checks:** the per-type sums equal the local + foreign totals in every row (0 failures).
- **Descriptive (no outcomes):** median individual share of custodied shares:
  - 14% (2016)
  - 21% (2021)
  - 27% (2026)
- **Two rules to freeze at G0:**
  1. **PIT:** the zip's internal timestamp is about 3 days after month-end (2026-09-30 → 2026-10-01
     06:00), but the web publication date isn't recorded.
     - Proposed conservative rule: known from the 5th trading session of the following month.
     - Start a forward log of first-seen dates now, to confirm it.
  2. **Denominator:** the custodied total is well below listed shares. TOWR is 26.2B vs 59.1B and BBCA
     52.5B vs 123.3B, apparently controlling stakes held outside these accounts.
     - Choose ID / listed shares or ID / custodied total, and state why.
- **Tools:** `~/idx_external/ksei/fetch_ksei.sh` (resumable) and `parse_ksei.py` →
  `ksei_equity_holdings.csv`.

## Path 3 — margin and short-sell eligibility lists

- **Mechanism:**
  - Margin eligibility gives retail traders access to leverage, which brings levered demand on
    inclusion and forced deleveraging on exclusion.
  - Short-sell eligibility relaxes the short-sale constraint (Miller 1977).
  - IDX publishes a monthly list: Peng-xxxxx/BEI.POP, effective at the start of each month.
- **History:**
  - Lists exist monthly from at least 2019 (Kontan, IPOT and CNBC report each month's changes).
  - **Short-sell history (corrected the same day):**
    - All short-sell lists were revoked on 2020-03-02.
    - Lists reappeared later: four new short names in July 2023, 116 shortable names in June 2024, and a
      short-selling launch on 2024-10-03.
    - Short-sell *financing* resumed 2026-09-15, with a new list effective 2026-10.
  - So the short leg has a broken but non-empty history. Map its regime dates at G0.
- **Access:** idx.co.id returns 403 to scripted requests (Cloudflare). We don't bypass it.
  - Copies are re-hosted by brokers and on Stockbit.
  - Pilot: April 2025 (252 names) and April 2026 (285 names) parsed cleanly with `pdftotext`. Between
    them, **66 additions and 33 removals**.
  - So roughly 100 events a year, or 600–700 since 2019.
- **Remaining gap:** curate one list per month, 2019-01 → now (about 90 PDFs).
  - Sources: re-hosted PDFs, plus news articles that list ins and outs.
  - Or the owner downloads them from idx.co.id in a normal browser.
  - Record for each list the announcement date, which is the PIT date, and the effective date.
  - Files: `~/idx_external/margin/`.

- **Progress 2026-10-09 (later):**
  - `~/idx_external/margin/kiwoom_ledger.py` scraped Kiwoom Sekuritas' monthly posts. They cover
    **2019-07 → 2020-02 only**: 7 posts, 100 change rows (45 ADD, 55 DROP), each with its post date.
    Output: `kiwoom_changes.csv` plus raw text in `kiwoom_posts.json`.
  - **2020-03 → now is still missing.** Coverage is patchy across outlets (Kontan, Bisnis, EmitenNews,
    CNBC, IPOT).
  - idx.co.id serves a Cloudflare challenge to scripts and to headless browsers, and we don't bypass it.
  - The Chrome extension wasn't connected.
  - **Remaining action (owner):** in a normal browser, download IDX's monthly "Daftar Efek … Transaksi
    Marjin dan/atau Short Selling" announcements for 2020-03 → 2026-10 (about 80 PDFs) into
    `~/idx_external/margin/`.
    - Parsing is proven: `pdftotext -layout`, then ticker rows. The April 2025 and April 2026 pilots
      gave 252 and 285 names.

## Path 4 — special monitoring board (notation X)

- **Mechanism:** placement moves a stock to full call auction, a rule-imposed liquidity cut. Removal
  restores continuous trading. The literature (IDX event studies) measures only volatility and
  liquidity, not returns.
- **History:** none downloadable.
  - The board started 2024-03-25.
  - Stockbit `/emitten/{t}/info` exposes only today's notation codes, plus the UMA flag from the
    orderbook endpoint and index membership.
  - `suspension_events` is detector-derived, not announcement-dated.
- **Done today:** `~/idx_external/status/snap_status.py` records a daily PIT snapshot of all tickers
  (notation codes, UMA, status, index list, ARA/ARB). It is read-only, and the token is never printed.
  - First run 2026-10-09: **916 tickers, 0 errors**.
  - Notation counts: **X 49**, E 37, Y 34, L 33, M 10, D 7, B 6, S 6, F 4, other 6. **UMA 1.**
  - The snapshot also gives a PIT history of index membership (LQ45/IDX30/IDX80…) from today, which
    serves D-070 item 4 (index reconstitution).
- **Scheduled 2026-10-09:** user crontab `0 22 * * 1-5` (moved from 17:05 so it stays clear of the
  production broker jobs from 18:30 to 21:00), logging to `~/idx_external/status/cron.log`.
  To stop it, remove the line tagged `idx_external`.
  - Backfill: none possible (the Wayback Machine was offline, and idx.co.id is challenge-gated). The path
    is forward-only by design.
  - G0 trigger: n ≥ 20 X-removals recorded.

## Draft mechanism D-entries (for owner acceptance; not filed)

These are required by D-070 before any G0. Each states the mechanism, the falsifier and the design. None
names a result.

1. **Retail-broker imbalance:** online-retail net order flow (frozen 5-broker group) is absorbed by
   liquidity providers.
   - Prediction: weekly retail net buying is followed by negative excess returns at 1–4 weeks
     (liquidity-provision reward). A positive sign would be the Kaniel-Saar-Titman variant; G0 must pick
     one.
   - Design: pooled cross-section, Fama-MacBeth weekly sorts, net of `cost_realised`.
   - Window: test only after the formation window.
2. **KSEI retail share:**
   - (a) Level: stocks with high individual ownership are overpriced lottery-like names, so they
     underperform in the next month.
   - (b) Flow: a rise in individual share (retail inflow) is followed by underperformance.
   - Design: monthly cross-section 2009 → 2026, controlling for size, Parkinson volatility (VOLEX) and
     momentum.
   - Must show incremental value over VOLEX, the surviving risk premium.
3. **Margin list:**
   - Inclusion is followed by levered demand: positive drift from the announcement to the effective date.
   - Exclusion brings forced deleveraging: negative drift.
   - Design: event study on the announcement date, as a pooled event panel.
   - Feasibility gate: the curated count.
4. **Notation-X board:**
   - Placement is followed by a liquidity collapse and a discount.
   - Removal brings a return of continuous trading and recovery demand.
   - Forward-only. Accrue events, then G0 when n ≥ 20 removals.

## Sources

- KSEI archive: https://web.ksei.co.id/archive_download/holding_composition
- Margin lists: https://link.brights.id/brids/storage/pdf/List_Margin_25_Maret_2025_IDX.pdf ·
  https://stream-asset.stockbit.com/56e400bc-9885-44cc-b0ed-bf12777df348_stream.pdf
- Short-sell history: https://investasi.kontan.co.id/news/bei-rilis-efek-transaksi-margin-dan-shortselling-periode-juni-2019-berikut-daftarnya ·
  https://www.cnbcindonesia.com/market/20210113185405-17-215750/bei-hidupkan-lagi-transaksi-short-selling-siapa-terdepak ·
  https://ajaib.co.id/belajar/berita/short-selling-mulai-berlaku-hari-ini-bei-terbitkan-daftar-saham
- Retail share of trading 2025: https://www.idnfinancials.com/news/60059/retail-investors-dominate-the-market-ojk-warns-of-speculative-stocks
- Attention → volume, not returns (IDX80 2021–25): https://journal.unnes.ac.id/journals/jcs/article/download/53895/10103
- Retail lottery amplification: https://www.nber.org/system/files/working_papers/w29543/w29543.pdf
- Broker codes: https://www.mediasaham.com/2025/10/daftar-kode-broker-saham-lokal-dan-asing-di-bei.html
