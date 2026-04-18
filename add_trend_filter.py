#!/usr/bin/env python3
import shutil
from datetime import datetime

# Backup
shutil.copy2('paper_trade.py', f'paper_trade.py.trend_{datetime.now().strftime("%Y%m%d_%H%M%S")}')

# Add trend check function before open_trade
trend_function = '''
def check_trend(ticker: str) -> str:
    """
    Check trend direction.
    Returns: 'UPTREND', 'DOWNTREND', or 'SIDEWAYS'
    """
    import pandas as pd
    try:
        conn = get_db()
        df = pd.read_sql(
            'SELECT close FROM ohlcv WHERE ticker=? ORDER BY date DESC LIMIT 25',
            conn,
            params=(ticker,)
        )
        conn.close()
        
        if len(df) < 20:
            return 'UNKNOWN'
        
        df = df.iloc[::-1].reset_index(drop=True)  # Ascending
        df['ma20'] = df['close'].rolling(20).mean()
        
        # Latest values
        price = df['close'].iloc[-1]
        ma20_now = df['ma20'].iloc[-1]
        
        # MA20 slope (last 5 bars)
        ma20_slope = (df['ma20'].iloc[-1] - df['ma20'].iloc[-6]) / 5
        
        # Trend logic
        if price > ma20_now and ma20_slope > 0:
            return 'UPTREND'
        elif price < ma20_now and ma20_slope < 0:
            return 'DOWNTREND'
        else:
            return 'SIDEWAYS'
            
    except Exception as e:
        print(f"[check_trend] {ticker} error: {e}")
        return 'UNKNOWN'

'''

# Insert before open_trade function
with open('paper_trade.py', 'r') as f:
    content = f.read()

if 'def check_trend' not in content:
    content = content.replace('def open_trade(', trend_function + '\ndef open_trade(')
    with open('paper_trade.py', 'w') as f:
        f.write(content)
    print("✓ Added check_trend() function")
else:
    print("⊘ check_trend() already exists")
