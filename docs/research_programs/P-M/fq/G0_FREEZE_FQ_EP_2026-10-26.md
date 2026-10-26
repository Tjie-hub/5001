# {FQ} E/P value premium — G0 FROZEN (2026-10-26)

**Status: FROZEN on owner approval, 2026-10-26 ("approve and go").** Implements D-112. Frozen **before** the 92-code
pull lands and before any panel breadth or return has been computed. The draft
(`G0_FREEZE_FQ_EP_DRAFT_2026-10-26.md`) is kept as history. This file's sha256 is pinned in
`g0_fq_ep_breadth.py` and in the D-entry. Amendment only by a superseding D-entry; no rule changes after the run.

**No outcome read.** Everything below comes from metadata, counts and contemporaneous balance-sheet values. No return
from any month t to t+1 has been computed.

---

## 1. Inputs

| Input | File | sha256 |
|---|---|---|
| PIT rule (D-111) | `P-M/data_acquisition/13_FQ_PIT_RULE_FROZEN_V3_2026-10-26.md` | `8c78b96f12cd83c652eedf652b1cf7af8a52a8eea8e6bbfda3a20c52bdacb457` |
| Late filers (R5) | `P-M/data_acquisition/12_FQ_LATE_FILERS_2026-10-26.csv` | `b549358b68e560aba806ca7b99514853056b8ac8cc07ec8d343cf22b1c691e8c` |
| FY exceptions (R7) | `P-M/data_acquisition/13b_FQ_FISCAL_YEAR_EXCEPTIONS.csv` | `013af724fed5291c46e0872eb6d3a5eceb64e1420a26a2a71d4995b4d77f1089` |
| Universe, price, shares | `~/idx_external/ksei/ksei_equity_holdings.csv` (2009-03 … 2026-09) | `38c8a90b10546f0602d4568b277d79d154f994e5cafb921bd0d73c3ce55df781` |
| USD/IDR | `~/idx_external/fx/usdidr_month_end_yahoo_2026-10-26.csv` | `a0937cde0221f6a7d0e9f5b9e81060c67a30026672a0a686240f6e8e085ee1b9` |
| Fundamentals | `~/idx_external/stockbit_fin/fin.db` after the 92-code pull (timer 19:05) | the `fin.db` line of `SHA256SUMS_2026-10-26.txt`, written after the parse; that file's own sha256 goes in the D-entry |

