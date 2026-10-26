# {FQ} mechanism — DRAFT for owner decision (2026-10-26)

**Status: DRAFT — propose-only.** Nothing here opens a family, accepts a mechanism, freezes a G0 or adds to the
census. Those are owner decisions (§6). Builds on D-111 (the frozen {FQ} PIT rule) and on
`P-M/priors/RC_FQ_001_DRAFT_2026-09-30.md` and `POWER_MEMO_2026-09-30.md`, which were written before any
historical fundamentals existed.

**No outcome read.** No return, spread, IC or factor score was computed. The facts below are counts from
`~/idx_external/ksei/ksei_equity_holdings.csv` and `fin.db`, plus prior-only power arithmetic.

---

## 1. Mechanism

**Value (earnings yield, E/P) as a risk premium.** Cheap stocks carry distress and cash-flow risk that investors are
paid to hold. D-070 §1 admits risk premia as a mechanism class. This is not a price-pattern signal: the signal is
reported earnings over price, with price used only as the denominator.

- **Why E/P and not B/M:** the IDX prior is stronger for E/P (IR 0.75 vs 0.61, Rouwenhorst IDX 1990–97), and
  RC-FQ-001 already fixed E/P as primary with B/M as a sensitivity only.
- **Negative earnings:** excluded from the E/P rank that month, not floored (RC-FQ-001; Fama–French convention).
- **Behavioural reading (M5):** if the owner prefers to call this mispricing rather than risk, OBJECTIVES_2026H2
  puts the heavier burden on it. The test is identical either way; only the stated mechanism changes.
- **Profitability (ROE):** RC-FQ-001 combined it with value. Recommended here as a **reported sensitivity, not a
  second test**, to keep this to one census trial (§6, D-FQ-1).

## 2. Data — the survivorship problem is solvable with data already on disk

| Need | Source | Status |
|---|---|---|
| PIT fundamentals | `fin.db` + D-111 | 957 tickers, 2006-12 … 2026-09 |
| Survivorship-complete universe | KSEI monthly `Balancepos` (2009-03 … 2026-09, 211 months) | **1,055 equity codes**, incl. delisted (e.g., AQUA, BATI, BRAU, CTRS) |
| Month-end price + shares | same KSEI files (`price`, `sec_num`) | every code, every month listed |
| Fundamentals for codes `fin.db` lacks | Stockbit fin endpoint (keeps delisted history: BTEL, TRAM verified 10-20) | **98 codes missing** (49 gone from the latest KSEI month). In 2009, 80 of 433 KSEI equities (18%) lack fundamentals; in 2021, 52 of 804 |

**Gap to close:** pull the 98 missing codes from Stockbit (≈ 300 GETs, ≈ 8 min at 1.5 s; same endpoint, token-only,
stop on 401/403/429). This is an owner ToS call, like the 10-21 pull.

**Price caveats, all stated on the card:**
- KSEI price is a month-end level. Returns are **price-only**: no dividends. That biases *against* value
  (high-yield names lose their dividend), so it is conservative for this mechanism.
- **Splits/bonus:** adjust with `sec_num` (price × shares continuity). Issuance moves `sec_num` too, so a rule is
  needed: treat a jump as a split only when price moves by the inverse ratio within tolerance. To be frozen in G0.
- **Suspended names** carry a stale price. Rule (G0): no entry on a month whose price is unchanged from the
  prior month **and** whose shares are unchanged (an entry-side filter that uses past data only).
- **Delisting:** exit at the last KSEI print, with a **−100% sensitivity row** (D-065 v2 §2).
- **Universe:** no survivorship-complete daily volume exists before 2021, so ADV60 cannot define the universe.
  Use **top-N by market cap** (`sec_num × price`) at each month-end; N fixed in G0.

## 3. Power from priors only (G0 stop-rule arithmetic)

