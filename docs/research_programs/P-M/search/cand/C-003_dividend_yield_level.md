# C-003 · Dividend-yield level as a payout-commitment risk premium (monthly rank, 2009→)

**Status: PROPOSE-ONLY. Carries disclosed multiplicity debt** (alpha_search_v2 trial #6, 2026-09-19 — see §4).

## 1. Mechanism
A high trailing dividend yield is a standing payout commitment: cash leaves the firm monthly/quarterly, agency
costs fall, and the yield is a claim on real cash (hard to fake for long on IDX where payout is discretionary).
The premium is a **contractual/behavioural risk premium** (tax- and agency-based, M5.1/M3.1), not an earnings
forecast — distinct from the dead dividend EVENT arms (C4: those were run-up/capture windows around ex-dates).
Rule-based and public; persists after costs at monthly turnover ~0.16 with 0.60% RT (measured in alpha_v2:
net +7.07%/yr).

## 2. Falsifiable prediction
Formation: TTM dividends-paid / month-end price, only ex-dates strictly before t (PIT discipline already
demonstrated). Top-20% yield book vs EW liquid book, monthly, net 0.60% RT on turnover. Pass: mean monthly net
spread ≥ +0.60%/mo with t ≥ 3.30, both halves > 0, FM incremental over E/P, size, Parkinson-60. Kill: either
half ≤ 0, or FM incremental t < 2 (it must not be the value factor re-labelled).

## 3. Data
Dividends: **fin.db cashflow dividends-paid line** for 998 tickers (row-order layout machinery from {FQ};
coverage count to be run at build — the cashflow statement covers 998/998 tickers), plus walkforward
corporate-action events for 2021→ cross-check. Prices: KSEI + 5001 + backfill (2009→). PIT: {FQ} rule v3
(D-111) governs statement availability; dividends-paid lags period_end by the filing deadline — conservative
t+3-month availability like the {FQ} E/P build. Survivorship: KSEI-complete.

## 4. Counts and prior-only power
Prior evidence (in-repo, disclosed): alpha_v2 on 2021–26 only — mean +1.01%/mo t 2.46, median +1.32%/mo t 4.11,
net book +7.07%/yr; strongest in mid-caps; passes the median test that killed ma50/mom1/skew60/MAX.
Extending to 209 formations (2009→) cuts SE by ~√(59/209) ≈ 0.53: expected SE(mean) ≈ 0.22–0.30%/mo → t at the
prior mean ≈ **3.4–4.6 → power ~80–95% at a 0.80%/mo floor. POWERED — the strongest prior of any open cell.**
Multiplicity debt: the alpha_v2 92-trial census is already inside 613; this candidate adds 1 (the yield arm was
counted there as exploratory — an owner ruling may be needed on whether re-registration re-counts it; do not
assume it is free).

## 5. Non-overlap proof
Nearest rows: **C4/HYP-PM-0017** (dividend EVENT windows — FAILED; this is the standing LEVEL, different
construct, different horizon); **D6/{FQ} E/P** (earnings yield — the FM incremental test is the barrier; payout
and earnings yield can diverge: payers with depressed earnings); **D1** (B/M, ROE — null; yield is neither).
alpha_v2 #6 IS this candidate's origin — the debt is declared, not hidden.

## 6. Cost / capacity
Monthly, ~80 names, turnover 0.16 → cost drag ~0.10%/mo; ADV ≥ Rp 1bn gate; no event execution; capacity at
least that of {FQ}. The 6.25% deposit hurdle: net +7.07%/yr prior clears it, barely — the extended era (2009–21
deposit rates were higher) is the honest test.

## 7. Distinctness from the live book
**Highest correlation risk in the shortlist: same formation calendar as {FQ} E/P.** If the owner registers both,
the family governance must say whether {FQ} widens (payout arm) or a new family opens (K5 memo question). FM
incremental over E/P is the pre-registered separator, exactly as VOLEX was separated from momentum.
