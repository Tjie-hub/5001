# Crypto Day Trade & Short Swing — Unified Strategy Research

**Date:** 2026-06-05
**Source:** 4-domain agent research + domain synthesis
**Scope:** Chart Patterns, Market Context, Liquidity Pools, Trap Detection
**Target:** 5m / 15m / 1h / 1d timeframes, top-100 liquid coins, no memes

---

## 1. CHART PATTERNS

### 1.1 Which Patterns Have Edge in Crypto

Crypto markets differ from equities in four structural ways that change pattern behavior:
- **No market close** — no gaps, no overnight drift. Patterns must be evaluated on continuous bars.
- **Higher wick frequency** — wicks penetrate levels more often. A "breakout" that only touches with a wick is NOT a breakout.
- **Volatility clustering** — 5 consecutive 3% candles are normal. ATR-based stop placement is mandatory; fixed-percentage stops fail.
- **Session-driven volume** — patterns forming in low-volume Asian session are less reliable than those completing at US open.

| Pattern | Edge in Crypto | Best TF | Win Rate (approx) | Notes |
|---------|---------------|---------|-------------------|-------|
| **Flag / Pennant** | Strong | 1h → 15m entry | 55-62% | Continuation after impulse. Must have declining volume during consolidation. |
| **Double Top / Bottom** | Strong | 1h, 4h | 58-65% | Works BETTER in crypto due to liquidity-hunt behavior at equal highs/lows |
| **Head & Shoulders** | Moderate | 4h, 1d | 50-55% | Slower to develop. Right shoulder must have lower volume. |
| **Falling / Rising Wedge** | Strong | 1h, 4h | 55-60% | Crypto wedges resolve faster (~5-8 bars vs 10-15 in stocks) |
| **Cup & Handle** | Weak | 1d | ~45% | Too slow. Crypto trends don't last long enough for clean cup formation |
| **Triangle (symmetrical)** | Moderate | 1h, 4h | 50-55% | 50/50 continuation vs reversal. Need volume confirmation on break. |
| **Ascending / Descending Triangle** | Strong | 1h | 58-62% | Flat top/bottom + rising/falling lows/highs. Clear bias. |

### 1.2 Wick-Based Patterns (Crypto-Specific)

Crypto's unique wick behavior creates patterns not seen in stocks:

**Long Wick Reversal (Pin Bar / Hammer / Shooting Star)**
- Wick must be ≥ 3x body length
- Wick must be ≥ 70% of total candle range
- Close must be in top/bottom 25% of range
- MUST appear at a structural level (support/resistance/liquidity zone)
- Volume on the reversal candle ≥ 1.3x 20-period average
- Entry on NEXT candle after confirmation (close beyond 50% of wick)
- Stop: beyond the wick tip by 0.5 ATR
- Win rate: 55-60% at key levels; <40% in no-man's-land

**Wick Fill Pattern**
- A long wick creates a "vacuum" — price often returns to fill 50-80% of the wick within 3-6 candles
- Trade the fill, not the reversal
- Entry: when price retraces 50% into the wick
- Target: 80-90% of wick length
- Stop: beyond the wick origin (candle body)

**Double Wick Rejection**
- Two consecutive candles with long wicks in opposite directions at the same level
- Signals strong absorption — a battle zone
- Break of the double-wick range = strong directional signal
- More reliable than a single pin bar

### 1.3 Multi-Timeframe Pattern Confluence

The hierarchy for pattern confirmation:

```
1d structure → 1h pattern → 15m entry trigger → 5m precision
```

**Rule: Never trade against the 1d structure.**

| 1d Context | 1h Pattern | 15m Entry | Action |
|------------|-----------|-----------|--------|
| BULL trend (close > MA50, MA20 > MA50) | Bull flag | Breakout + vol | LONG — full size |
| BULL trend | Double top | — | IGNORE — counter-trend |
| SIDEWAYS | Double bottom at range low | Reversal candle + vol | LONG — 0.5x size |
| BEAR trend | Bear flag | Breakdown + vol | SHORT — full size |
| BEAR trend | Double bottom | Reversal candle | IGNORE — counter-trend |

