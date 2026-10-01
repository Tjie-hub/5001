# SPEC — EXT-BSJP: IDX retail "beli sore jual pagi" (close → next-morning) · Phase A

**Date:** 2026-10-01 · **Status:** PHASE A SPEC (docs only). **Not registered.** No hypothesis id,
no family slot, no gatekeeper run. **Owner decision 2026-10-01:** proceed with R1 (BSJP) from
`RETAIL_IDX_SURVEY.md`.
**Branch:** `spec/external-strategy-intake` · **Gate to Phase B:** P1 (research-fence cutover) must
have landed; then a Rule Card (`research/rulecard/`, D-055) is frozen from this SPEC before any
outcome is computed.

## 0. Snooping log (what has and has not been looked at)

| Looked at | When | Purpose |
|---|---|---|
| Video claims (win rates, returns) | 2026-10-01 | intake — treated as marketing, §6 |
| **Signal counts only** per variant, local `walkforward.db` snapshot (to 2026-07-29) | 2026-10-01 | power planning, §7 |
| **Any forward (next-open / next-day) return of any event** | **never** | — |

Nothing in this SPEC was chosen after seeing an outcome. Every threshold below is the source's own
number; where the source is ambiguous the SPEC picks a default **before** data and lists the
ambiguity in §9.

## 1. Source of record (verbatim, grep-verifiable)

All in `SOURCE/retail_idx/` (auto-transcripts via NotebookLM; NotebookLM full text has no
timestamps, so references are file + exact string). Quotes below were grep-checked 2026-10-01.

| Var | File | Rules as stated (verbatim Indonesian) |
|---|---|---|
| **a** | `YT_5zoKb511hL8_*` | "harga kemarin ditutup naik lebih dari 5%"; "Open lebih dari SMA 20 and close kurang dari SMA 20"; value "lebih dari Rp1 miliar"; screen "jam 1551 sampai dengan 15.58"; TP "harga beli ditambah 2%" (order booking, next morning); "minus 2% Cut loss" |
| **b** | `YT_Vt0zI0v0Bsk_*` | "kenaikan harga saham hari ini minimal 10%"; "nilai transaksi hari ini minimal 1 miliar"; "beli pucuk"; sell next morning |
| **c** | `YT_yE0qlHaz1ck_*` | "kenaikan baik itu high ataupun close minimal 20%" (DSI: high > previous close × 1,2); "nilai transaksi minimal 10 miliar"; exclude "uma repo tidak dijamin sedang cumdate dividen bad news"; BSJP entry at the close; SL "2% di bawah harga beli" |
| **d** | `YT_gKzpAzVl3Xo_*` (Kokocuan) | "nilai transaksi sebesar 5 miliar 10 miliar"; price "naik dalam beberapa persen tertentu" (unquantified); "maksimal beli tuh tiga saham doang dalam sehari"; "belinya jam 15.50"; "besok paginya jual" |
| e | `YT_Le-wAwIjLHM_*` | AmiBroker "JJS Cetar" fractal-breakout bot — rule not disclosed → **excluded** (§4) |

## 2. Mechanism (hypothesis, not assumption)

**Statement.** Stocks that drew attention today (large up-move, high value) close into the
pre-closing auction with unmet demand; attention-driven retail buying at the next open lifts the
open above the close. BSJP harvests that close → open gap.
**Loser.** Retail buyers who chase at the next open (the BSJP exit sells to them).
**Barrier.** No practical IDX short side; ARA locks ration supply at the limit, pushing unmet
demand into the next session.
**Competing prediction (must be tested, not ignored).** The same attention literature predicts the
open is *overpriced* and reverses intraday — that favours the pure next-open exit (E1) over
holding into the session (E2). And variants a/c buy names already up 5–20%: short-horizon reversal
predicts the opposite sign.

**Literature — tag [M] (from memory, NOT admissible as a prior until verified to [V]):**
- Berkman, Koch, Tuttle & Zhang (2012), "Paying Attention: Overnight Returns and the Hidden Cost
  of Buying at the Open", JFQA — high-attention stocks: high overnight return, intraday reversal.
- Lou, Polk & Skouras (2019), "A tug of war: Overnight versus intraday expected returns", JFE.
- IDX-specific overnight/limit-hit evidence: **none located yet** — Phase A open item §9-Q1.

With no verified IDX literature this is a **Tier N** card (`research/rulecard/card.py`:
t ≥ 3.0 and DSR ≥ 0.95), not Tier R.

## 3. Formal rules (frozen defaults)

