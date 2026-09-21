# Wyckoff Cycle Phases — STRONG-12 Tradeable Universe

> Generated 2026-06-25. Companion to `cluster.md`, but built on **cycle detection**
> (Wyckoff 4-phase) instead of buy-and-hold. Every label is **point-in-time / causal**
> — no look-ahead, no endpoint conditioning (the two flaws that sank `cluster.md`).
>
> Tickers: BRPT, TPIA, ANTM, ARCI, DSSA, BULL, ENRG, DEWA, MSIN, RAJA, SCMA, CDIA
> Detector: `scratchpad/wyckoff.py` (deterministic rule state-machine on daily price+volume).

---

## 0. TL;DR — read this first

1. **The cycle detector is reliable as a regime MAP and as a "don't buy now" filter.**
   Right now **11 of 12 names are in MARKDOWN, 1 (RAJA) in ACCUMULATION, 0 buy-scans firing.**
   That is the actionable output and it agrees with `cluster.md` and the TFB context work:
   *this is a risk-off / post-distribution market — stand aside.*

2. **The cycle-based BUY TIMING does NOT beat random entry in this universe.** This is a
   negative result and it is the honest headline. See §3. The "buying cluster"
   (accumulation→markup reclaim) won on a few moonshots but lost on win-rate and median
   to a random-entry baseline. Same lesson as `cluster.md`: in a survivor-heavy bull
   universe, *random entry ≈ buy-and-hold a winner*, so a price-only timing rule has
   nothing to beat.

3. **What's missing is confirmation, not a better price rule.** The accumulation signature
   (calm base + MA50 reclaim + volume pop) is *necessary but not sufficient* — winners and
   failed breakouts look identical on price. The discriminator is the **order-flow data this
   repo has** (composite_score). **Flow-gate tested (§8):** it cannot be backtested (daily flow
   only exists from ~2026-04), but on the only 2 historical signals it *could* see — both 2026
   false breakouts — flow correctly **blocked both**, and live it removes RAJA (price-only's
   lone watch) because RAJA's "base" shows distributive smart-money flow. Promising, but
   validate-forward only.

---

## 1. Method (point-in-time Wyckoff classifier)

Per ticker, daily bars, using **trailing windows only**:

| Phase | Signature (all causal) |
|---|---|
| **MARKDOWN** | close < MA50, MA50 slope < −0.3%/10d, price in lower part of 60-bar range |
| **ACCUMULATION** ← buy zone | price basing low (range pos < 0.5), MA50 flat (\|slope\|≤0.5%), ATR% **below** trailing-120 median (volatility dry-up) |
| **MARKUP** | close > MA50, MA50 slope > +0.3%, price in upper range |
| **DISTRIBUTION** | price near highs (pos > 0.55) but MA50 flattening/rolling over, ATR re-expanding |

Labels are smoothed (5-bar mode filter) into contiguous segments.

**Buying-cluster scan** (accumulation→markup transition) fires when **all** hold at bar *i*:
- fresh **MA50 reclaim** (crossed above within last 3 bars),
- prior 20 bars were majority **accumulation/markdown** (a real base, not mid-trend),
- **calm base**: median ATR% over the base < trailing median,
- **higher-low** in place (recent 10-bar low ≥ prior base low),
- **volume expansion** > 1.3× on the reclaim bar.

---

## 2. Cycle map — what these stocks actually did (2024-04 → 2026-06)

The dominant phase across the board is **MARKUP**. That is partly real and partly
**survivorship**: these 12 were *selected* in `cluster.md` as structural winners, so by
construction most of their history is uptrend. Clean **accumulation bases are rare** — only
~23 qualified buy-clusters across all 12 tickers in two years.

Representative cycle skeletons (segments ≥8 bars; full output in `scratchpad/wyckoff.py`):

