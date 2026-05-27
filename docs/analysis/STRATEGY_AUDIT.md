# IDX Strategy Audit vs Literatur Akademis/Teknikal

**Tanggal**: 2026-05-17
**Metodologi**: 5 grup strategi di `engine/strategies.py` di-research via NotebookLM research-agent dengan seed URLs Wikipedia (lihat `audit_A..E_*.md`). Hasil literatur lalu di-cross-reference dengan implementasi aktual di kode.
**Limitasi**: Sumber literatur Wikipedia-level (general framework). Untuk audit lebih dalam perlu paper akademis (Jegadeesh-Titman 1993, Crabel original, Steidlmayer original) atau buku rujukan yang belum di-ingest ke notebook.

---

## Ringkasan Verdict per Strategi

| # | Strategi | Verdict | Catatan singkat |
|---|---|---|---|
| 1 | Vol-Weighted Entry | 🟢 ALIGN | Standard volume-confirmation. Tambahkan OBV/MFI secondary. |
| 2 | Momentum Following | 🟡 LAG | "2-day streak" ≠ momentum klasik (Jegadeesh-Titman: 6–12 bln). Rebrand atau tambah HTF filter. |
| 3 | VWAP Reversion | 🟢 ALIGN | Klasik. Klarifikasi semantik `rolling(60)` VWAP vs session-anchored. |
| 4 | Conservative Confirm | 🟢 ALIGN | Mirip Alexander Elder triple-screen tapi pakai 1 MA. Pertimbangkan multi-MA alignment. |
| 5 | VWMA Breakout Pullback | 🔵 LEAD | Lebih canggih dari literatur. Invalidation rule + power-candle variant solid. |
| 6 | Volume Profile POC | 🟡 ALIGN-partial | POC bounce standard, tapi Value Area, Composite multi-day, Initial Balance belum dipakai. |
| 7 | Inside Bar Breakout | 🟠 INCONSISTENT | Cheatsheet bilang "2 inside bar", code cuma cek 1. Reconcile. |
| 8 | NR7 Breakout | 🟢 ALIGN | Crabel-style. Volume filter 0.8× avg5 = tambahan diskresioner (di luar Crabel original). |
| 9 | ORB | 🔴 DIVERGENT | "Daily approximation pakai ATR" bukan ORB sesungguhnya. Crabel/Fisher ORB = first 30/60 min intraday. Rename atau rebuild. |
| 10 | Swing Trend | 🔵 LEAD | Best-in-class. Dow theory + ADX regime + 7 exit rules + flow integration. |
| 11 | Trend Following Breakout | ⚪ Not assessed | Belum di-deep-read. Diasumsikan ALIGN/LEAD. |

**Legenda**: 🟢 ALIGN = sesuai literatur · 🟡 LAG = ketinggalan kanon literatur · 🔵 LEAD = lebih advanced dari literatur · 🟠 INCONSISTENT = code vs dokumentasi tidak match · 🔴 DIVERGENT = jalan sendiri (bukan masalah, tapi penamaan menyesatkan)

---

## Detail Gap & Rekomendasi per Strategi

### #2 Momentum Following — LAG dari kanon literatur

**Implementasi**: `streak2 & (vr > 1.3) & (vr <= 5.0)` — 2 hari close naik berturut + volume ratio 1.3-5×.

**Literatur**: Klasik momentum (Jegadeesh & Titman 1993) = cross-sectional return ranking selama 6-12 bulan, hold 3-12 bulan. Average +1%/bulan excess return. 52-week high adalah sinyal kanonik (George & Hwang 2004).

**Gap**: "2-day streak" lebih tepat disebut **short-term continuation** / **breakout follow-through**, bukan momentum. Tidak ada lookback panjang, tidak ada cross-sectional ranking.

**Rekomendasi**:
- Opsi A: Rebrand jadi `Short-Term Continuation` di display.
- Opsi B: Tambah strategi baru `strategy_momentum_classic` dengan filter: ranking 60-day return top quartile + entry pada pullback (combine "JT momentum" + technical entry).
- Opsi C: Tambah filter classical momentum sebagai layer di 9-layer filter — "must be in top 25% relative strength vs IHSG 60D" sebelum strategi #2 boleh fire.

