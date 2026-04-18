#!/usr/bin/env python3
"""
Adaptive Strategy Selection per Ticker
Each ticker uses its best-performing strategies from WF scores
"""
import shutil
from datetime import datetime

SCHEDULER = 'scheduler.py'
shutil.copy2(SCHEDULER, f'{SCHEDULER}.adaptive_{datetime.now().strftime("%Y%m%d_%H%M%S")}')

# New function to get best strategies per ticker
NEW_FUNCTION = '''
def get_ticker_best_strategies(ticker: str, min_consistency: float = 50.0):
    """
    Get best strategies for ticker from WF scores.
    Returns list of strategies with consistency >= min_consistency.
    """
    import sqlite3
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("""
            SELECT strategy, consistency_pct, weighted_score
            FROM wf_scores
            WHERE ticker = ? AND consistency_pct >= ?
            ORDER BY weighted_score DESC
        """, (ticker, min_consistency)).fetchall()
        conn.close()
        
        if not rows:
            # Fallback: use default strategies
            return ["vol_weighted", "vwap_reversion"]
        
        return [r[0] for r in rows]
    except Exception as e:
        print(f"[get_best_strategies] {ticker} error: {e}")
        return ["vol_weighted", "vwap_reversion"]  # Fallback

'''

# Replace the scan logic
OLD_SCAN_LOGIC = '''    # Config
    strategies = ["vol_weighted", "vwap_reversion"]
    flow_threshold = 2  # Score >= +2 to confirm
    
    # Get all tickers
    tickers = get_all_tickers()
    
    # Step 1: Collect signals per ticker per strategy
    ticker_signals = {}
    
    for ticker in tickers:
        try:
            df = get_ticker_data(ticker)
            if df is None or len(df) < 20:
                continue
            
            ticker_signals[ticker] = {}
            
            for strategy in strategies:
                signal_check = check_current_entry_signal(ticker, strategy, df)
                ticker_signals[ticker][strategy] = signal_check
        except Exception as e:
            print(f"[Scan] {ticker} error: {e}")
            continue
    
    # Step 2: Filter - intersection mode (pass ALL strategies)
    intersection_results = []
    
    for ticker, signals in ticker_signals.items():
        # Skip if not all strategies present
        if len(signals) < len(strategies):
            continue
        
        # Check if ALL strategies have signal
        all_pass = all(signals[s]['has_signal'] for s in strategies)
        
        if not all_pass:
            continue
        
        # Combine signal info
        combined_reasons = []
        combined_details = {}
        
        for strategy in strategies:
            sig = signals[strategy]
            combined_reasons.append(f"{strategy}: {sig['reason']}")
            combined_details[strategy] = sig['details']
        
        intersection_results.append({
            'ticker': ticker,
            'strategies': strategies,
            'has_signal': True,
            'signal_reasons': combined_reasons,
            'signal_details': combined_details
        })'''

NEW_SCAN_LOGIC = '''    # Config
    flow_threshold = 2  # Score >= +2 to confirm
    min_wf_consistency = 50.0  # Minimum WF consistency %
    
    # Get all tickers
    tickers = get_all_tickers()
    
    # Step 1: Adaptive strategy selection per ticker
    adaptive_results = []
    
    for ticker in tickers:
        try:
            df = get_ticker_data(ticker)
            if df is None or len(df) < 20:
                continue
            
            # Get best strategies for this ticker from WF scores
            best_strategies = get_ticker_best_strategies(ticker, min_wf_consistency)
            
            # Check signals for best strategies
            passing_strategies = []
            combined_reasons = []
            combined_details = {}
            
            for strategy in best_strategies:
                signal_check = check_current_entry_signal(ticker, strategy, df)
                
                if signal_check['has_signal']:
                    passing_strategies.append(strategy)
                    combined_reasons.append(f"{strategy}: {signal_check['reason']}")
                    combined_details[strategy] = signal_check['details']
            
            # If ANY best strategy has signal → add to results
            if len(passing_strategies) > 0:
                adaptive_results.append({
                    'ticker': ticker,
                    'strategies': passing_strategies,  # Only passing ones
                    'has_signal': True,
                    'signal_reasons': combined_reasons,
                    'signal_details': combined_details
                })
                
        except Exception as e:
            print(f"[Scan] {ticker} error: {e}")
            continue
    
    # Rename for compatibility with rest of code
    intersection_results = adaptive_results'''

# Apply patches
with open(SCHEDULER, 'r') as f:
    content = f.read()

if 'def get_ticker_best_strategies' not in content:
    # Insert function before scheduled_multi_strategy_scan
    content = content.replace(
        'def scheduled_multi_strategy_scan():',
        NEW_FUNCTION + '\ndef scheduled_multi_strategy_scan():'
    )
    print("✓ Added get_ticker_best_strategies() function")
else:
    print("⊘ Function already exists")

if OLD_SCAN_LOGIC in content:
    content = content.replace(OLD_SCAN_LOGIC, NEW_SCAN_LOGIC)
    print("✓ Replaced with adaptive strategy logic")
elif "adaptive_results" in content:
    print("⊘ Adaptive logic already applied")
else:
    print("⚠ Could not find scan logic to replace")

# Update summary text
content = content.replace(
    'print(f"[{time_str}] Strategy intersection:',
    'print(f"[{time_str}] Adaptive strategy signals:'
)

with open(SCHEDULER, 'w') as f:
    f.write(content)

print("\n✓ Adaptive strategy patch complete!")
print("\nChanges:")
print("  - Per-ticker strategy selection (WF >= 50%)")
print("  - Combine passing strategies into 1 trade")
print("  - DB strategy field: comma-separated")