Daily bars from `ohlcv` (`is_final=1`), split-adjusted per `corporate_actions` (existing
double-adjustment protection). Day *t* = signal/entry day, *t+1* = next trading day
(`trading_calendar`).

**Common definitions**
- `value_t` = close_t × volume_t (Rp). The DB has no traded-value column; this is an approximation
  (true value uses each trade's price) — §8.
- `ret_t` = close_t / close_{t-1} − 1.

**Event filters (per variant)**

| Var | Filter on day *t* (all must hold) |
|---|---|
| a | close_{t-1}/close_{t-2} − 1 > 5% **and** open_t > SMA20_t **and** close_t < SMA20_t (SMA20 of close, incl. day *t*, needs 20 bars) **and** value_t > Rp1B |
| b | ret_t ≥ 10% **and** value_t ≥ Rp1B |
| c | high_t ≥ 1.2 × close_{t-1} **and** value_t ≥ Rp10B **and** no dividend ex-date at *t+1* |
| d | ret_t > 0 **and** Rp5B ≤ value_t ≤ Rp10B; then **at most 3 names per day**, ranked by ret_t descending (the source gives no ranking; this default is fixed here, §9-Q3) |

**Entry fill (close-auction model — NOT the repo's P3 next-open default).** BSJP enters in the
pre-closing call auction, so the fill is close_t. The P3 convention (fill at next session's open)
exists for *intraday-decided* live signals and does not describe this strategy; using it would
erase the very return being tested.
- **Unfillable entry:** if close_t is at the ARA limit (close_t ≥ ARA(close_{t-1}) rounded down to
  the tick grid), the closing auction had no offer → **no trade** (P4-2 fillability authority,
  `engine/exits/price_limits.py`, applied to the *entry*). Expected to bind hard on b and c.
- Decision at 15:50 uses intraday information that daily bars only know at the close; the SPEC
  accepts filters on day-*t* close as the ~15:50 state (look-ahead of ≤10 minutes) and flags it §8.

**Exit models (both pre-declared; E1 is primary)**
- **E1 (primary) — "jual pagi":** sell at open_{t+1}. Pure overnight return. Unfillable if
  open_{t+1} is ARB-locked (no bid) → hold to close_{t+1} (conservative).
- **E2 — order-book TP/SL (variants a, c as stated):** TP at entry × 1.02, SL at entry × 0.98,
  evaluated on bar *t+1*: if open_{t+1} ≥ TP → fill at open; if open ≤ SL → fill at open; else if
  high ≥ TP and low ≤ SL in the same bar → **SL first** (daily bars cannot order them; pessimistic);
  else TP or SL if touched; else exit at close_{t+1}.
- **Success** = realized net P&L > 0. The sources' "success = intraday high ≥ +2%" definition is
  **not** used (it counts touches, not fills).

**Costs.** Round-trip 0.60% (D-059 cost authority) **plus** P4-6 liquidity-scaled slippage by
ADV as-of *t* (P4-1 as-of discipline). Gross results are reported but never used for a decision.

## 4. Multiplicity family (declared now, append-only from registration)

Family **EXT-BSJP** = {a, b, c, d} × {E1, E2} = **8 cells**. e is excluded (rule undisclosed).
DSR trial count = 8 from the first run. Per D-028 / PG-3 the family may only be widened by a
governance amendment, never narrowed; a dropped cell still counts.

## 5. Estimand and decision

- **Primary (per cell):** mean **net** return per trade. Events cluster by date (many names on the
  same day share market moves) → standard errors **clustered by trade date** (or day-level
  portfolio: equal-weight the day's trades, then NW t on the daily series — Phase B picks one in
  the Rule Card before running; default = day-level portfolio, NW lag 5).
- **Benchmark/null:** the unconditional close → next-open return of the same universe on the same
  dates (removes market-wide overnight drift).
- **Hurdle (Tier N):** t ≥ 3.0 on net, DSR ≥ 0.95 at trials = 8, and positive net in ≥ 4 of the 5
  calendar years. Out-of-sample: the last 12 months of data held out and evaluated once.
- **Regime breakdown** reported (BULL/BEAR/SIDEWAYS, `research/regime/`), never used to rescue a
  failed cell (NR7 lesson).

## 6. Claimed performance — unverified marketing

| Var | Claim | Why it is not evidence |
|---|---|---|
| a | 13/16 = 81% win, one December | n = 16, one month, success = high ≥ +2% |
| c | 43/45 = 96% win, one month | success = **high** > 2% (touch, not fill); top gainers at ARA unfillable at close |
| d | ~70% win, 1–2% gross/trade, 5–25%/month | self-reported, no sample, gross of costs |

## 7. Data-requirements check (local snapshot, signal counts only)

Local `data/walkforward.db` (Windows mirror; canonical production DB is longer): `ohlcv` final bars
2021-07-05 → 2026-07-29, 959 tickers, 1,055,598 rows.

**Signal counts (no outcomes computed), before the ARA-entry exclusion:**

| Var | 2021H2 | 2022 | 2023 | 2024 | 2025 | 2026H1 | Total |
|---|---|---|---|---|---|---|---|
| a | 155 | 309 | 282 | 239 | 421 | 394 | **1,800** |
| b | 1,367 | 2,008 | 1,615 | 1,685 | 3,491 | 2,203 | **12,369** |
| c | 670 | 889 | 658 | 599 | 1,684 | 1,124 | **5,624** |
| d (pre-cap proxy) | 2,149 | 4,046 | 4,320 | 4,029 | 4,948 | 3,118 | 22,610 (≤ 3/day after cap) |

Effective n is the number of **distinct trade dates** (≤ 1,216 in this snapshot), not events — power must be
planned on the day-level series (Phase B, from a planning σ that does not use these events'
outcomes).

| Requirement | Available? |
|---|---|
| OHLC + volume daily, split-adjusted | **yes** (`ohlcv`, `corporate_actions` split) |
| Dividend ex-dates (variant c exclusion; E1 across ex-date) | **yes** (`corporate_actions` dividend, 2,069 rows) |
| Trading calendar / suspensions | **yes** (`trading_calendar`, `suspension_events`) |
| Traded value | **approx only** (close × volume) |
| ARA/ARB band per date | **partly** — `price_limits.py` encodes the 2023 symmetric table only; 2021–2023 rules differed (§9-Q2) |
| UMA flags, "efek tidak dijamin", repo status (variant c exclusions) | **no** |
| Special-monitoring-board / full-call-auction membership | **no** — material: those stocks' "close" is a periodic-auction price |
| Delisted/inactive names (survivorship) | **weak** — only 14/959 flagged inactive (P4-7) |
| 15:50 intraday state, 09:00–09:30 next-morning path | **no** (stockbit_flow_bars coverage too thin) — daily-bar proxies used |

## 8. Known model gaps (documented, not silent)

1. Day-*t* close used as the 15:50 decision state (≤ 10-min look-ahead into the closing auction).
2. Traded value approximated by close × volume.
3. E2 intrabar ordering unknowable from daily bars → pessimistic SL-first.
4. Variant c's UMA / not-guaranteed / bad-news exclusions not implementable → c is tested without
   them; this is a deviation from the source and is reported as such.
5. Survivorship: universe built from currently-listed names (P4-7 open).
6. Special-board stocks not excluded (no data) — risk of fake fills at auction prints.

## 9. Open questions for the Owner (answer before the Rule Card freezes)

- **Q1.** Verify the [M] literature (§2) to [V] and search for IDX overnight / limit-hit studies.
  If none, Tier N stands.
- **Q2.** Historical ARA/ARB regimes 2021-07 → 2026: which BEI rule applied on each date? The
  entry-unfillable test needs the per-date ARA. Default if unanswered: tier table as in
  `price_limits.py` for all dates (ARA side), flagged as an approximation.
- **Q3.** Variant d's "naik dalam beberapa persen tertentu" is unquantified. Default fixed here:
  ret_t > 0, top-3 by ret_t. Alternative would be a new cell (widens the family).
- **Q4.** Do we want the data for special-board/UMA exclusions acquired before Phase B (cleaner c)
  or test as specified with the gaps in §8?
- **Q5.** Universe: all listed (as the videos screen) — default — or liquid preset
  (`liquid_idx_v1`)? Changing it later counts as a new cell.

## 10. Boundaries

- Phase B runs only in `research/` against the research fence; results go to the gatekeeper as a
  hypothesis. **Nothing is added to `engine/` or the scanner** unless a PROMOTE decision and a
  forward test exist (invariants 4, 9, 10).
- No `docs/research_programs/P-M/**` file is touched; this is not a P-M hypothesis.
- If the family fails, it is filed in `FAILURE_REGISTRY` with all 8 cells — including the ones
  that looked best.

## 11. Phase-A follow-ups (2026-10-01)

Research closure of §9-Q1 and §9-Q2 (brief `ZCODE_BRIEF_PUSH_PR_RECONCILE_2026-10-01.md` §5;
Q3–Q5 were already adopted at the SPEC's frozen defaults). Nothing in §0–§10 is edited by this
section; no forward return was computed; no Rule Card opened; nothing under
`docs/research_programs/P-M/**` was touched.

### 11.1 Q1 — §2 literature verified; IDX/ASEAN search

Both [M] citations were **opened** (not search-snippet-matched) and upgrade to **[V]**:

| §2 citation | Verified record | What was read |
|---|---|---|
| Berkman, Koch, Tuttle & Zhang (2012) | "Paying Attention: Overnight Returns and the Hidden Cost of Buying at the Open", *JFQA* **47(4)** (August 2012), pp. 715–741, DOI `10.1017/S0022109012000270` | Cambridge Core abstract, verbatim: "a strong tendency for positive returns during the overnight period followed by reversals during the trading day … concentrated among stocks that have recently attracted the attention of retail investors … more pronounced for stocks that are difficult to value and costly to arbitrage … The additional implicit transaction costs for retail traders who buy high-attention stocks near the open frequently exceed the effective half spread." The SPEC's one-line claim stands. |
| Lou, Polk & Skouras (2019) | "A tug of war: Overnight versus intraday expected returns", *JFE* **134(1)** (2019), pp. 192–213, DOI `10.1016/j.jfineco.2019.03.011` | RePEc/IDEAS abstract: "strong overnight and intraday firm-level return continuation along with an offsetting cross-period reversal"; across 14 strategies "profits are either earned entirely overnight … or entirely intraday, typically with profits of opposite signs." Consistent with the SPEC's use. |

URLs (opened 2026-10-01):
<https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/paying-attention-overnight-returns-and-the-hidden-cost-of-buying-at-the-open/F9AAD159B512C651F09D5D52011D88E0>
· <https://ideas.repec.org/a/eee/jfinec/v134y2019i1p192-213.html>

**IDX-/ASEAN-specific overnight-return or limit-hit studies: none admissible located.** The
sweep surfaced only Indonesian student/regional-venue items — each Q1-grade under
`LITERATURE_RESEARCH_STANDARD`, located via search snippets and **not opened** (recorded for
completeness, used for nothing): UNDIP DJOM article citing Berkman
(<https://ejournal3.undip.ac.id/index.php/djom/article/download/13203/12761>), UGM thesis on
overnight momentum
(<https://etd.repository.ugm.ac.id/home/detail_pencarian_downloadfiles/1507341>), IISTE JEDS
"overnight momentum" Indonesian-market study
(<https://iiste.org/Journals/index.php/JEDS/article/viewFile/42436/43703>), Hasanuddin 2024
thesis (<https://repository.unhas.ac.id/>), ResearchGate "Determinants of Momentum Strategy and
Return in Short Time Horizon: Case in Indonesian Stock Market"
(<https://www.researchgate.net/publication/324155700>). The only Indonesia-specific
**auto-rejection** study remains the in-repo LC-PM-0010 (Ma'rifah et al., Q1-Nominal).
**Verdict: Tier N stands** (§2/§5 unchanged).

### 11.2 Q2 — ARA/ARB regimes in force, 2021-07 → today

Regular-board equities only (special-monitoring board and IPO-first-day 2× bands are out of
scope, as in `ARB_REGIME_TABLE_v1`'s scope note). Tier table means: Rp50–≤Rp200 → 35%,
>Rp200–≤Rp5,000 → 25%, >Rp5,000 → 20% (minimum share price Rp50 throughout, until R5).

| # | Sessions | ARA (up) | ARB (down) | Legal basis |
|---|---|---|---|---|
| R1′ | 2021-07-05 → 2023-06-02 | tiered 35/25/20 | flat **−10%** all tiers | Pandemic-era asymmetric policy: −7% from 2020-03-13 (OJK FSR No. 04-2020), restored to −10% effective 2020-06-02 (Detik; BEI Annual Report 2020). In force, unchanged, across the whole SPEC window start. |
| R2 | 2023-06-05 → 2023-09-01 | tiered 35/25/20 | flat **−15%** | Kep-00055/BEI/03-2023 (issued 2023-03-30), staged normalization Tahap I (IDX siaran pers 1893 "Normalisasi Ketentuan Relaksasi Masa Pandemi"; Kontan; Bareksa). |
| R3 | 2023-09-04 → 2025-04-07 | tiered 35/25/20 | **symmetric** −35/−25/−20 | Same decree, Tahap II (Kontan 2023-08-31 "berlaku pada 4 September 2023"). |
| R4 | 2025-04-08 → 2026-09-25 | tiered 35/25/20 | flat **−15%** | Peraturan II-A amendment (decree number per in-repo `ARB_REGIME_TABLE_v1`: Kep-00003/BEI/04-2025 — not independently confirmed in this sweep); official IDX press release (EN/ID) opened. |
| **R5** | **2026-09-28 → 2026-12-31 (in force today)** | Rp1–10: **+Rp1 nominal**; >Rp10: tiered 35/25/20 | Rp1–10: **−Rp1 nominal**; >Rp10: flat **−15%** | **Kep-00136/BEI/09-2026 + Kep-00137/BEI/09-2026** (Perubahan Kedua atas Peraturan II-A; II-O DINFRA), issued 2026-09-21, effective 2026-09-28, PR **083/BEI.SPR/09-2026** — issuer document, opened and read verbatim. Minimum price Rp50 → Rp1. |
| R6 | 2027-01-01 → (announced) | unchanged | **symmetric** tiered restored (>Rp10); Rp1–10 stays Rp1/Rp1 | Same PR 083/BEI.SPR/09-2026 ("mulai berlaku 1 Januari 2027"). Announced, not yet in force. |

Sources (opened unless marked): IDX siaran pers 2704
<https://www.idx.co.id/id/berita/siaran-pers/2704> (R5/R6, primary, verbatim); IDX press
release on the 2025 ARB change <https://www.idx.co.id/en/news/press-release/2352> (R4; ID
version at siaran-pers/2352); consolidated II-A decree text whose header reads
Kep-00136/BEI/09-2026
<https://www.idx.co.id/Media/y0vjxqur/signed_peraturan_ii_a_perdagangan_efek_bersifat_ekuitas.pdf>
(PDF — located, not parsed this session); Kontan
<https://investasi.kontan.co.id/news/bei-pastikan-auto-rejection-simetris-berlaku-pada-4-september-2023>
and Bareksa
<https://www.bareksa.com/berita/saham/2023-08-31/bei-aturan-baru-batasan-persentase-auto-rejection-simetris-berlaku-mulai-4-september-2023>
(R2/R3, secondary); IDX siaran pers 1893
<https://www.idx.co.id/id/berita/siaran-pers/1893> (R2/R3 title located; page bot-walled);
Detik 2020-06-02
<https://finance.detik.com/bursa-dan-valas/d-4932313/bei-ubah-batas-auto-rejection-bawah-10-mulai-hari-ini>
and OJK FSR 04-2020
<https://www.ojk.go.id/id/data-dan-statistik/financial-stability-review/Documents/OJK%20FSR%20%20No.%2004-2020.pdf>
and BEI AR 2020 <https://idx.co.id/media/9969/2020.pdf> (pre-window COVID history, secondary).

In-repo corroboration: `docs/research_programs/P-M/reference/ARB_REGIME_TABLE_v1.json`
(behavioural session-exact boundaries R2→R3; R4 bounded 2025-03-18 < switch ≤ 2025-04-08).

**Consequences for Phase B (recorded; no decision taken here):**

1. **ARA side (§3's entry-unfillable test): the tier table 35/25/20 is valid for the entire
   local snapshot (2021-07-05 → 2026-07-29).** Every regime kept ARA tiered above Rp10, and the
   minimum price was Rp50 until 2026-09-28, so no in-window name can fall into R5's Rp1–10
   nominal band. §9-Q2's default (use `price_limits.py`'s tier table for the ARA side) is
   therefore exact on current data, not an approximation.
2. **ARB side (E1's ARB-locked open; E2's SL floor): `price_limits.py`'s symmetric table is
   wrong outside 2023-09-04 → 2025-04-07.** The Rule Card must date-stamp ARB: −10%
   (2021-07-05 → 2023-06-02), −15% (2023-06-05 → 2023-09-01), symmetric tiered (2023-09-04 →
   2025-04-07), −15% (2025-04-08 → snapshot end 2026-07-29).
3. **R5/R6 start after the snapshot's last bar (2026-07-29)** — no effect on Phase B with
   current data; revisit only if the research fence is ever refreshed past 2026-09-28.
4. `ARB_REGIME_TABLE_v1` (2026-09-14) records R4 as open-ended and knows nothing of R5/R6 — it
   is stale by one regime and should be regenerated before any D-2 primary-verification close
   (P-M scope; not touched in this follow-up).
