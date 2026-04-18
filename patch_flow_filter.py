#!/usr/bin/env python3
"""
Auto-patch script: Add flow filter integration to idx-walkforward app.py
Usage: python3 patch_flow_filter.py
"""

import os
import re
import shutil
from datetime import datetime

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Configuration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

APP_PY = "/home/tjiesar/idx-walkforward/app.py"
BACKUP_SUFFIX = f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Code snippets to insert
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IMPORT_FLOW = "from flow_filter import get_flow_confirmation, get_flow_batch"

HELPER_FUNCTION = '''
def attach_flow_data(results, include_flow=True, flow_threshold=2):
    """
    Attach flow data to scan results.
    
    Args:
        results: List of dicts with ticker + signal data
        include_flow: Whether to fetch flow data
        flow_threshold: Minimum flow score to mark as confirmed (+2 default)
    
    Returns:
        results with added 'flow' key for each ticker
    """
    if not include_flow:
        return results
    
    # Extract unique tickers
    tickers = list(set(r['ticker'] for r in results if 'ticker' in r))
    if not tickers:
        return results
    
    # Batch fetch flow data
    try:
        flow_data = get_flow_batch(tickers, token=None, delay=0.8)
    except Exception as e:
        print(f"Flow fetch error: {e}")
        flow_data = {}
    
    # Attach to results
    for r in results:
        ticker = r.get('ticker')
        if not ticker:
            continue
            
        if ticker in flow_data:
            flow = flow_data[ticker]
            r['flow'] = {
                'available': True,
                'score': flow['score'],
                'verdict': flow['verdict'],
                'smart_money': flow['smart_money'],
                'cum_delta': flow['cum_delta'],
                'price_chg_pct': flow['price_chg_pct'],
                'confirmed': flow['score'] >= flow_threshold,  # +2 threshold
                'timestamp': flow['timestamp']
            }
        else:
            # No flow data available
            r['flow'] = {
                'available': False,
                'score': None,
                'verdict': 'UNAVAILABLE',
                'smart_money': None,
                'confirmed': None,
                'reason': 'Data not available or token expired'
            }
    
    return results
'''

NEW_ENDPOINT = '''
@app.route('/api/flow/check', methods=['POST'])
def check_flow():
    """
    Standalone flow check endpoint.
    
    POST body:
        {
            "tickers": ["BRPT", "BBCA"],
            "threshold": 2
        }
    
    Returns flow data for requested tickers.
    """
    data = request.get_json()
    tickers = data.get('tickers', [])
    threshold = data.get('threshold', 2)
    
    if not tickers:
        return jsonify({'success': False, 'error': 'No tickers provided'}), 400
    
    try:
        flow_data = get_flow_batch(tickers, token=None, delay=0.8)
        
        results = []
        for ticker in tickers:
            if ticker in flow_data:
                flow = flow_data[ticker]
                results.append({
                    'ticker': ticker,
                    'score': flow['score'],
                    'verdict': flow['verdict'],
                    'smart_money': flow['smart_money'],
                    'confirmed': flow['score'] >= threshold,
                    'details': flow
                })
            else:
                results.append({
                    'ticker': ticker,
                    'score': None,
                    'verdict': 'UNAVAILABLE',
                    'confirmed': None
                })
        
        return jsonify({
            'success': True,
            'threshold': threshold,
            'results': results,
            'total': len(results)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
'''

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Patching functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def backup_file(filepath):
    """Create backup of original file."""
    backup = filepath + BACKUP_SUFFIX
    shutil.copy2(filepath, backup)
    print(f"✓ Backup created: {backup}")
    return backup


def add_import(content):
    """Add flow_filter import after engine.strategies import."""
    if IMPORT_FLOW in content:
        print("⊘ Flow import already exists, skipping")
        return content
    
    # Find last import from engine
    pattern = r'(from engine\.strategies import.*?\n)'
    match = re.search(pattern, content)
    
    if match:
        insert_pos = match.end()
        content = content[:insert_pos] + IMPORT_FLOW + "\n" + content[insert_pos:]
        print("✓ Added flow_filter import")
    else:
        print("⚠ Could not find engine.strategies import, adding at top")
        content = IMPORT_FLOW + "\n" + content
    
    return content


def add_helper_function(content):
    """Add attach_flow_data helper before first @app.route."""
    if "def attach_flow_data" in content:
        print("⊘ Helper function already exists, skipping")
        return content
    
    # Find first @app.route
    pattern = r'(@app\.route)'
    match = re.search(pattern, content)
    
    if match:
        insert_pos = match.start()
        content = content[:insert_pos] + HELPER_FUNCTION + "\n\n" + content[insert_pos:]
        print("✓ Added attach_flow_data helper function")
    else:
        print("✗ Could not find @app.route, cannot add helper")
    
    return content


