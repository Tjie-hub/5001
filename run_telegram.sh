#!/bin/bash
# Telegram Webhook Activation Script for IDX Walkforward

PROJECT_DIR="/home/tjiesar/10 Projects/idx-walkforward-5001"
cd "$PROJECT_DIR" || exit 1

echo "🚀 IDX Walkforward - Telegram Port 5001 Activation"
echo "=================================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Creating..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate 2>/dev/null || . venv/Scripts/activate

# Check required packages
echo "📦 Checking dependencies..."
pip list | grep -q "Flask" && echo "✅ Flask installed" || echo "❌ Flask missing"
pip list | grep -q "requests" && echo "✅ requests installed" || echo "❌ requests missing"

echo ""
echo "🔧 Configuration:"
echo "  - Port: 5001"
echo "  - Webhook: /telegram/updates"
echo "  - Setup: /telegram/setup"
echo "  - Status: /telegram/status"
echo ""

# Start the application
echo "🌐 Starting Flask app on port 5001..."
echo "   URL: http://localhost:5001"
echo "   Setup Telegram: http://localhost:5001/telegram/setup"
echo ""
echo "Press Ctrl+C to stop"
echo "=================================================="
echo ""

python3 app.py