### #6 Volume Profile POC — ALIGN partial

**Implementasi**: Single-day POC bounce. Low touches POC ±1.5%, close > POC, vol < avg, lower wick ≥ 50% body. TP = HVN terdekat. SL = low bar.

**Gap dari literatur** (Steidlmayer Market Profile, J. Dalton "Mind Over Markets"):
1. **Value Area (VAH/VAL)** tidak dipakai — VAH/VAL adalah pasangan POC, sering jadi reaction levels lebih kuat dari POC sendiri.
2. **Composite Profile multi-day** — single-day POC bisa noisy. Multi-day (5-20 bar) Composite Profile lebih reliable untuk swing.
3. **Initial Balance (IB)** — first hour range; break IB di pagi = sinyal "trend day" yang membatalkan POC bounce setup.
4. **`vol < avg` requirement** — kontrarian, asumsinya pullback pada vol rendah = healthy. Tapi literatur juga akui POC bounce pada vol tinggi ("balanced market test" — Dalton).

**Rekomendasi**:
- Tambah `calc_value_area(df, lookback=20)` → return (POC, VAH, VAL).
- Tambah variant `strategy_volume_profile_vah_rejection` (price ke VAH dari bawah lalu reject).
- Tambah `strategy_composite_poc_swing` pakai 20-bar Composite.
- Layer baru di 9-layer: "skip jika IB sudah break > 1×ATR sebelum entry signal".

### #7 Inside Bar — INCONSISTENT dokumentasi vs kode

**Cheatsheet** (strategies_cheatsheet.txt:13): `Inside Bar Breakout — 2 inside + 3rd break+vol`

**Code** (strategies.py:795): `inside = (prev['high'] < prev2['high']) and (prev['low'] > prev2['low'])` — hanya cek **1** inside bar (prev inside prev2), tidak ada 2 inside berturut. Juga tidak ada volume check di breakout bar.

**Rekomendasi**:
- Putuskan: ikutin cheatsheet (lebih selektif) atau code (lebih banyak signal).
- Kalau 2-inside: ubah jadi `inside_1 = ... ; inside_2 = (prev2 inside prev3); sig = inside_1 & inside_2 & break_3`.
- Tambah `vol_breakout = row['volume'] > avg_vol_20 * 1.3` sesuai cheatsheet.
- Pertimbangkan Hikkake pattern (failed inside bar breakout → reversal) sebagai strategi turunan.

### #9 ORB — DIVERGENT (paling perlu diperbaiki) — **partially addressed 2026-05-17**

**Status update**: Honesty restored in `strategy_orb` docstring + inline disclaimer block. Added `calc_opening_range_from_ticks()` and `check_orb_intraday_signal()` in `engine/strategies.py` (after `strategy_orb`). Both backed by the real `ticks` table (1-min Stockbit). Smoke-tested on 2026-05-15 LQ45 universe — 0 valid signals at 11:00 WIB (correctly selective).

**Still pending** for full A.2:
- Wire `check_orb_intraday_signal()` into `screener/screener_jobs.py` so it runs in the live scheduler scan.
- Build backtest variant `strategy_orb_intraday_backtest(df_daily, ticker)` that loops daily bars + queries ticks per date. (Existing `strategy_orb` registry entry untouched — wf_scores stay valid.)


**Implementasi**: "Opening Range Breakout — Daily approximation. Opening Range = open ± (ATR14 × 0.5). Breakout signal: close > open + (ATR × 0.5) AND volume > avg_vol × 1.5."

**Literatur** (Toby Crabel "Day Trading with Short Term Price Patterns" 1990, Mark Fisher "ACD Method"):
- ORB asli = breakout dari **first 30/60 min intraday range**.
- "Opening Range" adalah range price antara open dan jam X (biasanya 09:30-10:00 WIB).
- Inti setup: trend hari ini sering ditentukan apakah ada follow-through di luar range awal.

**Gap fundamental**: Implementasi current cuma pakai daily bar `open`-nya — bukan range first hour. ATR×0.5 dari open ≠ first-hour range. Tidak ada sense of "first hour" karena daily bar.