def add_new_endpoint(content):
    """Add /api/flow/check endpoint at end of file."""
    if "@app.route('/api/flow/check'" in content:
        print("⊘ Flow check endpoint already exists, skipping")
        return content
    
    # Add before final if __name__ == '__main__'
    pattern = r'(if __name__ == ["\']__main__["\']:)'
    match = re.search(pattern, content)
    
    if match:
        insert_pos = match.start()
        content = content[:insert_pos] + NEW_ENDPOINT + "\n\n" + content[insert_pos:]
        print("✓ Added /api/flow/check endpoint")
    else:
        # Just append at end
        content = content + "\n\n" + NEW_ENDPOINT
        print("✓ Added /api/flow/check endpoint (at end)")
    
    return content


def modify_quick_scan(content):
    """Modify /api/backtest/quick_scan to include flow data."""
    # Find the endpoint
    pattern = r"(@app\.route\('/api/backtest/quick_scan'.*?def quick_scan\(\):.*?)(return jsonify\(\{[^}]*'success': True.*?\}\))"
    
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        print("⚠ Could not find quick_scan endpoint return statement")
        return content
    
    if "attach_flow_data" in match.group(0):
        print("⊘ quick_scan already has flow integration, skipping")
        return content
    
    # Insert flow attachment code before return
    insertion = '''
    # Attach flow data (optional mode - display only, no filtering)
    include_flow = data.get('include_flow', True)  # Default: include
    flow_threshold = data.get('flow_threshold', 2)  # Default: +2
    
    results = attach_flow_data(results, include_flow, flow_threshold)
    '''
    
    new_return = '''return jsonify({
        'success': True,
        'strategy': strategy,
        'filter_mode': filter_mode,
        'results': results,
        'total': len(results),
        'flow_enabled': include_flow,
        'flow_threshold': flow_threshold
    })'''
    
    # Replace just the return statement section
    old_section = match.group(0)
    new_section = match.group(1) + insertion + "\n    " + new_return
    
    content = content.replace(old_section, new_section)
    print("✓ Modified quick_scan endpoint")
    
    return content


def modify_multi_quick_scan(content):
    """Modify /api/backtest/multi_quick_scan to include flow data."""
    pattern = r"(@app\.route\('/api/backtest/multi_quick_scan'.*?def multi_quick_scan\(\):.*?)(return jsonify\(\{[^}]*'success': True.*?\}\))"
    
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        print("⚠ Could not find multi_quick_scan endpoint return statement")
        return content
    
    if "attach_flow_data" in match.group(0):
        print("⊘ multi_quick_scan already has flow integration, skipping")
        return content
    
    insertion = '''
    # Attach flow data (optional mode - display only, no filtering)
    include_flow = data.get('include_flow', True)
    flow_threshold = data.get('flow_threshold', 2)
    
    if intersection_mode:
        # For intersection mode: results is already flat list
        results = attach_flow_data(results, include_flow, flow_threshold)
    else:
        # For union mode: results is dict {strategy: [tickers]}
        for strategy in results:
            results[strategy] = attach_flow_data(
                results[strategy], 
                include_flow, 
                flow_threshold
            )
    '''
    
    new_return = '''return jsonify({
        'success': True,
        'strategies': strategies,
        'filter_mode': filter_mode,
        'intersection_mode': intersection_mode,
        'results': results,
        'total': len(results) if intersection_mode else sum(len(v) for v in results.values()),
        'flow_enabled': include_flow,
        'flow_threshold': flow_threshold
    })'''
    
    old_section = match.group(0)
    new_section = match.group(1) + insertion + "\n    " + new_return
    
    content = content.replace(old_section, new_section)
    print("✓ Modified multi_quick_scan endpoint")
    
    return content


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main execution
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    print("=" * 60)
    print("Flow Filter Integration Patcher")
    print("=" * 60)
    
    if not os.path.exists(APP_PY):
        print(f"✗ Error: {APP_PY} not found")
        return 1
    
    # Backup
    backup_file(APP_PY)
    
    # Read content
    with open(APP_PY, 'r') as f:
        content = f.read()
    
    print("\nApplying patches...")
    print("-" * 60)
    
    # Apply all patches
    content = add_import(content)
    content = add_helper_function(content)
    content = modify_quick_scan(content)
    content = modify_multi_quick_scan(content)
    content = add_new_endpoint(content)
    
    # Write back
    with open(APP_PY, 'w') as f:
        f.write(content)
    
    print("-" * 60)
    print("✓ Patching complete!")
    print("\nNext steps:")
    print("  1. sudo systemctl restart idx-walkforward")
    print("  2. sudo journalctl -u idx-walkforward -f")
    print("  3. Test: http://192.168.31.120:5001/signal-scanner")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    exit(main())
