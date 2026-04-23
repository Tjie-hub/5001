# Telegram Port 5001 - Aktivasi Selesai ✅

## Status: Telegram webhook sudah diaktifkan di port 5001

### Apa yang Ditambahkan

#### 1. **Telegram Webhook Handler** (`app.py`)
   - Endpoint: `POST /telegram/updates` - Menerima update dari Telegram
   - Endpoint: `GET /telegram/setup` - Setup webhook (jalankan sekali)
   - Endpoint: `GET /telegram/status` - Check status webhook

#### 2. **Command Processing**
   Telegram bot sekarang mendukung perintah:
   - `/start` - Initialize bot
   - `/status` - Status trading system
   - `/signals` - Lihat signals terbaru
   - `/flow` - Status broker flow
   - `/help` - Bantuan

#### 3. **Message Handling**
   - Bot menerima dan memproses pesan dari Telegram
   - Mengirim reply ke user
   - Dapat diintegrasikan dengan sistem trading

### Cara Menggunakan

#### **Opsi 1: Menggunakan Script**
```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
./run_telegram.sh
```

#### **Opsi 2: Manual**
```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
source venv/bin/activate
python app.py
```

### Setup Telegram Webhook

Setelah aplikasi berjalan, setup webhook dengan membuka di browser:
```
http://192.168.31.120:5001/telegram/setup
```

Atau via curl:
```bash
curl http://192.168.31.120:5001/telegram/setup
```

Response sukses:
```json
{
  "success": true,
  "message": "Telegram webhook activated",
  "webhook_url": "http://192.168.31.120:5001/telegram/updates"
}
```

### Verifikasi Setup

Cek status webhook:
```
http://192.168.31.120:5001/telegram/status
```

### API Endpoints yang Tersedia

| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| POST | `/telegram/updates` | Webhook receiver |
| GET | `/telegram/setup` | Setup webhook |
| GET | `/telegram/status` | Check webhook status |

### Struktur Komunikasi

```
┌─────────────────────────────────────────────────────┐
│ User mengirim pesan ke Telegram Bot                 │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
         Telegram Servers
                   │
                   ▼
    POST to 192.168.31.120:5001/telegram/updates
                   │
                   ▼
         Flask App (Port 5001)
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
      Process  Database   Telegram API
       Input   Query      Reply
        │          │          │
        └──────────┼──────────┘
                   ▼
    POST back ke Telegram Server
                   │
                   ▼
         Bot replies to user
```

### Konfigurasi (Optional)

Edit `.env` file untuk customisasi:
```env
TELEGRAM_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
WEBHOOK_URL=http://192.168.31.120:5001
WEBHOOK_PATH=/telegram/updates
```

### Testing

Test dengan curl:
```bash
curl -X POST http://192.168.31.120:5001/telegram/updates \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "chat": {"id": 5919142813},
      "text": "/status"
    }
  }'
```

### Troubleshooting

| Problem | Solusi |
|---------|--------|
| Webhook tidak connect | Port 5001 harus terbuka di firewall |
| Telegram tidak terima pesan | Check WEBHOOK_URL bisa diakses dari internet |
| Token error | Verify TELEGRAM_TOKEN di .env atau scheduler.py |
| Webhook setup gagal | Run `/telegram/setup` lagi atau check log |

### Integrasi dengan Trading System

Untuk mengirim notifikasi trading:
```python
from scheduler import send_telegram

# Dalam app.py atau scheduler.py
send_telegram("📊 Trade Opened: BBCA @20000, SL:19500, TP:21000")
```

### Files Modified

1. **app.py** - Added Telegram webhook handlers dan command processors
2. **TELEGRAM_SETUP.md** - Documentation lengkap
3. **run_telegram.sh** - Convenience script untuk start app

### Port 5001 Features

✅ Menjalankan Flask web app (sudah ada sebelumnya)
✅ Menerima Telegram webhook updates (BARU)
✅ Mengirim Telegram notifications (sudah ada)
✅ Bidirectional communication dengan Telegram

### Next Steps

1. Run aplikasi: `./run_telegram.sh`
2. Setup webhook: `http://192.168.31.120:5001/telegram/setup`
3. Test bot: Kirim `/status` ke Telegram bot
4. Monitor: Check `/telegram/status` untuk webhook health

---

**Telegram integration pada port 5001 sudah siap digunakan! 🚀**
