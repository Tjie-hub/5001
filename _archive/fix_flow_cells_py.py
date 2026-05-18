#!/usr/bin/env python3
"""
Flow Cells Fix - Direct String Replacement
Usage: python3 fix_flow_cells_py.py
"""

import shutil
from datetime import datetime

TEMPLATE = "/home/tjiesar/10 Projects/idx-walkforward-5001/templates/backtest_multi.html"
BACKUP_SUFFIX = f".fix_cells_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pattern 1: Intersection mode - EXACT MATCH
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OLD_INTERSECTION_CELLS = """                                        <td>
                                            ${r.strategies.map(s => `<span class="strategy-tag">${strategyName(s)}</span>`).join('')}
                                        </td>
                                        <td>
                                            ${r.signal_reasons.map(reason => `
                                                <div class="signal-detail">${reason}</div>
                                            `).join('')}
                                        </td>"""

NEW_INTERSECTION_CELLS = """                                        <td>
                                            ${r.strategies.map(s => `<span class="strategy-tag">${strategyName(s)}</span>`).join('')}
                                        </td>
                                        <td>${formatFlowScore(r.flow)}</td>
                                        <td>${formatFlowVerdict(r.flow)}</td>
                                        <td>${formatSmartMoney(r.flow)}</td>
                                        <td>
                                            ${r.signal_reasons.map(reason => `
                                                <div class="signal-detail">${reason}</div>
                                            `).join('')}
                                        </td>"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pattern 2: Union mode - EXACT MATCH
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OLD_UNION_CELLS = """                                        <td><strong>${r.ticker}</strong></td>
                                        <td>${r.signal_reason}</td>
                                        <td>${formatDetails(r.signal_details, strategy)}</td>"""

NEW_UNION_CELLS = """                                        <td><strong>${r.ticker}</strong></td>
                                        <td>${formatFlowScore(r.flow)}</td>
                                        <td>${formatFlowVerdict(r.flow)}</td>
                                        <td>${formatSmartMoney(r.flow)}</td>
                                        <td>${r.signal_reason}</td>
                                        <td>${formatDetails(r.signal_details, strategy)}</td>"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main execution
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    print("=" * 60)
    print("Flow Cells Fix - String Replacement")
    print("=" * 60)
    
    # Backup
    backup = TEMPLATE + BACKUP_SUFFIX
    shutil.copy2(TEMPLATE, backup)
    print(f"✓ Backup created: {backup}")
    
    # Read
    with open(TEMPLATE, 'r') as f:
        content = f.read()
    
    print("\nApplying fixes...")
    print("-" * 60)
    
    # Fix 1: Intersection mode
    if OLD_INTERSECTION_CELLS in content:
        content = content.replace(OLD_INTERSECTION_CELLS, NEW_INTERSECTION_CELLS)
        print("✓ Fixed intersection mode row cells")
    else:
        print("⊘ Intersection cells already fixed or pattern not found")
    
    # Fix 2: Union mode
    if OLD_UNION_CELLS in content:
        content = content.replace(OLD_UNION_CELLS, NEW_UNION_CELLS)
        print("✓ Fixed union mode row cells")
    else:
        print("⊘ Union cells already fixed or pattern not found")
    
    # Write back
    with open(TEMPLATE, 'w') as f:
        f.write(content)
    
    print("-" * 60)
    print("✓ Fix complete!")
    print("\nTest:")
    print("  1. Browser: Ctrl+Shift+R (hard refresh)")
    print("  2. http://192.168.31.120:5001/signal-scanner")
    print("  3. Click 'Scan All'")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    exit(main())
