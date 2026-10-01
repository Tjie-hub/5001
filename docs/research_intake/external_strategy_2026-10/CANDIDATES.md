# External strategy intake: candidate shortlist (pre-Phase A)

**Date:** 2026-10-01 · **Status:** CANDIDATES. Nothing is registered and no slot is consumed.
The Owner picks one, then Phase A (`SPEC.md`) starts.
**Sources:** five YouTube transcripts in `SOURCE/`, taken verbatim via NotebookLM (notebook
`a44129ba-c7ce-4640-88cd-7a6194693b7c`). Every performance figure below is the video's own claim,
measured on **US index ETFs / futures, before IDX costs**. Treat each one as unverified marketing.
Two of the videos come from a channel that sells strategies (Quantified Strategies).

**Overlap check (repo grep, 2026-10-01):** none of these families has been tested here.

- RSI(2), IBS, streak mean reversion: none in `engine/strategies.py`, the registries, or
  `research/`. The closest in-house ideas are `Panic Rebound` and `Crash Recovery`, which are
  event-driven dip buys. They are not oscillator mean reversion.
- Turn-of-the-month: none.
- Connors appears only as the source of NR7 (Street Smarts, `docs/audit/PHASE_8_...`).

Families already falsified or failed here, which this list avoids: breakout (NR7, ORB, Inside Bar,
TFB), microstructure and broker-flow (P-M FAIL-0001/3/9/7), reconstitution (FAIL-PA-0001), and
exhaustion patterns.

**Cost hurdle that decides most of this:** the repo's round-trip cost authority is about **0.60%**
(D-059 modeled cost, P4-6 liquidity-scaled slippage on top for illiquid names). Several claimed
edges are smaller than that per trade, even on liquid US ETFs.

---

## C1. RSI(2) mean reversion with a trend filter (Connors/Alvarez). **Recommended first**

Source quotes:

- `YT_s4xx_9L_uEY`: "we buy when the 2-day RSI crosses below 10 and we sell when the 2-day RSI
  crosses above 80 … we enter and exit at the close".
- Variant from the same video: "sell when the close is higher than yesterday's high" (the
  "QS exit").
- `YT_b4eCe9SdVBY`: "rule number one … the close to be greater than the 200 period moving
  average … rule number two … RSI … two periods … crossing below the 10 level … buy … on close
  … or on the open of the next bar … exit … RSI … cross above 70".
- Optional scale-in, up to 3 entries, on repeated crosses below 10.

Claims: SPY 1993–2026 about 9%/yr, 27% time in market. E-mini 2005–2023 about 78–79% win rate.

Why it fits IDX:

- Long-only.
- Uses only daily OHLCV, which is already in `walkforward.db`.
- A fully specified rule with few parameters.
- An untested family.

Mechanism story: short-horizon reversal/liquidity provision. Note this is close to the
P-M I5 inventory mean-reversion mechanism that failed at the intraday/flow level (FAIL-PM-0001);
the daily-bar version is a different instrument and horizon. The Phase A SPEC must state that
relationship rather than ignore it.

Risks:

- Average gain per trade on US ETFs is small (about 0.5–0.7%), versus the 0.60% IDX round
  trip. It survives only if single-name IDX dips revert more strongly than US ETFs do.
- The universe choice (LQ45/IDX80) matters for both costs and ARB-lock fills (P4-2).

## C2. Turn-of-the-month (TOM)

Source quotes:

- `YT_rlSkRMmycWo`: "buy on the fifth [last] trading day of the month and sells on the third
  trading day of the new month".
- `YT_iZaAf9NJqN8`: several window definitions (last 1–5 days to first 1–10 days). The video
  quotes S&P average 0.2–0.6% per window, with drawdowns of 10% or more in some windows.

Why it fits IDX:

- A calendar rule with essentially zero free parameters once the window is frozen in advance.
- Applies to IHSG/LQ45.
- Whether Indonesian TOM literature exists has not been checked. Phase A should look for it
  before setting a prior.

Risks:

- The quoted edge per window (0.2–0.6%) is at or below the 0.60% round-trip cost.
- It needs a cheap index instrument. IDX ETFs are thin, and a stock basket pays full costs on
  every name.
- The video shows several windows. Picking one after seeing results is data snooping; the window
  must be frozen before any IDX data is looked at.

## C3. Down-streak reversal (N red candles, then buy)

Source: `YT_1KXEcQQKhcw` (USDJPY FX): "I wait for three red candles in a row … enter a trade at
the open of the next candle … I don't use a stop-loss … hold for three candles". The author
admits "picking this specific equity curve could be overfitting".

This is the same family as C1, with a different trigger. Test it only as a pre-declared
variant inside C1's multiplicity family, not as a separate edge.

## Not usable

- **Russell rebalancing (June):** US-index-specific. The IDX analogue, reconstitution, already
  FAILED (FAIL-PA-0001).
- **Meb Faber SPY/GLD/TLT 3/10-month rotation:** a multi-asset ETF allocation, not an IDX stock
  strategy. The video itself says it has underperformed since publication in 2015.
- **MFI(10-day time stop), weekly RSI on XLP, "rubber band":** the video gives no complete
  rules. The rubber band rules are "a bit more complex" and never stated.
- **Volatility strategy and TLT seasonal:** rules withheld ("premium strategy").
- **RSI momentum (100-day lookback, 14-day RSI):** the regime rule is not stated verbatim, and
  the video says it underperforms its own mean-reversion strategies.

---

## Next step (Owner)

1. Pick a candidate. The recommendation is **C1** (with C3 as a pre-declared variant).
2. Phase A: write `SPEC.md` on `spec/external-strategy-intake`. It includes:
   - named rules quoted from `SOURCE/`;
   - parameter ambiguities as open questions: RSI exit level 70 or 80, or the QS exit;
     close-entry or next-open entry (the repo's P3 execution model fills at the next session's
     open, so the close-entry claims do not transfer);
   - the universe;
   - the cost model.
3. Phase B (backtest and gatekeeper) stays gated behind P1, the research fence cutover.
