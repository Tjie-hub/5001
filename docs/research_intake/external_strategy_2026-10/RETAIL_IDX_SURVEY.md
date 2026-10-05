# IDX retail-strategy survey (YouTube): candidate shortlist (pre-Phase A)

**Date:** 2026-10-01 · **Status:** CANDIDATES. Nothing is registered and no slot is consumed.
Companion to `CANDIDATES.md` (US quant videos).
**Sources:** 23 verbatim auto-transcripts in `SOURCE/retail_idx/` (NotebookLM notebook
`de280092-3cf7-45e2-a310-a315f515599c`). Of 26 videos selected, 3 had no transcript:
`15FuIwlk9dA`, `IjCRTpkLm_k`, `CIK4D-haFxg`.

**Method:**
1. Search YouTube across 12 retail families.
2. Pick the videos most likely to state rules.
3. Extract per-video rules via NotebookLM.
4. Check every rule quoted below by grep against the verbatim transcript.

Every win rate and return figure is the creator's own claim. Several define "success" as
**intraday high ≥ +2%**, not as a realized exit. That inflates win rate by construction (see R1).

**Repo context that filters this list:**
- Round-trip cost is about 0.60% (D-059), plus liquidity-scaled slippage (P4-6).
- ARA/ARB fills are bounded (P4-2).
- Falsified or failed families here:
  - breakout: NR7, ORB, Inside Bar, TFB;
  - broker-flow / bandarmology: FAIL-PM-0003, FAIL-PM-0007 (INVALID data), FAIL-PM-0001;
  - reconstitution: FAIL-PA-0001.
- P-M already holds value (RC-FQ-001, E/P).

---

## Result: 9 of 23 videos state testable rules. 14 are discretionary

| Family | Videos | Testable rules? | Verdict |
|---|---|---|---|
| **BSJP: buy at close, sell next morning** | 6 | yes (4 of 6) | **R1, top candidate** |
| Trend following, MA20 cross | 1 | yes, complete | R3 |
| "Swing karyawan" (MA20/50 + Stoch/MACD) | 1 | mostly (broker filter is discretionary) | R3 variant |
| December window dressing | 2 | calendar rule | R2 |
| High-volume breakout | 1 | entry only, no exit | breakout family already falsified |
| Opening volume spike (09:00–09:30) | 1 | entry only, intraday | no exit rule, needs intraday data |
| Bandarmology / foreign flow | 5 | no | the family already FAILED/INVALID in P-M |
| Value (Lo Kheng Hong, PER<10, PBV<1) | 2 | thresholds only | already covered by P-M RC-FQ-001 |
| Dividend cum-date | 2 | no | discretionary |
| IPO | 2 | no | commentary |

---

## R1. BSJP (*beli sore jual pagi*): overnight hold. **Recommended**

The most widely taught IDX retail strategy in this sample. It is an **overnight-return**
strategy: enter at the close (pre-closing call auction), exit at or after the next open. **No
family in this repo tests the close→next-open return.** It can be tested from daily OHLCV
already in `walkforward.db` (today's close → next day's open, high and low), with a large sample.

Variants as stated (quotes verified in the transcripts). Pre-declare them as one multiplicity
family:

| Var | Source | Filter (verbatim) | Entry | Exit | Claim |
|---|---|---|---|---|---|
| a | `5zoKb511hL8` | yesterday up >5% ("harga kemarin ditutup naik lebih dari 5%"); today's candle crosses below MA20 ("Open lebih dari SMA 20 and close kurang dari SMA 20"); value >Rp1B | pre-closing, screen at "jam 1551 sampai dengan 15.58" | TP: order booking at "harga beli ditambah 2%"; SL −2% by 09:30 next day | 13/16 = "Win rate-nya 81%" (one December) |
| b | `Vt0zI0v0Bsk` | today up ≥10% ("kenaikan harga saham hari ini minimal 10%"); value ≥Rp1B | pre-closing ("beli pucuk") | sell next morning | none |
| c | `yE0qlHaz1ck` | high ≥1.2× previous close ("minimal 20%"); value ≥Rp10B; exclude UMA, cum-date, non-guaranteed | at the close (BSJP) or at the open (scalp) | SL −2%, TP ≥2% | 43/45 = "Win rate-nya 96%", success = **high** >2% |
| d | `gKzpAzVl3Xo` (Kokocuan) | value Rp5–10B, rising; max 3 names/day ("maksimal beli tuh tiga saham") | "jam 15.50" pre-closing | sell next morning; stop trading at −10%/month | "Win rate di 70%-an", "1 sampai 2% … gross" |
| e | `Le-wAwIjLHM` | AmiBroker fractal-breakout bot | 14:51–15:15 | TP ≥3 ticks ("3 titik"), SL 3 ticks | none numeric |