```
BRPT : MARK(2024-08..2025-01) → DIST(Jan'25) → MARK(2025-02..2026-04) → DIST(Apr-May'26) → MARKDOWN(now)
ANTM : long MARK 2025-02..2025-08 (106 bars) → choppy MARK → ACCU(Apr'26) → MARK → MARKDOWN(now)
ENRG : MARK → ACCU(Sep'24, 21 bars) → MARK 2025-05..2026-01 (171 bars) → MARKDOWN(now)
DEWA : MARK 2025-05..2026-01 (180 bars) → failed reclaims 2026-04..05 → MARKDOWN(now)
RAJA : MARK 2024-09..2026-04 (mostly) → ACCU(Apr-May'26) → brief MARK → ACCUMULATION(now)
```

**Pattern that repeats:** a long markup (100–180 bars) → a short distribution top →
markdown. The 2026-Q2 top is visible across nearly every name — they topped together
(index-driven), which is exactly why a single-name timing edge is hard here.

---

## 3. Does the buying-cluster pay? (the negative result)

Forward returns from every buy-cluster signal, pooled across all 12, vs a **random-entry
baseline** (same universe, 3× as many random bars, seed-fixed):

| Horizon | Buy-cluster | | | | Random entry | | |
|---|---|---|---|---|---|---|---|
| | n | mean | median | win% | mean | median | win% |
| 20d  | 23 | +6.93% | +2.36% | **52%** | +4.03% | +4.55% | **58%** |
| 60d  | 23 | +19.24% | +7.27% | **52%** | +17.04% | +6.61% | **60%** |
| 120d | 23 | +23.26% | +2.90% | 61% | **+35.65%** | **+7.88%** | 55% |

**Read:** the buy-cluster has a *higher mean* at 20/60d but a **lower median and lower
win-rate than random**, and at 120d random beats it outright on both mean and median. The
positive mean is carried entirely by a handful of moonshots:

```
MSIN 2024-08-05  +147.7% (20d)     SCMA 2025-07-17  +148.0% (60d)
ARCI 2025-01-31  +179.1% (120d)    ANTM 2025-02-14  +103.3% (60d)
```

…while an equal number failed, mostly the **2026 turns** that front-ran the top:

```
DEWA 2026-04-14  −43.8%    DEWA 2026-05-06  −37.9%
TPIA 2025-11-27  −73.7%    BULL 2026-04-16  −26.2%    RAJA 2026-05-13  −10.7%
```

**Conclusion:** as a *standalone price-only timing edge, the buying-cluster does not beat
random entry in this universe.* Same outcome as `cluster.md`'s "first cluster" claim once
you measure it honestly. n=23 is small, but the direction (below-random win-rate) is clear.

---

## 4. The accumulation signature (descriptive, not predictive)

What the bases that preceded big markups had in common:

| Feature | Typical value |
|---|---|
| Base ATR% / trailing median | **0.70 – 1.00** (calm — volatility dry-up confirmed) |
| Base length before reclaim | ~10–25 bars |
| Trigger | MA50 reclaim with volume > 1.3× |
| Structure | higher-low vs prior base low |

**Caveat:** winners (MSIN +147, SCMA +148) and failures (DEWA −44, BULL −26) share this
**same** signature. Calm base + volume reclaim is *necessary but not sufficient*. Price
alone cannot tell a true accumulation from a bull-trap reclaim into a topping tape.

---

## 5. Current phase — today (2026-06-25)

| Ticker | Phase | Buy-scan |
|---|---|---|
| BRPT | MARKDOWN | — |
| TPIA | MARKDOWN | — |
| ANTM | MARKDOWN | — |
| ARCI | MARKDOWN | — |
| DSSA | MARKDOWN | — |
| BULL | MARKDOWN | — |
| ENRG | MARKDOWN | — |
| DEWA | MARKDOWN | — |
| MSIN | MARKDOWN | — |
| **RAJA** | **ACCUMULATION** | — (watch for MA50 reclaim + volume) |
| SCMA | MARKDOWN | — |
| CDIA | MARKDOWN | — |

