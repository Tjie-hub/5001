#!/usr/bin/env python3
"""
Frontend Flow Integration Patch
Add flow score, verdict, and smart money columns to signal scanner
Usage: python3 patch_frontend_flow.py
"""

import os
import shutil
from datetime import datetime

TEMPLATE = "/home/tjiesar/10 Projects/idx-walkforward-5001/templates/backtest_multi.html"
BACKUP_SUFFIX = f".backup_flow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Patch 1: Add CSS for flow badges
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CSS_INSERT_MARKER = "        tbody tr:hover { background: #f8f9fa; }"

FLOW_CSS = """        tbody tr:hover { background: #f8f9fa; }
        
        /* Flow score badges */
        .flow-score {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 0.9em;
        }
        .flow-bullish { background: #28a745; color: white; }
        .flow-neutral { background: #6c757d; color: white; }
        .flow-bearish { background: #dc3545; color: white; }
        .flow-unavailable { background: #e9ecef; color: #6c757d; }
        
        .flow-verdict {
            font-size: 0.85em;
            padding: 2px 6px;
            border-radius: 3px;
        }
        .verdict-BULLISH { background: #d4edda; color: #155724; }
        .verdict-NEUTRAL { background: #fff3cd; color: #856404; }
        .verdict-BEARISH { background: #f8d7da; color: #721c24; }
        .verdict-UNAVAILABLE { background: #e9ecef; color: #6c757d; }
        
        .smart-money {
            font-size: 0.8em;
            color: #6c757d;
        }"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Patch 2: Add helper function for flow formatting (before displayResults)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HELPER_INSERT_MARKER = "        function displayResults(data) {"

FLOW_HELPER = """        function formatFlowScore(flow) {
            if (!flow || !flow.available) {
                return '<span class="flow-score flow-unavailable">N/A</span>';
            }
            
            const score = flow.score;
            let cssClass = 'flow-neutral';
            if (score >= 2) cssClass = 'flow-bullish';
            else if (score <= -2) cssClass = 'flow-bearish';
            
            const confirmed = flow.confirmed ? '✓' : '';
            return `<span class="flow-score ${cssClass}">${score > 0 ? '+' : ''}${score} ${confirmed}</span>`;
        }
        
        function formatFlowVerdict(flow) {
            if (!flow || !flow.available) {
                return '<span class="flow-verdict verdict-UNAVAILABLE">N/A</span>';
            }
            return `<span class="flow-verdict verdict-${flow.verdict}">${flow.verdict}</span>`;
        }
        
        function formatSmartMoney(flow) {
            if (!flow || !flow.available) {
                return '<span class="smart-money">-</span>';
            }
            return `<span class="smart-money">${flow.smart_money || 'N/A'}</span>`;
        }
        
        function displayResults(data) {"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Patch 3: Intersection mode - add headers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OLD_INTERSECTION_HEADER = """                            <thead>
                                <tr>
                                    <th>Ticker</th>
                                    <th>Strategies</th>
                                    <th>Signal Details</th>
                                </tr>
                            </thead>"""

NEW_INTERSECTION_HEADER = """                            <thead>
                                <tr>
                                    <th>Ticker</th>
                                    <th>Strategies</th>
                                    <th>Flow Score</th>
                                    <th>Flow Verdict</th>
                                    <th>Smart Money</th>
                                    <th>Signal Details</th>
                                </tr>
                            </thead>"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Patch 4: Intersection mode - add row cells
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OLD_INTERSECTION_ROW = """                                ${results.map(r => `
                                    <tr>
                                        <td><strong>${r.ticker}</strong></td>
                                        <td>
                                            ${r.strategies.map(s => `<span class="strategy-tag">${strategyName(s)}</span>`).join('')}
                                        </td>
                                        <td>
                                            ${r.signal_reasons.map(reason => `
                                                <div class="signal-detail">${reason}</div>
                                            `).join('')}
                                        </td>
                                    </tr>
                                `).join('')}"""

NEW_INTERSECTION_ROW = """                                ${results.map(r => `
                                    <tr>
                                        <td><strong>${r.ticker}</strong></td>
                                        <td>
                                            ${r.strategies.map(s => `<span class="strategy-tag">${strategyName(s)}</span>`).join('')}
                                        </td>
                                        <td>${formatFlowScore(r.flow)}</td>
                                        <td>${formatFlowVerdict(r.flow)}</td>
                                        <td>${formatSmartMoney(r.flow)}</td>
                                        <td>
                                            ${r.signal_reasons.map(reason => `
                                                <div class="signal-detail">${reason}</div>
                                            `).join('')}
                                        </td>
                                    </tr>
                                `).join('')}"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Patch 5: Union mode - add headers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OLD_UNION_HEADER = """                            <thead>
                                <tr>
                                    <th>Ticker</th>
                                    <th>Signal Info</th>
                                    <th>Details</th>
                                </tr>
                            </thead>"""

NEW_UNION_HEADER = """                            <thead>
                                <tr>
                                    <th>Ticker</th>
                                    <th>Flow Score</th>
                                    <th>Flow Verdict</th>
                                    <th>Smart Money</th>
                                    <th>Signal Info</th>
                                    <th>Details</th>
                                </tr>
                            </thead>"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Patch 6: Union mode - add row cells
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OLD_UNION_ROW = """                                ${tickerList.map(r => `
                                    <tr>
                                        <td><strong>${r.ticker}</strong></td>
                                        <td>${r.signal_reason}</td>
                                        <td>${formatDetails(r.signal_details, strategy)}</td>
                                    </tr>
                                `).join('')}"""

NEW_UNION_ROW = """                                ${tickerList.map(r => `
                                    <tr>
                                        <td><strong>${r.ticker}</strong></td>
                                        <td>${formatFlowScore(r.flow)}</td>
                                        <td>${formatFlowVerdict(r.flow)}</td>
                                        <td>${formatSmartMoney(r.flow)}</td>
                                        <td>${r.signal_reason}</td>
                                        <td>${formatDetails(r.signal_details, strategy)}</td>
                                    </tr>
                                `).join('')}"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main execution
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def apply_patches():
    print("=" * 60)
    print("Frontend Flow Integration Patch")
    print("=" * 60)
    
    if not os.path.exists(TEMPLATE):
        print(f"✗ Error: {TEMPLATE} not found")
        return 1
    
    # Backup
    backup = TEMPLATE + BACKUP_SUFFIX
    shutil.copy2(TEMPLATE, backup)
    print(f"✓ Backup created: {backup}")
    
    # Read
    with open(TEMPLATE, 'r') as f:
        content = f.read()
    
    print("\nApplying patches...")
    print("-" * 60)
    
    # Patch 1: CSS
    if "flow-score" not in content:
        content = content.replace(CSS_INSERT_MARKER, FLOW_CSS)
        print("✓ Added flow CSS styles")
    else:
        print("⊘ Flow CSS already exists")
    
    # Patch 2: Helper functions
    if "formatFlowScore" not in content:
        content = content.replace(HELPER_INSERT_MARKER, FLOW_HELPER)
        print("✓ Added flow helper functions")
    else:
        print("⊘ Flow helpers already exist")
    
    # Patch 3: Intersection header
    if OLD_INTERSECTION_HEADER in content and "Flow Score" not in content.split(OLD_INTERSECTION_HEADER)[0]:
        content = content.replace(OLD_INTERSECTION_HEADER, NEW_INTERSECTION_HEADER)
        print("✓ Patched intersection mode table header")
    else:
        print("⊘ Intersection header already patched")
    
    # Patch 4: Intersection rows
    if OLD_INTERSECTION_ROW in content and "formatFlowScore" not in content.split(OLD_INTERSECTION_ROW)[0].split("results.map")[-1]:
        content = content.replace(OLD_INTERSECTION_ROW, NEW_INTERSECTION_ROW)
        print("✓ Patched intersection mode table rows")
    else:
        print("⊘ Intersection rows already patched")
    
    # Patch 5: Union header
    if OLD_UNION_HEADER in content and "Flow Score" not in content.split(OLD_UNION_HEADER)[-1].split(OLD_INTERSECTION_HEADER)[0]:
        content = content.replace(OLD_UNION_HEADER, NEW_UNION_HEADER)
        print("✓ Patched union mode table header")
    else:
        print("⊘ Union header already patched")
    
    # Patch 6: Union rows
    if OLD_UNION_ROW in content and "formatFlowScore" not in content.split(OLD_UNION_ROW)[0].split("tickerList.map")[-1]:
        content = content.replace(OLD_UNION_ROW, NEW_UNION_ROW)
        print("✓ Patched union mode table rows")
    else:
        print("⊘ Union rows already patched")
    
    # Write back
    with open(TEMPLATE, 'w') as f:
        f.write(content)
    
    print("-" * 60)
    print("✓ Patching complete!")
    print("\nTest di browser:")
    print("  http://192.168.31.120:5001/signal-scanner")
    print("\nNo restart needed - just refresh browser!")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    exit(apply_patches())