Why it ranks first:
- IDX-specific and long-only.
- Uses existing data, with a large n (every qualifying stock-day).
- An untested return component (overnight).
- The mechanism is the documented overnight/close-auction premium and next-morning retail
  demand. Phase A must test that against the null, not assume it.

Known traps the SPEC must handle:
- **Win-rate inflation.** Variants a and c count a trade as a success when the *high* clears
  +2%. The test must use realized exits: the order-book TP at +2% fills only if high ≥ entry ×
  1.02, otherwise exit by the stated SL/time rule.
- **ARA lock at the close.** Top gainers (b, c) often close at ARA with no offer, so the close
  is not fillable. Apply the P4-2 fillability authority (`engine/exits/price_limits.py`) to the
  entry, not just the exits.
- **Execution model.** The repo's P3 convention fills at the *next* session's open. BSJP
  legitimately fills in the pre-closing auction at the close price. The SPEC must declare a
  close-auction fill model for this family and must not borrow the P3 default.
- **Costs.** The claimed gross is 1–2% per trade against about 0.60% round trip plus
  illiquid-name slippage. Variant d's Rp5–10B value filter is the cost-aware one.

## R2. December window dressing (IHSG)

Sources:
- `gsCM_-oq_w0`: "selama 20 tahun terakhir di bulan Desember [IHSG] itu naik sebanyak 19 kali
  atau setara dan 95%".
- `JT4-Y5KEUds`: "di bulan Desember itu kenaikannya sampai 4,56 persen". The rule as stated is
  to buy before Christmas and sell at year end.

Calendar rule, no free parameters once the window is frozen. The move (about 4%) is far above
costs.

**Evidence ceiling:** one observation per year, so about 20 independent trades. That can never
reach a high evidence tier however good it looks. The window must be frozen before looking at
IDX data, and it needs an index-tracking instrument. Good as a low-cost check, not as a core
edge.

## R3. MA20 trend following (`sbAxWgALG4M`) and "swing karyawan" (`dkID7G8Rg3c`)

`sbAxWgALG4M` is fully specified:
- Filters:
  - "SMA 20 lebih besar daripada SMA 50";
  - "open kurang dari SMA 20 and close lebih dari SMA 20";
  - 1-day change between 1% and 5%;
  - high ≤ close + 3 ticks;
  - volume > SMA20(volume);
  - value > Rp1B;
  - price > 60.
- Stop: close below the entry candle's low ("ditutup lebih rendah dari low").
- Exit: close below MA20 ("closing di bawah MA20").
- No aggregate performance claim.

`dkID7G8Rg3c`:
- Filters: market cap > Rp1T; 30-day ADV > Rp5B; "SMA20 is above SMA50"; Stoch %K crosses
  above 20 or MACD above signal.
- Target "10 15%", trailing stop.
- Its broker-summary filter is discretionary and in the failed broker-flow family. Drop it.

**An overlap check is required before Phase A.** The in-house `Swing Trend` and momentum
strategies may already cover this; the P4-2 sweep includes them. If they overlap, this adds
nothing.

---

## Ranking across both shortlists

1. **R1 BSJP overnight.** IDX-specific, untested return component, large n, data in hand.
2. **C1 RSI(2) mean reversion** (`CANDIDATES.md`). Untested family, fully specified, but the
   per-trade edge is close to costs.
3. **R2 December seasonality.** A cheap check, structurally capped evidence.
4. R3 / C2 / C3 only after an overlap or cost check.

Next step (Owner): choose R1 (recommended) or another. Phase A then writes `SPEC.md` on
`spec/external-strategy-intake`, with:

- the frozen variant family (a–e);
- the realized-exit definition;
- the close-auction fill model;
- the ARA entry-fill rule;
- the universe and cost model.

Phase B stays gated behind P1.
