# Telegram Webhook Setup Guide

## Status: ✅ ACTIVATED

Telegram webhook integration is now enabled on **port 5001**.

## Quick Start

### 1. Start the Application
```bash
python app.py
```
The Flask app will run on `http://0.0.0.0:5001`

### 2. Configure Telegram Webhook
Open in browser (replace IP with your server IP):
```
http://192.168.31.120:5001/telegram/setup
```

Or via curl:
```bash
curl http://192.168.31.120:5001/telegram/setup
```

Expected response:
```json
{
  "success": true,
  "message": "Telegram webhook activated",
  "webhook_url": "http://192.168.31.120:5001/telegram/updates"
}
```

### 3. Check Webhook Status
```
http://192.168.31.120:5001/telegram/status
```

## Available Telegram Commands

Once activated, use these commands in your Telegram bot:

| Command | Description |
|---------|-------------|
| `/start` | Initialize bot |
| `/status` | Get trading system status |
| `/signals` | View recent trading signals |
| `/flow` | Check broker flow status |
| `/help` | Show available commands |

## Environment Variables (Optional)

Set in `.env` file:
```env
TELEGRAM_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
WEBHOOK_URL=http://192.168.31.120:5001
WEBHOOK_PATH=/telegram/updates
```

## API Endpoints

### Webhook Receiver
- **POST** `/telegram/updates` - Receives updates from Telegram

### Setup
- **GET** `/telegram/setup` - Configure webhook (one-time)

### Status
- **GET** `/telegram/status` - Check webhook status

### Send Messages
- Direct call: `send_telegram(message)` in Python code

## Architecture

```
Telegram User Message
        ↓
Telegram Servers
        ↓
POST to http://your-ip:5001/telegram/updates
        ↓
Flask Handler Process Message
        ↓
Response (inline reply or new message)
```

## Testing

### Send test message via API
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

## Troubleshooting

### Webhook not connecting?
1. Check firewall rules - port 5001 must be open
2. Verify WEBHOOK_URL is reachable from internet
3. Check /telegram/status for errors

### Messages not received?
1. Run `/telegram/setup` again
2. Check bot token in TELEGRAM_TOKEN env var
3. View console output for debug messages

### SSL Certificate Issues
For production, use HTTPS with proper SSL certificates, or use a reverse proxy like nginx.

## Features

✅ Receive messages from Telegram  
✅ Send automated notifications  
✅ Execute commands via bot  
✅ Query trading status  
✅ Real-time updates  
✅ Bidirectional communication  

## Notes

- Default token and chat ID are pre-configured (if environment is set)
- Webhook will retry on failure
- Port 5001 must be accessible from Telegram servers
- For production, use HTTPS with domain name