The G0 script verifies every pin above (and `fin.db` against its sums file) and refuses to run on any mismatch.
Script sha256: recorded in the D-entry (it embeds this file's sha256, so it cannot be listed here).

## 2. Formation dates and universe

- **Formation dates D:** the KSEI file dates (the last trading day of each month), **2009-05 … 2026-08** (208 dates).
- **Universe at D:** KSEI rows with a 4-letter code (common equity; preferred/class codes excluded), price > 0,
  ranked by market cap = `sec_num × price` at D; **top 200**, ranked after the stale-price filter below.
- **Stale-price entry filter:** a name is not formed at D if its KSEI price was identical at D, D−1 and D−2 (a
  suspension proxy using past data only).

## 3. Fundamentals at D

- **Availability: D-111.** D ≥ usable_from(i, P), with R5 (late filers withheld) and R7 (FY exceptions; off-quarter
  fiscal years excluded). A period end in the store that is not a Mar/Jun/Sep/Dec month end is excluded the same way.
- **D11 at monthly granularity, without a full holiday calendar.** Every deadline in D-111 is a calendar month end.
  If KSEI's file date for that month equals the calendar month end, the deadline was a trading day and usable_from is
  the next month end. Otherwise the deadline moved into the next month, and usable_from falls in the month after
  (≤ ~10th), so the first qualifying D is that month's KSEI date. This reproduces R3 exactly at month-end granularity.
- **Earnings:** "Owners Of The Company" (`Pemilik Entitas Induk`), the row under "Net Income Attributable To" in the
  income statement. **TTM** = sum of the 4 most recent consecutive discrete quarters, all usable at D. If the latest
  usable quarter's window is blocked (missing, withheld, currency-ambiguous), the next-older window of 4 is tried
  (D-111 R5), down to a **staleness cap: the window's latest quarter must end within 15 months of D**; otherwise E/P
  is missing at D.
- **Currency.** `fin.db` stores each issuer's reporting currency without a field. Per issuer-period,
  r = vendor derived equity (IDR-converted) ÷ statement "Total Ekuitas". The derived row is "Total Equity (Quarter)"
  (total equity), or "Total Equity" after the statement rows in the late-filer layout (55 tickers, where it is
  parent equity, so r runs ~0.5–1.0). Only the magnitude is used:
  - 0.2 < r < 5 → IDR; 5,000 < r < 25,000 → USD; otherwise unclassified.
  - A period with no balance-sheet values takes the issuer's currency from its nearest classified periods within
    4 quarters either side, if they do not conflict.
  - **USD quarters convert at Yahoo's USD/IDR month-end close for the period-end month.** Checked against the
    vendor's own implied rate (total-equity layout) on 4,908 USD periods: 0 outside 3%.
  - Unclassified → E/P missing for any TTM that needs that quarter.
  - Measured 2026-10-26 on the current store: 38,701 IDR, 5,223 USD, **51 unclassified** of 43,975 issuer-periods.
- **E/P** = TTM owners' NI (IDR) ÷ market cap at D. **Negative TTM → excluded from the rank** (not from the universe).

## 4. Portfolios and returns (computed at G1 only)

- **Terciles** of valid E/P within the universe at D; **value-weighted** by market cap at D; long top − short bottom;
  hold one month.
- **Return D → D+1:** KSEI price ratio, adjusted for splits.
  - **Split rule:** k = sec_num(D+1) ÷ sec_num(D). Treat it as a split/consolidation, and multiply the price ratio
    by k, only if all three hold: k ≥ 1.5 or k ≤ 0.67; k or 1/k is within 2% of a whole number ≥ 2 (IDX splits use
    whole ratios, rights issues rarely do); and price(D+1) ÷ price(D) is within ±25% of 1/k. Otherwise use the raw
    price ratio (issuance and rights are not adjusted). A rights issue at an exact whole ratio with a deep discount
    can still pass; such rows are listed in the result for inspection, without a rule change.
  - **Price-only:** no dividends (conservative against value).
  - **Delisting:** a name absent at D+1 exits at its last KSEI price (return to that print). A **−100% row** is
    reported beside the result (D-065 v2 §2).
  - Rows with a period return below −95% after split adjustment are reported separately (D-065 v2 §2).
- **Statistic:** mean monthly long–short return, Newey–West SE with **6 lags**, **one-sided** (premium > 0), against
  the census bar **3.300069** at registration (`e_max_abs_z(614)`, `deflation_audit/bar_v2.py`).
- **Costs:** net line at 0.60% round trip × measured turnover, beside the gross result.

## 5. G0 checks and stop rule (no returns)

G0 builds the panel and reports **breadth only**:

1. A formation month **qualifies** if the universe has ≥ 120 names with valid E/P (≥ 40 per tercile).
2. T_eff = qualifying months ÷ 12. Prior-only power = Φ(0.75·√T_eff − 3.300069), from D-112's floor (IDX E/P IR 0.75).
3. **Stop rule: fire if power < 20%**, i.e. if fewer than **129 qualifying months** (T_eff < 10.74 y). If it fires:
   WITHDRAWN before registration, uncounted (precedents D-087, D-102, D-110).
4. Also report, without a rule attached: the USD share of the universe by year; the share of universe names with
   missing E/P by reason (no data, withheld, negative, currency-ambiguous, FY-excluded); coverage of the 92
   newly pulled codes.

## 6. Pre-declared sensitivities (G1, reported, never substituted)

B/M (statement total equity in IDR ÷ market cap, latest usable quarter) · ROE (TTM ÷ that equity) · equal-weight ·
the −100% delisting row · era split at 2021-07 (D-070) · without the formation months that can use D-111's covered
late-filer periods (Dec 2024 – Aug 2026) · USD reporters excluded · top-100 universe.

**Report-only lines in the script:** the FX cross-check (§3) and the 92-code coverage (§5.4), plus per-month
missing reasons and USD counts.

## 7. Run

1. 19:05 timer: pull and parse the 92 codes. Then write `SHA256SUMS_2026-10-26.txt` (raw/* + fin.db + manifest)
   and check the store still satisfies D-111 R1 (period ends, quarter mapping); any off-quarter end is excluded above.
2. D-entry: this file's sha256, the script's sha256, the sums file's sha256.
3. G0 runs **once**: breadth and power only. The stop rule decides.
4. If it does not fire: registration (HYP-PM-0023, N = 614) and G1 **only on the owner's separate go**.
