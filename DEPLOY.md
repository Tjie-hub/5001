# DEPLOY GUIDE — Multi-Strategy Backtest
## Integrasi ke idx-walkforward (port 5001)

### 1. Copy File ke Ubuntu Server

```bash
# Dari machine lain / SCP
scp engine/strategies.py       tjiesar@192.168.31.120:/home/tjiesar/idx-walkforward/engine/
scp engine/walkforward_multi.py tjiesar@192.168.31.120:/home/tjiesar/idx-walkforward/engine/
scp routes_backtest_multi.py   tjiesar@192.168.31.120:/home/tjiesar/idx-walkforward/
scp templates/backtest_multi.html tjiesar@192.168.31.120:/home/tjiesar/idx-walkforward/templates/
```

---

### 2. Edit app.py idx-walkforward

Tambahkan 2 baris ini di `app.py`:

```python
# ── TAMBAHKAN setelah import lain ──
from routes_backtest_multi import backtest_multi_bp
app.register_blueprint(backtest_multi_bp)

# ── TAMBAHKAN route halaman UI ──
@app.route('/backtest/multi')
def backtest_multi_page():
    return render_template('backtest_multi.html')
```

---

### 3. Pastikan DB Path Benar

Di `routes_backtest_multi.py` line 16:
```python
DB_PATH = 'data/walkforward.db'
```
Sesuaikan dengan path database idx-walkforward yang aktual.
Cek dengan: `ls /home/tjiesar/idx-walkforward/data/`

---

### 4. Restart Service

```bash
sudo systemctl restart idx-walkforward
sudo systemctl status  idx-walkforward
```

---

### 5. Akses Dashboard

```
http://192.168.31.120:5001/backtest/multi
```

---

### 6. Test API Manual (optional)

```bash
# Full backtest
curl -s -X POST http://localhost:5001/api/backtest/multi \
  -H "Content-Type: application/json" \
  -d '{"ticker":"BBCA","capital":50000000}' | python3 -m json.tool

# Walk-forward
curl -s -X POST http://localhost:5001/api/backtest/walkforward \
  -H "Content-Type: application/json" \
  -d '{"ticker":"BBCA","capital":50000000}' | python3 -m json.tool
```

---

## File Summary

| File | Lokasi di idx-walkforward | Fungsi |
|------|--------------------------|--------|
| `engine/strategies.py` | `/engine/strategies.py` | 4 strategy definitions + backtest engine |
| `engine/walkforward_multi.py` | `/engine/walkforward_multi.py` | Walk-forward + metrics + ranking |
| `routes_backtest_multi.py` | `/routes_backtest_multi.py` | Flask blueprint (4 API endpoints) |
| `templates/backtest_multi.html` | `/templates/backtest_multi.html` | Dashboard UI |

## API Endpoints (baru)

| Method | Path | Fungsi |
|--------|------|--------|
| POST | `/api/backtest/multi` | Full backtest 4 strategi |
| POST | `/api/backtest/walkforward` | Walk-forward analysis |
| POST | `/api/backtest/equity` | Equity curve data untuk chart |
| GET  | `/api/backtest/trades/<ticker>/<strategy>` | Trade log per strategi |
| GET  | `/backtest/multi` | Dashboard HTML |

---

## Catatan Teknis

**Strategies:**
1. **Vol-Weighted Entry** — Vol Ratio > 2.0x + Delta positif → TP 2% / SL 1.5%
2. **Momentum Following** — 2 hari streak naik + Vol 1.3x → Trailing SL 2% dari peak
3. **VWAP Reversion** — Harga > 1.5% di bawah VWAP + Vol spike → TP 1.5% / SL 1%
4. **Conservative Confirm** — Vol 1.5x + bullish + above MA20 + ATR normal → TP 1.5% / SL 1%

**Costs included:** Commission buy 0.15%, sell 0.25%, slippage 0.1%

**Walk-Forward:** Train 12 bln → Test 3 bln → Rolling 3 bln step
