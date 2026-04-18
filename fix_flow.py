#!/usr/bin/env python3
import re

with open('stockbit_fetcher.py.backup', 'r') as f:
    content = f.read()

# Fix: Remove all tabs, convert to 4 spaces
content = content.expandtabs(4)

# Fix: Remove _compute_score flag line
content = re.sub(r'\s*_compute_score\s*=\s*True.*\n', '', content)

# Fix: Change "if _compute_score and flow.get" to "if flow.get"
content = re.sub(
    r'if _compute_score and (flow\.get\("_raw_data"\))',
    r'if \1',
    content
)

# Fix: Change _flow_analyze to _analyze
content = content.replace('_flow_analyze', '_analyze')

# Verify import exists
if 'from flow_filter import _parse_bars, _analyze' not in content:
    # Add after datetime import
    content = content.replace(
        'from datetime import datetime',
        'from datetime import datetime\nfrom flow_filter import _parse_bars, _analyze'
    )

with open('stockbit_fetcher.py', 'w') as f:
    f.write(content)

print("✅ Fixed: stockbit_fetcher.py")
