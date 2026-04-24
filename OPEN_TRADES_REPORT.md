# Open Trades Status Report

**Purpose:** Automatic daily report of all open paper trades with current P&L, price changes, and distance to TP/SL levels.

---

## 📊 Report Features

Each report includes:

✅ **Per-Trade Details:**
- Current price vs entry price
- Price change (Rp and %)
- Distance to TP (+%)
- Distance to SL (%)
- Current P&L (Rp and %)

✅ **Summary:**
- Total capital allocated
- Total P&L (Rp)
- Total return (%)
- Breakdown: Profit/Loss/Breakeven trades

✅ **Visual Indicators:**
- 🟢 Green = Profitable trades
- 🔴 Red = Losing trades
- ⚪ Neutral = Breakeven

---

## 📅 Automatic Schedule

Reports are sent automatically **4x per trading day:**

| Time | Status |
|------|--------|
| 10:30 WIB | Mid-morning check |
| 12:30 WIB | Lunch-time check |
| 14:30 WIB | Afternoon check |
| 16:30 WIB | Pre-close check |

**Runs:** Monday-Friday only

---

## 🔧 Manual Trigger

Send report immediately on-demand via API:

```bash
curl -X POST http://localhost:5001/api/paper/report-telegram
```

Response:
```json
{
  "success": true,
  "message": "Report sent to Telegram"
}
```

---

## 📋 Example Report

```
📊 Open Trades Report — 16:30

🔴 LSIP @ Rp 1,670
   Entry: Rp 1,700 | Change: -1.76% (-30)
   📈 TP: Rp 1,829 (-23.3%)
   🛑 SL: Rp 1,635 (46.2%)
   💰 P&L: Rp -264,000 (-1.76%)

🟢 AALI @ Rp 1,500
   Entry: Rp 1,450 | Change: +3.45% (+50)
   📈 TP: Rp 1,650 (+55.2%)
   🛑 SL: Rp 1,400 (44.8%)
   💰 P&L: Rp +300,000 (+3.45%)

📈 Summary (2 trades):
   Total Capital: Rp 100,000,000
   Total P&L: Rp +36,000
   Total Return: +0.04%

   ✅ Profit: 1 | ❌ Loss: 1 | ⚪ Breakeven: 0
```

---

## 🔍 Key Metrics Explained

### Price Change
Shows current price vs entry price in Rp and percentage.

### % to TP (Take Profit)
- Percentage of the way from entry to TP
- Negative = below target (not yet reached)
- Positive = at or past target

### % to SL (Stop Loss)
- Percentage of distance remaining before hitting SL
- Lower % = closer to stop loss (higher risk)
- Higher % = further from stop loss (more room)

### P&L (Profit & Loss)
- Total unrealized profit/loss for the position
- Calculated as: (Current - Entry) × Lots × 100
- % shows return on entry price

---

## 🚨 Troubleshooting

### Report not received in Telegram?

1. **Check Telegram token validity:**
   ```bash
   grep TELEGRAM_TOKEN .env
   ```

2. **Manual test of send function:**
   ```bash
   curl -X POST http://localhost:5001/api/paper/report-telegram
   ```

3. **Check Telegram token in scheduler:**
   - Look for "ISI_" prefix in token (indicates placeholder)
   - Should be actual Telegram bot token

4. **Verify scheduler is running:**
   ```bash
   ps aux | grep scheduler
   # or check for running Flask app
   ps aux | grep python | grep app.py
   ```

---

## 📝 Configuration

No configuration needed. The report uses existing paper trading configuration:
- Capital amount (default: Rp 50,000,000)
- TP and SL settings from respective trade entries
- All trades with `status='OPEN'`

---

## 🔗 Related Features

- **Paper Trade Opening:** `/api/paper/open` (POST)
- **Paper Trade Closing:** `/api/paper/close` (POST)
- **Paper Trade Summary:** `/api/paper/summary` (GET)
- **Trade Monitoring:** Built-in monitor checks trades every 30 min

---

**Last Updated:** 2026-04-24
**Version:** 1.0
