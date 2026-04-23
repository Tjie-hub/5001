#!/usr/bin/env python3
"""
Targeted patch: Modify endpoint return statements to include flow data
Usage: python3 patch_endpoints.py
"""

import os
import shutil
from datetime import datetime

APP_PY = "/home/tjiesar/10 Projects/idx-walkforward-5001/app.py"
BACKUP_SUFFIX = f".backup_endpoints_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Patch 1: api_quick_scan
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OLD_QUICK_SCAN_RETURN = """    tickers_with_signal = sum(1 for r in results if r['has_signal'])
    
    return jsonify({
        'success': True,
        'results': results,
        'summary': {
            'total_tickers_scanned': len(tickers),
            'tickers_with_signal': tickers_with_signal,
            'tickers_displayed': len(results),
            'filter_mode': filter_mode,
            'strategy': strategy
        }
    })"""

NEW_QUICK_SCAN_RETURN = """    tickers_with_signal = sum(1 for r in results if r['has_signal'])
    
    # Attach flow data (optional mode - display only, no filtering)
    include_flow = body.get('include_flow', True)
    flow_threshold = body.get('flow_threshold', 2)
    results = attach_flow_data(results, include_flow, flow_threshold)
    
    return jsonify({
        'success': True,
        'results': results,
        'summary': {
            'total_tickers_scanned': len(tickers),
            'tickers_with_signal': tickers_with_signal,
            'tickers_displayed': len(results),
            'filter_mode': filter_mode,
            'strategy': strategy,
            'flow_enabled': include_flow,
            'flow_threshold': flow_threshold
        }
    })"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Patch 2: api_multi_quick_scan - intersection mode
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Find this section and add flow attachment before final results.append
OLD_INTERSECTION_APPEND = """            results.append({
                'ticker': ticker,
                'strategies': strategies,
                'has_signal': all_pass,
                'signal_reasons': combined_reasons,
                'signal_details': combined_details
            })"""

NEW_INTERSECTION_APPEND = """            result = {
                'ticker': ticker,
                'strategies': strategies,
                'has_signal': all_pass,
                'signal_reasons': combined_reasons,
                'signal_details': combined_details
            }
            results.append(result)"""

# After intersection results loop, before union mode check
OLD_UNION_START = """    else:
        # UNION: group by strategy (old behavior)"""

NEW_UNION_START = """        # Attach flow for intersection results
        include_flow = body.get('include_flow', True)
        flow_threshold = body.get('flow_threshold', 2)
        results = attach_flow_data(results, include_flow, flow_threshold)
    else:
        # UNION: group by strategy (old behavior)"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Patch 3: api_multi_quick_scan - union mode return
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Need to see full return, but will patch before return jsonify in union mode
OLD_UNION_RETURN_START = """        return jsonify({
            'success': True,
            'results': results_by_strategy,"""

NEW_UNION_RETURN_START = """        # Attach flow for union results
        include_flow = body.get('include_flow', True)
        flow_threshold = body.get('flow_threshold', 2)
        for strategy in results_by_strategy:
            results_by_strategy[strategy] = attach_flow_data(
                results_by_strategy[strategy],
                include_flow,
                flow_threshold
            )
        
        return jsonify({
            'success': True,
            'results': results_by_strategy,"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Execution
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def apply_patches():
    print("=" * 60)
    print("Endpoint Flow Integration - Targeted Patch")
    print("=" * 60)
    
    if not os.path.exists(APP_PY):
        print(f"✗ Error: {APP_PY} not found")
        return 1
    
    # Backup
    backup = APP_PY + BACKUP_SUFFIX
    shutil.copy2(APP_PY, backup)
    print(f"✓ Backup created: {backup}")
    
    # Read
    with open(APP_PY, 'r') as f:
        content = f.read()
    
    print("\nApplying patches...")
    print("-" * 60)
    
    # Patch 1: quick_scan return
    if OLD_QUICK_SCAN_RETURN in content:
        content = content.replace(OLD_QUICK_SCAN_RETURN, NEW_QUICK_SCAN_RETURN)
        print("✓ Patched api_quick_scan return statement")
    else:
        print("⊘ api_quick_scan already patched or structure changed")
    
    # Patch 2: intersection mode flow attachment
    if OLD_UNION_START in content and "attach_flow_data(results" not in content.split(OLD_UNION_START)[0].split("if intersection_mode:")[-1]:
        content = content.replace(OLD_UNION_START, NEW_UNION_START)
        print("✓ Patched intersection mode flow attachment")
    else:
        print("⊘ Intersection mode already patched")
    
    # Patch 3: union mode flow attachment
    if OLD_UNION_RETURN_START in content and "attach_flow_data" not in content.split(OLD_UNION_RETURN_START)[0].split("else:")[-1]:
        content = content.replace(OLD_UNION_RETURN_START, NEW_UNION_RETURN_START)
        print("✓ Patched union mode flow attachment")
    else:
        print("⊘ Union mode already patched")
    
    # Write back
    with open(APP_PY, 'w') as f:
        f.write(content)
    
    print("-" * 60)
    print("✓ Patching complete!")
    print("\nNext steps:")
    print("  1. sudo systemctl restart idx-walkforward")
    print("  2. sudo journalctl -u idx-walkforward -f")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    exit(apply_patches())