**Verdict: 11/12 in markdown, 1 in accumulation, nothing firing.** The single name worth a
watch is **RAJA** — it is the only one that has stopped making lower-lows and is basing. A
volume-backed MA50 reclaim there would be the first buy-cluster of the next cycle. Everything
else is still in markdown and should be left alone.

---

## 6. Limitations & honest next step

1. **Survivorship.** The 12 were pre-selected as winners, so the universe is markup-heavy and
   the random baseline is unusually strong. The buy-scan has little to beat.
2. **Markup-biased classifier.** The rule set leans toward MARKUP on ambiguous bars; treat
   short MARK segments inside chop as "trending-ish," not high-conviction.
3. **Small n.** 23 signals over 2 years. Directionally informative, not statistically tight.
4. **The real gap is confirmation.** The price-only cycle map is good for *where are we*
   (regime/defense) but not for *should I buy this base*. The repo's **order-flow layer**
   (composite_score, CVD/delta from `stockbit_flow`) is the natural discriminator: true
   Wyckoff accumulation shows **rising cumulative delta while price is flat/basing**; a
   bull-trap reclaim does not. **Recommended next step:** gate the buy-cluster on positive
   flow-delta during the base and re-measure vs random — this is the same flow-confirmation
   thesis that the merged liquidity-sweep work is built on.

---

## 8. Flow-gate test (the discriminator experiment)

**Hypothesis:** gate the buy-cluster on **positive composite_score during the base** — true
Wyckoff accumulation has smart money buying while price bases; a bull-trap reclaim does not.

**Hard data limit:** the daily flow table (`stockbit_flow.composite_score`) only covers
**~2026-04-22 → present (34–46 days)**. There is **no flow before April 2026**, so a
historical edge backtest is **impossible** — only 2 of 23 buy-clusters have any base-flow.

### What the 2 testable cases show

Both in-window signals were the **2026 false breakouts**, and flow would have vetoed both:

| Signal | Base flow (Σcs, 15d) | Flow gate | Actual fwd60 | Verdict |
|---|---|---|---|---|
| DEWA 2026-05-06 | −15 | **BLOCK** | −37.9% | flow **correct** |
| RAJA 2026-05-13 | −38 | **BLOCK** | −10.7% | flow **correct** |

So the two price-only reclaims that *looked* fine but lost both had **distributive flow
underneath** — exactly the trap flow-confirmation is meant to catch. **Caveat:** n=2, both
losers; there is no in-window *winner* to confirm the gate doesn't also block good trades.

### Live gate — today (2026-06-25)

Combined `price-phase == ACCUMULATION` **AND** `Σcomposite_score(15d) > 0`:

- Price-only watch: **RAJA** (only accumulation phase).
- RAJA flow: **Σcs = −26, last verdict BEARISH, smart_money mostly STRONG_SELL.** → **BLOCKED.**
- Only name with mildly positive flow is ANTM (Σcs +8) but its price phase is MARKDOWN → fails.
- **Combined gate: 0 buyable names** — higher conviction than price alone. RAJA's "base" is
  churn/distribution, not accumulation.

### Conclusion

The flow gate is **mechanistically sound and live-actionable** (it correctly downgrades the
one price-only candidate and vetoed the two historical traps), but it is **not statistically
validated** and **cannot be backtested** with current data. The only path is **forward /
shadow validation** from here — the same discipline applied to the merged liquidity-sweep
strategy (kept shadow until it earns WF scores). Recommended: log the price+flow gate in
shadow and accumulate out-of-sample signals before trading it.

---

## 7. Reproduce

```bash
PYTHONPATH="$PWD" venv/bin/python scratchpad/wyckoff.py        # phases + buy-scan + edge vs random
PYTHONPATH="$PWD" venv/bin/python scratchpad/wyckoff_flow.py   # flow-gate coverage + live gate
```
Detector + buy-scan + random baseline + current-phase snapshot + flow gate, all causal.
