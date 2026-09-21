# BRPT (Barito Pacific Tbk) — Deep Dive Strategy Report

**Generated:** 2026-05-27
**Source:** `dive.html` — IDX Walk-Forward Dashboard
**Engine:** `idx-walkforward-5001` multi-strategy backtest system
**Data Source:** Stockbit OHLCV + yfinance, 972 tickers IDX universe

---

## 1. DIVE.HTML — Dashboard Overview

`dive.html` adalah dashboard analisis teknikal tingkat lanjut untuk setiap ticker di bursa IDX. Dashboard ini menyediakan:

| Fitur | Deskripsi |
|-------|-----------|
| Candlestick Chart | Interactive (Lightweight Charts), support 1H/1D/1W timeframes |
| VWMA 20 | Volume-Weighted Moving Average overlay |
| Volume Profile | Primitive rendering Point of Control (POC), high-volume nodes |
| Delta Volume | Proxy buy/sell pressure per bar (Close positioning vs High-Low range) |
| Strategy Dropdown | Pilih strategi, plotting entry/exit markers langsung di chart |
| Strategy Signals Table | Semua 10 strategi dengan sinyal BUY/--, Walk-Forward %, avg return, Sharpe |
| Order Flow | Net volume 20 hari, delta bars, flow score from Stockbit |
| Top Brokers | Buy/Sell breakdown per broker, daily-selectable |
| Pre-Mover Setup | CONTINUATION + REVERSAL_BREAKOUT scoring badge |
| Regime Badge | BULL / BEAR / SIDEWAYS (ML-based) |

---

## 2. STRATEGY SUITE — 10 Strategi Terintegrasi

Dari `engine/strategies.py` dan `strategies_cheatsheet.txt`:

| # | Strategy | Entry Trigger | TP | SL | Target WR |
|---|----------|---------------|----|----|-----------|
| 1 | Vol-Weighted | VR > 1.8x + delta+ + > SMA10 | 2.0% | 1.5% | 65% |
| 2 | Momentum Following | 2-day streak + VR > 1.3x | 3.5% | 2.5% | 55% |
| 3 | VWAP Reversion | Price < VWAP(-1%) + VR > 1.3x | 1.5% | 1.0% | 67% |
| 4 | Conservative Confirm | VR > 1.3x + bullish candle + > MA20 | 1.5% | 1.0% | 70% |
| 5 | Volume Profile POC | Price reverts to POC from above | 1.5% | 1.5% | 65% |
| 6 | Inside Bar Breakout | Prev bar inside, breakout above high | ATR x2 | prev low | 60% |
| 7 | NR7 Breakout | Narrowest range in 7, breakout | -- | -- | -- |
| 8 | ORB | Opening Range Breakout (daily ATR proxy) | -- | -- | -- |
| 9 | Swing Trend | Swing high/low structure break | -- | -- | -- |
| 10 | Trend Following Breakout | Close > D20 Donchian, VR > 1.8x, ATR expanding, > MA50 | -- | -- | -- |

---

## 3. 9-LAYER SIGNAL FILTER

Sebelum sinyal BUY dikonfirmasi, ticker harus lolos 9 lapis:

```
1. Calendar Blackout    — H-1/H+1 sekitar BI Rate & FOMC -> skip scan
2. Sector Rotation      — Ticker harus di sektor OVERWEIGHT atau NEUTRAL
3. WF Filter            — Walk-forward score >= 50%
4. Fundamental          — PE < 20, PBV < 5, ROE > 5%
5. Flow Confirmation    — Stockbit flow score >= +2
6. Technical            — VR > 1.3x, VWAP align, ATR normal
7. WF Consistency       — Win rate >= 50%, Sharpe >= 0.8
8. Regime (ML)          — BULL atau SIDEWAYS (bukan BEAR)
9. Weekly Trend (MTF)   — Close >= MA20W dan MA20W slope >= -1%
```

---

## 4. BRPT WALK-FORWARD BACKTEST RESULTS

Data dari `out/meta_dataset_backtest.json` — 4 rolling windows @ 3 bulan:

```
Window 0: 2025-04-16 -> 2025-07-16  (Early Uptrend)
Window 1: 2025-07-16 -> 2025-10-16  (Strong Trend)
Window 2: 2025-10-16 -> 2026-01-16  (Exhaustion/Correction)
Window 3: 2026-01-16 -> 2026-04-16  (Consolidation)
```

