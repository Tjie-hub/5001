#!/usr/bin/env python3
import shutil
from datetime import datetime

SCHEDULER = 'scheduler.py'
shutil.copy2(SCHEDULER, f'{SCHEDULER}.trend_{datetime.now().strftime("%Y%m%d_%H%M%S")}')

with open(SCHEDULER, 'r') as f:
    content = f.read()

# Find and replace the auto-trade section
old_code = '''            try:
                # Get latest price from signal details
                signal_details = r.get('signal_details', {})
                # Try first strategy's price
                first_strategy = r['strategies'][0]
                entry_price = signal_details.get(first_strategy, {}).get('price')
                
                if not entry_price:
                    print(f"[{time_str}] {ticker}: No price found, skipping")
                    continue
                
                # Open paper trade
                trade_result = open_trade(ticker, float(entry_price))'''

new_code = '''            try:
                # Get latest price from signal details
                signal_details = r.get('signal_details', {})
                first_strategy = r['strategies'][0]
                entry_price = signal_details.get(first_strategy, {}).get('price')
                
                if not entry_price:
                    print(f"[{time_str}] {ticker}: No price found, skipping")
                    continue
                
                # Check trend filter
                from paper_trade import check_trend
                trend = check_trend(ticker)
                
                if trend != 'UPTREND':
                    print(f"[{time_str}] {ticker}: Trend={trend}, skipping (not UPTREND)")
                    auto_trade_results.append({
                        'ticker': ticker,
                        'success': False,
                        'reason': f'Trend: {trend}'
                    })
                    continue
                
                # Open paper trade
                trade_result = open_trade(ticker, float(entry_price))'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(SCHEDULER, 'w') as f:
        f.write(content)
    print("✓ Added trend filter to auto-trade logic")
else:
    print("⊘ Code pattern not found or already patched")
