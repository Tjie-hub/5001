# {FQ} E/P value premium — G0 freeze DRAFT (2026-10-26)

**Status: DRAFT — for owner approval.** Implements D-112. When approved, the rules below are frozen (sha256 in a
D-entry) **before any panel return is computed**. Data pins are filled in after tonight's 92-code pull and parse.

**No outcome read.** Everything below comes from metadata, counts and contemporaneous balance-sheet values. No return
from any month t to t+1 has been computed.

---

## 1. Inputs (pins filled at freeze)

| Input | File | sha256 |
|---|---|---|
| PIT rule | `P-M/data_acquisition/13_FQ_PIT_RULE_FROZEN_V3_2026-10-26.md` (D-111) | `8c78b96f…` |
| Late filers / FY exceptions | `12_FQ_LATE_FILERS_…csv` / `13b_FQ_FISCAL_YEAR_EXCEPTIONS.csv` | `b549358b…` / `013af724…` |
| Universe, price, shares | `~/idx_external/ksei/ksei_equity_holdings.csv` (2009-03 … 2026-09) | at freeze |
| Fundamentals | `~/idx_external/stockbit_fin/fin.db` after the 92-code pull | new `SHA256SUMS_2026-10-26.txt` |
| G1 script | `P-M/fq/g1_fq_ep.py` (tests: `tests/test_fq_g1.py`); refuses until registration is pinned | at registration |
| G0 script | `P-M/fq/g0_fq_ep_breadth.py` (tests: `tests/test_fq_g0.py`, 36 synthetic) | at freeze |
| USD/IDR conversion + check | `~/idx_external/fx/usdidr_month_end_yahoo_2026-10-26.csv` | `a0937cde…` |

## 2. Formation dates and universe

- **Formation dates D:** the KSEI file dates (the last trading day of each month), **2009-05 … 2026-08** (208 dates).
- **Universe at D:** KSEI rows with a 4-letter code (common equity; preferred/class codes excluded), price > 0,
  ranked by market cap = `sec_num × price` at D; **top 200**, ranked after the stale-price filter below.
- **Stale-price entry filter:** a name is not formed at D if its KSEI price was identical at D, D−1 and D−2 (a
  suspension proxy using past data only).

## 3. Fundamentals at D

- **Availability: D-111.** D ≥ usable_from(i, P), with R5 (late filers withheld) and R7 (FY exceptions; off-quarter
  fiscal years excluded).
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

B/M · ROE · equal-weight · the −100% delisting row · era split at 2021-07 (D-070) · with/without D-111's covered
late-filer window · USD reporters excluded · top-100 universe.

**Report-only lines in the script:** the FX cross-check (§3) and the 92-code coverage (§5.4), plus per-month
missing reasons and USD counts.

## 7. What the owner approves at freeze

The rules in §2–§6 as written, the data pins in §1 once filled, and the stop rule in §5. After the freeze, G0 runs
once. If it passes, registration (HYP-PM-0023, N = 614) and G1 run once. No rule changes after the freeze.