### Window 0 — Early Uptrend (Apr–Jul 2025) — GOLDEN WINDOW

| Metric | Value |
|--------|-------|
| ADX | 33.5 (trend established) |
| MA Slope | -4.9% (MA still declining, early reversal) |
| VR Mean | 0.90x (normal volume) |
| Close vs MA | -0.1% (PRICE AT MA — perfect entry zone) |
| Range | 41.9% |

| Strategy | Return | Win Rate | Sharpe | Verdict |
|----------|--------|----------|--------|---------|
| Trend Following Breakout | +6.8% | 100% | -- | BEST |
| Inside Bar Breakout | +4.9% | 100% | +36.66 | Strong |
| ORB | +4.4% | 100% | +208.28 | Strong |
| Vol-Weighted | +4.3% | 60% | +6.22 | Good |
| Momentum | +3.8% | 50% | +4.91 | Good |
| Conservative | +3.3% | 60% | +6.28 | Good |
| NR7 Breakout | -1.4% | 0% | -- | Fail |

Pattern: Ketika BRPT mulai naik dari dekat MA dengan ADX 25-40, semua strategi breakout bekerja. TFB +6.8%. Golden window.

### Window 1 — Strong Trend (Jul–Oct 2025)

| Metric | Value |
|--------|-------|
| ADX | 56.1 (VERY strong trend) |
| MA Slope | +5.9% |
| VR Mean | 1.10x |
| Close vs MA | +23.1% (extended) |

| Strategy | Return | Win Rate | Sharpe |
|----------|--------|----------|--------|
| Conservative | +9.8% | 100% | +79.42 |
| Momentum | +5.7% | 75% | +15.68 |
| Vol-Weighted | +4.2% | 67% | +7.91 |

### Window 2 — Exhaustion (Oct 2025–Jan 2026) — DANGER ZONE

| Metric | Value |
|--------|-------|
| ADX | 58.1 |
| MA Slope | +13.2% |
| VR Mean | 0.76x (VOLUME DRYING UP) |
| Close vs MA | +3.5% |

ALL strategies NEGATIVE. VR < 0.8x after rally = distribution. Exit signal.

### Window 3 — Consolidation (Jan–Apr 2026)

| Metric | Value |
|--------|-------|
| ADX | 23.0 (trend weak) |
| MA Slope | -5.2% |
| VR Mean | 0.92x |
| Close vs MA | -11.9% (below MA) |

| Strategy | Return | Win Rate | Sharpe |
|----------|--------|----------|--------|
| VWAP Reversion | +9.0% | 50% | +4.72 |
| Conservative | +6.8% | 100% | +859.16 |

---

## 5. KEY FINDINGS — When BRPT Price Starts Going Up

### Strategy Heatmap by Regime

```
                        +------------------------------------------+
REGIME                  | BEST STRATEGY                            |
------------------------+------------------------------------------+
EARLY UPTREND           | TFB >> Inside Bar > ORB > Vol-Weighted   |
(ADX 25-40, near MA)    | Semua breakout strategy unggul           |
------------------------+------------------------------------------+
STRONG UPTREND          | Conservative > Momentum > Vol-Weighted   |
(ADX > 40, above MA)    | Trend-following, kurangi breakout        |
------------------------+------------------------------------------+
EXHAUSTION/DISTRIBUTION | STAY OUT                                |
(VR < 0.8x after rally) | Semua strategi long FAIL                 |
------------------------+------------------------------------------+
CORRECTION/CONSOLIDATION| VWAP Reversion > Conservative            |
(ADX < 25, below MA)    | Mean-reversion, cari support             |
------------------------+------------------------------------------+
```

### 6 Methods Discovered

**1. Trend Following Breakout (TFB)** — Early trend catcher. ADX 25-40, price near MA, volume muncul. Return +6.8%.

**2. Multi-Strategy Confirmation** — 2+ strategi BUY bersamaan di dive.html = high conviction. Window 0: 7 dari 7 strategi positif.

**3. Volume Profile POC Entry** — Entry di level akumulasi institusional dari Volume Profile primitive.

**4. VWAP Reversion** — Counter-trend, ADX < 25, harga di bawah MA. Return +9.0%.

