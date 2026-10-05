# atr_plan — ATR exits vs fixed % (idx-walkforward-5001)

Standalone. Tidak menyentuh `data/walkforward.db` atau kode engine.

## Install (Ubuntu, XPS)

```bash
cd /home/tjiesar/idx-walkforward-5001
unzip ~/Downloads/atr_plan.zip -d .          # -> ./atr_plan/
source venv/bin/activate 2>/dev/null || true # kalau pakai venv
pip install yfinance pandas numpy tabulate
```

## Urutan jalan

```bash
# 0. unit test (harus semua "ok")
python atr_plan/test_atr_exits.py

# 1. null test — harness harus netral di random walk
python atr_plan/null_test.py
#    cek reports/null_test/*/summary.md bagian 2, baris "ohlc":
#    mean Δ/trade B/C vs A harus ≈ 0 (CI melewati 0). Kalau tidak, STOP dan kabari.

# 2. tarik histori 2010+ ke db terpisah (~87 ticker, ~2–3 menit)
python atr_plan/fetch_history.py --from-db data/walkforward.db
#    kalau ticker tidak ketemu: buat tickers.txt (satu kode per baris) lalu
#    python atr_plan/fetch_history.py --tickers-file tickers.txt
#    update harian nanti: tambah --update

# 3. perbandingan exit (~3–5 menit)
python atr_plan/exit_compare.py --db data/history_long.db
python atr_plan/exit_compare.py --db data/history_long.db --cost-filter   # skip ATR% < 1.6%
```

Output: `reports/exit_compare_YYYYMMDD_HHMM/` → `summary.md`, `verdict.csv`, `windows.csv`, `trades.csv`.

## Cara baca `summary.md`

- **BETTER_THAN_A**: menang atas fixed % di ≥70% tahun DAN 95% CI bootstrap > 0, di kedua konvensi same-bar (`stop_first` pesimis, `ohlc` netral).
- **PROFITABLE**: rata-rata net/trade > 0 pada cost 0.8%.
- Adopsi exit baru hanya kalau **BETTER_THAN_A = YES**. Kalau PROFITABLE = no, exit-nya lebih baik tapi strateginya tetap tidak punya edge. Masalahnya di entry, bukan di exit.

## Varian

| | Mean-reversion (vwap_rev, conservative) | Momentum (vol_weighted, momentum, nr7) |
|---|---|---|
| A | fixed % sekarang, max hold 20 | fixed % sekarang, max hold 20 |
| B | SL 1.5×ATR14, TP 1.5×ATR14, time stop 5 bar | SL 2×ATR14, TP 3×ATR14, max 20 |
| C | = B | SL 2×ATR14 + chandelier HH22 − 3×ATR22 (close → next open), max 60 |
| D | — | C + sizing 0.75% risk, cap 30% (hanya di tabel portfolio) |

## Batasan (penting)

- Entry di `exit_compare.py` adalah **aproksimasi** dari spec 5 strategi, bukan kode asli `engine/strategies.py`. Untuk keputusan final, sambungkan ke entry asli (lihat `CLAUDE_CODE_PROMPT.md`).
- Close dari yfinance sudah split-adjusted, jadi harga sebelum split bukan harga asli. Pembulatan tick untuk periode itu hanya aproksimasi.
- Universe = daftar ticker hari ini → ada survivorship bias.
- Rezim ARB berubah (Apr 2025: 15%, 2027: simetris). Lihat `windows.csv` per tahun, jangan hanya total.
