#!/usr/bin/env python3
"""
Phase 1C: Flow Filter Toggle
Add checkbox to filter by flow confirmation (score >= +2)
Usage: python3 add_flow_filter.py
"""

import shutil
from datetime import datetime

TEMPLATE = "/home/tjiesar/idx-walkforward/templates/backtest_multi.html"
BACKUP_SUFFIX = f".phase1c_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Patch 1: Add flow filter checkbox in HTML
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OLD_FILTER_OPTIONS = """                <div class="filter-option">
                    <input type="checkbox" id="displaySeparate">
                    <label for="displaySeparate">📊 Tampilkan terpisah per strategy</label>
                </div>
                <div class="help-text">
                    ℹ️ Default: hanya ticker yang lolos SEMUA strategy yang dipilih
                </div>"""

NEW_FILTER_OPTIONS = """                <div class="filter-option">
                    <input type="checkbox" id="displaySeparate">
                    <label for="displaySeparate">📊 Tampilkan terpisah per strategy</label>
                </div>
                <div class="filter-option">
                    <input type="checkbox" id="flowConfirmedOnly">
                    <label for="flowConfirmedOnly">✅ Flow Confirmed Only (score >= +2)</label>
                </div>
                <div class="help-text">
                    ℹ️ Default: hanya ticker yang lolos SEMUA strategy yang dipilih
                </div>"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Patch 2: Add flow filter logic in displayResults function
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OLD_DISPLAY_START = """        function displayResults(data) {
            const { results, summary, intersection_mode } = data;
            
            // Summary cards"""

NEW_DISPLAY_START = """        function displayResults(data) {
            let { results, summary, intersection_mode } = data;
            
            // Apply flow filter if enabled
            const flowFilterEnabled = document.getElementById('flowConfirmedOnly').checked;
            let flowFilteredCount = 0;
            
            if (flowFilterEnabled) {
                if (intersection_mode) {
                    // Filter intersection results
                    const beforeFilter = results.length;
                    results = results.filter(r => r.flow && r.flow.confirmed);
                    flowFilteredCount = beforeFilter - results.length;
                } else {
                    // Filter union results per strategy
                    for (const strategy in results) {
                        const beforeFilter = results[strategy].length;
                        results[strategy] = results[strategy].filter(r => r.flow && r.flow.confirmed);
                        flowFilteredCount += beforeFilter - results[strategy].length;
                    }
                }
            }
            
            // Summary cards"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Patch 3: Update summary cards to show flow stats
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OLD_INTERSECTION_SUMMARY = """                summaryHTML = `
                    <div class="summary-cards">
                        <div class="summary-card">
                            <h3>Total Scanned</h3>
                            <div class="value">${summary.total_tickers_scanned}</div>
                        </div>
                        <div class="summary-card">
                            <h3>Pass ALL Strategies</h3>
                            <div class="value">${summary.tickers_with_all_signals}</div>
                        </div>
                        <div class="summary-card">
                            <h3>Strategies Selected</h3>
                            <div class="value">${summary.strategies.length}</div>
                        </div>
                    </div>
                `;"""

NEW_INTERSECTION_SUMMARY = """                const flowConfirmedCount = results.filter(r => r.flow && r.flow.confirmed).length;
                
                summaryHTML = `
                    <div class="summary-cards">
                        <div class="summary-card">
                            <h3>Total Scanned</h3>
                            <div class="value">${summary.total_tickers_scanned}</div>
                        </div>
                        <div class="summary-card">
                            <h3>Pass ALL Strategies</h3>
                            <div class="value">${results.length}</div>
                        </div>
                        <div class="summary-card" style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%);">
                            <h3>Flow Confirmed</h3>
                            <div class="value">${flowConfirmedCount}</div>
                        </div>
                        <div class="summary-card">
                            <h3>Strategies Selected</h3>
                            <div class="value">${summary.strategies.length}</div>
                        </div>
                    </div>
                `;"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Patch 4: Update union mode summary
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OLD_UNION_SUMMARY = """            } else {
                // Union mode (separate display)
                summaryHTML = `
                    <div class="summary-cards">
                        <div class="summary-card">
                            <h3>Total Scanned</h3>
                            <div class="value">${summary.total_tickers_scanned}</div>
                        </div>
                        <div class="summary-card">
                            <h3>Total Signals</h3>
                            <div class="value">${summary.total_signals}</div>
                        </div>"""

NEW_UNION_SUMMARY = """            } else {
                // Union mode (separate display)
                const totalSignalsNow = Object.values(results).reduce((sum, arr) => sum + arr.length, 0);
                const flowConfirmedCount = Object.values(results).reduce((sum, arr) => 
                    sum + arr.filter(r => r.flow && r.flow.confirmed).length, 0);
                
                summaryHTML = `
                    <div class="summary-cards">
                        <div class="summary-card">
                            <h3>Total Scanned</h3>
                            <div class="value">${summary.total_tickers_scanned}</div>
                        </div>
                        <div class="summary-card">
                            <h3>Total Signals</h3>
                            <div class="value">${totalSignalsNow}</div>
                        </div>
                        <div class="summary-card" style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%);">
                            <h3>Flow Confirmed</h3>
                            <div class="value">${flowConfirmedCount}</div>
                        </div>"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main execution
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    print("=" * 60)
    print("Phase 1C: Flow Filter Toggle")
    print("=" * 60)
    
    # Backup
    backup = TEMPLATE + BACKUP_SUFFIX
    shutil.copy2(TEMPLATE, backup)
    print(f"✓ Backup created: {backup}")
    
    # Read
    with open(TEMPLATE, 'r') as f:
        content = f.read()
    
    print("\nApplying patches...")
    print("-" * 60)
    
    # Patch 1: Checkbox
    if "flowConfirmedOnly" not in content:
        content = content.replace(OLD_FILTER_OPTIONS, NEW_FILTER_OPTIONS)
        print("✓ Added flow filter checkbox")
    else:
        print("⊘ Flow filter checkbox already exists")
    
    # Patch 2: Filter logic
    if "flowFilterEnabled" not in content:
        content = content.replace(OLD_DISPLAY_START, NEW_DISPLAY_START)
        print("✓ Added flow filter logic")
    else:
        print("⊘ Flow filter logic already exists")
    
    # Patch 3: Intersection summary
    if "Flow Confirmed" not in content or "flowConfirmedCount" not in content.split(OLD_INTERSECTION_SUMMARY)[0]:
        content = content.replace(OLD_INTERSECTION_SUMMARY, NEW_INTERSECTION_SUMMARY)
        print("✓ Updated intersection summary cards")
    else:
        print("⊘ Intersection summary already updated")
    
    # Patch 4: Union summary
    if OLD_UNION_SUMMARY in content and "flowConfirmedCount" not in content.split(OLD_UNION_SUMMARY)[0]:
        content = content.replace(OLD_UNION_SUMMARY, NEW_UNION_SUMMARY)
        print("✓ Updated union summary cards")
    else:
        print("⊘ Union summary already updated")
    
    # Write back
    with open(TEMPLATE, 'w') as f:
        f.write(content)
    
    print("-" * 60)
    print("✓ Phase 1C complete!")
    print("\nTest:")
    print("  1. Ctrl+Shift+R (hard refresh)")
    print("  2. Check new checkbox: 'Flow Confirmed Only'")
    print("  3. Scan with filter ON → only score >= +2")
    print("  4. Summary card 'Flow Confirmed' should show count")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    exit(main())