**5. REVERSAL_BREAKOUT** — Tangkap saham dari support dengan volume explosion > 2x, SEBELUM uptrend terbentuk.

**6. Volume Dry-Up Detection** — VR < 0.8x setelah rally = EXIT semua posisi. Window 2: semua strategi negatif.

---

## 6. BRPT TRADING PLAYBOOK

### Entry Rules (When to BUY)

- ADX antara 25-45 (bukan < 25 sideways, bukan > 50 exhausted)
- Volume Ratio > 1.0x (minimal, ideal > 1.3x)
- Harga tidak lebih dari 10% di atas MA20 (hindari chasing)
- Minimal 2 dari: TFB, Conservative Confirm, Vol-Weighted memberi sinyal BUY
- Flow Score Stockbit > 0 (opsional)
- Regime = BULL (bukan BEAR)

### Exit / Avoid Rules

- VR turun di bawah 0.8x setelah rally -> CLOSE POSITION
- ADX > 55 + volume menurun -> late cycle, jangan entry baru
- Harga > 20% di atas MA20 -> trailing stop ketat
- Semua strategi berubah dari BUY ke -- -> exit

### Position Sizing

```
Capital:     Rp 50.000.000
Max/Trade:   30% = Rp 15.000.000
Commission:  Buy 0.15% / Sell 0.25%
Slippage:    0.10%
SL: 1.0-2.5% | TP: 1.5-3.5% | R:R minimal 1.5:1
```

---

## 7. LIVE BRPT STATE — 2026-05-26 (Current)

### Critical: BRPT is in a CRASH, NOT in any backtest window

```
May 5:  2,300 -> May 14: 2,080 -> [11-DAY GAP - SUSPENSION] -> May 25: 1,495 -> May 26: 1,565
         +--- -35% CRASH in 3 weeks ---+                            -28.1% gap   +4.7% bounce
```

| Metric | Live Value | Meaning |
|--------|-----------|---------|
| Close | 1,565 | -35% from May 5 peak |
| ADX | 13.8 | Trend collapsed — sideways/consolidating |
| Volume Ratio | 2.73x | Massive volume spike |
| Close vs MA20 | -23.3% | Deeply oversold |
| Close vs MA50 | -13.6% | Below MA50 |
| MA20 5-bar Slope | -4.5% | Still declining |
| Data Gap | 11 days (May 14-25) | Likely trading suspension |
| Premover Alert | REVERSAL_BREAKOUT score=55 | Detected May 26 |

### Key Concern: Fundamental Red Flags (from stockbit_keystats, last updated Apr 14)

| Metric | Value | Warning |
|--------|-------|---------|
| NPM | -4.47% | Net Profit Margin NEGATIF |
| DER | 3.47 | Utang 3.5x equity — sangat tinggi |
| Earnings Growth | -428% | Laba turun drastis |
| PE | 25.44 | Tidak meaningful karena NPM negatif |

---

## 8. GAP ANALYSIS — What's Already in IDX vs What's Missing

### Summary Table

| Component | Status | Gap Level | Notes |
|-----------|--------|-----------|-------|
| 10 Strategies (daily bar) | Implemented | -- | Mature |
| Walk-Forward Backtest | Implemented | RED | Stale windows, no rolling |
| Regime Detection (BULL/BEAR/SIDEWAYS) | Implemented | YELLOW | No adaptive switching |
| REVERSAL_BREAKOUT Pattern | Implemented | YELLOW | Context-blind VR |
| dive.html Dashboard | Functional | RED | PLAN.md (582 lines) not implemented |
| 9-Layer Signal Filter | Implemented | YELLOW | Stale fundamental data |
| Premover Detector | Implemented | YELLOW | No auto-execution |
| Post-Suspension Detection | MISSING | RED RED | Critical gap |
| Crash Recovery Strategy | MISSING | RED RED | Critical gap |
| Adaptive Strategy Switching | MISSING | YELLOW | High value |
| Portfolio Backtest | Planned (R6) | RED | Important |
| Parameter Optimizer | Planned (R7) | YELLOW | Medium |
| Frontend Strategy Registry | Planned (R1) | RED | High UX impact |
| Backtest Auto-Rolling | MISSING | RED | Data decays |
| Fundamental Live Refresh | MISSING | YELLOW | 6 weeks stale |