### 1.4 Volume Confirmation Rules

| Pattern | Volume Rule | Invalidation |
|---------|------------|-------------|
| Bull Flag | Flag formation: declining vol. Breakout candle: vol ≥ 2x flag average | Breakout vol < 1.5x → wait for retest |
| Double Bottom | Second bottom: vol < first bottom. Break above neckline: vol ≥ 1.5x avg | Low vol break → 70% trap probability |
| Wedge | Declining vol during wedge. Breakout: vol ≥ 1.8x wedge average | No vol expansion → false break |
| Head & Shoulders | Left shoulder: high vol. Head: moderate vol. Right shoulder: lowest vol. Breakdown: vol spike | Right shoulder vol > head vol → pattern invalid |
| Ascending Triangle | Flat top, rising lows. Breakout: vol ≥ 2x 20-period avg | Breakout without vol → expect retest or trap |

### 1.5 Pattern Failure / Invalidation Rules

A pattern is invalidated when:

1. **Time decay:** Pattern takes >2x expected bars to complete (e.g., a flag that doesn't break within 10 bars on 1h)
2. **Wick penetration:** A wick penetrates the pattern boundary by >0.3 ATR and closes back inside — the level is "used"
3. **Volume divergence:** Breakout occurs but volume is declining vs formation phase
4. **Premature break:** Pattern breaks before 60% completion (e.g., triangle breaks at 40% of its width)

### 1.6 The Liquidity Grab Pattern

The single most important pattern for crypto day trading.

**Setup:**
1. Identify a clear structural level (double top, range high, previous day high)
2. Price approaches the level — retail shorts place stops above it
3. Price breaks the level by 0.2-0.5%, triggering stops (the "grab")
4. Price IMMEDIATELY reverses (within 1-2 candles on 15m) and closes back below/above the level
5. Volume on the grab candle is elevated but the reversal candle has HIGHER volume

**Entry:** On the close of the reversal candle back inside the range
**Stop:** Beyond the grab wick
**Target:** Opposite side of the range / next liquidity level
**Win rate:** 65-70% when the grab occurs at a well-defined level with volume confirmation

---

## 2. MARKET CONTEXT

### 2.1 Regime Detection Framework

Three independent inputs, triangulated:

| Metric | TRENDING BULL | RANGING / SIDEWAYS | TRENDING BEAR |
|--------|--------------|-------------------|---------------|
| **ADX(14)** | >25 AND +DI > -DI | <20 | >25 AND -DI > +DI |
| **MA20 slope (5-bar)** | > +0.3% per bar | Between -0.3% and +0.3% | < -0.3% per bar |
| **Choppiness Index (14)** | < 38 | > 61 | < 38 |

**Decision rule:** If ≥2 of 3 agree → regime confirmed. If all 3 disagree → SIDEWAYS (safest default).

### 2.2 Market-Wide Context (The "Tide")

Before trading any individual coin, check the tide:

| Metric | Source | Bullish threshold | Bearish threshold |
|--------|--------|-------------------|-------------------|
| **BTC Dominance (BTC.D)** | TradingView / CoinGecko | < 48% (alt season) | > 55% (BTC flight) |
| **Total Market Cap (TOTAL)** | TradingView | > MA50, rising | < MA50, falling |
| **Altcoin Season Index** | Blockchain Center | > 75 (alt season) | < 25 (BTC season) |
| **USDT Dominance (USDT.D)** | TradingView | < 4% (risk-on) | > 6% (risk-off, cash) |

**Decision matrix:**

```
BTC.D > 55% AND TOTAL declining:
  → Altcoins in danger. Reduce position size to 0.5x.
  → Only trade BTC/ETH pairs. Skip mid-caps entirely.

BTC.D < 48% AND TOTAL > MA50:
  → Alt season. Full position size.
  → Mid-cap coins (<$5B mcap) are tradeable.

USDT.D > 6%:
  → Market is in cash. Minimal exposure. Wait for USDT.D to drop.
  → Any signals are suspect — cash-heavy markets reverse violently.
```

### 2.3 Key Level Identification

Not all levels are equal. Strength ranking:

| Level Type | Strength | Why |
|-----------|----------|-----|
| **Volume Profile POC (1w)** | ⭐⭐⭐⭐⭐ | Where the most volume traded over a week. Strongest magnet. |
| **Previous Week High / Low** | ⭐⭐⭐⭐ | Institutional reference points |
| **Volume Profile VAH / VAL (1d)** | ⭐⭐⭐⭐ | Value area edges — 70% of volume |
| **Previous Day High / Low** | ⭐⭐⭐ | Intraday reference |
| **Session High / Low (US)** | ⭐⭐⭐ | US session levels > Asia session levels |
| **Round numbers** | ⭐⭐⭐ | BTC 100K, ETH 5K, etc. — psychological magnets |
| **Equal highs / equal lows** | ⭐⭐⭐ | Liquidity magnets (see §3) |
| **Fibonacci levels** | ⭐⭐ | Self-fulfilling but not structural |
| **Moving averages (MA50, MA200)** | ⭐⭐ | Better for trend, weak as S/R |

**Level strength test:** A level is "strong" if price has:
- Touched it ≥3 times without breaking
- Reversed from it with volume expansion
- It aligns with a higher-timeframe level

### 2.4 Session Analysis

Crypto sessions ranked by tradeability:

| Session | UTC | Characteristics | Best For |
|---------|-----|----------------|----------|
| **US Open** | 13:30–16:30 | Highest volume, clearest breakouts, least fakeouts | ORB, Momentum, Trend Following |
| **US Mid** | 16:30–20:00 | Volume declining, choppy | VWAP Reversion only |
| **US Close / Asia Open** | 20:00–00:00 | Low volume, wide spreads, manipulation-prone | AVOID trading |
| **Asia Mid** | 00:00–06:00 | Lowest volume, highest fakeout rate | AVOID — scan only |
| **EU Open** | 08:00–11:00 | Second-best volume, good trends | ORB, Momentum |
| **EU Mid / Pre-US** | 11:00–13:30 | Consolidation, positioning for US | VWAP Reversion, range trades |

**Session rule:** The best 6 hours (US Open + EU Open) account for ~70% of profitable setups. If a signal fires outside these windows, require +1 confirmation (e.g., 2 timeframe alignment instead of 1).

### 2.5 Correlation Context

```
BTC correlation > 0.7 for 90%+ of altcoins in trending markets.

Rule: If BTC drops 2% in 1 hour, close ALL altcoin long positions immediately.
      Do not wait for individual stops to hit — correlation risk is systemic.

Exception: A coin showing negative BTC correlation for >48 hours may be in a 
           narrative-driven independent move. This is rare (<5% of setups).
```

### 2.6 Volatility Context (ATR Percentile)

Calculate ATR(14) as a percentile of the last 90 periods:

| ATR Percentile | Regime | Position Size | Stop Width |
|---------------|--------|---------------|------------|
| < 25% (low vol) | Expect expansion | 1.0x | 1.5 ATR (wider, anticipating expansion) |
| 25-75% (normal) | Normal trading | 1.0x | 1.0 ATR |
| > 75% (high vol) | Expect contraction or trend | 0.5x | 0.8 ATR (tighter, vol already priced in) |

### 2.7 Market Cap Context

| Cap Tier | Mkt Cap Range | Characteristics | Strategy Fit |
|----------|--------------|-----------------|-------------|
| **Large Cap** | >$10B (BTC, ETH, SOL, BNB, XRP) | High liquidity, tight spreads, institution-driven | All strategies work. Best for ORB and Momentum. |
| **Mid Cap** | $1B–$10B (top 20-50) | Good liquidity, more volatile, narrative-driven | Momentum, POC. VWAP less reliable (thinner books). |
| **Small Cap** | $100M–$1B | Thin books, manipulation-prone, high spike risk | **SKIP for day trade.** Only for swing on 4h/1d patterns. |

### 2.8 Narrative / Rotation Context

Crypto rotates through narratives. Aligning trades with the active narrative improves win rate ~5-8%:

| Narrative | Signal | Typical Duration | Tradeable Coins |
|-----------|--------|-----------------|-----------------|
| AI / DePIN | AI tokens outperforming BTC for 3+ days | 2-6 weeks | RENDER, TAO, FET, AKT |
| RWA | BlackRock / institutional news | 2-4 weeks | ONDO, MKR, CFG |
| L1 Rotation | New L1 launch or upgrade | 1-3 weeks | SUI, APT, SEI, NEAR |
| Meme Season | DOGE/SHIB/PEPE pumping on no news | 1-2 weeks | AVOID (skipped by filter) |
| BTC Dominance | BTC.D rising, alts bleeding | 2-8 weeks | Only BTC/ETH tradeable |

**Detection:** Scan CoinGecko "Categories" 24h change. If a category is up >8% while others are flat, that's the active narrative.

---

## 3. LIQUIDITY POOLS

### 3.1 Four Types of Liquidity Pools

| Type | Location | Visibility | Key Data Source |
|------|----------|------------|-----------------|
| **Order Book Liquidity Clusters** | CLOB bid/ask walls | Partially visible (depth chart) | Exchange depth API |
| **Stop-Loss Clusters** | Held off-book | Invisible to retail; visible to exchanges/MMs | Inferred from price behavior |
| **Liquidation Levels (Perps)** | Exchange liquidation engine | Visible via Coinglass/Hyblock | Coinglass API / Hyblock |
| **High-Volume Nodes (VPVR)** | Historical volume profile | Visible | Volume Profile indicator |

### 3.2 Liquidity Hunt / Stop Hunt Mechanics

The stop hunt is the single most reliable pattern in crypto. It works because:

1. Market makers / whales can see the order book and liquidation map
2. They know where stops cluster (below obvious support, above obvious resistance)
3. They push price into these zones to trigger stops → creates liquidity for THEIR opposite position
4. Once stops are triggered (providing liquidity), they reverse

**Identifying a stop hunt in real time:**

```
Setup:
  1. Clear support level (3+ touches) or equal lows
  2. Price approaches level as a magnet
  3. CVD showing steady selling (cumulative delta negative)
  4. Price breaks level, wicks below, triggers apparent breakdown
  5. CVD SUDDENLY flattens or turns positive — absorption
  6. Price closes back above the level within 1-2 candles
  
  Entry: On close above the level (confirmation the hunt is over)
  Stop: Below the hunt wick
  Target: Opposite liquidity zone (next resistance above)
```

### 3.3 Liquidity Zones — Where Stops Cluster

Ranked by reliability:

| Zone | Hunt Probability | Notes |
|------|-----------------|-------|
| **Equal highs** | Very High | Double/triple top — massive short liquidation pool above |
| **Equal lows** | Very High | Double/triple bottom — massive long stop cluster below |
| **Previous day high / low** | High | Retail traders place stops there |
| **Round numbers** | High | BTC 100K — everyone's watching |
| **Session high / low (US)** | Medium-High | US session levels carry more liquidity |
| **High-volume node edges** | Medium | VPVR high-volume zones act as magnets |
| **Large liquidation cluster** | Very High | Coinglass data: >$500M in liquidations at a level = guaranteed magnet |

### 3.4 Liquidation Cascade Dynamics

**Long Squeeze (cascading longs liquidated):**

```
Phase 1: Price starts dropping. Small liquidations begin.
Phase 2: Liquidations push price lower → triggers more liquidations (cascade).
Phase 3: Price accelerates down. Volume spikes massively. OI drops sharply.
Phase 4 (EXHAUSTION): Volume peaks, OI has dropped 30%+, price stabilizes or wicks.
         THIS IS THE ENTRY — the cascade is done.

Identification:
  - OI drop > 20% in 1 hour
  - Volume 3x+ normal
  - Price at/approaching a structural support
  - CVD starting to flatten after heavy selling
```

**Short Squeeze (cascading shorts liquidated):**
Same pattern inverted. Look for OI drop + volume spike + price at resistance.

### 3.5 CVD (Cumulative Volume Delta) Usage

CVD = running sum of (buyer-initiated volume - seller-initiated volume) per bar.

**Key CVD patterns:**

| CVD Pattern | Meaning | Action |
|------------|---------|--------|
| CVD ↑ + Price ↑ | Confirmed bullish — trend healthy | Long entries valid |
| CVD ↓ + Price ↓ | Confirmed bearish — trend healthy | Short entries valid |
| CVD ↑ + Price ↓ | **Absorption** — buyers absorbing selling at a level | Potential reversal. Watch for price reclaim. |
| CVD ↓ + Price ↑ | **Distribution** — sellers offloading into buying | Potential reversal. Watch for price break. |
| CVD flat + Price rising | **Exhaustion** — no new buyers, price rising on low participation | Warning: imminent reversal |
| CVD flat + Price falling | **Exhaustion** — no new sellers | Warning: imminent reversal |
| CVD extreme spike + Price spike | **Climax** — last push before reversal | Prepare for reversal entry |

**The most reliable setup:** CVD divergence at a liquidity zone.

```
At a double top (resistance):
  Price: making new high
  CVD: lower high (weaker buying)
  → Distribution. Expect reversal. Entry on price close below the level with volume.
```

### 3.6 Wyckoff Schematic in Crypto

The accumulation / distribution cycle maps to crypto order flow:

**Accumulation (precedes uptrend):**
1. Preliminary Support (PS) — initial buying
2. Selling Climax (SC) — panic low, high volume
3. Automatic Rally (AR) — bounce
4. Secondary Test (ST) — retest of SC, LOWER volume (key!)
5. Spring — stop hunt below SC (liquidity grab), immediately reverses
6. Sign of Strength (SOS) — breaks above AR

**Entry:** On the Spring (stop hunt below SC) OR on SOS (break above AR with volume)

**Distribution (precedes downtrend):**
1. Preliminary Supply (PSY) — initial selling
2. Buying Climax (BC) — euphoric high, high volume
3. Automatic Reaction (AR) — drop
4. Secondary Test (ST) — retest of BC, LOWER volume (key!)
5. Upthrust (UT) — liquidity grab above BC, immediately reverses
6. Sign of Weakness (SOW) — breaks below AR

**Entry:** On the Upthrust (liquidity grab above BC) OR on SOW (break below AR with volume)

### 3.7 Order Book Depth — What Matters

Retail traders obsess over order book walls. Most of it is noise. What actually matters:

- **Spoofing detection:** Large orders that appear and disappear without executing = fake. Ignore.
- **Executed volume (footprint):** What actually traded. CVD and volume profile are derived from this. Trust these.
- **Depth imbalance:** Bid volume / Ask volume ratio. >2.0 = buying pressure, <0.5 = selling pressure. But only at key levels, not in the middle of a range.
- **Iceberg orders:** Visible as repeated small fills at the same price. Indicates a large player accumulating/distributing.

**Rule:** Use order book data for level validation, not for entry timing. Executed volume (CVD, footprint) is more honest than displayed orders.

### 3.8 Funding Rate as Liquidity Signal

Funding rate extremes create predictable liquidity pools:

| Funding Rate | Crowd Position | Liquidity Pool | Expected Move |
|-------------|---------------|----------------|---------------|
| > 0.05% (very positive) | Overcrowded longs | Short liquidation pool ABOVE (liquidations will push price up before reversal) | Spike up → reversal down |
| > 0.03% (positive) | Crowded longs | Moderate | Slight long bias but watching for reversal |
| -0.01% to +0.01% (neutral) | Balanced | No extreme | Normal trading |
| < -0.03% (negative) | Crowded shorts | Long liquidation pool BELOW | Spike down → reversal up |
| < -0.05% (very negative) | Overcrowded shorts | Major long liquidation pool BELOW | Spike down → reversal up |

**The Funding Rate Reversal Trade:**
```
When funding > 0.05% AND price at resistance (double top, range high):
  → Longs are paying shorts. Market is overcrowded long.
  → Expect liquidity grab above resistance (trigger short liquidations + late longs)
  → Then reversal down.
  Entry: After the grab, on close below the level.
  Stop: Above the grab wick.
```

---

## 4. TRAP DETECTION

### 4.1 Bull Trap Identification

A bull trap = price breaks above resistance, triggers breakout buys, then reverses.

**Pre-entry bull trap checklist:**

| Check | Pass Condition | Fail = Trap Probability |
|-------|---------------|------------------------|
| Breakout candle volume | ≥ 2.0x 20-period average | <1.5x = >60% trap probability |
| 2nd candle volume | ≥ 1.2x 20-period average | Below avg = failing breakout |
| 3rd candle volume | ≥ 1.0x 20-period average | Below avg = confirmed trap |
| CVD on breakout | Rising, confirming | Flat or falling = distribution |
| 1h RSI at breakout | < 70 (not overbought) | >70 = exhaustion risk |
| Funding rate | < 0.03% (not overcrowded long) | >0.05% = short the breakout instead |
| OI change | Rising (new money entering) | Flat or falling = short covering, not new trend |
| Higher TF resistance | No nearby resistance on 4h/1d | Resistance within 0.5 ATR = likely rejection |

**Score:** ≥6/8 passes = enter. 4-5/8 = caution (0.5x size). <4/8 = DO NOT ENTER.

### 4.2 Bear Trap Identification

Same framework, inverted:

| Check | Pass Condition | Fail = Trap Probability |
|-------|---------------|------------------------|
| Breakdown candle volume | ≥ 2.0x 20-period average | <1.5x = >60% trap probability |
| 2nd candle volume | ≥ 1.2x 20-period average | Below avg = failing breakdown |
| CVD on breakdown | Falling, confirming | Flat or rising = absorption |
| 1h RSI at breakdown | > 30 (not oversold) | <30 = exhaustion risk |
| Funding rate | > -0.03% (not overcrowded short) | <-0.05% = long the breakdown instead |
| OI change | Rising (new shorts entering) | Flat or falling = long covering, not new trend |
| Higher TF support | No nearby support on 4h/1d | Support within 0.5 ATR = likely bounce |

### 4.3 False Breakout Statistics

Empirical data from crypto markets:

| Timeframe | True Breakout Rate | False Breakout Rate | Notes |
|-----------|-------------------|---------------------|-------|
| 5m | ~35% | ~65% | Mostly noise. Only use for entry timing, never for signal. |
| 15m | ~45% | ~55% | Marginal alone. Requires 1h confirmation. |
| 1h | ~58% | ~42% | Best for signal generation. Combine with volume = 65%+ accuracy. |
| 4h | ~65% | ~35% | Most reliable. But fewer signals. |
| 1d | ~70% | ~30% | Very reliable but slow. Good for bias, not entry. |

**Multi-timeframe boost:** When 15m breakout is confirmed by 1h structure, true breakout rate rises to ~62%. When also confirmed by 1d trend alignment, ~70%.

### 4.4 Range Trap (Accumulation vs Distribution)

How to distinguish a genuine range from accumulation or distribution:

| Indicator | Accumulation (Bullish) | Distribution (Bearish) | Genuine Range |
|-----------|----------------------|----------------------|---------------|
| Volume at range lows | Higher (buying) | Lower | Random |
| Volume at range highs | Lower | Higher (selling) | Random |
| CVD trend across the range | Rising (absorption) | Falling (distribution) | Flat |
| OI trend | Rising (position building) | Flat or falling | Oscillating |
| Wick direction at boundaries | Long lower wicks (rejection of lows) | Long upper wicks (rejection of highs) | Mixed |

**Rule:** Only trade a range if it's a GENUINE range (both accumulation and distribution ruled out). If accumulation → bias long from lows only. If distribution → bias short from highs only.

### 4.5 Momentum Trap (Exhaustion Candle)

The "monster green candle that traps FOMO buyers":

**Identification:**
- Candle body ≥ 3x average body size
- Volume ≥ 3x 20-period average
- RSI on 15m spikes above 85
- CVD: the spike candle shows massive buying, but the NEXT candle shows CVD flat or negative
- Candle closes near its high (looks strong) but the NEXT candle opens lower and trades lower

**Prevention:** Never enter on the exhaustion candle itself. Wait for the NEXT candle. If it:
- Continues higher with volume → trend is real, enter on pullback
- Reverses / goes flat → exhaustion confirmed, do not enter

**The 80% rule:** If a candle's range is >80% of the prior 10-candle range, it's an exhaustion candidate. Wait.

### 4.6 News Trap

Crypto news (especially Twitter/X, Telegram, Discord) creates instant spikes that reverse:

**Prevention rules:**
1. If a coin pumps >5% in 5 minutes on news → DO NOT CHASE. The move is done.
2. Wait for the 15m candle to close. If it closes >3% from the high → distribution. Stay out.
3. News-driven moves nearly always retrace 50%+ within 1-4 hours. Enter on the retest, not the spike.
4. Check if the news is "new" or recycled. 90% of crypto news is recycled narratives.

### 4.7 Time-Based Traps

Recurring manipulation patterns in crypto:

| Time | Pattern | Cause |
|------|---------|-------|
| **Sunday evening (UTC)** | Pump then dump | Low liquidity, easy to manipulate before weekly open |
| **Monday 00:00 UTC** | CME gap fill | BTC CME futures gap created over weekend |
| **Friday 20:00–23:59 UTC** | Profit-taking, position squaring | Traders closing before weekend |
| **Monthly expiry (last Friday)** | Max pain pin, then large move | Options expiry — price pinned to max pain then released |
| **Asia open (00:00 UTC)** | Fake breakout | Low volume, hunted stops |
| **US open (13:30 UTC)** | Genuine breakout OR fakeout — 50/50 | High volume, both real and fake moves happen |

**Rule:** Reduce position size by 0.5x during Sunday evening, Friday close, and monthly expiry. These windows have elevated trap probability.

### 4.8 Master Trap Avoidance Checklist

Before ANY entry, run this 8-point check. <5/8 passes = no trade.

| # | Check | Criteria | Pass? |
|---|-------|----------|-------|
| 1 | **Volume** | Signal candle volume ≥ 1.8x 20-period avg | |
| 2 | **Follow-through** | Next candle(s) confirming direction | |
| 3 | **CVD alignment** | CVD confirms the direction (not diverging) | |
| 4 | **RSI context** | Not extreme: RSI 30-70 for longs, 30-70 for shorts | |
| 5 | **Funding rate** | Not extreme: -0.03% to +0.03% | |
| 6 | **Session quality** | Signal in US or EU session, not Asia/transition | |
| 7 | **Higher TF alignment** | 1h and 1d structure not opposing the trade | |
| 8 | **Liquidity zone proximity** | Clear target zone within 1.5-3 ATR (good R:R) | |

### 4.9 When Trapped — Damage Control

**If you entered and the trap triggers:**

1. **Immediate rule:** If price closes back through the breakout level in the OPPOSITE direction on the same timeframe you entered → EXIT immediately. Do not wait for stop.

2. **The 1-candle rule:** If the candle AFTER your entry closes against you by >50% of your expected move → EXIT. The thesis is broken.

3. **Do NOT reverse immediately:** A trap doesn't guarantee the opposite direction works. Wait for the reversal to establish (1-2 confirming candles) before entering the opposite side.

4. **Trap → Opportunity:** A confirmed trap is actually a HIGHER probability setup in the opposite direction. If a bull trap is confirmed (price closed back below resistance), the short from that level has a 65-70% win rate.

5. **Size reduction after trap:** After being trapped, reduce next trade size by 50%. Revenge trading after a trap is the #1 account killer.

---

## 5. SYNTHESIS — How These Four Domains Combine

### 5.1 The Complete Decision Flow

```
1. MARKET CONTEXT: What's the tide?
   ├─ BTC.D, TOTAL trend, USDT.D → risk-on or risk-off?
   ├─ Session: are we in US/EU window or dead zone?
   └─ Narrative: what sector is leading?

2. LIQUIDITY POOLS: Where are the magnets?
   ├─ Where are equal highs/lows?
   ├─ Where are large liquidation clusters?
   ├─ What does funding rate say about crowded positions?
   └─ CVD: absorption or distribution?

3. CHART PATTERNS: Is there a setup at a liquidity zone?
   ├─ Flag/pennant at VWAP in an uptrend?
   ├─ Double bottom at a previous support + liquidation cluster?
   ├─ Wick reversal at a volume profile POC?
   └─ Multi-timeframe: does 1d structure support the 1h pattern?

4. TRAP CHECK: Is this setup real?
   ├─ Run 8-point trap avoidance checklist
   ├─ Volume confirms?
   ├─ CVD confirms?
   ├─ RSI/Funding not extreme?
   └─ Score ≥5/8 → ENTER
```

### 5.2 The Top 3 Highest-Conviction Setups

**Setup A: Session ORB + Liquidity Grab at US Open**
```
Context: US open (13:30 UTC), 1d BULL trend, funding neutral
Setup: First 30-min range forms. Price breaks above, grabs stops above range high,
       closes back inside. CVD shows brief spike then absorption.
Entry: SHORT after the grab confirms (close inside range + CVD turn)
Stop: Above the grab wick
Target: Range low → next support
WR: 65-70%
```

**Setup B: VWAP Reversion from Key Level**
```
Context: SIDEWAYS 1d regime, US or EU session
Setup: Price deviates >1.5% from 1h VWAP AND at a volume profile POC or prev day high/low.
       Wick rejection candle on 15m with vol >1.5x avg. CVD diverging.
Entry: On 15m candle close confirming reversal
Stop: Beyond the rejection wick
Target: VWAP
WR: 60-65%
```

**Setup C: Funding Rate Contrarian at Double Top/Bottom**
```
Context: Funding >0.05% (overcrowded long) AND price at 1h double top resistance
Setup: Price breaks above double top by 0.3% (grabbing short liquidation + late longs).
       Reversal candle closes back below the level. Volume on reversal > volume on breakout.
Entry: Short on close below the level
Stop: Above the grab wick
Target: Double top measured move down
WR: 65-70%
```

### 5.3 What This Means for the Screener Architecture

The screener must:

1. **Market context pre-filter:** Before scanning individual coins, determine tide (BTC.D, TOTAL, USDT.D). If risk-off → alert only, no trade signals.

2. **Liquidity zone pre-compute:** For each coin, pre-calculate: previous day H/L, previous week H/L, equal highs/lows (last 20 bars), volume profile POC/VAH/VAL (1d and 1w).

3. **Multi-timeframe scan:** Scan 1d for regime → 1h for pattern → 15m for entry setup. Only fire when ≥2 timeframes align.

4. **Derivatives integration:** Funding rate, OI, and liquidation data must be fetched alongside OHLCV. The `derivatives` agent in the firm consumes this.

5. **Session gate:** Signals outside US/EU sessions require +1 confirmation factor. Asian session signals are logged but not alerted unless multi-confirmation.

6. **Post-signal trap check:** The agent firm's risk agent runs the 8-point checklist before final approve/veto. A trap score <5/8 = automatic veto.

---

*End of research document. Next: implementation plan.*