Monthly cross-sections from 2009-05 (first month the FY2008 numbers are usable under D-111, inside KSEI's span) to
2026-08 (the last with a next-month price): **208 months, T = 17.33 years.** Bar at the next registration
(N = 614): **3.300**. Expected t = IR·√T, power = Φ(E[t] − bar).

| Prior (annual IR) | E[t] | Power | With a 50 % post-publication haircut: E[t] | Power |
|---|---|---|---|---|
| E/P, IDX 1990–97 (0.75) | 3.12 | **43.0 %** | 1.56 | 4.1 % |
| B/M, IDX 1990–97 (0.61) | 2.54 | 22.4 % | 1.27 | 2.1 % |
| Value, EM aggregate 1987–97 (1.15) | 4.79 | 93.2 % | 2.39 | 18.2 % |
| E/P, EM aggregate 1987–97 (1.34) | 5.58 | 98.9 % | 2.79 | 30.5 % |

For contrast, the clean post-2021-07 window alone (T = 5.08 y): E/P IDX power **5.4 %**. **The KSEI backfill is what
makes {FQ} testable at all.**

**Reading.** With an un-haircut literature prior (the D-109 precedent: the floor comes from external literature,
taken as published), E/P clears the 20 % minimum. With a realistic decay haircut it does not, unless the EM prior is
used. So the floor choice decides whether the stop rule fires, and it must be fixed before any data is touched.
Caveats on the priors themselves: Rouwenhorst's IDX sample is 8 years (1990–97) and was verified through a
NotebookLM summary, not the paper's own tables (POWER_MEMO v2). The LWZ IDX series named in D-065 v2 was never
obtained.

## 4. Test sketch (to be frozen in G0, not now)

- **Primary:** long top-⅓ E/P minus bottom-⅓, value-weighted within the top-N market-cap universe, monthly
  rebalance, t+1-month price return, Newey–West SE, one-sided (value premium > 0).
- **Costs:** a net line at 0.60 % round trip times the measured turnover (no turnover is measured before the freeze).
- **Pre-declared sensitivities (reported, never substituted):** B/M; ROE; equal-weight; the −100 % delisting row;
  the era split at 2021-07 (D-070 records repeated era flips); results with and without D-111's covered late-filer
  window (D-111 residual).
- **D-111 residuals** carried on the card.

## 5. Sequence

1. Owner decisions (§6).
2. If approved: pull the 98 missing codes (ToS), parse into `fin.db` under a new sha256 pin.
3. Build the monthly panel research-side (KSEI + `fin.db` + D-111). Report coverage only.
4. Freeze G0 (rule card, floor, universe N, split rule, stop rule), sha256-pinned in a D-entry.
5. Run G0 power check (prior-only plus panel breadth); stop rule fires below 20 %.
6. If it passes: registration (census N = 614), then G1 once.

## 6. Decisions for the owner

| # | Decision | Recommendation |
|---|---|---|
| **D-FQ-1** | Open family {FQ} and accept the mechanism | **E/P value as a risk premium; one arm** (B/M, ROE as sensitivities only) |
| **D-FQ-2** | G0 power floor | **E/P IDX IR 0.75, as published** (D-109 precedent), with the 50 % haircut row reported beside it. Alternative: EM E/P 1.34 haircut 50 % (power 30.5 %) |
| **D-FQ-3** | Stockbit pull of the 98 missing codes | **Approve**, outside market hours, token only, stop on 401/403/429 |
| **D-FQ-4** | Universe | **Top-200 by month-end market cap** from KSEI (no survivorship-complete volume pre-2021) |

PEAD's G0 runs tonight (17:45). If its stop rule fires on power, that is about event-study dispersion on earnings
dates. It does not bear on a monthly cross-sectional design, which pools ~200 names a month.

## 7. Owner response (2026-10-26)

Recommended option on all four: **D-FQ-1** E/P value, one arm · **D-FQ-2** IDX E/P 0.75 as published · **D-FQ-3** pull
approved · **D-FQ-4** top-200 by market cap. Filed as **D-112**. The six preferred/class codes (EDJSA, EDJSB, MAMIP,
MYRXP, TALFA, TALFB) are outside the common-equity universe, so the pull is 92 codes, scheduled 19:05 WIB.
