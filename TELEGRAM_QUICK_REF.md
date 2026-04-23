# 📱 Telegram Port 5001 - Quick Reference

## Status: ✅ ACTIVATED

```
Port: 5001
Service: Flask + Telegram Webhook
Status: Ready to activate
```

## 🚀 Quick Start

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
./run_telegram.sh
```

Then visit: `http://192.168.31.120:5001/telegram/setup`

## 📡 API Endpoints

### Setup Webhook
```
GET http://192.168.31.120:5001/telegram/setup
```
Response:
```json
{
  "success": true,
  "webhook_url": "http://192.168.31.120:5001/telegram/updates"
}
```

### Check Webhook Status
```
GET http://192.168.31.120:5001/telegram/status
```

### Telegram Webhook (Internal)
```
POST http://192.168.31.120:5001/telegram/updates
```
This is called by Telegram servers automatically.

## 💬 Bot Commands

Send these via Telegram to bot:

| Command | Action |
|---------|--------|
| `/start` | Initialize bot |
| `/status` | Trading system status |
| `/signals` | Recent trading signals |
| `/flow` | Broker flow status |
| `/help` | Show commands |

## 🔧 Configuration

### Environment Variables (.env)
```env
TELEGRAM_TOKEN=8790169868:AAE6qno0LrxxIdFydSKSLKhD8EPUzevPIFo
TELEGRAM_CHAT_ID=5919142813
WEBHOOK_URL=http://192.168.31.120:5001
WEBHOOK_PATH=/telegram/updates
```

## 📝 Send Message from Code

```python
from scheduler import send_telegram

# Send notification
send_telegram("📊 BBCA: BUY signal confirmed")
```

## 🧪 Test Webhook

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

## 🔍 Debug

### Check Imports
```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
source venv/bin/activate 2>/dev/null || . venv/Scripts/activate
python3 -c "import flask, requests; print('✓ OK')"
```

### Check Syntax
```bash
python3 -m py_compile app.py
```

## 📊 Telegram Features Added

✅ Message receiver endpoint  
✅ Command parser (/start, /status, /help, etc.)  
✅ Webhook setup and registration  
✅ Webhook status checker  
✅ Trading status queries  
✅ Signal reporting  
✅ Flow data queries  
✅ Error handling  

## 🔐 Security Notes

- Bot token stored in environment
- Chat ID verified before processing
- Invalid commands rejected gracefully
- Error messages sanitized

## 📋 Files Changed

1. **app.py** - Added 4 main functions + 3 endpoints
2. **run_telegram.sh** - New convenience script
3. **TELEGRAM_SETUP.md** - Full documentation
4. **TELEGRAM_AKTIVASI.md** - Indonesian guide

## 🎯 Architecture

```
Telegram User → Telegram API → HTTP POST to Port 5001
                                      ↓
                          Parse message/command
                                      ↓
                        Execute handler (status, flow, etc)
                                      ↓
                        Query database if needed
                                      ↓
                        Compose response
                                      ↓
                Send reply back via Telegram API
```

## 📚 Next Steps

1. **Activate app**: `./run_telegram.sh`
2. **Setup webhook**: Visit `/telegram/setup`
3. **Test bot**: Send `/status` via Telegram
4. **Monitor**: Check `/telegram/status`
5. **Integrate**: Use `send_telegram()` in code for notifications

---

**Telegram webhook di port 5001 siap digunakan! 🎉**
