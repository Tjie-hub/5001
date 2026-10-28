# G0 FREEZE — C-003 dividend-yield level (DRAFT, PROPOSE-ONLY — not pinned)

**Status: DRAFT.** The owner pins this freeze (records its sha256 in `g0_dy_breadth.py::FREEZE_SHA256`) before
any G0 run. Nothing here is registered; no HYP id; no family slot; no D-entry filed. The in-repo prior
(alpha_search_v2 #6: mean t 2.46 / median t 4.11 on 2021–26) is **disclosed multiplicity debt and is NOT used
to choose the floor, universe, sign or any parameter below** — the construction follows the mechanism, the
{FQ} panel machinery, and the program's cost/bar authorities.

## 1. Inputs (pinned)
KSEI monthly holdings csv (sha `38c8a90b…`), Yahoo USDIDR month-end (sha `a0937cde…`), {FQ} late-filer list
(`b549358b…`), fiscal-year exceptions (`013af724…`), fin.db as pinned by `SHA256SUMS_2026-10-26.txt`
(`caefb1a2…` — the same post-92-code-parse state the {FQ} G0 pins; any fin.db change needs a re-pin decision).
Extraction: `extract_dividends.py` v1.1 (v1 `72d2f6d`; v1.1 2026-10-28 replaced the f-string SQL predicate in
`_ticker_currency` with constant SQL + bound labels — currency output identical on all 998 tickers; 20 synthetic
tests) — vendor label whitelist for
parent dividends-paid, NCI/subsidiary/received/tax/advance exclusions, DISCRETE/CUMULATIVE layout classifier,
USD-reporter conversion at period-end month rate, D-111 v3 deadlines, late-filer withholding.

## 2. Universe and formation (proposed)
- Monthly formation at KSEI month-ends 2009-04 → 2026-09 (209 formations; 2 warm-up months).
- Universe per month: top-200 by KSEI market cap (sec_num × price), stale-price filter (D-112 rule).
  Liquidity gate: the freeze must pin ONE of (a) KSEI price ≥ Rp 50 all eras + ADV ≥ Rp 1bn from 2021-07 where
  ohlcv exists, or (b) price ≥ Rp 50 only. ({OC} used an ADV basis 2009→ whose source is not in this tree —
  the owner either re-derives it or picks (b).)
- Numerator: TTM cash dividends paid = sum of quarterly payouts whose period_end lies within 12m of the newest
  D-111-available period (disclosure-anchored), 15-month staleness cap, withheld periods excluded.
- Signal: TTM payout / KSEI market cap (total-payout yield; no per-share arithmetic).
- Book: long-only top quintile of valid-yield names (≥ 30 valid names required to form), EW, monthly
  close-to-close, net D-082 cost_realised on turnover.

## 3. Coverage gates (the G0's first verdict)
- **Formability:** ≥ 80% of the 209 months must have ≥ 30 valid-yield names (measured: median ≈ 68 valid
  names/month; every year 26.5–41.1% name-month coverage — formability holds throughout; the descriptive
  name-month payer coverage is 33.9%).
- Name-month coverage is REPORTED, not gated (the original 60%-of-panel idea in SKEL-C-003 was mis-specified
  for a payer-only signal; non-payers have yield 0, not missing data).

## 4. Power (the G0's second verdict, prior-only)
- SD source: pre-registered placebo — random quintile assignment on the same panel months, monthly
  quintile-spread SD from the placebo draws (no dividend-yield sort output touched). Same convention as the
  PEAD/{FQ} G0s.
- Floor: **PROPOSED 0.80%/mo net** (owner pins; floor < 0.60%/mo → stop). Bar **3.300069** (census 613 + this
  arm; the owner states the census bump at pin). Pass: power at the floor ≥ 20%, MDE80 reported.
- Expected scale (from the {OC} calibration on the same panel construction): SE ≈ 0.6–0.7%/mo → power at
  0.80%/mo ≈ 33–45%, MDE80 ≈ 1.7–2.0%/mo. If the owner wants 80% power the floor must be ≈ 1.7%/mo — stated
  plainly, not chosen for them.

## 5. Stop rule (proposed)
Fires (→ WITHDRAWN before registration, uncounted) if: formable share < 0.80, or floor power < 0.20, or the
pinned floor < 0.60%/mo, or a pinned-input mismatch. One run; crash-only re-run per the standing rule.

## 6. Family options for the owner (both as text, costed)
- **Option A — widen {FQ} (fundamentals family):** the dividend-yield arm joins the family the E/P arm opened.
  Deflation cost: the census moves 613 → 614 (+1); the bar rises by ≈ e_max_abs_z increment at N=614
  (≈ 3.3001 → 3.3003, negligible). Correlation governance: the FM incremental test (yield vs E/P, size,
  Parkinson-60, VOLEX, t ≥ 2) becomes part of the registered kill rule — the arm must carry information E/P
  does not.
- **Option B — new Payout ({PY}) family:** separately denominated; census 614 either way; the family ledger
  gains a slot; the FM-over-E/P separator is still mandatory at G1 (distinctness is empirical, not nominal).
  Cost: none in inference; a small bookkeeping cost (family ledger row).
- The options are inference-equivalent (the census counts arms, not families); the choice is about what
  future arms may piggyback (Option A makes later fundamentals arms siblings of E/P + yield; Option B keeps
  payout/contractual mechanisms separate). **Sequencing (per the approved shortlist): this G0 runs after the
  {FQ} E/P G0 result — if E/P stopped, the FM separator at G1 runs against a dead control and the family
  question is moot until E/P is ever re-opened.**

## 7. What the G0 script does NOT do
No return, spread, t-stat, IR or P/L of any dividend-yield sort; no sort of the panel by yield; no reading of
the alpha_search_v2 outcomes. If a step seems to need one, it stops and asks (brief rule).

## 8. Registration text (draft, family blank — filed only by the owner)

> **HYP-PM-00NN · {family} · dividend-yield level (payout-commitment risk premium).** Long-only top-quintile
> total-payout-yield book (TTM dividends paid / KSEI market cap, D-111 v3 PIT, universe per the freeze) vs the
> EW liquid book, monthly 2009-04→, net D-082 cost. H₁: net monthly spread ≥ +0.80% with |t| ≥ 3.3001, both
> halves > 0, FM incremental over E/P, size, Parkinson-60, VOLEX (t ≥ 2). Kill: t < bar, either half ≤ 0, or
> FM incremental < 2 (re-labelled value). Declared debt: alpha_search_v2 exploratory trial #6 (2021–26);
> census 613 → 614 at registration.

## 9. D-entry proposal (text only — do not file)

> ### D-1xx · Mechanism accepted: dividend-yield level (payout-commitment premium); C-003 G0 freeze pinned
> **Status:** (RECORDED when the owner pins it) · **Type:** mechanism + G0 freeze · **Approval authority:**
> the owner's shortlist approval 2026-10-27 + the standing G0 stop rule (precedents D-083, D-088, D-105,
> D-112). Scope: standing payout rate as a risk premium; NOT the D-077 ex-date event arms (distinct per
> `dy/00_OVERLAP_CHECK_2026-10-28.md`). Family decision: Option A/B per freeze §6. Floor pinned at __%/mo.
> Inputs pinned per §1. G0 once; stop rule per §5; registration only on a separate owner go.
