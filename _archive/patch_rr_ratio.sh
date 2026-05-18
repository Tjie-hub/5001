#!/bin/bash
echo "Patching paper_trade.py for 2:1 R/R ratio..."

# Backup
cp paper_trade.py paper_trade.py.backup_rr_$(date +%Y%m%d_%H%M%S)

# Find line numbers
LINE_START=$(grep -n "if candidates:" paper_trade.py | head -1 | cut -d: -f1)
echo "Found 'if candidates:' at line $LINE_START"

# Use awk to replace the block
awk -v start="$LINE_START" '
NR == start {
    print "        if candidates:"
    print "            swing_tp = min(candidates) * 0.995  # -0.5%"
    print "            "
    print "            # ENFORCE MINIMUM 2:1 R/R RATIO"
    print "            cfg = get_config()"
    print "            sl_pct = cfg.get(\"sl_pct\", 0.025)"
    print "            sl_price = entry_price * (1 - sl_pct)"
    print "            sl_distance = entry_price - sl_price"
    print "            min_tp_for_2to1 = entry_price + (2 * sl_distance)"
    print "            final_tp = max(swing_tp, min_tp_for_2to1)"
    print "            print(f\"[TP] {ticker}: Swing={swing_tp:.0f}, Min2:1={min_tp_for_2to1:.0f}, Final={final_tp:.0f}\")"
    print "            return round(final_tp)"
    # Skip next 2 lines (original tp = min... and return round...)
    getline; getline
    next
}
{print}
' paper_trade.py > paper_trade.py.tmp && mv paper_trade.py.tmp paper_trade.py

echo "✓ Patched! R/R ratio now enforced at 2:1 minimum"