**Rekomendasi**:
- **Opsi A (recommended)**: Rebuild pakai data intraday Stockbit yang sudah kamu punya (`screener/idx_scraper.py` sudah fetch tradebook ticks). Compute genuine 30-min/60-min opening range pakai 1-min/5-min bars.
- **Opsi B**: Rename jadi `strategy_atr_open_breakout` untuk hindari miskonsepsi.
- **Opsi C**: Drop strategi ini, tidak menambah edge unik vs NR7 + Vol-Weighted gabungan.

---

## Cross-Cutting Findings

### Yang LEAD dari literatur (jaga, ini diferensiator)

1. **9-layer signal filter** — kombinasi (calendar blackout, sector rotation, walk-forward score, fundamental, flow, technical, weekly trend, regime ML) sangat jarang ada di literatur ritel. Profesional-grade.
2. **VPIN integration** — microstructure metric (Easley-O'Hara) yang biasanya untuk institutional HFT. Penggunaan VPIN > 0.8 sebagai "danger" filter adalah aplikasi sound dari toxic order flow detection.
3. **Walk-forward optimization** — standar quant pro, jauh di atas backtest-and-forget yang dominan di literatur ritel.
4. **Swing Trend 7-rule exit** — exit logic lebih kaya dari "trend until trend ends" klasik.
5. **Calendar blackout (BI Rate RDG + FOMC)** — risk management makro yang spesifik untuk emerging market — di luar literatur Anglo-Saxon.
6. **Stockbit flow score integration** — broker-level flow analysis = sumber alpha unik IDX.

### Yang LAG dari literatur (worth menambahkan)

1. **Cross-sectional momentum** (Jegadeesh-Titman style) — belum ada. Setup untuk universe-wide ranking.
2. **Pairs trading / statistical arbitrage** — belum ada. IDX ada banyak pair sektor (BBCA-BBRI, ASII-UNVR, dll).
3. **Volatility regime trading** — ATR filter ada, tapi belum ada strategi yang aktif eksploit "low vol → high vol" transition (mis. Bollinger Squeeze → expansion).
4. **Multi-timeframe HH/HL structure** — Swing Trend pakai pivot 1 timeframe; literatur Dow theory rekomendasi 3 timeframe (primary/medium/short).

### Yang bisa di-strengthen

1. **Volume secondary confirmation** — OBV / Acc-Distribution Line belum dipakai. Untuk Strategi 1-4 (volume-based), tambah filter "OBV slope agree dengan price" akan kurangi false signals.
2. **Anchored VWAP** — strategi 3 pakai `rolling(60)` VWAP. Tambah anchored VWAP dari significant high/low juga berguna sebagai support/resistance dinamis.
3. **Value Area & Composite Profile** — sudah dibahas di Strategi #6.

---

## Top 5 Action Items (prioritized)

| Prioritas | Action | Effort | Impact |
|---|---|---|---|
| P0 | Fix Inside Bar code-vs-cheatsheet inconsistency (#7) | S | High — silent bug saat ini |
| P0 | Rename atau rebuild ORB (#9) — current implementation menyesatkan | M | Med — hindari false confidence |
| P1 | Tambah Value Area (VAH/VAL) ke Volume Profile (#6) | M | High — POC saja kurang lengkap |
| P1 | Tambah classical cross-sectional momentum filter (universe-rank 60D) | M | High — ngisi gap kanonik |
| P2 | Tambah OBV trend filter ke 9-layer | S | Med — secondary volume confirm |

---

## Material yang Dipakai

- `audit_A_volume_momentum.md` — Wikipedia: Momentum (finance), Volume (finance), Technical analysis
- `audit_B_vwap_reversion.md` — Wikipedia: VWAP, Mean reversion (finance)
- `audit_C_volume_profile.md` — Wikipedia: Market profile, Auction
- `audit_D_breakout.md` — Wikipedia: Opening range, Breakout (technical analysis)
- `audit_E_trend.md` — Wikipedia: Trend following, Dow theory, Swing trading

**Improvement untuk audit berikutnya**: Ingest paper SSRN/JSTOR original (Jegadeesh-Titman 1993, Easley-Lopez de Prado-O'Hara 2012 untuk VPIN, Crabel 1990 chapter scans). Wikipedia-only audit cukup untuk identifikasi gap permukaan, tidak untuk validasi parameter spesifik.

---

# Rekomendasi Lanjutan (Expanded)

## A. Implementasi-Ready untuk Top 5 Action Items

### A.1 — Fix Inside Bar (P0)

Lokasi: `engine/strategies.py:795`

```python
# Sebelum (1 inside bar):
inside = (prev['high'] < prev2['high']) and (prev['low'] > prev2['low'])

# Sesudah (2 inside bars + volume confirm, sesuai cheatsheet):
inside_1 = (prev['high']  < prev2['high']) and (prev['low']  > prev2['low'])
inside_2 = (prev2['high'] < df.iloc[i-3]['high']) and (prev2['low'] > df.iloc[i-3]['low'])
vol_ok   = row['volume'] > df['volume'].rolling(20).mean().iloc[i-1] * 1.3
if not (inside_1 and inside_2 and vol_ok):
    equity.append(capital_cur); continue
```

**Tambahan check**: pastikan `i >= 22` (butuh prev3). Update test `test_strategies.py::test_inside_bar_2bar`.

### A.2 — Rebuild ORB pakai intraday Stockbit (P0)

Karena `screener/idx_scraper.py` sudah fetch tradebook ticks, build genuine ORB:

```python
def strategy_orb_intraday(df_min: pd.DataFrame, capital=50_000_000,
                          opening_minutes=30) -> dict:
    """
    df_min: minute-bar OHLCV per ticker per session.
    Opening Range = high/low first N minutes (default 30).
    Long entry: break above OR_high with VR > 1.5x.
    Short entry: break below OR_low (kalau enable short).
    SL: OR_low (long) / OR_high (short).
    TP: OR_range × 2 atau session high/low.
    """
    df_min['date'] = pd.to_datetime(df_min['timestamp']).dt.date
    for session_date, day_bars in df_min.groupby('date'):
        opening = day_bars.iloc[:opening_minutes]
        or_high, or_low = opening['high'].max(), opening['low'].min()
        rest = day_bars.iloc[opening_minutes:]
        # ... iterate rest for breakout signal
```

Helper baru: `engine/intraday_loader.py::load_minute_bars(ticker, date_range)` yang baca dari tabel intraday (kalau ada) atau aggregate dari tradebook ticks.

### A.3 — Value Area helper (P1)

```python
def calc_value_area(df: pd.DataFrame, lookback: int = 20,
                    bin_pct: float = 0.005, va_pct: float = 0.70):
    """Return (POC, VAH, VAL) for last `lookback` bars."""
    window = df.iloc[-lookback:]
    price_min, price_max = window['low'].min(), window['high'].max()
    bin_size = price_min * bin_pct
    bins = np.arange(price_min, price_max + bin_size, bin_size)
    vol_at_price = np.zeros(len(bins))
    for _, bar in window.iterrows():
        # distribute bar volume across price range
        bar_range = bar['high'] - bar['low']
        if bar_range == 0: continue
        for i, b in enumerate(bins):
            if bar['low'] <= b <= bar['high']:
                vol_at_price[i] += bar['volume'] * bin_size / bar_range
    poc_idx = vol_at_price.argmax()
    poc = bins[poc_idx]
    # Expand from POC until 70% volume captured
    total_vol = vol_at_price.sum()
    captured, lo, hi = vol_at_price[poc_idx], poc_idx, poc_idx
    while captured / total_vol < va_pct and (lo > 0 or hi < len(bins)-1):
        up_vol = vol_at_price[hi+1] if hi < len(bins)-1 else 0
        dn_vol = vol_at_price[lo-1] if lo > 0 else 0
        if up_vol >= dn_vol and hi < len(bins)-1:
            hi += 1; captured += up_vol
        elif lo > 0:
            lo -= 1; captured += dn_vol
        else:
            break
    return poc, bins[hi], bins[lo]   # POC, VAH, VAL
```

Pakai di strategi baru `strategy_vah_rejection` (price test VAH dari bawah → reject → entry pullback).

### A.4 — Classical momentum filter (P1)

Tambah sebagai **filter layer**, bukan strategi baru. Edit `engine/strategies.py`:

```python
def filter_classical_momentum(df: pd.DataFrame, all_tickers_df: dict,
                              lookback: int = 60, top_pct: float = 0.25):
    """
    Cross-sectional momentum: ticker harus di top 25% return 60D
    across full universe.
    all_tickers_df: dict {ticker: df} dari load_all_tickers + OHLCV.
    """
    if len(df) < lookback: return pd.Series(False, index=df.index)
    ret60 = df['close'].pct_change(lookback)
    # rank ticker ini vs universe (snapshot per bar)
    # ... (butuh universe-wide query, mahal — pre-compute di scheduler harian)
```

**Catatan**: Cross-sectional ranking mahal untuk run real-time. Pre-compute daily di `scheduler.py` (mis. jam 08:00) → simpan sebagai `momentum_rank.parquet`, lalu strategi tinggal lookup.

### A.5 — OBV trend layer (P2)

Tambah ke `engine/strategies.py` filters:

```python
def calc_obv(df: pd.DataFrame) -> pd.Series:
    direction = np.sign(df['close'].diff()).fillna(0)
    return (direction * df['volume']).cumsum()

def filter_obv_rising(df: pd.DataFrame, slope_period: int = 10) -> pd.Series:
    obv = calc_obv(df)
    slope = obv.diff(slope_period)
    return slope > 0   # OBV trending up
```

Apply ke strategi 1-4 sebagai optional secondary confirm.

---

## B. Strategi Baru yang Worth Ditambahkan

### B.1 — Bollinger Squeeze → Expansion

**Rationale**: Bollinger Band width contracts (squeeze) sering precede high-volatility expansion. Combine dengan VPIN/ATR untuk timing.

**Setup**:
- BB(20, 2) width di percentile 20% terbawah selama 6 bln terakhir → squeeze active
- Wait for breakout candle: close menembus BB upper + vol > 1.5x avg + ATR rising
- Entry: break of squeeze high
- SL: BB middle (MA20)
- TP: 2× ATR atau target measured move

### B.2 — Anchored VWAP (AVWAP)

**Rationale**: VWAP yang di-anchor dari significant pivot (HH, gap, earnings day) sering jadi dynamic S/R. Lebih informatif dari rolling VWAP.

**Setup**: 
- Anchor dari swing high terbaru (atau earnings day kalau ada data)
- Long entry kalau price uji AVWAP dari atas + reject (lower wick)
- SL: di bawah AVWAP - 0.5 ATR

Implementation: helper `calc_anchored_vwap(df, anchor_idx)` yang return Series VWAP dari anchor bar ke end.

### B.3 — Pairs Trading Sektor

**Rationale**: IDX punya banyak pasangan kuat: BBCA-BBRI, ASII-UNVR, INDF-ICBP. Z-score spread → mean reversion.

**Setup**:
- Compute log-spread `log(A) - β × log(B)` (β dari rolling 60-day regression)
- Z-score 20-day. Entry kalau |Z| > 2 (long underperformer, short outperformer — kalau short dibolehkan).
- Exit kalau |Z| < 0.5 atau stop kalau |Z| > 3.5.

**Catatan**: IDX banyak retailer-driven, jadi cointegration tidak selalu stabil. Walk-forward β re-fit penting.

### B.4 — Hikkake Pattern (Failed Inside Bar)

**Rationale**: Inside bar breakout yang **gagal** (price break level, lalu balik dalam 2-3 bar) sering reversal kuat. Disebut Hikkake (Daniel L. Chesler 2003).

**Setup**:
- Inside bar terjadi (i-2 vs i-3)
- Break high di bar i-1 (or break low) → "false breakout"
- Bar i return ke dalam inside bar range
- Entry: opposite direction dari false breakout

Komplementer dengan Strategi #7 — kalau Inside Bar breakout fail, Hikkake yang ambil.

### B.5 — Gap Fade (Post-Overnight)

**Rationale**: IDX overnight gap (open > prev close × 1.02 atau < prev close × 0.98) sering mean-revert di sesi 1.

**Setup**:
- Gap up > 2%, vol opening > 1.5x avg → short fade (kalau short enabled) atau skip
- Gap down > 2%, IHSG tidak crash, fundamental ok → long entry pada retracement ke gap midpoint
- TP: prev close (gap fill)
- SL: gap extreme + 0.5 ATR

**Catatan**: Hati-hati dengan ARA/ARB rule IDX — kalau gap karena breaking news, jangan fade.

---

## C. Risk & Portfolio Level

### C.1 — Strategy Correlation Analysis

Strategi 1, 2, 4 sama-sama pakai `VR > 1.3` + bullish bias. Kemungkinan fire bersamaan → overlap signals = position concentration risk.

**Action**:
- Compute pairwise correlation antar daily signal series (boolean → 1/0) selama 6 bulan.
- Jika ρ > 0.7, treat sebagai duplikat: jangan double-size, atau dedupe di paper_trade layer.

```python
# analyze_strategy_overlap.py (new script)
sigs = {name: run_backtest_signals_only(name) for name in ALL_STRATEGIES}
corr_matrix = pd.DataFrame(sigs).corr()
print(corr_matrix[corr_matrix > 0.7])  # surface overlap
```

### C.2 — Regime-Conditional Position Sizing

Cheatsheet sudah menyebutkan TP shift per regime (TRENDING +0.5%, SIDEWAYS -0.5%), tapi **lot sizing** belum kondisional.

**Action**: di `paper_trade.py`, ubah `lot_size()` jadi terima `regime` arg:
- TRENDING + sektor OVERWEIGHT → 30% capital/trade (existing)
- SIDEWAYS → 20% capital/trade
- UNCERTAIN → blocked (existing)

### C.3 — Drawdown Circuit Breaker

Saat ini tidak ada portfolio-level circuit breaker. Kalau equity curve drawdown > X% → auto-pause new entries.

**Action**: `monitor.py` tambah:
```python
def check_dd_circuit_breaker(threshold_pct: float = 8.0):
    equity_30d = get_equity_series(days=30)
    peak = equity_30d.max()
    current = equity_30d.iloc[-1]
    dd = (peak - current) / peak * 100
    if dd > threshold_pct:
        set_global_flag('NEW_ENTRIES_BLOCKED', True)
        send_telegram_alert(f"🛑 DD circuit: -{dd:.1f}%, new entries blocked")
```

Reset manual via Telegram command atau setelah equity recover ke peak × 0.95.

### C.4 — Strategy Decay Monitoring

Strategi bisa lose edge over time. Track rolling 90-day win rate per strategi, alert kalau drop > 30% dari historical baseline.

**Action**: cron weekly di `scheduler.py`:
```python
for strat in ALL_STRATEGIES:
    wr_90d = compute_paper_wr(strat, days=90)
    wr_baseline = STRATEGY_BASELINE_WR[strat]  # dari STRATEGIES cheatsheet
    if wr_90d < wr_baseline * 0.7:
        send_telegram_alert(f"⚠️ {strat} decay: WR {wr_90d:.0%} vs baseline {wr_baseline:.0%}")
```

---

## D. R&D Process Improvements

### D.1 — Auto-Research Scheduler

Pakai `research-agent` (yang baru kita setup) untuk monthly scan paper baru di topik strategi yang sedang underperform. Cron di `scheduler.py`:

```bash
# Setiap awal bulan, run research per strategy yang WR turun
0 6 1 * * cd /d/DS/research-agent && PYTHONIOENCODING=utf-8 \
  uv run research-agent research "VWAP reversion 2026 emerging market" \
  -n "Liquidity Trading" -o D:/IDX/docs/analysis/monthly_$(date +%Y-%m)_vwap.md
```

Output otomatis masuk `docs/analysis/` untuk review manual sebelum implement.

### D.2 — Standardized Backtest Report Template

Bikin template `report_strategy.md.j2` (Jinja) yang generate per-strategy:
- Equity curve PNG
- Trade-level stats (WR, avg R, max DD, max consecutive losses)
- Distribution PnL histogram
- Comparison vs IHSG benchmark
- WF score timeline

Generate via `analyze_strategy.py --strat <name> --report` → bisa langsung jadi PDF untuk review/share.

### D.3 — Strategy A/B Test Framework

Untuk uji variant baru tanpa risiko: paper-trade variant baru paralel ke production strategy, tag berbeda di DB.

```python
# paper_trade.py extension
def execute_paper_with_variant(ticker, strat, variant=None):
    trade.variant_tag = variant or 'PROD'
    # ... store both
```

Setelah 30 hari, compare `WR(PROD)` vs `WR(VARIANT_X)`. Kalau lift signifikan (p < 0.05), promote variant.

---

## E. IDX-Specific Enhancements

### E.1 — Foreign Flow (KPEI) Integration

Stockbit flow score bagus, tapi foreign flow KPEI/RTI lebih institutional. Sumber: scrape data harian KPEI net buy/sell foreign per ticker.

**Action**: tambah filter layer ke-10: `foreign_net_buy_5d > 0` untuk strategi long-bias (Strategi 1-5).

### E.2 — LQ45 / IDX30 Tier Filter

Strategi current jalan ke semua 972 ticker. LQ45/IDX30 ticker punya liquidity profile sangat berbeda dari non-LQ45.

**Action**: tag setiap ticker dengan tier (LQ45/IDX30/MAIN/DEVELOPMENT) dan tune SL/TP per tier — non-LQ45 perlu SL lebih lebar karena spread + slippage tinggi.

### E.3 — ARA/ARB (Auto Rejection) Handling

IDX punya rule auto-rejection: harga gak boleh naik > 35% (ARA) atau turun > 20% (ARB) dalam 1 hari. Saat ini tidak ada handling.

**Action** di `paper_trade.py`:
- Saat compute TP, cap di ARA limit harian (jangan TP di 40% kalau ARA cuma allow 35%)
- Saat hit ARA, jangan auto-close immediately — wait sesi berikut karena suspended

### E.4 — Suspended Ticker Auto-Skip

Ticker yang suspended jangan masuk scan. Saat ini kemungkinan sudah handled di `data/fetcher.py`, tapi worth verify.

**Action**: tambah pre-scan check di `screener_jobs.py`:
```python
suspended_today = fetch_suspended_list_from_bei()
universe = [t for t in universe if t not in suspended_today]
```

---

## Prioritization Matrix (semua rekomendasi)

| Bucket | Item | Effort | Impact | Risk if skip |
|---|---|---|---|---|
| **P0 Fix** | A.1 Inside Bar reconcile | S | High | Silent backtest bias |
| **P0 Fix** | A.2 ORB rebuild/rename | M | Med | False confidence in strategy |
| **P1 Enhance** | A.3 Value Area helper + #6 variant | M | High | Leave alpha on table |
| **P1 Enhance** | C.3 DD circuit breaker | S | High | Catastrophic loss risk |
| **P1 Enhance** | C.1 Strategy correlation audit | S | Med | Hidden over-concentration |
| **P1 Enhance** | E.3 ARA/ARB cap handling | S | Med | Phantom TP that can't fill |
| **P2 New** | B.1 Bollinger Squeeze | M | Med | Optional alpha |
| **P2 New** | B.3 Pairs trading sektor | L | High | New strategy class |
| **P2 New** | A.4 Classical momentum filter | M | Med | Closes gap to literatur |
| **P2 New** | B.4 Hikkake reversal | S | Med | Complement #7 |
| **P3 Process** | D.1 Auto-research scheduler | S | Med | Strategi stagnan vs research baru |
| **P3 Process** | D.3 A/B test framework | M | Med | No structured way to iterate |
| **P3 Polish** | E.1 Foreign flow KPEI | L | Med | Missing institutional flow signal |
| **P3 Polish** | E.2 LQ45 tier-tuned SL/TP | M | Med | Sub-optimal sizing untuk small-cap |

**Quick win path** (1 week): A.1 + A.2 + C.3 + E.3 — semua S/M effort dengan High/Med impact.
**Strategic path** (1 month): tambahin P1 Enhance + A.3 implementation + 1 strategi baru B.x.