---

### GAP #1: Backtest Windows Don't Roll Forward 🔴

Backtest JSON di-generate dengan 4 fixed windows berakhir April 2026. Tidak ada window yang mencakup crash BRPT di May 2026. Cycle model "Window 0-3" tidak berlaku untuk crash/suspension. Backtest harus auto-rolling setiap 3 bulan.

### GAP #2: No Suspension / Trading Halt Awareness 🔴🔴

BRPT memiliki 11-day gap (May 14-25) — kemungkinan besar trading suspension. Gap-down -28.1% pada resume. Sistem tidak mendeteksi ini sebagai event spesial. Semua kalkulasi teknikal mengasumsikan kontinuitas yang salah.

### GAP #3: VR Spike is Context-Blind 🟡

VR 2.73x setelah crash -35% memiliki arti berbeda dari VR 2.73x dalam uptrend normal. REVERSAL_BREAKOUT score=55 tapi near_low=0 dan above_3ma=0. Score misleading karena volume explosion terjadi dalam konteks crash, bukan akumulasi sehat.

### GAP #4: Fundamental Data is Stale 🟡

Data fundamental terakhir: April 14, 2026 (6 minggu). NPM -4.47%, earnings growth -428%, DER 3.47 adalah red flags yang seharusnya memblokir entry. Filter fundamental tidak berfungsi efektif dengan data kadaluarsa.

### GAP #5: REVERSAL_BREAKOUT Fired but No Trade 🟡

Premover alert BRPT May 26 (score=55) terdeteksi, tapi paper_trades kosong. Gap antara knowing dan doing — sistem tahu ada setup tapi tidak bertindak.

### GAP #6: PLAN.md Frontend Strategy Registry Not Implemented 🔴

PLAN.md 582-line untuk interactive strategy marker plotting di dive.html — sudah diidentifikasi di Sprint 12 R1 tapi belum dikerjakan. Strategy dropdown saat ini hanya plotting entry markers tanpa exit markers, trade detail, atau PnL annotation.

### GAP #7: No Crash-Specific Strategies 🔴🔴

Tidak ada strategi untuk post-suspension gap-down, crash recovery, dead cat bounce, atau volume climax differentiation. BRPT May 2026 adalah skenario yang tidak tercover.

### GAP #8: No Adaptive Strategy Switching 🟡

Sistem tahu regime BRPT dan strategi mana yang perform di regime tersebut, tapi tidak otomatis switch. Semua manual.

### GAP #9: No Portfolio-Level Analysis 🔴

Single-ticker only. Tidak bisa analisis BRPT dalam konteks sektor, korelasi IHSG, atau portfolio impact. Direncanakan di Sprint 13 R6.

### GAP #10: No Parameter Optimization Per-Ticker 🟡

Parameter strategi hardcoded untuk semua 972 ticker. BRPT mungkin butuh parameter berbeda. Direncanakan di Sprint 13 R7.

---

## 9. BOTTOM LINE

**Apa yang sudah ada di IDX:** Semua 6 metode yang ditemukan (TFB, Multi-Strategy Confirmation, Volume Profile Entry, VWAP Reversion, REVERSAL_BREAKOUT, Volume Dry-Up) — **semuanya sudah ada di sistem idx-walkforward-5001.**

**Apa gap sebenarnya — 5 hal utama:**

1. **Sistem adalah rear-view mirror.** Analisis berdasarkan data historis yang tidak mencakup kondisi terkini. Backtest perlu rolling window otomatis.

2. **Tidak ada penanganan event ekstrem.** Suspension, gap-down, crash — BRPT May 2026 adalah skenario yang tidak tercover strategi manapun.

3. **Deteksi ada, aksi tidak.** REVERSAL_BREAKOUT terdeteksi tapi tidak ada paper trade. Gap antara knowing dan doing.

4. **Plan sudah ada, eksekusi belum.** PLAN.md (582 lines), R1-R16 di TODO.md — backlog yang jika diselesaikan akan menutup banyak gap. Sprint 12-16 sudah diprioritaskan.

5. **Fundamental kadaluarsa.** NPM -4.47% adalah red flag yang tidak terdeteksi karena data 6 minggu stale.

---

*Report generated from idx-walkforward-5001 engine backtest data, live database query, and dive.html dashboard analysis.*
